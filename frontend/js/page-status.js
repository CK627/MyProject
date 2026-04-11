/**
 * 页面状态检查模块
 * 用于检查页面是否处于维护状态，如果是则跳转到建设中页面
 */

/**
 * 检查页面状态
 * @param {string} pageName - 页面名称
 */
async function checkPageStatus(pageName) {
    try {
        const response = await fetch(`../api/page-status.php?page=${pageName}`);
        
        if (response.ok) {
            const contentType = response.headers.get('content-type');
            
            // 检查是否返回的是JSON
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                
                if (data.success) {
                    handlePageStatus(data);
                } else {
                    console.error('页面状态检查失败:', data.message);
                    // 检查失败时默认显示页面内容
                    showPageContent();
                }
            } else {
                // 如果不是JSON响应（比如静态服务器返回PHP源码），说明PHP环境不可用
                // PHP环境不可用，跳过页面状态检查
                showPageContent();
            }
        } else {
            console.error('页面状态检查请求失败:', response.status);
            showPageContent();
        }
        
    } catch (error) {
        console.error('检查页面状态失败:', error);
        // 如果检查失败，默认显示页面内容
        showPageContent();
    }
}

/**
 * 处理页面状态
 * @param {Object} data - 状态数据
 */
function handlePageStatus(data) {
    if (data.status === 'maintenance') {
        // 页面处于维护状态，重定向到建设中页面
        window.location.href = '../pages/under-construction.html';
    } else if (data.status === 'active') {
        // 页面正常，显示内容
        showPageContent();
    } else {
        // 未知状态，默认显示页面内容
        console.warn('未知的页面状态:', data.status);
        showPageContent();
    }
}

/**
 * 显示页面内容
 */
function showPageContent() {
    // 移除加载遮罩（如果存在）
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
    
    // 显示主要内容
    const mainContent = document.querySelector('main, .main-content, .container');
    if (mainContent) {
        mainContent.style.display = 'block';
        mainContent.style.visibility = 'visible';
        mainContent.style.opacity = '1';
    }
    
    // 特殊处理：如果页面有维护提示和实际内容区域，则隐藏维护提示，显示实际内容
    const maintenanceNotice = document.getElementById('maintenanceNotice');
    const pageContent = document.getElementById('pageContent');
    
    if (maintenanceNotice && pageContent) {
        // 隐藏维护提示
        maintenanceNotice.style.display = 'none';
        // 显示实际页面内容
        pageContent.style.display = 'block';
    }
    
    // 显示页面内容
    document.body.style.visibility = 'visible';
}

/**
 * 初始化页面状态检查
 * @param {string} pageName - 页面名称
 */
function initPageStatusCheck(pageName) {
    // 页面加载时检查
    document.addEventListener('DOMContentLoaded', () => {
        checkPageStatus(pageName);
    });
}