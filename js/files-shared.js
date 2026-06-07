/**
 * 文件页面 - 共享列表模块
 * 包含：共享文件列表渲染、子目录浏览
 * 
 * 依赖: js/index.js
 */

/**
 * 共享文件列表的状态
 */
const sharedState = { currentDir: '', targetUser: '' };

/**
 * 拉取并渲染共享文件列表
 * 支持浏览子目录（需要指定 targetUser）
 */
async function fetchSharedList(targetUser = '', dir = '') {
  const tbody = document.getElementById("shared-tbody");
  const msgEl = document.getElementById("shared-msg");
  if (!tbody || !msgEl) return;
  
  // 更新状态
  sharedState.targetUser = targetUser;
  sharedState.currentDir = dir;
  
  tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">加载中…</td></tr>';
  msgEl.textContent = '';
  
  try {
    // 如果是根目录浏览模式（无 targetUser），用 GET；如果是子目录浏览，用 POST 传参
    let url = "/api/list_shared.php";
    let options = { method: "GET" };
    
    if (targetUser) {
      options = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ target_user: targetUser, dir: dir })
      };
    } else {
      options = { method: "GET", credentials: "include" };
    }

    const res = await fetch(url, options);
    if (!res.ok) throw new Error('网络错误');
    const data = await res.json();
    const items = Array.isArray(data.items) ? data.items : [];
    
    tbody.innerHTML = "";
    
    // 如果在子目录，添加"返回上一级"行
    if (targetUser && dir) {
      const trBack = document.createElement('tr');
      trBack.className = 'folder-row parent-row';
      trBack.innerHTML = `
        <td><span class="icon-folder">📁</span> ..</td>
        <td>-</td>
        <td>
          <div class="actions">
            <button class="btn-link" onclick="handleSharedBack()">返回</button>
          </div>
        </td>`;
      tbody.appendChild(trBack);
      
      // 双击返回
      trBack.addEventListener('dblclick', handleSharedBack);
    }
    
    if (items.length === 0 && !dir) {
      msgEl.textContent = "暂无共享文件";
      return;
    }
    
    const frag = document.createDocumentFragment();
    items.forEach(it => {
      const tr = document.createElement('tr');
      if (it.type === 'folder') {
        tr.className = 'folder-row shared-folder';
        // 存储点击所需的元数据
        tr.dataset.user = it.username;
        // 注意：it.path 在根列表时是顶级目录名，在子目录列表时是相对路径
        // 我们统一使用 it.path (后端已处理好相对路径)
        tr.dataset.path = it.path || it.name; 
        
        tr.innerHTML = `
          <td><span class="icon-folder">📁</span> ${escapeHtml(it.name)}</td>
          <td>${escapeHtml(it.sharer_name)}</td>
          <td>
            <div class="actions">
              <button class="btn-link" onclick="fetchSharedList('${it.username}', '${escapeAttr(it.path || it.name)}')">打开</button>
              <button class="btn-link" onclick="window.open('/api/download_folder.php?username=${encodeURIComponent(it.username)}&name=${encodeURIComponent(it.path || it.name)}&dir=${encodeURIComponent(dir)}', '_blank')">打包下载</button>
            </div>
          </td>`;
          
        // 双击进入文件夹
        tr.addEventListener('dblclick', () => {
           fetchSharedList(it.username, it.path || it.name);
        });
        
      } else {
        tr.className = 'file-row shared-file';
        tr.innerHTML = `
          <td>${escapeHtml(it.name)}</td>
          <td>${escapeHtml(it.sharer_name)}</td>
          <td>
            <div class="actions">
              <button class="btn-link" onclick="window.open('/api/download.php?username=${encodeURIComponent(it.username)}&id=${encodeURIComponent(it.id)}', '_blank')">下载</button>
            </div>
          </td>`;
          
        // 双击下载文件
        tr.addEventListener('dblclick', () => {
           window.open(`/api/download.php?username=${encodeURIComponent(it.username)}&id=${encodeURIComponent(it.id)}`, '_blank');
        });
      }
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);
  } catch (e) {
    msgEl.textContent = "加载失败";
    tbody.innerHTML = "";
    console.error(e);
  }
}

/** 处理共享列表返回逻辑 */
function handleSharedBack() {
  if (!sharedState.targetUser) return;
  
  if (!sharedState.currentDir) {
    // 已经在该用户的根目录，返回到所有用户列表
    fetchSharedList('', '');
  } else {
    // 在子目录，返回上一级
    const parts = sharedState.currentDir.split('/');
    parts.pop();
    const parentDir = parts.join('/');
    if (parentDir === '') {
       // 返回到该用户的根目录
       fetchSharedList(sharedState.targetUser, '');
    } else {
       fetchSharedList(sharedState.targetUser, parentDir);
    }
  }
}
