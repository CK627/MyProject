// 报名管理页面JavaScript代码

// 全局变量
let currentRegistrations = [];
let currentPage = 1;
let totalPages = 1;
let currentFilters = {};
let currentEditingId = null; // 当前编辑的记录ID

// 显示报名管理
function viewRegistrations() {
    const clickedItem = event.target.closest('.nav-item');
    setActiveNavItem(clickedItem);
    document.getElementById('pageTitle').textContent = '报名管理';
    hideOtherContent();
    document.getElementById('registrationsContent').style.display = 'block';
    
    // 加载报名数据
    loadRegistrations();
}

// 加载报名数据
async function loadRegistrations(page = 1, filters = {}) {
    try {
        const params = {
            action: 'list',
            page: page,
            limit: 20,
            ...filters
        };
        
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.REGISTRATIONS, params));
        const result = await response.json();
        
        if (result.success) {
            currentRegistrations = result.data.list;
            currentPage = result.data.pagination.page;
            totalPages = result.data.pagination.pages;
            
            renderRegistrationsTable(result.data.list);
            updatePaginationInfo(result.data.pagination);
        } else {
            showError('加载报名数据失败: ' + result.error);
        }
    } catch (error) {
        showError('加载报名数据失败: ' + error.message);
    }
}

// 渲染报名表格
function renderRegistrationsTable(registrations) {
    const tbody = document.getElementById('registrationsTableBody');
    tbody.innerHTML = '';
    
    registrations.forEach(registration => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="checkbox" data-id="${registration.id}"></td>
            <td class="col-name">${registration.name}</td>
            <td class="col-phone">${registration.phone}</td>
            <td class="col-education">${formatEducationInfo(registration.education_info)}</td>
            <td class="col-amount">${formatPaymentAmount(registration.total_amount)}</td>
            <td class="col-family">${formatFamilyCount(registration.family_count)}</td>
            <td class="col-talent">${registration.talent_show || '无'}</td>
            <td class="col-material">${registration.material_sponsorship || '无'}</td>
            <td class="col-remarks">${registration.remarks || '无'}</td>
            <td class="col-payment">${getPaymentMethodText(registration.payment_method)}</td>
            <td class="col-time">${formatDateTime(registration.created_at)}</td>
            <td class="col-operation">
                <div class="action-buttons">
                    ${(registration.payment_screenshot || registration.payment_screenshot_2) ? 
                        `<button class="action-btn-sm action-btn-view" onclick="viewPaymentScreenshots(${registration.id}, '${registration.payment_screenshot || ''}', '${registration.payment_screenshot_2 || ''}')" title="查看付款凭证">查看凭证</button>` : 
                        '<span class="no-screenshot">无凭证</span>'
                    }
                    <button class="action-btn-sm action-btn-edit" onclick="editRegistrationRecord(${registration.id})" title="编辑">编辑</button>
                    <button class="action-btn-sm action-btn-delete" onclick="deleteRegistration(${registration.id})" title="删除">删除</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    // 为所有复选框添加事件监听器
    const checkboxes = tbody.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectAllCheckboxState);
    });
    
    // 初始化全选复选框状态
    updateSelectAllCheckboxState();
}

// 更新分页信息
function updatePaginationInfo(pagination) {
    // 检查是否选择了"全部显示"
    const selectedValue = document.getElementById('pageSize').value;
    const isShowAll = selectedValue === 'all';
    
    if (isShowAll) {
        // 全部显示时，隐藏分页控件，显示为第1页，共1页
        document.getElementById('currentPage').textContent = 1;
        document.getElementById('totalPages').textContent = 1;
        document.getElementById('totalRecords').textContent = pagination.total;
        
        // 隐藏分页控件
        const paginationControls = document.querySelector('.pagination-controls');
        if (paginationControls) {
            paginationControls.style.display = 'none';
        }
    } else {
        // 正常分页显示
        document.getElementById('currentPage').textContent = pagination.page;
        document.getElementById('totalPages').textContent = pagination.pages;
        document.getElementById('totalRecords').textContent = pagination.total;
        
        // 显示分页控件
        const paginationControls = document.querySelector('.pagination-controls');
        if (paginationControls) {
            paginationControls.style.display = 'flex';
        }
    }
}

// 格式化学历信息显示
function formatEducationInfo(educationInfo) {
    if (!educationInfo || educationInfo.trim() === '') {
        return '<span class="no-education">未填写</span>';
    }
    return educationInfo;
}

// 格式化家属人数显示
function formatFamilyCount(familyCount) {
    const count = parseInt(familyCount) || 0;
    
    if (count === 0) {
        return '<span class="family-status no-family">不携带家属</span>';
    } else if (count === 1) {
        return '<span class="family-status with-family">携带家属</span>';
    } else {
        return '<span class="family-status with-multiple-family">携带两位以上家属</span>';
    }
}

// 格式化缴费金额显示
function formatPaymentAmount(amount) {
    const numAmount = parseFloat(amount) || 0;
    
    if (numAmount === 0) {
        return '<span class="payment-amount zero-amount">¥0.00</span>';
    } else {
        return `<span class="payment-amount">¥${numAmount.toFixed(2)}</span>`;
    }
}



// 格式化日期时间
function formatDateTime(dateTimeString) {
    const date = new Date(dateTimeString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 获取付款方式文本
function getPaymentMethodText(method) {
    const methods = {
        'wechat': '微信支付',
        'alipay': '支付宝',
        'other': '其他方式',
        'student2025': '2025级学生证明'
    };
    return methods[method] || method;
}

// 渲染付款凭证缩略图
// 查看付款凭证（支持多个凭证）
function viewPaymentScreenshots(registrationId, screenshot1, screenshot2) {
    const screenshots = [];
    if (screenshot1) screenshots.push({ path: screenshot1, label: '付款凭证1' });
    if (screenshot2) screenshots.push({ path: screenshot2, label: '付款凭证2' });
    
    if (screenshots.length === 0) {
        showError('没有付款凭证');
        return;
    }
    
    // 创建模态框显示图片
    const modal = document.createElement('div');
    modal.className = 'image-modal';
    
    let imagesHtml = '';
    screenshots.forEach((screenshot, index) => {
        const imageUrl = ApiUtils.buildImageProxyUrl(screenshot.path);
        imagesHtml += `
            <div class="screenshot-container" ${screenshots.length > 1 ? `style="margin-bottom: 20px;"` : ''}>
                <h4 class="screenshot-title">${screenshot.label}</h4>
                <div class="image-container">
                    <img src="${imageUrl}" alt="${screenshot.label}" class="payment-screenshot" 
                         onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuWbvueJh+WKoOi9veWksei0pTwvdGV4dD48L3N2Zz4='; this.alt='图片加载失败';">
                </div>
                <div class="image-info">
                    <p class="image-path">文件路径: ${screenshot.path}</p>
                    <button class="btn btn-sm btn-outline-primary" onclick="downloadImage('${imageUrl}', '${screenshot.path}')" style="margin-top: 10px;">下载此图片</button>
                </div>
            </div>
        `;
    });
    
    modal.innerHTML = `
        <div class="image-modal-content">
            <div class="image-modal-header">
                <h3>付款凭证 (报名ID: ${registrationId})</h3>
                <button class="image-modal-close" onclick="closeImageModal()">&times;</button>
            </div>
            <div class="image-modal-body">
                ${imagesHtml}
            </div>
            <div class="image-modal-footer">
                <button class="btn btn-secondary" onclick="closeImageModal()">关闭</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 点击背景关闭模态框
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeImageModal();
        }
    });
}

// 查看付款凭证（兼容旧版本，单个凭证）
function viewPaymentScreenshot(screenshotPath) {
    if (!screenshotPath) {
        showError('没有付款凭证');
        return;
    }
    
    // 使用新的多凭证查看函数
    viewPaymentScreenshots(0, screenshotPath, '');
}

// 关闭图片模态框
function closeImageModal() {
    const modal = document.querySelector('.image-modal');
    if (modal) {
        modal.remove();
    }
}

// 下载图片
function downloadImage(imageUrl, filename) {
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = filename.split('/').pop(); // 获取文件名
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 报名管理相关函数
function refreshRegistrations() {
    const refreshIcon = document.getElementById('refreshRegistrationsIcon');
    refreshIcon.style.animation = 'spin 1s linear infinite';
    
    loadRegistrations(currentPage, currentFilters).finally(() => {
        refreshIcon.style.animation = '';
        showSuccess('报名数据刷新成功');
    });
}

async function exportRegistrations() {
    try {
        const format = document.getElementById('exportFormat').value || 'csv';
        
        const params = {
            action: 'export',
            format: format
        };
        
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.REGISTRATIONS, params));
        
        if (format === 'csv') {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `registrations_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showSuccess('CSV文件导出成功');
        } else {
            const result = await response.json();
            if (result.success) {
                const dataStr = JSON.stringify(result.data, null, 2);
                const blob = new Blob([dataStr], { type: 'application/json' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `registrations_${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                showSuccess('JSON文件导出成功');
            } else {
                showError('导出失败: ' + result.error);
            }
        }
    } catch (error) {
        showError('导出失败: ' + error.message);
    }
}

async function searchRegistrations() {
    const keyword = document.getElementById('searchInput').value.trim();
    
    if (!keyword) {
        loadRegistrations(1);
        return;
    }
    
    try {
        const params = {
            action: 'search',
            keyword: keyword
        };
        
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.REGISTRATIONS, params));
        const result = await response.json();
        
        if (result.success) {
            currentRegistrations = result.data.list;
            renderRegistrationsTable(result.data.list);
            
            // 隐藏分页控件，因为搜索结果通常不分页
            document.querySelector('.pagination-container').style.display = 'none';
        } else {
            showError('搜索失败: ' + result.error);
        }
    } catch (error) {
        showError('搜索失败: ' + error.message);
    }
}

function clearFilters() {
    document.getElementById('searchInput').value = '';

    document.getElementById('paymentMethodFilter').value = '';
    document.getElementById('talentShowFilter').value = '';
    
    currentFilters = {};
    loadRegistrations(1, currentFilters);
    
    // 显示分页控件
    document.querySelector('.pagination-container').style.display = '';
    
    showSuccess('筛选条件已清除');
}

// 添加筛选事件监听器
function initializeFilters() {
    
    // 付款方式筛选
    document.getElementById('paymentMethodFilter').addEventListener('change', function() {
        currentFilters.payment_method = this.value;
        loadRegistrations(1, currentFilters);
    });
    
    // 才艺表演筛选
    document.getElementById('talentShowFilter').addEventListener('change', function() {
        currentFilters.talent_show = this.value;
        loadRegistrations(1, currentFilters);
    });
    
    // 搜索框回车事件
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchRegistrations();
        }
    });
}

// 列显示控制函数
function toggleColumn(columnType) {
    const checkbox = document.getElementById(`show${columnType.charAt(0).toUpperCase() + columnType.slice(1).replace(/-/g, '')}`);
    const isVisible = checkbox.checked;
    
    // 获取对应的列元素
    const columnElements = document.querySelectorAll(`.col-${columnType}`);
    
    // 切换显示状态
    columnElements.forEach(element => {
        element.style.display = isVisible ? '' : 'none';
    });
    
    // 显示提示信息
    const columnNames = {
        'name': '姓名',
        'phone': '手机号',
        'education': '年级/学院',
        'amount': '缴费金额',
        'family': '家属人数',
        'talent': '才艺表演',
        'material': '物品赞助',
        'remarks': '备注',
        'payment': '付款方式',
        'time': '报名时间',
        'operation': '操作'
    };
    
    const columnName = columnNames[columnType] || columnType;
    showSuccess(`${columnName}列已${isVisible ? '显示' : '隐藏'}`);
}

function selectAll() {
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const checkboxes = document.querySelectorAll('.registrations-table tbody input[type="checkbox"]');
    
    // 检查当前是否有选中的复选框
    const checkedCount = document.querySelectorAll('.registrations-table tbody input[type="checkbox"]:checked').length;
    const totalCount = checkboxes.length;
    
    // 如果全部选中，则取消全选；否则全选
    const shouldSelectAll = checkedCount < totalCount;
    
    // 更新头部的全选复选框状态
    selectAllCheckbox.checked = shouldSelectAll;
    
    // 更新所有行的复选框状态
    checkboxes.forEach(checkbox => {
        checkbox.checked = shouldSelectAll;
    });
    
    showSuccess(shouldSelectAll ? '已全选' : '已取消全选');
}

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const checkboxes = document.querySelectorAll('.registrations-table tbody input[type="checkbox"]');
    
    // 根据头部复选框的状态来设置所有行的复选框
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
    
    showSuccess(selectAllCheckbox.checked ? '已全选' : '已取消全选');
}

// 更新全选复选框状态
function updateSelectAllCheckboxState() {
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const checkboxes = document.querySelectorAll('.registrations-table tbody input[type="checkbox"]');
    const checkedCheckboxes = document.querySelectorAll('.registrations-table tbody input[type="checkbox"]:checked');
    
    if (checkboxes.length === 0) {
        // 没有复选框时，全选复选框不选中且不是半选状态
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedCheckboxes.length === 0) {
        // 没有选中任何复选框
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedCheckboxes.length === checkboxes.length) {
        // 全部选中
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        // 部分选中
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    }
}

function batchDelete() {
    const selectedCheckboxes = document.querySelectorAll('.registrations-table tbody input[type="checkbox"]:checked');
    
    if (selectedCheckboxes.length === 0) {
        showError('请先选择要删除的记录');
        return;
    }
    
    if (confirm(`确定要删除选中的 ${selectedCheckboxes.length} 条记录吗？此操作不可恢复！`)) {
        const deletePromises = Array.from(selectedCheckboxes).map(checkbox => {
            const id = checkbox.getAttribute('data-id');
            return deleteRegistrationById(id);
        });
        
        Promise.all(deletePromises).then(() => {
            showSuccess(`成功删除 ${selectedCheckboxes.length} 条记录`);
            loadRegistrations(currentPage, currentFilters);
        }).catch(error => {
            showError('批量删除失败: ' + error.message);
        });
    }
}

async function editRegistrationRecord(id) {
    try {
        // 获取记录详情
        const params = {
            action: 'detail',
            id: id
        };
        
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.REGISTRATIONS, params));
        const result = await response.json();
        
        if (result.success) {
            const registration = result.data;
            
            // 填充基本信息
            document.getElementById('editName').value = registration.name;
            document.getElementById('editPhone').value = registration.phone;
            document.getElementById('editEducationInfo').value = registration.education_info || '';
            
            // 设置2025级学生选项
            const is2025Student = registration.is_2025_student === '1' || registration.is_2025_student === 1;
            document.getElementById('editIs2025Student').checked = is2025Student;
            
            // 设置家属人数选择
            const familyCount = parseInt(registration.family_count) || 0;
            const familyCountInput = document.getElementById('editFamilyCount');
            if (familyCountInput) {
                familyCountInput.value = familyCount.toString();
            }
            
            // 设置卡片选中状态
            updateFamilyCardSelection(familyCount);
            
            // 处理家属姓名
            handleEditFamilyCountChange();
            
            // 填充家属姓名
            if (registration.family_names && familyCount > 0) {
                const familyNamesArray = registration.family_names.split(',');
                for (let i = 0; i < familyNamesArray.length && i < familyCount; i++) {
                    const familyNameInput = document.getElementById(`editFamilyName${i + 1}`);
                    if (familyNameInput) {
                        familyNameInput.value = familyNamesArray[i].trim();
                    }
                }
            }
            
            // 填充缴费金额信息
            const paymentAmount = parseFloat(registration.total_amount) || 0;
            document.getElementById('editPaymentAmount').value = paymentAmount;
            
            // 处理2025级学生免费逻辑
            handleEdit2025StudentSelection();
            
            // 填充才艺表演信息
            const talentShow = registration.talent_show || '不才艺表演';
            document.getElementById('editTalentShow').value = talentShow;
            document.getElementById('editTalentDescription').value = registration.talent_description || '';
            
            // 根据才艺表演选择显示/隐藏详情区域
            handleEditTalentShowChange();
            
            // 填充其他信息
            document.getElementById('editMaterialSponsorship').value = registration.material_sponsorship || '';
            document.getElementById('editRemarks').value = registration.remarks || '';
            
            // 设置付款方式
            const paymentMethod = registration.payment_method;
            const paymentMethodInput = document.getElementById('editPaymentMethod');
            if (paymentMethodInput) {
                paymentMethodInput.value = paymentMethod || '';
            }
            
            // 填充其他付款方式详情
            document.getElementById('editOtherPaymentMethod').value = registration.other_payment_method || '';
            
            // 根据付款方式显示相应区域
            handleEditPaymentMethodChange();
            
            // 添加隐藏字段存储ID
            let idInput = document.getElementById('editRegistrationId');
            if (!idInput) {
                idInput = document.createElement('input');
                idInput.type = 'hidden';
                idInput.id = 'editRegistrationId';
                idInput.name = 'id';
                document.getElementById('editRegistrationForm').appendChild(idInput);
            }
            idInput.value = registration.id;
            
            // 设置当前编辑的ID
            currentEditingId = registration.id;
            
            // 加载付款凭证信息
            loadPaymentScreenshots(registration);
            
            // 初始化上传功能
            initializeEditUploadFunctions();
            
            // 添加事件监听器
            addEditEventListeners();
            
            // 显示编辑模态框
            document.getElementById('registrationEditModal').style.display = 'block';
        } else {
            showError('获取记录详情失败: ' + result.error);
        }
    } catch (error) {
        showError('获取记录详情失败: ' + error.message);
    }
}



async function deleteRegistration(id) {
    // 获取对应行的姓名
    const row = event.target.closest('tr');
    const nameCell = row.cells[1]; // 姓名在第二列（索引为1）
    const name = nameCell.textContent.trim();
    
    if (confirm(`确定要删除 ${name} 的报名记录吗？此操作不可恢复！`)) {
        try {
            await deleteRegistrationById(id);
            showSuccess(`${name} 的报名记录删除成功`);
            loadRegistrations(currentPage, currentFilters);
        } catch (error) {
            showError('删除失败: ' + error.message);
        }
    }
}

// 删除单个报名记录的API调用
async function deleteRegistrationById(id) {
    const response = await fetch(API_CONFIG.ENDPOINTS.REGISTRATIONS_MODIFY, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            action: 'delete',  // 添加action参数
            id: id 
        })
    });
    
    const result = await response.json();
    
    if (!result.success) {
        throw new Error(result.message);
    }
    
    return result;
}

function closeRegistrationEdit() {
    document.getElementById('registrationEditModal').style.display = 'none';
    
    // 清理编辑状态
    currentEditingId = null;
    
    // 清理上传预览
    removeUploadPreview(1);
    removeUploadPreview(2);
    
    // 重置表单字段
    document.getElementById('editRegistrationForm').reset();
    
    // 重置2025级学生选项
    const is2025StudentCheckbox = document.getElementById('editIs2025Student');
    if (is2025StudentCheckbox) {
        is2025StudentCheckbox.checked = false;
    }
    
    // 重置家属选择
    const familyCountInput = document.getElementById('editFamilyCount');
    if (familyCountInput) {
        familyCountInput.value = '0';
    }
    
    // 重置卡片选中状态
    updateFamilyCardSelection(0);
    updateFamilyCardDisabledState(false);
    
    // 隐藏家属姓名区域并清空输入框
    const familyNamesSection = document.getElementById('editFamilyNamesSection');
    if (familyNamesSection) {
        familyNamesSection.style.display = 'none';
    }
    
    // 清空家属姓名输入框
    const familyNamesContainer = document.getElementById('editFamilyNamesContainer');
    if (familyNamesContainer) {
        familyNamesContainer.innerHTML = '';
    }
    
    // 重置才艺表演选择
    document.getElementById('editTalentShow').value = '不才艺表演';
    const talentDetailsSection = document.getElementById('editTalentDetailsSection');
    if (talentDetailsSection) {
        talentDetailsSection.style.display = 'none';
    }
    
    // 重置付款方式选择
    const paymentMethodInput = document.getElementById('editPaymentMethod');
    if (paymentMethodInput) {
        paymentMethodInput.value = '';
    }
    
    // 隐藏相关区域并重置内容
    const otherPaymentDetails = document.getElementById('editOtherPaymentDetails');
    if (otherPaymentDetails) {
        otherPaymentDetails.style.display = 'none';
    }
    
    // 重置其他付款方式详情
    const otherPaymentMethod = document.getElementById('editOtherPaymentMethod');
    if (otherPaymentMethod) {
        otherPaymentMethod.value = '';
    }
    

    
    // 重置缴费金额
    const paymentAmountInput = document.getElementById('editPaymentAmount');
    if (paymentAmountInput) {
        paymentAmountInput.value = '';
        paymentAmountInput.disabled = false;
    }
    

}

// 保存编辑的报名记录
async function saveRegistrationEdit() {
    try {
        // 获取表单数据
        const id = document.getElementById('editRegistrationId').value;
        const name = document.getElementById('editName').value.trim();
        const phone = document.getElementById('editPhone').value.trim();
        const educationInfo = document.getElementById('editEducationInfo').value.trim();
        
        // 获取2025级学生选项
        const is2025Student = document.getElementById('editIs2025Student').checked;
        
        // 获取家属人数
        const familyCountInput = document.getElementById('editFamilyCount');
        const familyCount = familyCountInput ? parseInt(familyCountInput.value) : 0;
        
        // 获取家属姓名
        let familyNames = '';
        if (familyCount > 0) {
            const familyNameInputs = [];
            for (let i = 1; i <= familyCount; i++) {
                const familyNameInput = document.getElementById(`editFamilyName${i}`);
                if (familyNameInput && familyNameInput.value.trim()) {
                    familyNameInputs.push(familyNameInput.value.trim());
                }
            }
            familyNames = familyNameInputs.join(',');
        }
        
        // 获取缴费金额
        const paymentAmountInput = document.getElementById('editPaymentAmount');
        const paymentAmount = paymentAmountInput ? parseFloat(paymentAmountInput.value) || 0 : 0;
        
        // 使用用户输入的缴费金额（不再强制2025级学生为0）
        const totalAmount = paymentAmount;

        // 获取付款方式
        const paymentMethodInput = document.getElementById('editPaymentMethod');
        const paymentMethod = paymentMethodInput ? paymentMethodInput.value : '';
        
        const talentShow = document.getElementById('editTalentShow').value;
        const talentDescription = document.getElementById('editTalentDescription').value.trim();
        const materialSponsorship = document.getElementById('editMaterialSponsorship').value.trim();
        const remarks = document.getElementById('editRemarks').value.trim();
        
        // 获取其他付款方式详情
        const otherPaymentMethod = document.getElementById('editOtherPaymentMethod').value.trim();

        // 数据验证
        if (!name) {
            showError('请输入姓名');
            return;
        }
        if (!phone) {
            showError('请输入手机号');
            return;
        }

        // 验证手机号格式
        const phonePattern = /^1[3-9]\d{9}$/;
        if (!phonePattern.test(phone)) {
            showError('请输入正确的手机号格式');
            return;
        }

        if (!paymentMethod) {
            showError('请选择付款方式');
            return;
        }

        // 验证缴费金额
        if (paymentAmount < 0) {
            showError('以自愿为原则，量力而行，遵从内心，上不封顶');
            return;
        }
        if (paymentAmount > 99999) {
            showError('缴费金额不能超过99999元');
            return;
        }

        // 构建更新数据
        const updateData = {
            action: 'update',
            id: id,
            name: name,
            phone: phone,
            education_info: educationInfo,
            is_2025_student: is2025Student ? '1' : '0',
            family_count: familyCount,
            family_names: familyNames,
            payment_amount: totalAmount,
            payment_method: paymentMethod,
            talent_show: talentShow === '不才艺表演' ? null : talentShow,
            talent_description: talentDescription,
            material_sponsorship: materialSponsorship,
            remarks: remarks,
            other_payment_method: otherPaymentMethod
        };

        // 检查是否有新的付款凭证需要上传
        const paymentScreenshot1 = document.getElementById('paymentScreenshot1');
        const paymentScreenshot2 = document.getElementById('paymentScreenshot2');
        
        const hasNewScreenshot1 = paymentScreenshot1 && paymentScreenshot1.files && paymentScreenshot1.files.length > 0;
        const hasNewScreenshot2 = paymentScreenshot2 && paymentScreenshot2.files && paymentScreenshot2.files.length > 0;
        
        console.log('文件上传检查:', {
            hasNewScreenshot1,
            hasNewScreenshot2,
            screenshot1Files: paymentScreenshot1 ? paymentScreenshot1.files.length : 0,
            screenshot2Files: paymentScreenshot2 ? paymentScreenshot2.files.length : 0
        });
        
        if (hasNewScreenshot1 || hasNewScreenshot2) {
            // 如果有文件上传，使用FormData
            const formData = new FormData();
            
            // 添加基本数据
            Object.keys(updateData).forEach(key => {
                formData.append(key, updateData[key]);
            });
            
            // 添加文件
            if (hasNewScreenshot1) {
                formData.append('payment_screenshot', paymentScreenshot1.files[0]);
                console.log('添加付款凭证1:', paymentScreenshot1.files[0].name);
            }
            if (hasNewScreenshot2) {
                formData.append('payment_screenshot_2', paymentScreenshot2.files[0]);
                console.log('添加付款凭证2:', paymentScreenshot2.files[0].name);
            }
            
            // 发送请求
            const response = await fetch(API_CONFIG.ENDPOINTS.REGISTRATIONS_MODIFY, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                showSuccess('报名记录更新成功');
                closeRegistrationEdit();
                loadRegistrations(currentPage, currentFilters); // 刷新列表
            } else {
                showError('保存失败: ' + result.message);
            }
        } else {
            // 没有文件上传，使用JSON
            const response = await fetch(API_CONFIG.ENDPOINTS.REGISTRATIONS_MODIFY, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updateData)
            });

            const result = await response.json();

            if (result.success) {
                showSuccess('报名记录更新成功');
                closeRegistrationEdit();
                loadRegistrations(currentPage, currentFilters); // 刷新列表
            } else {
                showError('保存失败: ' + result.message);
            }
        }
    } catch (error) {
        showError('保存失败: ' + error.message);
    }
}



// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeFilters();
    loadRegistrations(1, {});
    
    // 添加2025级学生选项的事件监听器
    const is2025StudentCheckbox = document.getElementById('editIs2025Student');
    if (is2025StudentCheckbox) {
        is2025StudentCheckbox.addEventListener('change', handle2025StudentSelection);
    }
});

function changePageSize() {
    const selectedValue = document.getElementById('pageSize').value;
    let pageSize;
    
    if (selectedValue === 'all') {
        pageSize = 10000; // 设置一个足够大的数字来获取所有数据
    } else {
        pageSize = parseInt(selectedValue);
    }
    
    // 重新从第一页开始加载，使用新的页面大小
    const params = {
        ...currentFilters,
        limit: pageSize
    };
    loadRegistrations(1, params);
    
    if (selectedValue === 'all') {
        showSuccess('已切换到全部显示模式');
    } else {
        showSuccess(`每页显示条数已更改为: ${pageSize}`);
    }
}

function goToPage(page) {
    if (page < 1 || page > totalPages) {
        showError(`页码超出范围，请输入1-${totalPages}之间的页码`);
        return;
    }
    
    const pageSize = parseInt(document.getElementById('pageSize').value);
    const params = {
        ...currentFilters,
        limit: pageSize
    };
    
    loadRegistrations(page, params);
    showSuccess(`正在跳转到第 ${page} 页...`);
}

function goToPrevPage() {
    const currentPage = parseInt(document.getElementById('currentPage').textContent);
    if (currentPage > 1) {
        goToPage(currentPage - 1);
    } else {
        showError('已经是第一页了');
    }
}

function goToNextPage() {
    const currentPage = parseInt(document.getElementById('currentPage').textContent);
    const totalPages = parseInt(document.getElementById('totalPages').textContent);
    if (currentPage < totalPages) {
        goToPage(currentPage + 1);
    } else {
        showError('已经是最后一页了');
    }
}

function goToLastPage() {
    const totalPages = parseInt(document.getElementById('totalPages').textContent);
    goToPage(totalPages);
}

// 付款凭证管理功能
let currentScreenshots = {
    payment_screenshot: null,
    payment_screenshot_2: null
};

// 初始化付款凭证上传功能
function initializePaymentScreenshotUpload() {
    // 初始化上传区域1
    initializeUploadArea(1);
    // 初始化上传区域2
    initializeUploadArea(2);
}

// 初始化单个上传区域
function initializeUploadArea(index) {
    const uploadArea = document.getElementById(`uploadArea${index}`);
    const fileInput = document.getElementById(`paymentScreenshot${index}`);
    const uploadPreview = document.getElementById(`uploadPreview${index}`);
    
    if (!uploadArea || !fileInput) return;
    
    // 清除之前的事件监听器
    uploadArea.replaceWith(uploadArea.cloneNode(true));
    const newUploadArea = document.getElementById(`uploadArea${index}`);
    const newFileInput = document.getElementById(`paymentScreenshot${index}`);
    
    // 点击上传区域触发文件选择
    newUploadArea.addEventListener('click', function(e) {
        if (e.target === newFileInput) return;
        e.preventDefault();
        e.stopPropagation();
        newFileInput.click();
    });
    
    // 阻止input元素的点击事件冒泡
    newFileInput.addEventListener('click', function(e) {
        e.stopPropagation();
    });
    
    // 拖拽上传功能
    newUploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        newUploadArea.classList.add('drag-over');
    });
    
    newUploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        newUploadArea.classList.remove('drag-over');
    });
    
    newUploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        newUploadArea.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0], index);
        }
    });
    
    // 文件选择处理
    newFileInput.addEventListener('change', function(e) {
        e.stopPropagation();
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0], index);
        }
    });
}

// 处理文件选择
function handleFileSelect(file, index) {
    // 验证文件类型
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
    if (!allowedTypes.includes(file.type)) {
        showError('请选择图片文件（JPG、PNG、GIF）');
        return;
    }
    
    // 验证文件大小（5MB）
    if (file.size > 5 * 1024 * 1024) {
        showError('文件大小不能超过5MB');
        return;
    }
    
    // 将文件设置到对应的input元素中
    const fileInput = document.getElementById(`paymentScreenshot${index}`);
    if (fileInput) {
        // 创建一个新的FileList对象来设置文件
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
    }
    
    // 显示预览
    displayFilePreview(file, index);
}

// 显示文件预览
function displayFilePreview(file, index) {
    const uploadPreview = document.getElementById(`uploadPreview${index}`);
    const uploadArea = document.getElementById(`uploadArea${index}`);
    const uploadPlaceholder = uploadArea.querySelector('.upload-placeholder');
    
    if (!uploadPreview) {
        console.error(`uploadPreview${index} element not found`);
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        uploadPreview.innerHTML = `
            <div class="preview-container text-center">
                <img src="${e.target.result}" alt="付款凭证预览" class="preview-image" style="max-width: 200px; max-height: 150px; width: auto; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <div class="mt-2">
                    <small class="text-muted d-block">${file.name}</small>
                    <small class="text-muted">${(file.size / 1024 / 1024).toFixed(2)} MB</small>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger mt-2" onclick="removeUploadPreview(${index})">
                    <i class="fas fa-trash me-1"></i>删除
                </button>
            </div>
        `;
        uploadPreview.style.display = 'block';
        
        // 隐藏上传区域的占位符
        if (uploadPlaceholder) {
            uploadPlaceholder.style.display = 'none';
        }
    };
    reader.readAsDataURL(file);
}

// 移除上传预览
function removeUploadPreview(index) {
    const uploadPreview = document.getElementById(`uploadPreview${index}`);
    const fileInput = document.getElementById(`paymentScreenshot${index}`);
    const uploadArea = document.getElementById(`uploadArea${index}`);
    const uploadPlaceholder = uploadArea.querySelector('.upload-placeholder');
    
    if (uploadPreview) {
        uploadPreview.style.display = 'none';
        uploadPreview.innerHTML = '';
    }
    
    if (fileInput) {
        fileInput.value = '';
    }
    
    // 显示上传区域的占位符
    if (uploadPlaceholder) {
        uploadPlaceholder.style.display = 'block';
    }
}

// 查看当前付款凭证
function viewCurrentScreenshot(index) {
    const fieldName = index === 1 ? 'payment_screenshot' : 'payment_screenshot_2';
    const screenshotPath = currentScreenshots[fieldName];
    
    if (screenshotPath) {
        // 使用新的多凭证查看功能，显示当前选择的凭证
        const screenshot1 = currentScreenshots.payment_screenshot || '';
        const screenshot2 = currentScreenshots.payment_screenshot_2 || '';
        viewPaymentScreenshots(currentEditingId, screenshot1, screenshot2);
    } else {
        showError('没有找到付款凭证');
    }
}

// 删除当前付款凭证
async function removeCurrentScreenshot(index) {
    const fieldName = index === 1 ? 'payment_screenshot' : 'payment_screenshot_2';
    const screenshotName = index === 1 ? '付款凭证1' : '付款凭证2';
    
    if (confirm(`确定要删除${screenshotName}吗？`)) {
        try {
            // 调用API删除付款凭证
            const response = await fetch(API_CONFIG.ENDPOINTS.REGISTRATIONS_MODIFY, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'remove_screenshot',
                    id: currentEditingId,
                    field: fieldName
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                showSuccess(`${screenshotName}删除成功`);
                // 隐藏当前截图显示
                document.getElementById(`currentScreenshot${index}`).style.display = 'none';
                currentScreenshots[fieldName] = null;
            } else {
                showError('删除失败: ' + result.message);
            }
        } catch (error) {
            showError('删除失败: ' + error.message);
        }
    }
}

// 加载付款凭证信息
function loadPaymentScreenshots(registration) {
    currentScreenshots.payment_screenshot = registration.payment_screenshot;
    currentScreenshots.payment_screenshot_2 = registration.payment_screenshot_2;
    
    // 显示付款凭证1
    if (registration.payment_screenshot) {
        const currentScreenshot1 = document.getElementById('currentScreenshot1');
        const currentScreenshot1Image = document.getElementById('currentScreenshot1Image');
        
        if (currentScreenshot1 && currentScreenshot1Image) {
            const imageUrl = ApiUtils.buildImageProxyUrl(registration.payment_screenshot);
            currentScreenshot1Image.src = imageUrl;
            currentScreenshot1.style.display = 'block';
        }
    } else {
        const currentScreenshot1 = document.getElementById('currentScreenshot1');
        if (currentScreenshot1) {
            currentScreenshot1.style.display = 'none';
        }
    }
    
    // 显示付款凭证2
    if (registration.payment_screenshot_2) {
        const currentScreenshot2 = document.getElementById('currentScreenshot2');
        const currentScreenshot2Image = document.getElementById('currentScreenshot2Image');
        
        if (currentScreenshot2 && currentScreenshot2Image) {
            const imageUrl = ApiUtils.buildImageProxyUrl(registration.payment_screenshot_2);
            currentScreenshot2Image.src = imageUrl;
            currentScreenshot2.style.display = 'block';
        }
    } else {
        const currentScreenshot2 = document.getElementById('currentScreenshot2');
        if (currentScreenshot2) {
            currentScreenshot2.style.display = 'none';
        }
    }
    
    // 清空上传预览
    removeUploadPreview(1);
    removeUploadPreview(2);
}

// 编辑页面辅助函数
function handleEditFamilyCountChange() {
    // 获取选中的家属数量
    const familyCountInput = document.getElementById('editFamilyCount');
    const familyCount = familyCountInput ? parseInt(familyCountInput.value) : 0;
    
    // 更新卡片选中状态
    updateFamilyCardSelection(familyCount);
    
    // 由于已移除家属姓名输入和超员提示功能，此函数现在只需要处理基本的家属数量变化
    console.log('家属数量已更改为:', familyCount);
}

// 处理2025级学生选项变化
function handleEdit2025StudentSelection() {
    const is2025Student = document.getElementById('editIs2025Student').checked;
    const paymentAmountInput = document.getElementById('editPaymentAmount');
    
    if (is2025Student) {
        // 1. 2025级学生可以自由输入缴费金额（不再禁用）
        // if (paymentAmountInput) {
        //     paymentAmountInput.disabled = true;
        //     paymentAmountInput.value = '0';
        // }
        
        // 2. 限制家属选择
        const familyCountInput = document.getElementById('editFamilyCount');
        if (familyCountInput && familyCountInput.value === '1') {
            familyCountInput.value = '0';
            updateFamilyCardSelection(0);
        }
        updateFamilyCardDisabledState(true);
    } else {
        // 1. 缴费金额输入框保持启用状态（无需特殊处理）
        // if (paymentAmountInput) {
        //     paymentAmountInput.disabled = false;
        // }
        
        // 2. 恢复家属选择
        updateFamilyCardDisabledState(false);
    }
}

// 处理家属卡片点击事件
function handleFamilyCardClick(value) {
    const is2025Student = document.getElementById('editIs2025Student').checked;
    
    // 如果是2025级学生且尝试选择携带家属，则阻止操作
    if (is2025Student && value === 1) {
        showError('2025级学生不能选择携带家属');
        return;
    }
    
    // 更新隐藏的input值
    const familyCountInput = document.getElementById('editFamilyCount');
    if (familyCountInput) {
        familyCountInput.value = value.toString();
    }
    
    // 更新卡片选中状态
    updateFamilyCardSelection(value);
    
    console.log('家属数量已更改为:', value);
}

// 更新家属卡片的选中状态
function updateFamilyCardSelection(selectedValue) {
    const noFamilyCard = document.getElementById('editNoFamilyCard');
    const withFamilyCard = document.getElementById('editWithFamilyCard');
    
    if (noFamilyCard && withFamilyCard) {
        // 移除所有选中状态
        noFamilyCard.classList.remove('selected');
        withFamilyCard.classList.remove('selected');
        
        // 添加选中状态
        if (selectedValue === 0) {
            noFamilyCard.classList.add('selected');
        } else if (selectedValue === 1) {
            withFamilyCard.classList.add('selected');
        }
    }
}

// 更新家属卡片的禁用状态
function updateFamilyCardDisabledState(is2025Student) {
    const withFamilyCard = document.getElementById('editWithFamilyCard');
    
    if (withFamilyCard) {
        if (is2025Student) {
            withFamilyCard.classList.add('disabled');
        } else {
            withFamilyCard.classList.remove('disabled');
        }
    }
}

// 已移除updateEditPaymentAmount函数（额外捐赠功能已移除）

function handleEditTalentShowChange() {
    const talentShow = document.getElementById('editTalentShow').value;
    const talentDetailsSection = document.getElementById('editTalentDetailsSection');
    
    if (talentShow === '不才艺表演') {
        talentDetailsSection.style.display = 'none';
        document.getElementById('editTalentDescription').value = '';
    } else {
        talentDetailsSection.style.display = 'block';
    }
}

function handleEditPaymentMethodChange() {
    const paymentMethodSelect = document.getElementById('editPaymentMethod');
    const otherPaymentDetails = document.getElementById('editOtherPaymentDetails');
    
    if (!paymentMethodSelect) return;
    
    const selectedValue = paymentMethodSelect.value;
    
    if (selectedValue === 'other') {
        // 显示其他付款方式详情
        if (otherPaymentDetails) otherPaymentDetails.style.display = 'block';
    } else {
        // 隐藏其他付款方式详情
        if (otherPaymentDetails) otherPaymentDetails.style.display = 'none';
    }
}

function initializeEditUploadFunctions() {
    // 初始化付款凭证上传
    initializePaymentScreenshotUpload();
}

function addEditEventListeners() {
    // 家属卡片点击监听
    const noFamilyCard = document.getElementById('editNoFamilyCard');
    const withFamilyCard = document.getElementById('editWithFamilyCard');
    
    if (noFamilyCard) {
        noFamilyCard.addEventListener('click', function() {
            handleFamilyCardClick(0);
        });
    }
    
    if (withFamilyCard) {
        withFamilyCard.addEventListener('click', function() {
            // 检查是否被禁用
            if (!withFamilyCard.classList.contains('disabled')) {
                handleFamilyCardClick(1);
            }
        });
    }
    
    // 2025级学生选择监听
    const is2025StudentCheckbox = document.getElementById('editIs2025Student');
    if (is2025StudentCheckbox) {
        is2025StudentCheckbox.addEventListener('change', function() {
            handleEdit2025StudentSelection();
            handle2025StudentSelection();
            updateFamilyCardDisabledState(is2025StudentCheckbox.checked);
            
            // 如果勾选了2025级学生且当前选择了携带家属，自动切换到不携带家属
            if (is2025StudentCheckbox.checked) {
                const familyCountInput = document.getElementById('editFamilyCount');
                if (familyCountInput && familyCountInput.value === '1') {
                    handleFamilyCardClick(0);
                }
            }
        });
    }
    
    // 才艺表演选择监听
    document.getElementById('editTalentShow').addEventListener('change', handleEditTalentShowChange);
    
    // 付款方式选择监听
    document.getElementById('editPaymentMethod').addEventListener('change', handleEditPaymentMethodChange);
}

// 处理2025级学生选项变化
function handle2025StudentSelection() {
    const is2025StudentCheckbox = document.getElementById('editIs2025Student');
    const paymentMethodSelect = document.getElementById('editPaymentMethod');
    
    if (is2025StudentCheckbox && is2025StudentCheckbox.checked) {
        // 如果勾选了2025级学生
        
        // 1. 自动选择"2025级学生证明"付款方式
        if (paymentMethodSelect) {
            paymentMethodSelect.value = 'student2025';
        }
        
        // 2. 显示2025级学生证明上传区域
        const student2025Section = document.getElementById('editStudent2025Section');
        if (student2025Section) {
            student2025Section.style.display = 'block';
        }
        
    } else {
        // 如果取消勾选2025级学生
        
        // 1. 重置付款方式
        if (paymentMethodSelect && paymentMethodSelect.value === 'student2025') {
            paymentMethodSelect.value = '';
        }
        
        // 2. 隐藏2025级学生证明上传区域
        const student2025Section = document.getElementById('editStudent2025Section');
        if (student2025Section) {
            student2025Section.style.display = 'none';
        }
    }
}