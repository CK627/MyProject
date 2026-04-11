/**
 * food.js — 美食页面（从 API 加载数据）
 */

document.addEventListener('DOMContentLoaded', function () {
  loadFoods();
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

function loadFoods() {
  fetch('api/public/get_foods.php?pageSize=50')
    .then(function (res) { return res.json(); })
    .then(function (result) {
      if (result.code === 0 && result.data && result.data.list) {
        renderFoodsByCategory(result.data.list);
        if (typeof initLazyLoad === 'function') initLazyLoad();
      } else {
        hideEmptyContainers();
      }
    })
    .catch(function (err) {
      console.error('加载美食数据失败:', err);
      var containers = document.querySelectorAll('[data-food-category]');
      containers.forEach(function(c) {
        c.innerHTML = '<div class="loading-hint" style="color:#9E8C7E;">数据加载失败，请刷新重试</div>';
      });
    });
}

function renderFoodsByCategory(foods) {
  var categories = {};
  foods.forEach(function(food) {
    if (!categories[food.category]) {
      categories[food.category] = [];
    }
    categories[food.category].push(food);
  });

  // 渲染每个分类容器
  var containers = document.querySelectorAll('[data-food-category]');
  containers.forEach(function(container) {
    var cat = container.getAttribute('data-food-category');
    var items = categories[cat];

    if (!items || items.length === 0) {
      // 隐藏没有数据的分类
      var section = container.closest('.food-category');
      if (section) section.style.display = 'none';
      return;
    }

    var html = '';
    items.forEach(function(food) {
      var detailUrl = 'detail.html?type=food&id=' + encodeURIComponent(food.id);
      html += '<a href="' + escapeAttr(detailUrl) + '" class="card" style="text-decoration:none;color:inherit;display:block;">' +
        '<div class="card__image-wrapper">' +
          '<img data-src="' + escapeAttr(food.image || 'images/food/seafood.png') + '" alt="' + escapeAttr(food.name) + '" class="card__image lazy-img">' +
        '</div>' +
        '<div class="card__body">' +
          '<h3 class="card__title">' + escapeHtml(food.name) + '</h3>' +
          '<p class="card__desc">' + escapeHtml(food.description || '') + '</p>' +
          '<div class="card__meta">' +
            (food.tag ? '<span class="card__tag">' + escapeHtml(food.tag) + '</span>' : '') +
            (food.price ? '<span>💰 人均 ' + escapeHtml(food.price) + '</span>' : '') +
          '</div>' +
        '</div>' +
      '</a>';
    });
    container.innerHTML = html;
  });
}

function hideEmptyContainers() {
  var containers = document.querySelectorAll('[data-food-category]');
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
