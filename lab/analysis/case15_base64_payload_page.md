---
case_id: 15
type: base64-payload-page
source_file: （样例 2021-02-08-traffic-analysis-exercise.pcap）
linktype: 1
answer: unknown
detect: "HTML/JS 页面（含 saveAs / createObjectURL / data 变量）体积大、内部一段超长 base64"
method: carve_base64_blobs（长 b64 段 → 解码 → 文件签名校验 → 落盘）
tool: ctfsweep/core/extract.py（carve_base64_blobs）+ scanner 提取阶段
---

# case15：base64 载荷页解码（"saveAs 下载页"手法）

**类型**：嵌入式载荷提取（页面无文件签名，只有 base64 文本）
**样例**：`2021-02-08-traffic-analysis-exercise.pcap`（官方期望产物：822,272 字节 Word 文档）

## 现象：抓包里"没有"载荷文件

流中有下载链路（HTTP 200、octet-stream、EXE 都提取了），但**答案要的 Word 文档找不到**。
官方答案提示：载荷是 **base64 文本藏在网页里**（"Export this page… open in a browser"）。

## 识别特征

1. 响应是 `text/html`（或 JS），页面里出现 `saveAs(blob, fileName)` / `createObjectURL` 之类
   "浏览器端下载"代码——典型的"落地页"；
2. 页面**异常大**（本样例 1.1 MB 的 HTML），而正常页面没这么大；
3. 页面里有一段**超长连续 base64**（允许换行），长度远超普通图标/字体资源。

## 分析过程（验证链）

```
HTML 页（HTTP 响应体，1,097,546 字节）
  └ 单段 base64（clean 后 1,096,364 字符）
      └ base64 解码 → 822,272 字节，头 = D0 CF 11 E0（OLE2 复合文档）
          └ SHA-256 = 3a5648f7…a33de154d  ← 与官方答案逐字节一致 ✓
```

**关键验证**：解码长度 1,096,364 = ceil(822,272/3)*4 + padding 的长度（证明是整段单文件编码，
没有截断/拼接问题）；哈希与官方一致（黄金标准）。

## 实现规则（工具化）

- 在提取阶段对每个"响应体"（text/html 类）扫描 `[A-Za-z0-9+/=\s]{2000,}` 长段；
- 去空白 → **补 padding（绝不截断到 4 的倍数——会丢尾部字节！）** → base64 解码；
- 只接受解码结果带**明确文件签名**者：MZ（另验 PE 头）/ PK / OLE2 / %PDF / ELF / GZIP；
- 命中后按正常提取流程落盘（zip 会继续解包扫内容、dedup、编号）。

### 踩坑记录

1. **padding 处理**：曾用 `clean[:len//4*4]` 截断法 → 822,272 字节的文件丢了尾部 2 字节
   （822,270），哈希不符。正确做法 = 补 `=` 而不是截断。
2. **阈值选择**：min_chars 不能太大（会漏小载荷），也不能太小（网页都会命中）；
   2000 起 + 文件签名校验 + .exe 额外验 PE 头，实测在真实流量批次中零误报。

## 同类变体（判断指引）

- `data:text/plain;base64,…` / `<script>let data='<b64>'` / Blob 数组分段拼接；
- 分段（多个 `< 2000` 短段）目前不处理——需要时先合并同页多段再解码；
- 若解码结果是 PK(zip/docx)，继续走嵌套 zip 流程（条目扫描 + 弱口令尝试）。
