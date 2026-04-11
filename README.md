# 衢州古城文化旅游信息平台 (Responsive Qujiang Travel Information Platform)

> 一个为衢州衢江区量身定制的现代化、响应式文化旅游信息展示平台。旨在通过前沿的前端网页设计，全方位呈现当地独特的景点、特色美食、旅游线路以及深厚的民俗文化。

## 📖 项目简介

**衢州古城文化旅游信息平台** 是一个纯前端静态网页项目。它通过现代化的响应式布局，完美适配了桌面端（PC）、平板以及移动端（手机）设备的访问需求。该项目结构清晰，没有复杂的后端依赖，非常适合作为旅游宣传、文化展示或前端网页设计学习的参考范例。

## 🌟 主要功能与特性

- **100% 响应式设计 (Responsive Design)**：利用 CSS3 媒体查询（Media Queries）及 Flexbox/Grid 布局，实现在不同屏幕尺寸下的优雅降级与适配。
- **透明/沉浸式导航栏**：页面滚动时，导航栏可平滑过渡样式，提升用户视觉体验。
- **动态交互组件**：
  - **Tab 切换**：通过 JavaScript 和轻量级 Vue.js (CDN) 实现内容板块的快速无刷新切换。
  - **图片懒加载 (Lazy Loading)**：首屏渲染加速，滚动到可视区域再加载图片，大幅节省带宽。
  - **平滑滚动 (Smooth Scroll)**：锚点跳转时提供顺滑的过渡动画。
- **丰富的展示板块**：
  - 首页概览 (Index)
  - 景点介绍 (Scenic)
  - 地方美食 (Food)
  - 旅游线路规划 (Route)
  - 历史文化与民俗 (Culture)

## 🛠 技术栈

本项目属于纯前端（Static Web App）架构，依赖如下：

- **结构与样式**：HTML5, CSS3 (原生 CSS，未使用预处理器，易于阅读)
- **脚本逻辑**：原生 JavaScript (Vanilla JS) 搭配 Vue.js (仅通过 CDN 引入作为部分数据绑定的辅助)
- **图标与字体**：可能使用了部分开源 Web Font 或 Iconfont
- **无后端依赖**：所有数据（景点文字、图片路径等）均以静态 JSON 格式或硬编码在 HTML/JS 中。

## 🚀 启动与使用步骤

由于本平台为纯前端静态页面，无需安装数据库或配置后端环境。

### 方法一：直接运行（最简单）
1. 克隆或下载本代码库。
2. 使用浏览器（如 Chrome、Edge、Firefox）直接双击打开项目根目录下的 `index.html` 文件即可。

### 方法二：使用本地开发服务器（推荐）
为了确保某些本地资源（如 `fetch` 请求或 Vue.js 渲染）不受浏览器本地文件跨域策略（CORS）的限制，建议通过轻量级服务器运行：

- **如果你使用 VS Code**：
  安装 `Live Server` 插件，右键点击 `index.html` 选择 "Open with Live Server"。
- **如果你有 Python 环境**：
  在项目根目录下运行以下命令，然后在浏览器访问 `http://localhost:8000`：
  ```bash
  # Python 3
  python -m http.server 8000
  ```
- **如果你有 Node.js 环境**：
  使用 `serve` 或 `http-server`：
  ```bash
  npx serve .
  ```

## 📁 目录结构说明

```text
ResponsiveQujiangTravelInformationPlatform/
├── css/             # 存放各页面的样式文件 (如 index.css, style.css)
├── js/              # 存放页面交互逻辑脚本 (如 app.js, main.js)
├── images/          # 存放页面中用到的各类图片素材
├── docs/            # 存放项目的相关设计文档或说明资料
├── index.html       # 网站首页
├── scenic.html      # 景点介绍页
├── food.html        # 特色美食页
├── route.html       # 旅游线路规划页
├── culture.html     # 民俗文化介绍页
└── detail.html      # 详情展示页模板
```

## 📅 未来规划 (Roadmap)

虽然目前是静态页面，但未来可扩展方向如下：
- [ ] **接入后端 API**：利用 Node.js 或 PHP 构建后端，将硬编码的数据转移至数据库（如 MySQL），实现旅游资讯的动态后台管理。
- [ ] **集成地图服务**：接入高德地图/百度地图 API，为游客提供精确的景点定位和路线导航功能。
- [ ] **用户交互模块**：新增用户注册登录系统，增加景点打分、评论留言以及收藏功能。
- [ ] **多语言支持 (i18n)**：增加中英文一键切换，方便外国游客浏览。
