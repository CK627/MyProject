/**
 * index.js — 首页（从后端API加载精选景点）
 */

document.addEventListener('DOMContentLoaded', function () {
  loadFeaturedSpots();
});

/**
 * 从API加载精选景点（前3个）并渲染到首页
 */
function loadFeaturedSpots() {
  var grid = document.getElementById('featuredSpotsGrid');
  if (!grid) return;

  fetch('api/public/get_spots.php?pageSize=3')
    .then(function (res) { return res.json(); })
    .then(function (result) {
      if (result.code === 0 && result.data && result.data.list && result.data.list.length > 0) {
        var spots = result.data.list;
        var html = '';

        spots.forEach(function (spot, index) {
          var imgSrc = spot.image || 'images/scenic/tianyi.png';
          var delay = (index + 1) * 0.1;
          var detailUrl = 'detail.html?id=' + encodeURIComponent(spot.id);

          html += '<a href="' + escapeAttr(detailUrl) + '" class="card" data-animate="fade-in-up" data-delay="' + delay + '" style="text-decoration:none;color:inherit;display:block;">' +
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
              '</div>' +
            '</div>' +
          '</a>';
        });

        grid.innerHTML = html;
        // 重新初始化懒加载
        initLazyLoad();
        initScrollAnimations();
      }
    })
    .catch(function (err) {
      console.error('加载精选景点失败:', err);
      // 保留已有静态内容作为fallback
    });
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
