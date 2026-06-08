/**
 * detail.js — 通用详情页
 * 支持景点、美食、住宿、交通、攻略等多种内容类型
 * URL 参数：?type=spot|food|accommodation|transport|strategy&id=X
 */

// 类型配置
var typeConfig = {
  spot: {
    api: 'api/public/get_spot.php',
    backUrl: 'scenic.html',
    backText: '← 返回景点列表',
    titleSuffix: '景点详情',
    renderInfo: function(data) {
      return [
        { icon: '📍', label: '地址', value: data.address },
        { icon: '🎫', label: '门票', value: data.ticket },
        { icon: '⭐', label: '等级', value: data.level }
      ];
    }
  },
  food: {
    api: 'api/public/get_food.php',
    backUrl: 'food.html',
    backText: '← 返回美食列表',
    titleSuffix: '美食详情',
    renderInfo: function(data) {
      return [
        { icon: '💰', label: '人均', value: data.price },
        { icon: '🏷️', label: '标签', value: data.tag }
      ];
    }
  },
  accommodation: {
    api: 'api/public/get_accommodation.php',
    backUrl: 'accommodation.html',
    backText: '← 返回住宿列表',
    titleSuffix: '住宿详情',
    renderInfo: function(data) {
      return [
        { icon: '📍', label: '地址', value: data.address },
        { icon: '💰', label: '价格', value: data.price },
        { icon: '⭐', label: '评级', value: data.rating }
      ];
    }
  },
  transport: {
    api: 'api/public/get_transport.php',
    backUrl: 'transport.html',
    backText: '← 返回交通指南',
    titleSuffix: '交通详情',
    renderInfo: function(data) {
      return [
        { icon: '🚦', label: '类型', value: data.category }
      ];
    }
  },
  strategy: {
    api: 'api/public/get_strategy.php',
    backUrl: 'strategy.html',
    backText: '← 返回旅游攻略',
    titleSuffix: '攻略详情',
    renderInfo: function(data) {
      return [
        { icon: '📋', label: '类型', value: data.category }
      ];
    }
  }
};

// 全局变量
var currentType = '';
var currentId = '';

document.addEventListener('DOMContentLoaded', function () {
  var params = new URLSearchParams(window.location.search);
  currentType = params.get('type') || 'spot';
  currentId = params.get('id');

  if (!currentId) {
    showError('缺少ID参数');
    return;
  }

  var config = typeConfig[currentType];
  if (!config) {
    showError('未知的内容类型');
    return;
  }

  loadDetail(currentType, currentId, config);
});

/**
 * 加载详情
 */
function loadDetail(type, id, config) {
  var loading = document.getElementById('detailLoading');
  var hero = document.getElementById('detailHero');
  var main = document.getElementById('detailMain');
  var backLink = document.getElementById('backLink');

  // 设置返回链接
  backLink.href = config.backUrl;
  backLink.textContent = config.backText;

  fetch(config.api + '?id=' + encodeURIComponent(id))
    .then(function (res) { return res.json(); })
    .then(function (result) {
      loading.style.display = 'none';

      if (result.code === 0 && result.data) {
        var data = result.data;
        renderDetail(data, config);
        hero.style.display = '';
        main.style.display = '';

        // 更新页面标题
        document.title = data.name + ' — 宁波旅游';
        var metaDesc = document.querySelector('meta[name="description"]');
        if (metaDesc) {
          metaDesc.content = data.description || ('宁波' + config.titleSuffix + '：' + data.name);
        }

        // 加载评论
        loadComments(type, id);
      } else {
        showError(result.message || '内容不存在');
      }
    })
    .catch(function (err) {
      loading.style.display = 'none';
      showError('加载失败，请刷新重试');
      console.error('加载详情失败:', err);
    });
}

/**
 * 渲染详情
 */
function renderDetail(data, config) {
  // Hero
  var heroImg = document.getElementById('heroImage');
  var heroImgBlur = document.getElementById('heroImageBlur');
  var imgSrc = data.image || 'images/scenic/tianyi.png';
  heroImg.src = imgSrc;
  heroImgBlur.src = imgSrc;
  heroImg.alt = data.name;

  document.getElementById('heroCategory').textContent = data.category || '';
  document.getElementById('heroTitle').textContent = data.name || '';
  document.getElementById('heroDesc').textContent = data.description || '';

  // 信息条
  var infoBar = document.getElementById('infoBar');
  var infoItems = config.renderInfo(data);
  var infoHtml = '';
  infoItems.forEach(function(item) {
    if (item.value) {
      infoHtml += '<div class="detail-info-item">' +
        '<span class="detail-info-item__icon">' + item.icon + '</span>' +
        '<span class="detail-info-item__label">' + item.label + '：</span>' +
        '<span>' + escapeHtml(item.value) + '</span>' +
      '</div>';
    }
  });
  infoBar.innerHTML = infoHtml;

  // 详情内容
  var contentEl = document.getElementById('detailContent');
  if (data.detail_content && data.detail_content.trim()) {
    contentEl.innerHTML = '<div class="detail-content">' + data.detail_content + '</div>';
  } else {
    contentEl.innerHTML =
      '<div class="detail-content">' +
        '<div class="detail-empty">' +
          '<div class="detail-empty__icon">📋</div>' +
          '<p class="detail-empty__text">暂无详细介绍内容</p>' +
        '</div>' +
      '</div>';
  }
}

// ========== 评论功能 ==========

/**
 * 加载评论列表
 */
function loadComments(type, id) {
  var commentList = document.getElementById('commentList');
  var commentCount = document.getElementById('commentCount');
  var commentEmpty = document.getElementById('commentEmpty');

  fetch('api/public/get_comments.php?type=' + encodeURIComponent(type) + '&id=' + encodeURIComponent(id))
    .then(function (res) { return res.json(); })
    .then(function (result) {
      if (result.code === 0 && result.data) {
        var comments = result.data.list || [];
        var total = result.data.total || 0;
        commentCount.textContent = total + ' 条留言';

        if (comments.length === 0) {
          commentEmpty.style.display = '';
          // 清除已有评论卡片
          var existing = commentList.querySelectorAll('.comment-card');
          existing.forEach(function(c) { c.remove(); });
          return;
        }

        commentEmpty.style.display = 'none';
        var html = '';
        comments.forEach(function(c) {
          var initials = c.name.charAt(0);
          html += '<div class="comment-card">' +
            '<div class="comment-card__header">' +
              '<div class="comment-card__avatar">' + escapeHtml(initials) + '</div>' +
              '<div>' +
                '<div class="comment-card__name">' + escapeHtml(c.name) + '</div>' +
                '<div class="comment-card__time">' + escapeHtml(c.created_at || '') + '</div>' +
              '</div>' +
            '</div>' +
            '<div class="comment-card__content">' + escapeHtml(c.content) + '</div>' +
          '</div>';
        });
        commentList.innerHTML = html + commentEmpty.outerHTML;
        // 重新获取 commentEmpty 引用（因为 innerHTML 重写了）
        commentEmpty = document.getElementById('commentEmpty');
        if (commentEmpty) commentEmpty.style.display = 'none';
      }
    })
    .catch(function (err) {
      console.error('加载评论失败:', err);
    });
}

/**
 * 初始化评论表单
 */
function initCommentForm() {
  var form = document.getElementById('commentForm');
  if (!form) return;

  var charCount = document.getElementById('commentCharCount');
  var contentInput = document.getElementById('commentContent');

  if (contentInput && charCount) {
    contentInput.addEventListener('input', function() {
      charCount.textContent = this.value.length;
    });
  }

  form.addEventListener('submit', function(e) {
    e.preventDefault();

    var nameInput = document.getElementById('commentName');
    var name = nameInput.value.trim();
    var content = contentInput.value.trim();

    if (!name) {
      showToast('请输入昵称', 'error');
      nameInput.focus();
      return;
    }
    if (!content) {
      showToast('请输入留言内容', 'error');
      contentInput.focus();
      return;
    }

    var submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = '提交中...';

    fetch('api/public/submit_comment.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content_type: currentType,
        content_id: parseInt(currentId),
        name: name,
        content: content
      })
    })
    .then(function(res) { return res.json(); })
    .then(function(result) {
      submitBtn.disabled = false;
      submitBtn.textContent = '提交留言';

      if (result.code === 0) {
        showToast('留言提交成功！', 'success');
        form.reset();
        if (charCount) charCount.textContent = '0';
        loadComments(currentType, currentId);
      } else {
        showToast(result.message || '提交失败，请重试', 'error');
      }
    })
    .catch(function(err) {
      submitBtn.disabled = false;
      submitBtn.textContent = '提交留言';
      showToast('网络错误，请重试', 'error');
      console.error('提交评论失败:', err);
    });
  });
}

// 页面加载后初始化评论表单
document.addEventListener('DOMContentLoaded', function() {
  initCommentForm();
});

/**
 * 显示错误状态
 */
function showError(msg) {
  var loading = document.getElementById('detailLoading');
  loading.innerHTML =
    '<div style="text-align:center;padding:4rem;">' +
      '<div style="font-size:3rem;margin-bottom:1rem;">😔</div>' +
      '<p style="font-size:1.1rem;color:#6B5344;margin-bottom:1.5rem;">' + escapeHtml(msg) + '</p>' +
      '<a href="index.html" style="color:#B8763E;font-weight:600;text-decoration:none;">← 返回首页</a>' +
    '</div>';
}

/** HTML转义 */
function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}
