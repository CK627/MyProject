/**
 * 教师管理页面 - 文件统计模块
 * 包含：提交状态统计、下载/打回操作、导出功能
 * 
 * 依赖: js/index.js, js/teacher-core.js
 */

let fsState = { cls: '', items: [], q: '', status: 'all', selected: new Set(), view: 'thesis', reviewStatus: 'all' };

function getProjectName(key) {
    if (window.FILE_TYPE_NAMES && window.FILE_TYPE_NAMES[key]) {
        return window.FILE_TYPE_NAMES[key];
    }
    return key;
}

function initFileStat(adm) {
  fsState.cls = (adm && adm.class) ? String(adm.class) : '';
  if (!fsState.view) {
      if (globalProjects && globalProjects.length > 0) {
          fsState.view = globalProjects[0].type_key;
      } else {
          fsState.view = 'thesis';
      }
  }
  bindFileStatControls();
  refreshFileStat();

  // Start auto-refresh by default
  if (fsState.timer) clearInterval(fsState.timer);
  fsState.timer = setInterval(refreshFileStat, 5000);
}

function bindFileStatControls() {
  const qInput = document.getElementById('fs-search');
  const qBtn = document.getElementById('fs-search-btn');
  const master = document.getElementById('fs-select-all');
  const statusSel = document.getElementById('fs-status');
  const reviewStatusSel = document.getElementById('fs-review-status');
  const exportBtn = document.getElementById('fs-export');
  const batchPassBtn = document.getElementById('fs-batch-pass');

  if (qInput) qInput.addEventListener('input', () => { fsState.q = String(qInput.value||''); renderFileStatTable(); });
  if (qBtn) qBtn.addEventListener('click', () => { fsState.q = String(qInput && qInput.value || ''); renderFileStatTable(); });
  if (statusSel) statusSel.addEventListener('change', () => { fsState.status = String(statusSel.value||'all'); renderFileStatTable(); });
  if (reviewStatusSel) reviewStatusSel.addEventListener('change', () => { 
      fsState.reviewStatus = String(reviewStatusSel.value||'all'); 
      refreshFileStat(); // Need to fetch from backend for review filter
  });

  if (master) master.addEventListener('change', () => {
    const all = !!master.checked;
    fsState.selected.clear();
    document.querySelectorAll('#fs-tbody input.fs-row').forEach(chk => {
      chk.checked = all;
      if (all) fsState.selected.add(String(chk.getAttribute('data-username')||''));
    });
    updateBatchBtn();
  });
  if (exportBtn) exportBtn.addEventListener('click', exportSelectedFileStat);
  if (batchPassBtn) batchPassBtn.addEventListener('click', handleBatchPass);

  // Intercept review link clicks to save list state
  const tbody = document.getElementById('fs-tbody');
  if (tbody) {
      tbody.addEventListener('click', (e) => {
          const link = e.target.closest('a.btn-link.primary');
          if (link) {
              const currentView = fsState.view;
              // We need the latest filtered items. 
              // Since fsState.filteredItems is updated in renderFileStatTable, we use it.
              if (fsState.filteredItems) {
                  const reviewList = fsState.filteredItems.map(it => ({
                      username: String(it.username),
                      name: String(it.name),
                      isSubmitted: !!it[currentView + 'Submitted'],
                      reviewResult: it[currentView + 'ReviewResult'] || '未批阅'
                  }));
                  localStorage.setItem('reviewList', JSON.stringify(reviewList));
                  localStorage.setItem('reviewProject', currentView);
              }
          }
      });
  }

  const sub = document.getElementById('filestat-subnav');
  if (sub && sub.dataset.bound !== '1') {
    sub.dataset.bound = '1';
    sub.querySelectorAll('.sub-nav-item').forEach(btn => {
      btn.addEventListener('click', () => {
        sub.querySelectorAll('.sub-nav-item').forEach(x => x.classList.remove('active'));
        btn.classList.add('active');
        fsState.view = String(btn.getAttribute('data-sub')||'thesis');
        updateSectionTitle();
        refreshFileStat(); 
      });
    });
  }
}

function updateSectionTitle() {
    const el = document.getElementById('fs-current-project');
    if (el) {
        el.textContent = '- ' + getProjectName(fsState.view);
    }
}

async function refreshFileStat() {
  const section = document.getElementById('filestat-section');
  if (!section || !section.classList.contains('active')) return;

  updateSectionTitle();
  const url = `/api/filestat_list.php?class=${encodeURIComponent(fsState.cls)}&type=${encodeURIComponent(fsState.view)}&reviewResult=${encodeURIComponent(fsState.reviewStatus)}`;
  const res = await fetch(url, { method:'GET', credentials:'include' });
  const data = res.ok ? await res.json() : null;
  fsState.items = (data && data.items) ? data.items : [];
  renderFileStatTable();
}

function renderFileStatTable() {
  const tbody = document.getElementById('fs-tbody');
  const master = document.getElementById('fs-select-all');
  if (!tbody) return;
  const q = fsState.q.toLowerCase();
  
  // Dynamic Property Keys based on current view
  const currentView = fsState.view;
  const keySubmitted = currentView + 'Submitted';
  const keyDlCount = currentView + 'DownloadCount';
  const keyDlTime = currentView + 'LatestDownloadTime';
  const keyFinalTime = currentView + 'FinalSubmissionTime';
  const keyReview = currentView + 'ReviewResult';

  const arr = fsState.items.filter(it => {
    const u = String(it.username||'');
    const n = String(it.name||'');
    const okText = q === '' || u.toLowerCase().includes(q) || n.toLowerCase().includes(q);
    
    const isSubmitted = !!it[keySubmitted];
    
    let okStatus = true;
    if (fsState.status === 'submitted') {
      okStatus = isSubmitted;
    } else if (fsState.status === 'pending') {
      okStatus = !isSubmitted;
    } else {
      okStatus = true;
    }
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

  fsState.filteredItems = arr;

  tbody.innerHTML = '';
  const frag = document.createDocumentFragment();
  arr.forEach(it => {
    const tr = document.createElement('tr');
    
    const isSubmitted = !!it[keySubmitted];
    const dlCount = Number(it[keyDlCount]||0);
    const dlTime = String(it[keyDlTime]||'-');
    const finalTime = String(it[keyFinalTime]||'-');
    const reviewRes = it[keyReview] || '未批阅';
    
    const statusCell = isSubmitted ? '提交' : '未交';
    const u = String(it.username||'');
    
    // Review Result Dropdown
    const reviewSelect = `
      <select class="select review-result-select" data-username="${u}" style="width:100px; padding: 4px;">
        <option value="未批阅" ${reviewRes === '未批阅' ? 'selected' : ''}>未批阅</option>
        <option value="通过" ${reviewRes === '通过' ? 'selected' : ''}>通过</option>
        <option value="不通过" ${reviewRes === '不通过' ? 'selected' : ''}>不通过</option>
      </select>
    `;

    // Action Buttons
    const btnDownload = `<button class="btn-link" data-action="dl-${currentView}" data-username="${u}" ${isSubmitted?'':'disabled'}>下载</button>`;
    const btnReturn = `<button class="btn-link danger" data-action="reject-${currentView}" data-username="${u}" ${isSubmitted?'':'disabled'}>打回</button>`;
    const btnReview = `<a href="teacher_review.html?fileId=${u}&project=${currentView}" class="btn-link primary" target="_blank" ${isSubmitted?'':'style="pointer-events:none;color:#aaa;"'}>审查批阅</a>`;
    
    // Operation Cell
    const actionCell = `
      <span class="act-${currentView}">
        ${btnDownload}
        ${btnReturn}
        ${btnReview}
      </span>
    `;

    tr.innerHTML = `<td><input type="checkbox" class="fs-row" data-username="${u}" ${fsState.selected.has(u)?'checked':''} /></td><td>${u}</td><td>${String(it.name||'')}</td><td>${String(it.class||'')}</td><td>${statusCell}</td><td>${dlCount}</td><td>${dlTime}</td><td>${finalTime}</td><td>${reviewSelect}</td><td>${actionCell}</td>`;
    frag.appendChild(tr);
  });
  tbody.appendChild(frag);
  if (master) master.checked = false;
  
  // Bind events for review select
  tbody.querySelectorAll('.review-result-select').forEach(sel => {
    sel.addEventListener('change', () => {
       const u = sel.getAttribute('data-username');
       updateReviewResult(u, sel.value);
    });
  });

  // Re-bind other buttons (download/reject) - logic remains similar but simplified selectors
  tbody.querySelectorAll('button[data-action^="dl-"]').forEach(btn => {
    btn.addEventListener('click', () => {
        if (btn.disabled) return;
        const action = btn.getAttribute('data-action');
        const type = action.replace('dl-', '');
        const u = String(btn.getAttribute('data-username')||'');
        downloadFile(type, u);
    });
  });
  
  tbody.querySelectorAll('button[data-action^="reject-"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (btn.disabled) return;
      const action = btn.getAttribute('data-action');
      const type = action.replace('reject-', '');
      const u = String(btn.getAttribute('data-username')||'');
      const name = getProjectName(type);

      if (!confirm(`确认打回该学生的${name}并删除原文件吗？`)) return;
      
      let backendType = type;
      if (type === 'intern') backendType = 'internship';
      
      const res = await fetch('/api/reject_universal.php', { 
          method: 'POST', 
          credentials: 'include', 
          headers: {'Content-Type':'application/json'}, 
          body: JSON.stringify({ studentID: u, type: backendType }) 
      });
      const ok = res.ok ? await res.json() : null;
      if (ok && ok.ok) { alert(`已打回${name}`); refreshFileStat(); } 
      else { alert((ok && ok.error)||'打回失败'); }
    });
  });
  
  tbody.querySelectorAll('input.fs-row').forEach(chk => {
    chk.addEventListener('change', () => {
      const u = String(chk.getAttribute('data-username')||'');
      if (chk.checked) fsState.selected.add(u); else fsState.selected.delete(u);
    });
  });
  // Removed applyFileStatView function as it is no longer needed
}

function downloadFile(type, u) {
    let backendType = type;
    if (type === 'intern') backendType = 'internship';
    const url = `/api/download_universal.php?type=${encodeURIComponent(backendType)}&studentID=${encodeURIComponent(u)}`;
    window.open(url, '_blank');
    setTimeout(refreshFileStat, 800);
}

function exportSelectedFileStat() {
  const list = Array.from(fsState.selected);
  if (list.length === 0) { alert('请先选择要导出的学生'); return; }
  
  // Use the currently filtered and sorted items, but only those that are selected
  // Note: fsState.items contains the data for the current VIEW (e.g. thesis only)
  // which matches the table display exactly.
  const rows = fsState.items.filter(it => list.includes(String(it.username||'')));
  const esc = (s) => String(s||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  
  const currentView = fsState.view;
  const projectName = getProjectName(currentView);
  const keySubmitted = currentView + 'Submitted';
  const keyFinalTime = currentView + 'FinalSubmissionTime';
  const keyReview = currentView + 'ReviewResult';

  let html = '<html><head><meta charset="utf-8" /></head><body><table border="1">';
  html += `<thead><tr><th>学号</th><th>姓名</th><th>班级</th><th>${esc(projectName)}-提交状态</th><th>最近提交时间</th><th>审查结果</th></tr></thead><tbody>`;
  
  rows.forEach(it => {
    const isSubmitted = !!it[keySubmitted];
    const statusText = isSubmitted ? '已提交' : '未交';
    const finalTime = String(it[keyFinalTime]||'-');
    const reviewRes = String(it[keyReview]||'未批阅');
    
    html += `<tr><td>${esc(it.username)}</td><td>${esc(it.name)}</td><td>${esc(it.class)}</td><td>${esc(statusText)}</td><td>${esc(finalTime)}</td><td>${esc(reviewRes)}</td></tr>`;
  });
  html += '</tbody></table></body></html>';
  const blob = new Blob([html], { type: 'application/vnd.ms-excel;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const ts = new Date();
  const pad = (n) => String(n).padStart(2,'0');
  const name = `文件统计_${projectName}_${ts.getFullYear()}${pad(ts.getMonth()+1)}${pad(ts.getDate())}_${pad(ts.getHours())}${pad(ts.getMinutes())}${pad(ts.getSeconds())}.xls`;
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function updateBatchBtn() {
  const btn = document.getElementById('fs-batch-pass');
  if (!btn) return;
  const count = fsState.selected.size;
  if (count > 0) {
    btn.style.display = 'inline-block';
    btn.textContent = `批量通过 (${count})`;
  } else {
    btn.style.display = 'none';
  }
}

async function handleBatchPass() {
  const count = fsState.selected.size;
  if (count === 0) return;
  if (!confirm(`确认将选中的 ${count} 项设为‘通过’？`)) return;

  const fileIds = Array.from(fsState.selected);
  const res = await fetch('/api/review/batchPass.php', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ fileIds: fileIds, projectType: fsState.view })
  });
  
  const data = res.ok ? await res.json() : null;
  if (data && data.success) {
    alert(`已批量通过 ${data.affected_rows || count} 项`);
    refreshFileStat();
    fsState.selected.clear();
    document.getElementById('fs-select-all').checked = false;
    updateBatchBtn();
  } else {
    alert('操作失败: ' + (data && data.error || '未知错误'));
  }
}

async function updateReviewResult(u, val) {
  const res = await fetch('/api/review/result/update.php', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ studentID: u, project: fsState.view, result: val })
  });
  const data = res.ok ? await res.json() : null;
  if (data && data.success) {
    // success
  } else {
    alert('更新失败: ' + (data && data.error || '未知错误'));
    refreshFileStat(); // revert
  }
}
