#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ctfsweep 冒烟测试（纯标准库、免安装）：

    python3 tests/test_smoke.py

覆盖：
  * CLI：--version / --help / 无参数 / 路径不存在
  * VERSION 文件与包版本一致性
  * shell 脚本体检：$VAR 后不得紧跟全角字符（bash 变量名解析坑）
  * 补全体检：位置驱动（对齐 jtool/ptool）——选项只在敲 "-" 之后出现，第一个参数位
    只出「子命令 + 文件」；选项列表经 compadd -l -d 添加并合并显示同义短/长（"-f --file"）；
    不得回退为 _describe -t options；包装函数在 update 后自动重载（免手动 source）；
    以上在真 shell 里驱动补全函数逐字断言，静态字面量体检只作兜底
  * t1.pcap：明文 flag / hex 解码 / DNS base64 外带 / JWT / 环境变量回显 / --min-score 过滤
  * t2.pcapng：pcapng 封装 + -f/--file 参数
  * t3.evtx：UTF-16 明文 + 花括号片段 + 启发式拼接 + 噪音闸门（dll 后缀 / GUID / 乱码区剔除）
  * t4.pcap --extract：文件雕刻 + zip 内容扫描 + 落盘
  * 判断核（judge）：微型数据集训练与分离、离线训练脚本 lab/train.py（留一组评估）、
    --judge 打分与无模型兜底；且**命令行不再有任何训练/标注入口**（自学习已移除）
  * 扫描缓存：每次扫描都写（默认模式与 -q 内容相同），数据根下只有 cache/；
    **一次运行一个目录**（目录扫描不再一文件一目录，归属靠每行的「← 相对路径」）
  * 元判断核（meta_judge）：综合分不低于模块自评（单调不降）/ 低权重模块不倒扣 /
    分档口径与 utils.level_of 一致 / 畸形 confidence 不中断报告
  * 管线边界：Finding↔5 元组往返后 report() 渲染逐字节不变（含 latin-1 token、str 型 val）
  * t5-ad.pcap：AD 域协议（Kerberos 票据 / NetNTLM 响应 / LDAP 明文绑定 / SPN）
  * t6-hosts.pcap：主机表（ARP/Ethernet IP↔MAC + DHCP 主机名）
  * t7-tls.pcap：TLS 流雕刻跳过 / JPEG 头判别 / HTML 反误报 / 真 Windows 会话正例
  * t8-b64.pcap：HTML 载荷页内嵌 base64 的 ZIP（saveAs 页）自动解码提取
  * t9-dns.pcap：DNS 真实解析（长查询外带）/ HTML·CSS·文件名反误报
  * t10-ftp.pcap：FTP 会话（非 flag 证据）/ 二进制关键词字节巧合闸门 / 文本关键词正例
  * -q/--brief 精简输出：控制台只留分档块 + 缓存落盘（1/2/3.txt + <名>_cache.txt）/
    目录模式下逐文件只报条数、路径统一在运行级块出现一次
  * 目录模式
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = ''   # main() 里置为 <tmp>/data：测试用的数据目录（夹具住在 tmp 根，与它分开）
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import gen_fixtures  # noqa: E402
from ctfsweep import __version__  # noqa: E402
from ctfsweep.core import judge  # noqa: E402

FAILS = []

# 已从运行时移除的子命令（自学习闭环：留存 → 标注 → 训练 → 模型回写）。
# 训练能力保留，但只存在于仓库 lab/ 的离线脚本里——装机与敲命令都看不到它们。
_REMOVED_SUBCOMMANDS = ('train', 'label', 'auto-label', 'mark', 'learning', 'gen-data')


def check(cond, msg):
    print('  [%s] %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        FAILS.append(msg)


def run_cli(args):
    # stdin 显式接 /dev/null：破坏性命令（uninstall / clear）靠 isatty() 判"有没有人在旁边"，
    # 而交互式终端里跑测试时 stdin 正是 tty —— 不接就会停在确认提示上等输入。
    proc = subprocess.run(
        [sys.executable, '-B', '-m', 'ctfsweep'] + list(args),
        cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.decode('utf-8', 'replace')


def clear_cache(name=''):
    """清缓存——测试里复现用户 workflow：同一目标重扫前先 `clear`。

    运行时契约是"同一目标已有缓存就不覆盖、提示先 clear"（见 cli.cache_occupied），
    所以任何"要看一次全新落盘"的断言都得先清。
    """
    return run_cli(['clear'] + ([name] if name else []) + ['-y'])


def check_windows_payload():
    """Windows 载荷：不该装 POSIX 专有的东西（对齐 ptool 的干净布局）。

    ptool 在 Windows 上只装 bin\\ptool.bat · module\\install.bat · config\\ptool.conf
    · VERSION —— 一个多余的 .sh 都没有。照搬 POSIX 载荷表会把 deploy.sh /
    shell-setup.sh / uninstall / ctfsweep.sh / bash+zsh 补全一起丢进用户目录，
    而它们在那台机器上一个都用不上。
    """
    from ctfsweep.core import selfmgr

    win_dsts = [dst for _src, dst in selfmgr._PAYLOAD_WIN]
    joined = ' '.join(win_dsts)

    check(not any(d.endswith('.sh') for d in win_dsts),
          'Windows 载荷里没有 .sh（%s）' % win_dsts)
    check('completions' not in joined, 'Windows 载荷里没有 completions')
    check('uninstall' not in win_dsts, 'Windows 载荷里没有 uninstall 脚本')
    check('deploy.sh' not in win_dsts and 'shell-setup.sh' not in win_dsts,
          'Windows 载荷里没有 deploy.sh / shell-setup.sh')
    check('lib/ctfsweep' in win_dsts, 'Windows 载荷含 Python 包')
    check('lib/models' in win_dsts,
          'Windows 载荷含判断核模型（缺了 --judge 会静默退化成「未训练」）')
    check('VERSION' in win_dsts and 'config/ctfsweep.conf' in win_dsts,
          'Windows 载荷含 VERSION 与配置文件')

    # ⚠️ 功能项清单与载荷清单是**两件事**，断言必须分开：
    #   载荷 = 要装什么（不许有 POSIX 项）
    #   功能项 = 部署前先删、卸载时删什么——这里**应该**含历史遗留的 POSIX 名字，
    #            否则老用户升级上来时那几样会一直留在盘上（实测过）。
    for legacy in ('completions', 'uninstall', 'deploy.sh', 'shell-setup.sh'):
        check(legacy in selfmgr._WIN_FUNC_ITEMS,
              'Windows 功能项清单含历史遗留 %s（升级时顺手清掉）' % legacy)
    for need in ('bin', 'lib', 'config', 'VERSION'):
        check(need in selfmgr._WIN_FUNC_ITEMS,
              'Windows 功能项清单含 %s' % need)
    # ★ 最要紧的一条：功能项里**绝不能**出现用户数据——那是"永不自动删除"的东西。
    for data in ('cache', 'whitelist.json', 'backups', 'scans'):
        check(data not in selfmgr._WIN_FUNC_ITEMS,
              'Windows 功能项清单**不含**用户数据 %s' % data)

    # POSIX 载荷**不能**被削——那边这些文件都是必需的
    posix = [dst for _src, dst in selfmgr._PAYLOAD_REPO]
    for need in ('deploy.sh', 'shell-setup.sh', 'uninstall',
                 'completions/ctfsweep.zsh', 'lib/ctfsweep.sh'):
        check(need in posix, 'POSIX 载荷仍含 %s' % need)

    # 探测"装残了"的清单要分平台
    saved = os.name
    try:
        os.name = 'nt'
        check(selfmgr._installed_items() == selfmgr._INSTALLED_ITEMS_WIN,
              'os.name=nt 时用 Windows 的组件清单')
        os.name = 'posix'
        check(selfmgr._installed_items() == selfmgr._INSTALLED_ITEMS,
              'POSIX 时用 POSIX 的组件清单')
    finally:
        os.name = saved


def check_eof_is_noninteractive():
    """确认环节读到 EOF 也要按「非交互」报出来。

    Windows 上 stdin 接 NUL 设备时 isatty() 返回 **True**（NUL 是字符设备，实测
    cmd 的 `< NUL` 与 subprocess.DEVNULL 都如此），于是非交互那道闸拦不住，会走到
    input() 并立刻 EOF。若那时只是静默 ans=''，用户看到的是「已取消」退出码 0——
    既没提示该加 -y，脚本也分不清"用户拒绝"和"非交互取消"。
    """
    import io as _io
    from ctfsweep.core import selfmgr as _sm

    class _FakeTTY(object):
        """isatty 说"是终端"，但一读就 EOF —— 正是 Windows NUL 的行为。"""
        def isatty(self):
            return True

        def readline(self, *a):
            raise EOFError()

        def read(self, *a):
            return ''

    # 直接验"EOF 会走非交互提示"这一条：把 isatty 换成 True、stdin 换成假终端，
    # 调 _win_uninstall 会先去摸注册表——所以这里只验那个分支的判断逻辑，
    # 用一段与源码同形的代码不合适。改为**静态断言**源码里没有"静默吞掉 EOF"。
    import inspect
    src = inspect.getsource(_sm._win_uninstall)
    check('except EOFError:' in src, '_win_uninstall 处理了 EOFError')
    # 关键：except 分支里必须打印非交互提示并 return 1，而不是 ans = ''
    i = src.index('except EOFError:')
    # 窗口要放得下那段解释性注释——按 500 字符截会把 print/return 切在注释里，
    # 断言于是失败得莫名其妙（注释越长越容易踩）。
    seg = src[i:i + 1200]
    check('非交互环境' in seg,
          '_win_uninstall 的 EOF 分支打印「非交互环境」（不再静默当成取消）')
    check('return 1' in seg, '_win_uninstall 的 EOF 分支返回 1')
    check("ans = ''" not in seg.split('return 1')[-1][:120] or '非交互环境' in seg,
          '_win_uninstall 的 EOF 分支不再把 ans 置空后走「已取消」')

    csrc = inspect.getsource(_sm.cmd_clear)
    j = csrc.index('except EOFError:')
    cseg = csrc[j:j + 1200]
    check('非交互环境' in cseg, 'cmd_clear 的 EOF 分支打印「非交互环境」')
    check('return 1' in cseg, 'cmd_clear 的 EOF 分支返回 1')

    # _win_uninstall 结尾要收掉空目录（与 POSIX 侧 uninstall.sh 一致）
    check('os.rmdir(dest)' in src,
          '_win_uninstall 收掉空的安装目录（与 POSIX 侧一致）')


def check_windows_path_helpers():
    """Windows PATH 串的增删（纯函数，跨平台可测）。

    Windows 上装/卸的唯一"接线"就是 HKCU\Environment 里的 Path——写坏它是**全机器**级
    的事故（PATH 没了，用户的 cmd 连 ls 都敲不出来）。所以这段逻辑单独拎出来测：
    大小写不敏感、容忍尾部反斜杠、空段清理、以及**不碰无关条目**（真实 PATH 里就有
    `"%JAVA_HOME%\bin;%JAVA_HOME%\jre\bin;"` 这种带引号含分号的老条目）。
    """
    from ctfsweep.core import selfmgr
    entry = r'C:\Users\x\.devtools\ctfsweep\bin'
    other = r'C:\Windows;C:\Program Files\Git\cmd'

    got, changed = selfmgr.win_path_join('', entry)
    check(got == entry and changed, 'win PATH：空 PATH 直接写入该项')

    got, changed = selfmgr.win_path_join(other, entry)
    check(got.split(';')[0] == entry and other.split(';')[0] in got and changed,
          'win PATH：新项插到最前（其余条目保留）')

    for cur in (other + ';' + entry,
                other + ';' + entry.upper(),
                other + ';' + entry + '\\'):
        got, changed = selfmgr.win_path_join(cur, entry)
        check(not changed and got == cur,
              'win PATH：已存在（大小写/尾斜杠不同）原样返回、不重复添加')

    weird = r'C:\A;"%JAVA_HOME%\bin;%JAVA_HOME%\jre\bin;";C:\B'
    got, changed = selfmgr.win_path_drop(weird + ';' + entry, entry)
    check(changed and got == weird, 'win PATH：摘除时不动无关条目（含带引号的老条目）')

    got, changed = selfmgr.win_path_drop(other, entry)
    check(not changed and got == other, 'win PATH：本来就没有该项时不变更')

    joined, _ = selfmgr.win_path_join(other, entry)
    got, changed = selfmgr.win_path_drop(joined, entry)
    check(changed and got == other, 'win PATH：加进去再摘掉回到原样')


def check_shell_scripts():
    """体检 shell 脚本：$VAR 后不得紧跟非 ASCII 字符（bash 会把全角字符并入变量名导致解析错误）"""
    pat = re.compile(r'\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7f]')
    bad = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
        for f in sorted(files):
            if not (f.endswith('.sh') or f.endswith('.zsh') or f.endswith('.bash')
                    or f == 'ctfsweep'):
                continue
            p = os.path.join(root, f)
            for i, line in enumerate(open(p, encoding='utf-8', errors='replace'), 1):
                if pat.search(line):
                    bad.append('%s:%d' % (os.path.relpath(p, ROOT), i))
    check(not bad, 'shell 变量名体检（%s）' % (', '.join(bad) if bad else '全部通过'))


def check_completions():
    """补全静态体检（防回退）：

    选项列表经 compadd -l -d 添加：手写显示串、同义短/长选项合并为一行（如 "-f --file"）。
    不得回退为 _describe -t options —— 它一个条目只能给一个匹配词，合并显示做不出来
    （早期同义短/长会各占一行）。候选结构是位置驱动的：选项只在敲 "-" 之后出现，
    第一个参数位只出「子命令 + 文件」——这条静态查不出，由 _check_completion_behavior() 守。
    """
    zsh = open(os.path.join(ROOT, 'completions', 'ctfsweep.zsh'), encoding='utf-8').read()
    code = '\n'.join(l for l in zsh.splitlines() if not l.lstrip().startswith('#'))
    check('compadd -l -d' in code, 'zsh 补全：选项经 compadd -l -d 添加（一屏一行显示串）')
    check('_describe -t options' not in code, 'zsh 补全：未回退为 -t options（合并显示做不出来）')
    check('-f --file' in code and '-k --keywords' in code, 'zsh 补全：配对选项以 "-f --file" 合并显示')
    check('-F --folder' in code and '--folder:' in code, 'zsh 补全：含 -F --folder（指定文件夹）')
    check('-q --brief' in code, 'zsh 补全：含 -q --brief（精简输出）')
    check('--extract' in code and '--min-score' in code, 'zsh 补全：含主要选项')
    check('update:拉取最新源码快照并重装' in code and 'install:显示安装方式' in code,
          'zsh 补全：update/install 新语义文案在场')
    # 反向断言：安装形态已从「源码直跑 / 不装副本」翻转为 devtools 副本 + 真更新，
    # 别再让旧文案漂回来（history: install 曾是「已弃用」，update 曾是「更新指引」）
    check('已弃用' not in code and '更新指引' not in code and '--check' in code,
          'zsh 补全：无「已弃用 / 更新指引」残留，update 认出 --check')
    # 反向断言：自学习/训练入口已从运行时整体移除（改由仓库 lab/ 离线脚本承担），
    # 别再让它们以子命令形式漂回补全候选里
    check('--judge' in code, 'zsh 补全：含 --judge（保留打分）')
    check(not any(s in code for s in _REMOVED_SUBCOMMANDS),
          'zsh 补全：无自学习子命令（%s）' % '/'.join(_REMOVED_SUBCOMMANDS))
    # 安装形态约定（对齐 jtool/ptool 的同名补全文件）：
    #   · compinit 未跑时自己 bootstrap —— 否则 compdef 不存在，补全**静默**不注册；
    #   · 包装函数让 update 后在父 shell 里重载本文件（免手动 source / 重开终端），
    #     内部必须走 `command` 调真命令，否则自我递归。
    check('autoload -Uz compinit' in code and 'compdef _ctfsweep ctfsweep' in code,
          'zsh 补全：compinit 未初始化时自己 bootstrap（否则补全静默不注册）')
    check('command ctfsweep "$@"' in code and 'unfunction ctfsweep' in code,
          'zsh 补全：包装函数 command 调用真命令 + uninstall 后自我清理')
    bash = open(os.path.join(ROOT, 'completions', 'ctfsweep.bash'), encoding='utf-8').read()
    check('--extract' in bash and '--folder' in bash, 'bash 补全：含主要选项')
    check('--brief' in bash, 'bash 补全：含 --brief（精简输出）')
    check('--judge' in bash, 'bash 补全：含 --judge')
    check(not any(s in bash for s in _REMOVED_SUBCOMMANDS),
          'bash 补全：无自学习子命令')
    # 反向断言：兜底分支不得再「选项 + 文件」并列（history: 旧语句让
    # `ctfsweep -q <TAB>` 把全部选项连 --config 一起倒出来——按字母排第一，最扎眼）。
    # 也顺带守住第一个参数位：它现在只出「子命令 + 文件」，不该再出现这条并列。
    check('COMPREPLY=( $(compgen -W "$opts" -- "$cur") $(compgen -f -- "$cur") )' not in bash,
          'bash 补全：无「选项 + 文件」并列（位置驱动：选项只在敲 "-" 后出现）')
    check('command ctfsweep "$@"' in bash and 'unset -f ctfsweep' in bash,
          'bash 补全：包装函数 command 调用真命令 + uninstall 后自我清理')
    _check_completion_behavior()
    _check_completion_wrapper()


# 驱动补全函数、把它要加的候选打出来：覆写补全原语，不需要真实补全上下文。
# 这是唯一能守住「哪个位置出哪些候选」的手段——静态体检看不见候选集合，
# 上面那条 `ctfsweep -q <TAB>` 倒出 --config 的缺陷正是从静态检查缝里漏过去的。
_COMPLETION_STUB_ZSH = r'''compadd() {
  local -a got=()
  while (( $# )); do
    case "$1" in
      --) shift; got=("$@"); break ;;
      -d|-O|-o|-t|-M|-a|-k|-W|-p|-P|-S|-I|-i|-s|-x|-X) shift ;;
      *) shift ;;
    esac
  done
  print -r -- "opts: ${(j: :)got}"
}
_files() { print -r -- "files" }
_describe() { print -r -- "cmds: ${(P)4}" }
source "$1"; shift
words=("$@"); CURRENT=$#words
_ctfsweep
'''

_COMPLETION_STUB_BASH = r'''source "$1"; shift
COMP_WORDS=("$@")
COMP_CWORD=$(( ${#COMP_WORDS[@]} - 1 ))
compgen() {
  local mode="" word=""
  while [ $# -gt 0 ]; do
    case "$1" in
      -W) mode=W; word="$2"; shift 2 ;;
      -f) mode=f; shift ;;
      -d) mode=d; shift ;;
      -o) shift 2 ;;
      --) shift; break ;;
      *) shift ;;
    esac
  done
  case "$mode" in
    W) local w; for w in $word; do echo "$w"; done ;;
    f) echo "files" ;;
    d) echo "dirs" ;;
  esac
}
_ctfsweep
printf 'opts: %s\n' "${COMPREPLY[*]}"
'''


def _completion_candidates(shell, words):
    """在 <shell> 里跑补全函数，返回其候选串（-q 场景应不再出现任何 --选项）。"""
    tmp = tempfile.mkdtemp(prefix='ctfsweep-comp-')
    try:
        stub = os.path.join(tmp, 'stub')
        src = _COMPLETION_STUB_ZSH if shell == 'zsh' else _COMPLETION_STUB_BASH
        open(stub, 'w', encoding='utf-8').write(src)
        comp = os.path.join(ROOT, 'completions',
                            'ctfsweep.zsh' if shell == 'zsh' else 'ctfsweep.bash')
        # -f：跳过用户的 rc 文件（补全候选不该依赖本机 shell 配置）
        proc = subprocess.run([shell, '-f', stub, comp] + list(words),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return proc.stdout.decode('utf-8', 'replace')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _check_completion_behavior():
    """补全行为体检：位置驱动——选项只在当前词以「-」开头时出现。

    第一个参数位只出「子命令 + 文件」（对齐 jtool/ptool，不铺选项墙）；缺失这道
    闸门时 `ctfsweep -q <TAB>` 仍会把除 --brief 外的全部选项（含 --config）铺出来。
    zsh 缺失的机器（如纯 bash 的 CI 镜像）跳过，不因此判失败。
    """
    for shell in ('bash', 'zsh'):
        if not shutil.which(shell):
            check(True, '%s 补全：本机无该 shell，跳过行为体检' % shell)
            continue
        first = _completion_candidates(shell, ['ctfsweep', ''])
        check('--config' not in first and '-f' not in first,
              '%s 补全：第一个参数位不列选项（选项留给敲 "-"）' % shell)
        check('update' in first, '%s 补全：第一个参数位列出子命令' % shell)
        check('files' in first, '%s 补全：第一个参数位补文件（第一个参数常常就是抓包）' % shell)

        dash = _completion_candidates(shell, ['ctfsweep', '-'])
        check('--config' in dash, '%s 补全：裸 "-" 后列出选项' % shell)

        after_q = _completion_candidates(shell, ['ctfsweep', '-q', ''])
        check('--config' not in after_q and '-f' not in after_q,
              '%s 补全：-q 之后不再铺选项（历史缺陷：--config 排第一）' % shell)
        check('files' in after_q, '%s 补全：-q 之后补文件' % shell)

        after_q_dash = _completion_candidates(shell, ['ctfsweep', '-q', '-'])
        check('--config' in after_q_dash, '%s 补全：-q 之后敲 "-" 仍可补选项' % shell)

        after_file = _completion_candidates(shell, ['ctfsweep', 'a.pcap', ''])
        check('--config' not in after_file and 'files' in after_file,
              '%s 补全：文件参数之后只补文件' % shell)


def _check_completion_wrapper():
    """包装函数体检：update 后自动重载补全文件（对齐 jtool/ptool）。

    补全是 source 进父 shell 的，而 update 是就地替换安装目录里的那一份——
    shell 认的是内存里的旧定义，只有 shell 函数能在父 shell 里重载它。
    做法：假 ctfsweep 命令（证明实参真的透传）+ 调用前改写补全文件
    （重载即会执行到新追加的那行），两头都对上才算过。
    """
    if not shutil.which('zsh'):
        check(True, 'zsh 补全：本机无 zsh，跳过包装函数体检')
        return
    tmp = tempfile.mkdtemp(prefix='ctfsweep-wrap-')
    try:
        bindir = os.path.join(tmp, 'bin')
        os.makedirs(bindir)
        fake = os.path.join(bindir, 'ctfsweep')
        with open(fake, 'w', encoding='utf-8') as fh:
            fh.write('#!/bin/sh\nprintf "FAKE %s\\n" "$*"\n')
        os.chmod(fake, 0o755)
        comp = os.path.join(tmp, 'ctfsweep.zsh')
        shutil.copy(os.path.join(ROOT, 'completions', 'ctfsweep.zsh'), comp)
        script = ('PATH=%s:$PATH; source %s; '
                  'printf "\\nprint -r -- RELOADED-OK\\n" >> %s; ctfsweep update'
                  % (bindir, comp, comp))
        proc = subprocess.run(['zsh', '-f', '-c', script],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        text = proc.stdout.decode('utf-8', 'replace')
        check('FAKE update' in text, 'zsh 补全：包装函数把实参透传给真命令')
        check('RELOADED-OK' in text, 'zsh 补全：update 后自动重载（免手动 source / 重开终端）')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _judge_samples():
    """微型数据集：正=真片段语境（空格/正常词），负=dll 后缀拼贴（二进制噪音）"""
    return [
        {'kind': '片段(前)', 'score': 0.6, 'val': '{krjl424', 'file_type': 'raw',
         'data': b'"cmd.exe /c echo {krjl424" /f', 'label': 1, 'group': 'g1', 'file': 'g1'},
        {'kind': '片段(前)', 'score': 0.6, 'val': '{wtq998', 'file_type': 'raw',
         'data': b'echo {wtq998 more', 'label': 1, 'group': 'g1', 'file': 'g1'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'zlmqu458xktq}', 'file_type': 'raw',
         'data': b'Service Key: zlmqu458xktq}\r\n', 'label': 1, 'group': 'g1', 'file': 'g1'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'q3dalb773}', 'file_type': 'raw',
         'data': b'echo q3dalb773} here', 'label': 1, 'group': 'g1', 'file': 'g1'},
        {'kind': '片段(前)', 'score': 0.6, 'val': '{yq5511', 'file_type': 'raw',
         'data': b'add user {yq5511 now', 'label': 1, 'group': 'g1', 'file': 'g1'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'dll55e3}', 'file_type': 'raw',
         'data': b'C:\\Windows\\system32\\setupetw.dll55e3}JK', 'label': 0, 'group': 'g2', 'file': 'g2'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'dllb39e}', 'file_type': 'raw',
         'data': b'C:\\Windows\\system32\\setupetw.dllb39e}XK', 'label': 0, 'group': 'g2', 'file': 'g2'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'exe6ce1}', 'file_type': 'raw',
         'data': b'C:\\Windows\\system32\\OpenWith.exe6ce1}\xa6', 'label': 0, 'group': 'g2', 'file': 'g2'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'dll984b}', 'file_type': 'raw',
         'data': b'C:\\Windows\\System32\\RstrtMgr.dll984b}\x0e', 'label': 0, 'group': 'g2', 'file': 'g2'},
        {'kind': '片段(尾)', 'score': 0.55, 'val': 'dllff1c}', 'file_type': 'raw',
         'data': b'C:\\Windows\\system32\\shwebsvc.dllff1c}\xf4', 'label': 0, 'group': 'g2', 'file': 'g2'},
    ]


def _rows_to_xy(rows):
    """样本行 → (X, y)：特征维度与当前 FEATURES 不符的行跳过（与 lab/train.py 同口径）。"""
    X, y = [], []
    for r in rows:
        feats = r.get('feats')
        if not feats or len(feats) != len(judge.FEATURES):
            continue
        X.append([float(v) for v in feats])
        y.append(1.0 if float(r.get('label') or 0) >= 0.5 else 0.0)
    return X, y


def check_judge(tmp):
    """判断核：机制训练、离线训练脚本、--judge 打分、无模型兜底。

    运行时只做推理打分，**没有任何训练/标注入口**（模型随版本发布）；
    训练能力整体下沉到仓库 `lab/train.py`——本函数既验打分链路，
    也验离线脚本仍然可用（用户「保留自己训练模型」的诉求）。
    """
    samples = _judge_samples()
    rows = []
    for s in samples:
        rows.append({'v': 1, 'group': s['group'], 'file': s['file'], 'kind': s['kind'],
                     'score': s['score'], 'val': judge.normalize_val(s['val']),
                     'label': s['label'], 'note': 'smoke',
                     'feats': judge.extract_features(s)})

    # 1) 机制：微型训练能分离正负
    net = judge.JudgeNet(seed=1)
    X, y = _rows_to_xy(rows)
    check(len(X) == len(rows) and X and len(X[0]) == len(judge.FEATURES),
          '样本特征维度与 FEATURES 一致（%d 维）' % len(judge.FEATURES))
    net.train(X, y)
    p_pos = net.predict(judge.extract_features(samples[0]))
    p_neg = net.predict(judge.extract_features(samples[5]))
    check(p_pos > 0.5 > p_neg, '微型训练：正负分离（p 正 %.2f > 0.5 > 负 %.2f）' % (p_pos, p_neg))

    # 2) 离线训练脚本（lab/train.py）：留一组评估 + 保存模型。
    #    注意这**不是** CLI 子命令——跑的是仓库脚本，不是 `ctfsweep train`。
    ds = os.path.join(tmp, 'judge_ds.jsonl')
    mdl = os.path.join(tmp, 'judge_model.ctfj')
    with open(ds, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    proc = subprocess.run(
        [sys.executable, '-B', os.path.join(ROOT, 'lab', 'train.py'),
         '--data', ds, '--out', mdl, '--epochs', '150'],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    tout = proc.stdout.decode('utf-8', 'replace')
    check(proc.returncode == 0 and os.path.isfile(mdl), 'lab/train.py：离线训练并保存模型')
    check('留一组评估' in tout and 'AUC' in tout, 'lab/train.py 输出留一组评估信息')

    # 3) 命令行不再暴露训练/标注入口（离线脚本不进安装载荷，也不进子命令表）
    for sub in _REMOVED_SUBCOMMANDS:
        rc, out = run_cli([sub])
        check(rc != 0, '子命令已移除：%s（当普通路径处理并报错）' % sub)

    # 4) --judge：扫描输出 p 分与重点候选
    os.environ['CTFSWEEP_JUDGE_MODEL'] = mdl
    try:
        rc, out = run_cli([os.path.join(tmp, 't3.evtx'), '--judge'])
    finally:
        os.environ.pop('CTFSWEEP_JUDGE_MODEL', None)
    check(rc == 0 and '已加载模型' in out, '--judge：显示模型加载信息')
    check('p=' in out, '--judge：扫描结果带 p 分')
    check('【判断核·重点候选】' in out, '--judge：重点候选区块')

    # 5) 无模型兜底：提示但扫描照常
    os.environ['CTFSWEEP_JUDGE_MODEL'] = os.path.join(tmp, 'no_such_model.ctfj')
    try:
        rc, out = run_cli([os.path.join(tmp, 't2.pcapng'), '--judge'])
    finally:
        os.environ.pop('CTFSWEEP_JUDGE_MODEL', None)
    check('未找到模型' in out and 'flag{pcapng-smoke-ok}' in out,
          '--judge 无模型：提示并正常扫描')


def check_scan_cache(tmp):
    """每次扫描都尝试落缓存，两种模式产出的缓存逐字节相同。

    历史问题：默认模式（不加 -q）**完全不写任何结果文件**，跑完扫描用户拿不到
    可回看的报告，只得到一个自学习留存区（留存区已随自学习机制整体移除）。
    现在数据根下只有 `cache/`：<运行名>-<路径哈希>/1.txt|2.txt|3.txt + <运行名>_cache.txt。
    单文件时「一次运行 = 一个文件」，与旧的"每文件一份"逐字节相同。

    ⚠️ 一次运行一份、**已有则不覆盖**（改了历史行为：从前是静默覆盖）。所以这里
    比"两种模式内容相同"之前先 clear —— 两次都必须是**全新落盘**才谈得上相同。
    """
    fp = os.path.join(tmp, 't1.pcap')
    clear_cache()   # 前面几节已经扫过它，缓存目录里有上一轮的文件
    rc, out = run_cli([fp])
    check('【扫描缓存】' in out, '默认模式：控制台报出本次扫描的缓存路径')

    croot = os.path.join(DATA, 'cache')
    cdirs = [d for d in (os.listdir(croot) if os.path.isdir(croot) else [])
             if d.startswith('t1-')]
    check(len(cdirs) == 1, '默认模式：缓存目录按「文件名-路径哈希」建立')
    cdir = os.path.join(croot, cdirs[0]) if cdirs else os.path.join(croot, '不存在')
    check(all(os.path.isfile(os.path.join(cdir, n)) for n in ('1.txt', '2.txt', '3.txt')),
          '默认模式：1/2/3.txt 分档明细已落盘')
    fc = os.path.join(cdir, 't1_cache.txt')
    check(os.path.isfile(fc), '默认模式：完整报告缓存已落盘')
    if not os.path.isfile(fc):
        return
    with open(fc, encoding='utf-8') as fh:
        default_body = fh.read()
    check('flag{plain-smoke-ok}' in default_body and '【扫描统计】' in default_body,
          '默认模式：缓存内容为该文件完整报告')

    # 缓存内容与模式无关：-q 只改变控制台是否上屏，缓存文件应逐字节相同。
    clear_cache()   # 不覆盖契约：不清就不写第二份，也就比不出"两种模式相同"
    rc, out = run_cli([fp, '-q'])
    with open(fc, encoding='utf-8') as fh:
        brief_body = fh.read()
    check(default_body == brief_body, '缓存内容与模式无关（默认模式 ≡ -q）')

    check(not os.path.exists(os.path.join(tmp, 'judge')),
          '数据根下无 judge/ 残留（自学习留存区已移除）')

    # —— 已有缓存不覆盖：同一目标第二次扫描只提示 clear，盘上那两份一字不改 ——
    before = {}
    for n in ('1.txt', '2.txt', '3.txt', 't1_cache.txt'):
        p = os.path.join(cdir, n)
        with open(p, 'rb') as fh:
            before[n] = fh.read()
    rc, out = run_cli([fp])
    check(rc == 0 and '目录有文件' in out and 'ctfsweep clear' in out,
          '重扫同一目标：提示缓存目录有文件、请用 clear（不再静默覆盖）')
    check('【扫描缓存】' not in out, '重扫同一目标：不再打"已写入"块')
    same = all(open(os.path.join(cdir, n), 'rb').read() == before[n]
               for n in before)
    check(same, '重扫同一目标：盘上旧缓存逐字节未动')
    check('flag{plain-smoke-ok}' in out, '重扫同一目标：报告照常上屏（只是不再落盘）')

    # clear 该项目 → 再扫又能落盘（用户 workflow：clear 完重扫）
    rc, out = clear_cache('t1.pcap')
    check(rc == 0 and not os.path.exists(cdir), 'clear <名称>：该项目缓存目录已删除')
    rc, out = run_cli([fp])
    check('【扫描缓存】' in out and os.path.isfile(fc),
          'clear 后重扫：缓存重新落盘')


def check_clear(tmp):
    """clear 子命令：清空数据目录内容（缓存 + 图片缓存），保留 ctfsweep.conf。

    数据目录在安装形态下就是扫描产物的家（cache/ 结果缓存 + 按题名分的图片缓存），
    此前「只增不减」的清理方式只有用户手动 rm —— clear 是它的官方入口。
    三条硬契约在这里守住：
      · 清的是**内容**（目录本身保留），不是 rmtree(数据根)——用户级安装下数据目录
        就是安装根，整删会把 ctfsweep 自己删掉；
      · ctfsweep.conf 是配置不是缓存，**必须保留**；
      · 非交互（无 tty）不带 -y 时拒绝执行——破坏性操作不能在管道里悄悄发生。
    """
    root = DATA  # main() 已把 CTFSWEEP_DATA_DIR 指到 DATA（tmp 下的子目录）
    conf = os.path.join(root, 'ctfsweep.conf')
    with open(conf, 'w', encoding='utf-8') as fh:
        fh.write('MIN_SCORE=0.5\n')
    cache_dir = os.path.join(root, 'cache', 't1-abc123')
    img_dir = os.path.join(root, 'some题')
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)
    for p in (os.path.join(cache_dir, '1.txt'), os.path.join(img_dir, 'a.png'),
              os.path.join(root, '杂项.txt')):
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write('x')
    # 用户级安装的形态：数据根 == 安装根，功能项就在这里——clear 一个都不能碰
    func = []
    for rel in ('VERSION', os.path.join('lib', 'ctfsweep', '__init__.py'),
                os.path.join('bin', 'ctfsweep'), os.path.join('config', 'ctfsweep.conf'),
                'uninstall', 'deploy.sh', 'shell-setup.sh'):
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write('functional\n')
        func.append(p)

    # 1) 无 -y 且非交互：必须拒绝（破坏性操作的闸门）
    rc, out = run_cli(['clear'])
    check(rc == 1 and '-y' in out and '已删除' not in out,
          'clear：非交互且无 -y 时拒绝执行')
    check(os.path.isdir(cache_dir) and os.path.isfile(conf),
          'clear：拒绝时什么都不删')

    # 2) -y：清掉缓存与图片目录，保留 conf 与数据目录本身
    rc, out = run_cli(['clear', '-y'])
    check(rc == 0 and '已清空' in out, 'clear -y：正常完成')
    check(not os.path.exists(os.path.join(root, 'cache')),
          'clear -y：cache/ 已删除')
    check(not os.path.exists(img_dir) and not os.path.exists(os.path.join(root, '杂项.txt')),
          'clear -y：图片缓存目录与散落文件一并删除')
    check(os.path.isfile(conf), 'clear -y：ctfsweep.conf（配置）保留')
    check(os.path.isdir(root), 'clear -y：数据目录本身保留（不 rmtree 根）')
    # 用户级安装下数据根就是安装根：功能项若被误删，ctfsweep 自己就没了
    missing = [p for p in func if not os.path.exists(p)]
    check(not missing,
          'clear -y：功能项（bin/lib/VERSION/uninstall …）全部保留%s'
          % ('' if not missing else '，缺: %s' % '、'.join(os.path.relpath(p, root) for p in missing)))

    # 3) 空目录再 clear：幂等、报"已是空的"
    rc, out = run_cli(['clear', '-y'])
    check(rc == 0 and ('已是空' in out or '已清空' in out), 'clear -y：重复执行不报错')

    # 4) 只清一个项目：`clear <名称>` 删该项目的图片目录 + `cache/<运行名>-<哈希>/`，
    #    别的项目与功能项一个不动（用户 workflow：某个题重扫前先清它自己）
    other_top = os.path.join(root, '另一题')
    os.makedirs(os.path.join(root, 'capture4.pcapng'), exist_ok=True)
    os.makedirs(other_top, exist_ok=True)
    for d in ('capture4-aaaaaa', 'capture4-bbbbbb', '另一题-cccccc'):
        os.makedirs(os.path.join(root, 'cache', d), exist_ok=True)
        with open(os.path.join(root, 'cache', d, '1.txt'), 'w', encoding='utf-8') as fh:
            fh.write('x')
    rc, out = run_cli(['clear', 'capture4.pcapng', '-y'])
    check(rc == 0 and 'capture4.pcapng' in out and '已清空' in out,
          'clear <名称>：按项目名清理并报出删了什么')
    check(not os.path.exists(os.path.join(root, 'capture4.pcapng'))
          and not os.path.exists(os.path.join(root, 'cache', 'capture4-aaaaaa'))
          and not os.path.exists(os.path.join(root, 'cache', 'capture4-bbbbbb')),
          'clear <名称>：该项目的图片目录与全部同名运行缓存都删掉')
    check(os.path.isdir(other_top) and os.path.isdir(os.path.join(root, 'cache', '另一题-cccccc')),
          'clear <名称>：别的项目原封不动')
    check(os.path.isfile(conf), 'clear <名称>：配置保留')

    # 5) 名称撞上功能项/不存在的项目：拒绝 / 如实报"未找到"
    rc, out = run_cli(['clear', 'VERSION', '-y'])
    check(rc == 1 and '拒绝清理' in out, 'clear <功能项名>：拒绝（不给误删程序本体）')
    rc, out = run_cli(['clear', '不存在的题', '-y'])
    check(rc == 0 and '未找到' in out, 'clear <不存在的项目>：如实报未找到')

    # 6) 未知参数 / 参数过多
    rc, out = run_cli(['clear', '--bogus'])
    check(rc == 2 and '未知参数' in out, 'clear：未知参数返回 2')
    rc, out = run_cli(['clear', 'a', 'b'])
    check(rc == 2 and '参数过多' in out, 'clear：参数过多返回 2')


def check_dir_scan_cache(tmp):
    """目录扫描：**一次运行一个缓存目录**，归属靠每行的「← 相对路径」。

    历史问题：缓存粒度按「文件」划分（旧 `brief_cache_dir()` 的注释写着"同名不同目录
    不互相覆盖"），而那个理由只在目录扫描下成立、`-f` 单文件时"一次运行 = 一个文件"
    两种粒度重合，所以一直没暴露——直到 `-F 项目/` 扫整个项目：缓存摊成十几个
    `<文件名>-<哈希>` 平铺目录，控制台连打十几行，`sub1/a.pcap` 与 `sub2/a.pcap`
    的目录名肉眼还分不出对应关系（只有文件名相同、哈希不同）。
    本节目录扫描回归就是那次漏网的直接补丁。
    """
    croot = os.path.join(DATA, 'cache')
    proj = os.path.join(tmp, 'projdir')
    os.makedirs(os.path.join(proj, 'sub1'), exist_ok=True)
    os.makedirs(os.path.join(proj, 'sub2'), exist_ok=True)
    os.makedirs(os.path.join(proj, 'empty'), exist_ok=True)
    with open(os.path.join(tmp, 't1.pcap'), 'rb') as src:
        blob = src.read()
    with open(os.path.join(proj, 'sub1', 'one.pcap'), 'wb') as dst:
        dst.write(blob)
    with open(os.path.join(tmp, 't2.pcapng'), 'rb') as src:
        pcapng = src.read()
    with open(os.path.join(proj, 'sub2', 'two.pcapng'), 'wb') as dst:
        dst.write(pcapng)

    rc, out = run_cli([proj])
    check(rc == 0 and '【扫描缓存】' in out, '目录扫描：默认模式报出缓存位置')

    dirs = [d for d in os.listdir(croot) if d.startswith('projdir-')]
    check(len(dirs) == 1,
          '目录扫描：整次运行只建**一个**缓存目录（旧布局下这里会是 0 个）')
    if len(dirs) != 1:
        return
    cdir = os.path.join(croot, dirs[0])

    # 控制台只列这一个目录：旧布局打印的是 one-<h>/two-<h>/，这一行一次都不会出现
    check(out.count(cdir + os.sep) == 1, '目录扫描：控制台只报出这一个运行目录')

    check(all(os.path.isfile(os.path.join(cdir, n)) for n in ('1.txt', '2.txt', '3.txt')),
          '目录扫描：1/2/3.txt 聚合落盘')
    fc = os.path.join(cdir, 'projdir_cache.txt')
    check(os.path.isfile(fc), '目录扫描：完整报告按运行名命名（projdir_cache.txt）')

    f1 = os.path.join(cdir, '1.txt')
    t1t = open(f1, encoding='utf-8').read() if os.path.isfile(f1) else ''
    check('← sub1/one.pcap' in t1t and '← sub2/two.pcap' in t1t,
          '聚合 1.txt：每条明细标出来源相对路径（Finding 自己不带来源文件）')
    # 归属必须**逐行对应**：整块共用一个文件名也能让上面那条通过，那样等于没有归属
    line_a = [l for l in t1t.splitlines() if 'flag{plain-smoke-ok}' in l]
    line_b = [l for l in t1t.splitlines() if 'flag{pcapng-smoke-ok}' in l]
    check(bool(line_a) and 'sub1/one.pcap' in line_a[0] and 'sub2/' not in line_a[0],
          '归属逐行对应：t1 的命中挂在 sub1/one.pcap 上')
    check(bool(line_b) and 'sub2/two.pcap' in line_b[0],
          '归属逐行对应：t2 的命中挂在 sub2/two.pcap 上')
    check(t1t.count('条数:') == 1, '聚合 1.txt：单文件头 + 全量明细（不是每文件一段）')

    if os.path.isfile(fc):
        body = open(fc, encoding='utf-8').read()
        check('flag{plain-smoke-ok}' in body and 'flag{pcapng-smoke-ok}' in body
              and '【扫描统计】' in body and '本次运行汇总' in body,
              '完整报告：两个文件都在，且带运行汇总尾段（files_total > 1）')

    # -q 目录模式：逐文件只报条数（路径不再逐文件重复），路径统一在运行级块出现一次
    clear_cache()   # 上面那次默认扫描已写下同一份缓存，先清掉
    rc, qout = run_cli([proj, '-q'])
    check('[文件] sub1/one.pcap' in qout and '[文件] sub2/two.pcap' in qout,
          '-q 目录模式：逐文件标注相对路径（只报文件名就分不出是哪一个）')
    check('，具体信息：' not in qout, '-q 目录模式：不再逐文件重复四条缓存路径')
    check(qout.count('【扫描缓存】') == 1 and qout.count(cdir + os.sep) == 1,
          '-q 目录模式：运行级缓存块恰好打一次')

    # 空目录：不建空壳缓存目录（旧行为，防"扫了空目录就多一个空目录"回归）
    before = sorted(os.listdir(croot))
    run_cli([os.path.join(proj, 'empty')])
    check(sorted(os.listdir(croot)) == before, '空目录：不产生空缓存目录')


def check_report_equivalence():
    """CLI 边界的等价性：`report([f.to_tuple() for f in findings])` ≡ `report(原始元组)`。

    即 `Finding.from_tuple()`/`to_tuple()` 往返不丢分、不解码。覆盖 report() 的
    每一个 kind 分支，外加：非 UTF-8 的 bytes token、字符串型 val、pfunc 路径。
    """
    import io
    from contextlib import redirect_stdout
    from ctfsweep.core.report import report
    from ctfsweep.core.router import Finding

    cases = [
        (0.97, '明文flag', b'flag{x}', b'flag{x}', 'loc01'),
        (0.95, 'hex', b'666c6167', b'flag{h}', 'loc02'),
        (0.93, 'base64', b'ZmxhZw==', b'flag{b}', 'loc03'),
        (0.91, 'USB键盘输入', b'usb', b'abc', 'loc04'),
        (0.88, 'DNS查询', b'dns', b'evil.com', 'loc05'),
        (0.86, 'JWT', b'jwt', b'eyJhbGci', 'loc06'),
        (0.84, 'Kerberos票据', b'krb', b'ticket', 'loc07'),
        (0.82, 'NetNTLM', b'ntlm', b'resp', 'loc08'),
        (0.80, 'LDAP口令', b'ldap', b'pwd', 'loc09'),
        (0.78, '域账号', b'ad', b'user', 'loc10'),
        (0.76, '命令回显', b'cmd', b'whoami', 'loc11'),
        (0.74, '环境/配置', b'env', b'K=V', 'loc12'),
        (0.72, '短文本响应', b'short', b'ok', 'loc13'),
        (0.70, '片段-abc', b'frag', b'fragval', 'loc14'),
        (0.68, '关键词[flag]', b'kw', b'kwval', 'loc15'),
        # 非 UTF-8 token：report 的 tok 走 latin-1，提前用 utf-8 解会变样
        (0.66, 'hex', b'\xff\xfe\x00\x01', b'raw\xff\xfe', 'loc16'),
        # val 是 str（部分模块产出 str 而非 bytes）
        (0.64, '明文flag', 'flag{str-val}', 'flag{str-val}', 'loc17'),
    ]

    def render(items, **kw):
        buf = io.StringIO()
        with redirect_stdout(buf):
            report(items, 20, 0.0, **kw)
        return buf.getvalue()

    # CLI 边界契约：`report([f.to_tuple() for f in findings])` 必须与被替换的原始元组
    # 渲染逐字节一致——即 from_tuple/to_tuple 往返不丢分、不解码（含 latin-1 token 与
    # str 型 val）。report() 本身只吃 5 元组，不再做 isinstance 分流。
    check(render(cases) == render([Finding.from_tuple(t).to_tuple() for t in cases]),
          'report()：经 Finding 往返的 5 元组渲染逐字节一致（CLI 边界）')
    check(render(cases, pfunc=lambda t: 0.5)
          == render([Finding.from_tuple(t).to_tuple() for t in cases], pfunc=lambda t: 0.5),
          'report()：带 pfunc（判断核打分）时同样一致')

    # to_tuple 必须原样回吐，不得解码
    check(Finding.from_tuple(cases[15]).to_tuple() == cases[15],
          'Finding.to_tuple()：原样回吐 5 元组（bytes 不解码）')

    # to_meta_dict 是 MetaJudge 的输入契约：不 round、evidence 走 evidence_text()
    d = Finding.from_tuple((0.975, '明文flag', b't', b'v', 'l')).to_meta_dict()
    check(d == {'kind': '明文flag', 'confidence': 0.975,
                'evidence': 'v', 'module': 'scanner'},
          'Finding.to_meta_dict()：confidence 不 round、bytes 证据解码成可读串')
    # bytes 证据必须解码：str(b'\\xe6\\x9c\\x8d') 是转义 repr，读不了；utf-8 非法字节
    # 用 replace 兜底（与 report() 对 val 的口径一致），不能抛异常。
    from ctfsweep.core.router import evidence_text
    check(evidence_text('服务票据'.encode('utf-8')) == '服务票据',
          'evidence_text()：UTF-8 字节解码为中文')
    check(evidence_text(b'A\xffB') == 'A�B',
          'evidence_text()：非法字节替换而非抛异常')
    check(evidence_text(b'x' * 400) == 'x' * 300, 'evidence_text()：截断到 300 字符')
    check(evidence_text('纯文本') == '纯文本', 'evidence_text()：str 原样返回')


def check_meta_judge():
    """元判断核评分不变式（纯离线，不依赖夹具）。

    回归目标：`final = confidence * module_weight` 时代，权重表全部 ≤0.95，
    乘法只会降分——config 逐字命中的明文 flag（自评 0.97）会被压到 中 0.87。
    """
    from ctfsweep.core.meta_judge import MetaJudge, MODULE_WEIGHTS
    from ctfsweep.core.utils import level_of

    def scored(module, kind, conf, evidence=''):
        f = {'module': module, 'kind': kind, 'confidence': conf, 'evidence': evidence}
        return MetaJudge([f]).score()[0]

    # (a) 不变式：综合分恒 >= 模块自评（规则与加成只加不减）
    bands = (0.0, 0.2, 0.55, 0.61, 0.85, 0.9, 0.97, 1.0)
    bad = []
    for module in list(MODULE_WEIGHTS) + ['未知模块']:
        for conf in bands:
            got = scored(module, '不变式检查', conf)['score']
            if got < round(conf, 2):
                bad.append('%s@%.2f→%.2f' % (module, conf, got))
    check(not bad, '元判断核：综合分不低于模块自评%s'
          % ('（异常：%s）' % ','.join(bad[:3]) if bad else ''))

    # archives 权重 0.60 低于中性点 0.65，加成须夹到 0（不倒扣）
    got = scored('archives', '不变式检查', 0.60)
    check(got['score'] == 0.60 and got['prior_bonus'] == 0.0,
          '元判断核：低权重模块不加成也不倒扣（archives 0.60→0.60）')

    # (b) 回归：明文 flag 曾因 0.97*0.85 掉到 中 0.87
    got = scored('config', '配置中的 flag', 0.97, '配置: flag{router-test}')['score']
    check(got >= 0.97, '元判断核：config 明文 flag 不再被降级（0.97→%.2f）' % got)

    # (c) MODULE_RULES 只作下限，不得覆盖更高的模块自评
    got = scored('ad', '域账号', 0.99)['score']
    check(got >= 0.99, '元判断核：规则分不覆盖更高自评（ad 域账号 0.99→%.2f）' % got)

    # (d) 分档口径与 utils.level_of 一致（0.86 在旧口径里算"中"）
    mj = MetaJudge([{'module': 'scanner', 'kind': '分级检查',
                     'confidence': 0.86, 'evidence': ''}])
    mj.score()
    summary = mj.get_summary()
    check(summary['high'] == 1 and summary['medium'] == 0 and level_of(0.86) == '高',
          '元判断核：分档口径与 level_of 一致（0.86 计高置信）')

    # (e) 畸形 confidence 不得中断整份报告（cli 里 meta.score() 无 try/except）
    got = scored('config', '畸形检查', None)['score']
    check(isinstance(got, float), '元判断核：畸形 confidence 不炸（None→%.2f）' % got)

    # (f) 前 N 项按 (kind, 证据) 去重：同一份证据在多个会话里重复出现时
    #     （FTP 爆破/邮件群发），全部占满前 N 项会让其余线索一条都看不见。
    mj = MetaJudge(
        [{'module': 'scanner', 'kind': 'FTP成功凭据', 'confidence': 0.85,
          'evidence': 'dj / dj', 'loc': 'FTP a:1→b:21'},
         {'module': 'scanner', 'kind': 'FTP成功凭据', 'confidence': 0.85,
          'evidence': 'dj / dj', 'loc': 'FTP a:2→b:21'},
         {'module': 'scanner', 'kind': 'FTP成功凭据', 'confidence': 0.85,
          'evidence': 'dj / dj', 'loc': 'FTP a:3→b:21'},
         {'module': 'scanner', 'kind': '漏洞利用', 'confidence': 0.80,
          'evidence': 'vsftpd 2.3.4 后门', 'loc': 'FTP a:1→b:21'}])
    mj.score()
    top = mj.get_top_findings(10)
    check([f['kind'] for f in top] == ['FTP成功凭据', '漏洞利用'],
          '元判断核：前 N 项按 (kind, 证据) 去重（重复证据不占满列表）')
    check(mj.get_summary()['total'] == 4,
          '元判断核：去重只作用于"前 N 项"，总数仍如实计数')
    mj2 = MetaJudge([{'module': 'scanner', 'kind': 'K%d' % i, 'confidence': 0.9,
                      'evidence': 'e%d' % i} for i in range(20)])
    mj2.score()
    check(len(mj2.get_top_findings(10)) == 10, '元判断核：不同线索仍取满 N 条')


def check_stream_merge():
    """TCP 重组不得按"序号跨度"无脑分配缓冲区（纯离线，不依赖夹具）。

    回归目标：spambot.pcap 的 7 条"流"各有 3 个包、18 字节载荷，序号却横跨
    3.5 GB（同一客户端端口被多条连接复用，几个 ISN 被按 4 元组聚合）。
    旧实现在每条流上分配 256 MB 零缓冲 → 10 MB 的抓包吃 2.1 GB 内存、跑 250 秒。
    """
    from ctfsweep.core.capture import merge_stream

    # 序号可比：正常重传/乱序合并（跨度 ≈ 载荷量）
    segs = [(1, 0.0, b'hello ', 100), (2, 0.0, b'world', 106)]
    check(merge_stream(segs) == b'hello world', '重组：正常流按 seq 拼接不丢字节')
    # 重传覆盖：后到的段覆盖先到的（last-wins）
    segs = [(1, 0.0, b'AAAA', 100), (2, 0.0, b'BB', 102)]
    check(merge_stream(segs) == b'AABB', '重组：重传 last-wins 覆盖')
    # 序号不可比：span 与载荷量悬殊 → 退回按包序拼接，且**不得**分配巨缓冲
    segs = [(1, 0.0, b'one', 100), (2, 0.0, b'two', 2000000000), (3, 0.0, b'six', 3600000000)]
    got = merge_stream(segs)
    check(got == b'onetwosix', '重组：序号跨度过大时退回按包序拼接（不补零、不爆内存）')
    # 空洞补零仍保留（真实丢包场景：跨度小、确实缺字节）
    segs = [(1, 0.0, b'AB', 100), (2, 0.0, b'CD', 104)]
    check(merge_stream(segs) == b'AB\x00\x00CD', '重组：真实小空洞仍补 0x00（Wireshark 一致）')


def check_readable_window():
    """二进制上下文净化：乱码尾巴必须被截掉，正常文本逐字不动（纯离线）。

    回归目标：`isprintable()` 拦不住"二进制按 UTF-16 解码"出来的乱码——
    Ā(U+0100) Ѐ(U+0400) ఀ(U+0C00) ᄀ(U+1100) ⨀(U+2A00) 全是 printable。
    实测 Security.evtx 有 9 条 `关键词[flag]` 命中，有效线索只在开头约 30 字节，
    其余几十字符是乱码，把 4 个 flag 片段挤出了可视范围。
    """
    from ctfsweep.core.utils import readable_window

    # 真实形态：可读线索 + 乱码尾巴 → 只留线索
    evtx = ('"C:\\Windows\\system32\\cmd.exe" /c echo flag{sol > C:\\Windows\\Temp'
            '\\test.txt.n桧.⨀*㠀.㤀...谀߹.�༁āఀ渁ꭚ☿.ሀ.ĀЀĀЀȀ.Ȁ...')
    got = readable_window(evtx)
    check('flag{sol' in got and '⨀' not in got and 'Ā' not in got,
          '净化：evtx 乱码尾巴被截掉，flag 线索保留')

    # 正常文本逐字不动（含中文/箭头/乘号/填充点——golden 基线断言着这些）
    for s in ('PWD=/AstrBot',
              '客户端自报主机名: neo-7ffc721bcc1 → 3 个服务器 ×2',
              '................cmd.exe /c echo flag{evtx-smoke-ok}........reg add HKLM'):
        check(readable_window(s) == s, '净化：正常文本不被改动（%s）' % s[:18])

    # 全乱码 / 太短的片段 → 返回空（调用方丢弃该命中，而不是印一堆乱码）
    check(readable_window('ĀЀఀᄀ⨀⎬☿' * 4) == '', '净化：纯乱码返回空串（丢弃命中）')
    check(readable_window('ĀЀఀ' + 'abc') == '', '净化：可读片段过短也丢弃')


def check_dedup_and_text_gate():
    """重复结论只留一条 + 加密请求体的乱码字段整条丢弃（纯离线）。

    回归目标（都是"同一条信息刷满屏幕"）：
      * dump.pcapng：50 条 FTP 会话连同一台 vsftpd 2.3.4，
        `漏洞利用：笑脸后门（CVE-2011-2523）` 证据逐字相同却印了 50 行。
      * FLAG 消失之谜.pcap：AES 后的 App 流量按 utf-8 'replace' 解出来，
        `[POST字段摘录]` 7 行里 6 行是 `��)�;��=l?�]` 这种读不了的乱码。
    """
    from ctfsweep.core.blobscan import add
    from ctfsweep.core.utils import looks_like_text

    # 同结论不同 loc → 只留第一条（loc 不进通用去重键）
    findings, seen = [], set()
    for port in (21, 22, 23):
        add((0.95, '漏洞利用', b'', 'vsftpd 2.3.4 笑脸后门', 'FTP x:%d→y:21' % port),
            findings, seen)
    check(len(findings) == 1, '去重：同结论不同位置只留一条')
    check(findings[0][4] == 'FTP x:21→y:21', '去重：保留的是第一条（带它的位置）')

    # 结论不同 → 都必须留下（别把去重做过头）
    add((0.95, '漏洞利用', b'', 'vsftpd 2.3.4 笑脸后门（已触发后门 shell）', 'FTP x:24→y:21'),
        findings, seen)
    check(len(findings) == 2, '去重：结论不同则各自保留')

    # 文本闸门
    check(looks_like_text('email=1@1.com'), '闸门：正常字段值判为文本')
    check(looks_like_text('mock_script=const sandbox = this'), '闸门：代码判为文本')
    check(not looks_like_text('��)�;��=l?�]��b�K'),
          '闸门：替换字符乱码判为二进制')
    check(not looks_like_text('\x00\x01\x02\x03\x04\x05\x06\x07'), '闸门：控制字节判为二进制')
    check(not looks_like_text(''), '闸门：空串不算文本（调用方需自行放行空值）')


def check_archives_content(tmp):
    """解开压缩包后必须报出**里面是什么**（纯离线）。

    回归目标：`SU_Artifact_Online.zip`（密码 password，1 KB）此前只报一句
    「ZIP 解压成功（密码: password）」+ 建议「检查解压出的文件内容」——包内是
    3369 字节的**卢恩字母替换密码**文本，报告一个字都没说。陌生题里"解开了但不说
    里面是什么"等于没解。
    """
    import os
    import zipfile
    from ctfsweep.core.archives import analyze

    zpath = os.path.join(tmp, 'rune.zip')
    runes = ('ᛗᚹᚱᛨᛚᛈᛇᚠᛒᛒᚺᚱᚨᛨᛇᛉᛗᚹᚱᛒᛨᛟᚠᛖᛨᚠᛨᛇᚠᛈᛨᛗᛟᚱᛈᛗᛣᚬᚬᚲᚺᛜᚱᛨᛣᚱᚠᛒᛖᛨᛉᛃᚨᛥᛨᛈᛉᛨᛗᚠᛃᛃᚱᛒ') * 3
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('something mysterious.txt', runes)
    res = analyze(zpath)
    kinds = [f.kind for f in res.findings]
    ev = ' | '.join(f.evidence for f in res.findings)
    check('压缩包内容' in kinds, '压缩包：必须报出成员清单（不再是"解开了什么都不说"）')
    check('something mysterious.txt' in ev, '压缩包：成员名出现在清单里')
    check('卢恩字母' in ev, '压缩包：认出卢恩字母（给出替换密码方向）')
    check(any('ᛗ' in f.evidence for f in res.findings), '压缩包：文本成员给出正文摘录')

    # flag 成员的 flag 必须抽出来（模块 docstring 承诺的"最终文件扫描"）
    fpath = os.path.join(tmp, 'flaggy.zip')
    with zipfile.ZipFile(fpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('a/note.txt', 'nothing here\n')
        zf.writestr('a/b/deep.txt', 'the answer is flag{zip_member_scan_ok}\n')
    res2 = analyze(fpath)
    flags = [f for f in res2.findings if f.kind == '压缩包中的 flag']
    check(flags and 'flag{zip_member_scan_ok}' in flags[0].evidence,
          '压缩包：成员里的 flag 被抽出（含子目录）')
    check(flags[0].confidence == 0.97, '压缩包：成员 flag 置信度 0.97（可直接提交）')

    # 递归解压出来的**容器内部零件**不算成员——否则 12 个列表名额与 6 个摘录名额
    # 会被 `byteorder`（6 B）/`version`（2 B）这类文件吃光（实测 SU_theif 的 .pth）
    npath = os.path.join(tmp, 'nested.zip')
    inner = os.path.join(tmp, 'inner.zip')
    with zipfile.ZipFile(inner, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('model/byteorder', 'little')
        zf.writestr('model/version', '3')
    with zipfile.ZipFile(npath, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(inner, 'model.pth')
        zf.writestr('README.md', '# README\n这是题面说明\n')
    res3 = analyze(npath)
    ev3 = ' | '.join(f.evidence for f in res3.findings)
    check('model/byteorder' not in ev3 and 'model/version' not in ev3,
          '压缩包：容器的内部零件不占成员名额（.pth 解出的 model/ 被折叠）')
    check('README.md' in ev3, '压缩包：折叠内部零件后，真正的题面成员仍列出')

    # bzImage 不能被 MZ 头判成 PE——kernel pwn 题被判成"Windows 可执行文件"会带偏方向
    from ctfsweep.core.archives import _text_of
    bz = b'MZ' + b'\x00' * 0x200 + b'HdrS' + b'\x00' * 32
    check('Linux 内核' in (_text_of(bz)[1] or ''),
          '压缩包：bzImage 认成 Linux 内核镜像，不是 PE (Windows)')
    check(_text_of(b'MZ' + b'\x00' * 64)[1] == 'PE (Windows)',
          '压缩包：真 PE 头仍认成 PE (Windows)')
    check(_text_of('中文文本\n'.encode('utf-8'))[0] == '中文文本\n',
          '压缩包：UTF-8 文本判定为文本')


def check_logs_wmi_gate():
    """WMI/WQL 查询行不得被判成 SQL 注入（纯离线）。

    回归目标：`日志排查` 那道题的 Application.evtx 里，Windows 自己的 WMI 提供程序
    轮询（`Start IWbemServices::ExecQuery - ROOT\\CIMV2 : SELECT * FROM Win32_Account`）
    用类 SQL 语法，被 SQL 注入正则整片命中——**15 条 [高 0.95]**，把【前 10 项发现】
    占掉 8 席，真正要看的 flag 线索被压在下面。
    """
    import re
    from ctfsweep.core.logs import ATTACK_PATTERNS, _is_wmi_query

    sqli = [p for p in ATTACK_PATTERNS if p[3] == 'sql_injection'][0][0]

    # 真实载荷必须照旧命中
    for s in ("1' UNION ALL SELECT username,password FROM users--",
              "'; EXEC xp_cmdshell 'dir' --",
              "EXEC xp_cmdshell('net user')",
              "exec master..xp_cmdshell 'whoami'",
              "EXEC(@sql)",
              "xp_cmdshell 'dir'"):
        check(bool(re.search(sqli, s, re.I)), 'SQLi：真实载荷仍命中（%s）' % s[:28])

    # WMI 轮询行被识别为 WMI 查询（真正生效的是派发前的整行剔除，见下）
    for s in ("Start IWbemServices::ExecQuery - ROOT\\CIMV2 : Select * from Win32_Process Where ProcessID = '4'",
              'Start IWbemServices::ExecQuery - root\\wmi : select * from WDMClassesOfDriver'):
        check(_is_wmi_query(s), 'WMI：识别为 WMI 查询（%s）' % s[:36])

    # 端到端：同一份内容里，WMI 行不出声，真载荷照旧出声
    from ctfsweep.core.logs import _detect_and_analyze
    from ctfsweep.core.router import AnalysisResult

    res = AnalysisResult('logs')
    _detect_and_analyze(
        "Start IWbemServices::ExecQuery - ROOT\\CIMV2 : Select * from Win32_Process Where ProcessID = '4'\n"
        "Start IWbemServices::ExecQuery - root\\wmi : select * from WDMClassesOfDriver\n",
        'wmi.evtx', res)
    check(not res.findings, 'WMI：纯 WMI 轮询日志零告警（实测原报 15 条 [高 0.95]）')

    res2 = AnalysisResult('logs')
    _detect_and_analyze(
        "Start IWbemServices::ExecQuery - ROOT\\CIMV2 : Select * from Win32_Process\n"
        "/search?q=1' UNION ALL SELECT username,password FROM users--\n",
        'mix.log', res2)
    kinds = [f.kind for f in res2.findings]
    check(any('SQL 注入' in k for k in kinds),
          'WMI：同一份内容里的真 SQLi 不受影响（剔除是按行的）')

    # 只是"提到" WMI 类名的普通行不能误杀（否则会漏掉同行的真线索）
    check(not _is_wmi_query('process Win32_Process created: cmd.exe /c whoami'),
          'WMI：仅提到类名不算 WMI 查询行')
    # 光秃秃的 xp_cmdshell（SQL Server 装机后的 perflib 计数器名）不是攻击
    check(not re.search(sqli, 'xp_cmdshell', re.I), 'SQLi：裸 xp_cmdshell 不再命中')
    check(not re.search(sqli, 'System.Web.HttpApplication.IExecutionStep.Execute()', re.I),
          'SQLi：.NET 栈帧的 Execute() 不再命中')


# 手搓 TLS ClientHello 的实现只有一份，放在 gen_fixtures（t13-sni.pcap 也要用）。
_client_hello = gen_fixtures.client_hello


def check_sni_render(tmp):
    """[TLS SNI] 块的渲染：按域名聚合 / 域名不截断 / 已知厂商折叠在末尾。

    回归目标：`2025-01-22-traffic-analysis-exercise.pcap`（全 mta 语料里唯一一道
    问域名的题），答案是 `google-authenticator.burleson-appliance.net` 与
    `authenticatoor.org`。旧版报告里：前者被 `sni[:38]` 印成 `…burleson-applianc`
    ——**看起来像答案、照抄却核验不了**；后者一个字都没有——15 个席位被
    `login.microsoftonline.com` 这类遥测按 (域名, IP) **逐行**占满
    （同一域名 10 个 IP = 10 行），真域名落进"…（其余 108 个省略）"。
    """
    rc, out = run_cli([os.path.join(tmp, 't13-sni.pcap')])
    check(rc == 0, 'SNI 渲染：扫描返回 0')

    # 非基础设施的域名必须原样出现（截断过的域名不再是 IOC，核验不了）
    check('evil-c2.example.net' in out, 'SNI 渲染：普通陌生域名逐条列出')
    long_dom = 'very-long-phishing-domain-name.example.org'
    check(long_dom in out,
          'SNI 渲染：超长域名**不截断**（旧版 sni[:38] 会印成 …name.example.o）')
    check(long_dom[:38] + ' ' not in out.replace(long_dom, ''),
          'SNI 渲染：没有留下被截断的半截域名')

    # 20 个已知厂商名折叠成一行计数，不占逐条席位。
    # 逐条行 = 缩进 4 空格且以域名开头；遇到下一个 `  [块]` / `  （无命中）` 即结束。
    body = out.split('[TLS SNI]', 1)[1].splitlines()[1:]
    rows = []
    for line in body:
        if re.match(r'^    \S', line) and '已知厂商/CDN' not in line:
            rows.append(line)
        elif line.strip():
            break
    check(len(rows) == 2,
          'SNI 渲染：2 个陌生域名各占一行、厂商遥测不占席位（实际 %d 行）' % len(rows))
    check('已知厂商/CDN 20 个' in out, 'SNI 渲染：已知厂商折叠为一行计数')
    check('login.microsoftonline.com' in out and 'static.edge.microsoftapp.net' in out,
          'SNI 渲染：折叠行里仍能看到被折叠的是哪些域名')


def check_mail_envelope_gate(tmp):
    """明文投递信封**多**的时候只报形态，不逐封刷屏；**少**的时候逐封列出。

    回归目标：`extracting-objects-from-pcap-example-04.pcap` 有 113 条 SMTP 会话，
    旧版逐封列出 = 212 行 `[邮件投递]`，占全文 273 行的 78%；78 条 finding 里
    76 条是这个 kind，把【前 10 项发现】10 个席位**全部**占满——而那道题
    （题名就是 "extracting objects from pcap"）真正要找的是抓包里的被提取文件。
    信封恰恰是最没有 IOC 的部分：113 封的发件域两两不同（随机化伪造）、
    收件人清一色 `@yahoo.com`（受害者）。
    """
    rc, out = run_cli([os.path.join(tmp, 't14-mailspam.pcap')])
    check(rc == 0, '邮件信封：扫描返回 0')

    n_deliver = out.count('[邮件投递]') + out.count('[投递样例]')
    check(n_deliver <= 8,
          '邮件信封：12 封只展开 ≤8 行（实际 %d）' % n_deliver)
    check('...（其余 9 封形态相同，已折叠' in out, '邮件信封：其余折叠成一行计数')
    check('发件域 12 个' in out and '每封都不同 = 随机化伪造，不是可用 IOC' in out,
          '邮件信封：说清发件域是随机化伪造（这正是"没有可用 IOC"的引导）')
    check('收件域 1 个: yahoo.com×12' in out, '邮件信封：收件域分布')
    # 折叠形态是**形态结论**，不是"可直接核验"的答案：它不该占【前 10 项发现】
    # 第一席、更不该被汇总区当成可提交候选。实测 ex04（113 封 spam）旧版给 0.85 高，
    # 稳坐第一席，而那道题里没有任何一封邮件是关键邮件。
    check('[0.85 高] 邮件投递' not in out,
          '邮件信封：折叠形态不进高置信（聚合不是可直接核验的答案）')
    check('[0.55 中] 邮件投递形态' in out, '邮件信封：折叠形态按"形态"计中置信')

    # 少的时候（t11-smtp 的 4 封）必须逐封列出——那时每封都是独立线索
    rc, out11 = run_cli([os.path.join(tmp, 't11-smtp.pcap')])
    check('[邮件投递] billing@example.net → victim@corp.example；主题: New Invoice 59175'
          in out11, '邮件信封：少量（4 封）仍然逐封列出，不折叠')
    check('形态相同，已折叠' not in out11, '邮件信封：少量时不出现折叠行')


def check_dns_discovery_fold(tmp):
    """服务发现类 DNS 查询折叠成**一行按域名计数**，域外域名必须显形。

    回归目标：2024-09-04 域渗透那道题。它的 DNS 段逐条列出 6 条
    `_ldap._tcp…（服务发现/投毒相关查询）`，全部是同一台主机对**本域**发起的
    常态查询——而该题的四个答案（主机名 `DESKTOP-RNVO9AT` / IP / MAC / 账号
    `afletcher`）与域名一个字都不沾，这 6 行对解题零引导。
    折叠的边界是**不埋线索**：`_ldap._tcp.pdc._msdcs.enemywatch.net` 这种域外
    域名的 SRV 查询是有效的，归组计数必须把它显形出来。
    """
    rc, out = run_cli([os.path.join(tmp, 't15-addns.pcap')])
    check(rc == 0, 'DNS 服务发现：扫描返回 0')

    # 旧的逐条形态必须消失：7 条查询不应产出 7 行 `DNS查询:`
    n_lines = out.count('] DNS查询: _ldap') + out.count('] DNS查询: _kerberos') \
        + out.count('] DNS查询: wpad.')
    check(n_lines == 0,
          'DNS 服务发现：不再逐条列出（旧版 7 条占 7 行，实际 %d 行）' % n_lines)
    check('] DNS查询（服务发现类，已折叠）: 7 条' in out,
          'DNS 服务发现：7 条折叠成一行并如实计数')

    # 不埋线索：域外域名必须出现在折叠行里，且计数报成"涉及 2 个域"
    check('涉及 2 个域: bepositive.com×6、enemywatch.net×1' in out,
          'DNS 服务发现：按域名归组，域外域名 enemywatch.net 显形')
    check('域外域名的 SRV 查询值得追' in out,
          'DNS 服务发现：多域时给出"值得追"的引导，而不是当成常态')

    # 纯本域的场景（没有域外域名）才说"与答案无关"
    check('与答案无关' not in out.split('DNS查询（服务发现类，已折叠）', 1)[1][:80],
          'DNS 服务发现：出现域外域名时不谎称"与答案无关"')


def check_dns_highfreq_gate():
    """「高频查询域名」必须跳过反向解析 / 服务发现 / 已知基础设施（纯离线）。

    回归目标：`B.pcap` 的【前 10 项发现】第 7–9 席曾被
    `1.10.168.192.in-addr.arpa`（948 次，反向解析——它是 IP 不是域名）、
    `teredo.ipv6.microsoft.com`（微软 Teredo 隧道）、`ns1.mediatemple.net`
    占满，而它们的建议文案是"可能是 C2 或 DGA"。同一份抓包的高位全是
    Web 攻击载荷——真正要看的线索被这三条挤在下面。
    """
    import collections
    from ctfsweep.core.dns import _analyze_domain_stats
    from ctfsweep.core.router import AnalysisResult
    from ctfsweep.core.utils import dns_lead_reason, is_reverse_dns

    # 反向解析名在两条链路上都要被当作常规流量：高频榜跳过 + 不逐条列出
    check(is_reverse_dns('1.10.168.192.in-addr.arpa')
          and is_reverse_dns('1.0.0.ip6.arpa')
          and not is_reverse_dns('in-addr.arpa.example.com'),
          '反向解析：只认 arpa 后缀，不误伤同名普通域名')
    long_v6 = '.'.join(['0'] * 32) + '.ip6.arpa'
    check(dns_lead_reason(long_v6) is None,
          '反向解析：IPv6 反向名不再被当成"多段拼接外带"')

    counts = collections.Counter({
        '1.10.168.192.in-addr.arpa': 948,     # 反向解析（PTR）
        'teredo.ipv6.microsoft.com': 23,      # 已知厂商基础设施
        'wpad.bepositive.com': 20,            # 服务发现
        '9.9.9.9.in-addr.arpa': 12,           # 反向解析
        'evil-c2-domain.com': 15,             # 真的高频陌生域名 → 必须保留
        'once.example.com': 3,                # 低于 count>10 阈值
    })
    res = AnalysisResult('dns')
    _analyze_domain_stats(counts, res)
    hi = [f.kind for f in res.findings if f.kind.startswith('高频查询域名')]
    check(hi == ['高频查询域名: evil-c2-domain.com'],
          '高频查询域名：只留真正陌生的高频域名%s'
          % ('（实际：%s）' % hi if hi != ['高频查询域名: evil-c2-domain.com'] else ''))

    sugg = [f.suggestion for f in res.findings if f.kind.startswith('高频查询域名')]
    check(sugg and '可能是 C2 或 DGA' not in sugg[0],
          '高频查询域名：建议文案不再断言"C2 或 DGA"（AD 域会被带偏）')


def check_kw_boundary_gate():
    """关键词必须是独立词，不能是词内子串（纯离线）。

    回归目标：`A.pcapng` 的一段 SocksiPy 代理脚本 hex 解码出 Python 源码，
    里面 `flags = args[:-1]` / `def recvfrom(self, bufsize, flags=0)` 让裸子串
    判定 `k in low` 命中关键词 `flag`，于是【前 10 项发现】的第 3–5 席全是
    `hex` 线索（证据是 Python 源码片段），真正的 Kerberos 票据被挤下去。
    同一个裸子串判定还让 DGA 随机串里的 `c2`、URL 编码里的 `%2C2` 白拿 +0.05。
    """
    from ctfsweep.core.decode import decode_chain
    from ctfsweep.core.meta_judge import MetaJudge
    from ctfsweep.core.utils import decode_score, kw_hit_bounded

    # (a) 词内子串不算命中；独立词 / flag{ 形态算命中
    cases = [
        ('def recvfrom(self, bufsize, flags=0)', 'flag', False),
        ('FolderValueFlags=1', 'flag', False),
        ('create_pdo_flag', 'flag', False),
        ('the flag is here', 'flag', True),
        ('payload flag{abc}', 'flag', True),
        ('payload flag{abc}', 'flag{', True),
        ('prefix2c2suffix', 'c2', False),      # URL 编码 %2c2 / 随机串
        ('beacon to c2 now', 'c2', True),
        ('keyboard layout', 'key', False),
        ('the key is here', 'key', True),
        # `key` 落在标识符内部（`api_key`）不算——但 `api_key` 自身在
        # HIGH_PRIORITY_KEYWORDS 里，所以该场景仍然命中，只是走另一条关键词
        ('api_key = x', 'key', False),
        ('api_key = x', 'api_key', True),
    ]
    bad = ['%r/%s' % (t, k) for t, k, want in cases
           if kw_hit_bounded(t, [k]) != want]
    check(not bad, '关键词边界：词内子串不算命中%s'
          % ('（异常：%s）' % ','.join(bad[:3]) if bad else ''))

    # (b) 解码链：Python 源码的 hex 产物不再被当成线索（曾产出 3 条 hex）
    src = (b'return _BaseSocket.recvfrom(self, bufsize, flags) '
           b'if not self._proxyconn: self.bind(("", 0))')
    hits, seen = [], set()
    decode_chain(src.hex().encode(), ['flag', 'ctf', 'key'], 3, hits, seen)
    check(not hits, '解码链：源码里的 flags 不再产出 hex 线索')

    # (c) 解码链正例：真 flag{...} 必须照旧命中
    hits, seen = [], set()
    decode_chain(b'the flag{abc123} is here'.hex().encode(),
                 ['flag', 'ctf', 'key'], 3, hits, seen)
    check(len(hits) == 1 and hits[0][1] == 'hex', '解码链：真 flag 仍被解出')

    # (d) 解码打分：`flags` 不给关键词档（0.70），落回 0.60
    check(decode_score(b'def f(self, flags=0): pass', ['flag']) == 0.60,
          '解码打分：词内的 flags 不算关键词命中')

    # (e) 元判断核：证据里的词内 `flags` 不再白拿 +0.05
    def score_of(ev):
        return MetaJudge([{'module': 'scanner', 'kind': 'hex', 'confidence': 0.60,
                           'evidence': ev}]).score()[0]['score']
    check(score_of('flags = args[:-1]') == 0.60,
          '元判断核：证据含词内 flags 时不加成')
    check(score_of('the flag{abc} is here') == 0.65,
          '元判断核：证据含真 flag 时仍 +0.05')


def _ntlm_type3(domain='', user='', host='', nt=b''):
    """手工拼一条 NTLMSSP Type-3（认证）报文，供离线回归使用。

    布局：签名(8) + 消息类型(4) + 六个安全缓冲区（各 8 字节：len/maxlen/offset），
    缓冲区次序 LM(0)/NT(1)/Domain(2)/User(3)/Host(4)/SessionKey(5)，字段按
    UTF-16LE 存放——真实报文就是这种编码（`ad._ntlm_field` 也正是这么取的）。
    """
    import struct
    head = b'NTLMSSP\x00' + struct.pack('<I', 3)
    fields = [b'', nt, domain.encode('utf-16-le'), user.encode('utf-16-le'),
              host.encode('utf-16-le'), b'']
    off, bufs, body = 12 + 6 * 8, b'', b''
    for f in fields:
        bufs += struct.pack('<HHI', len(f), len(f), off + len(body))
        body += f
    return head + bufs + body


def check_ad_ntlm_empty_account():
    """NTLM Type-3 账号字段为空时，不得产出"只有一个反斜杠"的线索（纯离线）。

    回归目标：`A.pcapng` 的【前 10 项发现】里曾有一条
    `域账号: NTLM 认证：\\（主机 WIN7-1，未捕获 challenge）`——匿名/机器认证的
    Type-3 报文 domain 与 user 都是空串，`'%s\\%s'` 硬拼出来就只剩一个反斜杠，
    对解题零引导价值，却照样占掉前十的一席。
    """
    from ctfsweep.core.ad import scan_ad

    def evidence_for(domain='', user='', host=''):
        """跑一遍 scan_ad，按渲染口径（val 走 utf-8）解码出「域账号」线索文本。"""
        out = []
        scan_ad({}, [(1, '10.0.0.5', 40000, '10.0.0.9', 445,
                      _ntlm_type3(domain, user, host))],
                lambda f: out.append(f))
        return [f[3].decode('utf-8', 'replace') for f in out if f[1] == '域账号']

    # 1) 全空 —— 旧版会吐出 `NTLM 认证：\（主机 ，...）`，现在整条丢弃
    empty = evidence_for()
    check(not empty, 'NTLM：domain/user/host 全空时不产出空壳线索')
    check(not any('认证：\\（' in e for e in empty),
          'NTLM：不出现"认证：\\（"这种孤立反斜杠')

    # 2) 只有域没有账号 —— 不拼出 `CORP\`，退化成"域 CORP 上的认证"
    dom = evidence_for(domain='CORP')
    check(dom == ['NTLM 认证：CORP（主机 未知，未捕获 challenge）'],
          'NTLM：只有域时不拼尾反斜杠')

    # 3) 只有主机 —— 主机名本身仍是有效信息，必须留下
    check(evidence_for(host='WIN7-1')
          == ['NTLM 认证（账号字段为空，未捕获 challenge）：主机 WIN7-1'],
          'NTLM：账号为空但主机名可用时仍输出主机')

    # 4) 账号齐全 —— 正常形态逐字不变（域\账号）
    check(evidence_for(domain='CORP', user='alice', host='PC1')
          == ['NTLM 认证：CORP\\alice（主机 PC1，未捕获 challenge）'],
          'NTLM：账号齐全时保持 域\\\\账号 形态')


def check_tls_sni():
    """TLS SNI 提取：全 HTTPS 的题目里，C2/投递域名只存在于 SNI（纯离线）。

    回归目标：2020-09-25 那道题报告能给出受害主机/MAC/账号/投递的 jojo.exe，
    却给不出 `paste.nrecom.net` 与 `37.120.174.218`——它们是 HTTPS，域名只在 SNI。
    """
    from ctfsweep.core.scanner import tls_sni

    for dom in ('paste.nrecom.net', 'a.b.c.example.co.uk', 'x.io'):
        check(tls_sni(_client_hello(dom)) == dom, 'SNI：提取 %s' % dom)

    # 前缀杂字节（TCP 流从中间开始是常态）也要能找到
    check(tls_sni(b'\x00' * 40 + _client_hello('evil.example')) == 'evil.example',
          'SNI：前缀杂字节不影响提取')
    # 多个记录：前面是别的 TLS 记录，ClientHello 在后面
    check(tls_sni(b'\x16\x03\x03\x00\x05' + b'\x99' * 5 + _client_hello('later.example'))
          == 'later.example', 'SNI：跳过非 ClientHello 记录')
    # 无扩展（老式 ClientHello）→ 空串；调用方拿到空串才不会写出乱码
    check(tls_sni(_client_hello(None)) == '', 'SNI：无扩展时返回空串')
    # ServerHello（握手类型 0x02）即使结构雷同也不当 ClientHello 解
    check(tls_sni(_client_hello('nope.example', hs_type=2)) == '',
          'SNI：ServerHello 不解 SNI')
    check(tls_sni(b'GET / HTTP/1.1\r\nHost: x\r\n\r\n') == '', 'SNI：明文 HTTP 不误判')
    # 截断不得抛异常（畸形包在真实抓包里遍地都是）
    full = _client_hello('trunc.example')
    for cut in range(0, len(full), 3):
        tls_sni(full[:cut])
    check(tls_sni(b'') == '' and tls_sni(b'\x16\x03') == '', 'SNI：截断/空输入不抛异常')


def check_router_dispatch(tmp):
    """文件类型模块必须真的被调度到（防"签名不匹配 → 静默空转"）。

    `Router._dispatch()` 曾无条件给所有模块传 `ctx=`，而 `browser`/`config`/`db`/
    `email`/`logs`/`memory`/`archives` 七个模块的 `analyze()` 都没有这个形参——
    全部 `TypeError`，又被 `run_filetype()` 的 `except: pass` 吞掉。症状是这些格式的
    `【模块名】` 块**永远为空，且不报任何错**。这里两头都守：形参匹配 + 端到端出块。
    """
    from ctfsweep.core.capture import CaptureContext
    from ctfsweep.core.router import Router, _TYPE_MAP

    p = os.path.join(tmp, 'dispatch.txt')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('flag{router-dispatch}\n')
    with open(p, 'rb') as f:
        ctx = CaptureContext(f.read())

    names = sorted({m for mods in _TYPE_MAP.values() for m in mods})
    bad = []
    for name in names:
        try:
            Router(p)._dispatch(name, ctx=ctx)
        except TypeError as ex:
            if 'unexpected keyword argument' in str(ex):
                bad.append('%s(%s)' % (name, ex))
    check(not bad, '文件类型模块可分派：%d 个签名匹配%s'
          % (len(names), '' if not bad else '——不匹配 %s' % '、'.join(bad)))

    rc, out = run_cli([p])
    check(rc == 0 and '【路由匹配模块】config' in out, '.txt 路由到 config 模块')
    check('【config】' in out and '配置中的 flag' in out,
          '文件类型模块真的产出块（.txt → 【config】）')


def main():
    global DATA
    tmp = tempfile.mkdtemp(prefix='ctfsweep-smoke-')
    DATA = os.path.join(tmp, 'data')
    # 全程隔离：扫描缓存 / 留存区 / 模型 / 训练配置全部读写临时目录，
    # 不污染真实 ~/.devtools/ctfsweep 与项目 models/（所有 run_cli 子进程继承此环境）
    _prev_env = {k: os.environ.get(k) for k in ('CTFSWEEP_DATA_DIR', 'CTFSWEEP_MODELS_DIR')}
    # ⚠️ 数据目录是 tmp 的**子目录**，不是 tmp 本身：夹具生成在 tmp 根下，
    #    而 `clear`（无参数）会清空数据目录内容——两者同处一层的话，一次 clear 就把
    #    夹具全端了（实测：t10-ftp.pcap 当场消失）。真实形态也是"数据目录里只有缓存"。
    os.environ['CTFSWEEP_DATA_DIR'] = DATA
    os.environ['CTFSWEEP_MODELS_DIR'] = tmp
    os.makedirs(DATA, exist_ok=True)
    try:
        print('== 生成测试样例 ==')
        names = gen_fixtures.generate(tmp)
        for n in names:
            print('  - %s' % n)

        print('== 基础 CLI ==')
        rc, out = run_cli(['--version'])
        check(rc == 0 and __version__ in out, '--version 输出版本号')
        with open(os.path.join(ROOT, 'VERSION'), encoding='utf-8') as f:
            check(f.read().strip() == __version__, 'VERSION 文件与包版本一致')
        rc, out = run_cli([])
        check(rc == 1 and '用法' in out, '无参数时打印帮助并返回 1')
        rc, out = run_cli(['--help'])
        # 帮助是 ptool 形态的薄索引（标题/用法/子命令/选项/示例/说明）；
        # 「示例」段是这套形态的招牌，也当作"这确实是那份帮助"的锚点
        check(rc == 0 and '用法' in out and '示例' in out, '--help 返回 0（薄索引形态）')
        check(all(s in out for s in ('update', 'install', 'uninstall', 'clear', 'config', 'help')),
              '--help 含管理子命令（update/install/uninstall/clear/config/help）')
        check(not any(re.search(r'^\s*ctfsweep\s+%s\b' % re.escape(s), out, re.M)
                      for s in _REMOVED_SUBCOMMANDS),
              '--help 无训练/标注子命令（%s）' % '/'.join(_REMOVED_SUBCOMMANDS))
        # README 不随安装载荷发布，装机用户手上只有 --help，所以「说明」里
        # 缓存在哪/是否自动写必须自足。"留存区"是被替换掉的旧段名，反向断言防它漂回来
        check('扫描缓存: ~/.devtools/ctfsweep/cache/' in out and '留存区' not in out,
              '--help 说明扫描缓存（替换原「留存区」段）')
        # 反向断言：散文墙别漂回来（history: 曾把置信度分数表 13 行 + 判断核 3 行 +
        # 缓存 5 行整块铺进帮助，共 63 行；改薄后 45 行）。上限留 5 行余量
        check(len(out.splitlines()) <= 50,
              '--help 保持精简（%d 行 ≤ 50，防散文墙漂回来）' % len(out.splitlines()))
        rc, out = run_cli(['/no/such/file.pcap'])
        check(rc == 2, '路径不存在时返回 2')
        rc, out = run_cli(['config'])
        check(rc == 0 and '扫描缓存:' in out,
              'config：报出扫描缓存占用（清理入口是 ctfsweep clear）')

        print('== Windows PATH 增删（纯函数）==')
        check_windows_path_helpers()

        print('== shell 脚本体检 ==')
        check_shell_scripts()

        print('== 补全体检 ==')
        check_completions()

        print('== t1.pcap：多载体 flag ==')
        rc, out = run_cli([os.path.join(tmp, 't1.pcap')])
        check('flag{plain-smoke-ok}' in out, '明文 flag')
        check('flag{h3x-smoke-ok}' in out, 'hex 解码 flag')
        check('flag{dns-smoke-ok}' in out, 'DNS 子域名 base64 外带')
        check('"username":"admin"' in out, 'JWT payload 解码')
        check('WEBUI_SK=Advanced_System_for_Text' in out, '环境变量回显')
        check('【flag 候选汇总】（可直接核验/提交）' in out, '汇总：flag 形状候选单独成组')
        rc, out = run_cli([os.path.join(tmp, 't1.pcap'), '--min-score', '0.9'])
        check('flag{plain-smoke-ok}' in out and 'WEBUI_SK' not in out, '--min-score 过滤低置信')

        print('== t2.pcapng ==')
        rc, out = run_cli([os.path.join(tmp, 't2.pcapng')])
        check('flag{pcapng-smoke-ok}' in out, 'pcapng 明文 flag')
        rc, out = run_cli(['-f', os.path.join(tmp, 't2.pcapng')])
        check(rc == 0 and 'flag{pcapng-smoke-ok}' in out, '-f/--file 等价位置参数')

        print('== t3.evtx ==')
        rc, out = run_cli([os.path.join(tmp, 't3.evtx')])
        check('flag{evtx-smoke-ok}' in out, 'evtx UTF-16 明文 flag')
        check('krjl424' in out and 'zlmqu458xktq}' in out, '花括号片段探测')
        check('flag{krjl424zlmqu458xktq}' in out, '启发式拼接建议')
        check('dll55e3' not in out, '噪音闸门：文件名后缀拼贴（.dll55e3}）已剔除')
        check('3050f3' not in out, '噪音闸门：GUID 花括号（{3050f3）已剔除')
        check('v8ozb' not in out, '噪音闸门：密集乱码 token（{v8ozb）已剔除')
        check('FolderValueFlags' not in out, '噪音闸门：词内误报（FolderValueFlags）已剔除')
        check('create_pdo_flag' not in out, '噪音闸门：标识符内部（create_pdo_flag）已剔除')
        check('msctf' not in out, '噪音闸门：标识符内部（msctf_）已剔除')
        check('【中置信（需人工确认）】' in out, '报告分级：中置信小标题（换行分区）')
        # EVTX 是二进制容器：早期按字节当文本读，`\x60` 这类字节的巧合会被喂给
        # 攻击正则，刷出满屏「RCE（命令替换）」乱码（证据本身就是乱码，对解题零帮助）。
        # 现在先抽 UTF-16 字符串再分析 → 命中真实的 flag 行，且不再有乱码误报。
        check('日志中的 flag' in out, 'evtx 二进制容器：抽字符串后命中真实 flag 行')
        check('RCE（命令替换）' not in out, 'evtx 二进制容器：乱码不再触发攻击正则误报')
        check('【扫描统计】' in out and '线路报告（抓包/原始文件）：高' in out,
              '统计：换行分区输出')
        # t3 有【logs】的 0.97，线路侧却没有高置信——只报线路会印出"高 0 条"，
        # 与上面刚打印的模块块自相矛盾。两条管线必须分开报。
        check('模块报告（类型块）：高 1 条' in out, '统计：模块侧高置信单独计数（不再自相矛盾）')
        check('统计: 高置信' not in out, '旧版单行统计已移除')
        check('片段池（按文件标注来源）' in out and '←' in out, '全局片段池：按行标注来源')

        print('== t4.pcap --extract ==')
        exdir = os.path.join(tmp, 'extract')
        rc, out = run_cli([os.path.join(tmp, 't4.pcap'), '--extract', '--extract-dir', exdir])
        check('[提取]' in out, '提取提示')
        check('flag{zip-carve-ok}' in out, 'zip 内 flag 内容扫描')
        carved = os.listdir(exdir) if os.path.isdir(exdir) else []
        check(any(f.endswith('.zip') for f in carved), 'zip 文件已落盘')

        print('== t5-ad.pcap：AD / 域协议 ==')
        rc, out = run_cli([os.path.join(tmp, 't5-ad.pcap')])
        check('【AD / 域渗透线索】' in out, 'AD 线索区块出现')
        check('域: CORP.LOCAL' in out, 'Kerberos 域名解析（CORP.LOCAL）')
        check('$krb5asrep$23$svc_sql@CORP.LOCAL:' in out, 'AS-REP Roasting 哈希（-m 18200 格式）')
        check('RC4-HMAC' in out and '可离线爆破' in out, 'RC4 票据标注可爆破')
        check('NetNTLMv2' in out and 'kanna.seto::corp:' in out, 'NetNTLMv2 响应（-m 5600 格式）')
        check('P@ssw0rd-AD-2026' in out, 'LDAP 明文绑定口令')
        check('MSSQLSvc/dc01.corp.local' in out, 'SPN（Kerberoasting 目标）')

        print('== t6-hosts.pcap：主机表（ARP / DHCP）==')
        rc, out = run_cli([os.path.join(tmp, 't6-hosts.pcap')])
        check('【主机表】' in out, '主机表区块出现')
        check('10.9.9.10' in out and '02:00:00:00:00:aa' in out, 'ARP/以太网解析 10.9.9.10 → MAC')
        check('10.9.9.20' in out and '02:00:00:00:00:bb' in out, 'ARP 应答解析 10.9.9.20 → MAC')
        check('SMOKE-PC' in out, 'DHCP 主机名（选项 12）')

        print('== t7-tls.pcap：TLS 跳过 / JPEG 判别 / 反误报 ==')
        exdir7 = os.path.join(tmp, 'extract7')
        rc, out = run_cli([os.path.join(tmp, 't7-tls.pcap'), '--extract', '--extract-dir', exdir7])
        check('跳过' in out and 'TLS' in out, 'TLS 加密流被跳过（密文不雕刻）')
        check('</td></tr>' not in out, 'HTML 标记行不误报为命令')
        check(out.count('[交互会话]') == 1, '仅真 Windows 会话被识别（HTML 页不误报）')
        check('whoami' in out and 'ipconfig' in out, '真会话命令序列完整（正例）')
        jpgs7 = [f for f in (os.listdir(exdir7) if os.path.isdir(exdir7) else []) if f.endswith('.jpg')]
        check(len(jpgs7) == 1, '仅提取明文流真 JPEG（TLS 伪 JPEG 被挡）')
        if jpgs7:
            data7 = open(os.path.join(exdir7, jpgs7[0]), 'rb').read()
            check(data7[:4] == b'\xff\xd8\xff\xe0' and data7[-2:] == b'\xff\xd9',
                  'JPEG 头/尾完整（FFD8FFE0…FFD9）')

        print('== t8-b64.pcap：页面内嵌 base64 载荷 ==')
        exdir8 = os.path.join(tmp, 'extract8')
        rc, out = run_cli([os.path.join(tmp, 't8-b64.pcap'), '--extract', '--extract-dir', exdir8])
        check('base64 @' in out, 'base64 载荷段被识别')
        check('flag{b64-embedded-ok}' in out, '解码出的 zip 内容被扫描（flag 命中）')
        zips8 = [f for f in (os.listdir(exdir8) if os.path.isdir(exdir8) else []) if f.endswith('.zip')]
        check(len(zips8) == 1, 'base64 解码的 zip 已落盘')
        if zips8:
            d8 = open(os.path.join(exdir8, zips8[0]), 'rb').read(4)
            check(d8[:2] == b'PK', '落盘文件为有效 zip（PK 头）')

        print('== t9-dns.pcap：DNS 真实解析 / 网页噪音闸门 ==')
        rc, out = run_cli([os.path.join(tmp, 't9-dns.pcap')])
        seg = out.split('【dns】', 1)[1].split('格式:', 1)[0] if '【dns】' in out else out
        check('tunnel-domain.com' in seg, '真实 DNS 长查询被识别（外带嫌疑）')
        check('wagbridge' not in seg, '良性长域名（多短标签拼接）不报外带')
        check('ms17-010' not in out, 'HTTP 文件名串不被当"长域名"（旧误报已修）')
        check('f2f2f2' not in out and 'fff9ec' not in out, 'CSS 颜色值不被当片段（旧误报已修）')
        # 常规域名折叠：一次正常上网抓包里有几十条 CDN/门户查询，逐条列出会把
        # 真正的外带/DGA 线索挤出屏幕。折叠成一行且**不丢信息**——外带的
        # tunnel-domain 仍逐条列出并标注原因，常规的 alibabadns 进折叠行。
        check('DNS查询（常规域名，已折叠）' in out, 'DNS：常规域名折叠成一行（不逐条刷屏）')
        check('alibabadns.com' in out, 'DNS：折叠只是少占屏，常规域名仍在报告里可见')
        check('（超长标签（编码外带/隧道特征））' in out, 'DNS：逐条列出的线索标注了判定原因')

        print('== DNS 线索判定（dns_lead_reason）==')
        from ctfsweep.core.utils import dns_lead_reason
        for name in ('college.usatoday.com', 's2.wp.com', 'jqmt.qq.com',
                     'cp601-prod.do.dsp.mp.microsoft.com',
                     'd15krst4gi8g86.cloudfront.net', 'b28-yk-w2.youku.com',
                     'v10.events.data.microsoft.com', 'addons.g-fox.cn'):
            check(dns_lead_reason(name) is None, '常规域名不报线索：%s' % name)
        # 只按长度判"超长标签"会把自然语言长词当编码外带：pisosyrecubrimientos
        # 是西语单词（20 字符、带元音、无数字），base64/hex 外带标签则不会三者都占。
        for name in ('mail.pisosyrecubrimientos.com',
                     'p3plcpnl001.prod.phx3.secureserver.net'):
            check(dns_lead_reason(name) is None, '自然语言长词不算编码外带：%s' % name)
        for name in ('Zm9vYmFyZm9vYmFyZm9vYmFyZm9vYmFyZm9vYmFyZm9vYmFy.x.com',
                     'a3f9b2c1d4e5f60718293a4b5c6d7e8f.x.com'):
            check(dns_lead_reason(name) is not None, '编码标签仍报外带：%s' % name[:30])
        for name in ('Zm9vYmFy' * 6 + '.exfil.tunnel-domain.com',
                     'kamuchehddhgfgf.ddns.net',
                     'ubbifeder.cyou', 'opsbox8097.com', 'wpad.wokemountain.com',
                     '_ldap._tcp.pdc._msdcs.enemywatch.net', 'isatap.corp.local'):
            check(dns_lead_reason(name) is not None, '异常域名报线索：%s' % name[:40])

        print('== t10-ftp.pcap：FTP 证据 / 二进制关键词闸门 ==')
        rc, out = run_cli([os.path.join(tmp, 't10-ftp.pcap')])
        check('[FTP会话]' in out and '成功凭据: dj / dj' in out, 'FTP 会话识别（凭据）')
        check('FTP成功凭据: dj / dj' in out, '报告行改用类型标签（不再是"关键词[]"空标签）')
        check('RETR 2.jpg' in out, 'FTP 命令序列（登录后）')
        check('关键词[]' not in out, '空关键词标签不再出现')
        check('关键词[flag]' not in out, '二进制流关键词字节巧合被剔除（flag）')
        check(out.count('关键词[ctf]') == 2 and 'the ctf challenge' in out,
              '二进制流的 ctf 巧合被剔除，真实文本关键词保留（正例×2）')
        check('【证据汇总】（未发现 flag 形状候选' in out, '汇总：非 flag 文件明确提示无 flag 候选')
        check('[FTP成功凭据] dj / dj' in out, '汇总：证据按类型标注（非 flag 类）')
        check('【flag 候选汇总】' not in out, '汇总：非 flag 文件不出 flag 候选组')

        print('== t10-ftp.pcap：-q/--brief 精简输出 ==')
        clear_cache()   # 上面刚扫过它：不清的话本次会走"已有缓存不覆盖"分支
        rc, out = run_cli([os.path.join(tmp, 't10-ftp.pcap'), '-q'])
        check('【扫描统计】' in out and '高置信（可直接核验），具体信息：' in out,
              '精简块：标题与高置信行')
        check('1.txt' in out and 'dj / dj' in out, '高置信行：明细文件路径 + 内联值')
        check('2.txt' in out and '3.txt' in out and 't10-ftp_cache.txt' in out,
              '中/低档与完整缓存路径')
        check('[FTP会话]' not in out and '格式:' not in out,
              '控制台不再输出详细报告（只留分档块）')
        croot = os.path.join(DATA, 'cache')
        cdirs = [d for d in (os.listdir(croot) if os.path.isdir(croot) else [])
                 if d.startswith('t10-ftp-')]
        check(len(cdirs) == 1, '缓存目录按「文件名-路径哈希」命名')
        cdir = os.path.join(croot, cdirs[0]) if cdirs else os.path.join(croot, '不存在')
        check(all(os.path.isfile(os.path.join(cdir, n)) for n in ('1.txt', '2.txt', '3.txt')),
              '1/2/3.txt 已落盘')
        f1 = os.path.join(cdir, '1.txt')
        if os.path.isfile(f1):
            with open(f1, encoding='utf-8') as fh:
                t1t = fh.read()
            check('条数: 1' in t1t and 'FTP成功凭据' in t1t and 'dj / dj' in t1t,
                  '1.txt：文件头 + 完整明细行')
        fc = os.path.join(cdir, 't10-ftp_cache.txt')
        check(os.path.isfile(fc), '完整报告缓存已落盘')
        if os.path.isfile(fc):
            with open(fc, encoding='utf-8') as fh:
                t2t = fh.read()
            check('[FTP会话]' in t2t and '【扫描统计】' in t2t,
                  '缓存含完整详细输出（会话 + 统计区）')

        # 同名文件（proj1/same.pcap 与 proj2/same.pcap）在目录扫描下**合进同一个**
        # 运行目录——旧断言"两个 same-<哈希> 目录各自独立"正是被废弃的按文件分粒度；
        # 现在守的是更强的性质：合了之后归属信息没有丢，两条命中各自带自己的相对路径。
        coll = os.path.join(tmp, 'coll')
        with open(os.path.join(tmp, 't10-ftp.pcap'), 'rb') as src:
            blob = src.read()
        for sub in ('proj1', 'proj2'):
            os.makedirs(os.path.join(coll, sub), exist_ok=True)
            with open(os.path.join(coll, sub, 'same.pcap'), 'wb') as dst:
                dst.write(blob)
        run_cli([coll, '-q'])
        same = [d for d in os.listdir(croot) if d.startswith('coll-')]
        check(len(same) == 1, '同名不同目录（目录扫描）：合进一个运行目录（不再一文件一目录）')
        if len(same) == 1:
            ct1 = os.path.join(croot, same[0], '1.txt')
            body = open(ct1, encoding='utf-8').read() if os.path.isfile(ct1) else ''
            check('← proj1/same.pcap' in body and '← proj2/same.pcap' in body,
                  '同名文件合并不丢归属（两条命中各自带相对路径）')

        print('== t11-smtp.pcap：邮件会话（EHLO / STARTTLS / 明文信封）==')
        rc, out = run_cli([os.path.join(tmp, 't11-smtp.pcap')])
        # 邮件流量曾经零输出：spambot 抓包（10 MB、25 条 SMTP）只报出 3 条低置信
        # DNS，整份文件看起来"什么都没扫到"——而会话形态本身就是那道题唯一的引导。
        check('[邮件会话] 4 条 SMTP' in out, '邮件会话聚合为一段（不逐条刷屏）')
        check('客户端自报主机名(HELO/EHLO): 10.0.0.19, 10.0.0.30, 10.0.0.45' in out,
              '客户端自报主机名（僵尸网络/群发题的关键指纹）')
        check('3 条正文被 STARTTLS 加密' in out, '加密会话如实说明"内容不可解读"')
        check('MAIL FROM <billing@example.net> → RCPT TO <victim@corp.example>' in out,
              '明文投递信封（发件人 / 收件人）')
        check('主题: New Invoice 59175' in out, '投递主题')
        check('[0.85 高] 邮件投递信封' in out, '信封进高置信（可直接核验）')
        check('[0.55 中] 邮件会话' in out, '会话形态进中置信（高于 MIN_SCORE，不被静默滤掉）')

        print('== t12-web.pcap：HTTP 攻击载荷（百分号编码）==')
        rc, out = run_cli([os.path.join(tmp, 't12-web.pcap')])
        # 山东.pcapng 实测：106 条请求里几十条是 sqlmap 载荷，全部百分号编码
        # （`%20AND%209418%3D3822%20UNION%20ALL%20SELECT`）。对原始 URI 匹配一条都报不出，
        # 整份文件零 finding——而"被注入了什么"正是那道题的核心。
        check('SQL注入（UNION SELECT） ×1' in out, 'SQLi：百分号解码后才匹配（UNION ALL SELECT）')
        check('例: /index.php?id=1 AND 9418=3822 UNION ALL SELECT 1,2' in out,
              'SQLi：报告里给出**解码后**的可读载荷')
        check('路径穿越 / 本地文件包含 ×1' in out, '路径穿越：..%2F..%2F..%2Fetc%2Fpasswd 命中')
        check('[0.85 高] Web攻击载荷' in out, '攻击载荷进高置信（可直接核验）')
        # 三种请求里只有两条是攻击：常规的 `?id=1` 若被算进去，"类数"会变成 3
        check('  [Web攻击载荷] 2 类（共 2 条请求' in out,
              '常规请求（?id=1）不被误报为攻击载荷')

        print('== 扫描缓存（每次扫描都写）==')
        check_scan_cache(tmp)

        print('== 扫描缓存（目录扫描：一次运行一个目录）==')
        check_dir_scan_cache(tmp)

        print('== 判断核（judge）==')
        check_judge(tmp)

        print('== 元判断核（meta_judge）==')
        check_meta_judge()

        print('== TCP 重组（merge_stream）==')
        check_stream_merge()

        print('== 二进制上下文净化（readable_window）==')
        check_readable_window()

        print('== 日志攻击检测的 WMI 闸门 ==')
        check_logs_wmi_gate()

        print('== 压缩包解压产物的扫描 ==')
        check_archives_content(tmp)

        print('== 重复结论去重 / 文本闸门 ==')
        check_dedup_and_text_gate()

        print('== DNS 高频榜的噪音闸门 ==')
        check_dns_highfreq_gate()

        print('== 关键词边界（词内子串不算命中）==')
        check_kw_boundary_gate()

        print('== NTLM 空账号字段的闸门 ==')
        check_ad_ntlm_empty_account()

        print('== TLS SNI 提取 ==')
        check_tls_sni()

        print('== TLS SNI 块的渲染（聚合 / 不截断 / 厂商折叠）==')
        check_sni_render(tmp)

        print('== 明文投递信封的展开上限 ==')
        check_mail_envelope_gate(tmp)

        print('== 服务发现类 DNS 查询的折叠 ==')
        check_dns_discovery_fold(tmp)

        print('== 路由分派 ==')
        check_router_dispatch(tmp)

        print('== report 渲染等价（CLI 边界的 Finding↔5 元组往返）==')
        check_report_equivalence()

        print('== 目录模式 ==')
        rc, out = run_cli([tmp])
        check(rc == 0, '目录扫描整体返回 0')
        rc, out = run_cli(['-F', tmp])
        check(rc == 0, '-F 指定文件夹')
        rc, out = run_cli(['--folder', tmp])
        check(rc == 0, '--folder 长选项等价')

        # ⚠️ clear 放**最后**：它清空整个数据目录，而 tmp 同时是模型目录、还住着上面
        # 各小节要用的夹具——放中间会把它们一并删掉，表现为后续小节莫名其妙地失败
        # （实测：夹具被删后 check_sni_render 连 '[TLS SNI]' 都拿不到）。
        print('== clear 子命令（清空数据目录）==')
        check_clear(tmp)

        print('== Windows 载荷 / 非交互确认 ==')
        check_windows_payload()
        check_eof_is_noninteractive()
    finally:
        for k, v in _prev_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print('冒烟失败 %d 项:' % len(FAILS))
        for m in FAILS:
            print('  - %s' % m)
        return 1
    print('冒烟全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
