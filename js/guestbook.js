/**
 * guestbook.js — 留言板（通过 AJAX 调用后端 PHP API）
 */

document.addEventListener('DOMContentLoaded', function () {
  var form = document.getElementById('guestbookForm');
  var nameInput = document.getElementById('guestName');
  var messageInput = document.getElementById('guestMessage');
  var charCount = document.getElementById('charCount');
  var listEl = document.getElementById('guestbookList');
  var emptyEl = document.getElementById('guestbookEmpty');
  var countEl = document.getElementById('messageCount');

  // 加载留言列表
  loadMessages();

  // 字数统计
  messageInput.addEventListener('input', function () {
    charCount.textContent = this.value.length;
  });

  // 提交留言
  form.addEventListener('submit', function (e) {
    e.preventDefault();

    var name = nameInput.value.trim();
    var content = messageInput.value.trim();

    if (!name) {
      showToast('请输入昵称', 'error');
      nameInput.focus();
      return;
    }
    if (!content) {
      showToast('请输入留言内容', 'error');
      messageInput.focus();
      return;
    }

    // 禁用按钮防止重复提交
    var submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = '提交中...';

    fetch('api/public/submit_message.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, content: content })
    })
    .then(function (res) { return res.json(); })
    .then(function (result) {
      submitBtn.disabled = false;
      submitBtn.textContent = '提交留言';

      if (result.code === 0) {
        showToast('留言提交成功！感谢您的分享', 'success');
        form.reset();
        charCount.textContent = '0';
        // 重新加载留言列表
        loadMessages();
      } else {
        showToast(result.message || '提交失败，请重试', 'error');
      }
    })
    .catch(function (err) {
      submitBtn.disabled = false;
      submitBtn.textContent = '提交留言';
      showToast('网络错误，请重试', 'error');
      console.error('提交留言失败:', err);
    });
  });

  /**
   * 从后端API加载留言列表
   */
  function loadMessages() {
    fetch('api/public/get_messages.php?pageSize=50')
      .then(function (res) { return res.json(); })
      .then(function (result) {
        if (result.code === 0 && result.data && result.data.list) {
          renderMessages(result.data.list, result.data.total);
        } else {
          emptyEl.style.display = '';
          countEl.textContent = '0 条留言';
        }
      })
      .catch(function (err) {
        emptyEl.innerHTML = '<p>加载留言失败，请刷新重试</p>';
        console.error('加载留言失败:', err);
      });
  }

  /**
   * 渲染留言列表
   */
  function renderMessages(messages, total) {
    countEl.textContent = total + ' 条留言';

    // 清空现有留言卡片
    var existingCards = listEl.querySelectorAll('.message-card');
    existingCards.forEach(function (card) { card.remove(); });

    if (!messages || messages.length === 0) {
      emptyEl.style.display = '';
      return;
    }

    emptyEl.style.display = 'none';

    messages.forEach(function (msg) {
      var initials = msg.name.charAt(0);
      var time = msg.created_at || '';
      var card = document.createElement('div');
      card.className = 'message-card';
      card.innerHTML =
        '<div class="message-card__header">' +
          '<div class="message-card__avatar">' + escapeHtml(initials) + '</div>' +
          '<div>' +
            '<div class="message-card__name">' + escapeHtml(msg.name) + '</div>' +
            '<div class="message-card__time">' + escapeHtml(time) + '</div>' +
          '</div>' +
        '</div>' +
        '<div class="message-card__content">' + escapeHtml(msg.content) + '</div>';

      listEl.insertBefore(card, emptyEl);
    });
  }

  /** HTML转义（防XSS） */
  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }
});
