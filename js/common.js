/**
 * 宁波旅游宣传网站 — 公共脚本
 * 包含：导航栏、页脚、返回顶部、懒加载、滚动动画等
 */

// ==================== 导航栏 ====================
function renderNavbar() {
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';

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
    {
      label: '美食', href: 'food.html', key: 'food.html',
      children: [
        { label: '海鲜', href: 'food.html#seafood' },
        { label: '传统小吃', href: 'food.html#snacks' },
        { label: '糕点甜品', href: 'food.html#dessert' },
        { label: '特色菜肴', href: 'food.html#dishes' }
      ]
    },
    {
      label: '住宿', href: 'accommodation.html', key: 'accommodation.html',
      children: [
        { label: '星级酒店', href: 'accommodation.html#hotel' },
        { label: '特色民宿', href: 'accommodation.html#homestay' }
      ]
    },
    {
      label: '交通', href: 'transport.html', key: 'transport.html',
      children: [
        { label: '到达宁波', href: 'transport.html#arrive' },
        { label: '市内交通', href: 'transport.html#city' }
      ]
    },
    {
      label: '攻略', href: 'strategy.html', key: 'strategy.html',
      children: [
        { label: '行程规划', href: 'strategy.html#itinerary' },
        { label: '攻略指南', href: 'strategy.html#guides' },
        { label: '实用贴士', href: 'strategy.html#tips' }
      ]
    },
    { label: '留言', href: 'guestbook.html', key: 'guestbook.html' }
  ];

  function buildNavItems() {
    return navItems.map(item => {
      const isActive = currentPage === item.key;
      const hasChildren = item.children && item.children.length > 0;

      let dropdown = '';
      if (hasChildren) {
        const links = item.children.map(child =>
          '<a href="' + child.href + '" class="navbar__dropdown-link">' + child.label + '</a>'
        ).join('');
        dropdown = '<div class="navbar__dropdown">' + links + '</div>';
      }

      return '<li class="navbar__item">' +
        '<a href="' + item.href + '" class="navbar__link ' + (isActive ? 'navbar__link--active' : '') + '">' +
          item.label +
          (hasChildren ? ' <span class="navbar__link-arrow">▼</span>' : '') +
        '</a>' +
        dropdown +
      '</li>';
    }).join('');
  }

  // 构建移动端菜单HTML（独立于navbar的DOM）
  function buildMobileMenu() {
    return navItems.map(function (item) {
      var isActive = currentPage === item.key;
      var hasChildren = item.children && item.children.length > 0;
      var children = '';
      if (hasChildren) {
        children = '<div class="mobile-menu__sub">' +
          item.children.map(function (child) {
            return '<a href="' + child.href + '" class="mobile-menu__sub-link">' + child.label + '</a>';
          }).join('') +
        '</div>';
      }
      return '<div class="mobile-menu__item" data-href="' + item.href + '">' +
        '<div class="mobile-menu__link' + (isActive ? ' mobile-menu__link--active' : '') + '">' +
          '<span>' + item.label + '</span>' +
          (hasChildren ? '<span class="mobile-menu__arrow">▼</span>' : '') +
        '</div>' +
        children +
      '</div>';
    }).join('');
  }

  var navbarHTML =
    '<nav class="navbar" id="navbar">' +
      '<div class="navbar__inner">' +
        '<a href="index.html" class="navbar__brand">' +
          '<img src="images/favicon.ico" alt="宁波旅游" class="navbar__brand-icon">' +
          '宁波旅游' +
        '</a>' +
        '<ul class="navbar__menu" id="navMenu">' +
          buildNavItems() +
        '</ul>' +
        '<button class="navbar__toggle" id="navToggle" aria-label="打开导航菜单">' +
          '<span></span><span></span><span></span>' +
        '</button>' +
      '</div>' +
    '</nav>';

  document.body.insertAdjacentHTML('afterbegin', navbarHTML);

  // 移动端：创建独立菜单面板（直接挂载到body上，避免stacking context问题）
  var mobilePanel = document.createElement('div');
  mobilePanel.id = 'mobileMenu';
  mobilePanel.className = 'mobile-menu';
  mobilePanel.innerHTML = buildMobileMenu();
  document.body.appendChild(mobilePanel);

  initNavbar();
}

function initNavbar() {
  var navbar = document.getElementById('navbar');
  var navToggle = document.getElementById('navToggle');
  var mobileMenu = document.getElementById('mobileMenu');

  // 滚动变色
  var menuOpen = false;
  function handleScroll() {
    if (menuOpen) return;
    if (window.scrollY > 60) {
      navbar.classList.add('navbar--scrolled');
    } else {
      navbar.classList.remove('navbar--scrolled');
    }
  }
  window.addEventListener('scroll', handleScroll, { passive: true });
  handleScroll();

  function closeMenu() {
    menuOpen = false;
    navToggle.classList.remove('navbar__toggle--active');
    mobileMenu.classList.remove('mobile-menu--open');
    mobileMenu.style.transform = 'translateX(100%)';
    mobileMenu.style.opacity = '0';
    mobileMenu.style.pointerEvents = 'none';
    document.body.style.overflow = '';
    if (window.scrollY <= 60) {
      navbar.classList.remove('navbar--scrolled');
    }
  }

  function openMenu() {
    menuOpen = true;
    navToggle.classList.add('navbar__toggle--active');
    mobileMenu.classList.add('mobile-menu--open');
    mobileMenu.style.transform = 'translateX(0)';
    mobileMenu.style.opacity = '1';
    mobileMenu.style.pointerEvents = 'auto';
    navbar.classList.add('navbar--scrolled');
    document.body.style.overflow = 'hidden';
  }

  // 汉堡按钮
  navToggle.addEventListener('click', function (e) {
    e.stopPropagation();
    if (menuOpen) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  // 移动端菜单项事件绑定
  var menuItems = mobileMenu.querySelectorAll('.mobile-menu__item');
  menuItems.forEach(function (item) {
    var linkDiv = item.querySelector('.mobile-menu__link');
    var subMenu = item.querySelector('.mobile-menu__sub');
    var href = item.getAttribute('data-href');

    linkDiv.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (subMenu) {
        // 有子菜单：切换展开
        var isOpen = item.classList.contains('mobile-menu__item--open');
        // 关闭其他
        menuItems.forEach(function (other) {
          other.classList.remove('mobile-menu__item--open');
        });
        if (!isOpen) {
          item.classList.add('mobile-menu__item--open');
        } else {
          // 再次点击已展开的 → 跳转
          closeMenu();
          window.location.href = href;
        }
      } else {
        // 无子菜单：直接跳转
        closeMenu();
        window.location.href = href;
      }
    });

    // 子菜单链接
    if (subMenu) {
      var subLinks = subMenu.querySelectorAll('.mobile-menu__sub-link');
      subLinks.forEach(function (sl) {
        sl.addEventListener('click', function (e) {
          e.stopPropagation();
          closeMenu();
          // 正常跳转由浏览器处理
        });
      });
    }
  });
}

// ==================== 页脚 ====================
function renderFooter() {
  const footerHTML = `
    <footer class="footer">
      <div class="container">
        <div class="footer__grid">
          <div>
            <div class="footer__brand">宁波旅游</div>
            <p class="footer__desc">
              探索千年文化名城，感受山海交融的独特魅力。<br>
              宁波，一座让你来了就不想走的城市。
            </p>
          </div>
          <div>
            <h4 class="footer__heading">探索</h4>
            <div class="footer__links">
              <a href="scenic.html" class="footer__link">热门景点</a>
              <a href="food.html" class="footer__link">地道美食</a>
              <a href="accommodation.html" class="footer__link">精选住宿</a>
              <a href="strategy.html" class="footer__link">旅游攻略</a>
            </div>
          </div>
          <div>
            <h4 class="footer__heading">服务</h4>
            <div class="footer__links">
              <a href="transport.html" class="footer__link">交通指南</a>
              <a href="guestbook.html" class="footer__link">游客留言</a>
              <a href="strategy.html" class="footer__link">行程规划</a>
            </div>
          </div>
          <div>
            <h4 class="footer__heading">联系</h4>
            <div class="footer__links">
              <span class="footer__link">电话: 0574-12345678</span>
              <span class="footer__link">邮箱: tour@ningbo.cn</span>
              <span class="footer__link">地址: 宁波市海曙区</span>
            </div>
          </div>
        </div>
        <div class="footer__bottom">
          <span>&copy; 2025 宁波旅游宣传网站 版权所有</span>
          <span>毕业设计作品</span>
        </div>
      </div>
    </footer>
  `;
  document.body.insertAdjacentHTML('beforeend', footerHTML);
}

// ==================== 返回顶部 ====================
function renderBackToTop() {
  const btn = document.createElement('button');
  btn.className = 'back-to-top';
  btn.id = 'backToTop';
  btn.innerHTML = '↑';
  btn.setAttribute('aria-label', '返回顶部');
  document.body.appendChild(btn);

  window.addEventListener('scroll', function () {
    if (window.scrollY > 400) {
      btn.classList.add('back-to-top--visible');
    } else {
      btn.classList.remove('back-to-top--visible');
    }
  }, { passive: true });

  btn.addEventListener('click', function () {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

// ==================== 图片懒加载 ====================
function initLazyLoad() {
  const images = document.querySelectorAll('img[data-src]');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          img.addEventListener('load', function () {
            img.classList.add('lazy-img--loaded');
          });
          observer.unobserve(img);
        }
      });
    }, { rootMargin: '200px' });

    images.forEach(function (img) {
      observer.observe(img);
    });
  } else {
    // fallback
    images.forEach(function (img) {
      img.src = img.dataset.src;
      img.classList.add('lazy-img--loaded');
    });
  }
}

// ==================== 滚动动画 ====================
function initScrollAnimations() {
  const elements = document.querySelectorAll('[data-animate]');
  if (!elements.length) return;

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

// ==================== Toast 通知 ====================
function showToast(message, type) {
  type = type || 'success';
  // 移除旧 toast
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

  setTimeout(function () {
    toast.classList.remove('toast--visible');
    setTimeout(function () { toast.remove(); }, 300);
  }, 3000);
}

// ==================== 搜索过滤 ====================
function initSearch(inputSelector, itemSelector, searchFields) {
  var input = document.querySelector(inputSelector);
  if (!input) return;

  input.addEventListener('input', function () {
    var keyword = this.value.trim().toLowerCase();
    var items = document.querySelectorAll(itemSelector);

    items.forEach(function (item) {
      if (!keyword) {
        item.style.display = '';
        return;
      }
      var match = false;
      searchFields.forEach(function (field) {
        var el = item.querySelector(field);
        if (el && el.textContent.toLowerCase().indexOf(keyword) !== -1) {
          match = true;
        }
      });
      item.style.display = match ? '' : 'none';
    });
  });
}

// ==================== 页面初始化 ====================
document.addEventListener('DOMContentLoaded', function () {
  renderNavbar();
  renderFooter();
  renderBackToTop();
  initLazyLoad();
  initScrollAnimations();
});
