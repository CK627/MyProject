/**
 * transport.js — 交通页面（从 API 加载数据）
 */

document.addEventListener('DOMContentLoaded', function () {
  loadTransports();
  handleHashScroll();
});

// 监听hash变化，实现导航栏二级菜单切换
window.addEventListener('hashchange', function () {
  handleHashScroll();
});

function handleHashScroll() {
  var hash = window.location.hash.replace('#', '');
  if (hash) {
    setTimeout(function () {
      var target = document.getElementById(hash);
      if (target) target.scrollIntoView({ behavior: 'smooth' });
    }, 300);
  }
}

function loadTransports() {
  fetch('api/public/get_transports.php?pageSize=50')
    .then(function (res) { return res.json(); })
    .then(function (result) {
      if (result.code === 0 && result.data && result.data.list) {
        renderTransportsByCategory(result.data.list);
        if (typeof initLazyLoad === 'function') initLazyLoad();
      }
    })
    .catch(function (err) {
      console.error('加载交通数据失败:', err);
      // 显示错误提示
      var containers = document.querySelectorAll('[data-transport-category]');
      containers.forEach(function(c) {
        c.innerHTML = '<div class="loading-hint" style="color:#9E8C7E;">数据加载失败，请刷新重试</div>';
      });
    });
}

function renderTransportsByCategory(transports) {
  var categories = {};
  transports.forEach(function(item) {
    if (!categories[item.category]) {
      categories[item.category] = [];
    }
    categories[item.category].push(item);
  });

  var iconMap = {
    '到达交通': ['✈️', '🚄', '🚗', '🚢', '🚌', '🚁'],
    '市内交通': ['🚇', '🚌', '🚕', '🚲', '🛵', '🚶'],
    '周边交通': ['🚢', '🚗', '🚌', '🚄', '✈️', '🛥️']
  };

  Object.keys(categories).forEach(function(cat) {
    var container = document.querySelector('[data-transport-category="' + cat + '"]');
    if (!container) return;

    var icons = iconMap[cat] || ['🚦'];
    var html = '';
    categories[cat].forEach(function(item, idx) {
      var detailUrl = 'detail.html?type=transport&id=' + encodeURIComponent(item.id);
      var icon = icons[idx % icons.length];
      html += '<a href="' + escapeAttr(detailUrl) + '" class="transport-card" style="text-decoration:none;color:inherit;">' +
        '<div class="transport-card__icon">' + icon + '</div>' +
        '<div>' +
          '<h3 class="card__title">' + escapeHtml(item.name) + '</h3>' +
          '<p class="card__desc">' + escapeHtml(item.description || '') + '</p>' +
          '<div class="card__meta">' +
            '<span class="card__tag">' + escapeHtml(item.category) + '</span>' +
            '<span style="color:#B8763E;font-weight:600;font-size:13px;">查看详情 →</span>' +
          '</div>' +
        '</div>' +
      '</a>';
    });
    container.innerHTML = html;
  });
}

function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

function escapeAttr(text) {
  return (text || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
