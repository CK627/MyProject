/**
 * 文件页面 - 核心模块
 * 包含：状态管理、入口初始化、用户表初始化、登出
 * 
 * 依赖: js/index.js (公共库)
 * 被依赖: files-list.js, files-settings.js, files-graduation.js, files-shared.js
 */

/**
 * 列表刷新并发控制序号，确保只渲染最后一次请求的结果
 */
let listRequestSeq = 0;

/**
 * 当前目录状态
 */
const state = { currentDir: '', skipHiddenUpload: true, showHiddenList: false, thesisSubmitted: false, internshipSubmitted: false };
// 服务器上传大小限制（字节），在首次成功上传响应中同步
const serverLimits = { uploadMaxBytes: null, postMaxBytes: null };
// 多选状态：已选文件 id 集合
const selectedIds = new Set();
// 多选状态：已选文件夹名集合（当前目录下的名称）
const selectedFolders = new Set();

/**
 * 为列表消息显示提供便捷方法
 */
function showListMessage(text, type = "info") {
  showMessage(text, type, "list-msg");
}

/**
 * 初始化用户表（FileUploadS）
 * @param {string} username
 */
async function ensureUserTable(username) {
  const res = await fetch("/api/files.php", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username })
  });
  if (res.ok) {
    const data = await res.json();
    if (data && data.ok) {
      showMessage(data.created ? "已创建用户文件表" : "用户文件表已存在", "success");
    } else {
      showMessage("初始化失败", "error");
    }
  } else {
    showMessage("服务不可用：初始化失败", "error");
  }
}

/**
 * 格式化已选择的文件名列表
 * @param {FileList} files
 * @returns {string}
 */
function formatChosenFiles(files) {
  try {
    return Array.from(files || [])
      .filter(f => {
        const rel = (f.webkitRelativePath || f.name || '').trim();
        return !isHiddenPath(rel);
      })
      .map(f => (f.webkitRelativePath || f.name))
      .join('、');
  } catch (e) {
    return '';
  }
}

/**
 * 将已选文件渲染为标签 chips
 * @param {FileList} files
 * @returns {DocumentFragment}
 */
function renderChosenChips(files) {
  const frag = document.createDocumentFragment();
  Array.from(files || [])
    .filter(f => {
      const rel = (f.webkitRelativePath || f.name || '').trim();
      return !isHiddenPath(rel);
    })
    .forEach(f => {
    const span = document.createElement('span');
    span.className = 'chip';
    span.textContent = f.webkitRelativePath || f.name;
    frag.appendChild(span);
  });
  return frag;
}

/**
 * 页面初始化（优先使用 Session 认证）
 */
async function init() {
  // 优先检查 Session 认证
  let user = null;
  try {
    const session = await checkSession();
    if (session.loggedIn && session.user) {
      user = {
        username: session.user.username,
        userId: session.user.userId,
        role: session.user.role,
        isGraduation: session.user.role === 'graduation'
      };
      // 同步到 localStorage 保持兼容
      try {
        localStorage.setItem('currentUser', JSON.stringify(user));
      } catch (e) {}
    }
  } catch (e) {
    console.warn('[Session Check Failed]', e);
  }
  
  // 回退到 localStorage
  if (!user) {
    user = getSessionUser();
  }
  
  if (!user || !/^\d+$/.test(user.username)) {
    // 无会话或不合规用户名，跳回登录页
    location.href = "index.html";
    return;
  }
  {
    const chip = document.getElementById("current-user");
    const label = user.isGraduation ? '毕业生' : '用户';
    const display = user.isGraduation && String(user.realName || '').trim() !== '' ? String(user.realName).trim() : String(user.username);
    if (chip) chip.textContent = `${label}：${display}`;
  }
  if (!user.isGraduation) {
    await ensureUserTable(user.username);
  }

  // 根据用户设置决定默认面板（上传/列表）
  let initialTarget = user.isGraduation ? 'graduation' : 'list';
  if (!user.isGraduation) {
    try {
      const s = await fetchSettings(user.username);
      initialTarget = String(s.HomepageSettings || 'list');
      state.skipHiddenUpload = !!s.HiddenFile;
      state.showHiddenList = !!s.ShowHiddenFiles;
    } catch (_) {
      initialTarget = 'list';
    }
  }
  initSidebar(user.username, initialTarget);

  // 上传实现
  initUploadSection(user);

  // 登出
  const btnLogout = document.getElementById("btn-logout");
  if (btnLogout) btnLogout.addEventListener("click", async () => {
    await logout();
    location.href = "index.html";
  });

  // 目录操作：返回上级
  const btnDirUp = document.getElementById('btn-dir-up');
  if (!user.isGraduation && btnDirUp) btnDirUp.addEventListener('click', async () => {
    if (!state.currentDir) return;
    if (btnDirUp.dataset.busy === '1') return;
    btnDirUp.dataset.busy = '1';
    btnDirUp.disabled = true;
    showLoading('正在加载列表，请稍候…');
    const parts = state.currentDir.split('/');
    parts.pop();
    state.currentDir = parts.join('/');
    try {
      await fetchList(user.username, state.currentDir);
    } finally {
      hideLoading();
      btnDirUp.disabled = false;
      delete btnDirUp.dataset.busy;
    }
  });
  // 新建文件夹
  const btnMkdir = document.getElementById('btn-mkdir');
  if (!user.isGraduation && btnMkdir) btnMkdir.addEventListener('click', async () => {
    const name = prompt('输入新文件夹名称，例如: Docs 或 Images');
    if (!name) return;
    try {
      if (btnMkdir.dataset.busy === '1') return;
      btnMkdir.dataset.busy = '1';
      btnMkdir.disabled = true;
      showLoading('正在创建文件夹，请稍候…');
      const res = await fetch('/api/mkdir.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: user.username, dir: state.currentDir, name })
      });
      const ok = res.ok ? await res.json() : null;
      if (ok && ok.ok) {
        await fetchList(user.username, state.currentDir);
      } else {
        alert((ok && ok.error) || '创建文件夹失败');
      }
    } catch (e) {
      alert('创建文件夹异常');
    } finally {
      hideLoading();
      btnMkdir.disabled = false;
      delete btnMkdir.dataset.busy;
    }
  });

  // 初次加载列表
  if (!user.isGraduation) { await fetchList(user.username, state.currentDir); }

  // 初始化毕业模块
  await initGraduationSection(user);

  // 选择文件状态展示
  const inputElFiles = document.getElementById("file-input-files");
  const inputElFolder = document.getElementById("file-input-folder");
  const chosenEl = document.getElementById("file-chosen");
  function onFilesChosen(files) {
    if (!chosenEl) return;
    const count = files ? files.length : 0;
    if (count === 0) { chosenEl.textContent = "未选择文件/文件夹"; return; }
    chosenEl.innerHTML = "";
    chosenEl.appendChild(renderChosenChips(files));
  }
  if (!user.isGraduation && inputElFiles) inputElFiles.addEventListener("change", () => {
    // 清空文件夹选择，避免混用
    if (inputElFolder) inputElFolder.value = "";
    onFilesChosen(inputElFiles.files);
  });
  if (!user.isGraduation && inputElFolder) inputElFolder.addEventListener("change", () => {
    // 清空文件选择，避免混用
    if (inputElFiles) inputElFiles.value = "";
    onFilesChosen(inputElFolder.files);
  });
  
  // 启动 Session 监控
  startSessionMonitor(30000);
}

/**
 * 初始化上传区域事件绑定
 */
function initUploadSection(user) {
  const btnUpload = document.getElementById("btn-upload");
  const fileInput = document.getElementById("file-input-files");
  const folderInput = document.getElementById("file-input-folder");
  if (!user.isGraduation && btnUpload) btnUpload.addEventListener("click", async () => {
    const files = (folderInput && folderInput.files && folderInput.files.length > 0) ? folderInput.files : (fileInput && fileInput.files) ;
    const msg = document.getElementById("upload-msg");
    if (!files || files.length === 0) {
      msg.textContent = "请选择文件后再上传";
      msg.className = "message error";
      return;
    }
    // 检测是否为"文件夹模式"：使用文件夹输入或存在 webkitRelativePath
    const isFolderMode = (folderInput && folderInput.files && folderInput.files.length > 0) || Array.from(files).some(f => (f.webkitRelativePath || '').includes('/'));
    // 前端大小预检：若已知服务器限制，自动走分片上传以绕过限制
    const sizes = Array.from(files).map(f => f.size || 0);
    const total = sizes.reduce((s, n) => s + n, 0);
    const overSingle = (serverLimits.uploadMaxBytes && sizes.some(s => s > serverLimits.uploadMaxBytes));
    const overPost = (serverLimits.postMaxBytes && total > serverLimits.postMaxBytes);
    const fd = new FormData();
    fd.append("username", user.username);
    for (const f of files) fd.append("files[]", f);
    try {
      if (btnUpload.dataset.busy === '1') return;
      btnUpload.dataset.busy = '1';
      btnUpload.disabled = true;
      // 文件夹模式：统一走分片上传，并按 webkitRelativePath 还原结构
      if (isFolderMode) {
        showLoading('正在上传文件夹（分片）…');
        const results = await uploadFolderChunked(files, user.username, state.currentDir, (cur, tot) => {
          const pct = Math.floor((cur / tot) * 100);
          showLoading(`正在上传文件夹（${pct}%）…`);
        }, state.skipHiddenUpload);
        const okCount = results.filter(x => x.ok).length;
        const failCount = results.length - okCount;
        if (okCount > 0 && failCount === 0) {
          msg.textContent = `上传完成：成功 ${okCount} 个`;
          msg.className = "message success";
        } else if (okCount > 0 && failCount > 0) {
          msg.textContent = `部分上传成功：成功 ${okCount} 个，失败 ${failCount} 个`;
          msg.className = "message info";
        } else {
          msg.textContent = `上传失败（失败 ${failCount} 个）`;
          msg.className = "message error";
        }
        await fetchList(user.username, state.currentDir);
        return;
      }

      // 若检测到超限，直接走分片上传
      if (overSingle || overPost) {
        showLoading('正在分片上传，请稍候…');
        const results = await uploadFilesChunked(files, user.username, state.currentDir, (cur, tot) => {
          const pct = Math.floor((cur / tot) * 100);
          showLoading(`正在分片上传（${pct}%）…`);
        }, state.skipHiddenUpload);
        const okCount = results.filter(x => x.ok).length;
        const failCount = results.length - okCount;
        if (okCount > 0 && failCount === 0) {
          msg.textContent = `上传完成：成功 ${okCount} 个`;
          msg.className = "message success";
        } else if (okCount > 0 && failCount > 0) {
          msg.textContent = `部分上传成功：成功 ${okCount} 个，失败 ${failCount} 个`;
          msg.className = "message info";
        } else {
          msg.textContent = `上传失败（失败 ${failCount} 个）`;
          msg.className = "message error";
        }
        await fetchList(user.username, state.currentDir);
        return;
      }

      showLoading('正在上传文件，请稍候…');
      const res = await fetch("/api/upload.php", { method: "POST", credentials: "include", body: fd });
      if (res.ok) {
        const data = await res.json();
        const items = Array.isArray(data.items) ? data.items : [];
        // 若服务端携带限制信息，保存以用于后续预检
        if (data && data.limits) {
          serverLimits.uploadMaxBytes = Number(data.limits.upload_max_bytes) || serverLimits.uploadMaxBytes;
          serverLimits.postMaxBytes = Number(data.limits.post_max_bytes) || serverLimits.postMaxBytes;
        }
        const okCount = items.filter(x => x.ok).length;
        const failItems = items.filter(x => !x.ok);
        const overs = failItems.filter(x => /大小限制|超过服务器大小限制|FORM_SIZE|INI_SIZE/.test(String(x.error || '')));
        // 若存在因大小限制失败的文件，自动对这些文件使用分片上传重试
        if (overs.length > 0) {
          const needNames = new Set(overs.map(o => String(o.name || '')));
          const retryFiles = Array.from(files).filter(f => needNames.has(f.name));
          showLoading('检测到大小限制，正在自动分片重试…');
          const chunkResults = await uploadFilesChunked(retryFiles, user.username, state.currentDir, (cur, tot) => {
            const pct = Math.floor((cur / tot) * 100);
            showLoading(`分片重试中（${pct}%）…`);
          });
          const chunkOk = chunkResults.filter(x => x.ok).length;
          const finalOk = okCount + chunkOk;
          const finalFail = (failItems.length - overs.length) + (chunkResults.length - chunkOk);
          if (finalOk > 0 && finalFail === 0) {
            msg.textContent = `上传完成：成功 ${finalOk} 个`;
            msg.className = "message success";
          } else if (finalOk > 0 && finalFail > 0) {
            msg.textContent = `部分上传成功：成功 ${finalOk} 个，失败 ${finalFail} 个`;
            msg.className = "message info";
          } else {
            msg.textContent = `上传失败（失败 ${finalFail} 个）`;
            msg.className = "message error";
          }
        } else {
          if (okCount > 0 && failItems.length === 0) {
            msg.textContent = `上传完成：成功 ${okCount} 个`;
            msg.className = "message success";
          } else if (okCount > 0 && failItems.length > 0) {
            msg.textContent = `部分上传成功：成功 ${okCount} 个，失败 ${failItems.length} 个`;
            msg.className = "message info";
          } else {
            msg.textContent = `上传失败（失败 ${failItems.length} 个）`;
            msg.className = "message error";
          }
        }
        await fetchList(user.username, state.currentDir);
      } else {
        // 常规上传返回 413，自动切换到分片上传
        if (res.status === 413) {
          showLoading('服务器限制触发，正在分片上传…');
          const results = await uploadFilesChunked(files, user.username, state.currentDir, (cur, tot) => {
            const pct = Math.floor((cur / tot) * 100);
            showLoading(`正在分片上传（${pct}%）…`);
          });
          const okCount = results.filter(x => x.ok).length;
          const failCount = results.length - okCount;
          if (okCount > 0 && failCount === 0) {
            msg.textContent = `上传完成：成功 ${okCount} 个`;
            msg.className = "message success";
          } else if (okCount > 0 && failCount > 0) {
            msg.textContent = `部分上传成功：成功 ${okCount} 个，失败 ${failCount} 个`;
            msg.className = "message info";
          } else {
            msg.textContent = `上传失败（失败 ${failCount} 个）`;
            msg.className = "message error";
          }
          await fetchList(user.username, state.currentDir);
        } else {
          msg.textContent = "上传失败";
          msg.className = "message error";
        }
      }
    } catch (e) {
      msg.textContent = "上传异常";
      msg.className = "message error";
    } finally {
      hideLoading();
      btnUpload.disabled = false;
      delete btnUpload.dataset.busy;
    }
  });
}

/**
 * 初始化侧边栏并设置默认面板
 * @param {string} username 纯数字用户名
 * @param {('upload'|'list'|'settings'|'shared')} [initialTarget='list'] 默认激活面板
 */
function initSidebar(username, initialTarget = 'list') {
  const btns = Array.from(document.querySelectorAll('.nav-item'));
  const panels = Array.from(document.querySelectorAll('.panel'));
  const setActive = (target) => {
    btns.forEach(b => b.classList.toggle('active', b.dataset.target === target));
    panels.forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(`${target}-section`);
    if (panel) panel.classList.add('active');
    if (target === 'list') { fetchList(username, state.currentDir); }
    if (target === 'shared') { fetchSharedList(); }
    if (target === 'settings') { loadSettingsPanel(username); }
  };
  const user = getSessionUser();
  btns.forEach(b => {
    const t = String(b.dataset.target || '');
    if (user && user.isGraduation && (t === 'upload' || t === 'list' || t === 'settings' || t === 'shared')) { b.setAttribute('disabled', 'true'); return; }
    if (user && !user.isGraduation && t === 'graduation') { b.setAttribute('disabled', 'true'); return; }
    b.addEventListener('click', () => setActive(t));
  });
  // 默认面板根据设置决定
  setActive(initialTarget);
}

// 在 Edge 等浏览器中确保 DOM 完全就绪后再初始化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { init().catch(e => console.error('init error', e)); });
} else {
  init().catch(e => console.error('init error', e));
}
