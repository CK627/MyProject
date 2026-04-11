/**
 * 后端管理系统配置文件
 * 福建师范大学广东校友会一周年庆典晚会系统
 */

// API配置
const API_CONFIG = {
    // 动态获取基础URL，支持不同端口环境
    BASE_URL: (() => {
        const protocol = window.location.protocol;
        const hostname = window.location.hostname;
        const port = window.location.port;
        
        // 如果是54321端口（后台管理系统），使用相对路径
        if (port === '54321') {
            return './api';
        }
        
        // 其他情况使用相对路径
        return './api';
    })(),
    
    // API端点
    ENDPOINTS: {
        LOGIN: './api/login.php',
        LOGOUT: './api/logout.php',
        VERIFY_SESSION: './api/verify-session.php',
        DASHBOARD: './api/dashboard.php',
        CHARTS: './api/charts.php',
        REGISTRATIONS: './api/registrations.php',
        REGISTRATIONS_MODIFY: './api/registrations-modify.php',
        SEATINGS: './api/seatings.php',
        SYSTEMS: './api/systems.php',
        PAGE_MANAGER: './api/PageManager.php',
        FRONT_CONTROL: './api/front_control.php',
        IMAGE_PROXY: './api/image-proxy.php'
    }
};

// 工具函数
const ApiUtils = {
    /**
     * 构建完整的API URL
     * @param {string} endpoint - API端点
     * @param {Object} params - URL参数
     * @returns {string} 完整的URL
     */
    buildUrl(endpoint, params = {}) {
        let url = endpoint;
        
        if (Object.keys(params).length > 0) {
            const searchParams = new URLSearchParams(params);
            url += (url.includes('?') ? '&' : '?') + searchParams.toString();
        }
        
        return url;
    },

    /**
     * 构建图片代理URL
     * @param {string} imagePath - 图片路径
     * @returns {string} 图片代理URL
     */
    buildImageProxyUrl(imagePath) {
        return `${API_CONFIG.ENDPOINTS.IMAGE_PROXY}?path=${encodeURIComponent(imagePath)}`;
    },

    /**
     * 发送API请求
     * @param {string} endpoint - API端点
     * @param {Object} options - fetch选项
     * @returns {Promise} fetch Promise
     */
    async request(endpoint, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };

        const finalOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(endpoint, finalOptions);
            return response;
        } catch (error) {
            console.error('API请求失败:', error);
            throw new Error('网络连接失败，请检查网络后重试');
        }
    }
};

// 导出配置（兼容不同的模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { API_CONFIG, ApiUtils };
} else if (typeof window !== 'undefined') {
    window.API_CONFIG = API_CONFIG;
    window.ApiUtils = ApiUtils;
}