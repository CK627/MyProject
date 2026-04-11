# 飞控板维修工单管理系统 (Flight Control Board Maintenance Work Order System)

一个基于 Web 的飞控板维修工单管理系统，用于记录、追踪与统计飞控板的维修流程，覆盖“工单创建 → 故障描述 → 测试与定位 → 维修与复测 → 评价与归档”等核心环节。

## 功能概览

- 工单管理：创建、查询、更新维修工单与状态
- 用户与权限：支持工程师/队长/裁判/管理员等不同角色
- 数据库初始化：提供初始化页面与接口，支持一键创建表结构
- API 接口：提供 REST 风格接口供前端调用
- 统计与追踪：包含基础统计、记录追踪等功能模块

## 技术栈

- 后端：PHP（mysqli）
- 数据库：MySQL 5.7+ / 8.0+
- 前端：HTML / CSS / JavaScript（原生）

## 目录结构

```text
FlightControlBoardMaintenanceWorkOrderSystem/
├── api/                      # 后端 API
├── config/                   # 配置文件
│   ├── app-config.ini        # 应用状态配置
│   ├── mysql.ini.example     # 数据库配置模板（需复制生成 mysql.ini）
│   └── 配置说明.md
├── css/                      # 样式文件
├── js/                       # 前端脚本
├── images/                   # 图片资源
├── database-init.html        # 数据库初始化页面
├── login.html                # 登录页面
├── index.html                # 主页面
├── fcbmwos_mysql8.sql         # 数据库结构与示例数据（模板化密码）
├── fcbmwos_mysql8_updated.sql # 数据库结构与示例数据（更新版，模板化密码）
├── 使用说明.md
├── API使用指南.md
├── 部署指南.md
└── 故障排除指南.md
```

## 开始使用（本地开发）

### 1) 准备环境

- PHP 7.4+（建议开启 `mysqli` 扩展）
- MySQL 5.7+ / 8.0+

### 2) 配置数据库连接

复制数据库配置模板，并将占位符替换为你的真实配置：

```bash
cp config/mysql.ini.example config/mysql.ini
```

然后编辑 `config/mysql.ini`：

```ini
[database]
host = <DB_HOST>
user = <DB_USER>
password = "<DB_PASSWORD>"
database = <DB_NAME>
port = <DB_PORT>
charset = utf8
```

提示：为了避免泄露隐私，本仓库默认不提交 `config/mysql.ini`，只提交 `config/mysql.ini.example`。

### 3) 初始化数据库

本项目的用户密码存储逻辑为 `md5(明文密码)`（详见 [login.php](./api/login.php)）。导入 SQL 前需要你先准备好密码的 MD5：

```bash
php -r 'echo md5("你的密码");'
```

随后二选一导入数据库（推荐使用更新版本）：

- `fcbmwos_mysql8_updated.sql`
- `fcbmwos_mysql8.sql`

这两个 SQL 文件中用户表的 `password` 字段为占位符 `<MD5_PASSWORD>`，请在导入前替换为你实际的 MD5 值。

### 4) 启动服务

在项目目录下启动 PHP 内置服务器：

```bash
php -S localhost:8000
```

### 5) 访问系统

- 登录页：`http://localhost:8000/login.html`
- 数据库初始化页：`http://localhost:8000/database-init.html`

## 配置与安全建议

- 生产环境不要提交 `config/mysql.ini`（仅提交模板即可），并确保 Web 服务器对 `config/` 目录不可访问
- 首次部署后请及时修改初始账号密码并最小化数据库权限
- 如果要用于生产环境，建议将密码存储从 MD5 升级为更安全的哈希算法（如 bcrypt/argon2）

## 文档

- 使用说明：[使用说明.md](./使用说明.md)
- API 文档：[API使用指南.md](./API使用指南.md)
- 部署指南：[部署指南.md](./部署指南.md)
- 故障排除：[故障排除指南.md](./故障排除指南.md)

## 未来规划（Roadmap）

- 账号与权限体系完善（更细粒度的权限控制）
- 密码安全升级（bcrypt/argon2）
- 部署脚本与容器化方案完善（提供可直接使用的 docker-compose）
