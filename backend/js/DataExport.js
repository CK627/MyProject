// 数据导出页面JavaScript代码

// 安全工具函数：HTML转义
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// 安全工具函数：JS字符串转义（用于HTML属性中的JS代码）
function escapeJsInHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

// 全局变量
let allRegistrations = []; // 存储所有报名数据
let selectedRegistrations = []; // 存储选中的报名数据
let filteredRegistrations = []; // 存储搜索过滤后的数据
let isSearchMode = false; // 是否处于搜索模式

// 分页相关变量
let currentExportPage = 1;
let exportPageSize = 20;
let totalExportPages = 1;
let totalExportRecords = 0;

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('exportContent')) {
        initDataExportPage();
    }
});

// 页面初始化
function initDataExportPage() {
    console.log('数据导出页面初始化');
    
    // 设置默认页面大小
    const pageSizeSelect = document.getElementById('exportPageSize');
    if (pageSizeSelect) {
        pageSizeSelect.value = exportPageSize;
    }
    
    loadRegistrationsForExport();
    updateExportStats();
}

// 加载报名数据用于导出（支持分页）
async function loadRegistrationsForExport(page = 1) {
    try {
        const params = {
            action: 'list',
            page: page,
            limit: exportPageSize
        };
        
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.REGISTRATIONS, params));
        const result = await response.json();
        
        if (result.success) {
            allRegistrations = result.data.list || [];
            
            // 更新分页信息
            if (result.data.pagination) {
                updateExportPagination(result.data.pagination);
            }
            
            console.log('加载的报名数据:', allRegistrations);
            
            renderExportTable();
            updateExportStats();
            showSuccess(`成功加载第 ${currentExportPage} 页数据，共 ${allRegistrations.length} 条`);
        } else {
            showError('加载报名数据失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        console.error('加载报名数据错误:', error);
        showError('加载报名数据时发生错误: ' + error.message);
    }
}

// 更新分页信息
function updateExportPagination(pagination) {
    currentExportPage = pagination.page;
    totalExportPages = pagination.pages;
    totalExportRecords = pagination.total;
    
    // 检查是否选择了"全部显示"
    const pageSizeSelect = document.getElementById('exportPageSize');
    const isShowAll = pageSizeSelect && pageSizeSelect.value === 'all';
    
    // 更新分页信息显示
    const currentPageElement = document.getElementById('currentExportPage');
    const totalPagesElement = document.getElementById('totalExportPages');
    const totalRecordsElement = document.getElementById('totalExportRecords');
    
    if (currentPageElement) currentPageElement.textContent = isShowAll ? '1' : currentExportPage;
    if (totalPagesElement) totalPagesElement.textContent = isShowAll ? '1' : totalExportPages;
    if (totalRecordsElement) totalRecordsElement.textContent = totalExportRecords;
    
    // 获取分页控件容器
    const paginationControls = document.querySelector('.pagination-controls');
    
    if (isShowAll) {
        // 隐藏分页控件
        if (paginationControls) paginationControls.style.display = 'none';
    } else {
        // 显示分页控件
        if (paginationControls) paginationControls.style.display = 'flex';
        
        // 更新分页按钮状态
        const firstPageBtn = document.getElementById('firstExportPageBtn');
        const prevPageBtn = document.getElementById('prevExportPageBtn');
        const nextPageBtn = document.getElementById('nextExportPageBtn');
        const lastPageBtn = document.getElementById('lastExportPageBtn');
        
        if (firstPageBtn) firstPageBtn.disabled = currentExportPage === 1;
        if (prevPageBtn) prevPageBtn.disabled = currentExportPage === 1;
        if (nextPageBtn) nextPageBtn.disabled = currentExportPage === totalExportPages;
        if (lastPageBtn) lastPageBtn.disabled = currentExportPage === totalExportPages;
        
        // 生成页码
        generateExportPageNumbers();
    }
}

// 生成页码
function generateExportPageNumbers() {
    const container = document.getElementById('exportPageNumbers');
    if (!container) return;
    
    container.innerHTML = '';
    
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentExportPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalExportPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = `btn btn-sm ${i === currentExportPage ? 'btn-primary' : 'btn-outline-primary'}`;
        pageBtn.textContent = i;
        pageBtn.onclick = () => goToExportPage(i);
        container.appendChild(pageBtn);
    }
}

// 跳转到指定页面
function goToExportPage(page) {
    if (page < 1 || page > totalExportPages) return;
    currentExportPage = page;
    loadRegistrationsForExport(page);
}

// 上一页
function goToPrevExportPage() {
    if (currentExportPage > 1) {
        currentExportPage--;
        loadRegistrationsForExport(currentExportPage);
    }
}

// 下一页
function goToNextExportPage() {
    if (currentExportPage < totalExportPages) {
        currentExportPage++;
        loadRegistrationsForExport(currentExportPage);
    }
}

// 跳转到第一页
function goToFirstExportPage() {
    if (currentExportPage > 1) {
        currentExportPage = 1;
        loadRegistrationsForExport(1);
    }
}

// 跳转到最后一页
function goToLastExportPage() {
    if (totalExportPages > 0 && currentExportPage < totalExportPages) {
        currentExportPage = totalExportPages;
        loadRegistrationsForExport(totalExportPages);
    }
}

// 改变每页显示数量
function changeExportPageSize() {
    const pageSizeSelect = document.getElementById('exportPageSize');
    if (pageSizeSelect) {
        const selectedValue = pageSizeSelect.value;
        if (selectedValue === 'all') {
            exportPageSize = 10000; // 设置一个足够大的数值来显示所有记录
        } else {
            exportPageSize = parseInt(selectedValue);
        }
        currentExportPage = 1; // 重置到第一页
        loadRegistrationsForExport(1);
    }
}

// 渲染导出数据表格（与报名管理页面保持一致的显示格式）
function renderExportTable() {
    const tableBody = document.getElementById('exportTableBody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    // 根据搜索模式选择数据源
    const dataSource = isSearchMode ? filteredRegistrations : allRegistrations;
    
    if (dataSource.length === 0) {
        const emptyMessage = isSearchMode ? '未找到匹配的数据' : '暂无报名数据';
        tableBody.innerHTML = `
            <tr>
                <td colspan="17" class="empty-data">
                    <div class="empty-icon">📝</div>
                    <p>${emptyMessage}</p>
                </td>
            </tr>
        `;
        return;
    }
    
    dataSource.forEach((registration, index) => {
        const row = document.createElement('tr');
        const isSelected = selectedRegistrations.find(r => r.id == registration.id);
        row.innerHTML = `
            <td>
                <input type="checkbox" class="export-row-checkbox" 
                       data-id="${registration.id}" 
                       ${isSelected ? 'checked' : ''}
                       onchange="handleRowSelection(${registration.id})">
            </td>
            <td class="col-name">${escapeHtml(registration.name)}</td>
            <td class="col-phone">${escapeHtml(registration.phone)}</td>
            <td class="col-education">${formatEducationInfo(registration.education_info)}</td>
            <td class="col-amount">${formatPaymentAmount(registration.total_amount)}</td>
            <td class="col-family">${formatFamilyCount(registration.family_count)}</td>
            <td class="col-talent">${escapeHtml(registration.talent_show || '无')}</td>
            <td class="col-material">${escapeHtml(registration.material_sponsorship || '无')}</td>
            <td class="col-remarks">${escapeHtml(registration.remarks || '无')}</td>
            <td class="col-payment">${getPaymentMethodText(registration.payment_method)}</td>
            <td class="col-time">${formatDateTime(registration.created_at)}</td>
            <td class="col-seat-number">${formatSeatNumber(registration.seat_number)}</td>
            <td class="col-checkin-status">${formatCheckinStatus(registration.is_checked_in)}</td>
            <td class="col-checkin-time">${formatCheckinTime(registration.checkin_time)}</td>
            <td class="col-payment-screenshot-1">${renderPaymentScreenshotThumbnail(registration.payment_screenshot, '凭证1', registration.id)}</td>
            <td class="col-payment-screenshot-2">${renderPaymentScreenshotThumbnail(registration.payment_screenshot_2, '凭证2', registration.id)}</td>
        `;
        tableBody.appendChild(row);
    });
    
    // 更新全选复选框状态
    updateSelectAllCheckbox();
}

// 格式化学历信息显示（与报名管理页面完全一致）
function formatEducationInfo(educationInfo) {
    if (!educationInfo || educationInfo.trim() === '') {
        return '<span class="no-education">未填写</span>';
    }
    return educationInfo;
}

// 格式化家属人数显示（与报名管理页面完全一致）
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

// 格式化缴费金额显示（与报名管理页面完全一致）
function formatPaymentAmount(amount) {
    const numAmount = parseFloat(amount) || 0;
    
    if (numAmount === 0) {
        return '<span class="payment-amount zero-amount">¥0.00</span>';
    } else {
        return `<span class="payment-amount">¥${numAmount.toFixed(2)}</span>`;
    }
}



// 格式化日期时间（与报名管理页面完全一致）
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

// 获取付款方式文本（与报名管理页面完全一致）
function getPaymentMethodText(method) {
    const methods = {
        'wechat': '微信支付',
        'alipay': '支付宝',
        'other': '其他方式'
    };
    return methods[method] || method;
}

// 格式化座位号显示
function formatSeatNumber(seatNumber) {
    if (!seatNumber || seatNumber.trim() === '') {
        return '<span class="no-seat">未分配</span>';
    }
    return `<span class="seat-number">${seatNumber}</span>`;
}

// 格式化签到状态显示
function formatCheckinStatus(isCheckedIn) {
    if (isCheckedIn === 1 || isCheckedIn === '1' || isCheckedIn === true) {
        return '<span class="checkin-status checked-in">已签到</span>';
    } else {
        return '<span class="checkin-status not-checked-in">未签到</span>';
    }
}

// 格式化签到时间显示
function formatCheckinTime(checkinTime) {
    if (!checkinTime || checkinTime === '0000-00-00 00:00:00' || checkinTime === null) {
        return '<span class="no-checkin-time">未签到</span>';
    }
    return formatDateTime(checkinTime);
}

// 渲染付款凭证缩略图（与报名管理页面一致）
function renderPaymentScreenshotThumbnail(screenshotPath, label, registrationId) {
    if (!screenshotPath) {
        return '<span class="no-screenshot">无凭证</span>';
    }
    
    const imageUrl = ApiUtils.buildImageProxyUrl(screenshotPath);
    // 对路径进行JS转义，防止XSS
    const safePath = escapeJsInHtml(screenshotPath);
    
    return `
        <div class="screenshot-thumbnail-container">
            <img src="${imageUrl}" 
                 alt="${escapeHtml(label)}" 
                 class="screenshot-thumbnail" 
                 onclick="viewPaymentScreenshots(${registrationId}, '${safePath}', '')"
                 onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIiBzdHJva2U9IiNkZGQiLz48dGV4dCB4PSI1MCUiIHk9IjUwJSIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjEwIiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+5peg5Zu+PC90ZXh0Pjwvc3ZnPg=='; this.alt='图片加载失败';"
                 title="点击查看${escapeHtml(label)}">
            <div class="thumbnail-label">${escapeHtml(label)}</div>
        </div>
    `;
}

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
        const safePath = escapeJsInHtml(screenshot.path);
        imagesHtml += `
            <div class="screenshot-container" ${screenshots.length > 1 ? `style="margin-bottom: 20px;"` : ''}>
                <h4 class="screenshot-title">${escapeHtml(screenshot.label)}</h4>
                <div class="image-container">
                    <img src="${imageUrl}" alt="${escapeHtml(screenshot.label)}" class="payment-screenshot" 
                         onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuWbvueJh+WKoOi9veWksei0pTwvdGV4dD48L3N2Zz4='; this.alt='图片加载失败';">
                </div>
                <div class="image-info">
                    <p class="image-path">文件路径: ${escapeHtml(screenshot.path)}</p>
                    <button class="btn btn-sm btn-outline-primary" onclick="downloadImage('${imageUrl}', '${safePath}')" style="margin-top: 10px;">下载此图片</button>
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

// 列显示控制功能
function toggleExportColumn(columnType) {
    // 根据columnType参数映射到正确的复选框ID
    const idMapping = {
        'name': 'showExportName',
        'phone': 'showExportPhone',
        'education': 'showExportEducation',
        'family': 'showExportFamily',

        'amount': 'showExportAmount',
        'donation': 'showExportDonation',
        'talent': 'showExportTalent',
        'material': 'showExportMaterial',
        'remarks': 'showExportRemarks',
        'payment': 'showExportPayment',
        'time': 'showExportTime',
        'payment-screenshot-1': 'showExportPaymentScreenshot1',
        'payment-screenshot-2': 'showExportPaymentScreenshot2',
        'seat-number': 'showExportSeatNumber',
        'checkin-status': 'showExportCheckinStatus',
        'checkin-time': 'showExportCheckinTime'
    };
    
    const checkboxId = idMapping[columnType];
    
    if (!checkboxId) {
        console.error(`未找到列类型 ${columnType} 对应的复选框ID`);
        return;
    }
    
    const checkbox = document.getElementById(checkboxId);
    if (!checkbox) {
        console.error(`找不到复选框: ${checkboxId}`);
        return;
    }
    
    const isVisible = checkbox.checked;
    
    // 构建正确的CSS选择器 - 实际的CSS类名是 col-name, col-phone 等
    const cssSelector = `.col-${columnType}`;
    const columnElements = document.querySelectorAll(cssSelector);
    
    if (columnElements.length === 0) {
        console.warn(`未找到CSS类名为 ${cssSelector} 的元素`);
    }
    
    columnElements.forEach(element => {
        element.style.display = isVisible ? '' : 'none';
    });
    
    // 显示提示信息
    const columnNames = {
        'name': '姓名',
        'phone': '手机号',
        'education': '年级/学院',
        'family': '家属人数',
        'amount': '缴费金额',
        'talent': '才艺表演',
        'payment': '付款方式',
        'time': '报名时间',
        'seat-number': '座位号',
        'checkin-status': '签到状态',
        'checkin-time': '签到时间',
        'payment-screenshot-1': '凭证1',
        'payment-screenshot-2': '凭证2'
    };
    
    const columnName = columnNames[columnType] || columnType;
    showSuccess(`${columnName}列已${isVisible ? '显示' : '隐藏'}`);
}

// 处理行选择
function handleRowSelection(registrationId) {
    const checkbox = document.querySelector(`.export-row-checkbox[data-id="${registrationId}"]`);
    const registration = allRegistrations.find(r => r.id == registrationId);
    
    if (!checkbox || !registration) {
        console.error(`找不到复选框或注册数据: ${registrationId}`);
        return;
    }
    
    if (checkbox.checked) {
        if (!selectedRegistrations.find(r => r.id == registrationId)) {
            selectedRegistrations.push(registration);
        }
    } else {
        selectedRegistrations = selectedRegistrations.filter(r => r.id != registrationId);
    }
    
    updateExportStats();
    updateSelectAllCheckbox();
}

// 全选/取消全选
function toggleSelectAllExport() {
    const selectAllCheckbox = document.getElementById('selectAllExportCheckbox');
    const rowCheckboxes = document.querySelectorAll('.export-row-checkbox');
    
    if (selectAllCheckbox.checked) {
        // 全选
        selectedRegistrations = [...allRegistrations];
        rowCheckboxes.forEach(checkbox => {
            checkbox.checked = true;
        });
    } else {
        // 取消全选
        selectedRegistrations = [];
        rowCheckboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
    }
    
    updateExportStats();
}

// 更新全选复选框状态
function updateSelectAllCheckbox() {
    const selectAllCheckbox = document.getElementById('selectAllExportCheckbox');
    const rowCheckboxes = document.querySelectorAll('.export-row-checkbox');
    const checkedCount = document.querySelectorAll('.export-row-checkbox:checked').length;
    
    if (checkedCount === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedCount === rowCheckboxes.length) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    }
}

// 更新导出统计信息
function updateExportStats() {
    const totalCount = isSearchMode ? filteredRegistrations.length : allRegistrations.length;
    const selectedCount = selectedRegistrations.length;
    
    document.getElementById('totalDataCount').textContent = totalCount;
    document.getElementById('selectedDataCount').textContent = selectedCount;
    
    // 更新导出按钮状态
    const exportButtons = document.querySelectorAll('.export-btn');
    exportButtons.forEach(btn => {
        btn.disabled = selectedCount === 0;
    });
}

// 快速选择功能
function quickSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllExportCheckbox');
    selectAllCheckbox.checked = true;
    toggleSelectAllExport();
    showSuccess('已选择全部数据');
}

function quickSelectNone() {
    const selectAllCheckbox = document.getElementById('selectAllExportCheckbox');
    selectAllCheckbox.checked = false;
    toggleSelectAllExport();
    showSuccess('已取消选择全部数据');
}

function quickSelectReverse() {
    const rowCheckboxes = document.querySelectorAll('.export-row-checkbox');
    selectedRegistrations = [];
    
    rowCheckboxes.forEach(checkbox => {
        checkbox.checked = !checkbox.checked;
        if (checkbox.checked) {
            const registrationId = checkbox.getAttribute('data-id');
            const registration = allRegistrations.find(r => r.id == registrationId);
            if (registration) {
                selectedRegistrations.push(registration);
            }
        }
    });
    
    updateExportStats();
    updateSelectAllCheckbox();
    showSuccess('已反选数据');
}

// 获取可见列的配置
function getVisibleColumnsConfig(exportType = 'excel') {
    // 定义所有列的配置
    const allColumns = [
        {
            id: 'name',
            checkboxId: 'showExportName',
            header: '姓名',
            getValue: (registration) => registration.name || ''
        },
        {
            id: 'phone',
            checkboxId: 'showExportPhone',
            header: '手机号',
            getValue: (registration) => registration.phone || ''
        },
        {
            id: 'education',
            checkboxId: 'showExportEducation',
            header: '年级/学院',
            getValue: (registration) => formatEducationInfo(registration.education_info)
        },
        {
            id: 'family',
            checkboxId: 'showExportFamily',
            header: '家属人数',
            getValue: (registration) => {
                const count = parseInt(registration.family_count) || 0;
                if (count === 0) {
                    return '不携带家属';
                } else if (count === 1) {
                    return '携带家属';
                } else {
                    return '携带两位以上家属';
                }
            }
        },
        {
            id: 'amount',
            checkboxId: 'showExportAmount',
            header: '缴费金额',
            getValue: (registration) => formatPaymentAmount(registration.total_amount)
        },
        {
            id: 'talent',
            checkboxId: 'showExportTalent',
            header: '才艺表演',
            getValue: (registration) => registration.talent_show || '无'
        },
        {
            id: 'material',
            checkboxId: 'showExportMaterial',
            header: '物品赞助',
            getValue: (registration) => registration.material_sponsorship || '无'
        },
        {
            id: 'remarks',
            checkboxId: 'showExportRemarks',
            header: '备注',
            getValue: (registration) => registration.remarks || '无'
        },
        {
            id: 'payment',
            checkboxId: 'showExportPayment',
            header: '付款方式',
            getValue: (registration) => getPaymentMethodText(registration.payment_method)
        },
        {
            id: 'time',
            checkboxId: 'showExportTime',
            header: '报名时间',
            getValue: (registration) => formatDateTime(registration.created_at)
        },
        {
            id: 'seat-number',
            checkboxId: 'showExportSeatNumber',
            header: '座位号',
            getValue: (registration) => registration.seat_number || '未分配'
        },
        {
            id: 'checkin-status',
            checkboxId: 'showExportCheckinStatus',
            header: '签到状态',
            getValue: (registration) => {
                if (registration.is_checked_in === 1 || registration.is_checked_in === '1' || registration.is_checked_in === true) {
                    return '已签到';
                } else {
                    return '未签到';
                }
            }
        },
        {
            id: 'checkin-time',
            checkboxId: 'showExportCheckinTime',
            header: '签到时间',
            getValue: (registration) => {
                if (!registration.checkin_time || registration.checkin_time === '0000-00-00 00:00:00' || registration.checkin_time === null) {
                    return '未签到';
                }
                return formatDateTime(registration.checkin_time);
            }
        },
        {
            id: 'payment-screenshot-1',
            checkboxId: 'showExportPaymentScreenshot1',
            header: exportType === 'excel' ? '凭证1' : '凭证1路径',
            getValue: (registration) => {
                if (exportType === 'excel') {
                    // Excel导出时，返回占位符，实际图片将直接嵌入
                    return registration.payment_screenshot && registration.payment_screenshot !== '无凭证' ? '图片' : '无凭证';
                } else {
                    // CSV导出：返回路径
                    return registration.payment_screenshot || '无凭证';
                }
            }
        },
        {
            id: 'payment-screenshot-2',
            checkboxId: 'showExportPaymentScreenshot2',
            header: exportType === 'excel' ? '凭证2' : '凭证2路径',
            getValue: (registration) => {
                if (exportType === 'excel') {
                    // Excel导出时，返回占位符，实际图片将直接嵌入
                    return registration.payment_screenshot_2 && registration.payment_screenshot_2 !== '无凭证' ? '图片' : '无凭证';
                } else {
                    // CSV导出：返回路径
                    return registration.payment_screenshot_2 || '无凭证';
                }
            }
        }
    ];
    
    // 过滤出可见的列（复选框被选中的列）
    return allColumns.filter(column => {
        const checkbox = document.getElementById(column.checkboxId);
        return checkbox && checkbox.checked;
    });
}

// 导出为Excel（使用ExcelJS支持图片嵌入）
async function exportToExcel() {
    if (selectedRegistrations.length === 0) {
        showError('请先选择要导出的数据');
        return;
    }
    
    // 记录导出开始
    exportLogger.logExportStart('Excel', selectedRegistrations.length);
    
    try {
        // 创建工作簿
        const workbook = new ExcelJS.Workbook();
        const worksheet = workbook.addWorksheet('报名数据');
        
        // 获取要导出的列配置（Excel类型）
        const columnConfig = getVisibleColumnsConfig('excel');
        
        // 设置列定义
        worksheet.columns = columnConfig.map((col, index) => ({
            header: col.header,
            key: col.id,
            width: getColumnWidth(col.id)
        }));
        
        // 设置表头样式
        worksheet.getRow(1).font = { bold: true };
        worksheet.getRow(1).fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFE6F3FF' }
        };
        
        // 图片处理统计
        const imageStats = { total: 0, success: 0, failed: 0, skipped: 0 };
        
        // 添加数据行
        for (let i = 0; i < selectedRegistrations.length; i++) {
            const registration = selectedRegistrations[i];
            const rowData = {};
            
            // 为每列添加数据
            for (const col of columnConfig) {
                if (col.id === 'payment-screenshot-1' || col.id === 'payment-screenshot-2') {
                    // 对于凭证列，先添加占位符
                    rowData[col.id] = '图片';
                } else {
                    rowData[col.id] = col.getValue(registration);
                }
            }
            
            const row = worksheet.addRow(rowData);
            
            // 处理图片嵌入
            for (let j = 0; j < columnConfig.length; j++) {
                const col = columnConfig[j];
                if (col.id === 'payment-screenshot-1' || col.id === 'payment-screenshot-2') {
                    const imagePath = col.id === 'payment-screenshot-1' ? 
                        registration.payment_screenshot : 
                        registration.payment_screenshot_2;
                    
                    imageStats.total++;
                    
                    if (imagePath && imagePath !== '无凭证') {
                        try {
                            // 记录开始处理图片
                            exportLogger.logImageProcessing(registration.id, imagePath, col.id, 'PROCESSING');
                            
                            // 加载图片并嵌入到Excel中
                            const imageBuffer = await loadImageAsBuffer(imagePath);
                            if (imageBuffer) {
                                const imageId = workbook.addImage({
                                    buffer: imageBuffer,
                                    extension: getImageExtension(imagePath)
                                });
                                
                                // 将图片添加到单元格
                                worksheet.addImage(imageId, {
                                    tl: { col: j, row: i + 1 }, // 从第二行开始（第一行是表头）
                                    ext: { width: 100, height: 100 }
                                });
                                
                                // 设置行高以适应图片
                                row.height = 80;
                                
                                // 记录图片处理成功
                                exportLogger.logImageProcessing(registration.id, imagePath, col.id, 'SUCCESS');
                                imageStats.success++;
                            } else {
                                // 图片加载失败
                                row.getCell(j + 1).value = '图片加载失败';
                                exportLogger.logImageProcessing(registration.id, imagePath, col.id, 'FAILED', '图片缓冲区为空');
                                imageStats.failed++;
                            }
                        } catch (error) {
                            console.warn('图片加载失败:', imagePath, error);
                            // 如果图片加载失败，显示文本
                            row.getCell(j + 1).value = '图片加载失败';
                            exportLogger.logImageProcessing(registration.id, imagePath, col.id, 'FAILED', error.message);
                            imageStats.failed++;
                        }
                    } else {
                        row.getCell(j + 1).value = '无凭证';
                        exportLogger.logImageProcessing(registration.id, imagePath || '无凭证', col.id, 'SKIPPED', '无凭证图片');
                        imageStats.skipped++;
                    }
                }
            }
        }
        
        // 生成文件名
        const now = new Date();
        const fileName = `报名数据导出_${now.getFullYear()}${(now.getMonth()+1).toString().padStart(2,'0')}${now.getDate().toString().padStart(2,'0')}_${now.getHours().toString().padStart(2,'0')}${now.getMinutes().toString().padStart(2,'0')}`;
        
        // 导出文件
        const buffer = await workbook.xlsx.writeBuffer();
        const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${fileName}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        // 记录导出完成
        exportLogger.logExportComplete('Excel', selectedRegistrations.length, `${fileName}.xlsx`, imageStats);
        
        // 输出日志汇总到控制台
        exportLogger.exportLogsToConsole();
        
        showSuccess(`Excel文件导出成功！共导出 ${selectedRegistrations.length} 条数据，图片已嵌入到Excel中。详细日志请查看控制台。`);
    } catch (error) {
        console.error('导出Excel错误:', error);
        exportLogger.logExportError('Excel', error.message);
        showError('导出Excel文件时发生错误: ' + error.message);
    }
}

// 获取列宽
function getColumnWidth(columnId) {
    switch (columnId) {
        case 'name': return 15;
        case 'phone': return 18;
        case 'education': return 20;
        case 'family': return 12;

        case 'amount': return 12;
        case 'donation': return 12;
        case 'talent': return 15;
        case 'payment': return 15;
        case 'time': return 20;
        case 'payment-screenshot-1': return 15;
        case 'payment-screenshot-2': return 15;
        case 'seat-number': return 12;
        case 'checkin-status': return 12;
        case 'checkin-time': return 20;
        default: return 15;
    }
}

// 加载图片为Buffer格式
async function loadImageAsBuffer(imagePath) {
    return new Promise((resolve, reject) => {
        if (!imagePath || imagePath === '无凭证') {
            resolve(null);
            return;
        }
        
        // 构建本地API路径，使用image-proxy.php来读取图片
        let apiPath;
        if (imagePath.includes('pages/payment-records/')) {
            // 如果路径已包含完整路径，直接使用
            apiPath = ApiUtils.buildImageProxyUrl(imagePath);
        } else {
            // 如果只是文件名，添加完整路径
            apiPath = ApiUtils.buildImageProxyUrl('pages/payment-records/' + imagePath);
        }
        
        fetch(apiPath)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.arrayBuffer();
            })
            .then(arrayBuffer => {
                resolve(arrayBuffer);
            })
            .catch(error => {
                console.warn('图片加载失败:', apiPath, error);
                resolve(null);
            });
    });
}

// 获取图片扩展名
function getImageExtension(imagePath) {
    const ext = imagePath.toLowerCase().split('.').pop();
    switch (ext) {
        case 'jpg':
        case 'jpeg':
            return 'jpeg';
        case 'png':
            return 'png';
        case 'gif':
            return 'gif';
        default:
            return 'png'; // 默认为png
    }
}



// 导出为CSV
function exportToCSV() {
    if (selectedRegistrations.length === 0) {
        showError('请先选择要导出的数据');
        return;
    }
    
    // 记录导出开始
    exportLogger.logExportStart('CSV', selectedRegistrations.length);
    
    try {
        let csvContent = '';
        
        // 获取要导出的列配置（CSV类型）
        const columnConfig = getVisibleColumnsConfig('csv');
        
        // 添加表头（只包含可见列）
        const headers = columnConfig.map(col => col.header);
        csvContent += headers.join(',') + '\n';
        
        // 图片处理统计
        const imageStats = { total: 0, success: 0, failed: 0, skipped: 0 };
        
        // 添加数据行（只包含可见列）
        selectedRegistrations.forEach(registration => {
            const row = columnConfig.map(col => {
                const value = col.getValue(registration);
                
                // 如果是凭证列，记录图片地址
                if (col.id === 'payment-screenshot-1' || col.id === 'payment-screenshot-2') {
                    const imagePath = col.id === 'payment-screenshot-1' ? 
                        registration.payment_screenshot : 
                        registration.payment_screenshot_2;
                    
                    imageStats.total++;
                    
                    if (imagePath && imagePath !== '无凭证') {
                        // 记录图片地址
                        exportLogger.logImageProcessing(registration.id, imagePath, col.id, 'SUCCESS', 'CSV导出记录图片路径');
                        imageStats.success++;
                    } else {
                        // 记录无凭证情况
                        exportLogger.logImageProcessing(registration.id, imagePath || '无凭证', col.id, 'SKIPPED', '无凭证图片');
                        imageStats.skipped++;
                    }
                }
                
                // 对于CSV，需要处理包含逗号的值
                if (typeof value === 'string' && (value.includes(',') || value.includes('"') || value.includes('\n'))) {
                    return `"${value.replace(/"/g, '""')}"`;
                }
                return value;
            });
            csvContent += row.join(',') + '\n';
        });
        
        // 创建下载链接
        const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        
        // 生成文件名
        const now = new Date();
        const fileName = `报名数据导出_${now.getFullYear()}${(now.getMonth()+1).toString().padStart(2,'0')}${now.getDate().toString().padStart(2,'0')}_${now.getHours().toString().padStart(2,'0')}${now.getMinutes().toString().padStart(2,'0')}`;
        
        link.setAttribute('download', `${fileName}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 记录导出完成
        exportLogger.logExportComplete('CSV', selectedRegistrations.length, `${fileName}.csv`, imageStats);
        
        // 输出日志汇总到控制台
        exportLogger.exportLogsToConsole();
        
        showSuccess(`CSV文件导出成功！共导出 ${selectedRegistrations.length} 条数据。详细日志请查看控制台。`);
    } catch (error) {
        console.error('导出CSV错误:', error);
        exportLogger.logExportError('CSV', error.message);
        showError('导出CSV文件时发生错误: ' + error.message);
    }
}

// 搜索导出数据
function searchExportData() {
    const keyword = document.getElementById('exportSearchInput').value.trim();
    
    if (!keyword) {
        clearExportSearch();
        return;
    }
    
    // 执行本地搜索
    filteredRegistrations = allRegistrations.filter(registration => {
        return (
            registration.name.toLowerCase().includes(keyword.toLowerCase()) ||
            registration.phone.includes(keyword) ||
            (registration.education_info && registration.education_info.toLowerCase().includes(keyword.toLowerCase())) ||
            (registration.talent_description && registration.talent_description.toLowerCase().includes(keyword.toLowerCase())) ||
            (registration.remarks && registration.remarks.toLowerCase().includes(keyword.toLowerCase()))
        );
    });
    
    isSearchMode = true;
    
    // 重新渲染表格和更新统计
    renderExportTable();
    updateExportStats();
    
    // 隐藏分页控件（搜索结果通常不分页）
    const paginationContainer = document.querySelector('.pagination-container');
    if (paginationContainer) {
        paginationContainer.style.display = 'none';
    }
    
    console.log(`搜索关键词: ${keyword}, 找到 ${filteredRegistrations.length} 条匹配数据`);
}

// 清空搜索
function clearExportSearch() {
    document.getElementById('exportSearchInput').value = '';
    isSearchMode = false;
    filteredRegistrations = [];
    
    // 重新渲染表格和更新统计
    renderExportTable();
    updateExportStats();
    
    // 显示分页控件
    const paginationContainer = document.querySelector('.pagination-container');
    if (paginationContainer) {
        paginationContainer.style.display = 'block';
    }
    
    console.log('已清空搜索，显示所有数据');
}

// 处理搜索框回车键
function handleExportSearchKeyPress(event) {
    if (event.key === 'Enter') {
        searchExportData();
    }
}



// 刷新导出数据
function refreshExportData() {
    selectedRegistrations = [];
    loadRegistrationsForExport();
}

// 显示加载状态（已禁用）
function showLoading(message = '0') {
    // 不显示加载状态
}

// 隐藏加载状态（已禁用）
function hideLoading() {
    // 不显示加载状态
}

// 显示成功消息
function showSuccess(message) {
    // 这里应该调用全局的成功提示函数
    if (typeof window.showSuccess === 'function') {
        window.showSuccess(message);
    } else {
        alert(message);
    }
}

// 显示错误消息
function showError(message) {
    // 这里应该调用全局的错误提示函数
    if (typeof window.showError === 'function') {
        window.showError(message);
    } else {
        alert(message);
    }
}

// 数据导出日志记录功能
class ExportLogger {
    constructor() {
        this.logs = [];
    }

    // 记录导出开始
    logExportStart(exportType, selectedCount) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            type: 'EXPORT_START',
            exportType,
            selectedCount,
            message: `开始导出${exportType}文件，共选择${selectedCount}条数据`
        };
        this.logs.push(logEntry);
        console.log(`[导出日志] ${logEntry.message}`, logEntry);
    }

    // 记录图片处理
    logImageProcessing(registrationId, imagePath, imageType, status, errorMessage = null) {
        const timestamp = new Date().toISOString();
        const fullImageUrl = this.getFullImageUrl(imagePath);
        
        const logEntry = {
            timestamp,
            type: 'IMAGE_PROCESSING',
            registrationId,
            imagePath,
            fullImageUrl,
            imageType, // 'payment-screenshot-1' 或 'payment-screenshot-2'
            status, // 'SUCCESS', 'FAILED', 'SKIPPED'
            errorMessage,
            message: `报名ID ${registrationId} 的${imageType === 'payment-screenshot-1' ? '凭证1' : '凭证2'}: ${status === 'SUCCESS' ? '处理成功' : status === 'FAILED' ? '处理失败' : '跳过处理'}`
        };
        
        this.logs.push(logEntry);
        console.log(`[导出日志] ${logEntry.message}`, logEntry);
        
        // 如果是失败状态，额外记录错误信息
        if (status === 'FAILED' && errorMessage) {
            console.warn(`[导出日志] 图片处理失败详情: ${errorMessage}`);
        }
    }

    // 记录导出完成
    logExportComplete(exportType, selectedCount, fileName, imageStats) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            type: 'EXPORT_COMPLETE',
            exportType,
            selectedCount,
            fileName,
            imageStats, // { total: 总图片数, success: 成功数, failed: 失败数, skipped: 跳过数 }
            message: `${exportType}文件导出完成: ${fileName}，共处理${imageStats.total}张图片（成功${imageStats.success}张，失败${imageStats.failed}张，跳过${imageStats.skipped}张）`
        };
        this.logs.push(logEntry);
        console.log(`[导出日志] ${logEntry.message}`, logEntry);
    }

    // 记录导出错误
    logExportError(exportType, errorMessage) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            type: 'EXPORT_ERROR',
            exportType,
            errorMessage,
            message: `${exportType}文件导出失败: ${errorMessage}`
        };
        this.logs.push(logEntry);
        console.error(`[导出日志] ${logEntry.message}`, logEntry);
    }

    // 获取完整的图片URL
    getFullImageUrl(imagePath) {
        if (!imagePath || imagePath === '无凭证') {
            return null;
        }
        
        // 修改：安全处理 URL，防止 XSS
        // 如果是 URL，确保它是 http 或 https 开头，并且进行了转义
        if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
            // 这里我们只是返回 URL 用于日志记录，但在 HTML 中使用时必须转义
            // 为了安全起见，我们对 URL 进行基本的清理
            return imagePath.replace(/[<>"']/g, '');
        }
        
        // 生成本地API路径，用于日志记录和访问
        if (imagePath.includes('pages/payment-records/')) {
            // 如果路径已包含完整路径，直接使用
            return ApiUtils.buildImageProxyUrl(imagePath);
        } else {
            // 如果只是文件名，添加完整路径
            return ApiUtils.buildImageProxyUrl('pages/payment-records/' + imagePath);
        }
    }

    // 获取所有日志
    getAllLogs() {
        return [...this.logs];
    }

    // 获取图片相关的日志
    getImageLogs() {
        return this.logs.filter(log => log.type === 'IMAGE_PROCESSING');
    }

    // 导出日志到控制台（格式化输出）
    exportLogsToConsole() {
        console.group('📊 数据导出日志汇总');
        
        // 按类型分组显示
        const logsByType = this.logs.reduce((acc, log) => {
            if (!acc[log.type]) acc[log.type] = [];
            acc[log.type].push(log);
            return acc;
        }, {});

        Object.keys(logsByType).forEach(type => {
            console.group(`${this.getLogTypeIcon(type)} ${type}`);
            logsByType[type].forEach(log => {
                console.log(`${log.timestamp}: ${log.message}`, log);
            });
            console.groupEnd();
        });

        // 图片处理统计
        const imageLogs = this.getImageLogs();
        if (imageLogs.length > 0) {
            console.group('🖼️ 图片处理统计');
            const imageStats = imageLogs.reduce((acc, log) => {
                acc[log.status] = (acc[log.status] || 0) + 1;
                return acc;
            }, {});
            console.log('图片处理统计:', imageStats);
            
            // 显示所有图片地址
            console.group('📋 所有图片地址列表');
            imageLogs.forEach(log => {
                if (log.fullImageUrl) {
                    console.log(`${log.registrationId} - ${log.imageType}: ${log.fullImageUrl} (${log.status})`);
                }
            });
            console.groupEnd();
            console.groupEnd();
        }

        console.groupEnd();
    }

    // 获取日志类型图标
    getLogTypeIcon(type) {
        const icons = {
            'EXPORT_START': '🚀',
            'IMAGE_PROCESSING': '🖼️',
            'EXPORT_COMPLETE': '✅',
            'EXPORT_ERROR': '❌'
        };
        return icons[type] || '📝';
    }

    // 清空日志
    clearLogs() {
        this.logs = [];
        console.log('[导出日志] 日志已清空');
    }

    // 下载日志文件
    downloadLogs() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const fileName = `export_logs_${timestamp}.json`;
        
        const logData = {
            exportTime: new Date().toISOString(),
            totalLogs: this.logs.length,
            logs: this.logs
        };
        
        const blob = new Blob([JSON.stringify(logData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        console.log(`[导出日志] 日志文件已下载: ${fileName}`);
    }
}

// 创建全局日志实例
const exportLogger = new ExportLogger();