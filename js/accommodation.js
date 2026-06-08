/**
 * accommodation.js — 住宿页面（从 API 加载数据）
 */

document.addEventListener('DOMContentLoaded', function () {
  loadAccommodations();
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

function loadAccommodations() {
  fetch('api/public/get_accommodations.php?pageSize=50')
    .then(function (res) { return res.json(); })
    .then(function (result) {
      if (result.code === 0 && result.data && result.data.list) {
        renderAccommodationsByCategory(result.data.list);
        if (typeof initLazyLoad === 'function') initLazyLoad();
      } else {
        hideEmptyContainers();
      }
    })
    .catch(function (err) {
      console.error('加载住宿数据失败:', err);
      var containers = document.querySelectorAll('[data-acc-category]');
      containers.forEach(function(c) {
        c.innerHTML = '<div class="loading-hint" style="color:#9E8C7E;">数据加载失败，请刷新重试</div>';
      });
    });
}

function renderAccommodationsByCategory(accommodations) {
  var categories = {};
  accommodations.forEach(function(acc) {
    if (!categories[acc.category]) {
      categories[acc.category] = [];
    }
    categories[acc.category].push(acc);
  });

  var containers = document.querySelectorAll('[data-acc-category]');
  containers.forEach(function(container) {
    var cat = container.getAttribute('data-acc-category');
    var items = categories[cat];

    if (!items || items.length === 0) {
      // 隐藏没有数据的分类区块
      var section = container.closest('section');
      if (section) section.style.display = 'none';
      return;
    }

    var html = '';
    items.forEach(function(acc) {
      var detailUrl = 'detail.html?type=accommodation&id=' + encodeURIComponent(acc.id);
      var badge = acc.category === '星级酒店' ? '五星级' : (acc.category === '特色民宿' ? '精品' : acc.category);
      html += '<a href="' + escapeAttr(detailUrl) + '" class="card" style="text-decoration:none;color:inherit;display:block;">' +
        '<div class="card__image-wrapper">' +
          '<img data-src="' + escapeAttr(acc.image || 'images/accommodation/hotel.png') + '" alt="' + escapeAttr(acc.name) + '" class="card__image lazy-img">' +
          '<span class="card__badge">' + escapeHtml(badge) + '</span>' +
        '</div>' +
        '<div class="card__body">' +
          '<h3 class="card__title">' + escapeHtml(acc.name) + '</h3>' +
          '<p class="card__desc">' + escapeHtml(acc.description || '') + '</p>' +
          '<div class="card__meta">' +
            (acc.rating ? '<span class="rating">' + escapeHtml(acc.rating) + '</span>' : '') +
            (acc.price ? '<span class="price-tag">' + escapeHtml(acc.price) + '</span>' : '') +
          '</div>' +
        '</div>' +
      '</a>';
    });
    container.innerHTML = html;
  });
}

function hideEmptyContainers() {
  var containers = document.querySelectorAll('[data-acc-category]');
  containers.forEach(function(c) {
    c.innerHTML = '<div class="loading-hint" style="color:#9E8C7E;">暂无数据</div>';
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
