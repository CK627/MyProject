/**
 * 文件页面 - 设置模块
 * 包含：用户设置获取、设置面板渲染、密码修改
 * 
 * 依赖: js/index.js, js/files-core.js
 */

/**
 * 绑定主题下拉选择（默认首页）
 * @param {HTMLElement} wrap 容器 .select-wrap
 * @param {string} username 纯数字用户名
 */
function bindHomepageSelect(wrap, username) {
  const btn = wrap.querySelector('.select-display');
  const menu = wrap.querySelector('.select-menu');
  if (!btn || !menu) return;
  const parentRow = wrap.closest('.settings-row');
  const close = () => {
    wrap.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
    if (parentRow) parentRow.classList.remove('dropdown-open');
  };
  const open = () => {
    wrap.classList.add('open');
    btn.setAttribute('aria-expanded', 'true');
    if (parentRow) parentRow.classList.add('dropdown-open');
  };
  btn.addEventListener('click', () => { wrap.classList.contains('open') ? close() : open(); });
  document.addEventListener('click', (e) => { if (!wrap.contains(e.target)) close(); });
  menu.querySelectorAll('.option').forEach(item => {
    item.addEventListener('click', async () => {
      const value = String(item.getAttribute('data-value') || 'list');
      // UI 更新
      menu.querySelectorAll('.option').forEach(el => el.setAttribute('aria-selected', el === item ? 'true' : 'false'));
      btn.textContent = item.textContent || value;
      wrap.setAttribute('data-value', value);
      close();
      // 保存到后端
      try {
        const res = await fetch('/api/settings.php', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ username, HomepageSettings: value })
        });
        const ok = res.ok ? await res.json() : null;
        const container = document.getElementById('settings-content') || (wrap.parentElement || wrap);
        if (!ok || !ok.ok) throw new Error('保存失败');
        showTransientMessage(container, '默认首页已更新', 'success', 1800);
      } catch (e) {
        const container = document.getElementById('settings-content') || (wrap.parentElement || wrap);
        showTransientMessage(container, `保存失败：${String(e.message || e)}`, 'error', 2200);
      }
    });
  });
}

/**
 * 拉取或初始化用户设置
 * @param {string} username 纯数字用户名
 * @returns {Promise<{id:number,user:string,HomepageSettings:boolean}>}
 */
async function fetchSettings(username) {
  const url = `/api/settings.php?username=${encodeURIComponent(username)}`;
  const res = await fetch(url, { method: 'GET', credentials: 'include' });
  if (!res.ok) throw new Error('settings 请求失败');
  const data = await res.json();
  if (!data || !data.ok || !data.settings) throw new Error('settings 数据异常');
  return {
    id: Number(data.settings.id),
    user: String(data.settings.user),
    HomepageSettings: String(data.settings.HomepageSettings || 'list'),
    HiddenFile: Boolean(data.settings.HiddenFile),
    ShowHiddenFiles: Boolean(data.settings.ShowHiddenFiles)
  };
}

/**
 * 渲染设置面板内容
 * @param {string} username
 */
async function loadSettingsPanel(username) {
  const box = document.getElementById('settings-content');
  if (!box) return;
  box.innerHTML = '<span>加载中…</span>';
  try {
    const s = await fetchSettings(username);
    const checkedHidden = s.HiddenFile ? 'checked' : '';
    const checkedShowHidden = s.ShowHiddenFiles ? 'checked' : '';
    // 读取左侧导航按钮（排除 settings），构建下拉选项
    const user = getSessionUser();
    const navBtns = Array.from(document.querySelectorAll('.nav .nav-item'))
      .map(b => ({ target: String(b.dataset.target || ''), label: String(b.textContent || '').trim() }))
      .filter(x => x.target && x.target !== 'settings')
      .filter(x => {
        // 根据用户身份过滤不可用选项
        if (user && !user.isGraduation && x.target === 'graduation') return false;
        if (user && user.isGraduation && ['upload', 'list', 'shared'].includes(x.target)) return false;
        return true;
      });
    const currentLabel = (navBtns.find(x => x.target === s.HomepageSettings) || navBtns[0] || {label:'文件列表'}).label;
    const liHtml = navBtns.map(x => {
      const selected = (x.target === s.HomepageSettings) ? 'true' : 'false';
      return `<li class="option" role="option" data-value="${escapeAttr(x.target)}" aria-selected="${selected}">${escapeHtml(x.label)}</li>`;
    }).join('');
    box.innerHTML = `
      <div class="settings-row">
        <div class="setting-left">
          <div class="setting-icon">📄</div>
          <div>
            <div class="setting-title">默认首页</div>
            <div class="setting-desc"><span class="status-dot"></span>选择进入页面（自动读取左侧导航项）</div>
          </div>
        </div>
        <div class="setting-right">
          <div id="homepage-select" class="select-wrap" data-value="${escapeAttr(s.HomepageSettings)}">
            <button type="button" class="select-display" aria-haspopup="listbox" aria-expanded="false">${escapeHtml(currentLabel)}</button>
            <ul class="select-menu" role="listbox">${liHtml}</ul>
          </div>
        </div>
      </div>
      <div class="settings-row">
        <div class="setting-left">
          <div class="setting-icon">🔒</div>
          <div>
            <div class="setting-title">修改密码</div>
            <div class="setting-desc"><span class="status-dot"></span>点击打开修改密码窗口</div>
          </div>
        </div>
        <div class="setting-right">
          <button type="button" id="btn-change-pwd" class="btn primary">修改密码</button>
        </div>
      </div>
      <div class="settings-row">
        <div class="setting-left">
          <div class="setting-icon">🙈</div>
          <div>
            <div class="setting-title">上传时跳过隐藏文件</div>
            <div class="setting-desc"><span class="status-dot"></span>以"."开头的路径段将被过滤</div>
          </div>
        </div>
        <div class="setting-right">
          <label class="toggle">
            <input type="checkbox" id="hiddenfile-toggle" ${checkedHidden} />
            <span class="toggle-track"></span>
            <span class="toggle-thumb"></span>
          </label>
        </div>
      </div>
      <div class="settings-row">
        <div class="setting-left">
          <div class="setting-icon">👁️</div>
          <div>
            <div class="setting-title">列表显示隐藏文件</div>
            <div class="setting-desc"><span class="status-dot"></span>控制文件列表中隐藏项的可见性</div>
          </div>
        </div>
        <div class="setting-right">
          <label class="toggle">
            <input type="checkbox" id="showhidden-toggle" ${checkedShowHidden} />
            <span class="toggle-track"></span>
            <span class="toggle-thumb"></span>
          </label>
        </div>
      </div>
    `;
    const wrap = document.getElementById('homepage-select');
    if (wrap) { bindHomepageSelect(wrap, username); }
    const btnChangePwd = document.getElementById('btn-change-pwd');
    if (btnChangePwd) {
      btnChangePwd.addEventListener('click', () => {
        showChangePasswordModal(username);
      });
    }
    const toggleHidden = document.getElementById('hiddenfile-toggle');
    if (toggleHidden) {
      toggleHidden.onchange = async () => {
        const body = { username, HiddenFile: !!toggleHidden.checked };
        try {
          const res = await fetch('/api/settings.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(body)
          });
          if (!res.ok) throw new Error('保存失败');
          const data = await res.json();
          if (!data || !data.ok) throw new Error('保存失败');
          showTransientMessage(box, '设置已更新', 'success', 2000);
          state.skipHiddenUpload = !!toggleHidden.checked;
        } catch (e) {
          showTransientMessage(box, `保存失败：${String(e.message || e)}`, 'error', 2500);
          toggleHidden.checked = !toggleHidden.checked; // 回滚 UI
        }
      };
    }
    const toggleShowHidden = document.getElementById('showhidden-toggle');
    if (toggleShowHidden) {
      toggleShowHidden.onchange = async () => {
        const body = { username, ShowHiddenFiles: !!toggleShowHidden.checked };
        try {
          const res = await fetch('/api/settings.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(body)
          });
          if (!res.ok) throw new Error('保存失败');
          const data = await res.json();
          if (!data || !data.ok) throw new Error('保存失败');
          showTransientMessage(box, '设置已更新', 'success', 2000);
          state.showHiddenList = !!toggleShowHidden.checked;
          // 刷新列表以应用可见性变化
          await fetchList(username, state.currentDir);
        } catch (e) {
          showTransientMessage(box, `保存失败：${String(e.message || e)}`, 'error', 2500);
          toggleShowHidden.checked = !toggleShowHidden.checked; // 回滚 UI
        }
      };
    }
  } catch (e) {
    box.innerHTML = `<span class="error">加载设置失败：${escapeHtml(String(e.message || e))}</span>`;
  }
}

/**
 * 显示修改密码模态框
 * @param {string} username 当前用户
 */
function showChangePasswordModal(username) {
  // 避免重复创建
  let overlay = document.getElementById('modal-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'modal-overlay';
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div class="modal-title" id="modal-title">修改密码</div>
        <div class="modal-body">
          <label class="form-label">当前密码
            <input type="password" id="pwd-old" class="input" placeholder="输入当前密码" />
          </label>
          <label class="form-label">新密码
            <input type="password" id="pwd-new" class="input" placeholder="至少 6 位" />
          </label>
          <label class="form-label">确认新密码
            <input type="password" id="pwd-confirm" class="input" placeholder="再次输入新密码" />
          </label>
          <div id="pwd-msg" class="message" aria-live="polite"></div>
        </div>
        <div class="modal-actions">
          <button type="button" id="pwd-cancel" class="btn">取消</button>
          <button type="button" id="pwd-save" class="btn primary">保存</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
  }
  overlay.style.display = 'flex';

  const elOld = overlay.querySelector('#pwd-old');
  const elNew = overlay.querySelector('#pwd-new');
  const elConfirm = overlay.querySelector('#pwd-confirm');
  const msgEl = overlay.querySelector('#pwd-msg');
  const btnCancel = overlay.querySelector('#pwd-cancel');
  const btnSave = overlay.querySelector('#pwd-save');

  const close = () => { overlay.style.display = 'none'; };
  btnCancel.onclick = close;
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });
  btnSave.onclick = async () => {
    msgEl.textContent = '';
    const oldPwd = elOld ? elOld.value : '';
    const newPwd = elNew ? elNew.value : '';
    const confirmPwd = elConfirm ? elConfirm.value : '';
    if (!oldPwd || !newPwd) { msgEl.textContent = '请填写当前密码与新密码'; msgEl.className = 'message error'; return; }
    if (newPwd.length < 6) { msgEl.textContent = '新密码长度至少 6 位'; msgEl.className = 'message error'; return; }
    if (newPwd !== confirmPwd) { msgEl.textContent = '两次输入的新密码不一致'; msgEl.className = 'message error'; return; }
    try {
      btnSave.disabled = true;
      const res = await fetch('/api/change_password.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, oldPassword: oldPwd, newPassword: newPwd })
      });
      const data = res.ok ? await res.json() : null;
      if (!res.ok || !data || !data.ok) {
        msgEl.textContent = (data && data.error) ? data.error : '修改失败';
        msgEl.className = 'message error';
        btnSave.disabled = false;
        return;
      }
      msgEl.textContent = '修改成功，请使用新密码重新登录';
      msgEl.className = 'message success';
      setTimeout(() => {
        close();
        // 安全起见，清除会话并跳转登录
        localStorage.removeItem('currentUser');
        location.href = 'index.html';
      }, 1200);
    } catch (e) {
      msgEl.textContent = `修改失败：${String(e.message || e)}`;
      msgEl.className = 'message error';
      btnSave.disabled = false;
    }
  };
}
