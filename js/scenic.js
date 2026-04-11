/**
 * scenic.js — 景点页（通过 AJAX 从后端 API 获取数据）
 */

// 全局景点数据缓存
var allSpots = [];

document.addEventListener('DOMContentLoaded', function () {
  loadSpots();
  initTabs();
  initSearchFilter();
});

// 监听hash变化，实现导航栏二级菜单切换
window.addEventListener('hashchange', function () {
  handleHashFilter();
});

/**
 * 从后端API加载景点数据
 */
function loadSpots() {
  var grid = document.getElementById('scenicGrid');
  var loading = document.getElementById('scenicLoading');

  fetch('api/public/get_spots.php?pageSize=50')
    .then(function (res) { return res.json(); })
    .then(function (result) {
      loading.style.display = 'none';

      if (result.code === 0 && result.data && result.data.list) {
        allSpots = result.data.list;
        renderSpots(allSpots);
        // 懒加载新渲染的图片
        initLazyLoad();
        // URL hash 自动筛选
        handleHashFilter();
      } else {
        grid.innerHTML = '<div style="text-align:center;padding:3rem;color:var(--color-text-muted);">暂无景点数据</div>';
      }
    })
    .catch(function (err) {
      loading.style.display = 'none';
      grid.innerHTML = '<div style="text-align:center;padding:3rem;color:var(--color-accent);">加载失败，请刷新重试</div>';
      console.error('加载景点数据失败:', err);
    });
}

/**
 * 渲染景点卡片
 */
function renderSpots(spots) {
  var grid = document.getElementById('scenicGrid');
  if (!spots || spots.length === 0) {
    grid.innerHTML = '<div style="text-align:center;padding:3rem;color:var(--color-text-muted);">没有找到匹配的景点</div>';
    return;
  }

  var html = '';
  spots.forEach(function (spot) {
    var imgSrc = spot.image || 'images/scenic/tianyi.png';
    var detailUrl = 'detail.html?id=' + encodeURIComponent(spot.id);
    html += '<a href="' + escapeAttr(detailUrl) + '" class="card scenic-item" data-category="' + escapeAttr(spot.category) + '" style="text-decoration:none;color:inherit;display:block;">' +
      '<div class="card__image-wrapper">' +
        '<img data-src="' + escapeAttr(imgSrc) + '" alt="' + escapeAttr(spot.name) + '" class="card__image lazy-img">' +
        '<span class="card__badge">' + escapeHtml(spot.category) + '</span>' +
      '</div>' +
      '<div class="card__body">' +
        '<h3 class="card__title">' + escapeHtml(spot.name) + '</h3>' +
        '<p class="card__desc">' + escapeHtml(spot.description || '') + '</p>' +
        '<div class="card__meta">' +
          '<span class="card__tag">⭐ ' + escapeHtml(spot.level || '') + '</span>' +
          '<span>📍 ' + escapeHtml(spot.address || '') + '</span>' +
          '<span>🎫 ' + escapeHtml(spot.ticket || '') + '</span>' +
        '</div>' +
      '</div>' +
    '</a>';
  });

  grid.innerHTML = html;
}

/**
 * 分类标签切换
 */
function initTabs() {
  var tabs = document.querySelectorAll('#scenicTabs .tab');
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) { t.classList.remove('tab--active'); });
      tab.classList.add('tab--active');
      filterAndRender();
    });
  });
}

/**
 * 搜索过滤
 */
function initSearchFilter() {
  var input = document.getElementById('scenicSearch');
  if (!input) return;
  input.addEventListener('input', function () {
    filterAndRender();
  });
}

/**
 * 根据当前标签和搜索条件过滤并重新渲染
 */
function filterAndRender() {
  var activeTab = document.querySelector('#scenicTabs .tab--active');
  var category = activeTab ? activeTab.dataset.category : 'all';
  var keyword = (document.getElementById('scenicSearch').value || '').trim().toLowerCase();

  var filtered = allSpots.filter(function (spot) {
    var matchCategory = (category === 'all') || (spot.category === category);
    var matchKeyword = !keyword ||
      spot.name.toLowerCase().indexOf(keyword) !== -1 ||
      (spot.description && spot.description.toLowerCase().indexOf(keyword) !== -1);
    return matchCategory && matchKeyword;
  });

  renderSpots(filtered);
  initLazyLoad();
}

/**
 * URL hash 自动筛选
 */
function handleHashFilter() {
  var hash = window.location.hash.replace('#', '');
  if (!hash) return;

  var categoryMap = {
    'nature': '自然风光',
    'culture': '人文古迹',
    'red': '红色研学'
  };

  var category = categoryMap[hash];
  if (category) {
    var tabs = document.querySelectorAll('#scenicTabs .tab');
    tabs.forEach(function (tab) {
      tab.classList.remove('tab--active');
      if (tab.dataset.category === category) {
        tab.classList.add('tab--active');
      }
    });
    filterAndRender();
  }
}

/** HTML转义 */
function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

/** 属性转义 */
function escapeAttr(text) {
  return (text || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
