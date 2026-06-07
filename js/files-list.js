/**
 * 文件页面 - 列表模块
 * 包含：文件列表渲染、文件夹渲染、操作绑定
 * 
 * 依赖: js/index.js, js/files-core.js
 */

/**
 * 拉取并渲染文件列表
 * @param {string} username
 */
async function fetchList(username, dir = '') {
  const tbody = document.getElementById("file-tbody");
  const msgEl = document.getElementById("list-msg");
  if (!tbody || !msgEl) {
    console.error('列表容器未找到：#file-tbody 或 #list-msg 缺失');
    return;
  }
  const seq = ++listRequestSeq;
  try {
    const res = await fetch("/api/list.php", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ username, dir })
    });
    if (!res.ok) {
      msgEl.textContent = '列表加载失败，请稍后重试';
      msgEl.className = 'message error';
      return;
    }
    const data = await res.json();
    const items = Array.isArray(data.items) ? data.items : [];
    const folders = Array.isArray(data.folders) ? data.folders : [];
    // 若有新的列表刷新请求发出，丢弃当前旧请求的结果，避免重复渲染
    if (seq !== listRequestSeq) return;
    msgEl.textContent = (items.length === 0 && folders.length === 0) ? '暂无文件' : '';
    // 清空并渲染最新结果
    tbody.innerHTML = "";
    const frag = document.createDocumentFragment();
    // 文件夹行
    renderFolderRows(folders).forEach(el => frag.appendChild(el));
    // 文件行
    renderFileRows(items).forEach(el => frag.appendChild(el));
    tbody.appendChild(frag);
    try { bindActions(username); } catch (err) {
      console.error('绑定交互时发生错误：', err);
      msgEl.textContent = '列表渲染完成，但交互绑定失败';
      msgEl.className = 'message error';
    }
    // 更新当前位置
    document.getElementById('current-dir').textContent = `当前位置：/${state.currentDir || ''}`;
  } catch (e) {
    msgEl.textContent = '列表加载异常：网络或服务不可用';
    msgEl.className = 'message error';
    console.error('fetchList 异常：', e);
  }
}

/** 渲染文件夹行为节点数组 */
function renderFolderRows(folders) {
  const rows = [];
  // 非根目录时，加入".."上级目录条目
  if (state.currentDir) {
    const trParent = document.createElement('tr');
    trParent.className = 'folder-row parent-row';
    trParent.innerHTML = `
      <td></td>
      <td>📁 ..</td>
      <td>-</td>
      <td>
        <div class="actions">
          <button class="btn-link" data-action="open-parent">打开</button>
        </div>
      </td>`;
    rows.push(trParent);
  }
  folders.forEach(f => {
    const rawName = typeof f === 'string' ? f : ((f && f.name) ?? '');
    const name = String(rawName);
    if (!state.showHiddenList && name.startsWith('.')) return;
    const created = typeof f === 'string' ? '-' : (f && f.created_at) || '-';
      const tr = document.createElement('tr');
      // 共享状态显示
      let shareText = '共享';
      let isPublic = '0';
      // f 可能是对象也可能是字符串（兼容旧API），新API返回对象且含 public_state
      const pState = (f && typeof f === 'object') ? (f.public_state ?? 0) : 0;
      if (pState === 1) { shareText = '取消共享'; isPublic = '1'; }
      else if (pState === 2) { shareText = '全部共享'; isPublic = '0'; }
      else { shareText = '共享'; isPublic = '0'; }

      tr.className = 'folder-row';
      tr.setAttribute('data-folder', name);
      tr.innerHTML = `
        <td><input type="checkbox" class="row-check" data-type="folder" data-folder="${escapeAttr(name)}" /></td>
        <td>
          <span class="icon-folder">📁</span>
          <a href="#" class="folder-link" data-name="${escapeHtml(f.name)}">${escapeHtml(f.name)}</a>
        </td>
        <td>${escapeHtml(created)}</td>
        <td>
          <div class="actions">
            <button class="btn-link" data-action="open-folder" data-folder="${escapeAttr(name)}">打开</button>
            <button class="btn-link" data-action="rename-folder" data-folder="${escapeAttr(name)}">重命名</button>
            <button class="btn-link" data-action="download-folder" data-folder="${escapeAttr(name)}">下载</button>
            <button class="btn-link" data-action="share-folder" data-folder="${escapeAttr(name)}" data-public="${isPublic}">${shareText}</button>
            <button class="btn-link" data-action="delete-folder" data-folder="${escapeAttr(name)}">删除</button>
          </div>
        </td>`;
      rows.push(tr);
  });
  return rows;
}

/** 渲染文件行为节点数组 */
function renderFileRows(items) {
  const rows = [];
  items.forEach(it => {
    const tr = document.createElement('tr');
    // 标记为可双击下载的文件行
    tr.className = 'file-row';
    tr.setAttribute('data-id', it.id);
    const name = getFilename(it.file_path);
    if (!state.showHiddenList && isHiddenPath(it.file_path || name)) return;
    tr.innerHTML = `
      <td><input type=\"checkbox\" class=\"row-check\" data-type=\"file\" data-id=\"${it.id}\" /></td>
      <td>${escapeHtml(name)}</td>
      <td>${it.upload_at || '-'}</td>
      <td>
        <div class="actions">
          <button class="btn-link" data-action="download" data-id="${it.id}">下载</button>
          <button class="btn-link" data-action="rename" data-id="${it.id}" data-name="${escapeAttr(name)}">重命名</button>
          <button class="btn-link" data-action="share" data-id="${it.id}" data-public="${it.is_public ? '1' : '0'}">${it.is_public ? '取消共享' : '共享'}</button>
          <button class="btn-link" data-action="move" data-id="${it.id}">移动</button>
          <button class="btn-link" data-action="delete" data-id="${it.id}">删除</button>
        </div>
      </td>`;
    rows.push(tr);
  });
  return rows;
}

/** 判断当前是否所有行都被选中 */
function isAllSelected() {
  const checks = document.querySelectorAll('#file-tbody input.row-check');
  if (!checks.length) return false;
  for (const c of checks) { if (!c.checked) return false; }
  return true;
}

/** 绑定下载与删除动作 */
function bindActions(username) {
  const tbody = document.getElementById('file-tbody');
  // 初始化复选框与全选
  const master = document.getElementById('select-all');
  tbody.querySelectorAll('input.row-check').forEach(chk => {
    const type = chk.getAttribute('data-type');
    if (type === 'file') {
      const id = Number(chk.getAttribute('data-id'));
      chk.checked = selectedIds.has(id);
      chk.addEventListener('change', () => {
        if (chk.checked) selectedIds.add(id); else selectedIds.delete(id);
        if (master) master.checked = isAllSelected();
      });
    } else if (type === 'folder') {
      const folder = String(chk.getAttribute('data-folder') || '');
      chk.checked = selectedFolders.has(folder);
      chk.addEventListener('change', () => {
        if (chk.checked) selectedFolders.add(folder); else selectedFolders.delete(folder);
        if (master) master.checked = isAllSelected();
      });
    }
  });
  if (master) {
    master.checked = isAllSelected();
    master.addEventListener('change', () => {
      const all = master.checked;
      selectedIds.clear();
      selectedFolders.clear();
      tbody.querySelectorAll('input.row-check').forEach(chk => {
        chk.checked = all;
        if (!all) return;
        const type = chk.getAttribute('data-type');
        if (type === 'file') selectedIds.add(Number(chk.getAttribute('data-id')));
        else if (type === 'folder') selectedFolders.add(String(chk.getAttribute('data-folder') || ''));
      });
    });
  }
  tbody.querySelectorAll('button[data-action]').forEach(btn => {
    const id = btn.getAttribute('data-id');
    const action = btn.getAttribute('data-action');
    if (action === 'download') {
      btn.addEventListener('click', () => {
        const url = `/api/download.php?username=${encodeURIComponent(username)}&id=${encodeURIComponent(id)}`;
        window.open(url, '_blank');
      });
    } else if (action === 'delete') {
      btn.addEventListener('click', async () => {
        if (!confirm('确认删除该文件吗？')) return;
        if (btn.dataset.busy === '1') return;
        btn.dataset.busy = '1';
        btn.disabled = true;
        showLoading('正在删除文件，请稍候…');
        try {
          const res = await fetch('/api/delete.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, id: Number(id) })
          });
          const ok = res.ok ? await res.json() : null;
          if (ok && ok.ok) {
            await fetchList(username, state.currentDir);
          } else {
            alert((ok && ok.error) || '删除失败');
          }
        } catch (e) {
          alert('删除失败：网络或服务器错误');
        } finally {
          hideLoading();
          btn.disabled = false;
          delete btn.dataset.busy;
        }
      });
    } else if (action === 'open-folder') {
      btn.addEventListener('click', async () => {
        const folder = btn.getAttribute('data-folder');
        if (btn.dataset.busy === '1') return;
        btn.dataset.busy = '1';
        btn.disabled = true;
        showLoading('正在加载文件，请稍候…');
        state.currentDir = state.currentDir ? `${state.currentDir}/${folder}` : folder;
        try {
          await fetchList(username, state.currentDir);
        } finally {
          hideLoading();
          btn.disabled = false;
          delete btn.dataset.busy;
        }
      });
    } else if (action === 'open-parent') {
      btn.addEventListener('click', async () => {
        if (!state.currentDir) return;
        if (btn.dataset.busy === '1') return;
        btn.dataset.busy = '1';
        btn.disabled = true;
        showLoading('正在加载列表，请稍候…');
        const parts = state.currentDir.split('/');
        parts.pop();
        state.currentDir = parts.join('/');
        try {
          await fetchList(username, state.currentDir);
        } finally {
          hideLoading();
          btn.disabled = false;
          delete btn.dataset.busy;
        }
      });
    } else if (action === 'download-folder') {
      btn.addEventListener('click', () => {
        const folder = btn.getAttribute('data-folder');
        if (!folder) return;
        const url = `/api/download_folder.php?username=${encodeURIComponent(username)}&dir=${encodeURIComponent(state.currentDir || '')}&name=${encodeURIComponent(folder)}`;
        window.open(url, '_blank');
      });
    } else if (action === 'share-folder') {
      btn.addEventListener('click', async () => {
        if (btn.dataset.busy === '1') return;
        btn.dataset.busy = '1';
        btn.disabled = true;
        const folder = btn.getAttribute('data-folder');
        const isPublic = btn.getAttribute('data-public') === '1';
        const label = isPublic ? '取消共享' : '共享';
        // 目标目录相对路径
        const targetPath = state.currentDir ? `${state.currentDir}/${folder}` : folder;
        
        showLoading(`正在${label}文件夹…`);
        try {
          const res = await fetch('/api/toggle_public.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, type: 'folder', path: targetPath })
          });
          const ok = res.ok ? await res.json() : null;
          if (ok && ok.ok) {
            await fetchList(username, state.currentDir);
            showTransientMessage(document.getElementById('list-section'), `${label}成功`, 'success');
          } else {
            alert((ok && ok.error) || `${label}失败`);
          }
        } catch (e) {
          alert('操作失败：网络或服务器错误');
        } finally {
          hideLoading();
          btn.disabled = false;
          delete btn.dataset.busy;
        }
      });
    } else if (action === 'delete-folder') {
      btn.addEventListener('click', async () => {
        const folder = btn.getAttribute('data-folder');
        const targetDir = state.currentDir ? `${state.currentDir}/${folder}` : folder;
        try {
          // 查询该目录内容，决定是否需要确认提示
          const res = await fetch('/api/list.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, dir: targetDir })
          });
          const data = res.ok ? await res.json() : { items: [], folders: [] };
          const hasContent = (Array.isArray(data.items) && data.items.length > 0) || (Array.isArray(data.folders) && data.folders.length > 0);
          const msg = hasContent
            ? '该文件夹不为空，删除将同时删除其中所有文件和子文件夹，是否继续？'
            : '确认删除该文件夹吗？';
          const ok = confirm(msg);
          if (!ok) return;
          if (btn.dataset.busy === '1') return; // 防抖，避免重复触发
          btn.dataset.busy = '1';
          btn.disabled = true;
          showLoading('正在删除文件夹，请稍候…');
          const delRes = await fetch('/api/delete_folder.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, dir: state.currentDir || '', name: folder })
          });
          const delData = delRes.ok ? await delRes.json() : null;
          if (!delRes.ok || !delData || !delData.ok) {
            alert((delData && delData.error) || '删除失败');
            return;
          }
          await fetchList(username, state.currentDir);
        } catch (e) {
          alert('删除失败：网络或服务器错误');
        } finally {
          hideLoading();
          btn.disabled = false;
          delete btn.dataset.busy;
        }
      });
    } else if (action === 'share') {
      btn.addEventListener('click', async () => {
        if (btn.dataset.busy === '1') return;
        btn.dataset.busy = '1';
        btn.disabled = true;
        const isPublic = btn.getAttribute('data-public') === '1';
        const label = isPublic ? '取消共享' : '共享';
        showLoading(`正在${label}…`);
        try {
          const res = await fetch('/api/toggle_public.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, id: Number(id) })
          });
          const ok = res.ok ? await res.json() : null;
          if (ok && ok.ok) {
            await fetchList(username, state.currentDir);
            showTransientMessage(document.getElementById('list-section'), `${label}成功`, 'success');
          } else {
            alert((ok && ok.error) || `${label}失败`);
          }
        } catch (e) {
          alert('操作失败：网络或服务器错误');
        } finally {
          hideLoading();
          btn.disabled = false;
          delete btn.dataset.busy;
        }
      });
    } else if (action === 'move') {
      btn.addEventListener('click', async () => {
        let to = prompt(`输入目标目录路径（相对根，例如: Docs 或 Docs/2025）。\n输入".."表示移动到上一级目录。`, state.currentDir || '');
        if (to === null) return;
        const parent = state.currentDir.split('/').slice(0, -1).join('/') || '';
        to = String(to).replace(/\\/g, '/').trim();
        if (to === '..') {
          to = parent;
        } else {
          to = to.replace(/^\/+|\/+$/g, '');
        }
        if ((to || '') === (state.currentDir || '')) {
          alert('已在目标目录，无需移动');
          return;
        }
        try {
          if (btn.dataset.busy === '1') return;
          btn.dataset.busy = '1';
          btn.disabled = true;
          showLoading('正在移动文件，请稍候…');
          const res = await fetch('/api/move.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, id: Number(id), to })
          });
          const ok = res.ok ? await res.json() : null;
          if (ok && ok.ok) {
            await fetchList(username, state.currentDir);
          } else {
            alert((ok && ok.error) || '移动失败');
          }
        } catch (e) {
          alert('移动异常');
        } finally {
          hideLoading();
          btn.disabled = false;
          delete btn.dataset.busy;
        }
      });
    } else if (action === 'rename') {
      // 重命名文件
      btn.addEventListener('click', async () => {
        const oldName = btn.getAttribute('data-name') || '';
        // 提取后缀名
        const extIndex = oldName.lastIndexOf('.');
        const ext = extIndex > 0 ? oldName.slice(extIndex) : '';
        const baseName = extIndex > 0 ? oldName.slice(0, extIndex) : oldName;
        
        const newBaseName = await showPrompt({
          title: '重命名文件',
          message: ext ? `请输入新文件名（后缀 ${ext} 不可更改）：` : '请输入新文件名：',
          defaultValue: baseName,
          placeholder: '文件名',
          confirmText: '确认',
          cancelText: '取消',
          validator: (val) => {
            if (!val) return '文件名不能为空';
            if (val === baseName) return '新名称与原名称相同';
            if (val.includes('/') || val.includes('\\')) return '文件名不能包含路径分隔符';
            if (val.includes('.')) return '文件名不能包含小数点';
            return null;
          }
        });
        if (newBaseName === null) return;
        
        const newName = newBaseName + ext;
        if (btn.dataset.busy === '1') return;
        btn.dataset.busy = '1';
        btn.disabled = true;
        showLoading('正在重命名文件…');
        try {
          const res = await fetch('/api/rename.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, id: Number(id), newName })
          });
          const data = res.ok ? await res.json() : null;
          if (data && data.ok) {
            await fetchList(username, state.currentDir);
            showTransientMessage(document.getElementById('list-section'), '重命名成功', 'success');
          } else {
            alert((data && data.error) || '重命名失败');
          }
        } catch (e) {
          alert('重命名失败：网络或服务器错误');
        } finally {
          hideLoading();
          btn.disabled = false;
          delete btn.dataset.busy;
        }
      });
    } else if (action === 'rename-folder') {
      // 重命名文件夹
      btn.addEventListener('click', async () => {
        const oldName = btn.getAttribute('data-folder') || '';
        const newName = await showPrompt({
          title: '重命名文件夹',
          message: '请输入新文件夹名：',
          defaultValue: oldName,
          placeholder: '文件夹名',
          confirmText: '确认',
          cancelText: '取消',
          validator: (val) => {
            if (!val) return '文件夹名不能为空';
            if (val === oldName) return '新名称与原名称相同';
            if (val.includes('/') || val.includes('\\')) return '文件夹名不能包含路径分隔符';
            return null;
          }
        });
        if (newName === null) return;
        if (btn.dataset.busy === '1') return;
        btn.dataset.busy = '1';
        btn.disabled = true;
        showLoading('正在重命名文件夹…');
        try {
          const res = await fetch('/api/rename_folder.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, dir: state.currentDir || '', name: oldName, newName })
          });
          const data = res.ok ? await res.json() : null;
          if (data && data.ok) {
            await fetchList(username, state.currentDir);
            showTransientMessage(document.getElementById('list-section'), '重命名成功', 'success');
          } else {
            alert((data && data.error) || '重命名失败');
          }
        } catch (e) {
          alert('重命名失败：网络或服务器错误');
        } finally {
          hideLoading();
          btn.disabled = false;
          delete btn.dataset.busy;
        }
      });
    }
  });
  // 文件夹行支持双击打开
  tbody.querySelectorAll('tr.folder-row').forEach(tr => {
    tr.addEventListener('dblclick', async () => {
      const isParent = tr.classList.contains('parent-row');
      if (isParent && !state.currentDir) return;
      const folder = tr.getAttribute('data-folder');
      if (!isParent && !folder) return;
      if (tr.dataset.busy === '1') return;
      tr.dataset.busy = '1';
      showLoading('正在加载文件，请稍候…');
      if (isParent) {
        const parts = state.currentDir.split('/');
        parts.pop();
        state.currentDir = parts.join('/');
      } else {
        state.currentDir = state.currentDir ? `${state.currentDir}/${folder}` : folder;
      }
      try {
        await fetchList(username, state.currentDir);
      } finally {
        hideLoading();
        delete tr.dataset.busy;
      }
    });
  });
  // 文件行支持双击下载
  tbody.querySelectorAll('tr.file-row').forEach(tr => {
    tr.addEventListener('dblclick', () => {
      const id = tr.getAttribute('data-id');
      if (!id) return;
      const url = `/api/download.php?username=${encodeURIComponent(username)}&id=${encodeURIComponent(id)}`;
      window.open(url, '_blank');
    });
  });

  // 批量删除
  const btnBulkDel = document.getElementById('btn-bulk-delete');
  if (btnBulkDel) {
    if (btnBulkDel.dataset.bound !== '1') {
      btnBulkDel.dataset.bound = '1';
      btnBulkDel.addEventListener('click', async () => {
        const ids = Array.from(selectedIds);
        const folders = Array.from(selectedFolders);
        if (ids.length === 0 && folders.length === 0) { alert('请先选择要删除的文件或文件夹'); return; }
        if (!confirm(`确认删除选中的 ${ids.length} 个文件 和 ${folders.length} 个文件夹吗？`)) return;
        if (btnBulkDel.dataset.busy === '1') return;
        btnBulkDel.dataset.busy = '1'; btnBulkDel.disabled = true; showLoading('正在批量删除…');
        try {
          let ok = 0, fail = 0;
          for (const id of ids) {
            const res = await fetch('/api/delete.php', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({ username, id: Number(id) })
            });
            const data = res.ok ? await res.json() : null;
            if (res.ok && data && data.ok) ok++; else fail++;
          }
          for (const name of folders) {
            const res = await fetch('/api/delete_folder.php', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({ username, dir: state.currentDir || '', name })
            });
            const data = res.ok ? await res.json() : null;
            if (res.ok && data && data.ok) ok++; else fail++;
          }
          selectedIds.clear();
          selectedFolders.clear();
          await fetchList(username, state.currentDir);
          alert(fail === 0 ? `删除成功：${ok} 个` : `部分删除成功：成功 ${ok} 个，失败 ${fail} 个`);
        } catch (e) {
          alert('批量删除异常');
        } finally { hideLoading(); btnBulkDel.disabled = false; delete btnBulkDel.dataset.busy; }
      });
    }
  }

  // 批量移动
  const btnBulkMove = document.getElementById('btn-bulk-move');
  if (btnBulkMove) {
    if (btnBulkMove.dataset.bound !== '1') {
      btnBulkMove.dataset.bound = '1';
      btnBulkMove.addEventListener('click', async () => {
        const ids = Array.from(selectedIds);
        const folders = Array.from(selectedFolders);
        if (ids.length === 0 && folders.length === 0) { alert('请先选择要移动的文件或文件夹'); return; }
        let to = prompt(`输入目标目录路径（相对根，例如: Docs 或 Docs/2025）。\n输入".."表示移动到上一级目录。`, state.currentDir || '');
        if (to === null) return;
        const parent = state.currentDir.split('/').slice(0, -1).join('/') || '';
        to = String(to).replace(/\\/g, '/').trim();
        if (to === '..') to = parent; else to = to.replace(/^\/+|\/+$/g, '');
        if ((to || '') === (state.currentDir || '')) { alert('已在目标目录，无需移动'); return; }
        if (btnBulkMove.dataset.busy === '1') return;
        btnBulkMove.dataset.busy = '1'; btnBulkMove.disabled = true; showLoading('正在批量移动…');
        try {
          let ok = 0, fail = 0;
          for (const id of ids) {
            const res = await fetch('/api/move.php', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({ username, id: Number(id), to })
            });
            const data = res.ok ? await res.json() : null;
            if (res.ok && data && data.ok) ok++; else fail++;
          }
          for (const name of folders) {
            const res = await fetch('/api/move_folder.php', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({ username, dir: state.currentDir || '', name, to })
            });
            const data = res.ok ? await res.json() : null;
            if (res.ok && data && data.ok) ok++; else fail++;
          }
          selectedIds.clear();
          selectedFolders.clear();
          await fetchList(username, state.currentDir);
          alert(fail === 0 ? `移动成功：${ok} 个` : `部分移动成功：成功 ${ok} 个，失败 ${fail} 个`);
        } catch (e) {
          alert('批量移动异常');
        } finally { hideLoading(); btnBulkMove.disabled = false; delete btnBulkMove.dataset.busy; }
      });
    }
  }
}
