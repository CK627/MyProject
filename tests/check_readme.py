# -*- coding: utf-8 -*-
r"""体检：README 必须含 devtool 系列的**骨架章节**。

系列以 ptool 的 README 为基准，13 个顶级章节是这套文档的招牌：
  安装 卸载 功能特性 使用方法 命令速查表 Tab 补全 配置文件
  跨平台支持 在脚本中使用 项目结构 常见问题 开发与测试 许可证

只要求"**至少包含**"——各项目可以有自己的额外章节（CtfSweep 的「支持的输入格式」、
startupctl 的「进程守护」、jtool 的「版本号说明」都是合理的）。缺任何一个都算漂了。

⚠️ 用 Python 而不是 grep：BSD grep 的转义坑本项目踩过（一条 `grep -E '[^\\x00-\\x7f]'`
   的检查曾因 `\xNN` 不被支持而以 rc=2 退出，又被 `if grep` 当成"没匹配"，
   于是永远报 ok）。检查器自己出错必须能被看见。
"""
import re
import sys

CANON = ['安装', '卸载', '功能特性', '使用方法', '命令速查表', 'Tab 补全',
         '配置文件', '跨平台支持', '在脚本中使用', '项目结构', '常见问题',
         '开发与测试', '许可证']


def main(argv):
    path = argv[0] if argv else 'README.md'
    try:
        text = open(path, encoding='utf-8').read()
    except OSError as e:
        print('读不到 %s: %s' % (path, e))
        return 2
    have = [m.group(1).strip() for m in re.finditer(r'^## (.+)$', text, re.M)]
    missing = [s for s in CANON if s not in have]
    if missing:
        print('README 缺骨架章节: %s' % '、'.join(missing))
        print('  现有章节: %s' % '、'.join(have))
        return 1
    print('README 骨架章节齐备（%d 个）' % len(CANON))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
