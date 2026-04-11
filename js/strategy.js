/**
 * strategy.js — 攻略页面（从 API 加载数据）
 */

document.addEventListener('DOMContentLoaded', function () {
  loadStrategies();
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

function loadStrategies() {
  fetch('api/public/get_strategies.php?pageSize=50')
    .then(function (res) { return res.json(); })
    .then(function (result) {
      if (result.code === 0 && result.data && result.data.list) {
        renderStrategiesByCategory(result.data.list);
        if (typeof initLazyLoad === 'function') initLazyLoad();
      }
    })
    .catch(function (err) {
      console.error('加载攻略数据失败:', err);
      var containers = document.querySelectorAll('[data-strategy-category]');
      containers.forEach(function(c) {
        c.innerHTML = '<div class="loading-hint" style="color:#9E8C7E;">数据加载失败，请刷新重试</div>';
      });
    });
}

function renderStrategiesByCategory(strategies) {
  var categories = {};
  strategies.forEach(function(item) {
    if (!categories[item.category]) {
      categories[item.category] = [];
    }
    categories[item.category].push(item);
  });

  var iconMap = {
    '行程规划': '📍',
    '攻略指南': '📖',
    '实用贴士': '💡'
  };

  Object.keys(categories).forEach(function(cat) {
    var container = document.querySelector('[data-strategy-category="' + cat + '"]');
    if (!container) return;

    var html = '<div class="strategy-card-list">';
    categories[cat].forEach(function(item) {
      var detailUrl = 'detail.html?type=strategy&id=' + encodeURIComponent(item.id);
      var icon = iconMap[cat] || '📋';
      html += '<a href="' + escapeAttr(detailUrl) + '" class="strategy-card" style="text-decoration:none;color:inherit;">' +
        '<div class="strategy-card__image">' +
          '<img data-src="' + escapeAttr(item.image || 'images/scenic/dongqian.png') + '" alt="' + escapeAttr(item.name) + '" class="lazy-img">' +
        '</div>' +
        '<div class="strategy-card__body">' +
          '<span class="strategy-card__icon">' + icon + '</span>' +
          '<h3 class="strategy-card__title">' + escapeHtml(item.name) + '</h3>' +
          '<p class="strategy-card__desc">' + escapeHtml(item.description || '') + '</p>' +
          '<span class="strategy-card__link">查看详情 →</span>' +
        '</div>' +
      '</a>';
    });
    html += '</div>';
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
