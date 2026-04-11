/* ============================================
   衢江文化旅游信息平台 - 公共脚本
   导航栏、页脚 Vue 组件 + 通用工具
   ============================================ */

/* ---------- 导航组件 ---------- */
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
        {
          name: '美食',
          key: 'food',
          href: 'food.html',
          children: [
            { name: '特色小吃', href: 'food.html#snacks' },
            { name: '地方菜肴', href: 'food.html#dishes' }
          ]
        },
        {
          name: '线路',
          key: 'route',
          href: 'route.html',
          children: [
            { name: '一日游', href: 'route.html#oneday' },
            { name: '深度游', href: 'route.html#deep' }
          ]
        },
        {
          name: '民俗',
          key: 'culture',
          href: 'culture.html',
          children: [
            { name: '传统节日', href: 'culture.html#festivals' },
            { name: '民间技艺', href: 'culture.html#crafts' }
          ]
        }
      ],
      mobileSubOpen: ''
    };
  },
  mounted() {
    window.addEventListener('scroll', this.onScroll);
  },
  beforeUnmount() {
    window.removeEventListener('scroll', this.onScroll);
  },
  methods: {
    onScroll() {
      this.scrolled = window.scrollY > 10;
    },
    toggleMobile() {
      this.mobileOpen = !this.mobileOpen;
    },
    toggleMobileSub(key) {
      this.mobileSubOpen = this.mobileSubOpen === key ? '' : key;
    }
  },
  template: `
    <header class="site-header" :class="{ scrolled }">
      <div class="header-inner">
        <a href="index.html" class="site-logo">
          <img src="images/logo.png" alt="衢州古城文化旅游区" class="logo-img">
        </a>
        <nav class="main-nav" :class="{ open: mobileOpen }">
          <div class="nav-item" v-for="item in navItems" :key="item.key"
               :class="{ 'mobile-open': mobileSubOpen === item.key }">
            <a :href="item.href" class="nav-link" :class="{ active: current === item.key }"
               @click.stop="item.children && window.innerWidth <= 768 ? (toggleMobileSub(item.key), $event.preventDefault()) : null">
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

/* ---------- 页脚组件 ---------- */
const SiteFooter = {
  template: `
    <footer class="site-footer">
      <div class="container">
        <div class="footer-grid">
          <div class="footer-brand">
            <div class="footer-logo">衢江文旅</div>
            <p>衢江区位于浙江省衢州市，拥有丰富的自然山水与深厚的人文底蕴。这里山清水秀、古韵悠长，是休闲旅游与文化探访的理想目的地。</p>
          </div>
          <div class="footer-col">
            <h4>景点推荐</h4>
            <a href="scenic.html#nature">自然风光</a>
            <a href="scenic.html#culture">人文古迹</a>
          </div>
          <div class="footer-col">
            <h4>美食探索</h4>
            <a href="food.html#snacks">特色小吃</a>
            <a href="food.html#dishes">地方菜肴</a>
          </div>
          <div class="footer-col">
            <h4>旅游线路</h4>
            <a href="route.html#oneday">一日游</a>
            <a href="route.html#deep">深度游</a>
          </div>
        </div>
        <div class="footer-bottom">
          <p>&copy; 2026 衢江文化旅游信息平台 · 仅供学习交流使用</p>
        </div>
      </div>
    </footer>
  `
};

/* ---------- 卡片组件 ---------- */
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
        <img v-if="item.img" :data-src="item.img" :alt="item.name" class="card-img" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7">
        <div v-else class="img-placeholder">暂无图片</div>
      </div>
      <div class="card-body">
        <span v-if="item.tag" class="card-tag">{{ item.tag }}</span>
        <h3 class="card-title">{{ item.name }}</h3>
        <p class="card-desc">{{ item.desc }}</p>
      </div>
    </a>
    <div class="card" v-else>
      <div class="card-img-wrap">
        <img v-if="item.img" :data-src="item.img" :alt="item.name" class="card-img" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7">
        <div v-else class="img-placeholder">暂无图片</div>
      </div>
      <div class="card-body">
        <span v-if="item.tag" class="card-tag">{{ item.tag }}</span>
        <h3 class="card-title">{{ item.name }}</h3>
        <p class="card-desc">{{ item.desc }}</p>
      </div>
    </div>
  `
};

/* ---------- 图片懒加载 ---------- */
let _lazyObserver = null;

function initLazyLoad() {
  if ('IntersectionObserver' in window) {
    if (!_lazyObserver) {
      _lazyObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.onload = () => img.classList.add('loaded');
            img.onerror = () => {
              img.style.display = 'none';
              const placeholder = document.createElement('div');
              placeholder.className = 'img-placeholder';
              placeholder.textContent = '图片加载失败';
              img.parentNode.insertBefore(placeholder, img);
            };
            _lazyObserver.unobserve(img);
          }
        });
      }, { rootMargin: '200px' });
    }
    document.querySelectorAll('img[data-src]:not(.loaded)').forEach(img => {
      _lazyObserver.observe(img);
    });
  } else {
    document.querySelectorAll('img[data-src]:not(.loaded)').forEach(img => {
      img.src = img.dataset.src;
      img.classList.add('loaded');
    });
  }
}

/* ---------- 回到顶部 ---------- */
function initBackToTop() {
  const btn = document.querySelector('.back-to-top');
  if (!btn) return;
  window.addEventListener('scroll', () => {
    btn.classList.toggle('visible', window.scrollY > 400);
  });
  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

/* ---------- 平滑滚动到锚点 ---------- */
function initSmoothScroll() {
  const hash = window.location.hash;
  if (hash) {
    setTimeout(() => {
      const target = document.querySelector(hash);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 300);
  }
}

/* ---------- Vue 应用初始化工具 ---------- */
function createPageApp(options = {}) {
  const app = Vue.createApp(options);
  app.component('site-header', SiteHeader);
  app.component('site-footer', SiteFooter);
  app.component('spot-card', SpotCard);
  return app;
}

/* ---------- 页面就绪后的公共初始化 ---------- */
function commonInit() {
  // 延迟执行以等待 Vue 子组件渲染完成
  Vue.nextTick(() => {
    setTimeout(() => {
      initLazyLoad();
      initBackToTop();
      initSmoothScroll();
    }, 100);
  });

  // 监听 DOM 变化，自动处理后续动态添加的图片
  const mo = new MutationObserver(() => {
    const pending = document.querySelectorAll('img[data-src]:not(.loaded)');
    if (pending.length) initLazyLoad();
  });
  mo.observe(document.body, { childList: true, subtree: true });
}
