/**
 * 手机端页面状态检查模块
 * 用于检查页面是否处于维护状态，如果是则跳转到建设中页面
 */

/**
 * 检查页面状态
 * @param {string} pageName - 页面名称
 */
async function checkPageStatus(pageName) {
    try {
        // console.log(`[Mobile] 检查页面状态: ${pageName}`);
        
        // 调用API检查页面状态 - 使用正确的相对路径
        const response = await fetch(`../../api/page-status.php?page=${pageName}`);
        
        if (response.ok) {
            const contentType = response.headers.get('content-type');
            
            // 检查是否返回的是JSON
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                // console.log(`[Mobile] 页面状态响应:`, data);
                
                if (data.success) {
                    handlePageStatus(data);
                } else {
                    console.error(`[Mobile] 页面状态检查失败:`, data.message);
                    // 检查失败时默认显示页面内容
                    showPageContent();
                }
            } else {
                // 如果不是JSON响应（比如静态服务器返回PHP源码），说明PHP环境不可用
                // console.log(`[Mobile] PHP环境不可用，跳过页面状态检查`);
                showPageContent();
            }
        } else {
            console.warn(`[Mobile] API响应错误: ${response.status}`);
            showPageContent();
        }
        
    } catch (error) {
        console.error(`[Mobile] 检查页面状态时发生错误:`, error);
        // 发生错误时默认显示页面内容
        showPageContent();
    }
}

/**
 * 处理页面状态
 * @param {Object} data - 状态数据
 */
function handlePageStatus(data) {
    if (data.status === 'maintenance') {
        // console.log(`[Mobile] 页面处于维护状态，跳转到建设中页面`);
        // 跳转到手机端建设中页面
        window.location.href = 'under-construction.html';
    } else if (data.status === 'active') {
        // console.log(`[Mobile] 页面状态正常`);
        // 页面正常，显示内容
        showPageContent();
    } else {
        // 未知状态，默认显示页面内容
        console.warn(`[Mobile] 未知的页面状态:`, data.status);
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
    
    // 显示页面内容
    document.body.style.visibility = 'visible';
}

/**
 * 从当前页面URL获取页面名称
 * @returns {string} 页面名称
 */
function getCurrentPageName() {
    const path = window.location.pathname;
    const filename = path.split('/').pop();
    
    // 移除.html扩展名
    const pageName = filename.replace('.html', '');
    
    // 手机端页面名称映射到桌面端对应的页面名称
    const pageMapping = {
        'agenda': 'agenda',
        'transport': 'transport', 
        'live': 'video-live',
        'live_photos': 'photo-live',
        'seating': 'seating',
        'registration': 'registrations'  // 注意：手机端是registration，桌面端是registrations
    };
    
    return pageMapping[pageName] || pageName;
}

/**
 * 初始化页面状态检查
 * @param {string} pageName - 页面名称（可选，如果不提供则自动获取）
 */
function initPageStatusCheck(pageName) {
    // 如果没有提供页面名称，则自动获取
    if (!pageName) {
        pageName = getCurrentPageName();
    }
    
    // 排除不需要检查的页面
    const excludePages = ['under-construction', 'index', 'home'];
    
    if (!excludePages.includes(pageName)) {
        // console.log(`[Mobile] 初始化页面状态检查: ${pageName}`);
        checkPageStatus(pageName);
    } else {
        // console.log(`[Mobile] 跳过页面状态检查: ${pageName}`);
        showPageContent();
    }
}

// 页面加载完成后自动执行检查
document.addEventListener('DOMContentLoaded', function() {
    // console.log('[Mobile] 页面状态检查模块已加载');
    initPageStatusCheck();
});