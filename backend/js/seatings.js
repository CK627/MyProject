// 座位信息管理相关变量
let currentSeatingsPage = 1;
let seatingsPageSize = 20;
let totalSeatingsPages = 1;
let totalSeatingsRecords = 0;
let selectedSeatings = new Set();

// 座位信息管理主函数
function manageSeatings() {
    hideAllSections();
    
    // 设置活动导航项
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 找到座位管理导航项并设置为活动状态
    const seatingsNavItem = document.querySelector('.nav-item[onclick="manageSeatings()"]');
    if (seatingsNavItem) {
        seatingsNavItem.classList.add('active');
    }
    
    document.getElementById('seatingsContent').style.display = 'block';
    loadSeatings();
}

// 加载座位信息数据
async function loadSeatings(page = 1) {
    try {
        showSeatingsLoading();
        
        const dataSource = document.getElementById('dataSourceFilter').value;
        const seatStatus = document.getElementById('seatStatusFilter').value;
        const checkinStatus = document.getElementById('checkinStatusFilter').value;
        
        const params = {
            action: 'list',
            page: page,
            pageSize: seatingsPageSize,
            dataSource: dataSource,
            seatStatus: seatStatus,
            checkinStatus: checkinStatus
        };
        
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.SEATINGS, params));
        const data = await response.json();
        
        if (data.success) {
            displaySeatingsData(data.data);
            updateSeatingspagination(data.pagination);
        } else {
            throw new Error(data.message || '加载数据失败');
        }
    } catch (error) {
        console.error('加载座位信息失败:', error);
        showAlert('加载座位信息失败: ' + error.message, 'error');
    } finally {
        hideSeatingsLoading();
    }
}

// 显示座位信息数据
function displaySeatingsData(seatings) {
    const tbody = document.getElementById('seatingsTableBody');
    tbody.innerHTML = '';
    
    if (seatings.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center" style="padding: 40px;">
                    <div class="empty-state">
                        <div class="empty-icon">🪑</div>
                        <p>暂无座位信息数据</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    seatings.forEach(seating => {
        const isSelected = selectedSeatings.has(seating.id);
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="checkbox" value="${seating.id}" onchange="toggleSeatingSelection(${seating.id})" ${isSelected ? 'checked' : ''}>
            </td>
            <td>${escapeHtml(seating.name)}</td>
            <td>${escapeHtml(seating.phone)}</td>
            <td>
                <span class="${seating.seat_number === '未安排座位' ? 'unassigned-seat' : 'assigned-seat'}">
                    ${escapeHtml(seating.seat_number)}
                </span>
            </td>
            <td>
                <span class="status-badge ${seating.is_checked_in ? 'status-checked-in' : 'status-not-checked-in'}">
                    ${seating.checkin_status_text}
                </span>
            </td>
            <td>${seating.checkin_time}</td>
            <td>
                <div class="action-buttons">
                    <button class="action-btn-sm action-btn-edit" onclick="editSeating(${seating.id})" title="编辑">
                        编辑
                    </button>
                    <button class="action-btn-sm action-btn-delete" onclick="clearSeatAssignment(${seating.id})" title="清除座位">
                        清除座位
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    // 更新全选复选框状态
    updateSeatingsSelectionUI();
}

// 更新分页信息
function updateSeatingspagination(pagination) {
    currentSeatingsPage = pagination.page;
    totalSeatingsPages = pagination.totalPages;
    totalSeatingsRecords = pagination.totalRecords;
    
    // 检查是否选择了"全部显示"
    const selectedValue = document.getElementById('seatingsPageSize').value;
    const isShowAll = selectedValue === 'all';
    
    if (isShowAll) {
        // 全部显示时，隐藏分页控件，显示为第1页，共1页
        document.getElementById('currentSeatingsPage').textContent = 1;
        document.getElementById('totalSeatingsPages').textContent = 1;
        document.getElementById('totalSeatingsRecords').textContent = totalSeatingsRecords;
        
        // 隐藏分页控件
        const paginationControls = document.querySelector('.pagination-controls');
        if (paginationControls) {
            paginationControls.style.display = 'none';
        }
    } else {
        // 正常分页显示
        document.getElementById('currentSeatingsPage').textContent = currentSeatingsPage;
        document.getElementById('totalSeatingsPages').textContent = totalSeatingsPages;
        document.getElementById('totalSeatingsRecords').textContent = totalSeatingsRecords;
        
        // 显示分页控件
        const paginationControls = document.querySelector('.pagination-controls');
        if (paginationControls) {
            paginationControls.style.display = 'flex';
        }
        
        // 更新分页按钮状态
        document.getElementById('firstSeatingsPageBtn').disabled = currentSeatingsPage === 1;
        document.getElementById('prevSeatingsPageBtn').disabled = currentSeatingsPage === 1;
        document.getElementById('nextSeatingsPageBtn').disabled = currentSeatingsPage === totalSeatingsPages;
        document.getElementById('lastSeatingsPageBtn').disabled = currentSeatingsPage === totalSeatingsPages;
        
        // 生成页码
        generateSeatingsPageNumbers();
    }
}

// 生成页码
function generateSeatingsPageNumbers() {
    const container = document.getElementById('seatingsPageNumbers');
    container.innerHTML = '';
    
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentSeatingsPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalSeatingsPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = `btn btn-sm ${i === currentSeatingsPage ? 'btn-primary' : 'btn-outline-primary'}`;
        pageBtn.textContent = i;
        pageBtn.onclick = () => goToSeatingsPage(i);
        container.appendChild(pageBtn);
    }
}

// 分页导航函数
function goToSeatingsPage(page) {
    if (page >= 1 && page <= totalSeatingsPages) {
        loadSeatings(page);
    }
}

function goToPrevSeatingsPage() {
    if (currentSeatingsPage > 1) {
        loadSeatings(currentSeatingsPage - 1);
    }
}

function goToNextSeatingsPage() {
    if (currentSeatingsPage < totalSeatingsPages) {
        loadSeatings(currentSeatingsPage + 1);
    }
}

function goToLastSeatingsPage() {
    loadSeatings(totalSeatingsPages);
}

function changeSeatingsPageSize() {
    const selectedValue = document.getElementById('seatingsPageSize').value;
    if (selectedValue === 'all') {
        seatingsPageSize = 10000; // 设置一个足够大的数值来获取所有数据
    } else {
        seatingsPageSize = parseInt(selectedValue);
    }
    loadSeatings(1);
}

// 搜索功能
async function searchSeatings() {
    const keyword = document.getElementById('seatingSearchInput').value.trim();
    
    try {
        showSeatingsLoading();
        
        const dataSource = document.getElementById('dataSourceFilter').value;
        
        const params = {
            action: 'search',
            keyword: keyword,
            page: 1,
            pageSize: seatingsPageSize,
            dataSource: dataSource
        };
        
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.SEATINGS, params));
        const data = await response.json();
        
        if (data.success) {
            displaySeatingsData(data.data);
            updateSeatingspagination(data.pagination);
        } else {
            throw new Error(data.message || '搜索失败');
        }
    } catch (error) {
        console.error('搜索失败:', error);
        showAlert('搜索失败: ' + error.message, 'error');
    } finally {
        hideSeatingsLoading();
    }
}

// 清除筛选条件
function clearSeatingsFilters() {
    document.getElementById('seatingSearchInput').value = '';
    document.getElementById('seatStatusFilter').value = '';
    document.getElementById('checkinStatusFilter').value = '';
    loadSeatings(1);
}

// 切换数据源
function changeDataSource() {
    loadSeatings(1);
}

// 刷新数据
function refreshSeatings() {
    const icon = document.getElementById('refreshSeatingsIcon');
    icon.style.animation = 'spin 1s linear infinite';
    
    loadSeatings(currentSeatingsPage).finally(() => {
        setTimeout(() => {
            icon.style.animation = '';
        }, 1000);
    });
}

// 选择功能
function toggleSeatingSelection(id) {
    const checkbox = document.querySelector(`input[value="${id}"]`);
    if (checkbox.checked) {
        selectedSeatings.add(id);
    } else {
        selectedSeatings.delete(id);
    }
    updateSeatingsSelectionUI();
}

function selectAllSeatings() {
    const checkboxes = document.querySelectorAll('#seatingsTableBody input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
        selectedSeatings.add(parseInt(checkbox.value));
    });
    document.getElementById('selectAllSeatingsCheckbox').checked = true;
    updateSeatingsSelectionUI();
}

function toggleSelectAllSeatings() {
    const selectAllCheckbox = document.getElementById('selectAllSeatingsCheckbox');
    const checkboxes = document.querySelectorAll('#seatingsTableBody input[type="checkbox"]');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
        if (selectAllCheckbox.checked) {
            selectedSeatings.add(parseInt(checkbox.value));
        } else {
            selectedSeatings.delete(parseInt(checkbox.value));
        }
    });
    updateSeatingsSelectionUI();
}

function updateSeatingsSelectionUI() {
    const selectedCount = selectedSeatings.size;
    const batchAssignBtn = document.querySelector('button[onclick="batchAssignSeats()"]');
    
    if (batchAssignBtn) {
        batchAssignBtn.disabled = selectedCount === 0;
        batchAssignBtn.textContent = selectedCount > 0 ? `批量分配座位 (${selectedCount})` : '批量分配座位';
    }
}

// 编辑座位信息
async function editSeating(id) {
    try {
        const dataSource = document.getElementById('dataSourceFilter').value;
        
        // 获取座位信息
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.SEATINGS, { 
            action: 'list', 
            page: 1, 
            pageSize: 1000,
            dataSource: dataSource
        }));
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || '获取数据失败');
        }
        
        const seating = data.data.find(s => s.id == id);
        if (!seating) {
            throw new Error('找不到指定的座位信息');
        }
        
        // 填充编辑表单
        document.getElementById('editSeatingId').value = seating.id;
        document.getElementById('editSeatingName').value = seating.name;
        document.getElementById('editSeatingPhone').value = seating.phone;
        document.getElementById('editSeatingNumber').value = seating.seat_number === '未安排座位' ? '' : seating.seat_number;
        document.getElementById('editCheckinStatus').value = seating.is_checked_in;
        
        // 存储数据源信息
        document.getElementById('seatingEditModal').setAttribute('data-source', dataSource);
        
        // 显示编辑模态框
        document.getElementById('seatingEditModal').style.display = 'block';
    } catch (error) {
        console.error('获取座位信息失败:', error);
        showAlert('获取座位信息失败: ' + error.message, 'error');
    }
}

// 保存座位信息编辑
async function saveSeatingEdit() {
    try {
        const id = document.getElementById('editSeatingId').value;
        const seatNumber = document.getElementById('editSeatingNumber').value.trim();
        const isCheckedIn = document.getElementById('editCheckinStatus').value;
        const dataSource = document.getElementById('seatingEditModal').getAttribute('data-source');
        
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.SEATINGS, { action: 'update' }), {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id: parseInt(id),
                seat_number: seatNumber,
                is_checked_in: parseInt(isCheckedIn),
                dataSource: dataSource
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('座位信息更新成功', 'success');
            closeSeatingEdit();
            loadSeatings(currentSeatingsPage);
        } else {
            throw new Error(data.message || '更新失败');
        }
    } catch (error) {
        console.error('更新座位信息失败:', error);
        showAlert('更新座位信息失败: ' + error.message, 'error');
    }
}

// 关闭编辑模态框
function closeSeatingEdit() {
    document.getElementById('seatingEditModal').style.display = 'none';
}

// 清除座位分配
async function clearSeatAssignment(id) {
    if (!confirm('确定要清除这个用户的座位分配吗？')) {
        return;
    }
    
    try {
        const dataSource = document.getElementById('dataSourceFilter').value;
        
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.SEATINGS, { 
            action: 'delete', 
            id: id,
            dataSource: dataSource
        }), {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('座位分配已清除', 'success');
            loadSeatings(currentSeatingsPage);
        } else {
            throw new Error(data.message || '清除失败');
        }
    } catch (error) {
        console.error('清除座位分配失败:', error);
        showAlert('清除座位分配失败: ' + error.message, 'error');
    }
}

// 显示导入模态框
function showImportModal() {
    document.getElementById('importSeatingModal').style.display = 'block';
    clearImportForm();
    initializeFileUploadArea();
}

// 初始化文件上传区域的拖拽功能
function initializeFileUploadArea() {
    const fileUploadArea = document.getElementById('fileUploadArea');
    const fileInput = document.getElementById('excelFileInput');
    
    if (!fileUploadArea || !fileInput) return;
    
    // 防止默认拖拽行为
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // 拖拽进入和悬停
    ['dragenter', 'dragover'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, highlight, false);
    });
    
    // 拖拽离开
    fileUploadArea.addEventListener('dragleave', unhighlight, false);
    
    // 文件放置
    fileUploadArea.addEventListener('drop', handleDrop, false);
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight(e) {
        fileUploadArea.classList.add('dragover');
    }
    
    function unhighlight(e) {
        fileUploadArea.classList.remove('dragover');
    }
    
    function handleDrop(e) {
        unhighlight(e);
        
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            const file = files[0];
            
            // 检查文件类型
            if (!file.name.match(/\.(xlsx|xls)$/i)) {
                showAlert('请选择Excel文件（.xlsx 或 .xls 格式）', 'error');
                return;
            }
            
            // 模拟文件输入
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput.files = dataTransfer.files;
            
            // 触发文件选择处理
            handleFileSelect({ target: { files: [file] } });
        }
    }
}

// 关闭导入模态框
function closeImportModal() {
    document.getElementById('importSeatingModal').style.display = 'none';
    clearImportForm();
}

// 清除导入表单
function clearImportForm() {
    document.getElementById('excelFileInput').value = '';
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('previewSection').style.display = 'none';
    document.getElementById('importBtn').disabled = true;
}

// 处理文件选择
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // 显示文件信息
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileInfo').style.display = 'block';
    
    // 读取并预览Excel文件
    readExcelFile(file);
}

// 读取Excel文件
function readExcelFile(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array' });
            const firstSheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[firstSheetName];
            const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
            
            if (jsonData.length < 2) {
                throw new Error('Excel文件数据不足，至少需要包含表头和一行数据');
            }
            
            // 预览数据
            previewExcelData(jsonData);
            document.getElementById('importBtn').disabled = false;
        } catch (error) {
            console.error('读取Excel文件失败:', error);
            showAlert('读取Excel文件失败: ' + error.message, 'error');
        }
    };
    reader.readAsArrayBuffer(file);
}

// 预览Excel数据
function previewExcelData(data) {
    const previewSection = document.getElementById('previewSection');
    const tableHead = document.getElementById('previewTableHead');
    const tableBody = document.getElementById('previewTableBody');
    const rowCount = document.getElementById('previewRowCount');
    
    // 清空表格
    tableHead.innerHTML = '';
    tableBody.innerHTML = '';
    
    if (data.length === 0) return;
    
    // 生成表头
    const headerRow = document.createElement('tr');
    const expectedHeaders = ['姓名', '手机号', '座位号'];
    expectedHeaders.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        headerRow.appendChild(th);
    });
    tableHead.appendChild(headerRow);
    
    // 生成数据行（最多显示前10行）
    const maxPreviewRows = Math.min(10, data.length - 1);
    for (let i = 1; i <= maxPreviewRows; i++) {
        const row = data[i];
        const tr = document.createElement('tr');
        
        for (let j = 0; j < 3; j++) {
            const td = document.createElement('td');
            td.textContent = row[j] || '';
            tr.appendChild(td);
        }
        tableBody.appendChild(tr);
    }
    
    rowCount.textContent = data.length - 1;
    previewSection.style.display = 'block';
    
    // 存储数据供导入使用
    window.importData = data;
}

// 清除文件
function clearFile() {
    clearImportForm();
}

// 导入座位数据
async function importSeatingData() {
    if (!window.importData || window.importData.length < 2) {
        showAlert('请先选择有效的Excel文件', 'error');
        return;
    }
    
    try {
        // 转换数据格式
        const importData = [];
        for (let i = 1; i < window.importData.length; i++) {
            const row = window.importData[i];
            if (row[0] && row[1] && row[2]) { // 确保三列都有数据
                importData.push({
                    name: row[0].toString().trim(),
                    phone: row[1].toString().trim(),
                    seat_number: row[2].toString().trim()
                });
            }
        }
        
        if (importData.length === 0) {
            throw new Error('没有找到有效的数据行');
        }
        
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.SEATINGS, { action: 'import' }), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ data: importData })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(result.message, 'success');
            if (result.details && result.details.errors.length > 0) {
                console.log('导入错误详情:', result.details.errors);
            }
            closeImportModal();
            loadSeatings(currentSeatingsPage);
        } else {
            throw new Error(result.message || '导入失败');
        }
    } catch (error) {
        console.error('导入失败:', error);
        showAlert('导入失败: ' + error.message, 'error');
    }
}

// 批量分配座位
function batchAssignSeats() {
    if (selectedSeatings.size === 0) {
        showAlert('请先选择要分配座位的用户', 'warning');
        return;
    }
    
    document.getElementById('selectedCount').textContent = selectedSeatings.size;
    document.getElementById('batchAssignModal').style.display = 'block';
}

// 关闭批量分配模态框
function closeBatchAssignModal() {
    document.getElementById('batchAssignModal').style.display = 'none';
}

// 执行批量分配
async function executeBatchAssign() {
    try {
        const prefix = document.getElementById('seatPrefix').value.trim();
        const startNumber = parseInt(document.getElementById('startNumber').value);
        
        if (isNaN(startNumber) || startNumber < 1) {
            throw new Error('请输入有效的起始编号');
        }
        
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.SEATINGS, { action: 'batch_assign' }), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ids: Array.from(selectedSeatings),
                prefix: prefix,
                startNumber: startNumber
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(data.message, 'success');
            closeBatchAssignModal();
            selectedSeatings.clear();
            loadSeatings(currentSeatingsPage);
        } else {
            throw new Error(data.message || '批量分配失败');
        }
    } catch (error) {
        console.error('批量分配失败:', error);
        showAlert('批量分配失败: ' + error.message, 'error');
    }
}

// 加载和隐藏状态
function showSeatingsLoading() {
    const tbody = document.getElementById('seatingsTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="7" class="text-center" style="padding: 40px;">
                <div class="loading-spinner"></div>
                <p>加载中...</p>
            </td>
        </tr>
    `;
}

function hideSeatingsLoading() {
    // 加载完成后会被实际数据替换
}

// 工具函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 显示提示消息
function showAlert(message, type = 'info') {
    // 移除现有的提示框
    const existingAlert = document.querySelector('.alert-message');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    // 创建提示框
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert-message alert-${type}`;
    alertDiv.innerHTML = `
        <div class="alert-content">
            <span class="alert-icon">${getAlertIcon(type)}</span>
            <span class="alert-text">${escapeHtml(message)}</span>
            <button class="alert-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // 添加到页面顶部
    document.body.insertBefore(alertDiv, document.body.firstChild);
    
    // 自动消失
    setTimeout(() => {
        if (alertDiv && alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
    
    // 添加淡入动画
    setTimeout(() => {
        alertDiv.classList.add('show');
    }, 10);
}

// 获取提示图标
function getAlertIcon(type) {
    switch (type) {
        case 'success':
            return '✓';
        case 'error':
            return '✗';
        case 'warning':
            return '⚠';
        default:
            return 'ℹ';
    }
}

// 监听筛选条件变化
document.addEventListener('DOMContentLoaded', function() {
    // 为筛选条件添加事件监听器
    const seatStatusFilter = document.getElementById('seatStatusFilter');
    const checkinStatusFilter = document.getElementById('checkinStatusFilter');
    
    if (seatStatusFilter) {
        seatStatusFilter.addEventListener('change', () => loadSeatings(1));
    }
    
    if (checkinStatusFilter) {
        checkinStatusFilter.addEventListener('change', () => loadSeatings(1));
    }
    
    // 为搜索框添加回车键监听
    const searchInput = document.getElementById('seatingSearchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchSeatings();
            }
        });
    }
});