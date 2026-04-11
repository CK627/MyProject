// 页面管理相关功能

// 显示页面管理
function managePages() {
    const clickedItem = event.target.closest('.nav-item');
    setActiveNavItem(clickedItem);
    document.getElementById('pageTitle').textContent = '页面管理';
    hideOtherContent();
    document.getElementById('pagesContent').style.display = 'block';
    
    // 加载页面状态数据
    loadPageStatuses();
    
    // 初始化服务状态
    refreshServiceStatus();
}

// 前端服务控制功能
async function toggleFrontendService() {
    const toggleInput = document.getElementById('frontend-service-toggle');
    const statusIndicator = document.getElementById('frontend-status-indicator');
    const statusText = document.getElementById('frontend-status-text');
    
    if (!toggleInput || !statusIndicator || !statusText) {
        showError('服务控制元素未找到');
        return;
    }

    const isEnabled = toggleInput.checked;
    
    try {
        // 显示加载状态
        statusIndicator.className = 'status-indicator loading';
        statusText.textContent = '操作中...';
        
        // 调用后端API执行命令
        const response = await fetch(API_CONFIG.ENDPOINTS.FRONT_CONTROL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: isEnabled ? 'open' : 'close'
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            // 更新UI状态
            updateFrontendServiceStatus(isEnabled);
            
            if (isEnabled) {
                showSuccess('前端页面权限已开放');
                console.log('前端页面权限已开放');
            } else {
                showSuccess('前端页面权限已关闭');
                console.log('前端页面权限已关闭');
            }
        } else {
            throw new Error(result.message || '操作失败');
        }
        
    } catch (error) {
        console.error('切换服务状态失败:', error);
        // 如果操作失败，恢复开关状态
        toggleInput.checked = !toggleInput.checked;
        updateFrontendServiceStatus(!isEnabled);
        showError('切换服务状态失败: ' + error.message);
    }
}

function updateFrontendServiceStatus(isRunning) {
    const statusIndicator = document.getElementById('frontend-status-indicator');
    const statusText = document.getElementById('frontend-status-text');
    
    if (statusIndicator && statusText) {
        if (isRunning) {
            statusIndicator.className = 'status-indicator running';
            statusText.textContent = '开放中';
        } else {
            statusIndicator.className = 'status-indicator stopped';
            statusText.textContent = '已关闭';
        }
    }
}

async function refreshServiceStatus() {
    try {
        // 检查服务状态 - GET请求不需要action参数
        const response = await fetch(API_CONFIG.ENDPOINTS.FRONT_CONTROL, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            const isRunning = result.status === 'open';
            const toggleInput = document.getElementById('frontend-service-toggle');
            
            if (toggleInput) {
                toggleInput.checked = isRunning;
                updateFrontendServiceStatus(isRunning);
            }
            
            showSuccess('前端页面权限状态已刷新');
        } else {
            throw new Error(result.message || '获取状态失败');
        }
        
    } catch (error) {
        console.error('刷新服务状态失败:', error);
        showError('刷新服务状态失败: ' + error.message);
    }
}

// 加载页面状态数据
async function loadPageStatuses() {
    try {
        const response = await fetch(API_CONFIG.ENDPOINTS.PAGE_MANAGER, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            updatePageStatusDisplay(result.data);
        } else {
            console.error('获取页面状态失败:', result.message);
            showError('获取页面状态失败: ' + result.message);
        }
        
    } catch (error) {
        console.error('加载页面状态失败:', error);
        showError('加载页面状态失败: ' + error.message);
    }
}

// 更新页面状态显示
function updatePageStatusDisplay(statuses) {
    // PC端页面状态更新 - 只处理我们API支持的页面
    const pcPages = [
        { key: 'registration_page_status', id: 'pc-registration' },
        { key: 'agenda_page_status', id: 'pc-agenda' },
        { key: 'photo_live_page_status', id: 'pc-photo-live' },
        { key: 'video_live_page_status', id: 'pc-video-live' },
        { key: 'transport_page_status', id: 'pc-transport' },
        { key: 'seating_page_status', id: 'pc-seating' }
    ];
    
    pcPages.forEach(page => {
        const toggleInput = document.getElementById(`${page.id}-toggle`);
        const statusIndicator = document.getElementById(`${page.id}-status-indicator`);
        const statusText = document.getElementById(`${page.id}-status-text`);
        
        if (toggleInput && statuses[page.key] !== undefined) {
            const isEnabled = statuses[page.key] == 1;
            toggleInput.checked = isEnabled;
            
            // 更新状态指示器
            if (statusIndicator && statusText) {
                if (isEnabled) {
                    statusIndicator.className = 'status-indicator running';
                    statusText.textContent = '正在运行中';
                } else {
                    statusIndicator.className = 'status-indicator stopped';
                    statusText.textContent = '正在建设中';
                }
            }
        }
    });

    // 手机端页面状态更新 - 使用正确的API字段名
    const mobilePages = [
        { key: 'mobile_registration_status', id: 'mobile-registration' },
        { key: 'mobile_agenda_status', id: 'mobile-agenda' },
        { key: 'mobile_transport_status', id: 'mobile-transport' },
        { key: 'mobile_live_status', id: 'mobile-live' },
        { key: 'mobile_live_photos_status', id: 'mobile-live-photos' },
        { key: 'mobile_seating_status', id: 'mobile-seating' }
    ];
    
    mobilePages.forEach(page => {
        const toggleInput = document.getElementById(`${page.id}-toggle`);
        const statusIndicator = document.getElementById(`${page.id}-status-indicator`);
        const statusText = document.getElementById(`${page.id}-status-text`);
        
        if (toggleInput && statuses[page.key] !== undefined) {
            const isEnabled = statuses[page.key] == 1;
            toggleInput.checked = isEnabled;
            
            // 更新状态指示器
            if (statusIndicator && statusText) {
                if (isEnabled) {
                    statusIndicator.className = 'status-indicator running';
                    statusText.textContent = '正在运行中';
                } else {
                    statusIndicator.className = 'status-indicator stopped';
                    statusText.textContent = '正在建设中';
                }
            }
        }
    });
}

async function togglePageStatus(pageId) {
    const toggleInput = document.getElementById(`${pageId}-toggle`);
    const statusIndicator = document.getElementById(`${pageId}-status-indicator`);
    const statusText = document.getElementById(`${pageId}-status-text`);
    
    if (!toggleInput) {
        showError('页面开关未找到');
        return;
    }

    const isEnabled = toggleInput.checked;
    
    // 根据页面类型确定状态值
    let newStatus;
    if (pageId.startsWith('mobile-')) {
        // 手机端页面使用 open/under_construction
        newStatus = isEnabled ? 'open' : 'under_construction';
    } else {
        // PC端页面使用 active/maintenance
        newStatus = isEnabled ? 'active' : 'maintenance';
    }
    
    // 获取数据库字段名
    const dbField = getDbFieldName(pageId);
    if (!dbField) {
        showError('页面配置错误');
        return;
    }

    try {
        const response = await fetch(API_CONFIG.ENDPOINTS.PAGE_MANAGER, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                page_key: dbField,
                status: newStatus
            })
        });

        const result = await response.json();
        
        if (result.success) {
            // 立即更新状态指示器
            if (statusIndicator && statusText) {
                if (isEnabled) {
                    statusIndicator.className = 'status-indicator running';
                    statusText.textContent = '正在运行中';
                } else {
                    statusIndicator.className = 'status-indicator stopped';
                    statusText.textContent = '正在建设中';
                }
            }
            
            const statusDescription = pageId.startsWith('mobile-') 
                ? (newStatus === 'open' ? '开启' : '建设中')
                : (newStatus === 'active' ? '启用' : '维护模式');
            
            showSuccess(`${getPageName(pageId)}状态已更新为${statusDescription}`);
        } else {
            // 如果更新失败，恢复开关状态
            toggleInput.checked = !toggleInput.checked;
            showError('更新页面状态失败: ' + result.message);
        }
        
    } catch (error) {
        console.error('更新页面状态失败:', error);
        // 如果更新失败，恢复开关状态
        toggleInput.checked = !toggleInput.checked;
        showError('更新页面状态失败: ' + error.message);
    }
}

// 获取数据库字段名
function getDbFieldName(pageId) {
    const fieldMap = {
        // PC端页面 - 匹配我们API中的字段
        'pc-registration': 'registration_page_status',
        'pc-agenda': 'agenda_page_status',
        'pc-photo-live': 'photo_live_page_status',
        'pc-video-live': 'video_live_page_status',
        'pc-transport': 'transport_page_status',
        'pc-seating': 'seating_page_status',
        
        // 手机端页面 - 已在API中实现
        'mobile-registration': 'mobile_registration_status',
        'mobile-agenda': 'mobile_agenda_status',
        'mobile-transport': 'mobile_transport_status',
        'mobile-live': 'mobile_live_status',
        'mobile-live-photos': 'mobile_live_photos_status',
        'mobile-seating': 'mobile_seating_status'
    };
    return fieldMap[pageId];
}

function getPageName(pageId) {
    const pageNames = {
        // PC端页面 - 只包含我们API支持的页面
        'pc-registration': 'PC端报名页面',
        'pc-agenda': 'PC端议程页面',
        'pc-photo-live': 'PC端照片直播',
        'pc-video-live': 'PC端视频直播',
        'pc-transport': 'PC端交通指引',
        'pc-seating': 'PC端座位信息',
        
        // 手机端页面
        'mobile-registration': '手机端报名页面',
        'mobile-agenda': '手机端议程页面',
        'mobile-transport': '手机端交通页面',
        'mobile-live': '手机端直播页面',
        'mobile-live-photos': '手机端图片直播',
        'mobile-seating': '手机端座位信息'
    };
    return pageNames[pageId] || '未知页面';
}

function togglePageSetting(settingId) {
    const toggle = document.getElementById(settingId);
    if (toggle) {
        toggle.classList.toggle('active');
        const isActive = toggle.classList.contains('active');
        showSuccess(`设置已${isActive ? '启用' : '禁用'}`);
    }
}

function savePageSettings() {
    // 获取所有设置值
    const settings = {
        siteName: document.getElementById('siteName').value,
        siteDescription: document.getElementById('siteDescription').value,
        contactEmail: document.getElementById('contactEmail').value,
        contactPhone: document.getElementById('contactPhone').value,
        enableRegistration: document.getElementById('enableRegistration').classList.contains('active'),
        enableComments: document.getElementById('enableComments').classList.contains('active'),
        enableNotifications: document.getElementById('enableNotifications').classList.contains('active'),
        maintenanceMode: document.getElementById('maintenanceMode').classList.contains('active')
    };
    
    // 这里可以发送到后端保存
    console.log('保存设置:', settings);
    showSuccess('页面设置保存成功！');
}

// 刷新页面状态
async function refreshPageStatus() {
    try {
        await loadPageStatuses();
        showSuccess('页面状态刷新成功');
    } catch (error) {
        showError('页面状态刷新失败: ' + error.message);
    }
}