/**
 * 教师管理页面 - 系统设置模块
 * 包含：文件上传格式限制配置、项目管理
 * 
 * 依赖: js/index.js, js/teacher-core.js
 */

let settingsInited = false;

async function initSettings(adm) {
    if (adm) {
        if (!settingsInited) {
            initSettingsSubnav();
            initProjectModal();
            settingsInited = true;
        }
        
        // Fetch and display settings
        const tbody = document.getElementById('settings-tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '<tr><td colspan="3" class="text-center">加载中...</td></tr>';
        
        try {
            const res = await fetch('/api/config_file_types.php', { method: 'GET', credentials: 'include' });
            const data = res.ok ? await res.json() : null;
            
            if (data && data.ok) {
                renderSettingsTable(data.items);
            } else {
                tbody.innerHTML = '<tr><td colspan="3" class="text-center error">加载失败</td></tr>';
            }
            
            // Also render project table
            renderProjectTable();
        } catch (e) {
            console.error(e);
            tbody.innerHTML = '<tr><td colspan="3" class="text-center error">加载出错</td></tr>';
        }
    }
}

function initSettingsSubnav() {
    const subnavBtns = document.querySelectorAll('#settings-subnav .sub-nav-item');
    const titleSpan = document.getElementById('ss-current-sub');
    
    subnavBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            subnavBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const target = btn.getAttribute('data-sub');
            titleSpan.textContent = btn.textContent;
            
            document.querySelectorAll('.settings-sub-panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.settings-sub-panel').forEach(p => p.style.display = 'none');
            
            const panel = document.getElementById(`settings-${target}-panel`);
            if (panel) {
                panel.style.display = 'block';
                panel.classList.add('active');
            }
        });
    });
}

function renderSettingsTable(items) {
    const tbody = document.getElementById('settings-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    const frag = document.createDocumentFragment();
    
    // globalProjects should be available from teacher-core.js
    if (typeof globalProjects === 'undefined' || !globalProjects) return;
    
    globalProjects.forEach(p => {
        const key = p.type_key;
        const name = p.name;
        const exts = items[key] || p.allowed_extensions || []; 
        const extStr = exts.join(', ');
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${name}</td>
            <td>
                <input type="text" class="input settings-ext-input" id="setting-${key}" value="${extStr}" placeholder="如: pdf, doc, docx" />
            </td>
            <td>
                <button class="btn-link" data-action="save-settings" data-key="${key}">保存</button>
            </td>
        `;
        frag.appendChild(tr);
    });
    
    tbody.appendChild(frag);
    
    // Bind events
    tbody.querySelectorAll('button[data-action="save-settings"]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const key = btn.getAttribute('data-key');
            const input = document.getElementById(`setting-${key}`);
            const val = input ? input.value : '';
            
            await saveSetting(key, val, btn);
        });
    });
}

function renderProjectTable() {
    const tbody = document.getElementById('settings-project-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    if (typeof globalProjects === 'undefined' || !globalProjects || globalProjects.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">暂无项目</td></tr>';
        return;
    }
    
    const frag = document.createDocumentFragment();
    globalProjects.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${p.id}</td>
            <td>${p.type_key}</td>
            <td>${p.name}</td>
            <td>${p.has_template ? '有' : '无'}</td>
            <td>${p.template_filename || '-'}</td>
            <td>
                <button class="btn-link" onclick="editProject(${p.id})">编辑</button>
                <button class="btn-link danger" onclick="deleteProject(${p.id})">删除</button>
            </td>
        `;
        frag.appendChild(tr);
    });
    tbody.appendChild(frag);
}

function initProjectModal() {
    const btnAdd = document.getElementById('btn-project-add');
    const modal = document.getElementById('project-modal');
    const btnSave = document.getElementById('proj-save');
    const btnCancel = document.getElementById('proj-cancel');
    const cbTemplate = document.getElementById('proj-has-template');
    const wrapperTemplate = document.getElementById('proj-template-filename-wrapper');
    
    if (!btnAdd || !modal) return;
    
    btnAdd.addEventListener('click', () => {
        document.getElementById('project-title').textContent = '添加项目';
        document.getElementById('proj-id').value = '';
        document.getElementById('proj-name').value = '';
        cbTemplate.checked = false;
        document.getElementById('proj-template-filename').value = '';
        wrapperTemplate.style.display = 'none';
        modal.classList.add('active');
    });
    
    cbTemplate.addEventListener('change', () => {
        wrapperTemplate.style.display = cbTemplate.checked ? 'block' : 'none';
    });
    
    btnCancel.addEventListener('click', () => {
        modal.classList.remove('active');
    });
    
    btnSave.addEventListener('click', async () => {
        const id = document.getElementById('proj-id').value;
        const name = document.getElementById('proj-name').value.trim();
        const hasTemplate = cbTemplate.checked ? 1 : 0;
        const templateFilename = document.getElementById('proj-template-filename').value.trim();
        
        if (!name) {
            alert('请输入项目名称');
            return;
        }
        
        const method = id ? 'PUT' : 'POST';
        const payload = { name, has_template: hasTemplate, template_filename: templateFilename };
        if (id) payload.id = id;
        
        try {
            btnSave.disabled = true;
            btnSave.textContent = '保存中...';
            
            const res = await fetch('/api/config_projects.php', {
                method,
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (data.ok) {
                alert(id ? '项目更新成功' : '项目添加成功');
                modal.classList.remove('active');
                // Reload page to re-init everything cleanly
                location.reload();
            } else {
                alert(data.error || '保存失败');
            }
        } catch (e) {
            console.error(e);
            alert('网络错误');
        } finally {
            btnSave.disabled = false;
            btnSave.textContent = '保存';
        }
    });
}

window.editProject = function(id) {
    const p = globalProjects.find(x => x.id == id);
    if (!p) return;
    
    document.getElementById('project-title').textContent = '编辑项目';
    document.getElementById('proj-id').value = p.id;
    document.getElementById('proj-name').value = p.name;
    
    const cbTemplate = document.getElementById('proj-has-template');
    cbTemplate.checked = !!p.has_template;
    
    document.getElementById('proj-template-filename').value = p.template_filename || '';
    document.getElementById('proj-template-filename-wrapper').style.display = p.has_template ? 'block' : 'none';
    
    document.getElementById('project-modal').classList.add('active');
};

window.deleteProject = async function(id) {
    const p = globalProjects.find(x => x.id == id);
    if (!p) return;
    
    if (!confirm(`确定要删除项目 [${p.name}] 吗？此操作不可恢复，且将删除该项目对应的所有提交数据列！`)) {
        return;
    }
    
    try {
        const res = await fetch('/api/config_projects.php', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ id })
        });
        const data = await res.json();
        
        if (data.ok) {
            alert('删除成功');
            location.reload();
        } else {
            alert(data.error || '删除失败');
        }
    } catch (e) {
        console.error(e);
        alert('网络错误');
    }
};

async function saveSetting(key, val, btn) {
    const exts = val.split(/[,，]/).map(s => s.trim()).filter(s => s);
    
    if (exts.length === 0) {
        alert('请输入至少一个允许的扩展名');
        return;
    }
    
    const originalText = btn.textContent;
    btn.textContent = '保存中...';
    btn.disabled = true;
    
    try {
        const res = await fetch('/api/config_file_types.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ type_key: key, allowed_extensions: exts })
        });
        
        const data = res.ok ? await res.json() : null;
        
        if (data && data.ok) {
            // Update input value with cleaned extensions
            const input = document.getElementById(`setting-${key}`);
            if (input) input.value = data.extensions.join(', ');
            
            btn.textContent = '已保存';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
            }, 1500);
        } else {
            alert('保存失败: ' + ((data && data.error) || '未知错误'));
            btn.textContent = originalText;
            btn.disabled = false;
        }
    } catch (e) {
        console.error(e);
        alert('保存出错: ' + e.message);
        btn.textContent = originalText;
        btn.disabled = false;
    }
}
