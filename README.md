# FileUpload（文件管理与毕业提交系统）

一个基于 PHP + MySQL 的 Web 文件管理系统，支持普通文件传输、毕业生材料提交与教师审批流程。采用毛玻璃（Glassmorphism）视觉风格，适配桌面端。

---

## 主要功能

### 普通用户
- 注册 / 登录（学号 + 密码，bcrypt 哈希存储）
- 文件管理：新建文件夹、上传（支持拖拽与大文件分片）、移动、重命名、删除、下载
- 文件共享：将文件/文件夹公开给其他用户
- 个性化设置：默认首页、隐藏文件显示偏好

### 毕业生
- 系统自动识别 `graduation_information` 表中的学生身份
- 12 种毕业文档分类提交（论文、实习证明、申请表等）
- 部分项目提供 Word 模板下载
- 文件自动重命名为规范格式（学号+姓名+文档名）
- 重复提交自动覆盖旧文件

### 教师 / 管理员
- 按班级管理学生名单（支持 Excel/CSV 批量导入）
- 文件统计概览（提交率饼图）
- 审批批阅：通过/不通过快捷按钮，自动跳转下一个待办
- 打回不合格文档、批量打包下载
- 管理员可查看所有班级，普通教师仅限本班

---

## 技术架构

| 层级 | 技术 |
|------|------|
| 前端 | HTML5, CSS3, Vanilla JavaScript |
| 后端 | PHP 7.4+（mysqli 扩展） |
| 数据库 | MySQL 5.7+ / MariaDB 10.2+ |
| 部署 | PHP 内置服务器 / Nginx + PHP-FPM / Vercel |

**核心依赖：**
- `mysqli` — 数据库连接
- `password_hash` / `password_verify` — 密码安全
- `mbstring` — 中文文件名处理
- `zip` — 打包下载功能

---

## 环境配置

### 1. 数据库

创建两个数据库：

```sql
CREATE DATABASE IF NOT EXISTS `FileUpload` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `FileUploadS` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

导入主库表结构：

```bash
mysql -u root -p FileUpload < docs/FileUpload.sql
```

> `FileUploadS` 库无需手动建表，系统会在用户首次操作时自动创建 `user_{username}` 表。

### 2. 配置文件

复制并编辑配置文件，填入你的数据库凭据：

```bash
cp config/mysql.ini config/mysql.ini.local      # 主库连接
cp config/mysql_files.ini config/mysql_files.ini.local  # 文件库连接
```

配置格式（`config/mysql.ini`）：
```ini
host="127.0.0.1"
port=3306
username="root"
password="<YOUR_PASSWORD>"
database="FileUpload"
charset="utf8mb4"
```

`config/mysql_files.ini` 同理，`database` 改为 `FileUploadS`。

### 3. 目录权限

确保 Web 服务器对以下目录有写权限：
- `FileUploadGraduationSubmission/` — 毕业文件存储

---

## 启动

**开发环境：**
```bash
php -S 0.0.0.0:8000 -t .
```
访问 `http://localhost:8000/index.html`

**生产环境：** 参考 `USAGE.md` 中的 Nginx + PHP-FPM 配置示例。

---

## 目录结构

```
FileUpload/
├── api/                  # PHP 后端 API（约 60 个文件，按功能命名）
│   ├── Database.php      # 单例数据库连接管理器
│   ├── login.php         # 登录/注册
│   ├── upload.php        # 文件上传
│   ├── graduation_*.php  # 毕业提交相关
│   └── ...
├── config/               # 数据库配置文件
├── css/                  # 样式文件
├── js/                   # 前端 JavaScript
├── static/               # 静态资源（PDF.js 等）
├── template/             # 可下载的文档模板
├── docs/                 # 数据库 Schema 与项目文档
├── index.html            # 主入口（文件管理）
├── files.html            # 文件列表页
├── teacher.html          # 教师管理页
└── teacher_review.html   # 教师审批页
```

---

## 相关文档

- `USAGE.md` — 详细的部署与使用指南
- `REFACTOR_PLAN.md` — MVC 架构重构规划
- `docs/database-schema.sql` — 完整数据库 Schema
