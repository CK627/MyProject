# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

ctfsweep 是面向 CTF / 应急响应的取证扫描 CLI：把 pcap/pcapng、evtx、.reg/任意文本、
内存镜像、浏览器数据库、邮件、日志、数据库导出等输入里的"可疑线索"一次性翻出来，
按**置信度分级**输出（高置信可直接核验 / 中低置信留作人工排查）。

三条硬约束（改任何代码前先记住）：

1. **零第三方依赖**：纯标准库、Python 3.8+。`pyproject.toml` 的 `dependencies = []`。
2. **源码直跑**：不做外部安装，功能全在仓库内；`installer/` 里是历史遗留脚本（只用于
   冒烟测试的历史路径回归，正常使用不需要）。
3. **文档/输出/注释/提交信息全部中文**。报告标题（`【高置信（可直接核验）】`）、
   CLI 帮助、findings 的 `kind` 字段都是中文字面量，测试直接断言这些字符串——
   改文案等于改测试，见下文「改文案前必看」。

## 常用命令

```bash
# 跑工具（三种等价方式）
./bin/ctfsweep <文件或目录> [选项]
python3 -m ctfsweep <文件或目录> [选项]
ctf -f capture.pcap            # 短命令 ctf = ctfsweep，由 installer 写入 shell 配置的 alias
                               # （纯源码直跑时未必存在，以 ./bin/ctfsweep 为准）

# 完整冒烟（语法门 + 单元冒烟 + shell 语法 + 启动器 + 安装/卸载循环 + 引导模式）
bash tests/smoke.sh

# 只跑 Python 冒烟（快，日常用这个）
python3 tests/test_smoke.py

# 生成确定性测试样例（pcap/pcapng/evtx/内嵌 zip/AD 域流量/USB/TLS/主机表）
python3 tests/gen_fixtures.py /tmp/fixtures
```

**单个测试怎么跑**：`tests/test_smoke.py` 是一条线性脚本，没有 pytest/测试发现机制。
断言走 `check(cond, msg)`，失败只累加到 `FAILS` 并在末尾统一打印。
要隔离调试某一节（如 `check_judge(tmp)`），在临时目录里 `gen_fixtures.generate(tmp)`
后再调用该节的函数即可。定位失败项用 `python3 tests/test_smoke.py 2>&1 | grep FAIL`。

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

判定标准是**"这条输出对解题有没有引导价值"**，不是"看起来像不像可疑"。已经落地的十三条：

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

### 输入解析层

`core/capture.py` 是纯 Python 的 pcap/pcapng 解析器（无 scapy/dpkt/Wireshark），
含链路层分派（Ethernet/VLAN/PPPoE/Raw-IP/Linux-SLL/SLL2/NULL）与
`merge_stream()`（按 TCP seq 重组，提取文件字节与 Wireshark 一致——这是有测试守着的
行为，见 `lab/analysis/case12`）。`core/extract.py` 负责文件雕刻、口令池、zip 假加密绕过。
`core/utils.py` 集中了所有共享正则（`FLAG_RE`/`JWT_RE`/`B64_RUN`/`HEX_RUN`/`SECRET_LINE_RE`）
与 `kw_boundary_ok()`（词内误报闸门：`FolderValueFlags`、`create_pdo_flag`、`msctf_`）。
DNS 相关的 `KNOWN_INFRA_SUFFIXES` / `dns_lead_reason` 也在这里（见上文「噪音闸门」）。

⚠️ **`merge_stream()` 的缓冲区按"序号跨度"分配，跨度必须先过合理性闸门**：
同一个客户端临时端口被多条连接复用（或序号被伪造）时，几个互不相干的 ISN 会被按
4 元组聚合到一起，序号之间根本没有可比性。实测 spambot.pcap：7 条"流"各有 3 个包、
18 字节载荷，序号却横跨 3.5 GB ⇒ 旧实现每条流分配 256 MB 零缓冲，10 MB 的抓包吃
**2.1 GB 内存、跑 250 秒**。现在的判据是 `span > max(4 MB, 载荷总量 × 64)` 就退回
"按包序直接拼接"——序号可比的流跨度 ≈ 去重后的字节数，丢包空洞只占零头，不会误伤
（`tests/test_smoke.py::check_stream_merge()` 守着：正常合并 / last-wins / 巨跨度退化 /
小空洞补零四种情形）。

### 判断核（本地 MLP，可训练）

`core/judge.py`（最大的模块）自成一套：140 维特征的手写 MLP 集成（5 种子），
二进制 `.ctfj` 格式（`core/model_io.py`），以及**数据生命周期**：

```
每次扫描 → 候选快照写入留存区 retention.jsonl（RETENTION_MIN_SCORE=0.6 以上）
        → ctfsweep mark <路径> <真实flag>：命中答案的候选=正样本，同题其他高分候选=难负样本
        → 累积到 dataset.jsonl
        → ctfsweep train / learning：留一组评估 + 全量重训
        → 模型写回项目内 models/model.ctfj
```

- **模型与超参数随项目**：`models/model.ctfj` + `models/train_config.json`
  （改网络结构/学习率/种子改 JSON，不改代码）。
- **运行时数据在用户目录**：`~/.devtools/ctfsweep/judge/`（`retention.jsonl`/`pending.jsonl`/
  `dataset.jsonl`）。**这些数据永不自动删除**，`uninstall` 也保留。
- 环境变量可覆盖路径（测试与实验靠这些隔离）：`CTFSWEEP_DATA_DIR`、`CTFSWEEP_MODELS_DIR`、
  `CTFSWEEP_TRAIN_CONFIG`、`CTFSWEEP_JUDGE_MODEL`、`CTFSWEEP_CONF`、`CTFSWEEP_MIRROR`。

🚨 **负样本必须来自同题语境**。`lab/analysis/README.md` 记录了受控实验：把"真实恶意流量"
（无 flag）题目的高分候选当负样本灌进训练集，留一组评估显示 AUC 0.956→0.779 明显退化。
原因是同一 `kind`（如 `NetNTLM`/`命令回显`/`片段`）在 CTF 题里就是答案、在真实流量里是噪音，
模型无法在全局特征空间区分两者。跨题样本只留在留存区（标记 skipped），**不进训练集**。

## 改文案/接口前必看（有测试守着）

- **版本号两处同步**：`VERSION` 文件与 `ctfsweep/__init__.py` 的 `__version__`
  必须一致（`test_smoke.py` 断言）。发版/改动后按语义化版本递增。
- **改 CLI 选项 → 同步四处**：`cli.HELP`、`completions/ctfsweep.zsh`、
  `completions/ctfsweep.bash`、README 的选项表。补全有静态体检防回退：
  必须用 `compadd -l -d` + 手写显示串，**不得**改回 `_describe -t options`
  （其 prefix-needed 门禁会导致"不敲 `-` 就看不到选项"）；同义短/长选项合并为
  一行显示（`-f --file` 只出现一次）。`update`/`install` 的文案也被断言。
- **shell 脚本里 `$VAR` 后不得紧跟非 ASCII 字符**——bash 会把全角字符并入变量名。
  `check_shell_scripts()` 扫描所有 `*.sh`/`*.zsh`/`*.bash`/`bin/ctfsweep` 强制这条。
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
- **子命令名优先于文件路径**：`update`/`train`/`mark`/… 会被当子命令。要扫同名文件得用
  `-f 文件名` 或 `./文件名`。
- **行尾契约**（`.gitattributes`）：`*.bat` 用 CRLF、`*.sh` 用 LF——改这些文件别让编辑器
  自动转换，否则 Windows 版启动器会解析错位。
- **`-q/--brief` 是开关式灰度**：默认输出必须逐字节不变（14 个 golden 里 13 个是默认模式，
  开着它就是回归）。它靠 `redirect_stdout` **逐文件**捕获详细输出写进
  `<数据目录>/cache/<文件名>-<路径哈希6位>/`（`1/2/3.txt` 分档明细 + `<名>_cache.txt`
  完整报告），目录名带**完整路径**短哈希是为了同名不同目录不互相覆盖（目录扫描时才撞）。
  `tests/test_golden.py::normalize()` 会把该哈希归一化掉，否则基线随 `$TMPDIR` 漂移。
  该缓存**只增不减**（用户数据目录内的文件永不自动删除），清理入口只有
  `ctfsweep config` 里那行「精简缓存: <路径>（N 个文件，X MB）」——改缓存布局时同步它。

## lab/ 与 models/

- `lab/` 是实验区：**脚本进库，数据产物不进库**（`.gitignore` 排除 `lab/*.jsonl`、
  `lab/*.ctfj`、`lab/output/`）。
- `lab/analysis/` 是**案例库**：每题一个 `.md`，头部 YAML front matter（`case_id`/`type`/
  `answer`/`detect`/`method`/`tool`），正文是完整推理链。新解出的题按此格式沉淀，
  新沉淀的工具函数回填 `tool:` 字段指向 `ctfsweep/core/*.py`。
- `lab/auto_learning.py` 是"生成题目 → 扫描 → 分析 → 收集 → 训练"闭环，
  `lab/task_generator.py` 靠 SSH 连远程 Windows 生成题目——两者都依赖本机环境，
  不要在 CI 或无关改动里跑。

## 工作流

- 仓库是 monorepo（`main` 是作品集索引，本项目专用分支是 `CtfSweep`，也是当前分支）。
  单独开发本项目就在 `CtfSweep` 分支上。
- 提交信息用 Conventional Commits 前缀 + 中文描述，例如
  `feat(ad): 新增 AD / 域协议取证（Kerberos 票据 · NetNTLM · LDAP 明文绑定）`。
- 判断核相关的调试/对比实验脚本（如 AUC 对比）历史上放在 `/tmp`，只把结论写进
  `lab/analysis/README.md`，不把实验脚本提交进库。
