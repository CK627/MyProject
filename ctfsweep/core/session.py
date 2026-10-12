# -*- coding: utf-8 -*-
"""交互会话提取：FTP 登录/爆破序列、反弹 shell（交互式命令会话）。

针对"入侵行为分析"类取证题（问答式取证，2022 中职组等比赛的常见题型）：
- FTP：登录尝试序列（USER/PASS 失败与成功）、成功凭据、登录后命令序列
- 交互 shell：Windows cmd（含版本 banner）与 Linux shell 的命令记录与回显
- 输出可直接回答："第 N 条命令是什么"、"执行了什么操作"、"系统版本号"

纯标准库。用法：analyze_sessions(tcp_streams, add_finding) → [展示行]
"""
import re

from .capture import merge_stream

# ---------------------------------------------------------------- FTP
_FTP_CMD = re.compile(rb'^([A-Z]{3,5})(?:\s(.*))?$')


def _ftp_lines(blob):
    """blob → [(line bytes)]（去空行、\x00）"""
    out = []
    for raw in re.split(rb'\r?\n', blob):
        line = raw.replace(b'\x00', b'').strip()
        if line:
            out.append(line)
    return out


def _analyze_ftp_client(cli_segs, srv_segs):
    """返回 dict：attempts / success / commands / banner

    通过客户端/服务端包号合并为统一时序，精确配对登录尝试与响应：
    - PASS 后有 '530' = 失败，'230' = 成功
    - 命令序列 = 登录成功之后的全部 FTP 命令
    """
    # 统一时间线：(num, side, line)
    events = []
    for seg in cli_segs:
        for line in _ftp_lines(seg[2]):
            events.append((seg[0], 'C', line))
    for seg in srv_segs:
        for line in _ftp_lines(seg[2]):
            events.append((seg[0], 'S', line))
    events.sort(key=lambda e: e[0])

    attempts = []
    success = None
    cur_user = None
    last_attempt = None
    logged_in = False
    commands = []
    banner = None
    skip = {b'USER', b'PASS', b'QUIT'}

    for num, side, line in events:
        if side == 'C':
            m = re.match(rb'USER\s+(.*)', line, re.I)
            if m:
                cur_user = m.group(1).decode('latin-1', 'replace')
                continue
            m = re.match(rb'PASS\s*(.*)', line, re.I)
            if m:
                last_attempt = (cur_user or '?', m.group(1).decode('latin-1', 'replace'))
                attempts.append(last_attempt)
                cur_user = None
                continue
            # 命令序列（登录成功后）
            if logged_in:
                m = _FTP_CMD.match(line)
                if m:
                    cmd = m.group(1)
                    if cmd not in skip:
                        arg = (m.group(2) or b'').decode('latin-1', 'replace')
                        commands.append(('%s %s' % (cmd.decode(), arg)).strip())
        else:
            if banner is None and line.startswith(b'220'):
                banner = line.decode('latin-1', 'replace')
            if line.startswith(b'230') and last_attempt and not logged_in:
                success = last_attempt
                logged_in = True
            elif line.startswith(b'530') and last_attempt and success == last_attempt:
                # 极端情况：530 出现在 230 之后（不应发生，保护）
                success = None
                logged_in = False
            elif line.startswith(b'221') and logged_in:
                logged_in = False  # 会话结束（QUIT），后续重新登录的命令不再计
    return {'attempts': attempts, 'success': success, 'commands': commands, 'banner': banner}


# ---------------------------------------------------------------- Shell（交互会话）
# Windows 提示符：行首（或换行后）的 "X:\路径>"。
# ① 行首锚定 + ② 内容禁 '<'：防止把 HTML 网页里的 C:\ 字样/标签误当提示符
#    （HTTP 文件服务器页面曾整页误报"命令序列"）
_WIN_PROMPT = re.compile(rb'(?:^|[\r\n])([A-Za-z]:\\[^\r\n<>]{0,90}>)')
_WIN_BANNER = re.compile(rb'Microsoft Windows \[[^\]]{0,20}?(\d+(?:\.\d+)+)[^\]]{0,20}\]')
_WIN_KNOWN = [b'whoami', b'net user', b'net localgroup', b'ipconfig', b'systeminfo',
              b'tasklist', b'schtasks', b'netstat', b'shutdown', b'hostname', b'chcp',
              b'wmic', b'reg ', b'dir', b'type ', b'taskkill', b'net share', b'net start',
              b'net stop', b'query user', b'sc ', b'ping ', b'copy ', b'del ', b'move ',
              b'powershell', b'cmd', b'ver', b'set ', b'md ', b'rd ']
# 已知 Windows 命令词首（用于交互会话强度判定，防二进制误报）
_WIN_CMD_HEADS = {'whoami', 'ipconfig', 'net', 'dir', 'cd', 'type', 'chcp', 'systeminfo',
                  'tasklist', 'hostname', 'ver', 'shutdown', 'taskkill', 'query', 'wmic',
                  'reg', 'ping', 'sc', 'copy', 'del', 'move', 'schtasks', 'netstat',
                  'powershell', 'cmd', 'set', 'md', 'rd', 'echo', 'cls', 'exit', 'time',
                  'date', 'attrib', 'find', 'findstr', 'tree', 'path', 'start'}
_LNX_KNOWN = [b'whoami', b'id', b'uname', b'cat ', b'ls ', b'ls\n', b'pwd', b'cd ',
              b'ps ', b'wget ', b'curl ', b'chmod ', b'bash', b'python', b'find ',
              b'grep ', b'nc ', b'netstat', b'ifconfig', b'export ', b'echo ']

# Linux 命令语法：行 = 命令词（+ 短参数）。用于识别"命令行会话"方向（如反弹 shell 客户端）
_LNX_CMD_RE = re.compile(
    rb'^(id|whoami|pwd|uname|ls|ps|cat|cd|echo|nohup|wget|curl|chmod|chown|nc|bash|sh'
    rb'|python[23]?|perl|find|grep|netstat|ifconfig|ip|top|free|df|du|hostname|date|kill'
    rb'|mkdir|rm|cp|mv|touch|tar|zip|unzip|crontab|service|systemctl|reboot|shutdown'
    rb'|passwd|useradd|adduser|su|sudo|ssh|scp|nmap|hydra|mysql|sqlite3|export)'
    rb'(\s[^\r\n]{0,80})?$', re.I)


def _parse_win_transcript(blob):
    """从含 Windows 提示符的 blob 解析 [(cmd, output_snippet)]"""
    parts = _WIN_PROMPT.split(blob)
    # parts: [前置, prompt1, body1, prompt2, body2, ...]
    cmds = []
    for i in range(1, len(parts) - 1, 2):
        body = parts[i + 1].replace(b'\x00', b'')
        # body: 第一行=命令回显，后续=输出
        lines = body.split(b'\n', 1)
        cmd = lines[0].strip(b'\r ')
        if not cmd or len(cmd) > 120:
            continue
        cmd_s = _clean_cmd(cmd)
        if cmd_s is None:
            continue
        out = lines[1].strip()[:160] if len(lines) > 1 else ''
        try:
            out_s = out.decode('gbk', 'replace').strip()
        except Exception:
            out_s = ''
        cmds.append((cmd_s, out_s))
    return cmds


def _clean_cmd(cmd_bytes):
    """命令净化：必须是 ASCII 主导的可打印文本（拒绝二进制噪声段）。

    误报来源：①TLS 随机字节可能撞上 'X:\\...>' 模式，其"命令"实际是乱码，
    解码后呈现 CJK/控制字符主导——用 ASCII 占比校验剔除；
    ②HTML/XML 标记行（</td></tr>、<a href=...>）——含 '<' 或实体即剔除。
    """
    if not cmd_bytes or len(cmd_bytes) > 120:
        return None
    if b'<' in cmd_bytes or b'&lt;' in cmd_bytes or b'&gt;' in cmd_bytes:
        return None
    ascii_ok = sum(1 for b in cmd_bytes if 32 <= b < 127)
    if ascii_ok < len(cmd_bytes) * 0.85:
        return None
    if any(b < 32 and b not in (9,) for b in cmd_bytes):
        return None
    try:
        s = cmd_bytes.decode('ascii').strip()
    except Exception:
        return None
    if not s or not any(ch.isalnum() for ch in s):
        return None
    return s


def analyze_sessions(tcp_streams, add_finding=None):
    """分析 TCP 会话集合，返回展示行列表；发现通过 add_finding 回调登记。

    tcp_streams: {(src, sport, dst, dport): [(num, ts, payload, seq), ...]}
    add_finding: 同 scanner.add，签名 add((score, kind, tok, val, loc))
    """
    lines = []
    done_pairs = set()

    # ---------------- FTP ----------------
    keys = set(tcp_streams.keys())
    for key in sorted(keys):
        src, sport, dst, dport = key
        if dport != 21 or key in done_pairs:
            continue
        rev = (dst, dport, src, sport)
        if rev not in keys:
            continue
        done_pairs.add(key)
        done_pairs.add(rev)
        cli_segs = tcp_streams[key]
        srv_segs = tcp_streams[rev]
        if not any(b'USER' in s[2] for s in cli_segs):
            continue
        info = _analyze_ftp_client(cli_segs, srv_segs)
        n_att = len(info['attempts'])
        if n_att == 0:
            continue
        att_disp = ', '.join('%s/%s' % (u or '(空)', p or '(空)') for u, p in info['attempts'][:6])
        succ = info['success']
        head = '  [FTP会话] %s:%d → %s:%d 登录尝试 %d 次: %s' % (src, sport, dst, dport, n_att, att_disp)
        lines.append(head)
        if succ:
            ok_user, ok_pass = succ
            lines.append('    成功凭据: %s / %s' % (ok_user, ok_pass))
            if add_finding:
                add_finding((0.85, 'FTP成功凭据', b'',
                             '%s / %s' % (ok_user, ok_pass),
                             'FTP %s:%d→%s:%d' % (src, sport, dst, dport)))
        if info['commands']:
            seq = ' → '.join(info['commands'])
            lines.append('    命令序列(%d): %s' % (len(info['commands']), seq[:600]))
            if add_finding and succ:
                add_finding((0.8, 'FTP命令序列', b'', seq[:400],
                             'FTP %s:%d→%s:%d（登录后）' % (src, sport, dst, dport)))

        # ---- vsftpd 2.3.4 笑脸后门（CVE-2011-2523）特征 ----
        # 严格判定：banner 必须是 vsFTPd 2.3.4（该后门版本）才可能触发；
        # 其他服务器的 "user:)"" 可能是笔误（如 Microsoft FTP 服务），不报
        banner = info.get('banner') or ''
        smile_users = [u for u, _p in info['attempts'] if u.endswith(':)')]
        is_vuln_ver = 'vsFTPd 2.3.4' in banner or 'vsftpd 2.3.4' in banner
        if is_vuln_ver or (smile_users and not banner):
            detail = 'vsftpd 2.3.4 笑脸后门（CVE-2011-2523）'
            if smile_users:
                detail += '：USER %s 触发，后门 shell 监听 6200' % smile_users[0]
            else:
                detail += '：服务器为含后门版本（未观察到触发）'
            lines.append('    ⚠️ 检测到 %s（banner=%s）' % (detail, banner[:40]))
            if add_finding:
                add_finding((0.95, '漏洞利用', b'',
                             '%s；banner=%s' % (detail, banner[:60]),
                             'FTP %s:%d→%s:%d' % (src, sport, dst, dport)))

    # ---------------- 爆破工具输出提取（Hydra/Medusa 等）----------------
    # 特征：终端流中出现 "host: X login: Y password: Z"（常带 ANSI 颜色码）
    # 对应"hydra 爆破得到的密码是什么"类问题——直接出凭据
    seen_bf = set()
    for key in sorted(keys):
        if key in seen_bf:
            continue
        src, sport, dst, dport = key
        blob = merge_stream(tcp_streams[key])
        if b'password:' not in blob.lower() or b'login:' not in blob.lower():
            continue
        clean = re.sub(rb'\x1b\[[0-9;]*[A-Za-z]', b'', blob)  # 去 ANSI 转义
        hits = re.findall(
            rb'host:\s*([0-9a-zA-Z.:]+)\s+login:\s*(\S+)\s+password:\s*(\S+)', clean)
        if not hits:
            continue
        seen_bf.add(key)
        rev = (dst, dport, src, sport)
        seen_bf.add(rev)
        for host, user, pw in hits[:6]:
            h, u, p = host.decode(), user.decode(), pw.decode()
            lines.append('  [🔓 爆破结果] %s → login: %s / password: %s'
                         % (h, u, p))
            if add_finding:
                add_finding((0.95, '爆破成功凭据', b'',
                             '%s login:%s password:%s' % (h, u, p),
                             '终端流 %s:%d→%s:%d' % (src, sport, dst, dport)))
        # 扫描报告（Nmap OS/服务信息）
        for m in re.finditer(rb'Nmap scan report for ([^\r\n]{1,60})', clean):
            tgt = m.group(1).decode('latin-1', 'replace').strip()
            lines.append('  [Nmap报告] 目标: %s' % tgt)
            if add_finding:
                add_finding((0.8, '扫描报告', b'', 'Nmap 目标: %s' % tgt,
                             '终端流 %s:%d→%s:%d' % (src, sport, dst, dport)))

    # ---------------- Redis 利用特征（写文件提权链）----------------
    # 经典手法：AUTH 弱口令 → config set dir /root/.ssh → config set dbfilename
    # authorized_keys → set <ssh 公钥> → save（写公钥后可 root 免密登录）
    # 注意：逐方向独立检查（客户端方向才有攻击内容；服务端方向的 COMMAND 输出
    #       含 config 等词但无 /root/.ssh，不会误报）
    redis_exploit_done = set()
    redis_keys_seen = set()
    for key in sorted(keys):
        src, sport, dst, dport = key
        if 6379 not in (sport, dport):
            continue
        blob = merge_stream(tcp_streams[key])
        low = blob.lower()
        if b'config' not in low and b'AUTH' not in blob and b'ssh-rsa' not in low:
            continue
        # SSH 公钥素材（独立提取——可能出现在与 config 不同的流中）
        keydata = re.search(rb'ssh-rsa\s+[A-Za-z0-9+/=]{40,}', blob)
        if keydata and keydata.group(0)[:60] not in redis_keys_seen:
            redis_keys_seen.add(keydata.group(0)[:60])
            lines.append('  [⚠️ Redis利用] 流中发现 SSH 公钥（写 authorized_keys 素材）')
            if add_finding:
                add_finding((0.9, 'SSH公钥', b'',
                             keydata.group(0)[:200].decode('latin-1', 'replace'),
                             'Redis %s:%d↔%s:%d' % (src, sport, dst, dport)))
        # AUTH 密码提取（RESP 协议：AUTH\r\n$6\r\nxxxx）
        pw = ''
        m = re.search(rb'AUTH\r\n\$\d+\r\n([^\r\n]{1,64})\r\n', blob) or \
            re.search(rb'(?m)^AUTH[ \t]+([^\r\n]{1,64})\r?$', blob)
        if m:
            pw = m.group(1).decode('latin-1', 'replace').strip()
        wrote_ssh = (b'/root/.ssh' in low) or (b'authorized_keys' in low)
        cfg_write = (b'dbfilename' in low and b'config' in low)
        if (wrote_ssh or cfg_write) and (dst, dport) not in redis_exploit_done:
            redis_exploit_done.add((dst, dport))
            detail = 'Redis 写文件提权链'
            if wrote_ssh:
                detail += '（写 SSH 公钥 → authorized_keys，可 root 免密登录）'
            if pw:
                detail += '；AUTH 密码=%s' % pw
            lines.append('  [⚠️ Redis利用] %s:%d → %s:%d %s' % (src, sport, dst, dport, detail))
            if add_finding:
                add_finding((0.95, 'Redis利用', b'', detail,
                             'Redis %s:%d↔%s:%d' % (src, sport, dst, dport)))
        elif pw and (dst, dport) not in redis_exploit_done:
            redis_exploit_done.add((dst, dport))
            lines.append('  [Redis] %s:%d → %s:%d AUTH 密码: %s' % (src, sport, dst, dport, pw))
            if add_finding:
                add_finding((0.8, 'Redis凭据', b'', 'AUTH 密码=%s' % pw,
                             'Redis %s:%d↔%s:%d' % (src, sport, dst, dport)))

    # ---------------- 交互 Shell ----------------
    # 判定：某方向 blob 含 Windows 提示符/banner，或含 ≥4 个已知命令词
    seen_conv = set()
    for key in sorted(keys):
        if key in seen_conv:
            continue
        src, sport, dst, dport = key
        blob = merge_stream(tcp_streams[key])
        rev = (dst, dport, src, sport)
        rev_blob = merge_stream(tcp_streams[rev]) if rev in keys else b''

        win_hit = bool(_WIN_BANNER.search(blob)) or bool(_WIN_PROMPT.search(blob))
        if not win_hit:
            continue

        # 找出"被控端"blob（含 prompt 的那侧）
        host_blob = blob if _WIN_PROMPT.search(blob) else rev_blob
        cmds = _parse_win_transcript(host_blob)
        if not cmds:
            continue
        ver = None
        mv = _WIN_BANNER.search(host_blob) or _WIN_BANNER.search(blob)
        if mv:
            ver = mv.group(1).decode()

        cmd_list = [c for c, _o in cmds]
        # 强度门禁（防 TLS 随机字节撞 'X:\\...>' 误报）：
        # 有 banner / ≥2 条命令 / 命令以已知 Windows 命令词开头——三者之一才成立
        strong = bool(mv) or len(cmd_list) >= 2 or any(
            c.split(' ')[0].lower() in _WIN_CMD_HEADS for c in cmd_list)
        if not strong:
            continue
        seen_conv.add(key)
        seen_conv.add(rev)
        lines.append('  [交互会话] %s:%d ↔ %s:%d（Windows%s，%d 条命令）'
                     % (src, sport, dst, dport, (' ' + ver) if ver else '', len(cmd_list)))
        lines.append('    命令: ' + ' → '.join(cmd_list)[:600])
        if ver:
            lines.append('    系统版本: %s' % ver)
        if add_finding:
            tok = '; '.join(cmd_list)[:400]
            add_finding((0.9, '交互会话记录', b'',
                         '命令序列: %s' % tok,
                         '会话 %s:%d↔%s:%d' % (src, sport, dst, dport)))
            if ver:
                add_finding((0.85, '系统版本', b'', ver,
                             '会话 %s:%d↔%s:%d' % (src, sport, dst, dport)))

    # ---------------- Linux / 通用命令行会话 ----------------
    # 特征：某个方向的数据几乎全是"命令词"整行（反弹 shell 客户端发命令）；≥3 条命中即判定
    for key in sorted(keys):
        if key in seen_conv:
            continue
        src, sport, dst, dport = key
        # 跳过明显服务端口（避免把 HTTP/FTP/数据库协议正文里的词当命令）
        if dport in (21, 80, 443, 8080, 3306, 6379, 1433, 5432, 27017, 25, 110, 143) or \
           sport in (21, 80, 443, 8080, 3306, 6379, 1433, 5432, 27017, 25, 110, 143):
            continue
        blob = merge_stream(tcp_streams[key])
        if not blob or len(blob) > 65536:
            continue

        # ---- 暴露的 bash shell 特征（bind shell 被轻触即报 command not found）----
        # 如对小写探针 '\r\n' 直接返回 "bash: line 1: ...: command not found"
        if (b'bash: line' in blob or b': command not found' in blob) and len(blob) < 4096:
            lines.append('  [⚠️ shell服务] %s:%d → %s:%d 疑似暴露的 bash shell（对探测直接回命令解析错误）'
                         % (src, sport, dst, dport))
            if add_finding:
                add_finding((0.82, '暴露shell服务', b'',
                             '疑似 bash bind shell：对轻量探测返回 command not found',
                             '%s:%d→%s:%d' % (src, sport, dst, dport)))
            seen_conv.add(key)
            continue

        blob_lines = [l.replace(b'\x00', b'').strip() for l in re.split(rb'\r?\n', blob)]
        cmds = []
        for bl in blob_lines:
            if not (bl and len(bl) <= 100 and _LNX_CMD_RE.match(bl)):
                continue
            # 剔除 HTML/XML 标记行（&lt; 实体 / 标签）
            if b'<' in bl or b'&lt;' in bl or b'&gt;' in bl:
                continue
            # 剔除"工具输出行"（非用户命令）：URL/开始时间/报告头
            low = bl.lower()
            if any(k in low for k in (b'http://', b'https://', b' starting at ', b' finished at ',
                                      b' report for ', b' scan report')):
                continue
            try:
                cmds.append(bl.decode('utf-8', 'replace').strip())
            except Exception:
                pass
        if len(cmds) < 3:
            continue
        # 反向流存在且含输出（粗校验：有内容即可）
        rev = (dst, dport, src, sport)
        out_blob = merge_stream(tcp_streams[rev]) if rev in keys else b''
        seen_conv.add(key)
        seen_conv.add(rev)
        lines_out = ['  [交互会话] (Linux/命令) %s:%d → %s:%d（%d 条命令）'
                     % (src, sport, dst, dport, len(cmds))]
        lines_out.append('    命令: ' + ' → '.join(cmds)[:600])
        # 输出侧亮点（uid=/Linux 版本/root 等）
        if out_blob:
            m = re.search(rb'uid=\d+\([^)]*\)[^\r\n]{0,60}', out_blob)
            if m:
                lines_out.append('    权限回显: %s' % m.group(0).decode('latin-1', 'replace'))
            mv = re.search(rb'Linux [^\s]+ [\d.]+[^\r\n]{0,60}', out_blob)
            if mv:
                lines_out.append('    系统: %s' % mv.group(0).decode('latin-1', 'replace')[:100])
        lines.extend(lines_out)
        if add_finding:
            add_finding((0.88, '交互会话记录', b'',
                         '命令序列(Linux): %s' % ('; '.join(cmds))[:400],
                         '会话 %s:%d→%s:%d' % (src, sport, dst, dport)))

    return lines
