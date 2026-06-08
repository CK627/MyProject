// 座位信息页面JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initSeatingPage();
    
    // 绑定事件监听器
    bindEventListeners();
});

/**
 * 初始化座位信息页面
 */
function initSeatingPage() {
    // 座位信息页面初始化完成
    
    // 检查URL参数中是否有手机号码或姓名
    const urlParams = new URLSearchParams(window.location.search);
    const phone = urlParams.get('phone');
    const name = urlParams.get('name');
    if (phone || name) {
        document.getElementById('searchInput').value = phone || name;
        // 自动查询
        setTimeout(() => {
            searchSeatInfo();
        }, 500);
    }
}

/**
 * 绑定事件监听器
 */
function bindEventListeners() {
    // 搜索表单提交
    const searchForm = document.getElementById('seatSearchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            searchSeatInfo();
        });
    }
    
    // 搜索输入框验证
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            // 清除之前的错误状态
            this.classList.remove('is-invalid');
            hideError();
        });
        
        // 回车键搜索
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchSeatInfo();
            }
        });
    }
}



/**
 * 搜索座位信息
 */
async function searchSeatInfo() {
    const searchInput = document.getElementById('searchInput');
    const searchValue = searchInput.value.trim();
    
    // 验证输入
    if (!searchValue) {
        showError('请输入姓名或手机号码');
        searchInput.classList.add('is-invalid');
        return;
    }
    
    // 判断输入类型（手机号或姓名）
    const isPhone = /^1[3-9]\d{9}$/.test(searchValue);
    const isName = /^[\u4e00-\u9fa5a-zA-Z\s]{2,10}$/.test(searchValue);
    
    if (!isPhone && !isName) {
        showError('请输入正确的手机号码（11位数字）或姓名（2-10个字符）');
        searchInput.classList.add('is-invalid');
        return;
    }
    
    // 显示加载状态
    showLoading();
    hideError();
    hideResult();
    
    try {
        // 构建查询参数
        const queryParam = isPhone ? `phone=${encodeURIComponent(searchValue)}` : `name=${encodeURIComponent(searchValue)}`;
        
        // 调用真实API
        const response = await fetch(`/api/seating.php?${queryParam}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            displaySeatInfo(data.data);
            showResult();
        } else {
            showError(data.message || '未找到相关座位信息，请检查姓名或手机号码是否正确');
        }
    } catch (error) {
        console.error('查询座位信息失败:', error);
        showError('查询失败，请稍后重试');
    } finally {
        hideLoading();
    }
}



/**
 * 模拟座位查询API（实际开发时替换为真实API调用）
 */
async function mockSearchSeat(phone) {
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // 模拟数据
    const mockData = {
        '13800138000': {
            success: true,
            data: {
                name: '张三',
                phone: '13800138000',
                seatNumber: 'A-001',
                isCheckedIn: false,
                checkinTime: null,
                familyMembers: [
                    {
                        name: '李四',
                        relationship: '配偶',
                        seatNumber: 'A-002'
                    }
                ]
            }
        },
        '13900139000': {
            success: true,
            data: {
                name: '王五',
                phone: '13900139000',
                seatNumber: 'B-015',
                isCheckedIn: true,
                checkinTime: '2025-01-20 18:30:00',
                familyMembers: []
            }
        }
    };
    
    return mockData[phone] || {
        success: false,
        message: '未找到相关座位信息，请检查手机号码是否正确'
    };
}

/**
 * 显示座位信息
 */
function displaySeatInfo(data) {
    // 基本信息
    document.getElementById('guestName').textContent = data.name;
    document.getElementById('guestPhone').textContent = formatPhoneDisplay(data.phone);
    document.getElementById('seatNumber').textContent = data.seat_number;
    
    // 签到状态
    updateCheckinStatus(data.is_checked_in, null);
    
    // 家属信息（只在未签到时显示）
    if (!data.is_checked_in) {
        const familyMembers = [];
        if (data.family_count > 0) {
            for (let i = 1; i <= data.family_count; i++) {
                familyMembers.push({
                    name: `家属 ${i}`,
                    relationship: '家属',
                    seatNumber: '待分配'
                });
            }
        }
        displayFamilyMembers(familyMembers);
    } else {
        // 已签到时隐藏家属信息
        displayFamilyMembers([]);
    }
}

/**
 * 格式化手机号码显示
 */
function formatPhoneDisplay(phone) {
    if (phone && phone.length === 11) {
        return phone.slice(0, 3) + '****' + phone.slice(7);
    }
    return phone;
}

/**
 * 更新签到状态
 */
function updateCheckinStatus(isCheckedIn, checkinTime) {
    const statusElement = document.getElementById('checkinStatus');
    const btnElement = document.getElementById('checkinBtn');
    
    if (isCheckedIn) {
        // 已签到状态
        statusElement.innerHTML = `
            <i class="fas fa-check-circle fa-3x text-success"></i>
            <p class="mt-2 mb-0 text-success">已签到</p>
            ${checkinTime ? `<small class="text-muted">签到时间: ${formatDateTime(checkinTime)}</small>` : ''}
        `;
        statusElement.classList.add('checked-in');
        
        btnElement.innerHTML = '<i class="fas fa-check-circle me-2"></i>已完成签到';
        btnElement.classList.remove('btn-success');
        btnElement.classList.add('btn-secondary', 'checked-in');
        btnElement.disabled = true;
    } else {
        // 未签到状态
        statusElement.innerHTML = `
            <i class="fas fa-clock fa-3x text-warning"></i>
            <p class="mt-2 mb-0 text-muted">未签到</p>
        `;
        statusElement.classList.remove('checked-in');
        
        btnElement.innerHTML = '<i class="fas fa-check-circle me-2"></i>立即签到';
        btnElement.classList.remove('btn-secondary', 'checked-in');
        btnElement.classList.add('btn-success');
        btnElement.disabled = false;
    }
}

/**
 * 显示家属信息
 */
function displayFamilyMembers(familyMembers) {
    const familySection = document.getElementById('familySection');
    const familyList = document.getElementById('familyList');
    
    if (familyMembers && familyMembers.length > 0) {
        let familyHtml = '';
        familyMembers.forEach((member, index) => {
            familyHtml += `
                <div class="family-member">
                    <div class="row align-items-center">
                        <div class="col-md-4">
                            <h6><i class="fas fa-user me-2"></i>家属 ${index + 1}</h6>
                            <p class="mb-0">${member.name}</p>
                        </div>
                        <div class="col-md-4">
                            <h6><i class="fas fa-heart me-2"></i>关系</h6>
                            <p class="mb-0">${member.relationship}</p>
                        </div>
                        <div class="col-md-4">
                            <h6><i class="fas fa-chair me-2"></i>座位号</h6>
                            <p class="mb-0 text-primary font-weight-bold">${member.seatNumber}</p>
                        </div>
                    </div>
                </div>
            `;
        });
        
        familyList.innerHTML = familyHtml;
        familySection.style.display = 'block';
    } else {
        familySection.style.display = 'none';
    }
}

/**
 * 处理签到
 */
async function handleCheckin() {
    const searchValue = document.getElementById('searchInput').value.trim();
    
    if (!searchValue) {
        showError('请先查询座位信息');
        return;
    }
    
    // 判断输入类型（手机号或姓名）
    const isPhone = /^1[3-9]\d{9}$/.test(searchValue);
    const isName = /^[\u4e00-\u9fa5a-zA-Z\s]{2,10}$/.test(searchValue);
    
    if (!isPhone && !isName) {
        showError('请输入正确的手机号码或姓名进行签到');
        return;
    }
    
    const btnElement = document.getElementById('checkinBtn');
    const originalText = btnElement.innerHTML;
    
    try {
        // 显示加载状态
        btnElement.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>签到中...';
        btnElement.disabled = true;
        
        // 调用真实签到API
        const response = await fetch('../api/seating.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'checkin',
                phone: isPhone ? searchValue : null,
                name: isName ? searchValue : null
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 更新签到状态
            updateCheckinStatus(true, data.data.checkin_time);
            
            // 隐藏家属信息
            displayFamilyMembers([]);
            
            // 显示成功模态框
            showCheckinSuccessModal(data.data);
        } else {
            showError(data.message || '签到失败，请稍后重试');
            btnElement.innerHTML = originalText;
            btnElement.disabled = false;
        }
    } catch (error) {
        console.error('签到失败:', error);
        showError('签到失败，请稍后重试');
        btnElement.innerHTML = originalText;
        btnElement.disabled = false;
    }
}

/**
 * 模拟签到API
 */
async function mockCheckin(phone) {
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // 模拟成功响应
    return {
        success: true,
        message: '签到成功'
    };
}

/**
 * 显示签到成功模态框
 */
function showCheckinSuccessModal(data) {
    // 更新模态框内容
    if (data) {
        const modalBody = document.querySelector('#checkinSuccessModal .modal-body');
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="text-center">
                    <i class="fas fa-check-circle text-success" style="font-size: 4rem;"></i>
                    <h4 class="mt-3 text-success">签到成功！</h4>
                    <p class="mt-3">
                        <strong>姓名：</strong>${data.name}<br>
                        <strong>签到时间：</strong>${formatDateTime(data.checkin_time)}
                    </p>
                </div>
            `;
        }
    }
    
    const modal = new bootstrap.Modal(document.getElementById('checkinSuccessModal'));
    modal.show();
}

/**
 * 格式化日期时间
 */
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

/**
 * 显示加载状态
 */
function showLoading() {
    document.getElementById('loadingIndicator').style.display = 'block';
}

/**
 * 隐藏加载状态
 */
function hideLoading() {
    document.getElementById('loadingIndicator').style.display = 'none';
}

/**
 * 显示结果区域
 */
function showResult() {
    document.getElementById('resultSection').style.display = 'block';
}

/**
 * 隐藏结果区域
 */
function hideResult() {
    document.getElementById('resultSection').style.display = 'none';
}

/**
 * 显示错误信息
 */
function showError(message) {
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    
    errorMessage.textContent = message;
    errorAlert.style.display = 'block';
    
    // 滚动到错误提示
    errorAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    // 3秒后自动隐藏
    setTimeout(() => {
        hideError();
    }, 5000);
}

/**
 * 隐藏错误信息
 */
function hideError() {
    document.getElementById('errorAlert').style.display = 'none';
}

/**
 * 工具函数：防抖
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 导出函数供全局使用
window.searchSeatInfo = searchSeatInfo;
window.handleCheckin = handleCheckin;