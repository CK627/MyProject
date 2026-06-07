/**
 * 教师管理页面 - 班级管理模块
 * 包含：学生列表、添加/编辑/删除学生、导入导出
 * 
 * 依赖: js/index.js, js/teacher-core.js
 */

let cmState = { items: [], filtered: [], page: 1, size: 10, status: 'all', q: '', selected: new Set(), cls: '' };

function initClassManage(adm) {
  cmState.cls = (adm && adm.class) ? String(adm.class) : '';
  bindClassControls();
  refreshRoster();
}

async function refreshRoster() {
  const tbody = document.getElementById('cm-tbody');
  if (!tbody) return;
  const res = await fetch(`/api/class_list.php?class=${encodeURIComponent(cmState.cls)}`, { method: 'GET', credentials: 'include' });
  const data = res.ok ? await res.json() : null;
  cmState.items = (data && data.items) ? data.items : [];
  applyClassFilters();
}

function applyClassFilters() {
  const q = cmState.q.toLowerCase();
  let arr = cmState.items.filter(it => {
    const okText = q === '' || String(it.username).toLowerCase().includes(q) || String(it.name||'').toLowerCase().includes(q);
    const okStatus = cmState.status === 'all' || (cmState.status === 'submitted' && it.submitted) || (cmState.status === 'pending' && !it.submitted);
    return okText && okStatus;
  });
  arr.sort((a,b) => {
    const au = Number(a.username||0);
    const bu = Number(b.username||0);
    if (isNaN(au) && isNaN(bu)) return String(a.username||'').localeCompare(String(b.username||''));
    if (isNaN(au)) return 1;
    if (isNaN(bu)) return -1;
    return au - bu;
  });
  cmState.filtered = arr;
  cmState.page = 1;
  renderClassTable();
}

function renderClassTable() {
  const tbody = document.getElementById('cm-tbody');
  const master = document.getElementById('cm-select-all');
  const info = document.getElementById('cm-page-info');
  if (!tbody) return;
  const start = (cmState.page - 1) * cmState.size;
  const pageItems = cmState.filtered.slice(start, start + cmState.size);
  tbody.innerHTML = '';
  const frag = document.createDocumentFragment();
  pageItems.forEach(it => {
    const tr = document.createElement('tr');
    const u = String(it.username);
    const nm = String(it.name || '').trim();
    const cls = String(it.class || '').trim();
    tr.innerHTML = `<td><input type="checkbox" class="cm-row" data-username="${u}" ${cmState.selected.has(u)?'checked':''} /></td><td>${u}</td><td>${nm || '未设置'}</td><td>${cls || '-'}</td><td><button class="btn-link" data-action="edit" data-username="${u}">编辑</button> <button class="btn-link" data-action="del" data-username="${u}">删除</button></td>`;
    frag.appendChild(tr);
  });
  tbody.appendChild(frag);
  if (master) master.checked = false;
  const total = cmState.filtered.length;
  const pages = Math.max(1, Math.ceil(total / cmState.size));
  if (info) info.textContent = `第 ${cmState.page}/${pages} 页，共 ${total} 条`;
  tbody.querySelectorAll('input.cm-row').forEach(chk => {
    chk.addEventListener('change', () => { const u = String(chk.getAttribute('data-username')||''); if (chk.checked) cmState.selected.add(u); else cmState.selected.delete(u); });
  });
  tbody.querySelectorAll('button[data-action="edit"]').forEach(btn => {
    btn.addEventListener('click', () => { const u = String(btn.getAttribute('data-username')||''); openEditModal(u); });
  });
  tbody.querySelectorAll('button[data-action="del"]').forEach(btn => {
    btn.addEventListener('click', async () => { const u = String(btn.getAttribute('data-username')||''); await deleteOneStudent(u); });
  });
}

function bindClassControls() {
  const master = document.getElementById('cm-select-all');
  const prev = document.getElementById('cm-prev');
  const next = document.getElementById('cm-next');
  const sizeSel = document.getElementById('cm-size');
  const qInput = document.getElementById('cm-search');
  const qBtn = document.getElementById('cm-search-btn');
  const chips = document.querySelectorAll('.chip-btn');
  const btnAdd = document.getElementById('btn-cm-add');
  const btnImport = document.getElementById('btn-cm-import');
  const btnBulkDel = document.getElementById('btn-cm-bulk-del');
  const btnTemplate = document.getElementById('btn-cm-template');
  const fileInput = document.getElementById('cm-file');
  if (master) master.addEventListener('change', () => { const all = !!master.checked; cmState.selected.clear(); document.querySelectorAll('#cm-tbody input.cm-row').forEach(chk => { chk.checked = all; if (all) cmState.selected.add(String(chk.getAttribute('data-username')||'')); }); });
  if (prev) prev.addEventListener('click', () => { cmState.page = Math.max(1, cmState.page - 1); renderClassTable(); });
  if (next) next.addEventListener('click', () => { const total = cmState.filtered.length; const pages = Math.max(1, Math.ceil(total / cmState.size)); cmState.page = Math.min(pages, cmState.page + 1); renderClassTable(); });
  if (sizeSel) sizeSel.addEventListener('change', () => { 
    if (sizeSel.value === 'all') {
      cmState.size = 10000; 
    } else {
      cmState.size = Number(sizeSel.value||10); 
    }
    cmState.page = 1; 
    renderClassTable(); 
  });
  if (qInput) qInput.addEventListener('input', () => { cmState.q = String(qInput.value||''); applyClassFilters(); });
  if (qBtn) qBtn.addEventListener('click', () => { cmState.q = String(qInput && qInput.value || ''); applyClassFilters(); });
  chips.forEach(c => c.addEventListener('click', () => { chips.forEach(x => x.classList.remove('active')); c.classList.add('active'); cmState.status = String(c.getAttribute('data-status')||'all'); applyClassFilters(); }));
  if (btnAdd) btnAdd.addEventListener('click', () => { openAddModal(); });
  if (btnTemplate) btnTemplate.addEventListener('click', () => { location.href = '/api/template_excel.php'; });
  if (btnImport && fileInput) btnImport.addEventListener('click', async () => { const f = fileInput.files && fileInput.files[0]; if (!f) { alert('请选择Excel或CSV文件'); return; } const fd = new FormData(); const admin = getAdmin(); fd.append('adminUsername', (admin && admin.username) ? String(admin.username) : ''); fd.append('file', f); const res = await fetch('/api/class_import.php', { method:'POST', credentials:'include', body: fd }); const ok = res.ok ? await res.json() : null; if (ok && ok.ok) { alert(`导入成功：${ok.ok_count}，失败：${ok.fail_count}`); fileInput.value=''; refreshRoster(); } else { alert((ok && ok.error)||'导入失败'); } });
  if (btnBulkDel) btnBulkDel.addEventListener('click', async () => { const list = Array.from(cmState.selected); if (list.length === 0) { alert('请先选择要删除的学生'); return; } const res = await fetch('/api/class_bulk_delete.php', { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ usernames: list }) }); const ok = res.ok ? await res.json() : null; if (ok && ok.ok) { alert(`删除成功：${ok.ok_count}，失败：${ok.fail_count}`); refreshRoster(); } else { alert('删除失败'); } });
}

async function deleteOneStudent(u) {
  const res = await fetch('/api/class_delete.php', { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ username: u }) });
  const ok = res.ok ? await res.json() : null;
  if (ok && ok.ok) { refreshRoster(); } else { alert('删除失败'); }
}

// ===== 编辑模态框 =====

let editState = { username: '' };

function initEditModal() {
  const cancel = document.getElementById('em-cancel');
  const save = document.getElementById('em-save');
  if (cancel) cancel.addEventListener('click', closeEditModal);
  if (save) save.addEventListener('click', saveEditModal);
}

function openEditModal(u) {
  editState.username = String(u);
  const overlay = document.getElementById('edit-modal');
  const uEl = document.getElementById('em-username');
  const nEl = document.getElementById('em-name');
  const cEl = document.getElementById('em-class');
  if (uEl) uEl.value = editState.username;
  if (nEl) nEl.value = '';
  if (cEl) cEl.value = '';
  if (overlay) overlay.classList.add('active');
  fetch(`/api/class_get.php?username=${encodeURIComponent(editState.username)}`, { method:'GET', credentials:'include' })
    .then(res => res.ok ? res.json() : null)
    .then(data => { if (!data || !data.ok) return; if (nEl) nEl.value = String(data.name||''); if (cEl) cEl.value = String(data.class||''); })
    .catch(()=>{});
}

function closeEditModal() {
  const overlay = document.getElementById('edit-modal');
  if (overlay) overlay.classList.remove('active');
}

async function saveEditModal() {
  const uEl = document.getElementById('em-username');
  const nEl = document.getElementById('em-name');
  const cEl = document.getElementById('em-class');
  const admin = getAdmin();
  const payload = {
    adminUsername: (admin && admin.username) ? String(admin.username) : '',
    username: String(uEl && uEl.value || ''),
    name: String(nEl && nEl.value || ''),
    class: String(cEl && cEl.value || '')
  };
  const res = await fetch('/api/class_update.php', { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const ok = res.ok ? await res.json() : null;
  if (ok && ok.ok) { closeEditModal(); refreshRoster(); } else { alert((ok && ok.error)||'保存失败'); }
}

// ===== 添加模态框 =====

function initAddModal() {
  const cancel = document.getElementById('am-cancel');
  const save = document.getElementById('am-save');
  if (cancel) cancel.addEventListener('click', closeAddModal);
  if (save) save.addEventListener('click', saveAddModal);
}

function openAddModal() {
  const overlay = document.getElementById('add-modal');
  const uEl = document.getElementById('am-username');
  const nEl = document.getElementById('am-name');
  if (uEl) uEl.value = '';
  if (nEl) nEl.value = '';
  if (overlay) overlay.classList.add('active');
}

function closeAddModal() {
  const overlay = document.getElementById('add-modal');
  if (overlay) overlay.classList.remove('active');
}

async function saveAddModal() {
  const uEl = document.getElementById('am-username');
  const nEl = document.getElementById('am-name');
  const u = String(uEl && uEl.value || '').trim();
  const n = String(nEl && nEl.value || '').trim();
  if (!/^\d+$/.test(u)) { alert('学号需为纯数字'); return; }
  const admin = (getAdmin() && getAdmin().username) ? String(getAdmin().username) : '';
  const payload = { adminUsername: admin, username: u, name: n };
  const res = await fetch('/api/class_add.php', { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const ok = res.ok ? await res.json() : null;
  if (ok && ok.ok) { closeAddModal(); refreshRoster(); } else { alert((ok && ok.error)||'添加失败'); }
}
