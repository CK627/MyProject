// 系统设置管理 JavaScript
console.log('SystemSettings.js 开始加载... 版本: 20250806010030');

// 全局变量声明（参考RegistrationManagement.js的方式）
let systemSettings = {};
let isLoading = false;
let checkinSettings = {};
let isCheckinLoading = false;

console.log('SystemSettings.js 全局变量已声明:', {
    systemSettings,
    isLoading,
    checkinSettings,
    isCheckinLoading
});

// 初始化系统设置
async function initializeSystemSettings() {
    console.log('初始化系统设置...');
    await loadSystemSettings();
    await loadCheckinSettings();
}

// 加载系统设置数据
async function loadSystemSettings() {
    if (isLoading) return;
    
    setSettingsLoading(true);
    
    try {
        // 只加载报名时间设置（简化后的API）
        const registrationResponse = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.SYSTEMS, { action: 'registration_times' }));

        if (!registrationResponse.ok) {
            throw new Error(`获取报名时间失败: ${registrationResponse.status}`);
        }

        const registrationData = await registrationResponse.json();
        
        // 存储数据
        systemSettings.registration = registrationData.data || registrationData;
        
        // 更新显示
        updateRegistrationTimeDisplay();
        
        // 使用全局 showToast 替代 showSettingsAlert
        // if (typeof showToast === 'function') {
        //     showToast('系统设置加载成功', 'success');
        // } else {
        //     showSettingsAlert('success', '系统设置加载成功');
        // }
        
    } catch (error) {
        console.error('加载系统设置失败:', error);
        // 使用全局 showToast 替代 showSettingsAlert
        if (typeof showToast === 'function') {
            showToast('加载系统设置失败: ' + error.message, 'error');
        } else {
            showSettingsAlert('danger', '加载系统设置失败: ' + error.message);
        }
        
        // 显示默认数据
        systemSettings.registration = {
            registration_start_time: '',
            registration_end_time: '',
            registration_page_status: 'inactive'
        };
        updateRegistrationTimeDisplay();
    } finally {
        setSettingsLoading(false);
    }
}

// 更新报名时间显示
function updateRegistrationTimeDisplay() {
    const settings = systemSettings.registration;
    
    // 转换时间格式：从 YYYY-MM-DD HH:MM:SS 转换为 YYYY-MM-DDTHH:MM
    const formatTimeForInput = (timeString) => {
        if (!timeString) return '';
        // 将空格替换为T，并移除秒数
        return timeString.replace(' ', 'T').substring(0, 16);
    };
    
    // 更新输入框
    document.getElementById('registrationStartTime').value = formatTimeForInput(settings.registration_start_time) || '';
    document.getElementById('registrationEndTime').value = formatTimeForInput(settings.registration_end_time) || '';
    
    // 更新状态显示
    const statusElement = document.getElementById('registrationStatus');
    
    // 判断报名状态：基于时间范围和is_registration_valid字段
    let isActive = false;
    if (settings.registration_start_time && settings.registration_end_time) {
        const now = new Date();
        const startTime = new Date(settings.registration_start_time);
        const endTime = new Date(settings.registration_end_time);
        isActive = now >= startTime && now <= endTime;
    }
    
    // 如果API返回了is_registration_valid字段，优先使用它
    if (settings.hasOwnProperty('is_registration_valid')) {
        isActive = settings.is_registration_valid;
    }
    
    statusElement.className = `status-indicator ${isActive ? 'status-active' : 'status-inactive'}`;
    statusElement.innerHTML = `
        <span class="status-dot"></span>
        ${isActive ? '报名开放中' : '报名已关闭'}
    `;
    
    // 更新时间信息
    updateTimeInfo();
}

// 更新所有设置显示
function updateAllSettingsDisplay() {
    // 这里可以添加其他系统设置的显示逻辑
    console.log('所有系统设置:', systemSettings.all);
}

// 更新时间信息
function updateTimeInfo() {
    const settings = systemSettings.registration;
    const timeInfoElement = document.getElementById('timeInfo');
    
    if (!settings.registration_start_time || !settings.registration_end_time) {
        timeInfoElement.innerHTML = `
            <div class="time-info-title">⚠️ 时间配置</div>
            <div class="time-info-content">请设置报名开始和结束时间</div>
        `;
        return;
    }
    
    const now = new Date();
    const startTime = new Date(settings.registration_start_time);
    const endTime = new Date(settings.registration_end_time);
    
    let statusText = '';
    let statusIcon = '';
    
    if (now < startTime) {
        statusIcon = '⏳';
        statusText = `报名将于 ${formatDateTime(startTime)} 开始`;
    } else if (now > endTime) {
        statusIcon = '⏰';
        statusText = `报名已于 ${formatDateTime(endTime)} 结束`;
    } else {
        statusIcon = '✅';
        statusText = `报名进行中，将于 ${formatDateTime(endTime)} 结束`;
    }
    
    timeInfoElement.innerHTML = `
        <div class="time-info-title">${statusIcon} 当前状态</div>
        <div class="time-info-content">
            ${statusText}<br>
            当前时间: ${formatDateTime(now)}
        </div>
    `;
}

// 保存报名时间设置
async function saveRegistrationTimes() {
    const startTime = document.getElementById('registrationStartTime').value;
    const endTime = document.getElementById('registrationEndTime').value;
    
    if (!startTime || !endTime) {
        // 使用全局 showToast 替代 showSettingsAlert
        if (typeof showToast === 'function') {
            showToast('请填写完整的报名时间', 'error');
        } else {
            showSettingsAlert('warning', '请填写完整的报名时间');
        }
        return;
    }
    
    if (new Date(startTime) >= new Date(endTime)) {
        // 使用全局 showToast 替代 showSettingsAlert
        if (typeof showToast === 'function') {
            showToast('报名开始时间必须早于结束时间', 'error');
        } else {
            showSettingsAlert('warning', '报名开始时间必须早于结束时间');
        }
        return;
    }
    
    // 转换时间格式：从 YYYY-MM-DDTHH:MM 转换为 YYYY-MM-DD HH:MM:SS
    const formatTimeForServer = (timeString) => {
        if (!timeString) return '';
        // 将 T 替换为空格，并添加秒数
        return timeString.replace('T', ' ') + ':00';
    };
    
    const formattedStartTime = formatTimeForServer(startTime);
    const formattedEndTime = formatTimeForServer(endTime);
    
    setButtonLoading('saveRegistrationBtn', true);
    
    try {
        const response = await fetch(API_CONFIG.ENDPOINTS.SYSTEMS, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'update_registration_times',
                registration_start_time: formattedStartTime,
                registration_end_time: formattedEndTime
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            // 使用全局 showToast 替代 showSettingsAlert
            if (typeof showToast === 'function') {
                showToast('报名时间设置保存成功', 'success');
            } else {
                showSettingsAlert('success', '报名时间设置保存成功');
            }
            // 重新加载设置
            await loadSystemSettings();
        } else {
            throw new Error(result.error || '保存失败');
        }
        
    } catch (error) {
        console.error('保存报名时间设置失败:', error);
        // 使用全局 showToast 替代 showSettingsAlert
        if (typeof showToast === 'function') {
            showToast('保存失败: ' + error.message, 'error');
        } else {
            showSettingsAlert('danger', '保存失败: ' + error.message);
        }
    } finally {
        setButtonLoading('saveRegistrationBtn', false);
    }
}

// 重置报名时间设置
function resetRegistrationTimes() {
    if (confirm('确定要重置报名时间设置吗？这将清空当前的时间配置。')) {
        document.getElementById('registrationStartTime').value = '';
        document.getElementById('registrationEndTime').value = '';
        updateTimeInfo();
        
        // 使用全局 showToast 替代 showSettingsAlert
        if (typeof showToast === 'function') {
            showToast('报名时间设置已重置，请记得保存', 'success'); // 使用 success 类型以显示绿色提示，或者自定义 info 类型
        } else {
            showSettingsAlert('info', '报名时间设置已重置，请记得保存');
        }
    }
}

// 刷新系统设置
async function refreshSystemSettings() {
    await loadSystemSettings();
}

// 设置加载状态
function setSettingsLoading(loading) {
    isLoading = loading;
    const overlay = document.getElementById('settingsLoadingOverlay');
    const refreshBtn = document.getElementById('refreshSettingsBtn');
    
    if (overlay) {
        overlay.style.display = loading ? 'flex' : 'none';
    }
    
    if (refreshBtn) {
        refreshBtn.disabled = loading;
        const icon = refreshBtn.querySelector('span');
        if (icon) {
            icon.style.animation = loading ? 'spin 1s linear infinite' : 'none';
        }
    }
}

// 设置按钮加载状态
function setButtonLoading(buttonId, loading) {
    const button = document.getElementById(buttonId);
    if (!button) return;
    
    button.disabled = loading;
    const icon = button.querySelector('span');
    if (icon) {
        icon.style.animation = loading ? 'spin 1s linear infinite' : 'none';
    }
}

// 显示设置提示
function showSettingsAlert(type, message) {
    const alertContainer = document.getElementById('settingsAlertContainer');
    if (!alertContainer) return;
    
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type}`;
    alertElement.textContent = message;
    
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alertElement);
    
    // 3秒后自动隐藏
    setTimeout(() => {
        if (alertElement.parentNode) {
            alertElement.parentNode.removeChild(alertElement);
        }
    }, 3000);
}

// 格式化日期时间
function formatDateTime(date) {
    if (!date) return '';
    
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}`;
}

// 获取当前时间字符串（用于设置默认值）
function getCurrentTimeString() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// 设置当前时间为开始时间
function setCurrentTimeAsStart() {
    document.getElementById('registrationStartTime').value = getCurrentTimeString();
    updateTimeInfo();
}

// 设置当前时间为结束时间
function setCurrentTimeAsEnd() {
    document.getElementById('registrationEndTime').value = getCurrentTimeString();
    updateTimeInfo();
}

// ==================== 签到时间管理功能 ====================

// 加载签到时间设置
async function loadCheckinSettings() {
    if (isCheckinLoading) return;
    
    setCheckinSettingsLoading(true);
    
    try {
        const response = await fetch(ApiUtils.buildUrl(API_CONFIG.ENDPOINTS.SYSTEMS, { action: 'checkin_times' }));

        if (!response.ok) {
            throw new Error(`获取签到时间失败: ${response.status}`);
        }

        const data = await response.json();
        
        // 存储数据
        checkinSettings = data.data || data;
        
        // 更新显示
        updateCheckinTimeDisplay();
        
        // 使用全局 showToast 替代 showSettingsAlert
        // if (typeof showToast === 'function') {
        //     showToast('签到时间设置加载成功', 'success');
        // } else {
        //     showSettingsAlert('success', '签到时间设置加载成功');
        // }
        
    } catch (error) {
        console.error('加载签到时间设置失败:', error);
        // 使用全局 showToast 替代 showSettingsAlert
        if (typeof showToast === 'function') {
            showToast('加载签到时间设置失败: ' + error.message, 'error');
        } else {
            showSettingsAlert('warning', '加载签到时间设置失败: ' + error.message);
        }
        
        // 显示默认数据
        checkinSettings = {
            checkin_start_time: '',
            checkin_end_time: ''
        };
        updateCheckinTimeDisplay();
    } finally {
        setCheckinSettingsLoading(false);
    }
}

// 更新签到时间显示
function updateCheckinTimeDisplay() {
    const settings = checkinSettings;
    
    // 转换时间格式：从 YYYY-MM-DD HH:MM:SS 转换为 YYYY-MM-DDTHH:MM
    const formatTimeForInput = (timeString) => {
        if (!timeString) return '';
        // 将空格替换为T，并移除秒数
        return timeString.replace(' ', 'T').substring(0, 16);
    };
    
    // 更新输入框
    document.getElementById('checkinStartTime').value = formatTimeForInput(settings.checkin_start_time) || '';
    document.getElementById('checkinEndTime').value = formatTimeForInput(settings.checkin_end_time) || '';
    
    // 更新状态显示
    const statusElement = document.getElementById('checkinStatus');
    
    // 判断签到状态：基于时间范围
    let isActive = false;
    if (settings.checkin_start_time && settings.checkin_end_time) {
        const now = new Date();
        const startTime = new Date(settings.checkin_start_time);
        const endTime = new Date(settings.checkin_end_time);
        isActive = now >= startTime && now <= endTime;
    }
    
    // 如果API返回了is_checkin_valid字段，优先使用它
    if (settings.hasOwnProperty('is_checkin_valid')) {
        isActive = settings.is_checkin_valid;
    }
    
    statusElement.className = `status-indicator ${isActive ? 'status-active' : 'status-inactive'}`;
    statusElement.innerHTML = `
        <span class="status-dot"></span>
        ${isActive ? '签到开放中' : '签到已关闭'}
    `;
    
    // 更新时间信息
    updateCheckinTimeInfo();
}

// 更新签到时间信息
function updateCheckinTimeInfo() {
    const settings = checkinSettings;
    const timeInfoElement = document.getElementById('checkinTimeInfo');
    
    if (!settings.checkin_start_time || !settings.checkin_end_time) {
        timeInfoElement.innerHTML = `
            <div class="time-info-title">⚠️ 签到时间配置</div>
            <div class="time-info-content">请设置签到开始和结束时间</div>
        `;
        return;
    }
    
    const now = new Date();
    const startTime = new Date(settings.checkin_start_time);
    const endTime = new Date(settings.checkin_end_time);
    
    let statusText = '';
    let statusIcon = '';
    
    if (now < startTime) {
        statusIcon = '⏳';
        statusText = `签到将于 ${formatDateTime(startTime)} 开始`;
    } else if (now > endTime) {
        statusIcon = '⏰';
        statusText = `签到已于 ${formatDateTime(endTime)} 结束`;
    } else {
        statusIcon = '✅';
        statusText = `签到进行中，将于 ${formatDateTime(endTime)} 结束`;
    }
    
    timeInfoElement.innerHTML = `
        <div class="time-info-title">${statusIcon} 当前状态</div>
        <div class="time-info-content">
            ${statusText}<br>
            当前时间: ${formatDateTime(now)}
        </div>
    `;
}

// 保存签到时间设置
async function saveCheckinTimes() {
    const startTime = document.getElementById('checkinStartTime').value;
    const endTime = document.getElementById('checkinEndTime').value;
    
    if (!startTime || !endTime) {
        // 使用全局 showToast 替代 showSettingsAlert
        if (typeof showToast === 'function') {
            showToast('请填写完整的签到时间', 'error');
        } else {
            showSettingsAlert('warning', '请填写完整的签到时间');
        }
        return;
    }
    
    if (new Date(startTime) >= new Date(endTime)) {
        // 使用全局 showToast 替代 showSettingsAlert
        if (typeof showToast === 'function') {
            showToast('签到开始时间必须早于结束时间', 'error');
        } else {
            showSettingsAlert('warning', '签到开始时间必须早于结束时间');
        }
        return;
    }
    
    // 转换时间格式：从 YYYY-MM-DDTHH:MM 转换为 YYYY-MM-DD HH:MM:SS
    const formatTimeForServer = (timeString) => {
        if (!timeString) return '';
        // 将 T 替换为空格，并添加秒数
        return timeString.replace('T', ' ') + ':00';
    };
    
    const formattedStartTime = formatTimeForServer(startTime);
    const formattedEndTime = formatTimeForServer(endTime);
    
    setButtonLoading('saveCheckinBtn', true);
    
    try {
        const response = await fetch(API_CONFIG.ENDPOINTS.SYSTEMS, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'update_checkin_times',
                checkin_start_time: formattedStartTime,
                checkin_end_time: formattedEndTime
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            // 使用全局 showToast 替代 showSettingsAlert
            if (typeof showToast === 'function') {
                showToast('签到时间设置保存成功', 'success');
            } else {
                showSettingsAlert('success', '签到时间设置保存成功');
            }
            // 重新加载设置
            await loadCheckinSettings();
        } else {
            throw new Error(result.error || '保存失败');
        }
        
    } catch (error) {
        console.error('保存签到时间设置失败:', error);
        // 使用全局 showToast 替代 showSettingsAlert
        if (typeof showToast === 'function') {
            showToast('保存失败: ' + error.message, 'error');
        } else {
            showSettingsAlert('danger', '保存失败: ' + error.message);
        }
    } finally {
        setButtonLoading('saveCheckinBtn', false);
    }
}

// 重置签到时间设置
function resetCheckinTimes() {
    if (confirm('确定要重置签到时间设置吗？这将清空当前的时间配置。')) {
        document.getElementById('checkinStartTime').value = '';
        document.getElementById('checkinEndTime').value = '';
        updateCheckinTimeInfo();
        
        // 使用全局 showToast 替代 showSettingsAlert
        if (typeof showToast === 'function') {
            showToast('签到时间设置已重置，请记得保存', 'success');
        } else {
            showSettingsAlert('info', '签到时间设置已重置，请记得保存');
        }
    }
}

// 刷新签到时间设置
async function refreshCheckinSettings() {
    await loadCheckinSettings();
}

// 设置签到设置加载状态
function setCheckinSettingsLoading(loading) {
    isCheckinLoading = loading;
    const overlay = document.getElementById('checkinSettingsLoadingOverlay');
    const refreshBtn = document.getElementById('refreshCheckinBtn');
    
    if (overlay) {
        overlay.style.display = loading ? 'flex' : 'none';
    }
    
    if (refreshBtn) {
        refreshBtn.disabled = loading;
        const icon = refreshBtn.querySelector('span');
        if (icon) {
            icon.style.animation = loading ? 'spin 1s linear infinite' : 'none';
        }
    }
}

// 设置当前时间为签到开始时间
function setCurrentTimeAsCheckinStart() {
    document.getElementById('checkinStartTime').value = getCurrentTimeString();
    updateCheckinTimeInfo();
}

// 设置当前时间为签到结束时间
function setCurrentTimeAsCheckinEnd() {
    document.getElementById('checkinEndTime').value = getCurrentTimeString();
    updateCheckinTimeInfo();
}

// 设置当前时间为结束时间
function setCurrentTimeAsEnd() {
    document.getElementById('registrationEndTime').value = getCurrentTimeString();
    updateTimeInfo();
}

// SystemSettings 命名空间，供其他模块调用
const SystemSettings = {
    initialize: initializeSystemSettings,
    loadSystemSettings: loadSystemSettings,
    loadCheckinSettings: loadCheckinSettings,
    refreshSystemSettings: refreshSystemSettings,
    refreshCheckinSettings: refreshCheckinSettings,
    saveRegistrationTimes: saveRegistrationTimes,
    saveCheckinTimes: saveCheckinTimes,
    resetRegistrationTimes: resetRegistrationTimes,
    resetCheckinTimes: resetCheckinTimes,
    setCurrentTimeAsStart: setCurrentTimeAsStart,
    setCurrentTimeAsEnd: setCurrentTimeAsEnd,
    setCurrentTimeAsCheckinStart: setCurrentTimeAsCheckinStart,
    setCurrentTimeAsCheckinEnd: setCurrentTimeAsCheckinEnd
};

// 导出到全局
window.SystemSettings = SystemSettings;

// 导出关键函数供HTML直接调用
window.loadCheckinSettings = loadCheckinSettings;
window.saveCheckinTimes = saveCheckinTimes;
window.resetCheckinTimes = resetCheckinTimes;
window.refreshCheckinSettings = refreshCheckinSettings;
window.setCurrentTimeAsCheckinStart = setCurrentTimeAsCheckinStart;
window.setCurrentTimeAsCheckinEnd = setCurrentTimeAsCheckinEnd;
window.updateCheckinTimeInfo = updateCheckinTimeInfo;
window.updateCheckinTimeDisplay = updateCheckinTimeDisplay;

// 使用Object.defineProperty创建动态绑定的全局变量
Object.defineProperty(window, 'systemSettings', {
    get: () => systemSettings,
    set: (value) => { systemSettings = value; },
    configurable: true
});

Object.defineProperty(window, 'isLoading', {
    get: () => isLoading,
    set: (value) => { isLoading = value; },
    configurable: true
});

Object.defineProperty(window, 'checkinSettings', {
    get: () => checkinSettings,
    set: (value) => { checkinSettings = value; },
    configurable: true
});

Object.defineProperty(window, 'isCheckinLoading', {
    get: () => isCheckinLoading,
    set: (value) => { isCheckinLoading = value; },
    configurable: true
});

console.log('SystemSettings.js 所有函数和变量已导出到window对象');
console.log('导出的函数:', {
    loadCheckinSettings: typeof window.loadCheckinSettings,
    saveCheckinTimes: typeof window.saveCheckinTimes,
    refreshCheckinSettings: typeof window.refreshCheckinSettings,
    setCurrentTimeAsCheckinStart: typeof window.setCurrentTimeAsCheckinStart,
    setCurrentTimeAsCheckinEnd: typeof window.setCurrentTimeAsCheckinEnd,
    updateCheckinTimeInfo: typeof window.updateCheckinTimeInfo,
    updateCheckinTimeDisplay: typeof window.updateCheckinTimeDisplay
});
console.log('导出的变量:', {
    systemSettings: typeof window.systemSettings,
    isLoading: typeof window.isLoading,
    checkinSettings: typeof window.checkinSettings,
    isCheckinLoading: typeof window.isCheckinLoading
});

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 如果当前页面是系统设置页面，则初始化
    if (document.getElementById('settingsContent') && 
        document.getElementById('settingsContent').style.display !== 'none') {
        initializeSystemSettings();
    }
});