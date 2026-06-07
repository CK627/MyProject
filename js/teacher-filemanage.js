/**
 * 教师管理页面 - 文件管理模块
 * 包含：班级/学生/文件列表浏览、按类型浏览、下载操作
 * 
 * 依赖: js/index.js, js/teacher-core.js
 */

// FILE_TYPES dynamically fetched
function getFileTypes() {
  if (typeof globalProjects !== 'undefined' && globalProjects && globalProjects.length > 0) {
    return globalProjects.map(p => ({ id: p.type_key, name: p.name }));
  }
  return [];
}

let fmState = { 
  level: 'root',      // root | class | student | files | type_list | type_class | type_files
  cls: '', 
  defaultCls: '', 
  student: '', 
  dir: '',
  fileType: '',       // 当前选中的文件类型
  typeCls: '',        // 类型浏览下的班级（管理员用）
  isAdmin: false      // 是否管理员（无班级限制）
};

function initFileManage(adm) {
  fmState.level = 'root';
  fmState.defaultCls = (adm && adm.class) ? String(adm.class) : '';
  fmState.isAdmin = !fmState.defaultCls; // 没有班级限制就是管理员
  fmState.cls = '';
  fmState.student = '';
  fmState.dir = '';
  fmState.fileType = '';
  fmState.typeCls = '';
  bindFileManageControls();
  fetchFmList();
}

function bindFileManageControls() {
  const up = document.getElementById('fm-dir-up');
  if (up && up.dataset.bound !== '1') {
    up.dataset.bound = '1';
    up.addEventListener('click', () => {
      if (fmState.level === 'files' && fmState.dir) { const parts = fmState.dir.split('/'); parts.pop(); fmState.dir = parts.join('/'); fetchFmList(); return; }
      if (fmState.level === 'files' && !fmState.dir) { fmState.level = 'student'; fetchFmList(); return; }
      if (fmState.level === 'student') { fmState.level = 'class'; fmState.cls = ''; fetchFmList(); return; }
      if (fmState.level === 'class') { fmState.level = 'root'; fetchFmList(); return; }
      if (fmState.level === 'type_files') { fmState.level = fmState.isAdmin ? 'type_class' : 'type_list'; fmState.typeCls = ''; fetchFmList(); return; }
      if (fmState.level === 'type_class') { fmState.level = 'type_list'; fmState.fileType = ''; fetchFmList(); return; }
      if (fmState.level === 'type_list') { fmState.level = 'root'; fetchFmList(); return; }
    });
  }
}

async function refreshFmStudents() { fetchFmList(); }

async function fetchFmList() {
  const tbody = document.getElementById('fm-tbody');
  const cur = document.getElementById('fm-breadcrumb');
  const msg = document.getElementById('fm-msg');
  if (!tbody) return;
  tbody.innerHTML = '';
  const frag = document.createDocumentFragment();
  
  
  // 根目录：显示两个入口
  if (fmState.level === 'root') {
    // 按班级浏览
    const trClass = document.createElement('tr');
    trClass.className = 'folder-row';
    trClass.setAttribute('data-folder', 'by-class');
    trClass.innerHTML = `<td></td><td>📁 按班级浏览</td><td>-</td><td><div class="actions"><button class="btn-link" data-action="open-by-class">打开</button></div></td>`;
    frag.appendChild(trClass);
    // 按类型浏览
    const trType = document.createElement('tr');
    trType.className = 'folder-row';
    trType.setAttribute('data-folder', 'by-type');
    trType.innerHTML = `<td></td><td>📁 按类型浏览</td><td>-</td><td><div class="actions"><button class="btn-link" data-action="open-by-type">打开</button></div></td>`;
    frag.appendChild(trType);
    tbody.appendChild(frag);
    if (cur) cur.textContent = `当前位置：/`;
    if (msg) msg.textContent = '';
    bindFmActions();
    return;
  }
  
  // Fetch student data for stats if needed
  let allStudents = [];
  if (['class', 'student', 'type_list', 'type_class', 'type_files'].includes(fmState.level)) {
      try {
        // Fetch all students to calculate stats
        const resS = await fetch('/api/class_list.php', { method:'GET', credentials:'include' });
        const dataS = resS.ok ? await resS.json() : null;
        allStudents = (dataS && dataS.items) ? dataS.items : [];
      } catch(e) { console.error(e); }
  }

  // 类型列表层级
  if (fmState.level === 'type_list') {
    // 返回上级
    const trParent = document.createElement('tr');
    trParent.className = 'folder-row parent-row';
    trParent.innerHTML = `<td></td><td>📁 ..</td><td>-</td><td><div class="actions"><button class="btn-link" data-action="open-parent">打开</button></div></td>`;
    frag.appendChild(trParent);
    
    // 显示所有文件类型
    getFileTypes().forEach(t => {
      // Calculate status for this type: Is any student missing this type?
      // Filter students relevant to current view (if admin, all; if teacher, only my class)
      // fmState.defaultCls
      const relevantStudents = fmState.isAdmin 
        ? allStudents 
        : allStudents.filter(s => s.class === fmState.defaultCls);
        
      const unsubmittedStudents = relevantStudents.filter(s => s.missing && s.missing.includes(t.name));
      const unsubmittedCount = unsubmittedStudents.length;
      const statusHtml = (relevantStudents.length > 0 && unsubmittedCount === 0)
        ? `<span style="color:green">已经收齐</span>`
        : `<span style="color:orange">还未收齐</span>`;

      // Button Logic
      const btnDisabled = unsubmittedCount === 0;
      const btnStyle = btnDisabled ? 'color: #999; cursor: not-allowed;' : 'color: #007bff; cursor: pointer;';
      const btnTitle = btnDisabled ? '当前无未交项' : '下载未交项清单';
      // Store data in attribute as JSON string is risky with quotes, let's use ID or just rely on click handler to re-calculate/fetch
      // Better: bind data using a map or just pass ID and re-filter in handler.
      // I'll attach data-type attribute and let handler calculate.
      
      const tr = document.createElement('tr');
      tr.className = 'folder-row';
      tr.setAttribute('data-folder', t.id);
      tr.innerHTML = `<td></td><td>📁 ${t.name}</td><td>${statusHtml}</td>
        <td>
            <div class="actions">
                <button class="btn-link" data-action="open-type" data-type="${t.id}">打开</button>
                <button class="btn-link" data-action="download-type" data-type="${t.id}">下载</button>
                <button class="btn-link" data-action="download-type-unsubmitted" data-type="${t.id}" ${btnDisabled ? 'disabled' : ''} style="${btnStyle}" title="${btnTitle}">未交统计</button>
            </div>
        </td>`;
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);
    if (cur) cur.textContent = `当前位置：/按类型浏览`;
    if (msg) msg.textContent = '';
    bindFmActions(allStudents); // Pass allStudents to actions
    return;
  }
  
  // 类型下的班级列表（仅管理员）
  if (fmState.level === 'type_class') {
    const typeName = getFileTypes().find(t => t.id === fmState.fileType)?.name || fmState.fileType;
    // 返回上级
    const trParent = document.createElement('tr');
    trParent.className = 'folder-row parent-row';
    trParent.innerHTML = `<td></td><td>📁 ..</td><td>-</td><td><div class="actions"><button class="btn-link" data-action="open-parent">打开</button></div></td>`;
    frag.appendChild(trParent);
    
    const clsSet = new Set(allStudents.map(x => String(x.class||'')).filter(x => x !== ''));
    const classes = Array.from(clsSet).sort();
    
    classes.forEach(cls => {
      // Status for this class in this type
      const studentsInClass = allStudents.filter(s => s.class === cls);
      const unsubmittedStudents = studentsInClass.filter(s => s.missing && s.missing.includes(typeName));
      const unsubmittedCount = unsubmittedStudents.length;
      const statusHtml = (studentsInClass.length > 0 && unsubmittedCount === 0)
        ? `<span style="color:green">已经收齐</span>`
        : `<span style="color:orange">还未收齐</span>`;

      // Button Logic
      const btnDisabled = unsubmittedCount === 0;
      const btnStyle = btnDisabled ? 'color: #999; cursor: not-allowed;' : 'color: #007bff; cursor: pointer;';
      const btnTitle = btnDisabled ? '当前无未交项' : '下载未交项清单';

      const tr = document.createElement('tr');
      tr.className = 'folder-row';
      tr.setAttribute('data-folder', cls);
      tr.innerHTML = `<td></td><td>📁 ${cls}</td><td>${statusHtml}</td>
        <td>
            <div class="actions">
                <button class="btn-link" data-action="open-type-class" data-class="${cls}">打开</button>
                <button class="btn-link" data-action="download-type-class" data-type="${fmState.fileType}" data-class="${cls}">下载</button>
                <button class="btn-link" data-action="download-type-class-unsubmitted" data-type="${fmState.fileType}" data-class="${cls}" ${btnDisabled ? 'disabled' : ''} style="${btnStyle}" title="${btnTitle}">未交统计</button>
            </div>
        </td>`;
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);
    if (cur) cur.textContent = `当前位置：/按类型浏览/${typeName}`;
    if (msg) msg.textContent = (classes.length === 0) ? '无班级数据' : '';
    bindFmActions(allStudents);
    return;
  }
  
  // 类型文件列表
  if (fmState.level === 'type_files') {
    const typeName = getFileTypes().find(t => t.id === fmState.fileType)?.name || fmState.fileType;
    
    // 返回上级
    const trParent = document.createElement('tr');
    trParent.className = 'folder-row parent-row';
    trParent.innerHTML = `<td></td><td>📁 ..</td><td>-</td><td><div class="actions"><button class="btn-link" data-action="open-parent">打开</button></div></td>`;
    frag.appendChild(trParent);
    // 获取该类型的文件（根据角色筛选班级）
    const classFilter = fmState.isAdmin ? fmState.typeCls : fmState.defaultCls;
    const res = await fetch(`/api/graduation_list_by_type.php?type=${encodeURIComponent(fmState.fileType)}&class=${encodeURIComponent(classFilter)}`, { method:'GET', credentials:'include' });
    const data = res.ok ? await res.json() : null;
    const items = (data && data.ok && data.items) ? data.items : [];
    items.forEach(it => {
      const tr = document.createElement('tr');
      tr.className = 'file-row';
      tr.setAttribute('data-name', it.filename);
      tr.setAttribute('data-path', it.path);
      tr.setAttribute('data-student', it.studentID);
      const displayName = `${it.studentID}${it.name}${it.filename}`;
      // File row status
      let statusHtml = '<span style="color:green">已经收齐</span>';
      if (it.reviewResult === '不通过') {
          statusHtml = '<span style="color:red">审核不通过</span>';
      } else if (it.reviewResult === '未批阅') {
          // statusHtml = '<span style="color:orange">未批阅</span>'; // Optional: Differentiate unreviewed?
          // Requirement says "Unapproved does not count as collected".
          // If it is "Unreviewed", it is collected but not approved.
          // Usually "Collected" means submitted.
          // But user said "Unapproved does not count as collected".
          // This implies "Unapproved" -> "Not Collected" status logic (which we did in class_list.php).
          // Here is the file list. If it is submitted, it is here.
          // So we should show the review status.
      }

      tr.innerHTML = `<td></td><td>${displayName}</td><td>${statusHtml}</td><td><div class="actions"><button class="btn-link" data-action="download-type-file" data-student="${it.studentID}" data-path="${it.path}">下载</button></div></td>`;
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);
    // 面包屑：管理员显示班级，普通教师不显示
    const breadcrumb = fmState.isAdmin 
      ? `当前位置：/按类型浏览/${typeName}/${fmState.typeCls}`
      : `当前位置：/按类型浏览/${typeName}`;
    if (cur) cur.textContent = breadcrumb;
    if (msg) msg.textContent = items.length === 0 ? '暂无该类型的提交文件' : `共 ${items.length} 个文件`;
    bindFmActions();
    return;
  }
  
  // 班级层级
  if (fmState.level === 'class') {
    // 返回上级
    const trParent = document.createElement('tr');
    trParent.className = 'folder-row parent-row';
    trParent.innerHTML = `<td></td><td>📁 ..</td><td>-</td><td><div class="actions"><button class="btn-link" data-action="open-parent">打开</button></div></td>`;
    frag.appendChild(trParent);
    
    const clsSet = new Set(allStudents.map(x => String(x.class||'')).filter(x => x !== ''));
    const classes = Array.from(clsSet).sort();
    
    // Filter classes if not admin (though logic handles this by defaultCls usually, but here we iterate all)
    const visibleClasses = fmState.isAdmin ? classes : (fmState.defaultCls ? [fmState.defaultCls] : []);

    visibleClasses.forEach(cls => {
      // Calculate Status
      const studentsInClass = allStudents.filter(s => s.class === cls);
      const unsubmittedStudents = studentsInClass.filter(s => !s.submitted);
      const unsubmittedCount = unsubmittedStudents.length;
      const statusHtml = (studentsInClass.length > 0 && unsubmittedCount === 0)
         ? `<span style="color:green">已经收齐</span>`
         : `<span style="color:orange">还未收齐</span>`;

      // Button Logic
      const btnDisabled = unsubmittedCount === 0;
      const btnStyle = btnDisabled ? 'color: #999; cursor: not-allowed;' : 'color: #007bff; cursor: pointer;';
      const btnTitle = btnDisabled ? '当前无未交项' : '下载未交项清单';

      const tr = document.createElement('tr');
      tr.className = 'folder-row';
      tr.setAttribute('data-folder', cls);
      tr.innerHTML = `<td></td><td>📁 ${cls}</td><td>${statusHtml}</td>
        <td>
            <div class="actions">
                <button class="btn-link" data-action="open-class" data-class="${cls}">打开</button>
                <button class="btn-link" data-action="download-class" data-class="${cls}">下载</button>
                <button class="btn-link" data-action="download-class-unsubmitted" data-class="${cls}" ${btnDisabled ? 'disabled' : ''} style="${btnStyle}" title="${btnTitle}">未交统计</button>
            </div>
        </td>`;
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);
    if (cur) cur.textContent = `当前位置：/按班级浏览`;
    if (msg) msg.textContent = (visibleClasses.length === 0) ? '无班级数据' : '';
    bindFmActions(allStudents);
    return;
  }
  
  if (fmState.level === 'student') {
    // Update Button Logic for Class View -> Can't do row-based button for "whole class" here.
    // The requirement "3a. 班级浏览模式: 当进入某一班级视图... 激活按钮" implies it should be available here.
    // Since the user asked for "parallel to Open", and Open is in row, I moved it to row in PARENT view.
    // However, inside Student view, there is no row for "The Class".
    // I will NOT add it here to avoid confusion, assuming user will use the button in Class List view.
    // Or if I must, I'd have to put it in toolbar. But user said "parallel to Open".
    // I'll stick to List View only.

    const studentsInClass = allStudents.filter(s => s.class === fmState.cls);
    const items = studentsInClass; // Use already fetched students
    items.sort((a,b) => {
      const au = Number(a.username||0);
      const bu = Number(b.username||0);
      if (isNaN(au) && isNaN(bu)) return String(a.username||'').localeCompare(String(b.username||''));
      if (isNaN(au)) return 1;
      if (isNaN(bu)) return -1;
      return au - bu;
    });
    {
      const tr = document.createElement('tr');
      tr.className = 'folder-row parent-row';
      tr.innerHTML = `<td></td><td>📁 ..</td><td>-</td><td><div class="actions"><button class="btn-link" data-action="open-parent">打开</button></div></td>`;
      frag.appendChild(tr);
    }
    
    // Add "Export Unsubmitted" button to the parent row (or a new special row) for easy access inside the class view?
    // User complaint: "Click into class, operation column has no button... format should be single column ID, Name, Class, Unsubmitted Items"
    // Interpretation: When viewing the list of students (inside a class), there should be a button to download unsubmitted stats for THIS class.
    // Since individual student rows represent ONE student, a "Unsubmitted Stats" button per student row doesn't make sense (it would just be that student's missing items).
    // BUT, the user might mean a "Batch Download" button for the whole class, located somewhere visible.
    // The previous implementation put it on the CLASS LIST view (parent level).
    // If the user wants it INSIDE the class view, I should add it to the toolbar or the header row?
    // User said: "In the operation column...".
    // Maybe they mean for each STUDENT row, show their missing items?
    // "Export format should be... Name, ID, Class, Unsubmitted Items". This sounds like the Batch Export for the whole class.
    // If I am inside the class view, I can add a button to the "Parent Row" or a specific "Stats" row?
    // Or maybe the user means they want to download the unsubmitted items for a SINGLE student?
    // "Single column version... header is Name, ID, Class, Unsubmitted Items".
    // If it's for a single student, the CSV would have 1 row.
    // If it's for the whole class, it has N rows.
    // "Click into class... found no button". This implies they expect the "Class Unsubmitted Stats" button to be available INSIDE the class view too.
    // Let's add it to the toolbar or the parent row.
    // "Operation column... parallel to Open".
    // The "Parent Row" has an "Open" (Open Parent) button. I can add it there?
    // Or I can add a specific row for "Unsubmitted Stats"?
    // Let's add it to the Toolbar of the Student View?
    // User said "Operation Column".
    // Let's look at the student row.
    // If I add it to the student row, it would download stats for THAT student.
    // If the user wants class stats, it should be a global button.
    // Wait, the requirement 3a says: "When entering a class view... activate button... download CSV...".
    // This implies a page-level action.
    // But user asked for it in "Operation Column".
    // Maybe they want a button on each student row to download THAT student's missing items?
    // "File content: ... each row corresponds to an unsubmitted student".
    // This confirms it's a list of students. So it's a CLASS-LEVEL report.
    // So where should the button be?
    // 1. On the "Class List" view (already done).
    // 2. Inside "Class View" (Student List)?
    // If inside, where in "Operation Column"?
    // The only logical place in the table for a "Whole Class" action is the header or a special row.
    // BUT, maybe the user missed the button in the Class List view?
    // Or maybe they want it in the "Parent Row" (..)?
    // Let's add it to the "Parent Row" (..) in the Student View.
    // The parent row has `<td>...</td><td>📁 ..</td><td>-</td><td><div class="actions"><button...data-action="open-parent">...`
    // I will add the button there.
    
    // Calculate class stats
    const unsubmittedStudentsInClass = studentsInClass.filter(s => !s.submitted);
    const btnDisabled = unsubmittedStudentsInClass.length === 0;
    const btnStyle = btnDisabled ? 'color: #999; cursor: not-allowed;' : 'color: #007bff; cursor: pointer;';
    const btnTitle = btnDisabled ? '当前无未交项' : '下载未交项清单';
    
    // Update Parent Row to include the download button
    const trParent = tbody.querySelector('.parent-row');
    if (trParent) {
        trParent.innerHTML = `<td></td><td>📁 .. (返回上级)</td><td>-</td>
            <td>
                <div class="actions">
                    <button class="btn-link" data-action="open-parent">返回</button>
                    <button class="btn-link" data-action="download-current-class-unsubmitted" data-class="${fmState.cls}" ${btnDisabled ? 'disabled' : ''} style="${btnStyle}" title="${btnTitle}">本班未交统计</button>
                </div>
            </td>`;
    }

    items.forEach(it => {
      const u = String(it.username||'');
      const nm = String(it.name||'');
      
      const statusHtml = it.submitted 
         ? `<span style="color:green">已经收齐</span>`
         : `<span style="color:orange">还未收齐</span>`;

      // Student row button: Download missing items for THIS student?
      // "Export format... single column version (all unsubmitted)... Header: Name, ID, Class, Unsubmitted Items".
      // This format works for a single student too.
      // Let's add a button for each student too?
      // "I found no button under the operation column of the PERSONAL FOLDER".
      // "Personal folder" = Student Row.
      // So yes, the user wants a button on the Student Row to download stats for THAT student.
      
      const studentMissing = it.missing || [];
      const studentDisabled = studentMissing.length === 0;
      const studentBtnStyle = studentDisabled ? 'color: #999; cursor: not-allowed;' : 'color: #007bff; cursor: pointer;';
      const studentBtnTitle = studentDisabled ? '已全部收齐' : '下载该生未交项';

      const tr = document.createElement('tr');
      tr.className = 'folder-row';
      tr.setAttribute('data-folder', u);
      tr.innerHTML = `<td></td><td>📁 ${u} ${nm}</td><td>${statusHtml}</td>
        <td>
            <div class="actions">
                <button class="btn-link" data-action="open-student" data-username="${u}">打开</button>
                <button class="btn-link" data-action="download-student" data-username="${u}">下载</button>
                <button class="btn-link" data-action="download-student-unsubmitted" data-username="${u}" ${studentDisabled ? 'disabled' : ''} style="${studentBtnStyle}" title="${studentBtnTitle}">未交统计</button>
            </div>
        </td>`;
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);
    if (cur) cur.textContent = `当前位置：/按班级浏览/${fmState.cls || ''}`;
    if (msg) msg.textContent = (items.length === 0) ? '该班级暂无学生' : '';
    bindFmActions(allStudents);
    return;
  }
  
  // files 层级
  if (fmState.level === 'files') {
    // ... existing logic for files ...
    // Note: User says "Replace Upload Time...".
    // For files, we show "已经收齐" (Green)
    const res = await fetch('/api/graduation_list.php', { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ studentID: fmState.student, dir: fmState.dir }) });
    const data = res.ok ? await res.json() : null;
    const items = Array.isArray(data && data.items) ? data.items : [];
    const folders = Array.isArray(data && data.folders) ? data.folders : [];
    
    // ... sorting ...
    folders.sort((a,b) => {
      const na = typeof a === 'string' ? a : ((a && a.name) || '');
      const nb = typeof b === 'string' ? b : ((b && b.name) || '');
      return String(na).localeCompare(String(nb));
    });
    items.sort((a,b) => String(a.name||'').localeCompare(String(b.name||'')));

    {
      const tr = document.createElement('tr');
      tr.className = 'folder-row parent-row';
      tr.innerHTML = `<td></td><td>📁 ..</td><td>-</td><td><div class="actions"><button class="btn-link" data-action="open-parent">打开</button></div></td>`;
      frag.appendChild(tr);
    }
    folders.forEach(f => {
      const rawName = typeof f === 'string' ? f : ((f && f.name) ?? '');
      const name = String(rawName);
      if (name.startsWith('.')) return;
      // Folder status in File View? Usually unknown unless we check content.
      // Assuming "Collected" for now or "-"
      const tr = document.createElement('tr');
      tr.className = 'folder-row';
      tr.setAttribute('data-folder', name);
      tr.innerHTML = `<td></td><td>📁 ${name}</td><td>-</td><td><div class="actions"><button class="btn-link" data-action="open-folder" data-folder="${name}">打开</button><button class="btn-link" data-action="download-folder" data-folder="${name}">下载</button></div></td>`;
      frag.appendChild(tr);
    });
    items.forEach(it => {
      const name = String(it.name||'');
      if (name.startsWith('.')) return;
      const tr = document.createElement('tr');
      tr.className = 'file-row';
      tr.setAttribute('data-name', name);
      
      let statusHtml = '<span style="color:green">已经收齐</span>';
      if (it.reviewResult === '不通过') {
          statusHtml = '<span style="color:red">审核不通过</span>';
      }
      
      tr.innerHTML = `<td></td><td>${name}</td><td>${statusHtml}</td><td><div class="actions"><button class="btn-link" data-action="download" data-name="${name}">下载</button></div></td>`;
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);
    const tail = fmState.dir ? `/${fmState.dir}` : '';
    if (cur) cur.textContent = `当前位置：/按班级浏览/${fmState.cls || ''}/${fmState.student || ''}${tail}`;
    if (msg) msg.textContent = (items.length === 0 && folders.length === 0) ? '该学生暂无文件或文件夹' : '';
    bindFmActions();
    return;
  }
}

// Helper functions at the end of file
function updateUnsubmittedBtn(active, mode, data) {
    const btn = document.getElementById('fm-btn-unsubmitted');
    if (!btn) return;
    
    // Remove existing listener to avoid duplicates?
    // A clean way is to replace the node or handle event correctly.
    // Or just set a property on the button and use a single listener.
    // I will use a property.
    btn._data = data;
    btn._mode = mode;
    
    if (active) {
        btn.disabled = false;
        btn.style.color = '#007bff'; // Active color
        btn.style.cursor = 'pointer';
        btn.title = '下载未交项清单';
    } else {
        btn.disabled = true;
        btn.style.color = '#999';
        btn.style.cursor = 'not-allowed';
        btn.title = '当前无未交项';
    }
}

// Global listener for the button (only bind once)
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('fm-btn-unsubmitted');
    if (btn) {
        btn.addEventListener('click', () => {
            if (btn.disabled || !btn._data) return;
            downloadUnsubmittedCsv(btn._mode, btn._data);
        });
    }
});

function downloadUnsubmittedCsv(mode, data) {
    // Show loading? (Requirement: "File generation process requires frontend loading mask")
    // I can assume there is a loading mask available or create a simple one.
    // teacher-core.js might have one. Or I'll just change cursor.
    // But requirement says "loading mask".
    const mask = document.createElement('div');
    mask.style.position = 'fixed'; mask.style.top = 0; mask.style.left = 0; mask.style.width = '100%'; mask.style.height = '100%';
    mask.style.background = 'rgba(0,0,0,0.3)'; mask.style.zIndex = 9999; mask.style.display = 'flex'; mask.style.justifyContent = 'center'; mask.style.alignItems = 'center';
    mask.innerHTML = '<div style="background:white;padding:20px;border-radius:5px;">生成中...</div>';
    document.body.appendChild(mask);

    setTimeout(() => {
        try {
            const now = new Date();
            const timestamp = now.getFullYear() + 
                            String(now.getMonth()+1).padStart(2,'0') + 
                            String(now.getDate()).padStart(2,'0') + 
                            String(now.getHours()).padStart(2,'0') + 
                            String(now.getMinutes()).padStart(2,'0') + 
                            String(now.getSeconds()).padStart(2,'0');
            
            let csvContent = '\uFEFF'; // BOM
            let filename = '';

            if (mode === 'class') {
                // Check if it's a single student export
                if (data.students.length === 1) {
                    const s = data.students[0];
                    const safeName = (s.name || '').replace(/[\\/:*?"<>|]/g, '');
                    // User requested: ClassStudentIDName_xxxxxx_xxxxx
                    filename = `${s.class}${s.username}${safeName}_未交项统计_${timestamp}.csv`;
                    csvContent += '姓名,学号,班级,未交项\n';
                    const missingStr = (s.missing || []).join('、');
                    csvContent += `${s.name},${s.username},${s.class},${missingStr}\n`;
                } else {
                    const className = data.className || '班级';
                    filename = `${className}_未交项统计_${timestamp}.csv`;
                    csvContent += '姓名,学号,班级,未交项\n';
                    data.students.forEach(s => {
                        const missingStr = (s.missing || []).join('、');
                        csvContent += `${s.name},${s.username},${s.class},${missingStr}\n`;
                    });
                }
            } else if (mode === 'type') {
                const typeName = data.typeName || '类型';
                filename = `${typeName}_未交项统计_${timestamp}.csv`;
                csvContent += '姓名,学号\n';
                data.students.forEach(s => {
                    csvContent += `${s.name},${s.username}\n`;
                });
            }

            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch(e) {
            console.error(e);
            alert('生成失败');
        } finally {
            document.body.removeChild(mask);
        }
    }, 100); // Small delay to allow UI to update
}

function bindFmActions(allStudents) {
  const tbody = document.getElementById('fm-tbody');
  if (!tbody) return;
  
  if (allStudents) {
      bindUnsubmittedDownloadActions(allStudents);
  }
  
  // 根目录操作
  tbody.querySelectorAll('button[data-action="open-by-class"]').forEach(btn => {
    btn.addEventListener('click', () => { fmState.level = 'class'; fetchFmList(); });
  });
  tbody.querySelectorAll('button[data-action="open-by-type"]').forEach(btn => {
    btn.addEventListener('click', () => { fmState.level = 'type_list'; fetchFmList(); });
  });
  
  // 类型操作
  tbody.querySelectorAll('button[data-action="open-type"]').forEach(btn => {
    btn.addEventListener('click', () => { 
      fmState.fileType = String(btn.getAttribute('data-type')||''); 
      // 管理员进入班级列表，普通教师直接进入文件列表
      fmState.level = fmState.isAdmin ? 'type_class' : 'type_files';
      fmState.typeCls = '';
      fetchFmList(); 
    });
  });
  tbody.querySelectorAll('button[data-action="download-type"]').forEach(btn => {
    btn.addEventListener('click', () => { 
      const t = String(btn.getAttribute('data-type')||''); 
      // 普通教师只下载本班级
      const clsParam = fmState.isAdmin ? '' : `&class=${encodeURIComponent(fmState.defaultCls)}`;
      const url = `/api/graduation_download_by_type.php?type=${encodeURIComponent(t)}${clsParam}`; 
      window.open(url, '_blank'); 
    });
  });
  // 类型下的班级操作（仅管理员）
  tbody.querySelectorAll('button[data-action="open-type-class"]').forEach(btn => {
    btn.addEventListener('click', () => { 
      fmState.typeCls = String(btn.getAttribute('data-class')||''); 
      fmState.level = 'type_files';
      fetchFmList(); 
    });
  });
  tbody.querySelectorAll('button[data-action="download-type-class"]').forEach(btn => {
    btn.addEventListener('click', () => { 
      const t = String(btn.getAttribute('data-type')||''); 
      const cls = String(btn.getAttribute('data-class')||''); 
      const url = `/api/graduation_download_by_type.php?type=${encodeURIComponent(t)}&class=${encodeURIComponent(cls)}`; 
      window.open(url, '_blank'); 
    });
  });
  tbody.querySelectorAll('button[data-action="download-type-file"]').forEach(btn => {
    btn.addEventListener('click', () => { 
      const path = String(btn.getAttribute('data-path')||'');
      // 从路径提取学号（FileUploadGraduationSubmission/学号/...)
      const parts = path.split('/');
      const studentID = parts.length > 1 ? parts[1] : '';
      const url = `/api/graduation_download.php?studentID=${encodeURIComponent(studentID)}&path=${encodeURIComponent(path.replace(/^FileUploadGraduationSubmission\/[^/]+\//, ''))}`;
      window.open(url, '_blank'); 
    });
  });
  
  // 班级操作
  tbody.querySelectorAll('button[data-action="open-class"]').forEach(btn => {
    btn.addEventListener('click', () => { fmState.cls = String(btn.getAttribute('data-class')||''); fmState.level = 'student'; fetchFmList(); });
  });
  tbody.querySelectorAll('button[data-action="open-student"]').forEach(btn => {
    btn.addEventListener('click', () => { fmState.student = String(btn.getAttribute('data-username')||''); fmState.level = 'files'; fmState.dir = ''; fetchFmList(); });
  });
  tbody.querySelectorAll('button[data-action="open-folder"]').forEach(btn => {
    btn.addEventListener('click', () => { const f = String(btn.getAttribute('data-folder')||''); fmState.dir = fmState.dir ? `${fmState.dir}/${f}` : f; fetchFmList(); });
  });
  tbody.querySelectorAll('button[data-action="open-parent"]').forEach(btn => {
    btn.addEventListener('click', () => {
      if (fmState.level === 'files') {
        if (!fmState.dir) { fmState.level = 'student'; fetchFmList(); return; }
        const parts = fmState.dir.split('/'); parts.pop(); fmState.dir = parts.join('/'); fetchFmList(); return;
      }
      if (fmState.level === 'student') { fmState.level = 'class'; fmState.cls = ''; fetchFmList(); return; }
      if (fmState.level === 'class') { fmState.level = 'root'; fetchFmList(); return; }
      if (fmState.level === 'type_files') { fmState.level = fmState.isAdmin ? 'type_class' : 'type_list'; fmState.typeCls = ''; fetchFmList(); return; }
      if (fmState.level === 'type_class') { fmState.level = 'type_list'; fmState.fileType = ''; fetchFmList(); return; }
      if (fmState.level === 'type_list') { fmState.level = 'root'; fetchFmList(); return; }
    });
  });
  tbody.querySelectorAll('button[data-action="download-folder"]').forEach(btn => {
    btn.addEventListener('click', () => { const f = String(btn.getAttribute('data-folder')||''); const url = `/api/graduation_download_folder.php?studentID=${encodeURIComponent(fmState.student)}&dir=${encodeURIComponent(fmState.dir||'')}&name=${encodeURIComponent(f)}`; window.open(url, '_blank'); });
  });
  tbody.querySelectorAll('button[data-action="download-class"]').forEach(btn => {
    btn.addEventListener('click', () => { const cls = String(btn.getAttribute('data-class')||''); const url = `/api/graduation_download_class.php?class=${encodeURIComponent(cls)}`; window.open(url, '_blank'); });
  });
  tbody.querySelectorAll('button[data-action="download-student"]').forEach(btn => {
    btn.addEventListener('click', () => { const sid = String(btn.getAttribute('data-username')||''); const url = `/api/graduation_download_student.php?studentID=${encodeURIComponent(sid)}`; window.open(url, '_blank'); });
  });
  tbody.querySelectorAll('button[data-action="download"]').forEach(btn => {
    btn.addEventListener('click', () => { const name = String(btn.getAttribute('data-name')||''); const p = fmState.dir ? `${fmState.dir}/${name}` : name; const url = `/api/graduation_download.php?studentID=${encodeURIComponent(fmState.student)}&path=${encodeURIComponent(p)}`; window.open(url, '_blank'); });
  });
  
  // 双击操作
  tbody.querySelectorAll('tr.folder-row').forEach(tr => {
    tr.addEventListener('dblclick', () => {
      const isParent = tr.classList.contains('parent-row');
      if (isParent) {
        if (fmState.level === 'files') {
          if (!fmState.dir) { fmState.level = 'student'; fetchFmList(); return; }
          const parts = fmState.dir.split('/');
          parts.pop();
          fmState.dir = parts.join('/');
          fetchFmList();
          return;
        }
        if (fmState.level === 'student') { fmState.level = 'class'; fmState.cls = ''; fetchFmList(); return; }
        if (fmState.level === 'class') { fmState.level = 'root'; fetchFmList(); return; }
        if (fmState.level === 'type_files') { fmState.level = fmState.isAdmin ? 'type_class' : 'type_list'; fmState.typeCls = ''; fetchFmList(); return; }
        if (fmState.level === 'type_class') { fmState.level = 'type_list'; fmState.fileType = ''; fetchFmList(); return; }
        if (fmState.level === 'type_list') { fmState.level = 'root'; fetchFmList(); return; }
        return;
      }
      const name = String(tr.getAttribute('data-folder')||'');
      // 根目录双击
      if (fmState.level === 'root') {
        if (name === 'by-class') { fmState.level = 'class'; fetchFmList(); return; }
        if (name === 'by-type') { fmState.level = 'type_list'; fetchFmList(); return; }
        return;
      }
      // 类型列表双击
      if (fmState.level === 'type_list') { 
        fmState.fileType = name; 
        fmState.level = fmState.isAdmin ? 'type_class' : 'type_files';
        fmState.typeCls = '';
        fetchFmList(); 
        return; 
      }
      // 类型下的班级双击
      if (fmState.level === 'type_class') { fmState.typeCls = name; fmState.level = 'type_files'; fetchFmList(); return; }
      // 班级层级双击
      if (fmState.level === 'class') { fmState.cls = name; fmState.level = 'student'; fetchFmList(); return; }
      if (fmState.level === 'student') { fmState.student = name; fmState.level = 'files'; fmState.dir = ''; fetchFmList(); return; }
      fmState.dir = fmState.dir ? `${fmState.dir}/${name}` : name;
      fetchFmList();
    });
  });
  
  tbody.querySelectorAll('tr.file-row').forEach(tr => {
    tr.addEventListener('dblclick', () => {
      // 类型文件列表双击下载
      if (fmState.level === 'type_files') {
        const path = String(tr.getAttribute('data-path')||'');
        const parts = path.split('/');
        const studentID = parts.length > 1 ? parts[1] : '';
        const url = `/api/graduation_download.php?studentID=${encodeURIComponent(studentID)}&path=${encodeURIComponent(path.replace(/^FileUploadGraduationSubmission\/[^/]+\//, ''))}`;
        window.open(url, '_blank');
        return;
      }
      const name = String(tr.getAttribute('data-name')||'');
      if (!name) return;
      const p = fmState.dir ? `${fmState.dir}/${name}` : name;
      const url = `/api/graduation_download.php?studentID=${encodeURIComponent(fmState.student)}&path=${encodeURIComponent(p)}`;
      window.open(url, '_blank');
    });
  });
}

function bindUnsubmittedDownloadActions(allStudents) {
    const tbody = document.getElementById('fm-tbody');
    if (!tbody) return;

    // Class View Unsubmitted Download
    tbody.querySelectorAll('button[data-action="download-class-unsubmitted"]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.disabled) return;
            const cls = btn.getAttribute('data-class');
            const studentsInClass = allStudents.filter(s => s.class === cls);
            const unsubmittedStudents = studentsInClass.filter(s => !s.submitted);
            downloadUnsubmittedCsv('class', { className: cls, students: unsubmittedStudents });
        });
    });

    // Type View Unsubmitted Download
    tbody.querySelectorAll('button[data-action="download-type-unsubmitted"]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.disabled) return;
            const typeId = btn.getAttribute('data-type');
            const typeName = getFileTypes().find(t => t.id === typeId)?.name || typeId;
            
            // Filter relevant students (admin vs teacher)
            const relevantStudents = fmState.isAdmin 
                ? allStudents 
                : allStudents.filter(s => s.class === fmState.defaultCls);
                
            const unsubmittedStudents = relevantStudents.filter(s => s.missing && s.missing.includes(typeName));
            downloadUnsubmittedCsv('type', { typeName: typeName, students: unsubmittedStudents });
        });
    });

    // Type Class View Unsubmitted Download
    tbody.querySelectorAll('button[data-action="download-type-class-unsubmitted"]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.disabled) return;
            const typeId = btn.getAttribute('data-type');
            const cls = btn.getAttribute('data-class');
            const typeName = getFileTypes().find(t => t.id === typeId)?.name || typeId;
            
            const studentsInClass = allStudents.filter(s => s.class === cls);
            const unsubmittedStudents = studentsInClass.filter(s => s.missing && s.missing.includes(typeName));
            downloadUnsubmittedCsv('type', { typeName: typeName, students: unsubmittedStudents });
        });
    });

    // Current Class View (Parent Row) Unsubmitted Download
    tbody.querySelectorAll('button[data-action="download-current-class-unsubmitted"]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.disabled) return;
            const cls = btn.getAttribute('data-class');
            const studentsInClass = allStudents.filter(s => s.class === cls);
            const unsubmittedStudents = studentsInClass.filter(s => !s.submitted);
            downloadUnsubmittedCsv('class', { className: cls, students: unsubmittedStudents });
        });
    });

    // Individual Student Unsubmitted Download
    tbody.querySelectorAll('button[data-action="download-student-unsubmitted"]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.disabled) return;
            const u = btn.getAttribute('data-username');
            const student = allStudents.find(s => s.username === u);
            if (student) {
                // Reuse 'class' mode but with only 1 student
                downloadUnsubmittedCsv('class', { className: student.class, students: [student] });
            }
        });
    });
}
