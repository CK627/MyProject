# 衢州古城文化旅游信息平台

一个响应式的文化旅游信息展示平台，基于衢州古城文化旅游区官方网站风格设计，展示衢江地区的景点、美食、旅游线路和民俗文化。

## 目录

- [项目预览](#项目预览)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [功能特性](#功能特性)
- [核心代码实现](#核心代码实现)
- [快速开始](#快速开始)
- [设计规范](#设计规范)
- [开发指南](#开发指南)
- [浏览器支持](#浏览器支持)
- [许可证](#许可证)

---

## 项目预览

### 桌面端
- 首页轮播、景点推荐、美食展示
- 透明导航栏叠加在Banner图片上
- 三栏详情页布局

### 移动端
- 响应式布局自适应
- 汉堡菜单导航
- 触摸友好的交互

---

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| HTML5 | - | 语义化结构 |
| CSS3 | - | 样式与动画 |
| JavaScript | ES6+ | 交互逻辑 |
| Vue.js | 3.x (CDN) | 组件化开发 |

---

## 项目结构

```
ResponsiveQujiangTravelInformationPlatform/
├── index.html              # 首页
├── scenic.html             # 景点推荐页
├── food.html               # 美食推荐页
├── route.html              # 旅游线路页
├── culture.html            # 民俗文化页
├── detail.html             # 详情页（通用模板）
├── css/
│   ├── common.css          # 公共样式（导航、页脚、通用组件）
│   ├── index.css           # 首页专属样式
│   ├── scenic.css          # 景点页样式
│   ├── food.css            # 美食页样式
│   ├── route.css           # 线路页样式
│   ├── culture.css         # 民俗页样式
│   └── detail.css          # 详情页样式
├── js/
│   ├── common.js           # 公共组件（导航、页脚、卡片）
│   ├── data.js             # 数据源（景点、美食、线路、民俗）
│   ├── index.js            # 首页逻辑
│   ├── scenic.js           # 景点页逻辑
│   ├── food.js             # 美食页逻辑
│   ├── route.js            # 线路页逻辑
│   ├── culture.js          # 民俗页逻辑
│   └── detail.js           # 详情页逻辑
├── images/
│   ├── logo.png            # 网站Logo
│   ├── favicon.ico         # 网站图标
│   ├── apple-touch-icon.png # iOS图标
│   ├── index/              # 首页图片
│   ├── scenic/             # 景点图片
│   ├── food/               # 美食图片
│   ├── route/              # 线路图片
│   └── culture/            # 民俗图片
└── README.md               # 项目说明
```

---

## 功能特性

### 1. 响应式透明导航栏
- 透明背景叠加在Banner上
- 滚动后变为深色半透明
- 移动端汉堡菜单

### 2. 分类Tab切换
- Hash路由实现（#nature, #culture）
- 无刷新切换内容
- URL可分享

### 3. 详情页三栏布局
- 左侧：相关推荐
- 中间：主内容（图片、介绍）
- 右侧：基本信息

### 4. 图片懒加载
- IntersectionObserver API
- 占位符过渡动画

### 5. Vue组件化
- SiteHeader 导航组件
- SiteFooter 页脚组件
- SpotCard 卡片组件

---

## 核心代码实现

### 1. Vue应用初始化 (common.js)

```javascript
/* 创建页面应用 */
function createPageApp(options) {
  return Vue.createApp({
    ...options,
    components: {
      'site-header': SiteHeader,
      'site-footer': SiteFooter,
      'spot-card': SpotCard
    }
  });
}

/* 通用初始化 */
function commonInit() {
  initLazyLoad();
  initBackToTop();
}
```

### 2. 导航组件 (common.js)

```javascript
const SiteHeader = {
  props: {
    current: { type: String, default: '' }
  },
  data() {
    return {
      mobileOpen: false,
      scrolled: false,
      navItems: [
        { name: '首页', key: 'index', href: 'index.html', children: null },
        {
          name: '景点',
          key: 'scenic',
          href: 'scenic.html',
          children: [
            { name: '自然风光', href: 'scenic.html#nature' },
            { name: '人文古迹', href: 'scenic.html#culture' }
          ]
        },
        // ... 更多导航项
      ]
    };
  },
  mounted() {
    window.addEventListener('scroll', this.onScroll);
  },
  methods: {
    onScroll() {
      this.scrolled = window.scrollY > 10;
    },
    toggleMobile() {
      this.mobileOpen = !this.mobileOpen;
    }
  },
  template: `
    <header class="site-header" :class="{ scrolled }">
      <div class="header-inner">
        <a href="index.html" class="site-logo">
          <img src="images/logo.png" alt="衢州古城文化旅游区" class="logo-img">
        </a>
        <nav class="main-nav" :class="{ open: mobileOpen }">
          <div class="nav-item" v-for="item in navItems" :key="item.key">
            <a :href="item.href" class="nav-link" :class="{ active: current === item.key }">
              {{ item.name }}
              <span v-if="item.children" class="nav-arrow">▾</span>
            </a>
            <div v-if="item.children" class="sub-nav">
              <a v-for="sub in item.children" :key="sub.name"
                 :href="sub.href" class="sub-nav-link">{{ sub.name }}</a>
            </div>
          </div>
        </nav>
        <button class="mobile-menu-btn" :class="{ open: mobileOpen }" @click="toggleMobile">
          <span></span><span></span><span></span>
        </button>
      </div>
    </header>
  `
};
```

### 3. 卡片组件 (common.js)

```javascript
const SpotCard = {
  props: ['item', 'type'],
  computed: {
    detailUrl() {
      if (!this.type || !this.item.id) return null;
      return `detail.html?type=${this.type}&id=${this.item.id}`;
    }
  },
  template: `
    <a :href="detailUrl" class="card card-link" v-if="detailUrl">
      <div class="card-img-wrap">
        <img :data-src="item.img" :alt="item.name" class="card-img lazy">
      </div>
      <div class="card-body">
        <span class="card-tag">{{ item.tag }}</span>
        <h3 class="card-title">{{ item.name }}</h3>
        <p class="card-desc">{{ item.desc }}</p>
      </div>
    </a>
    <div class="card" v-else>
      <!-- 无链接版本 -->
    </div>
  `
};
```

### 4. 图片懒加载 (common.js)

```javascript
function initLazyLoad() {
  const lazyImages = document.querySelectorAll('img.lazy, img[data-src]');
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        const src = img.dataset.src;
        if (src) {
          img.src = src;
          img.removeAttribute('data-src');
          img.classList.remove('lazy');
          img.classList.add('loaded');
        }
        observer.unobserve(img);
      }
    });
  }, {
    rootMargin: '200px'
  });

  lazyImages.forEach(img => observer.observe(img));
  
  // 监听DOM变化，处理动态添加的图片
  const mutationObserver = new MutationObserver((mutations) => {
    mutations.forEach(mutation => {
      mutation.addedNodes.forEach(node => {
        if (node.nodeType === 1) {
          const newImages = node.querySelectorAll 
            ? node.querySelectorAll('img.lazy, img[data-src]') 
            : [];
          newImages.forEach(img => observer.observe(img));
        }
      });
    });
  });
  
  mutationObserver.observe(document.body, { childList: true, subtree: true });
}
```

### 5. Hash路由切换 (scenic.js)

```javascript
const app = createPageApp({
  data() {
    return {
      activeTab: 'all',
      nature: SITE_DATA.scenic.nature,
      culture: SITE_DATA.scenic.culture
    };
  },
  watch: {
    activeTab() {
      this.$nextTick(() => initLazyLoad());
    }
  },
  mounted() {
    commonInit();
  }
});

const vm = app.mount('#app');

// Hash路由处理
function applyHashScenic() {
  const hash = window.location.hash;
  if (hash === '#nature') vm.activeTab = 'nature';
  else if (hash === '#culture') vm.activeTab = 'culture';
}

applyHashScenic();
window.addEventListener('hashchange', applyHashScenic);
```

### 6. 详情页URL参数解析 (detail.js)

```javascript
// 获取URL参数
function getUrlParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    type: params.get('type'),
    id: parseInt(params.get('id'))
  };
}

// 根据类型获取数据源
function getDataSource(type) {
  switch (type) {
    case 'scenic':
      return [...SITE_DATA.scenic.nature, ...SITE_DATA.scenic.culture];
    case 'food':
      return [...SITE_DATA.food.snacks, ...SITE_DATA.food.dishes];
    case 'route':
      return [...SITE_DATA.routes.oneDay, ...SITE_DATA.routes.deep];
    case 'culture':
      return [...SITE_DATA.culture.festivals, ...SITE_DATA.culture.crafts];
    default:
      return [];
  }
}

// 获取返回链接
function getBackUrl(type) {
  const urls = {
    scenic: 'scenic.html',
    food: 'food.html',
    route: 'route.html',
    culture: 'culture.html'
  };
  return urls[type] || 'index.html';
}

const app = createPageApp({
  data() {
    const { type, id } = getUrlParams();
    const dataSource = getDataSource(type);
    const item = dataSource.find(d => d.id === id) || null;
    
    return {
      type,
      item,
      error: item ? null : '未找到相关内容',
      currentImageIndex: 0,
      backUrl: getBackUrl(type)
    };
  },
  computed: {
    currentImage() {
      if (this.item?.gallery?.length) {
        return this.item.gallery[this.currentImageIndex];
      }
      return this.item?.img;
    },
    relatedItems() {
      if (!this.item) return [];
      const dataSource = getDataSource(this.type);
      return dataSource
        .filter(d => d.id !== this.item.id)
        .slice(0, 4);
    }
  },
  methods: {
    formatContent(content) {
      if (!content) return '';
      return content.split('\n').map(p => p.trim())
        .filter(p => p).map(p => `<p>${p}</p>`).join('');
    },
    goDetail(item) {
      window.location.href = `detail.html?type=${this.type}&id=${item.id}`;
    }
  },
  mounted() {
    if (this.item) {
      document.title = `${this.item.name} - ${this.type === 'scenic' ? '景点' : 
        this.type === 'food' ? '美食' : this.type === 'route' ? '线路' : '民俗'} - 衢江文化旅游信息平台`;
    }
    commonInit();
  }
});

app.mount('#app');
```

### 7. 数据结构 (data.js)

```javascript
const SITE_DATA = {
  // 景点数据
  scenic: {
    nature: [
      {
        id: 1,
        name: '乌溪江风景区',
        desc: '乌溪江水清澈碧绿，两岸山峦叠翠...',
        tag: '自然风光',
        img: 'images/scenic/wuxijiang.jpg',
        detail: `乌溪江是钱塘江上游的重要支流...`,
        gallery: [
          'images/scenic/wuxijiang.jpg',
          'images/scenic/wuxijiang2.jpg'
        ],
        address: '浙江省衢州市衢江区乌溪江沿线',
        openTime: '全天开放',
        ticket: '免费',
        traffic: '从衢州市区出发，沿G60沪昆高速...',
        tips: '建议穿着舒适的运动鞋...',
        highlights: ['清澈碧绿的江水', '原生态峡谷风光', '竹筏漂流体验', '清水鱼垂钓']
      },
      // ... 更多景点
    ],
    culture: [
      // 人文古迹数据
    ]
  },
  
  // 美食数据
  food: {
    snacks: [
      {
        id: 1,
        name: '衢州烤饼',
        desc: '衢州烤饼外酥内嫩，馅料丰富...',
        tag: '特色小吃',
        img: 'images/food/kaobing.jpg',
        detail: `衢州烤饼是衢州最具特色的传统小吃...`,
        // ...
      }
    ],
    dishes: [
      // 地方菜肴数据
    ]
  },
  
  // 线路数据
  routes: {
    oneDay: [
      {
        id: 1,
        name: '衢江山水一日游',
        desc: '上午游览天脊龙门景区...',
        highlights: ['天脊龙门', '农家午餐', '药王山'],
        duration: '1天',
        difficulty: '轻松',
        img: 'images/scenic/tianjilongmen.jpg',
        detail: `【行程安排】
08:00 从衢州市区出发
09:30 抵达天脊龙门景区...`,
        // ...
      }
    ],
    deep: [
      // 深度游数据
    ]
  },
  
  // 民俗数据
  culture: {
    festivals: [
      // 传统节日数据
    ],
    crafts: [
      // 民间技艺数据
    ]
  }
};
```

### 8. 透明导航栏样式 (common.css)

```css
/* 导航栏 - 透明背景 */
.site-header {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 1000;
  background: transparent;
  transition: var(--transition);
}

/* 滚动后变深色 */
.site-header.scrolled {
  background: rgba(44, 27, 16, 0.95);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: var(--shadow-md);
}

/* 导航链接 - 白色文字 */
.nav-link {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 18px;
  font-size: 0.95rem;
  font-weight: 500;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0,0,0,0.3);
  transition: var(--transition-fast);
}

.nav-link:hover,
.nav-link.active {
  color: var(--color-accent);
}

/* 二级导航 - 玻璃效果 */
.sub-nav {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  min-width: 150px;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  opacity: 0;
  visibility: hidden;
  transition: var(--transition-fast);
}

.nav-item:hover .sub-nav {
  opacity: 1;
  visibility: visible;
}
```

### 9. 详情页三栏布局 (detail.css)

```css
/* 三栏布局 */
.detail-layout-three {
  display: grid;
  grid-template-columns: 240px 1fr 280px;
  gap: var(--space-lg);
  align-items: start;
}

/* 左侧 - 相关推荐 */
.detail-left {
  position: sticky;
  top: calc(var(--nav-height) + var(--space-lg));
}

.related-item {
  display: flex;
  gap: var(--space-sm);
  padding: var(--space-sm);
  background: var(--color-bg-warm);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition);
}

.related-item:hover {
  background: var(--color-bg-section);
  transform: translateX(4px);
}

/* 中间 - 主内容 */
.detail-main {
  min-width: 0;
}

/* 右侧 - 侧边栏 */
.detail-sidebar {
  position: sticky;
  top: calc(var(--nav-height) + var(--space-lg));
}

/* 响应式 */
@media (max-width: 1024px) {
  .detail-layout-three {
    grid-template-columns: 1fr;
  }
  
  .detail-left,
  .detail-sidebar {
    position: static;
  }
}
```

### 10. 移动端导航样式 (common.css)

```css
@media (max-width: 768px) {
  .main-nav {
    position: fixed;
    top: var(--nav-height);
    left: 0;
    right: 0;
    background: rgba(0, 0, 0, 0.85);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    flex-direction: column;
    padding: var(--space-md) var(--space-lg);
    transform: translateY(-100%);
    opacity: 0;
    visibility: hidden;
    transition: var(--transition);
  }

  .main-nav.open {
    transform: translateY(0);
    opacity: 1;
    visibility: visible;
  }

  .nav-link {
    padding: 14px 16px;
    color: #fff;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .sub-nav {
    position: static;
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: none;
  }

  .mobile-menu-btn {
    display: flex;
  }

  .mobile-menu-btn span {
    background: #fff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  }
}
```

### 11. CSS设计令牌 (common.css)

```css
:root {
  /* 颜色 */
  --color-primary: #7A3B2E;
  --color-primary-light: #9C5A4D;
  --color-accent: #C4A265;
  --color-accent-light: #D4B885;
  
  /* 背景 */
  --color-bg: #FAF6F0;
  --color-bg-warm: #F5EDE3;
  --color-bg-section: #F0E8DC;
  --color-bg-dark: #2C1B10;
  
  /* 文字 */
  --color-text: #3D2E24;
  --color-text-light: #5A4A3F;
  --color-text-muted: #8C7B6F;
  
  /* 边框 */
  --color-border: #D9CFC3;
  --color-border-light: #E8E0D5;
  
  /* 间距 */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
  --space-3xl: 64px;
  
  /* 圆角 */
  --radius-xs: 4px;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  
  /* 阴影 */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.12);
  --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.06);
  
  /* 过渡 */
  --transition: all 0.3s ease;
  --transition-fast: all 0.2s ease;
  
  /* 布局 */
  --nav-height: 70px;
  --container-max: 1200px;
}
```

---

## 快速开始

### 本地运行

1. **克隆项目**
```bash
git clone https://github.com/your-username/ResponsiveQujiangTravelInformationPlatform.git
cd ResponsiveQujiangTravelInformationPlatform
```

2. **启动本地服务器**

```bash
# Python 3
python -m http.server 8080

# Node.js
npx http-server -p 8080

# PHP
php -S localhost:8080
```

3. **访问网站**
```
http://localhost:8080
```

---

## 设计规范

### 配色方案

| 用途 | 颜色 | 色值 |
|------|------|------|
| 主色调 | 深棕色 | `#7A3B2E` |
| 强调色 | 金色 | `#C4A265` |
| 背景色 | 米白色 | `#FAF6F0` |
| 深色背景 | 深褐色 | `#2C1B10` |
| 正文文字 | 深棕色 | `#3D2E24` |

### 响应式断点

| 设备 | 断点 | 布局 |
|------|------|------|
| 桌面端 | > 1024px | 三栏/四列网格 |
| 平板端 | 768px - 1024px | 两栏布局 |
| 手机端 | < 768px | 单列布局 |

### 字体

```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 
             'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 
             sans-serif;
```

---

## 开发指南

### 添加新景点

1. 在 `js/data.js` 添加数据：
```javascript
{
  id: 9,  // 唯一ID
  name: '新景点名称',
  desc: '简短描述',
  tag: '分类标签',
  img: 'images/scenic/new-spot.jpg',
  detail: '详细介绍...',
  gallery: ['images/scenic/new-spot.jpg'],
  address: '地址',
  openTime: '开放时间',
  ticket: '门票信息',
  traffic: '交通指南',
  tips: '温馨提示',
  highlights: ['亮点1', '亮点2']
}
```

2. 将图片放入 `images/scenic/` 目录

### 修改配色

修改 `css/common.css` 中的 CSS 变量：
```css
:root {
  --color-primary: #新颜色;
  --color-accent: #新颜色;
}
```

### 添加新页面

1. 复制现有HTML文件作为模板
2. 创建对应的CSS和JS文件
3. 在导航组件中添加链接

---

## 浏览器支持

| 浏览器 | 版本 |
|--------|------|
| Chrome | 80+ |
| Firefox | 75+ |
| Safari | 13+ |
| Edge | 80+ |
| 移动端 Chrome | 80+ |
| 移动端 Safari | 13+ |

---

## 数据来源

- 图片资源来自衢州古城文化旅游区官网 (qzgcwhlyq.com)
- 文字内容参考官方资料整理
- **仅供学习交流使用，不作商业用途**

---

## 许可证

MIT License

本项目仅供学习交流使用，图片版权归原作者所有。

---

## 致谢

- [衢州古城文化旅游区](https://qzgcwhlyq.com) - 设计参考及图片来源
- [Vue.js](https://vuejs.org) - 前端框架
