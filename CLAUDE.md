# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

ctfsweep 是面向 CTF / 应急响应的取证扫描 CLI：把 pcap/pcapng、evtx、.reg/任意文本、
内存镜像、浏览器数据库、邮件、日志、数据库导出等输入里的"可疑线索"一次性翻出来，
按**置信度分级**输出（高置信可直接核验 / 中低置信留作人工排查）。

三条硬约束（改任何代码前先记住）：

1. **零第三方依赖**：纯标准库、Python 3.8+。`pyproject.toml` 的 `dependencies = []`。
2. **安装副本，不是源码直跑**：与同仓库的 jtool / ptool 同规——代码装成 devtools 副本
   （`~/.devtools/ctfsweep`，sudo 则 `/Library/devtools/ctfsweep`），启动器实体在
   `<根>/lib/ctfsweep.sh`，PATH 上只有 `<根>/bin/ctfsweep`（无后缀软链，指向 `../lib/ctfsweep.sh`）。
   仓库 `bin/` 是**素材目录**（`ctfsweep.sh` + `ctfsweep.bat` 靠扩展名区分系统），
   **绝不能整体进 PATH**：zsh 命令名补全走 `$commands` 哈希、不检查可执行位，`.bat` 会跟着
   进候选（这正是本次改造的起因）。`ctfsweep update` 是**真更新**（镜像优先 + GitHub 回退）。
3. **文档/输出/注释/提交信息全部中文**。报告标题（`【高置信（可直接核验）】`）、
   CLI 帮助、findings 的 `kind` 字段都是中文字面量，测试直接断言这些字符串——
   改文案等于改测试，见下文「改文案前必看」。

## 常用命令

```bash
# 跑工具（三种等价方式）
ctfsweep -f capture.pcap       # 已安装：PATH 上唯一的无后缀软链（命令名只有这一个，无别名）
python3 -m ctfsweep <文件或目录> [选项]
./bin/ctfsweep.sh <文件或目录> [选项]   # 仓库启动器（macOS / Linux；.bat 是 Windows 版）
                               # ⚠️ 别把仓库 bin/ 加进 PATH（见「项目概览」第 2 条）

# 安装 / 更新 / 卸载（改完安装逻辑必跑：tests/smoke.sh 第 5、7 步守着布局契约与真更新）
sudo bash installer/install.sh     # 本机落地；用户级去掉 sudo（installer/install.sh 亦可）
ctfsweep update [--check]
ctfsweep clear [名称] [-y]        # 清空数据目录（给名称只清那个项目；唯一主动删数据的命令）

# 完整冒烟（语法门 + 单元冒烟 + shell 语法 + 启动器 + 安装/布局契约 + 引导模式 + 真更新）
bash tests/smoke.sh

# 只跑 Python 冒烟（快，日常用这个）
python3 tests/test_smoke.py

# 生成确定性测试样例（pcap/pcapng/evtx/内嵌 zip/AD 域流量/USB/TLS/主机表）
python3 tests/gen_fixtures.py /tmp/fixtures

# 特征化回归（16 个基线逐字节比对；不进 CI，重构期手工跑）
python3 tests/test_golden.py            # 比对
python3 tests/test_golden.py --record   # 重录（重录前逐行核对 diff！）

# 离线训练判断核（运行时不提供训练入口，只有这条脚本）
python3 lab/train.py --data lab/dataset.jsonl --out models/model.ctfj
```

**单个测试怎么跑**：`tests/test_smoke.py` 是一条线性脚本，没有 pytest/测试发现机制。
断言走 `check(cond, msg)`，失败只累加到 `FAILS` 并在末尾统一打印。
要隔离调试某一节（如 `check_judge(tmp)`），在临时目录里 `gen_fixtures.generate(tmp)`
后再调用该节的函数即可。定位失败项用 `python3 tests/test_smoke.py 2>&1 | grep FAIL`。
`check_judge` 走 `subprocess` 跑 `lab/train.py`（那是它唯一的训练入口），
`check_scan_cache` 断言两种模式的缓存内容一致、且数据根下没有 `judge/`；
`check_dir_scan_cache` 守目录扫描的「一次运行一个目录」（含逐行 `← 相对路径` 归属）。

**测试必须隔离数据目录**，否则会污染真实缓存（`main()` 用 `try/finally` 设置）：

```bash
CTFSWEEP_DATA_DIR=/tmp/csdata CTFSWEEP_MODELS_DIR=/tmp/csmodels python3 tests/test_smoke.py
```

CI（`.github/workflows/ci.yml`）在 ubuntu 上用 **Python 3.8 / 3.11 / 3.13** 跑同一套
`bash tests/smoke.sh`——最低版本承诺不能漂移（不用 3.9+ 语法：dict `|` 合并、`match`、
内置泛型 `list[int]` 等都会在 3.8 上炸）。

## 架构

### 单文件扫描：一条管线、两个阶段

`cli.main()` 对每个文件：`CaptureContext(data)` **解析一次**（`core/capture.py`，缓存
`l4`/`tcp_streams`/`udp_payloads`/`stream_blobs()`），再交给 `core/router.py` 的 `Router`
按顺序跑两个阶段。**阶段次序是契约**——`tests/test_smoke.py` 断言 `【dns】` 出现在 `格式:`
之前，因为阶段二的过程输出（`格式:`/`【主机表】`/`【AD / 域渗透线索】`/`[交互会话]`/`[邮件会话]`/`[提取]`）
由模块自己 print，与分带报告交错，无法事后重排：

1. **`run_filetype()`** — `match_module()` 按扩展名（`_TYPE_MAP`）+ 文件头特征
   （`_CONTENT_SIGNS`）选模块 → `importlib.import_module("ctfsweep.core.<名>")`
   → `analyze(filepath, ctx=ctx)` → `AnalysisResult`（内含 `Finding`），渲染成
   一行行 `【<模块名>】` 块。这些 `Finding` 同时喂 `core/meta_judge.py` 的 `MetaJudge`。
2. **`run_stream()`** — `_STREAM_MODULE`（`scanner`）**每个文件都跑**：抓包走
   `scan_capture()`、其余走 `scan_rawfile()`。它的输出进 `core/report.py` 的分带报告。
   `ad` 是 `role="sub"` 的亚模块，**不顶层分派**，由 `scan_capture()` 内部驱动——
   这样它的 findings 才是 `module="scanner"`，`print_ad_info()` 才落在 `[交互会话]` 之前。

`_MODULE_ROLE`（`scanner`=stream / `ad`=sub / 其余=filetype）决定谁在哪个阶段跑。
**只有抓包**的 stream findings 进 `MetaJudge`（`ctx.is_capture` 把关）——非抓包走
`scan_rawfile`，它的候选只进分带报告，放开会让每个 `.evtx`/`.txt`/`.mem` 凭空多出一个
`【元判断核综合评分】` 块。

⚠️ **异常口径不对称**：阶段一(`run_filetype`) 的失败是静默的（`try/except: pass`），
只表现为"这个模块这次没输出"；阶段二失败由 CLI 打 `扫描出错: %r` 并 `continue` 跳过该文件。
调试"某模块没输出"时先手写 `importlib.import_module` 确认能否导入、有无 `analyze`/`scan`。

⚠️ **`_dispatch()` 按形参表传参**（`inspect.signature`）：只有声明了 `ctx`/`opts` 的模块才
收得到它们（`scanner`/`ad` 收两个，`dns` 收 `ctx`，其余 7 个仍是 `analyze(filepath)`）。
给新模块加 `analyze()` 时**不需要**跟着加 `ctx` 形参；反之若给模块加了 `ctx` 却忘了用，
不会有任何提示。历史上这里无条件传 `ctx=`，7 个模块集体 `TypeError` 被静默吞掉——
`tests/test_smoke.py::check_router_dispatch()` 专门守这条（形参匹配 + 端到端出块）。

MetaJudge 按 `MODULE_WEIGHTS`（ad 0.95 / memory 0.90 / config 0.85 … scanner 0.65）聚合。
**评分是单调不降的**：模块自报的 confidence 是**下界**，`MetaJudge.score()` 只会往上加
（权重高出中性点 0.65 的部分给先验加成、命中关键词 +0.05），加成封顶 0.95；
`MODULE_RULES` 的规则分同样只作**下限**抬高，不覆盖模块自评。改这几个数就是改评分语义，
`tests/test_smoke.py::check_meta_judge()` 会断言"综合分 ≥ 模块自评"这条不变式。
分档阈值统一走 `core/utils.py` 的 `BAND_HIGH`(0.85) / `BAND_MID`(0.55) 与 `level_of()`，
报告渲染、`【<模块名>】` 块、元判断核三处都调它，**不要在别处重写阈值**。

### findings 数据契约（改扫描逻辑的核心）

两条并存的表示，**边界在 `scanner.analyze()`**，转换只能发生在那里：

- **`Finding`**（`core/router.py`）是跨模块的统一货币，也是 MetaJudge 的输入。
  `Finding.to_tuple()` **原样回吐** `tok`/`val`（bytes 就是 bytes，**不解码**）；
  `confidence` 存**不 round 的原始值**（只有 `to_dict()` 才 round）。
- **5 元组** `(score, kind, tok, val, loc)` 是 `blobscan`/`decode`/`extract`/`http`/`session`
  及渲染层 `report()`、`judge.predict_finding` 的局部 ABI。CLI 持 `Finding`，需要时
  `[f.to_tuple() for f in findings]`。`report()` 对 `val` 用 **utf-8**、对 `tok` 用
  **latin-1** 解码——提前解码会静默改掉非 UTF-8 的 token。

`kind` 是中文类型标签（如 `'明文flag'`/`'片段(前)'`/`'NetNTLM'`），`val` 是值
（`bytes` 或 `str`），`loc` 是位置说明。

所有新增都经 `core/blobscan.py` 的 `add(finding, findings, seen)` 入库，
**去重键按 kind 分支**（解码/片段按内容、关键词按文本、flag 按值、上下文类跨视图合并）。
新增一种 finding 时要在这里决定去重键，否则会重复刷屏或误合并。

置信度分级由 `core/utils.py` 的 `level_of()` 决定：`>=0.85` 高 / `>=0.55` 中 / 其余 低。
分数含义表在 `cli.HELP` 和 README 里同步维护（0.97 明文 flag → 0.40 关键词上下文）。

### 噪音闸门（改扫描逻辑时先看这里）

判定标准是**"这条输出对解题有没有引导价值"**，不是"看起来像不像可疑"。已经落地的二十条：

- **二进制容器先抽字符串**（`core/logs.py::_extract_strings`）：`.evtx` 这类容器不能按字节
  当文本读——`\x60` 之类的字节巧合会被喂给攻击正则，刷出满屏「RCE（命令替换）」，
  证据本身就是乱码。现在按 **UTF-16LE 两种对齐**（EVTX 里的字符串常相对文件头错位 1 字节，
  即 `\x00f\x00l\x00a\x00g`）+ ASCII 抽可读片段后再分析。
- **常规域名折叠**（`core/utils.py::dns_lead_reason` + `scanner.py` 的 DNS 循环）：只逐条列出
  **结构异常**的查询名（超长标签 / DGA 主机名 / 动态 DNS / 滥用高发 TLD / WPAD·`_msdcs`
  等服务发现），其余折叠成一行。判据刻意**不是**"厂商域名白名单"——那盖不住中文流量
  （qq.com、g-fox.cn 一条都不匹配），而中文 CDN/门户的常规查询会把真线索挤出屏幕。
  `KNOWN_INFRA_SUFFIXES`（厂商遥测/CDN，含国内 CDN）只用于**豁免随机主机名判定**
  （`d15krst4gi8g86.cloudfront.net` 是正常的），`dns.py` 与 `dns_lead_reason` 共用这一份名单。
  ⚠️ 折叠行的分数必须 `>= cli` 的 `MIN_SCORE` 默认值（0.40），否则会被静默滤掉——
  折叠是"少占屏"，不是"隐瞒"。
- **服务发现类查询单独归组、折叠成一行按域名计数**（`scanner.py` 的 `dns_discovery` +
  `utils.base_domain`；判据是 `dns_lead_reason` 返回常量 `SERVICE_DISCOVERY_REASON`）：
  SRV `_ldap._tcp`/`_msdcs`/`_sites` 与 `wpad.` 在**每个** Windows 域环境里都成片出现，
  名字里只有域内拓扑。实测 `2024-09-04` 那道域渗透题，DNS 段逐条列出 6 条
  `_ldap._tcp…（服务发现/投毒相关查询）`——而该题四个答案（主机名 `DESKTOP-RNVO9AT` /
  IP / MAC / 账号 `afletcher`）**与域名一个字都不沾**，这 6 行对解题零引导。
  ⚠️ **折叠的边界是不埋线索**：域外域名的 SRV 查询（`_ldap._tcp.pdc._msdcs.enemywatch.net`）
  是有效线索，所以那一行按**域名归组**——出现域外域名时计数立刻变成「涉及 2 个域: …」
  并改口提示"域外域名的 SRV 查询值得追"，只有全是本域时才说"与答案无关"。
  `dns_lead_reason` 对这类名字仍返回非 None（`test_smoke` 断言着），改变的是**渲染**。
  ⚠️ **"超长标签"不能只看长度**：`mail.pisosyrecubrimientos.com` 的 20 字符标签是西语单词
  （pisos y recubrimientos）。判据走 `_encoded_label()`——带数字 / 大小写混排 / 几乎无元音，
  三者都不占的长标签是词，不是编码外带。`dns_lead_reason` 因此**保留原串大小写**做这一步
  （`lower()` 之后就分不出 base64 了）。
  ⚠️ **两类 AD 常态名词必须豁免**（都来自 `2024-09-04` 那道域渗透题）：
  ① `_` 前缀的 SRV 定位名（`_ldap._tcp.Default-First-Site-Name._sites.dc._msdcs...`，74 字符）
  在 `dns_lead_reason` 里**先于长度判定**返回"服务发现/投毒相关查询"——不先挡就会被
  「域名超长」误报成外带隧道；`_encoded_label` 另加"连字符分词的短语"豁免，
  否则 `Default-First-Site-Name`（22 字符驼峰）会被判成 base64。
  ② Windows 自动生成的机器名（`DESKTOP-RNVO9AT` / `WIN-CTL9XBQ9Y19`）走
  `_WIN_MACHINE_RE` 跳过 DGA 判定——尾串本就是系统随机分配的。
  `dns.py` 的「高频查询域名」与「DGA 域名」两个循环也过 `utils.is_service_discovery()`，
  否则 `wpad.bepositive.com`（20 次）会靠"查询最多"坐上【dns】块与【前 10 项发现】第一名。
- **同一证据不占满"前 10 项发现"**（`meta_judge.MetaJudge.get_top_findings`）：FTP 爆破的 11 次
  登录会产出 11 条一模一样的"成功凭据"，按分数排序后把前 10 项全部占满，其余线索一条都看不见
  （实测 FTP-malware.pcap 正是如此）。前 N 项按 `(kind, 证据)` 去重；`get_summary` 与分带报告
  仍按原始条数如实计数——**去重只作用于"前 N 项"这个展示位**。
- **邮件会话聚合、加密要如实说**（`core/session.py::_analyze_mail`）：23 条 SMTP 会话之间只有
  服务器 IP 不同，逐条列出就是刷屏。聚合成一段报会话数 / 客户端自报主机名（HELO/EHLO，
  僵尸网络题的关键指纹）/ 信封 / 其中多少条被 `STARTTLS` 加密。正文加密时**必须写明
  "内容不可解读"**——否则 10 MB 的 spambot 抓包会看起来"什么都没扫到"，而会话形态恰恰是
  那种题唯一可用的引导（实测修复前只有 3 条低置信 DNS 输出）。
- **明文投递信封：多就报形态，少才逐封列**（`core/session.py` 的 `_MAIL_LIST_MAX=8`）：
  信封是**最没有 IOC**的部分，逐封列出在群发题上是灾难。实测
  `extracting-objects-from-pcap-example-04.pcap` 有 113 条 SMTP 会话，旧版产出 **212 行**
  `[邮件投递]`（占全文 273 行的 78%），78 条 finding 里 **76 条**是这个 kind，
  把【前 10 项发现】10 个席位**全部**占满——而那道题（题名就是
  "extracting objects from pcap"）真正要找的是抓包里的被提取文件，一行都没露出来。
  而且那 113 封本身没有可用线索：发件域 46 个（`6374.com` / `5395.com`…）、收件人清一色
  `@yahoo.com`——前者是随机化伪造、后者是受害者。所以 `> 8 封` 时只报**形态**
  （`发件域 46 个: …；收件域 3 个: …` + 3 个样例 + 折叠行），且在发件域数 == 信封数时
  直接点名"每封都不同 = 随机化伪造，不是可用 IOC"——**把"这里没有 IOC"说出来才是引导**，
  逐封罗列反而让人以为捡到了 113 个线索。`≤ 8 封`（如 `t11-smtp.pcap` 的 4 封）保持原有的
  逐封列出与 finding 定位（`@SMTP src:port→dst:port`），14 个 golden 逐字节不变。
  ⚠️ **折叠形态另起一个 kind 且只给 0.55 中**（`邮件投递形态`，逐封形态仍是
  `邮件投递信封` 0.85 高）：一条"76 封"的聚合**不是"可直接核验"的答案**，它和
  `邮件会话` 一样是形态结论。给它 0.85 会让它坐上【前 10 项发现】第一席并谎称
  "可直接提交"——实测 ex04 正是如此，而那道题里没有哪一封邮件是关键邮件
  （该 pcap 里 `Content-Type`/`filename=`/`PK`/`PDF`/`JPEG` 一个都没有，
  76 封信封就是全部，不存在被漏掉的可提取对象）。
  `tests/test_smoke.py::check_mail_envelope_gate()` 两头都守着。
- **二进制上下文只留最长可读片段**（`core/utils.py::readable_window`，调用点在
  `scanner.py::scan_rawfile.push`）：`isprintable()` **拦不住**二进制按 UTF-16 解码出的乱码——
  `Ā`(U+0100) `Ѐ`(U+0400) `ఀ`(U+0C00) `ᄀ`(U+1100) `⨀`(U+2A00) 全是 printable。实测
  `Security.evtx` 的 9 条 `关键词[flag]` 命中，有效线索只在开头约 30 字节，尾巴几十字符是乱码：
  零信息量，还把 4 个 flag 片段挤出可视范围。规则是**按码位白名单切段取最长一段**（ASCII +
  Latin-1 + 通用标点 + 箭头 + CJK + 谚文 + 全角），整串干净则**原样返回**（短凭据
  `PWD=/AstrBot` 也得留），切段后短于 16 字符则丢弃该命中。净化放在**源头**（val 干净了，
  下游 `report()` 与 MetaJudge 证据行自动干净）。⚠️ **不做首尾裁剪**——填充点号是既有约定，
  golden 基线逐字断言着它。
- **证据行必须单行渲染**（`core/meta_judge.py::print_report`）：含换行的证据（命令回显整段
  输出、多行响应体）要压成一行再打印。实测 `challenge.pcap` 的一条 `cmd=ls` 回显撑开 14 行，
  前 10 项里其余 9 条线索全被顶出屏幕。只在**确实含换行**时压，单行证据（含制表符）逐字节不动。
- **证据必须是可读文本，不能是 bytes 的 repr**（`core/router.py::evidence_text`，
  `Finding.to_meta_dict`/`from_tuple` 共用）：`str(b'\xe6\x9c\x8d\xe5\x8a\xa1')` 得到的是
  `b'\xe6\x9c\x8d...'` 这样的转义串，元判断核的"证据"行满屏反斜杠读不了。实测 AD 那道题
  前 10 项全部退化成 `b'TGS-REP \xe6\x9c\x8d...'`——而这一行正是"解不出答案也要给出的
  关键信息引导"。改成 `val.decode('utf-8', 'replace')`，与 `report()` 对 `val` 的口径一致；
  **`tok` 仍走 latin-1 且只给 `report()` 用，不在此处解码**（见 `Finding` 的两条约定）。
- **`exec(`/`execute(` 不能单独当 SQL 注入判据**（`core/logs.py::ATTACK_PATTERNS`）：
  .NET/Java 的栈帧里满地都是 `System.Web.HttpApplication.IExecutionStep.Execute()`，
  实测 `Application.evtx` 因此报出 `[高 0.95] SQL 注入`——0.95 是"可直接核验"档，
  误报代价最高。现在要求真正的 SQL 语境（`union select` / `exec(@sql)` / `exec('…')`
  / `sp_executesql` / `exec xp_cmdshell` / `xp_cmdshell '…'`）。
  ⚠️ `xp_cmdshell` **光看名字也不行**：装了 SQL Server 的主机，Application.evtx 的
  perflib 计数器里就有一个光秃秃的 `xp_cmdshell` 字符串，要求 exec 上下文或调用括号。
- **WMI/WQL 查询行整行剔除**（`core/logs.py::_is_wmi_query`，在 `_detect_and_analyze`
  派发前过滤）：Windows 的 WMI 提供程序用**类 SQL 语法**查询
  （`Start IWbemServices::ExecQuery - ROOT\CIMV2 : SELECT * FROM Win32_Account ...`），
  在 `select … from` 这条 SQLi 正则上整片命中。实测 `日志排查` 那道题的 Application.evtx
  产出 **15 条 `[高 0.95] 攻击检测: SQL 注入`**，把【前 10 项发现】占掉 8 席——真正要看的
  flag 线索被压在下面，是最难排查的那种噪音（误报越"可信"，伤害越大）。
  判据要求**两个条件同时成立**：出现 WMI 调用标记（`IWbemServices`/`ExecQuery`/`wmic`）
  **且**出现 WMI 类名或 SQL 关键字——只看类名会误伤"提到 `Win32_Process` 的普通日志行"。
  按行剔除，同一份内容里的真 SQLi 不受影响（`check_logs_wmi_gate()` 端到端守着）。
- **HTTP 请求必须记下 `Host` 头**（`core/http.py::http_summary` + `scanner.py` 的
  `[HTTP服务端]` 块）：请求行里只有**裸路径**，主机名在 `Host` 头里。实测 2021-09-10 那道题
  （BazarLoader 投递）48 条请求全是 `/bmdff/...`，投递域名 `simpsonsavingss.com` 与投递 IP
  在报告里一个字都不出现——而答案要的正是这两个 IOC。`http_reqs` 条目因此是 5 元组
  `(ts, method, uri, host, peer_ip)`，请求列表按 `host+uri` 渲染，另出
  `[HTTP服务端]（Host → IP ×请求数）` 汇总块。
- **从 TLS ClientHello 抽 SNI**（`core/scanner.py::tls_sni` + `[TLS SNI]` 块）：HTTPS 已是
  C2/投递的主要载体，正文全加密，**唯一留在明文的身份信息就是 SNI**。实测 2020-09-25
  那道题报告给出了受害主机/MAC/账号/投递的 `jojo.exe`，却给不出 `paste.nrecom.net` 与
  `37.120.174.218`。纯字节游走（record `0x16 0x03` → 握手类型 `0x01` → 跳过
  4+2+32 / session_id / cipher_suites / compression → 扩展里找 `0x0000`），不做解密。
  ⚠️ 排序必须把 `under_known_infra()` 命中的放**后面**——一台普通 Windows 主机的 SNI
  列表 90% 是 Microsoft/Edge/Teams 遥测，不排会把真 C2 域名挤出 15 条上限；
  `KNOWN_INFRA_SUFFIXES` 因此补了 `.msedge.net` / `.skype.com` / `.xboxlive.com` /
  `.trafficmanager.net` 等 HTTPS 服务后缀（同一份名单也让 DNS 折叠受益）。
- **域名块按域名聚合、不许截断、厂商折叠**（`[TLS SNI]` 与 `[HTTP服务端]` 两个块，
  `core/scanner.py`）：光有 SNI 提取还不够，**渲染方式会把答案毁掉**。实测
  `2025-01-22-traffic-analysis-exercise.pcap`（全 mta 语料里唯一一道问域名的题，
  答案是 `authenticatoor.org`）三条同时踩中：
  ① 旧版一行一个 `(域名, IP)`，`login.microsoftonline.com` 一台机器落 10 个 IP = **10 行**，
  15 个席位里 14 个是同一家的遥测；
  ② 旧版 `%-38s % sni[:38]` 把 41 字符的 `google-authenticator.burleson-appliance.net`
  印成 `google-authenticator.burleson-applianc`——**看起来像答案、照抄却核验不了，
  比不印更坏**；`[HTTP服务端]` 同病（`msedge.b.tlu.dl.delivery.mp.microsoft.`）；
  ③ 唯一的答案域名只被查询 1 次，落进"…（其余 108 个省略）"。
  现在是：按域名聚合成一行（`域名 → N 个 IP（…） ×次数`，`_ip_list()` 负责压 IP 列表）、
  **不截断**、非基础设施域名逐条列出（上限 20）、基础设施折叠成一行计数
  （`已知厂商/CDN N 个（遥测/CDN，通常不是答案）: …`）。改完这道题的 SNI 块
  第 2、3 行就是那两个答案域名。`KNOWN_INFRA_SUFFIXES` 同步补了
  `.microsoftonline.com` / `.microsoftapp.net` / `.sfx.ms` 与成片的广告/分析后缀
  （`.demdex.net` / `.doubleclick.net` / `.liveperson.net` / `.clarity.ms` / `.owneriq.net` …）
  ——`.microsoft.com` 盖不住 `login.microsoftonline.com`，那两条正是从"已知基础设施"
  漏进【前 10 项发现】第 2、3 席的。`tests/test_smoke.py::check_sni_render()` 守着。
- **同一条结论只留一条**（`core/blobscan.py::add` 的通用分支）：通用去重键**刻意不含
  `loc`**。历史上是 `(kind, v, loc)`，于是"同一结论在不同会话里各报一次"会全部活下来——
  实测 `dump.pcapng` 是 50 条 FTP 会话连同一台 vsftpd 2.3.4，`漏洞利用：笑脸后门
  （CVE-2011-2523）` 被逐字印了 **50 行**（只有端口不同），把要看的爆破口令序列顶出屏幕。
  同值即同结论；会话级差异由 `[FTP会话]`/`[交互会话]` 这类**块**按会话呈现，不该由
  findings 承担。同理 `session.py` 的 `⚠️ 检测到 vsftpd 后门` 按 `(服务器, 结论)` 只提示一次。
  ⚠️ 例外要各自守住（都**不是**噪音）：`明文flag` 同值跨视图合并、`DNS查询` 在循环内已按
  `dns_seen` 去重、`域账号`/`Kerberos票据` 在 `ad.py` 内已去重。改这个键必须重跑 golden。
- **加密请求体的乱码字段整条丢弃**（`core/utils.py::looks_like_text` +
  `core/http.py::_field_text_ok`）：AES 后的 App 流量按 utf-8 `'replace'` 解出来是整片乱码，
  `[POST字段摘录]` 会印出 `��)�;��=l?�]��b` 这种一个字都读不了的"字段"。实测
  `FLAG 消失之谜.pcap` 的 7 行摘录里 6 行如此。与 `readable_window` 分工：那是"从混合串里
  **切出**一段可读文本"（证据串用），这是"整串算不算文本"的是/否判定（整条丢弃用），
  共用同一份 `_text_ok` 码位白名单。**空值放行**——`password=` 为空本身就是爆破线索。
- **压缩包解开后必须说清里面是什么**（`core/archives.py::_scan_extracted`）：模块 docstring
  一直写着「最终文件扫描」，但 `analyze()` 解压完就把临时目录 `rmtree` 了。实测
  `SU_Artifact_Online.zip`（密码 password，1 KB）只报一句「ZIP 解压成功（密码: password）」
  + 建议「检查解压出的文件内容」，而包内是 3369 字节的**卢恩字母替换密码**文本——
  陌生题里"解开了却不说里面是什么"等于没解。现在报成员清单（名 + 体积）、扫成员里的
  flag、给文本成员一段正文摘录。四条配套约定：
  - **文本判定不能用 `utils.looks_like_text`**（`archives._text_of`）：它的码位白名单
    只放行 ASCII/Latin-1/CJK/谚文/全角，卢恩字母这类真脚本会被整串判成"乱码"丢掉——
    恰恰是最该看见的那类题。改判「严格 UTF-8 可解码 + 控制字符 <2%」。
  - **单块占比超 70% 时点名 Unicode 块**（`_script_hint`）：卢恩/欧甘/哥特/私用区
    （字体加密）/全角……认出区块就等于给出解法方向。
  - **递归解压产物不算成员**：`.pth`/`.docx` 解出的 `model/`、`word/` 是**容器内部结构**，
    判据是"第 1 层目录名 == 某个第 0 层文件的词干"。不折叠的话 `byteorder`（6 B）/
    `version`（2 B）会把 12 个列表名额与 6 个摘录名额吃光（实测 SU_theif）。
    摘录按「层级浅 → 同层体积大」发放，并有 32 B 下限。
  - **`bzImage` 先于 `MZ` 判定**：Linux 内核镜像开头是引导用 `MZ` 桩，会被认成
    「PE (Windows)」——kernel pwn 题的关键附件被判成 Windows 可执行文件，方向就带偏了。
    真标志是偏移 `0x202` 的 `HdrS`。递归解压成功的证据只留**成员名**，
    不留 `/var/folders/...` 临时路径。
- **账号字段为空时别硬拼分隔符**（`core/ad.py::scan_ad` 的 NTLM 分支）：NTLM Type-3
  的 `domain`/`user` 常为空（匿名认证、机器账户、报文被截断），旧代码无条件
  `'%s\\%s' % (domain, user)`，于是实测 `A.pcapng` 报出
  `NTLM 认证：\（主机 WIN7-1，未捕获 challenge）`——**整条线索的价值就是一个孤立反斜杠**，
  却照样占掉【前 10 项发现】一席。改成有账号才写 `域\账号`，没账号只报
  "这台主机发生了 NTLM 认证"（主机名仍是有效信息），两者都空则整条丢弃。
  ⚠️ 同文件 `_add_user()` 早有 `if u and u != '?'` 守卫，账号**列表**本来就是干净的——
  漏的只是这条拼串，改的时候别把两处搞混。
- **关键词必须是独立词，不能是词内子串**（`core/utils.py::kw_hit_bounded`）：解码链
  （`decode_chain`）、解码打分（`decode_score`）、DNS 子域解码（`scanner.py`）与元判断核
  的关键词加成，原来都写 `k.encode() in low` 这种**裸子串**判定。实测 `A.pcapng`：
  一段 SocksiPy 代理脚本 hex 解码出 Python 源码，里面的 `flags = args[:-1]`、
  `def recvfrom(self, bufsize, flags=0)` 让 `flags` 命中关键词 `flag`，于是产出 **3 条
  `hex` 线索**（证据是 Python 源码片段，两条还是词中间截断的），再靠关键词加成顶到 0.65，
  把【前 10 项发现】的第 3–5 席全占了。同一个判定还让 DGA 随机串里的 `c2`
  （`...c21va2ut...`）、URL 编码里的 `%2C2` 白拿 +0.05。
  判据与 `blobscan` 的 ASCII 通道共用 `kw_boundary_ok`；关键词自身以标点结尾
  （`flag{`）时右边界由标点保证，只看左边界（`myflag{x}` 不算）。
  ⚠️ 这条**会改分数**：`tests/golden/t1.pcap.txt` 两条与 `t12-web.pcap.txt` 一条各降 0.05
  （全是 `c2` 的误命中），已随改动重录——重录前逐行核对过，不是"改测试让它过"。
  `tests/test_smoke.py::check_kw_boundary_gate()` 端到端守着。
- **反向解析名不是域名，高频榜必须跳过**（`core/utils.py::is_reverse_dns` +
  `dns.py::_analyze_domain_stats`）：`1.10.168.192.in-addr.arpa` 是把 IP 倒着拼出来的
  PTR 名，IPv6 版（`….ip6.arpa`）必然有 32 个单字符标签、总长必然过 60。实测 `B.pcap`
  里 `1.10.168.192.in-addr.arpa` 被查了 **948 次**，稳坐「高频查询域名」第一名，
  还配上建议"检查该域名是否可疑（**可能是 C2 或 DGA**）"——把 IP 当域名报，还扣了顶
  最误导的帽子；同一榜的第 8、9 席是 `teredo.ipv6.microsoft.com`（微软隧道）与
  `ns1.mediatemple.net`，三条合起来把真正的 Web 攻击载荷挤出【前 10 项发现】。
  现在两处同时挡：① `dns_lead_reason` 开头就返回 `None`（IPv6 反向名不再被误报成
  "多段拼接外带"）；② 高频榜跳过反向解析名 + `under_known_infra()` 命中项。
  ⚠️ 建议文案同时**去掉了"C2 或 DGA"的断言**——`sunnystation.com` 是那道 AD 题的域，
  说成 C2 只会把解题人往反方向带；改成"确认是否为本环境已知域名（业务/AD）"。
  `tests/test_smoke.py::check_dns_highfreq_gate()` 守着（含"不误伤同名普通域名"
  `in-addr.arpa.example.com` 的反向断言）。
  ⚠️ 折叠行（`DNS查询（常规域名，已折叠）`）**不改**：它本来就只占一行、承认自己被折叠，
  把反向解析名列在里面是如实陈述，且 golden 逐字断言着那一行的形态。

### 输入解析层

`core/capture.py` 是纯 Python 的 pcap/pcapng 解析器（无 scapy/dpkt/Wireshark），
含链路层分派（Ethernet/VLAN/PPPoE/Raw-IP/Linux-SLL/SLL2/NULL）与
`merge_stream()`（按 TCP seq 重组，提取文件字节与 Wireshark 一致——这是有测试守着的
行为，见 `lab/analysis/case12`）。`core/extract.py` 负责文件雕刻、口令池、zip 假加密绕过。
`core/utils.py` 集中了所有共享正则（`FLAG_RE`/`JWT_RE`/`B64_RUN`/`HEX_RUN`/`SECRET_LINE_RE`）
与 `kw_boundary_ok()`（词内误报闸门：`FolderValueFlags`、`create_pdo_flag`、`msctf_`）。
DNS 相关的 `KNOWN_INFRA_SUFFIXES` / `dns_lead_reason` 也在这里（见上文「噪音闸门」）。

`core/paths.py` 是**数据目录布局的单点定义**（`data_root()` / `cache_root()`，
`CTFSWEEP_DATA_DIR` 的语义仍是"根"）——`cli.brief_cache_root()` 与测试都调它，
**不要在别处再拼一遍 `cache` 路径或另写一份数据根解析**。
（目录名的运行标识由 `cli.run_identity()` / `run_cache_dir()` 决定，见下文「缓存」那条。）

⚠️ **`merge_stream()` 的缓冲区按"序号跨度"分配，跨度必须先过合理性闸门**：
同一个客户端临时端口被多条连接复用（或序号被伪造）时，几个互不相干的 ISN 会被按
4 元组聚合到一起，序号之间根本没有可比性。实测 spambot.pcap：7 条"流"各有 3 个包、
18 字节载荷，序号却横跨 3.5 GB ⇒ 旧实现每条流分配 256 MB 零缓冲，10 MB 的抓包吃
**2.1 GB 内存、跑 250 秒**。现在的判据是 `span > max(4 MB, 载荷总量 × 64)` 就退回
"按包序直接拼接"——序号可比的流跨度 ≈ 去重后的字节数，丢包空洞只占零头，不会误伤
（`tests/test_smoke.py::check_stream_merge()` 守着：正常合并 / last-wins / 巨跨度退化 /
小空洞补零四种情形）。

### 判断核（本地 MLP，**运行时只推理**）

`core/judge.py`：140 维特征的手写 MLP 集成（5 种子）+ 二进制 `.ctfj` 格式
（`core/model_io.py`）。**自学习闭环已整体移除**——运行时没有任何训练/标注入口：

```
离线（仓库内，不随安装提供）           运行时装机后
  lab/build_dataset.py  → lab/dataset.jsonl
  lab/data_generator.py → 合成样本      ctfsweep <文件> --judge
  lab/train.py          → models/model.ctfj   →  p= 分 + 【判断核·重点候选】
```

- **模型与超参数随版本发布**：`models/model.ctfj` + `models/train_config.json`
  （改网络结构/学习率/种子改 JSON，不改代码）。⚠️ `models_dir()` 走 `judge.project_dir()`，
  而后者是 `judge.py` 上溯三级目录——**安装态下解析成 `<安装根>/lib/models`**，所以
  `deploy.sh` 必须把 `models/` 一起装（不装则 `--judge` **静默**显示「未训练」，不报错；
  `tests/smoke.sh` 第 5 步断言 `lib/models/model.ctfj` 存在）。
- ⚠️ **`judge.py` 的删除边界由 `model_io` 反向约束**：`core/model_io.py` 要
  `judge.FEATURES / JudgeNet / JudgePredictor / param_count` 才能把 `.ctfj` 还原成网络，
  这些**一个都不能删**；`JudgeNet.train()` 也要留着（`lab/train.py` 靠它）。删掉的是数据
  生命周期那一半：`record_scan`/留存区/`save_pending`/`mark_answers`/`learning_loop` 等。
- **数据目录只有一个语义：扫描缓存**。`~/.devtools/ctfsweep/cache/<运行名>-<短哈希>/`
  （一次运行一个目录；布局单点在 `core/paths.py`），**永不自动删除**——`update` 与
  `uninstall` 都只覆盖功能项
  （`bin lib completions config VERSION uninstall deploy.sh shell-setup.sh`），
  **永不 `rm -rf <安装根>`**；`tests/smoke.sh` 7.4/7.6 各埋一个
  `cache/sentinel-abc123/1.txt` 哨兵守着这条契约。
- 环境变量可覆盖路径（测试与实验靠这些隔离）：`CTFSWEEP_DATA_DIR`、`CTFSWEEP_MODELS_DIR`、
  `CTFSWEEP_TRAIN_CONFIG`、`CTFSWEEP_JUDGE_MODEL`、`CTFSWEEP_CONF`、`CTFSWEEP_MIRROR`、
  `CTFSWEEP_GITHUB`（`none` = 只认镜像，离线验证失败路径用）、`CTFSWEEP_GITHUB_TARBALL`。
  安装层级另有两个（见「硬约束」第 2 条）：`CTFSWEEP_USER=1` 装用户级、`CTFSWEEP_DEVROOT=<dir>`
  显式指定 devtools 根（优先级最高，只给测试用）。
  ⚠️ **冒烟里凡是真落盘的安装/更新都显式带 `CTFSWEEP_USER=1`**：默认是系统级
  （`/Library/devtools`，Linux `/usr/local/devtools`），CI 既没有 tty 也没有免密 sudo，
  跑默认路径会卡在密码提示上。默认层级的正确性由 `install-from-source.sh print-install-dir`
  守（只问不装），`tests/smoke.sh` 第 5 步断言。

🚨 **负样本必须来自同题语境**。`lab/analysis/README.md` 记录了受控实验：把"真实恶意流量"
（无 flag）题目的高分候选当负样本灌进训练集，留一组评估显示 AUC 0.956→0.779 明显退化。
原因是同一 `kind`（如 `NetNTLM`/`命令回显`/`片段`）在 CTF 题里就是答案、在真实流量里是噪音，
模型无法在全局特征空间区分两者。跨题样本**不进训练集**（`lab/build_dataset.py` 按 `group`
分组，训练时留一组评估即按此切分）。

## 改文案/接口前必看（有测试守着）

- **版本号两处同步**：`VERSION` 文件与 `ctfsweep/__init__.py` 的 `__version__`
  必须一致（`test_smoke.py` 断言）。发版/改动后按语义化版本递增。
- **改 CLI 选项 → 同步四处**：`cli.HELP`、`completions/ctfsweep.zsh`、
  `completions/ctfsweep.bash`、README 的选项表。补全有静态体检防回退：
  必须用 `compadd -l -d` + 手写显示串，**不得**改回 `_describe -t options`
  （一个条目只能给一个匹配词，同义短/长合并成一行 `-f --file` 做不出来）；
  同义短/长选项合并为一行显示（`-f --file` 只出现一次）。
  ⚠️ **候选结构是位置驱动的（对齐 jtool/ptool）**：选项**只在当前词以 `-` 开头时**出现，
  第一个参数位只出「子命令 + 文件」。早期两份补全都无条件铺选项，于是 `ctfsweep -q <TAB>`
  把除 `--brief` 外的 14 个选项连 `--config` 一起倒出来（按显示串排序，`--config` 恰好
  第一，最扎眼）；更早还一度反过来要求"不敲 `-` 也能看到选项"，两版都不是位置驱动的。
  这条**静态体检看不见**（它只查字面量在场），由 `check_completions()` 里的
  `_check_completion_behavior()` 守：在 `zsh -f` / `bash -f` 里覆写补全原语（`compadd` /
  `compgen` / `_files` / `_describe`）驱动补全函数，逐字断言各位置**实际给出的候选集合**；
  本机缺 zsh 时跳过（CI 镜像不保证有 zsh）。
  ⚠️ **两份补全文件末尾都有包装函数**（同 jtool/ptool）：`ctfsweep update` 后就地
  `source` 本文件（父 shell 里才做得到，脚本子进程改不了调用者的 shell），`uninstall`
  后重载 rc 并 `unfunction` 自己；`install` 不在列（只打印安装方式，不落地文件）。
  内部必须 `command ctfsweep "$@"`，否则自我递归。文件路径靠 source 时取
  `${(%):-%x}`（zsh）/ `${BASH_SOURCE[0]}`（bash），不是安装脚本生成的占位符——
  本项目的补全是**静态素材**，不像 jtool/ptool 那样由安装脚本生成。
  改这条要同步 `_check_completion_wrapper()`（假命令 + 调用前改写文件，两头验证）。
- **`cli.HELP` 是薄索引，不是文档**：形态对齐同仓库的 jtool / ptool——标题 / 用法 /
  子命令 / 选项 / 示例 / 说明六段，**每个选项、每条子命令、每条示例严格一行**。
  历史上这里铺过散文墙：置信度分数表 13 行 + 判断核 3 行 + 扫描缓存 5 行，全文 63 行
  （`--extract` 一条占 4 行、`-q` 占 2 行），"扫一眼"变成"读半天"——细节回流 README
  （选项表 / 子命令表 / 输出与置信度 / 判断核 四节都在那儿）。
  ⚠️ **README 不随安装载荷发布**（`deploy.sh` 白名单里没有它），装机用户手上只有
  `--help` 这一份参考，所以末尾「说明」三条（分档 / 缓存 / 判断核）**必须自足**，
  不能写成"详见 README"。
  ⚠️ **排版**：各段描述列按**显示宽度**对齐（CJK 占两列，与 ptool 的 `用法` 段同一算法）；
  选项名统一 `-f --file`（空格，无逗号，与补全的显示串一致）；选项段第一列全 ASCII，
  所以按字符数补齐即等于按显示宽度补齐。
  改这段文案要同步 `tests/test_smoke.py` 的两条锚点断言（含 `'用法'`+`'示例'`、
  `'每次扫描都写缓存'` 与 `'留存区' not in out` 反向断言）和那条 **`≤ 50 行`** 的上限反向断言
  （防散文墙漂回来；现 45 行）。
- **安装/更新/卸载的文案被两处逐字断言**，改这五个字符串之一就要同步改测试：
  `update:拉取最新源码快照并重装`、`install:显示安装方式`（`tests/test_smoke.py:95`，另有一条
  「无 `已弃用` / `更新指引` 残留」的反向断言防旧文案漂回来）；以及 `smoke.sh` 第 7 步断言的
  `运行模式: devtools 安装`、`已是最新版本`、`远端 vX 可用` + `--check：仅比对`、
  `更新完成: vA → vB`、`无法获取远端版本号`、`清理完成`。改 `cli.HELP` 里的三种运行方式说明
  同样要同步 README 的「安装」一节。
  ⚠️ **「要不要重开终端」只在 `installer/shell-setup.sh` 一处判**：改写前后比对 rc 的 cksum，
  改过 → `已写入 shell 配置: <rc>（重开终端或 source 后生效）`；没改 → `shell 配置未变: <rc>
  （接线一致，无需重开终端）`——升级时 rc 通常一字不变，所以后者才是 update 的常态。
  调用方（`install.sh` / `install-from-source.sh` / `selfmgr.cmd_update`）**都不得再补一句**
  同样的话：历史上三处各打一句，一次 `update` 连报三遍「重开终端」，用户以为更新没生效
  （命令本体本来就不需要刷新——启动器每次重新执行）。`update` 现在只多打一句
  `扫描缓存（数据目录）未受影响。`。回归位：`smoke.sh` 第 5 步断言重复安装报「shell 配置未变」、
  7.4 断言真更新时接线没变、7.6 断言 `清理完成`。
- **命令名只有 `ctfsweep` 一个，不许再加短别名**：1.10.5 及更早的 shell 接线写过
  `alias ctf='ctfsweep'`，已移除——`ctf` 太通用（macOS 自带 `ctf_insert`），
  同一个环境里再装别的 CTF 工具必然撞名，谁后接线谁赢，而且撞了之后用户看到的是
  别人的工具。因此：
  ⚠️ `shell-setup.sh` 写块时**只写三行**（PATH / 补全 / 成对标记），别再写回 alias；
  但 `_strip()` 里的 `^alias ctf='ctfsweep'$` 识别与删除**必须留着**——老装机升级/卸载时
  靠它把旧别名摘干净（`smoke.sh` 7.6 就塞了一行老形态 alias 验证清理）。
  文档/补全/FAQ 里凡是"短命令 ctf"的写法都要写成 `ctfsweep`；
  `flag,ctf` 那类**关键词**完全是另一回事（扫描用的关键词表），一个字都别动。
- **shell 脚本里 `$VAR` 后不得紧跟非 ASCII 字符**——bash 会把全角字符并入变量名。
  `check_shell_scripts()` 扫描所有 `*.sh`/`*.zsh`/`*.bash`/`bin/ctfsweep.sh` 强制这条。
  （`installer/shell-setup.sh` 里 `echo "…: $RC（…）"` 就是这么炸过一次，写成 `${RC}` 才行。）
- **报告文案是测试断言**：如 `【中置信（需人工确认）】`、`片段池（按文件标注来源）`、
  `←` 来源标注、`统计: 高置信` 的"已移除"反向断言。改输出前先 grep `tests/`。
- **汇总区分「flag 候选」与「非 flag 证据」**：`cli.py` 用 `utils.FLAG_RE` 判候选值是否呈
  flag 形状——有 flag 形状才出 `【flag 候选汇总】`，其余进 `【证据汇总】` 并按 `[kind]`
  标注类型；两者都空才打印 `【重点候选】未发现高（≥0.85）候选`。日志/流量题（无 flag）
  靠这条避免把 FTP 凭据一类证据误报成"可提交候选"。
- **关键词命中要走 `utils.text_like_window()`**：二进制区（图片/压缩/加密）里 `flag`/`ctf`
  会以**字节巧合**出现，而 latin-1 视角下"貌似可打印"（JPEG 实测可打印率约 75%，旧 0.7
  闸门挡不住）。ascii 通道用严格文本判定（ASCII 占比 / 可严格 UTF-8 解码）；utf-16 通道
  维持原检查。`tests/gen_fixtures.py::build_t10()` 同时含正例与字节巧合，负样本同题。
- **子命令名优先于文件路径**：`update`/`install`/`uninstall`/`clear`/`config`/`help` 会被当子命令。
  要扫同名文件得用 `-f 文件名` 或 `./文件名`。
- **行尾契约**（`.gitattributes`）：`*.bat` 用 CRLF、`*.sh` 用 LF——改这些文件别让编辑器
  自动转换，否则 Windows 版启动器会解析错位。
- **缓存是"每次都尝试写"，不是 `-q` 专属**：两种模式都捕获详细输出写进
  `<数据目录>/cache/<运行名>-<路径哈希6位>/`（`1/2/3.txt` 分档明细 + `<运行名>_cache.txt`
  完整报告）。
  ⚠️ **同一目标已有缓存则不再落盘**（`cli.cache_occupied()`，历史行为是静默覆盖）：
  第二次扫同一个目标时打 `缓存目录：<dir>/ 目录有文件，请使用 clear 清除`（`brief_print_occupied`），
  报告照常上屏、盘上旧文件一字不动。所以「两种模式内容相同」这类断言要先 `clear`——
  `tests/test_smoke.py::clear_cache()` 就是干这个的；`tests/test_golden.py` 则**每个用例前
  清空数据目录**（用带用例名的子目录会把路径写进 `-q` 输出，凭空多一堆基线差异）。
  ⚠️ **粒度是「一次运行」，不是「一个文件」**（历史缺陷：旧 `brief_cache_dir(fp)` 的注释
  写着按文件分是为了让 `a/capture.pcap` 与 `b/capture.pcap` 不互相覆盖——那个理由**只在
  目录扫描下成立**，`-f` 单文件时"一次运行 = 一个文件"两种粒度重合，所以一直没暴露；等到
  `-F 项目/` 就把缓存摊成十几个 `<文件名>-<哈希>` 平铺目录，`tests/golden/dir.txt` 尾部
  那 15 行同一形态的目录行就是铁证）。
  现在：`cli.run_identity()` 给出 `(运行名, 哈希输入, 是否目录扫描, 扫描根)`——
  **运行名走 `abspath`、哈希走 `realpath`**。⚠️ 名字**不能**用 realpath：单文件时
  `basename(abspath(fp))` 与旧的 `basename(fp)` 恒等（14 个单文件 golden 逐字节断言着旧名），
  realpath 会把软链解析成目标名；`abspath` 同时把 `-F .` / `-F dir/` 规范化（裸 `basename`
  会给 `.`，建出隐藏目录 `.-abc123`）。单文件时"一次运行 = 一个文件"，
  缓存路径与内容与旧的"每文件一份"**逐字节相同**。
  实现是 `cli._TeeStream` 一个替身**整轮只 `bind` 一次**（正文 → 汇总尾段之间换绑一次，
  不是逐文件换绑、更不是逐文件 `enter_context`）——循环里的 `continue` 才不会让捕获挂住
  写进上一个缓冲区；`passthrough=not brief` 决定是否上屏，所以**两个模式的缓存文件内容
  逐字节相同**（`check_scan_cache()` 断言着）。
  聚合后的 `1/2/3.txt` 全局按分数降序（`tierize()` 稳定排序），新增的 `← <相对路径>` 归属
  标签**只在目录扫描时**加——`Finding` 自己不带来源文件（模块类 finding 的 `loc` 常为空串），
  归属只能由 CLI 在 `brief_write_run()` 里补。同一个 `label`（`cli.file_label()`：目录扫描
  相对路径、单文件文件名）也用在 `[文件]` 头与汇总区的 `来自 %s`——只报 `basename` 的话
  `sub1/a.pcap` 与 `sub2/a.pcap` 在报告里长得一模一样。
  默认模式在**恢复真实 stdout 之后**打 `【扫描缓存】` 块（目录行末尾带 `os.sep`，否则
  `test_golden.normalize()` 的 `/<名>-<6位哈希>/` 正则匹配不上、哈希会写进基线），
  `brief_print_tiers` / `brief_print_counts` / `brief_print_run_cache` 同理必须收
  `stream=_real_stdout`（`brief_write_run` 的报错也走 `err_stream`——-q 下 passthrough=False，
  走默认 `print` 会让"写入失败"只落进缓存缓冲，控制台上什么都看不到）。
  ⚠️ 块首行「本次 N 个文件」必须用 **`len(targets)`**：换成"写出的缓存文件数"（现在是 0/1）
  会让 15 个文件的目录扫描印出"本次 1 个文件"。
  `tests/test_golden.py::normalize()` 把该哈希归一化掉，否则基线随 `$TMPDIR` 漂移。
  该缓存**只增不减**（**自动**路径 —— 装/卸/更新 —— 永不碰它），唯一的清理入口是
  `ctfsweep clear [-y]`（用户显式发起，见下一条）；`ctfsweep config` 报占用与路径。
  ⚠️ **单文件 `-q` 的控制台输出仍必须逐字节不变**（golden `t10-ftp.pcap+brief.txt` 是回归位）；
  目录模式 `-q` 是本次新增的形态（逐文件只报条数 + 末尾一次运行级块），`dir.txt` 之外
  没有基线守它，由 `check_dir_scan_cache()` 断言。
- **`ctfsweep clear [名称] [-y]` 只删数据，绝不删功能文件**：清空**数据目录**
  （`core/paths.py::data_root()`，默认 `~/.devtools/ctfsweep`、`CTFSWEEP_DATA_DIR` 可覆盖）下的
  **内容**——`cache/` 结果缓存、各题图片缓存目录、散落文件；**保留**目录本身与 `ctfsweep.conf`
  （配置不是缓存，删了等于丢设置）。⚠️ **带名称时只清那一个项目**（`_project_targets()`）：
  数据根下的同名条目（如 `capture4.pcapng/` 这种提取出的图片缓存）+ `cache/capture4-<6位哈希>/`；
  运行名同时试 `name` 与去扩展名的 `splitext(name)[0]`（扫描 `capture4.pcapng` 的运行名是
  `capture4`，用户两种写法都该命中），匹配用 `^<名>-[0-9a-f]{6}$` 的严格正则、不是前缀匹配。
  名称撞上功能项/配置时**直接拒绝**（`clear VERSION` 之类的误写要挡住），名称不存在则如实报
  "未找到"并返回 0。
  ⚠️ 绝不可写成 `rmtree(data_root())`：**用户级安装下数据目录就是安装根**，`bin/ lib/ models/`
  都住在那儿，整删等于把 ctfsweep 删掉。破坏性闸门与 uninstall 同规：**非交互（无 tty）且不带
  `-y` 一律拒绝**（返回 1，提示 `ctfsweep clear -y`）；交互式先报路径 / 文件数 / 占用 / 保留项
  再等一次确认；`-y --yes` 跳过。用户级安装下它天然"只清数据"，系统级安装下数据目录里只有数据，
  等于整目录清空。回归位 `tests/test_smoke.py::check_clear()`。
  加子命令要同步四处：`cli.HELP`（子命令段严格一行，**总行数 ≤ 50** 的反向断言仍在）、
  两份补全（zsh `_ctfsweep_subcmds` 与参数分支 / bash `subcmds=` 与 case —— clear 与
  uninstall 同收 `-y --yes`）、README 的子命令表与「子命令名优先」清单。

## lab/ 与 models/

- `lab/` 是实验区：**脚本进库，数据产物不进库**（`.gitignore` 排除 `lab/*.jsonl`、
  `lab/*.ctfj`、`lab/output/`）。这里的脚本**不随安装提供**（`deploy.sh` 的拷贝清单里没有
  `lab/`），所以训练能力只存在于仓库。
- `lab/train.py` 是判断核**唯一的训练入口**（`--data` / `--out` / `--epochs` / `--config`），
  内含 `load_rows`/`rows_to_xy`/`run_training`；`lab/build_dataset.py` 从题库构建
  `lab/dataset.jsonl`（本机数据，gitignore 内），`lab/data_generator.py` 合成样本。
  运行时的 `cli.py` **不再有 train/mark/learning/label/gen-data 子命令**，也别再加回去
  （`test_smoke.py::check_judge` 会逐个跑这些名字并断言非 0 退出）。
- `lab/analysis/` 是**案例库**：每题一个 `.md`，头部 YAML front matter（`case_id`/`type`/
  `answer`/`detect`/`method`/`tool`），正文是完整推理链。新解出的题按此格式沉淀，
  新沉淀的工具函数回填 `tool:` 字段指向 `ctfsweep/core/*.py`。
- `lab/task_generator.py` 靠 SSH 连远程 Windows 生成题目——依赖本机环境，
  不要在 CI 或无关改动里跑。
- `models/` 不只是"项目内的模型"：`deploy.sh` 会把它复制到 `<安装根>/lib/models`，
  **它属于安装载荷**（见上文 `models_dir()`）。改 `models/` 下任何文件都要走一次
  `bash tests/smoke.sh`（第 5 步断言安装后模型就位）。

### Windows（nt 分支）

`os.name == 'nt'` 时**整条安装链换一套**（没有 bash、没有 rc 文件）：

- **安装形态**：`%USERPROFILE%\.devtools\ctfsweep`（**用户级、不需要管理员**），
  PATH 上挂 `<根>\bin\ctfsweep.bat`。与 macOS/Linux 用户级一致——**安装根就是数据目录**，
  所以 `_CLEAR_KEEP`（含 `bin`/`lib`）在这里同样是"别把程序删掉"的那道闸门。
- **入口**：`installer/install.ps1`（一键：下载快照 → 解压 → 交给 `ctfsweep install`
  → 刷新当前会话 PATH）、`installer/windows/install.bat` / `uninstall.bat`（右键运行）。
  `publish-mirror.sh` 同步发 `install.ps1`（Windows 那行 `irm … | iex` 读它）。
- **PATH 走注册表** `HKCU\Environment`（`winreg`，REG_EXPAND_SZ）——**不用 `setx`**：
  它会把超过 1024 字符的 PATH 截断。增删是 `win_path_join` / `win_path_drop` 两个
  纯函数（大小写不敏感、容忍尾斜杠、空段清理、**不碰无关条目**），`test_smoke.py::
  check_windows_path_helpers()` 逐条守着——写坏 PATH 是全机器级事故。
- **部署**：`selfmgr.deploy_nt()` 按同一份 `_PAYLOAD_REPO` 拷文件 + 写启动器，
  替代 shell 的 `deploy.sh`；`cmd_update` 在 nt 上走它，`_shell_setup()` 直接返回 0。
- ⚠️ **文本编码契约：UTF-8，声明行 + 按类型的落地机制**（`tests/check_text_encoding.py`
  逐条核对「声明 = 实际字节」）。各运行环境**没有共通的 pragma**，别指望一个声明走天下：
  - `.bat` → `@rem encoding: utf-8`。**UTF-8 无 BOM + CRLF + `chcp 65001` 必须在第一处
    非 ASCII 之前**。带 BOM 第一行报 `'?@echo' 不是内部或外部命令`；LF-only 会碎片化
    解析（ptool 的 build-remote.bat 记着这笔）。
  - `.ps1`（`irm … | iex` 分发）→ `# encoding: ascii-b64`。正文**必须纯 ASCII**：
    响应体被当**字符串**喂给 Invoke-Expression，BOM 会并进第一行去执行一个叫 `<BOM>#`
    的命令（实测 `CommandNotFoundException (ï»¿#)`），非 ASCII 按 ANSI 解码后整段乱码。
    中文以 UTF-8 Base64 内嵌、运行时 `T()` 解码；检查器会把每条 Base64 反解一遍。
  - `.ps1`（磁盘执行）→ `# encoding: utf-8-bom`，**BOM 是 Windows PowerShell 5.1
    唯一认的编码信号**（无 BOM 按 ANSI/GBK 读）。
  - `.iss` → `; encoding: utf-8`。ISCC 6.7.3 实测默认按 UTF-8 读，有无 BOM 都对。
  - 用户可见的中文仍优先由 Python 侧打印（它自己管控制台编码）。
- **控制台编码**：`cli._console_utf8()` 在入口把重定向的 stdout/stderr 切到 UTF-8 +
  `errors='replace'`（真控制台只加 `errors='replace'`）。不这么做，Windows 上
  `ssh`/管道/`> file` 一遇到 GBK 编不出的字符（主机表 `↔`、会话告警 `⚠️`）就
  UnicodeEncodeError，连「扫描出错」的告警都会跟着炸（实测 t6-hosts.pcap 必崩）。

## 工作流

- 仓库是 monorepo（`main` 是作品集索引，本项目专用分支是 `CtfSweep`，也是当前分支）。
  单独开发本项目就在 `CtfSweep` 分支上。
- 提交信息用 Conventional Commits 前缀 + 中文描述，例如
  `feat(ad): 新增 AD / 域协议取证（Kerberos 票据 · NetNTLM · LDAP 明文绑定）`。
- 判断核相关的调试/对比实验脚本（如 AUC 对比）历史上放在 `/tmp`，只把结论写进
  `lab/analysis/README.md`，不把实验脚本提交进库。
