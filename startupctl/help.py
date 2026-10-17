# -*- coding: utf-8 -*-
"""帮助文本——**由数据表构建**，不手写对齐。

为什么是构建而不是一串字面量：手写的对齐会**漂移**。改一个子命令名、给某个选项
多打一个字，整节描述列就歪了，而这种歪在 review 里几乎看不出来。用 `pad()` 按显示
宽度（CJK 计 2 列）算出来，对齐就是构造上正确的；`tests` 里再用 `output.dw` 复算一遍
作为回归护栏。

`HELP` 是一份**瘦索引**，硬上限 50 行（冒烟断言）。每个子命令的完整选项放在
`SUB_HELP` 里，由 `startupctl <子命令> --help` 打印——把 19 个子命令的所有旗标塞进
顶层帮助，只会得到一屏没人会读的文字墙。

顶层「说明」段是自足的，因为 README **不随安装包分发**（见 installer/deploy.sh 的
白名单拷贝），装着的人只能看到这段。
"""
from .core.output import dw, pad

TITLE = 'startupctl - 启动项扫描与管理（零依赖，Python 3.8+）'

# 与 ptool 同形：**「用法:」本身就是命令清单**，一行一条、全部可见。
# 不设「子命令:」分区，也不写 `whitelist ...` 这种省略号——分组命令把可用的
# 动作名写在描述里。ptool 那 15 行是这套工具族的视觉基准，照着它走。
COMMANDS = [
    ('startupctl list [筛选]', '扫描并列启动项（默认只列第三方）'),
    ('startupctl show <项>', '看一项详情：来源 · 命令 · 分类依据'),
    ('startupctl check', '只读体检（干净退 0，否则退 1）'),
    ('startupctl scan --save|--diff', '存快照 / 比对载荷漂移'),
    ('startupctl disable <项>...', '禁用（可逆）'),
    ('startupctl enable <项>...', '恢复启用'),
    ('startupctl remove <项>...', '移到备份目录（不删，可 restore）'),
    ('startupctl add <名> <命令>', '新建用户级自启项'),
    ('startupctl restore [时间]', '从备份还原并重新启用'),
    ('startupctl backup list|prune', '看备份 / 按保留策略清理'),
    ('startupctl clean [-y]', '批量禁用第三方项（预览在前）'),
    ('startupctl proc [--orphans]', '进程视图：三方进程与启动项聚合'),
    ('startupctl kill <pid|项>', '结束进程（先 TERM，--force 才 KILL）'),
    ('startupctl whitelist <动作>', '白名单：add remove list doctor prune'),
    ('startupctl guard <动作>', '进程守护：off deny_all blacklist whitelist choose arm status'),
    ('startupctl update [--check]', '检查并更新到最新版本'),
    ('startupctl install', '完整安装（从源码目录）'),
    ('startupctl uninstall [-y]', '卸载（-y 跳过确认）'),
    ('startupctl config', '显示配置'),
    ('startupctl help [子命令]', '帮助（给子命令名则看它的完整选项）'),
]

OPTIONS = [
    ('--all', '含系统项（默认只列第三方）'),
    ('--vendor V', '按厂商前缀筛选（如 com.docker）'),
    ('--long', '显示分类依据等长字段'),
    ('--json', '机器可读输出'),
    ('-y --yes', '跳过确认（非交互环境必须显式给）'),
    ('--dry-run', '只打印将要做什么，绝不改动任何东西'),
    ('--sudo', '需要管理员时整条命令交给 sudo 跑一次'),
    ('--config F', '指定配置文件'),
    ('-h --help', '显示帮助'),
    ('--version', '显示版本'),
]

EXAMPLES = [
    ('startupctl list --running', '看这次开机拉起了哪些三方进程'),
    ('startupctl list --vendor com.docker', '看某厂商在本机装了什么'),
    ('startupctl clean --dry-run', '先看清 clean 会动哪些，不动手'),
    ('startupctl add 我的服务 /path/run.sh', '让自己的项目开机自启'),
    ('startupctl whitelist add homebrew.mxcl.mysql', '把要常驻的留下来'),
]

NOTES = [
    '子命令帮助: startupctl <子命令> --help，或 startupctl help <子命令>',
    '只碰第三方: com.apple.*、%SystemRoot% 下的、发行版单元一律按系统项（判不准也按）',
    '预览在前: 改动类子命令一律先打印清单再动手；管道里没 -y 就拒绝执行',
    '可回退: remove 是移到数据根 backups/ 而非删除，restore 能还原并重新启用',
    '白名单只收窄: 它只让 clean 少动几项，绝不会让系统项变得可改',
    '数据目录: ~/.devtools/startupctl/（白名单 · 备份 · 快照，永不自动删除）',
]


def _rows(rows, indent=2, gap=2):
    """把 (左, 右) 表渲染成按显示宽度对齐的行。"""
    if not rows:
        return []
    width = max(dw(left) for left, _ in rows)
    out = []
    for left, right in rows:
        out.append(' ' * indent + pad(left, width) + ' ' * gap + right)
    return out


def _build():
    lines = [TITLE, '']
    lines.append('用法:')
    lines.extend(_rows(COMMANDS))
    lines.append('')
    lines.append('选项:')
    lines.extend(_rows(OPTIONS))
    lines.append('')
    lines.append('示例:')
    lines.extend(_rows(EXAMPLES))
    lines.append('')
    lines.append('说明:')
    lines.extend('  ' + n for n in NOTES)
    return '\n'.join(lines) + '\n'


HELP = _build()


# 每个子命令的完整选项（顶层帮助只放公共项，专属项在这里）
SUB_HELP = {
    'list': """
用法: startupctl list [选项]

扫描并列启动项。默认**只列第三方**（系统项动辄近千个，全列等于没列）。

选项:
  --all            连系统项一起列
  --system         只看系统项
  --third-party    只看第三方项（默认）
  --running        只看正在运行的
  --vendor V       按厂商前缀筛选，如 com.docker
  --kind K         按类型筛选：launchd-daemon launchd-agent login-item btm
                   systemd systemd-user xdg-autostart initd cron
                   registry-run startup-folder win-service task-scheduler
  --scope S        system 或 user
  --long           每条多打一行分类依据与警告
  --errors         展开显示扫描错误与权限受限的根（默认只显示计数）
  --json           机器可读输出

示例:
  startupctl list --vendor com.docker --long
""",
    'show': """
用法: startupctl show <项> [选项]

看一项的完整信息。分类依据（origin_evidence）**总会打印**——用户必须能复核
"为什么工具认为这是第三方"，不可审计的分类就是不可信任的分类。

选项:
  --raw       打印原始 plist / unit 文件 / 注册表值
  --resolve   解析可执行文件真实路径与代码签名（macOS 调 codesign，较慢）
  --json      机器可读输出
""",
    'check': """
用法: startupctl check [--json]

**只读**体检：回答"我的开机启动干不干净、clean 会不会做事"。
干净退 0，有可清理项退 1。适合放进 dotfiles 的 post-install 钩子或 CI。
""",
    'scan': """
用法: startupctl scan [--save|--diff] [--json]

  --save   把本次扫描存成快照
  --diff   与上次快照比对，报**载荷漂移**：身份（uid）没变但命令被换了。
           保留 Label 却换掉 ProgramArguments 正是持久化植入的典型手法。
""",
    'disable': """
用法: startupctl disable <项>... [选项]

禁用而不删除。各平台语义：
  macOS   plist 加 Disabled=true 并移走 RunAtLoad，再 launchctl bootout
  Linux   systemctl disable（移除 WantedBy 符号链接）
  Windows Run 值改名为 StartupctlDisabled-*；服务 Start=4；任务 /DISABLE

选项:
  -y --yes    跳过确认
  --dry-run   只打印计划
  --sudo      系统级项需要管理员时，把整条命令交给 sudo 跑一次
""",
    'enable': """
用法: startupctl enable <项>... [选项]

恢复启用。与 disable 对称（见 startupctl disable --help）。
""",
    'remove': """
用法: startupctl remove <项>... [选项]

**移到备份目录，不是删除**。可以用 `startupctl restore` 还原。
这是 remove 敢做的全部理由：文件还在，只是不在原位了。

选项:
  -y --yes    跳过确认
  --dry-run   只打印计划
  --purge     仅 Windows 服务：真正删除服务（默认只置 Start=4）。
              ⚠️ sc delete 是本工具里唯一没有干净撤销手段的操作。
""",
    'add': """
用法: startupctl add <名称> <命令> [选项]

新建**用户级**自启项——「让某项目开机自动运行」。
默认拒绝写系统级位置（写系统级需 root 且显式 --scope system）。

选项:
  --name N        显示名（默认取 <名称>）
  --run-at-load   加载时即运行（默认开）
  --scope user    作用域（目前只支持 user）
  -y --yes        跳过确认
""",
    'restore': """
用法: startupctl restore [<时间戳>|last] [<项>...] [选项]

从备份还原，**并重新启用**（只把文件放回去却留着禁用态是"半还原"，会让人以为失败了）。

选项:
  --force     目标已存在且内容不同时也覆盖。默认**拒绝**——覆盖用户后来
              重写的文件是真实危害。
  -y --yes    跳过确认
  --dry-run   只打印计划
""",
    'backup': """
用法: startupctl backup list | backup prune [-y]

  list    列出备份（新的在前）
  prune   按 BACKUP_KEEP / BACKUP_MIN_DAYS 清理。不足 BACKUP_MIN_DAYS 天的
          备份一律不删——防止刚做完就手滑清掉后悔药。
""",
    'clean': """
用法: startupctl clean [选项]

批量**禁用**（不是删除）判为第三方的启动项。默认只处理 confidence=high 的。

选项:
  -y --yes              跳过确认
  --dry-run             只打印计划
  --remove              clean 改为"移除"（移入备份）而非仅禁用
  --confidence LEVEL    high|medium，默认 high。medium 那批会另列一块要求逐条确认
  --include-unknown     把"判不出来"的项也纳入。⚠️ 三道闸：措辞告警、
                        即使 -y 也要交互确认（除非再加 --i-know）、只允许禁用
  --i-know              配合 --include-unknown 免除二次确认
  --strict              把"跳过"也当作失败（脚本用）
  --sudo                系统级项交给 sudo 跑一次

注意:
  · **扫描不完整时拒绝运行**——绝不在残缺视图上做安全决定
  · 逐项计划永远先打印，-y 也打印；-y 的意思是我审过计划了，工具留收据
""",
    'proc': """
用法: startupctl proc [选项]

进程视图，并把进程关联回拉起它的启动项（关联是**尽力而为**，不是地面真相）。

选项:
  --third-party   只看第三方
  --system        只看系统
  --orphans       只看**没有对应启动项**的三方进程——"有人手工把它启起来了"那批
  --json          机器可读输出
""",
    'kill': """
用法: startupctl kill <pid|项> [选项]

结束进程。默认先 TERM（给它机会收尾），--force 才 KILL。
白名单中的进程会被拒绝。

⚠️ 绝不使用 sudo：结束 root 进程会被拒绝并提示，而不是偷偷提权。
""",
    'whitelist': """
用法: startupctl whitelist <add|remove|list|doctor|prune>

  add <项>       加入白名单（默认按稳定 id 匹配）
  remove <项>    移出白名单（或 --all-unmatched）
  list           列出条目
  doctor         报出本次扫描**一条都没命中**的条目
  prune          清掉未命中的条目

add 的选项:
  --glob P        按锚点通配匹配，如 homebrew.mxcl.*（用 fnmatch，不用正则）
  --vendor V      按厂商前缀匹配，如 com.docker
  --exec-prefix P 按可执行路径前缀匹配
  --pin           钉住当前载荷指纹：命令被换掉就撤销豁免
  --reason R      备注（会存下来供日后审计）

不变量: 白名单只能**收窄**破坏性集合。它只让 clean 少动几项，
        绝不会让一个系统项变得可改——这条有专门的测试。
""",
    'guard': """
用法: startupctl guard <status|mode|pick|list|add|remove|clear|check|arm>

进程守护：按策略结束不该跑的进程。三种模式：

  off         不干预，只报告（**默认**）
  deny_all    全部拒绝：除系统基础进程外一律结束
  blacklist   黑名单：只结束挑中的那些，其余放行
  whitelist   白名单：只放行挑中的那些，其余结束

★ **三种模式一律保留系统基础进程**——没有任何一个模式能杀掉它们。
  「全部拒绝」不是"什么都杀"。这条规则实现于决策函数里**先于模式判断**的一道硬闸，
  所以将来新增模式也会自动继承它，而不是各模式各自记得写一遍。

★ **「全部拒绝」也绝不含你自己**：shell · 终端 · 会话（zsh/bash/iTerm/Terminal/
  tmux/sshd…）一律受保护，否则第一次 arm 下去你就没法敲命令把它关掉了。

**模式与选择是分开的两件事:**

  mode     选策略模式。只决定"用哪一份清单"，**不改动清单内容**。
  choose   打开选择器，往**当前模式对应的那份清单**里填。
           这是**唯一会启动图形窗口**的命令（GUI 不是常态，
           日常命令突然弹窗既唐突又会挡住脚本化使用）。

  ★ 白名单与黑名单是**两份互相独立的清单**。以前是一份、含义随模式解释，
    那样切模式会把刚在白名单里挑的东西立刻变成"要杀"；现在切模式只是换用哪一份，
    两份内容都原样留着。

  status          看模式、两份清单、实时统计与"能不能执行"
  mode [M]        看/设模式（off|deny_all|blacklist|whitelist）
  mode choose     等价于 choose
  choose          打开选择器（图形窗口；无图形环境时退到终端界面/纯文本并说明原因）
                  --tui 强制终端界面 · --plain 强制纯文本
                  三个界面共用同一份"能不能选"的规则：**系统基础进程与已锁定条目
                  都真的选不动**，不是只显示成灰的。
  list            分别列两份清单（标出当前模式在用哪一份）
  add <名称|pid>  加一条；--whitelist/--blacklist 指定加进哪份（默认当前模式的）
  remove <值>     移除一条；--all 只清当前模式那份
  lock <值>       锁定：**任何模式下都不结束它**，选择器里也选不动（跨两份清单）
  unlock <值>     解除锁定
  check           只读：现在会结束哪些（退出 0 = 无事可做，1 = 有）
  arm             执行一轮；--watch 持续监视新起的进程（Ctrl-C 停）

★ 「只有选择的时候才生效」: 起作用的那份清单是空的就**不许执行**——
  白名单为空时它等于"除系统外全杀"，用户什么都没选，工具不该按最激进的解释动手。
  空清单下 arm 会被拒绝（退出 3）并指路到 guard choose。

锁定 vs 普通条目: 普通条目只在**它所在的那份清单被模式选中时**才起作用；
  锁定条目的含义**与模式无关**——一律"别动它"，且跨两份清单都生效。

选项:
  --match M       proc_name（默认）| exec_path | exec_prefix
  --value V       显式指定匹配值（默认从进程推断）
  --reason R      备注
  --watch         持续监视（配合 --interval、--rounds）
  --tui           强制终端界面（curses）
  --plain         强制纯文本选择器（编号清单，管道/脚本里用）
  -y --yes        跳过确认
  --dry-run       只预览，绝不结束任何进程

注意:
  · 任何改动都会**写盘后重新读回来核对**，不一致就报错退出——不许"看起来成了、
    其实没生效"
  · 默认 `off`——装上不会自己开始杀进程，必须显式选模式再 arm
  · 绝不使用 sudo；root/他人的进程会被跳过并提示
  · 本工具自身的进程链永不结束（否则等于锯自己脚下的地板）
  · 「全部拒绝」会连**你自己刚敲的命令**一起拒绝，这是它的设计意图，用前请知悉
""",
    'update': """
用法: startupctl update [--check]

拉取最新源码快照并重装（镜像优先，回退 GitHub）。

  --check   只比对版本，不落盘
""",
    'install': """
用法: startupctl install

显示安装方式（本工具装到 devtools 目录，与 jtool / ptool 同规）。
""",
    'uninstall': """
用法: startupctl uninstall [-y]

卸载安装副本并摘除 shell 接线。
**白名单与备份一律保留**——备份是 restore 的唯一来源，白名单是用户逐条确认过的。
""",
    'config': """
用法: startupctl config

显示运行信息：版本 · 平台 · 数据目录与占用 · 白名单条目数 · 备份数 · 配置文件路径。
""",
    'help': """
用法: startupctl help

显示本帮助。
""",
}


def sub_help(name):
    text = SUB_HELP.get(name)
    if not text:
        return None
    return text.strip('\n') + '\n'


def help_lines():
    """HELP 的行数（冒烟测试断言 <= 50）。"""
    return len(HELP.splitlines())


def align_report():
    """复算各分节的对齐，返回 [(section, lineno, 问题)]。

    测试用它而不是信任字面量：手改数据表导致某一节描述列不齐时，CI 会挂。
    分节内描述列的起始位置必须一致（按显示宽度算，CJK 计 2）。
    """
    problems = []
    section = None
    col = None
    for i, line in enumerate(HELP.splitlines(), 1):
        s = line.rstrip()
        if not s:
            section, col = None, None
            continue
        if s.endswith(':') and not s.startswith(' '):
            section, col = s[:-1], None
            continue
        if section not in ('用法', '子命令', '选项', '示例'):
            continue
        if not s.startswith('  '):
            continue
        body = s[2:]
        # 描述列 = 第一段连续两个以上空格的**结束**位置
        start = None
        for j in range(len(body) - 1):
            if body[j] == ' ' and body[j + 1] == ' ':
                start = j
                break
        if start is None:
            continue
        end = start
        while end < len(body) and body[end] == ' ':
            end += 1
        got = dw(body[:end])
        if col is None:
            col = got
        elif got != col:
            problems.append((section, i, '描述列在第 %d 列，本节应为第 %d 列' % (got, col)))
    return problems
