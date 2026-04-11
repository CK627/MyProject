# 宁波旅游宣传网站 (Ningbo Travel Guide Website)

> 一个完整的前后端分离旅游信息展示平台，致力于向游客全面展示宁波的文化底蕴、自然风光、美食住宿等旅游资源。

## 📖 项目简介

本项目是一个综合性的旅游宣传网页应用，采用响应式布局设计，完美适配 PC 端与移动端。
系统分为**前台展示**和**后台管理**两大部分：
- **前台展示**：游客可浏览宁波的著名景点、特色美食、精选住宿、交通指南以及旅游攻略，并支持留言板互动。
- **后台管理**：管理员可以对景点的分类、内容信息、用户留言及评论进行维护与审核。

## 🌟 主要功能与特性

- **纯原生前端实现**：无需依赖复杂的前端框架，采用 HTML5, CSS3, 原生 JavaScript 构建，代码轻量且便于二次开发。
- **响应式设计 (Responsive Design)**：通过 CSS 媒体查询，实现多终端（手机、平板、桌面）的良好视觉体验。
- **性能优化机制**：实现了基于原生 JS 的**图片懒加载 (Lazy Loading)**，有效减少初始加载带宽，提升首屏速度。
- **互动模块**：内置用户留言板及评论系统。
- **管理后台系统**：内置轻量级的 PHP 后台内容管理面板。

## 🛠 技术架构与核心栈

- **前端技术**：HTML5, CSS3, 原生 JavaScript (Vanilla JS)
- **后端技术**：PHP 7.4+ (基于 PDO 扩展的安全数据库操作)
- **数据库**：MySQL 5.7+ (推荐 8.0+)
- **架构模式**：前后端分离思想的轻量化实现，前端通过 Fetch API/AJAX 请求后端接口渲染数据。

## ⚙️ 环境配置与安装

### 1. 前置要求
- 任意支持 PHP 的 Web 服务器软件（推荐使用 XAMPP / WAMP / MAMP，或 Nginx + PHP-FPM）。
- MySQL 数据库服务。

### 2. 数据库初始化
1. 登录你的 MySQL 数据库，创建一个新库（建议字符集为 `utf8mb4`）：
   ```sql
   CREATE DATABASE <DB_NAME> CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
2. 将项目根目录下的 `api/config/init.sql` 导入到刚创建的数据库中以初始化表结构和默认数据。

### 3. 项目配置修改
1. 进入 `api/config/` 目录。
2. 复制或重命名 `db.php.example` 为 `db.php`。
3. 编辑 `db.php`，将里面的占位符替换为你本地实际的数据库配置：
   ```php
   define('DB_HOST', '<DB_HOST>');       // 数据库主机地址，通常是 127.0.0.1
   define('DB_NAME', '<DB_NAME>');       // 你创建的数据库名
   define('DB_USER', '<DB_USER>');       // 数据库用户名
   define('DB_PASS', '<DB_PASSWORD>');   // 数据库密码
   ```

### 4. 后台管理员配置
在 `api/includes/auth.php` 中配置管理员的默认账号密码：
```php
$adminUser = '<ADMIN_USER>';
$adminPass = '<ADMIN_PASSWORD>';
```

## 🚀 启动与使用

1. 将整个 `NingboTravelGuideWebsite` 目录放置在你的 Web 服务器的运行目录（如 XAMPP 的 `htdocs` 或 Nginx 的 `html`）下。
2. **前台访问**：浏览器打开 `http://localhost/NingboTravelGuideWebsite/index.html` 即可浏览。
3. **后台管理**：浏览器打开 `http://localhost/NingboTravelGuideWebsite/api/admin/login.php` 登录并管理内容。

## 📁 项目目录结构说明

```text
NingboTravelGuideWebsite/
├── api/                  # PHP 后端接口及逻辑处理
│   ├── admin/            # 后台管理页面与接口
│   ├── config/           # 数据库配置及 SQL 初始化文件
│   ├── includes/         # 公共函数、认证逻辑
│   └── public/           # 前台数据读取接口 (GET)
├── css/                  # 前端样式表
├── docs/                 # 开发文档、说明文档
├── images/               # 前端引用的静态图片资源
├── js/                   # 前端 JavaScript 逻辑文件
└── *.html                # 前端静态页面 (index, scenic, food 等)
```

## 📅 未来规划 (Roadmap)

- [ ] **接口安全增强**：为敏感的后台 API 引入 JWT 或更严格的 Session/CSRF 校验机制。
- [ ] **密码加密升级**：将硬编码的管理员密码迁移至数据库，并采用 `password_hash()` 算法进行加密存储。
- [ ] **图片上传功能**：为后台管理面板增加可视化图片上传和裁剪功能。
- [ ] **全站搜索引擎**：增加基于 MySQL 模糊查询或 ElasticSearch 的景点/美食全局搜索框。
