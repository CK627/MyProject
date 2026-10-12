---
case_id: 02
type: http-nested-file-extract
source_file: extracting-objects-from-pcap-example-01.pcap
answer: "unknown（教学题：目标是提取对象本身；提取物内未发现 flag）"
detect: "HTTP 响应 Content-Type: application/x-msdownload / application/msword + body 呈 chunked/gzip 特征"
method: http-body-decode + carve-files(PE/OLE2/ELF)
tool: "ctfsweep/core/http.py (http_body_decode) + ctfsweep/core/extract.py (carve_files 扩展)"
---

# 案例 02：HTTP 嵌套编码的文件提取（chunked → gzip → PE/OLE2）

## 一、题目信息

| 项 | 值 |
|---|---|
| 文件 | extracting-objects-from-pcap-example-01.pcap（1.3 MB，1790 包） |
| 流量特征 | 恶意文件投递：GET /Documents/Invoice&MSO-Request.doc + GET /knr.exe |
| 提取结果 | Invoice&MSO-Request.doc（110 KB，OLE2）+ knr.exe（2.4 MB，PE） |
| 答案 | 提取对象即目标；对提取物做 strings/宏/URL 分析后**未发现 flag**（二进制噪声中的 `{xxx}` 均为误报，见第五节） |

## 二、识别特征（这类题长什么样）

1. HTTP 请求序列中出现**可执行/文档文件名**（.exe/.doc/.xls/.zip/.rar）
2. 响应头 `Content-Type: application/x-msdownload`（exe）或 `application/msword`（doc）
3. 响应 body 首部呈：`[16进制长度]\r\n` + `\x1f\x8b\x08`（= **chunked 分块 + gzip 压缩**双层编码）
4. 常见于"恶意样本投递 / 从流量提取对象"题型

## 三、分析过程（完整推理链）

### Step 1: 初扫（无提取能力时）
- 高置信 0 条；低置信线索：DNS 恶意域名（smart-fax.com、dunlop.hopto.org）、950KB 会话拼接
- `--extract` 产出为空——**提取器只认 ZIP/PNG/PDF 等，不认 PE 和 OLE2**

### Step 2: 定位根因（手工解析）
```
GET /knr.exe 的响应体：
  31 66 61 61 0d 0a 1f 8b 08 ...
  └─"1faa\r\n"─┘└─gzip魔数─┘
→ chunked 分块（0x1faa=8106 字节/块）包裹 gzip 数据
→ 现有扫描器直接 carve 原始数据：gzip 流被分块标记打断 → 解不开 → 无产出
```

### Step 3: 实现解码链并提取
```
HTTP body → chunked 拼接（跳过分块长度行）→ gzip 解压 → 得到文件本体
  /Documents/Invoice&MSO-Request.doc → 110188 字节 OLE2（D0CF11E0）
  /knr.exe                           → 2437120 字节 PE（MZ + PE\0\0 签名）
```

### Step 4: 提取物分析（找 flag）
- **doc**：201 个可打印串，无 flag 特征（含加密/压缩数据噪音）
- **exe**：7381 个可打印串；含 2 处 http://（可疑 C2）；无 flag
- 结论：本题为"提取对象"教学题，提取成功即达成目标；无 flag

## 四、解码规则（可复用）

| 层 | 特征 | 处理 |
|---|---|---|
| chunked | body 首部 `^[0-9a-f]{1,8}\r\n`，每块 `[len]\r\n[data]\r\n` | 逐块拼接（size=0 结束） |
| gzip | `1f 8b 08` | `zlib.decompressobj(31)` |
| zlib | `78 9c` / `78 da` | `zlib.decompress` |
| PE | `MZ` + offset 0x3C 指向 `PE\0\0` | 提取（下一 PE / 100MB 界） |
| OLE2 | `D0 CF 11 E0 A1 B1 1A E1` | 提取（下一 OLE2 / 50MB 界） |
| ELF | `7F 45 4C 46` + class/data 校验 | 提取 |

多层可嵌套（最多循环 3 层解码）。

## 五、误报判别（重要经验）

二进制文件（PE/OLE2/加密数据）中，**片段探测器可能从随机字节里挖出 `{xxx}` 形式的假片段**，
启发式拼接会产出看似 flag 的字符串。**判别方法**：

1. **连续性**：真 flag 的片段应处于相近偏移（同数据块）；若片段间相距 >100KB 几乎必为误报
2. **上下文**：真片段周围是可读文本（strings 区）；样本片段周围是乱码/机器码则误报
3. **提取完整性**：本例"拼接建议"的第三个片段根本不在该文件中（跨文件误收集）
4. **实例**：本例曾产出 `flag{rtzyyypvtyyyrttyyyrtt9y...}` 的拼接——经上述检查**排除**
   （周围为 `\x1b\x10\x15` 等二进制噪点 + 片段间距 130KB + 第三片段不存在）

## 六、工具沉淀

- `http.py::http_body_decode(body)`：chunked → gzip/zlib 自动解码链（notes 记录变换）
- `http.py::parse_http_responses`：chunked 响应自动解码
- `extract.py::carve_files`：新增 PE / OLE2 / ELF 签名提取
- `scanner.scan_capture` 提取阶段：对 HTTP 响应体解码后再 carve + flag 快扫

## 七、同类变体（判断指引）

| 变体 | 识别 | 方法 |
|---|---|---|
| 恶意文档投递（本题） | .doc/.xls + 宏流量 | 提取 OLE2 → VBA 宏分析 |
| 载荷下载 | .exe/.dll | 提取 PE → strings / C2 提取 |
| 嵌套压缩 | .zip/.rar/.7z 内再套 | 提取后自动解压递归扫描 |
| 编码投递 | base64/chunked/gzip 组合 | 解码链按特征逐层处理 |
