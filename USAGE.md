# 项目部署与使用指南

本文档详细说明了如何从零开始部署和配置本项目，包括数据库环境搭建、配置文件修改及服务运行。

**最新更新**（v3.2 - 2026.02.16）：
- ✅ **审批流程优化**：
  - 新增“通过/不通过”快捷按钮，替代下拉菜单。
  - 自动跳转下一个“已提交但未审批”的项，提升批阅效率。
  - 支持“上一个/下一个”手动导航。
  - 列表页默认开启自动刷新，实时同步审批状态。
- ✅ **会话监控**：客户端自动检测 Session 有效性，过期自动跳转登录页，防止操作失效。
- ✅ **UI 升级**：审批按钮采用毛玻璃风格，优化视觉体验。
- ✅ **Bug 修复**：
  - 修复中文文件名在审批预览时的加载错误。
  - 修复审批弹窗加载时的逻辑错误。
  - 修复导航按钮在跨标签页时的状态同步问题（改用 localStorage）。

**v3.1 更新（历史）**：
- ✅ **数据库合并**：毕业生数据已迁移至主库 `FileUpload.graduation_information` 表，简化部署配置。
- ✅ **文件重命名**：普通文件传输系统支持文件和文件夹重命名（后缀名不可更改）。
- ✅ **自定义弹窗**：重命名等操作现使用毛玻璃主题的自定义弹窗，体验更统一。
- ✅ **文件列表优化**：毕业生文件列表现从数据库读取，确保数据一致性。

**v3.0 更新（历史）**：
- 视觉重构：全站升级为“High-End Glassmorphism”风格。
- 模板支持：毕业提交模块支持直接下载 Word 模板。
- 布局修复：解决了侧边栏与内容区的滚动冲突。

---

## 1. 环境要求

- **操作系统**：Linux / macOS / Windows
- **PHP 版本**：>= 7.4 (推荐 8.0+)
- **数据库**：MySQL >= 5.7 或 MariaDB >= 10.2
- **PHP 扩展**：`mysqli`, `mbstring`, `json`, `zip` (用于打包下载)

---

## 2. 数据库配置

本项目需要创建两个独立的数据库（Schema），分别用于存储用户账户/毕业生信息和私有文件索引。

### 2.1 创建数据库与表结构

请登录 MySQL 执行以下 SQL 语句：

#### (1) 主应用库 (`FileUpload`)
用于存储用户账号、管理员账号、个性化设置及毕业生信息。

```sql
CREATE DATABASE IF NOT EXISTS `FileUpload` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `FileUpload`;

-- 普通用户表
CREATE TABLE IF NOT EXISTS `Users` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(64) NOT NULL UNIQUE COMMENT '学号/用户名',
  `password` VARCHAR(255) NOT NULL COMMENT '密码哈希',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login_at` TIMESTAMP NULL
) ENGINE=InnoDB;

-- 管理员表
CREATE TABLE IF NOT EXISTS `admins` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(64) NOT NULL UNIQUE COMMENT '管理员用户名',
  `class` VARCHAR(64) NOT NULL COMMENT '负责班级（空为管理员）',
  `password` VARCHAR(255) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login_at` TIMESTAMP NULL
) ENGINE=InnoDB;

-- 用户设置表
CREATE TABLE IF NOT EXISTS `Settings` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `user` VARCHAR(64) NOT NULL UNIQUE COMMENT '关联用户名',
  `HomepageSettings` VARCHAR(32) NOT NULL DEFAULT 'list' COMMENT '默认首页',
  `HiddenFile` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '上传跳过隐藏文件',
  `ShowHiddenFiles` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '显示隐藏文件'
) ENGINE=InnoDB;

-- 毕业生信息表（原 FileUploadGraduationSubmission.Users 已迁移至此）
-- 包含基础信息及 12 种文档类型的状态记录
CREATE TABLE IF NOT EXISTS `graduation_information` (
  `ID` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `studentID` VARCHAR(32) NOT NULL UNIQUE COMMENT '学号',
  `name` VARCHAR(64) NOT NULL COMMENT '姓名',
  `class` VARCHAR(64) NOT NULL COMMENT '班级',
  -- 各文档类型字段（路径、提交时间、下载次数等）详见 graduation_config.php 配置
  -- ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### (2) 用户文件库 (`FileUploadS`)
用于存储普通用户的私有文件索引（动态分表）。

```sql
CREATE DATABASE IF NOT EXISTS `FileUploadS` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 注意：此库中不需要预先建表，系统会在用户首次登录或上传时自动创建 user_{username} 表。
```

> **注意**：旧版本的 `FileUploadGraduationSubmission` 数据库已废弃，毕业生数据现存储于主库的 `graduation_information` 表中。

### 2.2 配置文件

请在 `config/` 目录下确认或创建以下两个配置文件。

**1. `config/mysql.ini`** (连接 `FileUpload` 主库)
```ini
host="127.0.0.1"
port=3306
username="root"
password="your_password"
database="FileUpload"
charset="utf8mb4"
```

**2. `config/mysql_files.ini`** (连接 `FileUploadS` 文件库)
```ini
host="127.0.0.1"
port=3306
username="root"
password="your_password"
database="FileUploadS"
charset="utf8mb4"
```

> **注意**：旧版本的 `config/mysql_graduation.ini` 已不再需要，毕业生数据现已合并至主库。

---

## 3. 部署与安装

### 3.1 目录权限
确保 Web 服务器（如 `www-data` 或当前运行用户）对以下目录有**写权限**：

- `FileUploadGraduationSubmission/` (用于存储毕业文件)
- `uploads/` (如果用于存储普通文件，具体视代码配置而定，通常会自动创建)

### 3.2 启动服务

**开发环境（PHP 内置服务器）：**
在项目根目录下运行：
```bash
php -S 0.0.0.0:8000 -t .
```
访问 `http://localhost:8000/index.html` 即可。

**生产环境（Nginx + PHP-FPM）：**
Nginx 配置示例：
```nginx
server {
    listen 80;
    server_name example.com;
    root /path/to/project;
    index index.html index.php;

    # 禁止访问隐藏文件和配置目录
    location ~ /\.(?!well-known).* {
        deny all;
    }
    location /config/ {
        deny all;
    }

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php7.4-fpm.sock;
    }
}
```

---

## 4. 功能使用说明

### 4.1 普通用户
1. **注册/登录**：访问首页，输入纯数字账号（学号）和密码进行注册或登录。登录框现已采用居中悬浮玻璃设计。
2. **文件管理**：登录后默认进入文件列表，支持新建文件夹、上传文件（支持拖拽与大文件分片）、移动、删除、下载。
3. **文件重命名**：支持文件和文件夹重命名，文件后缀名不可更改，确保文件类型安全。
4. **共享文件**：在文件列表中点击“共享”可将文件/文件夹公开给其他用户。
5. **个性化设置**：在设置面板中可修改默认首页、切换是否显示隐藏文件。

### 4.2 毕业生
1. **身份识别**：当账号存在于 `FileUpload.graduation_information` 表中时，系统自动识别为毕业生。
2. **毕业提交**：点击侧边栏“毕业提交”，可提交 12 种类型的毕业文档。
   - **模板下载**：部分项目（如申请表、协议书）提供 Word 模板直接下载。
   - **格式限制**：大部分仅允许 PDF，劳动教育周表允许 Word 格式。
   - **自动命名**：文件会自动重命名为规范格式（学号+姓名+文档名）。
3. **更新提交**：重复提交会自动覆盖旧文件，并更新“最后提交时间”。

### 4.3 教师/管理员
1. **登录**：使用专用的教师账号登录（需预先在 `FileUpload.admins` 表中添加数据）。
   - `class` 字段为空表示管理员（可查看所有班级），非空表示普通教师（只能查看本班）。
2. **班级管理**：
   - **导入名单**：支持 Excel/CSV 批量导入学生名单（自动写入 `FileUpload.graduation_information`）。
   - **编辑学生**：修改学生姓名、班级信息。
3. **文件统计与审核**：
   - **概览**：查看各班级提交率饼图，采用新的三列布局。
   - **筛选**：按“未交/已交”筛选学生，支持多选导出 Excel 名单。
   - **打回**：可一键打回不合格的文档（将删除服务器文件并重置提交状态）。
   - **审批批阅**：
     - 点击学生姓名或“审批”按钮进入详情弹窗。
     - 使用“通过”或“不通过”按钮直接提交结果，系统自动跳转下一个待办。
     - 勾选“自动下一个”可连续批阅。
     - 列表页自动刷新，确保多人协作时状态同步。
   - **打包下载**：支持按班级、按学生批量打包下载所有提交的文件。
4. **文件管理**：
   - **按班级浏览**：查看各班级学生提交的文件列表（从数据库读取）。
   - **按类型浏览**：按文档类型查看所有学生的提交情况。
