/**
 * 手机端页面状态检查模块
 * 对接手机端专用API：mobile/api/page-status.php
 */

// 页面状态检查模块
const MobilePageStatusChecker = {
    
    /**
     * 检查页面状态
     * @param {string} pageName - 页面名称
     * @returns {Promise<Object>} API响应数据
     */
    async checkPageStatus(pageName) {
        try {
            // 开始检查页面状态
            
            // 手机端API路径 - 统一使用 api/page-status.php
            let apiPath;
            const currentPath = window.location.pathname;
            
            if (currentPath.includes('/mobile/pages/')) {
                // 在 pages 子目录中，需要回到上级目录
                apiPath = `../api/page-status.php?page=${pageName}`;
            } else if (currentPath.includes('/mobile/')) {
                // 在 mobile 根目录中
                apiPath = `api/page-status.php?page=${pageName}`;
            } else {
                // 其他情况，使用相对路径
                apiPath = `mobile/api/page-status.php?page=${pageName}`;
            }
            
            // API路径和响应处理
            
            const response = await fetch(apiPath);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            // API响应数据处理
            
            return data;
            
        } catch (error) {
            console.error(`[MobilePageStatus] API请求失败:`, error);
            // 返回默认的维护状态
            return {
                success: true,
                page: pageName,
                status: 'under_construction',
                note: 'API request failed, using default status'
            };
        }
    },
    
    /**
     * 处理页面状态响应
     * @param {Object} data - API响应数据
     */
    handlePageStatus(data) {
        // 处理页面状态
        
        if (!data.success) {
            console.warn(`[MobilePageStatus] API返回失败:`, data.message);
            this.showPageContent(); // 显示页面内容
            return;
        }
        
        const status = data.status;
        // 页面状态检查
        
        // 移动端页面状态值：open = 开启（正常显示），under_construction = 建设中（跳转到建设中页面）
        if (status === 'under_construction') {
            // 需要跳转到建设中页面
            this.redirectToUnderConstruction();
        } else if (status === 'open') {
            // 显示正常页面内容
            this.showPageContent();
        } else {
            // 未知状态，默认显示内容
            console.warn(`[MobilePageStatus] 未知状态: ${status}，默认显示页面内容`);
            this.showPageContent();
        }
    },
    
    /**
     * 跳转到建设中页面
     */
    redirectToUnderConstruction() {
        // 跳转到建设中页面
        
        // 根据当前页面位置确定跳转路径
        let redirectPath;
        const currentPath = window.location.pathname;
        
        if (currentPath.includes('/mobile/pages/')) {
            // 在 pages 子目录中
            redirectPath = 'under-construction.html';
        } else if (currentPath.includes('/mobile/')) {
            // 在 mobile 根目录中
            redirectPath = 'pages/under-construction.html';
        } else {
            // 其他情况
            redirectPath = 'mobile/pages/under-construction.html';
        }
        
        // 重定向路径处理
        
        window.location.href = redirectPath;
    },

    /**
     * 显示页面内容
     */
    showPageContent() {
        // 显示页面内容
        
        // 移除加载状态
        document.body.classList.remove('loading');
        
        // 显示页面内容
        const content = document.querySelector('.page-content, .container, main, body > *:not(script)');
        if (content) {
            content.style.display = '';
            content.style.visibility = 'visible';
            content.style.opacity = '1';
        }
        
        // 触发自定义事件
        document.dispatchEvent(new CustomEvent('mobilePageContentReady'));
    },
    
    /**
     * 获取当前页面名称并映射到API支持的页面名称
     * @returns {string} 页面名称
     */
    getCurrentPageName() {
        const pathname = window.location.pathname;
        const filename = pathname.split('/').pop();
        let pageName = filename.replace('.html', '');
        
        // 页面名称映射 - 将文件名映射到API支持的页面名称
        const pageNameMapping = {
            'agenda': 'agenda',
            'registration': 'registration', 
            'transport': 'transport',
            'live': 'video-live',           // live.html 对应 video-live
            'live_photos': 'photo-live',    // live_photos.html 对应 photo-live
            'seating': 'seating'            // 如果有座位页面
        };
        
        // 如果有映射，使用映射后的名称
        if (pageNameMapping[pageName]) {
            pageName = pageNameMapping[pageName];
        }
        
        // 当前页面名称处理
        return pageName;
    },
    
    /**
     * 初始化页面状态检查
     * @param {string} pageName - 可选的页面名称，如果不提供则自动获取
     */
    async initPageStatusCheck(pageName = null) {
        try {
            // 初始化页面状态检查
            
            // 如果没有提供页面名称，自动获取
            if (!pageName) {
                pageName = this.getCurrentPageName();
            }
            
            // 排除不需要检查的页面
            const excludePages = ['under-construction', 'index', 'home', 'test-page-status', 'api-test'];
            if (excludePages.includes(pageName)) {
                // 跳过页面状态检查
                this.showPageContent();
                return;
            }
            
            // 检查页面状态
            const statusData = await this.checkPageStatus(pageName);
            
            // 处理状态响应
            this.handlePageStatus(statusData);
            
        } catch (error) {
            console.error(`[MobilePageStatus] 初始化失败:`, error);
            // 出错时显示页面内容
            this.showPageContent();
        }
    }
};

// DOM加载完成后自动初始化
document.addEventListener('DOMContentLoaded', function() {
    // DOM加载完成，开始页面状态检查
    MobilePageStatusChecker.initPageStatusCheck();
});

// 向后兼容 - 保持原有的接口名称
const PageStatusChecker = MobilePageStatusChecker;

// 导出模块（如果需要）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MobilePageStatusChecker;
}