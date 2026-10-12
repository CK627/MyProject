# case05: 流量藏加密压缩包 + 提示爆破（嵌套 zip）

## 元数据

```yaml
id: case05
title: 从流量提取嵌套加密 zip，按提示爆破密码得 flag
type: file-transfer / encrypted-zip / hinted-bruteforce
source_files:
  - A.pcapng（430MB，SMB/HTTP 大流量）
  - logs.pcapng（Windows 日志分析题）
answers:
  A.pcapng: "flag{friday}（zip 密码 DBOQ6457）"
  logs.pcapng: "flag{Find You!}（zip 内 flag.txt）"
tools_used: [ctfsweep --extract, zipfile 纯 Python 爆破（10^4 组合）]
status: solved
```

## 识别特征

- 大流量中夹带文件传输（HTTP 下载 / SMB 拷贝）
- `--extract` 提取出 **zip/压缩包** 类文件（尤其小体积、可疑命名如 flag.zip）
- **关键辅助线索**：压缩包旁边常有密码提示文件（本例：GBK 编码的
  "新建文本文档.txt" —— "压缩包密码前四位是DBOQ，后四位是随机组成的数字。"）

## 分析步骤（A.pcapng）

### 1. 全量提取

```bash
ctfsweep A.pcapng --extract --extract-dir out/
# → out/ 得到 A_001.zip（494B，可疑）+ 19 张 jpg（干扰物）
```

### 2. 打开压缩包看结构

A_001.zip 内是 **flag.zip**（另一个压缩包，内层 flag.txt 条目带加密标志位）。

### 3. 读取提示文件（注意编码！）

同包内 "新建文本文档.txt" 是 **GBK 编码**：

```
压缩包密码前四位是DBOQ，后四位是随机组成的数字。
```

（GBK 解码：`\xd1\xb9\xcb\xf5...` → "压缩包密码前四位是DBOQ..."）

### 4. 按提示构造候选爆破

密码空间 = DBOQ + 4 位数字 = 10^4 组合，纯 Python zipfile 直接爆破：

```python
for i in range(10000):
    pwd = ('DBOQ%04d' % i).encode()
    try: data = z.read('flag.txt', pwd=pwd); break
    except: pass
# 0.1 秒命中：DBOQ6457 → flag{friday}
```

### 5. 另一款（logs.pcapng）

zip 未加密，直接解出 flag.txt = `flag{Find You!}`（与流量里的 SQL 注入
回显一致——双渠道互相印证）。

## 解码/提取规则

1. `--extract` 全量提取后**优先翻小体积 zip/rar**（大图片多为干扰）
2. 压缩包旁的 txt/说明文件**必须 decode 尝试多编码**（GBK/UTF-8/UTF-16）
3. 有提示直接按提示缩小爆破空间（前缀/后缀/位数）——0.1 秒级完成
4. 无提示优先试：空密码、zip 伪加密、常见弱口令（DBOQ 类题常用 4-6 位数字）

## 同类变体判断指引

- "流量题 + zip" 是高频组合：flag 可能 ①zip 明文在包内 ②加密需爆破
  ③zip 伪加密（改字节 0x09→0x00 可绕过）
- 遇到 `PK` 头文件小体积（<1KB）的，往往是"套娃"或"密码验证"，重点看
- 扫描器已支持 HTTP chunked+gzip 双层解码（case02），提取链覆盖到位
