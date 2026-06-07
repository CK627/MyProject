/**
 * 公共 JavaScript 工具库
 * 提供所有页面共用的基础功能，避免代码重复
 */

// =========================
// 常量配置
// =========================

/**
 * 分片大小（字节）- 2MB
 * 修改此常量可统一调整所有分片上传的分片大小
 */
const CHUNK_SIZE = 2 * 1024 * 1024;

// =========================
// HTML 转义工具
// =========================

/**
 * 简单转义，避免XSS
 * @param {string} s 原始字符串
 * @returns {string} 转义后的字符串
 */
function escapeHtml(s) {
  const str = s == null ? '' : String(s);
  return str.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
}

/**
 * 属性值转义
 * @param {string} s 原始字符串
 * @returns {string} 转义后的字符串
 */
function escapeAttr(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
}

// =========================
// 消息显示工具
// =========================

/**
 * 在页面上显示提示消息
 * @param {string} text 要显示的文案
 * @param {"success"|"error"|"info"} [type="info"] 消息类型
 * @param {string} [elementId="message"] 消息元素ID
 */
function showMessage(text, type = "info", elementId = "message") {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = text;
  el.className = `message ${type}`;
}

/**
 * 在容器中显示短暂提示并自动移除
 * @param {HTMLElement} container 提示插入的容器
 * @param {string} text 提示文本
 * @param {'success'|'error'|'info'} [type='info'] 提示类型影响颜色
 * @param {number} [timeout=2000] 自动移除的毫秒数
 */
function showTransientMessage(container, text, type = 'info', timeout = 2000) {
  const el = document.createElement('div');
  el.className = `message ${type}`;
  el.textContent = text;
  container.appendChild(el);
  setTimeout(() => {
    if (el.parentNode) el.parentNode.removeChild(el);
  }, timeout);
}

// =========================
// 进度条工具
// =========================

/**
 * 设置进度条
 * @param {string} wrapId 进度条容器ID
 * @param {number} pct 进度百分比 (0-100)
 * @param {string} label 进度标签
 */
function setProgress(wrapId, pct, label) {
  const wrap = document.getElementById(wrapId);
  if (!wrap) return;
  const bar = wrap.querySelector('.progress-bar');
  const text = wrap.querySelector('.progress-text');
  wrap.classList.add('active');
  if (bar) bar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  if (text) text.textContent = `${label}（${Math.max(0, Math.min(100, Math.floor(pct)))}%）`;
}

/**
 * 重置进度条
 * @param {string} wrapId 进度条容器ID
 */
function resetProgress(wrapId) {
  const wrap = document.getElementById(wrapId);
  if (!wrap) return;
  const bar = wrap.querySelector('.progress-bar');
  const text = wrap.querySelector('.progress-text');
  wrap.classList.remove('active');
  if (bar) bar.style.width = '0%';
  if (text) text.textContent = '';
}

// =========================
// 路径与文件工具
// =========================

/**
 * 判断路径是否为隐藏（任意段以 '.' 开头）
 * @param {string} p 相对路径或文件名
 * @returns {boolean}
 */
function isHiddenPath(p) {
  if (!p) return false;
  return String(p).split('/').some(seg => seg.startsWith('.'));
}

/**
 * 判断文件是否为隐藏（文件名或相对路径任意段以 '.' 开头）
 * @param {File} f 文件对象
 * @returns {boolean}
 */
function isHiddenFile(f) {
  const rel = String((f && (f.webkitRelativePath || f.name)) || '');
  return isHiddenPath(rel);
}

/**
 * 获取文件名（从路径中提取）
 * @param {string} p 文件路径
 * @returns {string} 文件名
 */
function getFilename(p) {
  const i = p.lastIndexOf('/');
  return i >= 0 ? p.slice(i + 1) : p;
}

/**
 * 简易 dirname 实现（基于 / 分隔）
 * @param {string} p 路径
 * @returns {string} 目录部分
 */
function dirname(p) {
  if (!p) return '';
  const idx = p.lastIndexOf('/');
  if (idx <= 0) return '';
  return p.slice(0, idx);
}

/**
 * 拼接路径（确保不重复斜杠）
 * @param {string} a 路径A
 * @param {string} b 路径B
 * @returns {string} 拼接后的路径
 */
function joinPath(a, b) {
  const A = String(a || '').replace(/\/+$/, '');
  const B = String(b || '').replace(/^\/+/, '');
  if (!A) return B;
  if (!B) return A;
  return `${A}/${B}`;
}

// =========================
// 本地存储工具
// =========================

/**
 * 获取当前登录用户（学生）
 * @returns {{username:string,userId:number,role?:string,isGraduation?:boolean}|null}
 */
function getSessionUser() {
  try {
    const raw = localStorage.getItem("currentUser");
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

/**
 * 获取当前登录管理员（教师）
 * @returns {{username:string,adminId?:number,class?:string}|null}
 */
function getAdmin() {
  try {
    const raw = localStorage.getItem('currentAdmin');
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

// =========================
// API 请求工具（支持 Session Cookie）
// =========================

/**
 * 发送 POST JSON 请求（携带 Session Cookie）
 * @param {string} url API 地址
 * @param {object} data 请求体对象
 * @returns {Promise<Response>}
 */
function apiPost(url, data = {}) {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(data)
  });
}

/**
 * 发送 GET 请求（携带 Session Cookie）
 * @param {string} url API 地址
 * @returns {Promise<Response>}
 */
function apiGet(url) {
  return fetch(url, {
    method: 'GET',
    credentials: 'include'
  });
}

// =========================
// Session 认证工具
// =========================

/**
 * 检查当前会话状态
 * @returns {Promise<{loggedIn: boolean, user?: {userId: number, username: string, role: string, class?: string}}>}
 */
async function checkSession() {
  try {
    const res = await apiGet('/api/check_session.php');
    if (res.ok) {
      return await res.json();
    }
    return { loggedIn: false };
  } catch (e) {
    console.error('[checkSession]', e);
    return { loggedIn: false };
  }
}

/**
 * 登出当前会话
 * @returns {Promise<boolean>}
 */
async function logout() {
  try {
    const res = await apiPost('/api/logout.php');
    // 必须等待响应体读取完成，否则页面跳转可能会中断请求连接
    await safeJson(res); 
    
    // 清除 localStorage 中的旧用户信息
    try {
      localStorage.removeItem('currentUser');
      localStorage.removeItem('currentAdmin');
    } catch (e) {}
    return res.ok;
  } catch (e) {
    console.error('[logout]', e);
    return false;
  }
}

/**
 * 要求必须登录，未登录则跳转到登录页
 * @param {string[]} allowedRoles 允许的角色，空数组表示任意角色
 * @returns {Promise<{userId: number, username: string, role: string}|null>}
 */
async function requireLogin(allowedRoles = []) {
  const session = await checkSession();
  if (!session.loggedIn) {
    alert('未登录或会话已过期，请重新登录');
    location.href = 'index.html';
    return null;
  }
  if (allowedRoles.length > 0 && !allowedRoles.includes(session.user.role)) {
    alert('无权访问此页面');
    location.href = 'index.html';
    return null;
  }
  return session.user;
}

// =========================
// Loading 遮罩工具
// =========================

/**
 * 创建遮罩 DOM（若不存在）
 * @returns {HTMLElement} overlay
 */
function ensureLoadingOverlay() {
  let overlay = document.getElementById('loading-overlay');
  if (overlay) return overlay;
  overlay = document.createElement('div');
  overlay.id = 'loading-overlay';
  overlay.setAttribute('role', 'alert');
  overlay.setAttribute('aria-live', 'assertive');
  overlay.setAttribute('aria-hidden', 'true');
  overlay.innerHTML = '<div class="loading-box"><div class="loading-spinner" aria-hidden="true"></div><span id="loading-text">正在处理，请稍候…</span></div>';
  document.body.appendChild(overlay);
  return overlay;
}

/**
 * 显示全局加载遮罩
 * @param {string} [text] 提示文案
 */
function showLoading(text) {
  const overlay = ensureLoadingOverlay();
  overlay.classList.add('active');
  overlay.setAttribute('aria-hidden', 'false');
  const label = document.getElementById('loading-text');
  if (label && text) label.textContent = text;
}

/**
 * 隐藏全局加载遮罩
 */
function hideLoading() {
  const overlay = ensureLoadingOverlay();
  overlay.classList.remove('active');
  overlay.setAttribute('aria-hidden', 'true');
}

// =========================
// JSON 安全解析
// =========================

/**
 * 安全解析 JSON
 * @param {Response} res fetch 响应对象
 * @returns {Promise<any>} 解析结果，失败返回 null
 */
async function safeJson(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

// =========================
// 唯一ID生成
// =========================

/**
 * 生成唯一上传 ID
 * @returns {string}
 */
function genUploadId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * 生成基于文件的稳定 upload_id（用于断点续传）
 * @param {File} file 文件对象
 * @param {string} username 用户名
 * @returns {string}
 */
function genStableUploadId(file, username) {
  // 使用文件名+大小+用户名生成稳定 ID
  const str = `${username}-${file.name}-${file.size}`;
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const chr = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + chr;
    hash |= 0;
  }
  return `resume-${Math.abs(hash).toString(36)}`;
}

// =========================
// 毛玻璃输入弹窗
// =========================

/**
 * 显示自定义输入弹窗（替代 prompt）
 * @param {Object} options 配置项
 * @param {string} options.title 弹窗标题
 * @param {string} [options.message] 提示文字
 * @param {string} [options.defaultValue=''] 默认值
 * @param {string} [options.placeholder=''] 输入框占位符
 * @param {string} [options.confirmText='确定'] 确认按钮文字
 * @param {string} [options.cancelText='取消'] 取消按钮文字
 * @param {Function} [options.validator] 验证函数，返回错误信息或 null
 * @returns {Promise<string|null>} 输入值或 null（取消）
 */
function showPrompt(options) {
  return new Promise((resolve) => {
    const {
      title = '请输入',
      message = '',
      defaultValue = '',
      placeholder = '',
      confirmText = '确定',
      cancelText = '取消',
      validator = null
    } = options || {};

    // 创建遮罩层
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.display = 'flex';
    overlay.innerHTML = `
      <div class="modal-dialog prompt-dialog" role="dialog" aria-modal="true" aria-labelledby="prompt-title">
        <div class="modal-title" id="prompt-title">${escapeHtml(title)}</div>
        <div class="modal-body">
          ${message ? `<p class="prompt-message">${escapeHtml(message)}</p>` : ''}
          <input type="text" class="input prompt-input" value="${escapeAttr(defaultValue)}" placeholder="${escapeAttr(placeholder)}" />
          <div class="prompt-error" aria-live="polite"></div>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-link prompt-cancel">${escapeHtml(cancelText)}</button>
          <button type="button" class="primary prompt-confirm">${escapeHtml(confirmText)}</button>
        </div>
      </div>`;

    document.body.appendChild(overlay);

    const input = overlay.querySelector('.prompt-input');
    const errorEl = overlay.querySelector('.prompt-error');
    const btnCancel = overlay.querySelector('.prompt-cancel');
    const btnConfirm = overlay.querySelector('.prompt-confirm');

    // 聚焦并选中输入框
    setTimeout(() => {
      input.focus();
      input.select();
    }, 50);

    // 关闭弹窗
    function close(value) {
      overlay.remove();
      resolve(value);
    }

    // 验证并确认
    function confirm() {
      const value = input.value.trim();
      if (validator) {
        const error = validator(value);
        if (error) {
          errorEl.textContent = error;
          input.focus();
          return;
        }
      }
      close(value);
    }

    // 事件绑定
    btnCancel.addEventListener('click', () => close(null));
    btnConfirm.addEventListener('click', confirm);
    
    // Enter 确认，Esc 取消
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        confirm();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        close(null);
      }
    });

    // 清除错误提示
    input.addEventListener('input', () => {
      errorEl.textContent = '';
    });

    // 点击遮罩层关闭
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        close(null);
      }
    });
  });
}

/**
 * 启动会话状态监控
 * 定期检查 Session 是否有效，若失效则自动登出并跳转
 * @param {number} [interval=60000] 检查间隔（毫秒），默认60秒
 */
function startSessionMonitor(interval = 60000) {
  if (window._sessionMonitorTimer) clearInterval(window._sessionMonitorTimer);
  window._sessionMonitorTimer = setInterval(async () => {
    try {
      const session = await checkSession();
      if (!session.loggedIn) {
        clearInterval(window._sessionMonitorTimer);
        alert('登录会话已过期，请重新登录');
        await logout();
        location.href = 'index.html';
      }
    } catch (e) {
      console.warn('[SessionMonitor] Check failed', e);
    }
  }, interval);
}

/**
 * 显示确认弹窗（替代 confirm）
 * @param {Object} options 配置项
 * @param {string} options.title 弹窗标题
 * @param {string} options.message 提示文字
 * @param {string} [options.confirmText='确定'] 确认按钮文字
 * @param {string} [options.cancelText='取消'] 取消按钮文字
 * @param {boolean} [options.danger=false] 是否危险操作
 * @returns {Promise<boolean>}
 */
function showConfirm(options) {
  return new Promise((resolve) => {
    const {
      title = '确认',
      message = '',
      confirmText = '确定',
      cancelText = '取消',
      danger = false
    } = options || {};

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.display = 'flex';
    overlay.innerHTML = `
      <div class="modal-dialog confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title">
        <div class="modal-title" id="confirm-title">${escapeHtml(title)}</div>
        <div class="modal-body">
          <p class="confirm-message">${escapeHtml(message)}</p>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-link confirm-cancel">${escapeHtml(cancelText)}</button>
          <button type="button" class="primary confirm-ok ${danger ? 'danger' : ''}">${escapeHtml(confirmText)}</button>
        </div>
      </div>`;

    document.body.appendChild(overlay);

    const btnCancel = overlay.querySelector('.confirm-cancel');
    const btnConfirm = overlay.querySelector('.confirm-ok');

    function close(result) {
      overlay.remove();
      resolve(result);
    }

    btnCancel.addEventListener('click', () => close(false));
    btnConfirm.addEventListener('click', () => close(true));
    
    // Esc 取消
    overlay.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        close(false);
      }
    });

    // 点击遮罩层关闭
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        close(false);
      }
    });

    // 聚焦确认按钮
    setTimeout(() => btnConfirm.focus(), 50);
  });
}
