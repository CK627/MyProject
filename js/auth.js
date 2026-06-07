/**
 * 简易登录/注册前端逻辑
 * - 尝试调用后端 API（开发默认 http://localhost:3000）
 * - 若后端不可用，回退到 localStorage 演示模式（仅用于本地演示）
 * - 每个函数控制在 50 行以内，含 JSDoc 注释
 * 
 * 依赖: js/index.js (公共库)
 */

const API_BASE = ""; // 同源调用 PHP API（通过内置服务器提供）

// showMessage, apiPost 等函数已移至 js/index.js

/**
 * 发送 JSON 请求（简单包装，支持 Session Cookie）- 对应登录页的路径调用
 * @param {string} path - API 路径，如 /api/auth/login
 * @param {object} data - 请求体对象
 * @returns {Promise<Response>} fetch 响应
 */
function postJSON(path, data) {
  return apiPost(`${API_BASE}${path}`, data);
}

/**
 * 切换登录/注册面板（带过渡动画）
 */
function initTabs() {
  const loginTab = document.getElementById("tab-login");
  const gradTab = document.getElementById("tab-grad");
  const teacherTab = document.getElementById("tab-teacher");
  const registerTab = document.getElementById("tab-register");
  const loginSection = document.getElementById("login-section");
  const gradSection = document.getElementById("grad-section");
  const teacherSection = document.getElementById("teacher-section");
  const registerSection = document.getElementById("register-section");
  
  const panels = [loginSection, gradSection, teacherSection, registerSection].filter(Boolean);
  const tabs = [loginTab, gradTab, teacherTab, registerTab].filter(Boolean);
  const panelMap = { login: loginSection, grad: gradSection, teacher: teacherSection, register: registerSection };
  const tabMap = { login: loginTab, grad: gradTab, teacher: teacherTab, register: registerTab };
  
  let currentPanel = 'login';
  let isAnimating = false;
  
  const setActive = (panel) => {
    if (panel === currentPanel || isAnimating) return;
    isAnimating = true;
    
    // 更新标签状态
    tabs.forEach(t => t && t.classList.remove('active'));
    if (tabMap[panel]) tabMap[panel].classList.add('active');
    
    // 隐藏当前面板（添加退出动画）
    const oldPanel = panelMap[currentPanel];
    const newPanel = panelMap[panel];
    
    if (oldPanel) {
      oldPanel.classList.add('fade-out');
      oldPanel.classList.remove('active');
    }
    
    // 延迟显示新面板（等待退出动画完成）
    setTimeout(() => {
      if (oldPanel) oldPanel.classList.remove('fade-out');
      if (newPanel) newPanel.classList.add('active');
      currentPanel = panel;
      isAnimating = false;
    }, 150);
    
    showMessage("");
  };
  
  if (loginTab) loginTab.addEventListener("click", () => setActive("login"));
  if (gradTab) gradTab.addEventListener("click", () => setActive("grad"));
  if (teacherTab) teacherTab.addEventListener("click", () => setActive("teacher"));
  if (registerTab) registerTab.addEventListener("click", () => setActive("register"));
}

/**
 * 生成密码哈希（演示用途，不替代后端安全实现）
 * @param {string} text - 原始密码
 * @returns {Promise<string>} 十六进制哈希
 */
async function hash(text) {
  const enc = new TextEncoder().encode(text);
  const buf = await crypto.subtle.digest("SHA-256", enc);
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
}

/**
 * 处理登录提交
 */
function initLogin() {
  const form = document.getElementById("login-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value;
    console.log('[Login] Input values - username:', username, 'password:', password ? '***' : '(empty)');
    console.log('[Login] Username field element:', document.getElementById("login-username"));
    console.log('[Login] Password field element:', document.getElementById("login-password"));
    if (!username || !password) return showMessage("请填写用户名和密码", "error");
    try {
      const res = await postJSON("/api/login.php", { action: "login", username, password });
      console.log('[Login] Response status:', res.status, res.ok);
      const text = await res.text();
      console.log('[Login] Response body:', text);
      let data;
      try {
        data = JSON.parse(text);
      } catch (parseErr) {
        console.error('[Login] JSON parse error:', parseErr);
        showMessage("登录异常：服务器返回无效数据", "error");
        return;
      }
      if (res.ok) {
        if (data && data.ok) {
          showMessage("登录成功，即将进入文件页", "success");
          // 保存当前会话并跳转
          try {
            localStorage.setItem("currentUser", JSON.stringify({ username, userId: data.userId || 0 }));
          } catch (e) {}
          // 先确保创建用户文件表，再跳转（也可在文件页初始化时处理）
          try {
            await postJSON("/api/files.php", { username });
          } catch (e) {}
          location.href = "files.html";
        } else {
          showMessage((data && data.error) || "登录失败", "error");
        }
      } else {
        // 回退：演示模式（localStorage）
        const demoUsers = JSON.parse(localStorage.getItem("demoUsers") || "{}");
        const saved = demoUsers[username];
        if (saved && saved.hash === await hash(password)) {
          showMessage("登录成功（演示模式）", "success");
        } else {
          showMessage("登录失败：用户名或密码错误", "error");
        }
      }
    } catch (err) {
      console.error('[Login Error]', err);
      showMessage("登录异常：后端不可用，使用演示模式", "error");
    }
  });
}

/**
 * 毕业学生登录
 */
function initGradLogin() {
  const form = document.getElementById("grad-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("grad-username").value.trim();
    if (!username) return showMessage("请填写学号", "error");
    if (!/^\d+$/.test(username)) return showMessage("学号必须为纯数字", "error");
    try {
      const res = await postJSON("/api/graduation_login.php", { username });
      const data = res.ok ? await res.json() : null;
      if (!res.ok || !data || !data.ok) return showMessage((data && data.error) || "毕业登录失败", "error");
      // 保存毕业会话并进入文件页（默认定位到毕业提交）
      try {
        localStorage.setItem("currentUser", JSON.stringify({ username, isGraduation: true, realName: data.name || "" }));
      } catch (e) {}
      location.href = "files.html";
    } catch (err) {
      console.error('[Graduation Login Error]', err);
      showMessage("毕业登录异常：网络或服务器错误", "error");
    }
  });
}

/**
 * 处理注册提交
 */
function initRegister() {
  const form = document.getElementById("register-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("register-username").value.trim();
    const password = document.getElementById("register-password").value;
    const password2 = document.getElementById("register-password2").value;
    if (!username || !password || !password2) return showMessage("请完整填写注册信息", "error");
    if (!/^\d+$/.test(username)) return showMessage("用户名必须为纯数字", "error");
    if (password.length < 6) return showMessage("密码长度至少 6 位", "error");
    if (password !== password2) return showMessage("两次密码不一致", "error");
    try {
      const res = await postJSON("/api/login.php", { action: "register", username, password });
      if (res.ok) {
        const data = await res.json();
        if (data && data.ok) {
          showMessage("注册成功，请切换到登录", "success");
        } else {
          showMessage((data && data.error) || "注册失败", "error");
        }
      } else {
        // 回退：演示模式（localStorage）
        const demoUsers = JSON.parse(localStorage.getItem("demoUsers") || "{}");
        if (demoUsers[username]) return showMessage("用户名已存在", "error");
        demoUsers[username] = { hash: await hash(password), createdAt: Date.now() };
        localStorage.setItem("demoUsers", JSON.stringify(demoUsers));
        showMessage("注册成功（演示模式），请切换到登录", "success");
      }
    } catch (err) {
      console.error('[Register Error]', err);
      showMessage("注册异常：后端不可用，使用演示模式", "error");
    }
  });
}

/**
 * 初始化“忘记密码”链接交互
 * - 登录页提供友好提示，当前系统不支持自助找回
 */
/**
 * 初始化“忘记密码”交互
 * 点击后弹出居中弹窗：按用户名设置新密码
 */
function initForgotPassword() {
  const link = document.getElementById("forgot-password");
  if (!link) return;
  link.addEventListener("click", (e) => {
    e.preventDefault();
    openForgotPasswordModal();
  });
}

/**
 * 打开重置密码弹窗（用户名 + 新密码 + 确认）
 */
function openForgotPasswordModal() {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="fp-title">
      <div class="modal-title" id="fp-title">重置密码</div>
      <div class="modal-body">
        <label class="form-label">用户名
          <input id="fp-username" class="input" type="text" maxlength="64" />
        </label>
        <label class="form-label">新密码
          <input id="fp-password" class="input" type="password" maxlength="255" />
        </label>
        <label class="form-label">确认新密码
          <input id="fp-password2" class="input" type="password" maxlength="255" />
        </label>
      </div>
      <div class="modal-actions">
        <button id="fp-cancel" class="btn-link" type="button">取消</button>
        <button id="fp-submit" class="primary" type="button">保存</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  overlay.style.display = "flex";

  // 预填用户名
  const usernameInput = overlay.querySelector("#fp-username");
  const loginUserInput = document.getElementById("login-username");
  if (loginUserInput && loginUserInput.value) {
    usernameInput.value = loginUserInput.value.trim();
  }

  overlay.querySelector("#fp-cancel").addEventListener("click", () => {
    overlay.remove();
  });
  overlay.addEventListener("click", (ev) => {
    if (ev.target === overlay) overlay.remove();
  });
  overlay.querySelector("#fp-submit").addEventListener("click", async () => {
    const username = usernameInput.value.trim();
    const p1 = overlay.querySelector("#fp-password").value;
    const p2 = overlay.querySelector("#fp-password2").value;
    if (!username || !p1 || !p2) return showMessage("请完整填写信息", "error");
    if (!/^\d+$/.test(username)) return showMessage("用户名必须为纯数字", "error");
    if (p1.length < 6) return showMessage("新密码长度至少 6 位", "error");
    if (p1 !== p2) return showMessage("两次新密码不一致", "error");
    try {
      const res = await postJSON("/api/reset_password.php", { username, newPassword: p1 });
      if (res.ok) {
        const data = await res.json();
        if (data && data.ok) {
          showMessage("重置成功，请使用新密码登录", "success");
          overlay.remove();
        } else {
          showMessage((data && data.error) || "重置失败", "error");
        }
      } else {
        showMessage("重置失败：服务器不可用", "error");
      }
    } catch (err) {
      console.error('[Reset Password Error]', err);
      showMessage("重置异常：网络或服务器错误", "error");
    }
  });
}

// 初始化
function initAll() {
  initTabs();
  initLogin();
  initGradLogin();
  initTeacherLogin();
  initRegister();
  initForgotPassword();
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAll);
} else {
  initAll();
}
function initTeacherLogin() {
  const form = document.getElementById("teacher-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("teacher-username").value.trim();
    const password = document.getElementById("teacher-password").value;
    if (!username || !password) return showMessage("请填写用户名和密码", "error");
    try {
      const res = await postJSON("/api/admin_login.php", { username, password });
      // 无论状态码如何，都尝试解析 JSON 响应
      let data = null;
      try {
        data = await res.json();
      } catch (parseErr) {
        console.error('[Teacher Login] JSON parse error:', parseErr);
      }
      console.log('[Teacher Login] Response:', { status: res.status, ok: res.ok, data });
      if (!res.ok || !data || !data.ok) {
        const errorMsg = (data && data.error) || "教师登录失败";
        return showMessage(errorMsg, "error");
      }
      try {
        localStorage.setItem("currentAdmin", JSON.stringify({ username, adminId: data.adminId || 0, class: String(data.class || '') }));
      } catch (e) {}
      location.href = "teacher.html";
    } catch (err) {
      console.error('[Teacher Login Error]', err);
      showMessage("教师登录异常：网络或服务器错误", "error");
    }
  });
}
