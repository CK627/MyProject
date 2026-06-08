# 宁波旅游宣传网站 项目文档

## 📖 项目概述

宁波旅游宣传网站是一个完整的旅游信息展示平台，采用**纯 HTML/CSS/JavaScript + PHP + MySQL** 技术栈开发，致力于向游客全面展示宁波的文化底蕴、自然风光、美食住宿等旅游资源。

### 项目特点

- **前后端分离架构**：前端纯静态页面，后端 RESTful API 接口
- **响应式设计**：完美适配PC端、平板、移动端多种设备
- **管理后台**：提供完整的内容管理系统（CMS）
- **用户交互**：支持游客留言、景点评论等互动功能
- **数据驱动**：所有内容从数据库动态加载，便于维护更新

---

## 🏗️ 技术架构

### 前端技术栈

| 技术 | 说明 |
|------|------|
| HTML5 | 语义化标签，SEO优化 |
| CSS3 | Flexbox/Grid布局，CSS变量，动画效果 |
| JavaScript (ES5) | 原生JS，无框架依赖 |
| Google Fonts | Noto Serif SC 字体 |

### 后端技术栈

| 技术 | 说明 |
|------|------|
| PHP 7.4+ | 服务端脚本语言 |
| PDO | 数据库访问层 |
| MySQL 5.7+ | 关系型数据库 |
| Session | 用户认证机制 |

### 核心特性

- ✅ **图片懒加载**：使用 IntersectionObserver API 优化性能
- ✅ **滚动动画**：元素进入视口时触发动画效果
- ✅ **Toast 通知**：友好的操作反馈提示
- ✅ **搜索过滤**：前端实时搜索功能
- ✅ **分页加载**：API 支持分页查询
- ✅ **XSS 防护**：输入验证和HTML转义
- ✅ **SQL 注入防护**：使用 PDO 预编译语句

---

## 📁 项目结构

```
NingboTravelGuideWebsite/
├── api/                          # 后端 API 接口
│   ├── admin/                    # 后台管理模块
│   │   ├── login.php            # 管理员登录
│   │   ├── dashboard.php        # 后台首页仪表盘
│   │   ├── manage_spots.php     # 景点管理
│   │   ├── manage_foods.php     # 美食管理
│   │   ├── manage_accommodations.php  # 住宿管理
│   │   ├── manage_transports.php      # 交通管理
│   │   ├── manage_strategies.php      # 攻略管理
│   │   ├── manage_messages.php  # 留言管理
│   │   ├── manage_comments.php  # 评论管理
│   │   └── upload.php          # 文件上传处理
│   ├── config/                  # 配置文件
│   │   ├── db.php              # 数据库连接配置
│   │   └── init.sql            # 数据库初始化脚本
│   ├── includes/                # 公共模块
│   │   ├── auth.php            # 认证模块
│   │   └── functions.php       # 工具函数库
│   └── public/                  # 公开 API 接口
│       ├── get_spots.php       # 获取景点列表
│       ├── get_spot.php        # 获取景点详情
│       ├── get_foods.php       # 获取美食列表
│       ├── get_food.php        # 获取美食详情
│       ├── get_accommodations.php   # 获取住宿列表
│       ├── get_accommodation.php    # 获取住宿详情
│       ├── get_transports.php  # 获取交通列表
│       ├── get_transport.php   # 获取交通详情
│       ├── get_strategies.php  # 获取攻略列表
│       ├── get_strategy.php    # 获取攻略详情
│       ├── get_messages.php    # 获取留言列表
│       ├── submit_message.php  # 提交留言
│       ├── get_comments.php    # 获取评论列表
│       └── submit_comment.php  # 提交评论
├── css/                         # 样式文件
│   ├── common.css              # 全局通用样式
│   ├── index.css               # 首页样式
│   ├── scenic.css              # 景点页样式
│   ├── food.css                # 美食页样式
│   ├── accommodation.css       # 住宿页样式
│   ├── transport.css           # 交通页样式
│   ├── strategy.css            # 攻略页样式
│   ├── detail.css              # 详情页样式
│   └── guestbook.css           # 留言板样式
├── js/                          # 脚本文件
│   ├── common.js               # 公共脚本（导航、页脚、懒加载等）
│   ├── index.js                # 首页脚本
│   ├── scenic.js               # 景点页脚本
│   ├── food.js                 # 美食页脚本
│   ├── accommodation.js        # 住宿页脚本
│   ├── transport.js            # 交通页脚本
│   ├── strategy.js             # 攻略页脚本
│   ├── detail.js               # 详情页脚本
│   └── guestbook.js            # 留言板脚本
├── images/                      # 静态图片资源
│   ├── scenic/                 # 景点图片
│   ├── food/                   # 美食图片
│   ├── accommodation/          # 住宿图片
│   ├── transport/              # 交通图片
│   ├── strategy/               # 攻略图片
│   ├── index/                  # 首页图片
│   └── favicon.ico             # 网站图标
├── docs/                        # 项目文档
├── index.html                   # 首页
├── scenic.html                  # 景点页
├── food.html                    # 美食页
├── accommodation.html           # 住宿页
├── transport.html               # 交通页
├── strategy.html                # 攻略页
├── detail.html                  # 详情页（通用）
└── guestbook.html               # 游客留言板
```

---

## 🎯 核心功能模块

### 1. 前台展示系统

#### 1.1 首页 (index.html)

**功能特点：**
- Hero 大图轮播展示
- 四大板块导航（文化溯源、山水休闲、红色研学、美食体验）
- 精选景点动态加载（从数据库读取前3个）
- 美食推荐展示
- 数据统计动画（历史年数、景点数量等）
- 快速导航入口

**核心代码示例：**

```javascript
// js/index.js - 动态加载精选景点
function loadFeaturedSpots() {
  var grid = document.getElementById('featuredSpotsGrid');
  if (!grid) return;

  fetch('api/public/get_spots.php?pageSize=3')
    .then(function (res) { return res.json(); })
    .then(function (result) {
      if (result.code === 0 && result.data && result.data.list) {
        var spots = result.data.list;
        var html = '';

        spots.forEach(function (spot, index) {
          var imgSrc = spot.image || 'images/scenic/tianyi.png';
          var delay = (index + 1) * 0.1;
          var detailUrl = 'detail.html?id=' + encodeURIComponent(spot.id);

          html += '<a href="' + escapeAttr(detailUrl) + '" class="card">' +
            '<div class="card__image-wrapper">' +
              '<img data-src="' + escapeAttr(imgSrc) + '" class="card__image lazy-img">' +
              '<span class="card__badge">' + escapeHtml(spot.category) + '</span>' +
            '</div>' +
            '<div class="card__body">' +
              '<h3 class="card__title">' + escapeHtml(spot.name) + '</h3>' +
              '<p class="card__desc">' + escapeHtml(spot.description) + '</p>' +
            '</div>' +
          '</a>';
        });

        grid.innerHTML = html;
        initLazyLoad(); // 重新初始化懒加载
      }
    })
    .catch(function (err) {
      console.error('加载失败:', err);
    });
}
```

#### 1.2 景点模块 (scenic.html)

**功能特点：**
- 按分类筛选（自然风光/人文古迹/红色研学）
- 关键词搜索
- 卡片式展示
- 点击进入详情页

**数据表设计：**
```sql
CREATE TABLE `spots` (
    `id`             INT AUTO_INCREMENT PRIMARY KEY,
    `name`           VARCHAR(100) NOT NULL COMMENT '景点名称',
    `category`       VARCHAR(50)  NOT NULL COMMENT '分类',
    `description`    TEXT         COMMENT '景点描述',
    `image`          VARCHAR(255) DEFAULT '',
    `address`        VARCHAR(200) COMMENT '地址',
    `ticket`         VARCHAR(100) COMMENT '门票信息',
    `level`          VARCHAR(50)  COMMENT '景区等级',
    `detail_content` LONGTEXT     COMMENT '详细介绍（HTML格式）',
    `sort_order`     INT          DEFAULT 0,
    `created_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### 1.3 美食模块 (food.html)

**功能特点：**
- 按分类展示（海鲜/传统小吃/糕点甜品/特色菜肴）
- 美食图片展示
- 特色标签
- 详情页介绍

**数据表设计：**
```sql
CREATE TABLE `foods` (
    `id`             INT AUTO_INCREMENT PRIMARY KEY,
    `name`           VARCHAR(100) NOT NULL COMMENT '美食名称',
    `category`       VARCHAR(50)  NOT NULL COMMENT '分类',
    `description`    TEXT         COMMENT '简介',
    `image`          VARCHAR(255) DEFAULT '',
    `price_range`    VARCHAR(50)  COMMENT '价格区间',
    `recommend_shop` VARCHAR(200) COMMENT '推荐店铺',
    `detail_content` LONGTEXT     COMMENT '详细介绍',
    `sort_order`     INT          DEFAULT 0,
    `created_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### 1.4 住宿模块 (accommodation.html)

**功能特点：**
- 星级酒店/特色民宿分类
- 价格区间显示
- 地理位置标注
- 联系方式

#### 1.5 交通模块 (transport.html)

**功能特点：**
- 到达宁波方式（飞机/高铁/自驾）
- 市内交通（地铁/公交/出租车）
- 交通信息查询

#### 1.6 攻略模块 (strategy.html)

**功能特点：**
- 行程规划推荐
- 主题攻略（美食地图/购物指南/自驾游等）
- 实用贴士

#### 1.7 详情页 (detail.html)

**通用详情页设计**，支持多种类型：
- 景点详情（type=spot）
- 美食详情（type=food）
- 住宿详情（type=accommodation）
- 交通详情（type=transport）
- 攻略详情（type=strategy）

**核心功能：**
```javascript
// js/detail.js - 根据 URL 参数动态加载详情
function loadDetail() {
  var params = getUrlParams();
  var id = params.id;
  var type = params.type || 'spot'; // 默认景点类型

  var apiMap = {
    'spot': 'api/public/get_spot.php',
    'food': 'api/public/get_food.php',
    'accommodation': 'api/public/get_accommodation.php',
    'transport': 'api/public/get_transport.php',
    'strategy': 'api/public/get_strategy.php'
  };

  var apiUrl = apiMap[type] + '?id=' + encodeURIComponent(id);

  fetch(apiUrl)
    .then(function(res) { return res.json(); })
    .then(function(result) {
      if (result.code === 0 && result.data) {
        renderDetail(result.data, type);
      }
    });
}
```

**评论功能：**
- 用户可对景点/美食等发表评论
- 支持审核机制（后台可管理）

```sql
CREATE TABLE `comments` (
    `id`          INT AUTO_INCREMENT PRIMARY KEY,
    `item_type`   VARCHAR(50)  NOT NULL COMMENT '关联类型：spot/food/accommodation',
    `item_id`     INT          NOT NULL COMMENT '关联ID',
    `user_name`   VARCHAR(50)  NOT NULL COMMENT '用户昵称',
    `content`     TEXT         NOT NULL COMMENT '评论内容',
    `status`      TINYINT      DEFAULT 0 COMMENT '状态：0待审核/1已发布',
    `created_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP
);
```

#### 1.8 游客留言板 (guestbook.html)

**功能特点：**
- 游客可留言分享旅行感受
- 实时展示最新留言
- 昵称+内容+时间戳

**表单提交示例：**
```javascript
// js/guestbook.js - 提交留言
function submitMessage(e) {
  e.preventDefault();
  
  var name = document.getElementById('name').value.trim();
  var content = document.getElementById('content').value.trim();

  if (!name || !content) {
    showToast('请填写完整信息', 'error');
    return;
  }

  fetch('api/public/submit_message.php', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name, content: content })
  })
  .then(function(res) { return res.json(); })
  .then(function(result) {
    if (result.code === 0) {
      showToast('留言成功！', 'success');
      document.getElementById('messageForm').reset();
      loadMessages(); // 重新加载留言列表
    } else {
      showToast(result.message || '提交失败', 'error');
    }
  });
}
```

---

### 2. 后台管理系统

#### 2.1 登录认证 (api/admin/login.php)

**核心代码：**
```php
<?php
// api/includes/auth.php - 认证模块

/**
 * 验证管理员登录凭据
 */
function verifyAdmin($username, $password) {
    // 固定管理员账号（生产环境建议存储在数据库中）
    $adminUser = 'admin';
    $adminPass = '123456';
    
    return ($username === $adminUser && $password === $adminPass);
}

/**
 * 检查是否已登录
 */
function checkAuth() {
    if (!isset($_SESSION['admin_logged_in']) || $_SESSION['admin_logged_in'] !== true) {
        header('Location: login.php');
        exit;
    }
}

/**
 * 设置登录 Session
 */
function setLoginSession($username) {
    $_SESSION['admin_logged_in'] = true;
    $_SESSION['admin_username'] = $username;
    $_SESSION['login_time'] = time();
}
?>
```

#### 2.2 仪表盘 (api/admin/dashboard.php)

**功能特点：**
- 数据统计概览（景点数量、留言数量等）
- 快速导航入口
- 最新留言预览

#### 2.3 内容管理模块

**景点管理 (manage_spots.php)**
- 增加景点
- 编辑景点信息
- 删除景点
- 图片上传
- 排序调整

**核心代码示例：**
```php
<?php
// api/admin/manage_spots.php - 添加景点

if ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'add') {
    $name = sanitizeInput($_POST['name'] ?? '');
    $category = sanitizeInput($_POST['category'] ?? '');
    $description = sanitizeInput($_POST['description'] ?? '');
    $detail_content = $_POST['detail_content'] ?? '';
    $sort_order = intval($_POST['sort_order'] ?? 0);

    // 处理图片上传
    $imagePath = '';
    if (isset($_FILES['image']) && $_FILES['image']['error'] === UPLOAD_ERR_OK) {
        $uploaded = handleImageUpload($_FILES['image'], '../../images/scenic/');
        if ($uploaded) {
            $imagePath = str_replace('../../', '', $uploaded);
        }
    }

    // 插入数据库
    $stmt = $db->prepare("INSERT INTO spots (name, category, description, image, detail_content, sort_order) VALUES (:name, :category, :description, :image, :detail_content, :sort_order)");
    $stmt->execute([
        ':name' => $name,
        ':category' => $category,
        ':description' => $description,
        ':image' => $imagePath,
        ':detail_content' => $detail_content,
        ':sort_order' => $sort_order
    ]);
    
    $message = '景点添加成功';
}
?>
```

**其他管理模块（结构相同）：**
- `manage_foods.php` - 美食管理
- `manage_accommodations.php` - 住宿管理
- `manage_transports.php` - 交通管理
- `manage_strategies.php` - 攻略管理
- `manage_messages.php` - 留言管理
- `manage_comments.php` - 评论管理

---

### 3. 公共组件模块

#### 3.1 导航栏 (common.js)

**功能特点：**
- 响应式导航菜单
- 二级下拉菜单
- 滚动时背景变色
- 移动端汉堡菜单

**核心代码：**
```javascript
// js/common.js - 导航栏渲染
function renderNavbar() {
  const navItems = [
    { label: '首页', href: 'index.html', key: 'index.html' },
    {
      label: '景点', href: 'scenic.html', key: 'scenic.html',
      children: [
        { label: '自然风光', href: 'scenic.html#nature' },
        { label: '人文古迹', href: 'scenic.html#culture' },
        { label: '红色研学', href: 'scenic.html#red' }
      ]
    },
    // ... 其他菜单项
  ];

  // 动态生成导航HTML
  const navbarHTML = `
    <nav class="navbar" id="navbar">
      <div class="navbar__inner">
        <a href="index.html" class="navbar__brand">
          <img src="images/favicon.ico" alt="宁波旅游">
          宁波旅游
        </a>
        <ul class="navbar__menu">
          ${buildNavItems()}
        </ul>
        <button class="navbar__toggle" id="navToggle">
          <span></span><span></span><span></span>
        </button>
      </div>
    </nav>
  `;

  document.body.insertAdjacentHTML('afterbegin', navbarHTML);
  initNavbar();
}

// 初始化导航栏交互
function initNavbar() {
  const navbar = document.getElementById('navbar');
  
  // 滚动变色效果
  function handleScroll() {
    if (window.scrollY > 60) {
      navbar.classList.add('navbar--scrolled');
    } else {
      navbar.classList.remove('navbar--scrolled');
    }
  }
  
  window.addEventListener('scroll', handleScroll, { passive: true });
}
```

#### 3.2 页脚 (common.js)

**功能特点：**
- 站点信息
- 链接导航
- 联系方式
- 版权声明

#### 3.3 图片懒加载 (common.js)

**使用 IntersectionObserver API 实现性能优化：**

```javascript
// js/common.js - 懒加载实现
function initLazyLoad() {
  const images = document.querySelectorAll('img[data-src]');
  
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src; // 设置真实图片路径
          img.addEventListener('load', function () {
            img.classList.add('lazy-img--loaded'); // 添加加载完成样式
          });
          observer.unobserve(img); // 停止观察
        }
      });
    }, { rootMargin: '200px' }); // 提前200px开始加载

    images.forEach(function (img) {
      observer.observe(img);
    });
  } else {
    // 降级方案：直接加载所有图片
    images.forEach(function (img) {
      img.src = img.dataset.src;
      img.classList.add('lazy-img--loaded');
    });
  }
}
```

**HTML使用方式：**
```html
<!-- 使用 data-src 代替 src -->
<img data-src="images/scenic/tianyi.png" alt="天一阁" class="card__image lazy-img">
```

**CSS配合：**
```css
.lazy-img {
  opacity: 0;
  transition: opacity 0.3s ease;
}

.lazy-img--loaded {
  opacity: 1;
}
```

#### 3.4 滚动动画 (common.js)

**元素进入视口时触发动画：**

```javascript
// js/common.js - 滚动动画
function initScrollAnimations() {
  const elements = document.querySelectorAll('[data-animate]');
  
  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        const el = entry.target;
        const anim = el.dataset.animate || 'fade-in-up';
        const delay = el.dataset.delay || '0';
        el.style.animationDelay = delay + 's';
        el.classList.add('animate-' + anim);
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.1 });

  elements.forEach(function (el) {
    observer.observe(el);
  });
}
```

**HTML使用方式：**
```html
<div class="card" data-animate="fade-in-up" data-delay="0.2">
  <!-- 卡片内容 -->
</div>
```

**CSS动画定义：**
```css
@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fade-in-up 0.6s ease-out forwards;
}
```

#### 3.5 Toast 通知 (common.js)

**友好的操作反馈提示：**

```javascript
// js/common.js - Toast通知
function showToast(message, type) {
  type = type || 'success';
  
  // 移除旧的toast
  var old = document.querySelector('.toast');
  if (old) old.remove();

  var toast = document.createElement('div');
  toast.className = 'toast toast--' + type;
  toast.textContent = message;
  document.body.appendChild(toast);

  // 触发动画
  requestAnimationFrame(function () {
    toast.classList.add('toast--visible');
  });

  // 3秒后自动消失
  setTimeout(function () {
    toast.classList.remove('toast--visible');
    setTimeout(function () { toast.remove(); }, 300);
  }, 3000);
}
```

**使用方式：**
```javascript
showToast('留言提交成功！', 'success');
showToast('提交失败，请重试', 'error');
```

---

## 🔌 API 接口设计

### API 规范

**统一响应格式：**
```json
{
  "code": 0,           // 0=成功，非0=失败
  "message": "操作成功",
  "data": {
    "list": [...],     // 列表数据
    "total": 100,      // 总数
    "page": 1,         // 当前页
    "pageSize": 10     // 每页条数
  }
}
```

**错误响应格式：**
```json
{
  "code": 1,
  "message": "参数错误",
  "data": null
}
```

### 公开 API 接口

#### 获取景点列表
```
GET /api/public/get_spots.php

参数：
  ?category=自然风光    [可选] 按分类筛选
  &keyword=东钱湖      [可选] 关键词搜索
  &page=1             [可选] 页码，默认1
  &pageSize=10        [可选] 每页条数，默认10

返回：
{
  "code": 0,
  "message": "获取成功",
  "data": {
    "list": [
      {
        "id": 1,
        "name": "天一阁",
        "category": "人文古迹",
        "description": "中国现存最早的私家藏书楼...",
        "image": "images/scenic/tianyi.png",
        "address": "海曙区天一街10号",
        "ticket": "30元",
        "level": "5A景区",
        "sort_order": 1
      }
    ],
    "total": 15,
    "page": 1,
    "pageSize": 10
  }
}
```

#### 获取景点详情
```
GET /api/public/get_spot.php?id=1

返回：
{
  "code": 0,
  "message": "获取成功",
  "data": {
    "id": 1,
    "name": "天一阁",
    "category": "人文古迹",
    "description": "简介...",
    "detail_content": "<h2>详细介绍</h2><p>内容...</p>",
    "image": "images/scenic/tianyi.png",
    "address": "海曙区天一街10号",
    "ticket": "30元",
    "level": "5A景区"
  }
}
```

#### 提交留言
```
POST /api/public/submit_message.php
Content-Type: application/json

请求体：
{
  "name": "游客小明",
  "content": "宁波真美！"
}

返回：
{
  "code": 0,
  "message": "留言提交成功",
  "data": { "id": 123 }
}
```

#### 提交评论
```
POST /api/public/submit_comment.php
Content-Type: application/json

请求体：
{
  "item_type": "spot",
  "item_id": 1,
  "user_name": "游客",
  "content": "景色很美，值得一去！"
}

返回：
{
  "code": 0,
  "message": "评论提交成功，等待审核",
  "data": { "id": 456 }
}
```

### 核心工具函数

```php
<?php
// api/includes/functions.php

/**
 * 输入过滤（防止XSS）
 */
function sanitizeInput($input) {
    return htmlspecialchars(trim($input), ENT_QUOTES, 'UTF-8');
}

/**
 * 统一成功响应
 */
function successResponse($data = null, $message = '操作成功') {
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode([
        'code' => 0,
        'message' => $message,
        'data' => $data
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

/**
 * 统一错误响应
 */
function errorResponse($message = '操作失败', $code = 1) {
    header('Content-Type: application/json; charset=utf-8');
    http_response_code($code >= 400 ? $code : 200);
    echo json_encode([
        'code' => $code,
        'message' => $message,
        'data' => null
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

/**
 * 获取分页参数
 */
function getPagination() {
    $page = isset($_GET['page']) ? max(1, intval($_GET['page'])) : 1;
    $pageSize = isset($_GET['pageSize']) ? max(1, min(100, intval($_GET['pageSize']))) : 10;
    $offset = ($page - 1) * $pageSize;
    return [$page, $pageSize, $offset];
}

/**
 * 图片上传处理
 */
function handleImageUpload($file, $uploadDir) {
    $allowedExts = ['jpg', 'jpeg', 'png', 'gif'];
    $maxSize = 5 * 1024 * 1024; // 5MB
    
    $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
    
    if (!in_array($ext, $allowedExts)) {
        return false;
    }
    
    if ($file['size'] > $maxSize) {
        return false;
    }
    
    $filename = uniqid() . '.' . $ext;
    $filepath = $uploadDir . $filename;
    
    if (move_uploaded_file($file['tmp_name'], $filepath)) {
        return $filepath;
    }
    
    return false;
}
?>
```

---

## 🗄️ 数据库设计

### 核心数据表

#### 1. 景点表 (spots)
```sql
CREATE TABLE `spots` (
    `id`             INT AUTO_INCREMENT PRIMARY KEY COMMENT '景点ID',
    `name`           VARCHAR(100) NOT NULL COMMENT '景点名称',
    `category`       VARCHAR(50)  NOT NULL COMMENT '分类：自然风光/人文古迹/红色研学',
    `description`    TEXT         COMMENT '景点描述',
    `image`          VARCHAR(255) DEFAULT '' COMMENT '图片路径',
    `address`        VARCHAR(200) COMMENT '地址',
    `ticket`         VARCHAR(100) COMMENT '门票信息',
    `level`          VARCHAR(50)  COMMENT '景区等级（如5A/4A）',
    `detail_content` LONGTEXT     COMMENT '详细介绍（HTML格式）',
    `sort_order`     INT          DEFAULT 0 COMMENT '排序（数字越小越靠前）',
    `created_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (`category`),
    INDEX idx_sort (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='景点信息表';
```

#### 2. 美食表 (foods)
```sql
CREATE TABLE `foods` (
    `id`             INT AUTO_INCREMENT PRIMARY KEY COMMENT '美食ID',
    `name`           VARCHAR(100) NOT NULL COMMENT '美食名称',
    `category`       VARCHAR(50)  NOT NULL COMMENT '分类：海鲜/传统小吃/糕点甜品/特色菜肴',
    `description`    TEXT         COMMENT '简介',
    `image`          VARCHAR(255) DEFAULT '',
    `price_range`    VARCHAR(50)  COMMENT '价格区间',
    `recommend_shop` VARCHAR(200) COMMENT '推荐店铺',
    `detail_content` LONGTEXT     COMMENT '详细介绍',
    `sort_order`     INT          DEFAULT 0,
    `created_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='美食信息表';
```

#### 3. 住宿表 (accommodations)
```sql
CREATE TABLE `accommodations` (
    `id`             INT AUTO_INCREMENT PRIMARY KEY COMMENT '住宿ID',
    `name`           VARCHAR(100) NOT NULL COMMENT '住宿名称',
    `category`       VARCHAR(50)  NOT NULL COMMENT '分类：星级酒店/特色民宿',
    `description`    TEXT         COMMENT '简介',
    `image`          VARCHAR(255) DEFAULT '',
    `address`        VARCHAR(200) COMMENT '地址',
    `price_range`    VARCHAR(50)  COMMENT '价格区间',
    `contact`        VARCHAR(100) COMMENT '联系方式',
    `detail_content` LONGTEXT     COMMENT '详细介绍',
    `sort_order`     INT          DEFAULT 0,
    `created_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='住宿信息表';
```

#### 4. 交通表 (transports)
```sql
CREATE TABLE `transports` (
    `id`             INT AUTO_INCREMENT PRIMARY KEY COMMENT '交通ID',
    `name`           VARCHAR(100) NOT NULL COMMENT '交通方式名称',
    `category`       VARCHAR(50)  NOT NULL COMMENT '分类：到达宁波/市内交通',
    `description`    TEXT         COMMENT '简介',
    `image`          VARCHAR(255) DEFAULT '',
    `detail_content` LONGTEXT     COMMENT '详细介绍',
    `sort_order`     INT          DEFAULT 0,
    `created_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交通信息表';
```

#### 5. 攻略表 (strategies)
```sql
CREATE TABLE `strategies` (
    `id`             INT AUTO_INCREMENT PRIMARY KEY COMMENT '攻略ID',
    `name`           VARCHAR(100) NOT NULL COMMENT '攻略标题',
    `category`       VARCHAR(50)  NOT NULL COMMENT '分类：行程规划/攻略指南/实用贴士',
    `description`    TEXT         COMMENT '简介',
    `image`          VARCHAR(255) DEFAULT '',
    `detail_content` LONGTEXT     COMMENT '详细内容',
    `sort_order`     INT          DEFAULT 0,
    `created_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='旅游攻略表';
```

#### 6. 留言表 (messages)
```sql
CREATE TABLE `messages` (
    `id`         INT AUTO_INCREMENT PRIMARY KEY COMMENT '留言ID',
    `name`       VARCHAR(50) NOT NULL COMMENT '用户昵称',
    `content`    TEXT        NOT NULL COMMENT '留言内容',
    `created_at` DATETIME    DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created (`created_at` DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='游客留言表';
```

#### 7. 评论表 (comments)
```sql
CREATE TABLE `comments` (
    `id`         INT AUTO_INCREMENT PRIMARY KEY COMMENT '评论ID',
    `item_type`  VARCHAR(50)  NOT NULL COMMENT '关联类型：spot/food/accommodation/transport/strategy',
    `item_id`    INT          NOT NULL COMMENT '关联项目ID',
    `user_name`  VARCHAR(50)  NOT NULL COMMENT '用户昵称',
    `content`    TEXT         NOT NULL COMMENT '评论内容',
    `status`     TINYINT      DEFAULT 0 COMMENT '状态：0待审核/1已发布/2已拒绝',
    `created_at` DATETIME     DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_item (`item_type`, `item_id`),
    INDEX idx_status (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户评论表';
```

### 数据库初始化

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS `ningbo_tourism`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `ningbo_tourism`;

-- 执行以上所有表创建语句...

-- 插入示例数据
INSERT INTO `spots` (`name`, `category`, `description`, `image`, `sort_order`) VALUES
('天一阁博物院', '人文古迹', '中国现存最早的私家藏书楼，建于明嘉靖年间...', 'images/scenic/tianyi.png', 1),
('东钱湖', '自然风光', '浙江省最大的天然淡水湖...', 'images/scenic/dongqian.png', 2),
('溪口雪窦山', '自然风光', '国家级风景名胜区...', 'images/scenic/xikou.png', 3);
```

---

## 🎨 样式设计规范

### CSS 变量系统

```css
/* css/common.css - 设计变量 */
:root {
  /* 品牌色 */
  --color-primary: #B8763E;        /* 青铜金 */
  --color-primary-light: #D4A574;
  --color-primary-dark: #8E5A2A;
  
  --color-secondary: #3D7A5F;      /* 宁波绿 */
  --color-secondary-light: #5A9B7E;
  --color-secondary-dark: #2C5945;
  
  /* 中性色 */
  --color-text-primary: #2C1810;   /* 深棕色文字 */
  --color-text-secondary: #5E4D42;
  --color-text-tertiary: #9E8C7E;
  
  --color-bg: #FFFBF5;             /* 米白背景 */
  --color-bg-alt: #F5EFE6;         /* 浅米色 */
  --color-border: #E8DDD1;
  
  /* 间距 */
  --space-1: 0.25rem;  /* 4px */
  --space-2: 0.5rem;   /* 8px */
  --space-3: 0.75rem;  /* 12px */
  --space-4: 1rem;     /* 16px */
  --space-6: 1.5rem;   /* 24px */
  --space-8: 2rem;     /* 32px */
  --space-12: 3rem;    /* 48px */
  --space-16: 4rem;    /* 64px */
  
  /* 圆角 */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  
  /* 阴影 */
  --shadow-sm: 0 2px 8px rgba(44, 24, 16, 0.08);
  --shadow-md: 0 4px 16px rgba(44, 24, 16, 0.12);
  --shadow-lg: 0 8px 32px rgba(44, 24, 16, 0.16);
  
  /* 字体 */
  --font-serif: 'Noto Serif SC', serif;
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
}
```

### 响应式断点

```css
/* 移动端 */
@media (max-width: 768px) {
  .container {
    padding: 0 1rem;
  }
  
  .grid--3 {
    grid-template-columns: 1fr;
  }
}

/* 平板 */
@media (min-width: 769px) and (max-width: 1024px) {
  .grid--3 {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 桌面端 */
@media (min-width: 1025px) {
  .container {
    max-width: 1200px;
  }
  
  .grid--3 {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

### 卡片组件样式

```css
/* 卡片基础样式 */
.card {
  background: var(--color-bg);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: all 0.3s ease;
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.card__image-wrapper {
  position: relative;
  width: 100%;
  padding-top: 66.67%; /* 3:2 宽高比 */
  overflow: hidden;
  background: var(--color-bg-alt);
}

.card__image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.card:hover .card__image {
  transform: scale(1.05);
}

.card__badge {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 12px;
  background: rgba(184, 118, 62, 0.9);
  color: #fff;
  font-size: 0.875rem;
  border-radius: var(--radius-sm);
  backdrop-filter: blur(8px);
}

.card__body {
  padding: var(--space-6);
}

.card__title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.card__desc {
  font-size: 0.9375rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-4);
}

.card__meta {
  display: flex;
  gap: var(--space-4);
  font-size: 0.875rem;
  color: var(--color-text-tertiary);
}
```

---

## 🚀 部署指南

### 环境要求

- **Web服务器**：Apache 2.4+ 或 Nginx 1.18+
- **PHP**：7.4+ （推荐 8.0+）
- **MySQL**：5.7+ （推荐 8.0+）
- **PHP扩展**：
  - PDO
  - pdo_mysql
  - gd（图片处理）
  - session

### 部署步骤

#### 1. 上传文件

将项目文件上传至服务器 Web 根目录（如 `/var/www/html/` 或 `public_html/`）

#### 2. 配置数据库

```bash
# 登录 MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE ningbo_tourism CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 导入初始化脚本
mysql -u root -p ningbo_tourism < api/config/init.sql
```

#### 3. 修改数据库配置

编辑 `api/config/db.php`：

```php
define('DB_HOST', 'localhost');     // 数据库主机
define('DB_NAME', 'ningbo_tourism');// 数据库名
define('DB_USER', 'your_username'); // 数据库用户名
define('DB_PASS', 'your_password'); // 数据库密码
```

#### 4. 配置 Web 服务器

**Apache (.htaccess)**

```apache
# 开启 URL 重写
RewriteEngine On

# 防止目录浏览
Options -Indexes

# PHP 设置
php_value upload_max_filesize 10M
php_value post_max_size 10M
php_value max_execution_time 300
```

**Nginx (nginx.conf)**

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.0-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }

    location ~ /\.ht {
        deny all;
    }
}
```

#### 5. 设置文件权限

```bash
# 设置上传目录可写权限
chmod -R 755 images/
chown -R www-data:www-data images/

# API目录权限
chmod -R 755 api/
```

#### 6. 测试访问

- 前台首页：`http://yourdomain.com/index.html`
- 后台登录：`http://yourdomain.com/api/admin/login.php`
- 默认账号：`admin` / `123456`

#### 7. 安全配置（生产环境）

**修改管理员密码**：编辑 `api/includes/auth.php`

```php
function verifyAdmin($username, $password) {
    // 建议改为从数据库读取，并使用 password_hash() 加密
    $adminUser = 'your_admin';
    $adminPass = 'strong_password_here';
    return ($username === $adminUser && $password === $adminPass);
}
```

**禁用错误显示**：编辑 `php.ini` 或在 PHP 文件开头添加：

```php
ini_set('display_errors', 0);
error_reporting(E_ALL);
ini_set('log_errors', 1);
ini_set('error_log', '/path/to/error.log');
```

---

## 🔒 安全措施

### 1. XSS 防护

**输入过滤：**
```php
function sanitizeInput($input) {
    return htmlspecialchars(trim($input), ENT_QUOTES, 'UTF-8');
}
```

**输出转义：**
```javascript
function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}
```

### 2. SQL 注入防护

**使用 PDO 预编译语句：**
```php
$stmt = $db->prepare("SELECT * FROM spots WHERE id = :id");
$stmt->bindValue(':id', $id, PDO::PARAM_INT);
$stmt->execute();
```

### 3. CSRF 防护

**生成 Token：**
```php
// 生成 CSRF Token
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

// 验证 Token
if ($_POST['csrf_token'] !== $_SESSION['csrf_token']) {
    die('CSRF验证失败');
}
```

### 4. 文件上传安全

**限制文件类型和大小：**
```php
function handleImageUpload($file, $uploadDir) {
    $allowedExts = ['jpg', 'jpeg', 'png', 'gif'];
    $maxSize = 5 * 1024 * 1024; // 5MB
    
    // 验证扩展名
    $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
    if (!in_array($ext, $allowedExts)) {
        return false;
    }
    
    // 验证文件大小
    if ($file['size'] > $maxSize) {
        return false;
    }
    
    // 验证文件MIME类型
    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    $mime = finfo_file($finfo, $file['tmp_name']);
    $allowedMimes = ['image/jpeg', 'image/png', 'image/gif'];
    if (!in_array($mime, $allowedMimes)) {
        return false;
    }
    
    // 使用随机文件名
    $filename = uniqid() . '.' . $ext;
    $filepath = $uploadDir . $filename;
    
    if (move_uploaded_file($file['tmp_name'], $filepath)) {
        return $filepath;
    }
    
    return false;
}
```

### 5. Session 安全

```php
// 配置安全的 Session
ini_set('session.cookie_httponly', 1);
ini_set('session.cookie_secure', 1);   // HTTPS环境
ini_set('session.cookie_samesite', 'Strict');
ini_set('session.use_strict_mode', 1);

session_start();

// Session 超时检查
if (isset($_SESSION['login_time'])) {
    $sessionLifetime = 3600; // 1小时
    if (time() - $_SESSION['login_time'] > $sessionLifetime) {
        session_destroy();
        header('Location: login.php');
        exit;
    }
}
```

---

## 📊 性能优化

### 1. 图片优化

- 使用 WebP 格式（降低 30% 文件大小）
- 懒加载：非首屏图片延迟加载
- 响应式图片：根据设备尺寸加载不同大小

```html
<picture>
  <source srcset="image-small.webp" media="(max-width: 768px)" type="image/webp">
  <source srcset="image-large.webp" type="image/webp">
  <img data-src="image.jpg" alt="景点图片" class="lazy-img">
</picture>
```

### 2. CSS/JS 优化

- 压缩 CSS 和 JS 文件
- 合并文件减少 HTTP 请求
- 使用 CDN 加速静态资源

### 3. 数据库优化

**添加索引：**
```sql
-- 为常用查询字段添加索引
CREATE INDEX idx_category ON spots(category);
CREATE INDEX idx_sort ON spots(sort_order);
CREATE INDEX idx_status ON comments(status);
```

**查询优化：**
```php
// 只查询需要的字段
$stmt = $db->prepare("SELECT id, name, image FROM spots LIMIT 10");

// 使用 LIMIT 限制结果数量
```

### 4. 缓存策略

**浏览器缓存：**
```apache
# Apache .htaccess
<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresByType image/jpg "access plus 1 year"
  ExpiresByType image/png "access plus 1 year"
  ExpiresByType text/css "access plus 1 month"
  ExpiresByType application/javascript "access plus 1 month"
</IfModule>
```

**PHP输出缓存：**
```php
// 设置缓存头
header('Cache-Control: public, max-age=3600');
header('Expires: ' . gmdate('D, d M Y H:i:s', time() + 3600) . ' GMT');
```

---

## 📝 使用说明

### 管理员操作手册

#### 登录后台
1. 访问 `/api/admin/login.php`
2. 输入用户名：`admin`，密码：`123456`
3. 登录成功后进入仪表盘

#### 管理景点
1. 点击「景点管理」菜单
2. 添加景点：填写名称、分类、描述、上传图片
3. 编辑景点：点击「编辑」按钮修改信息
4. 删除景点：点击「删除」按钮（需确认）
5. 调整排序：修改「排序」字段，数字越小越靠前

#### 管理留言
1. 点击「留言管理」菜单
2. 查看所有游客留言
3. 删除不当留言

#### 管理评论
1. 点击「评论管理」菜单
2. 审核待发布的评论
3. 通过/拒绝评论

### 游客使用指南

#### 浏览景点
1. 进入「景点」页面
2. 点击分类标签筛选
3. 使用搜索框查找景点
4. 点击卡片查看详情

#### 发表评论
1. 在详情页底部找到评论区
2. 填写昵称和评论内容
3. 提交后等待审核

#### 留言板
1. 进入「留言」页面
2. 填写昵称和留言内容
3. 提交后立即显示

---

## 🛠️ 开发技巧

### 添加新的内容类型

假设要添加「节日活动」模块，步骤如下：

#### 1. 创建数据表
```sql
CREATE TABLE `festivals` (
    `id`             INT AUTO_INCREMENT PRIMARY KEY,
    `name`           VARCHAR(100) NOT NULL,
    `date`           VARCHAR(50),
    `description`    TEXT,
    `image`          VARCHAR(255),
    `detail_content` LONGTEXT,
    `sort_order`     INT DEFAULT 0,
    `created_at`     DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2. 创建 API 接口

**api/public/get_festivals.php**（参考 `get_spots.php`）
**api/public/get_festival.php**（参考 `get_spot.php`）

#### 3. 创建后台管理

**api/admin/manage_festivals.php**（参考 `manage_spots.php`）

#### 4. 创建前台页面

**festivals.html**（参考 `scenic.html`）
**js/festivals.js**（参考 `scenic.js`）
**css/festivals.css**（参考 `scenic.css`）

#### 5. 更新导航菜单

编辑 `js/common.js` 的 `navItems` 数组，添加节日活动菜单项。

### 修改颜色主题

编辑 `css/common.css` 中的 CSS 变量：

```css
:root {
  --color-primary: #your-color;     /* 主色调 */
  --color-secondary: #your-color;   /* 辅助色 */
  /* ... */
}
```

所有使用该变量的地方会自动更新。

---

## 📖 常见问题 (FAQ)

### Q1: 数据库连接失败？
**A:** 检查 `api/config/db.php` 中的数据库配置是否正确，确保 MySQL 服务已启动。

### Q2: 图片上传失败？
**A:** 检查 `images/` 目录是否有写入权限（`chmod 755` 或 `777`），确保 PHP 上传大小限制足够（`upload_max_filesize`）。

### Q3: API 返回 404 错误？
**A:** 检查 Web 服务器配置是否正确，确保 PHP 文件可以被正确解析。

### Q4: 后台无法登录？
**A:** 确认用户名密码正确（默认 `admin`/`123456`），检查 Session 是否正常工作。

### Q5: 图片懒加载不工作？
**A:** 检查浏览器是否支持 `IntersectionObserver` API，旧版浏览器会自动降级为直接加载。

### Q6: 移动端菜单无法打开？
**A:** 检查 JavaScript 是否正确加载，打开浏览器控制台查看是否有错误。

---

## 📚 扩展阅读

### 技术文档
- [PHP PDO 文档](https://www.php.net/manual/zh/book.pdo.php)
- [IntersectionObserver API](https://developer.mozilla.org/zh-CN/docs/Web/API/Intersection_Observer_API)
- [MySQL 性能优化](https://dev.mysql.com/doc/refman/8.0/en/optimization.html)

### 设计参考
- [Material Design](https://material.io/design)
- [CSS Grid 布局](https://developer.mozilla.org/zh-CN/docs/Web/CSS/CSS_Grid_Layout)
- [Flexbox 布局](https://developer.mozilla.org/zh-CN/docs/Web/CSS/CSS_Flexible_Box_Layout)

---

## 👥 贡献者

本项目为毕业设计作品，由 **JJ** 开发完成。

---

## 📄 许可证

本项目仅用于学习和毕业设计展示，未经许可不得用于商业用途。

---

## 📮 联系方式

- **项目地址**：`/Users/jj/Documents/MyCode/NingboTravelGuideWebsite`
- **邮箱**：tour@ningbo.cn
- **电话**：0574-12345678

---

<div align="center">

**宁波旅游宣传网站** © 2025 