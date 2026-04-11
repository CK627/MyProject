/**
 * 设备检测和自动跳转模块
 * 检测用户设备类型，自动跳转到对应的页面
 */

class DeviceDetector {
    constructor() {
        this.userAgent = navigator.userAgent.toLowerCase();
        this.screenWidth = window.screen.width;
        this.screenHeight = window.screen.height;
        this.viewportWidth = window.innerWidth;
        this.viewportHeight = window.innerHeight;
        this.pixelRatio = window.devicePixelRatio || 1;
        
        // 初始化检测
        this.init();
    }

    /**
     * 初始化设备检测
     */
    init() {
        // console.log('设备检测模块初始化');
        // console.log('用户代理:', this.userAgent);
        // console.log('屏幕尺寸:', this.screenWidth + 'x' + this.screenHeight);
        // console.log('视口尺寸:', this.viewportWidth + 'x' + this.viewportHeight);
        // console.log('像素比:', this.pixelRatio);
        
        // 检查是否需要跳转
        this.checkAndRedirect();
    }

    /**
     * 检测是否为移动设备
     */
    isMobileDevice() {
        // 检查用户代理字符串
        const mobileKeywords = [
            'mobile', 'android', 'iphone', 'ipad', 'ipod', 
            'blackberry', 'windows phone', 'opera mini',
            'iemobile', 'mobile safari'
        ];
        
        const isMobileUA = mobileKeywords.some(keyword => 
            this.userAgent.includes(keyword)
        );
        
        // 检查屏幕尺寸（移动设备通常屏幕较小）
        const isMobileScreen = this.screenWidth <= 768 || this.viewportWidth <= 768;
        
        // 检查触摸支持
        const hasTouchSupport = 'ontouchstart' in window || 
                               navigator.maxTouchPoints > 0 || 
                               navigator.msMaxTouchPoints > 0;
        
        // console.log('移动设备UA检测:', isMobileUA);
        // console.log('移动设备屏幕检测:', isMobileScreen);
        // console.log('触摸支持检测:', hasTouchSupport);
        
        // 综合判断：满足任意两个条件即认为是移动设备
        const conditions = [isMobileUA, isMobileScreen, hasTouchSupport];
        const mobileConditionCount = conditions.filter(Boolean).length;
        
        return mobileConditionCount >= 2;
    }

    /**
     * 检测具体设备类型
     */
    getDeviceType() {
        if (this.userAgent.includes('ipad')) {
            return 'tablet';
        }
        
        if (this.userAgent.includes('iphone')) {
            return 'mobile';
        }
        
        if (this.userAgent.includes('android')) {
            if (this.screenWidth >= 768 && this.screenHeight >= 1024) {
                return 'tablet';
            }
            return 'mobile';
        }
        
        if (this.isMobileDevice()) {
            return 'mobile';
        }
        
        return 'desktop';
    }

    /**
     * 获取设备详细信息
     */
    getDeviceInfo() {
        const deviceType = this.getDeviceType();
        
        return {
            type: deviceType,
            isMobile: deviceType === 'mobile',
            isTablet: deviceType === 'tablet',
            isDesktop: deviceType === 'desktop',
            screenWidth: this.screenWidth,
            screenHeight: this.screenHeight,
            viewportWidth: this.viewportWidth,
            viewportHeight: this.viewportHeight,
            pixelRatio: this.pixelRatio,
            userAgent: this.userAgent,
            orientation: this.getOrientation(),
            browser: this.getBrowser(),
            os: this.getOS()
        };
    }

    /**
     * 获取屏幕方向
     */
    getOrientation() {
        if (screen.orientation) {
            return screen.orientation.type;
        }
        
        if (this.viewportWidth > this.viewportHeight) {
            return 'landscape';
        }
        
        return 'portrait';
    }

    /**
     * 获取浏览器类型
     */
    getBrowser() {
        if (this.userAgent.includes('chrome')) return 'chrome';
        if (this.userAgent.includes('firefox')) return 'firefox';
        if (this.userAgent.includes('safari') && !this.userAgent.includes('chrome')) return 'safari';
        if (this.userAgent.includes('edge')) return 'edge';
        if (this.userAgent.includes('opera')) return 'opera';
        return 'unknown';
    }

    /**
     * 获取操作系统
     */
    getOS() {
        if (this.userAgent.includes('windows')) return 'windows';
        if (this.userAgent.includes('mac')) return 'macos';
        if (this.userAgent.includes('linux')) return 'linux';
        if (this.userAgent.includes('android')) return 'android';
        if (this.userAgent.includes('ios') || this.userAgent.includes('iphone') || this.userAgent.includes('ipad')) return 'ios';
        return 'unknown';
    }

    /**
     * 检查并执行跳转
     */
    checkAndRedirect() {
        const deviceInfo = this.getDeviceInfo();
        
        // console.log('设备信息:', deviceInfo);
        
        // 检查当前页面路径
        const currentPath = window.location.pathname;
        const isInMobileFolder = currentPath.includes('/mobile/');
        
        // 如果是移动设备但不在移动端页面，则跳转到移动端
        if ((deviceInfo.isMobile || deviceInfo.isTablet) && !isInMobileFolder) {
            // console.log('检测到移动设备，准备跳转到移动端页面');
            this.redirectToMobile();
            return;
        }
        
        // 如果是桌面设备但在移动端页面，则跳转到桌面端
        if (deviceInfo.isDesktop && isInMobileFolder) {
            // console.log('检测到桌面设备，准备跳转到桌面端页面');
            this.redirectToDesktop();
            return;
        }
        
        // console.log('设备类型匹配当前页面，无需跳转');
        
        // 存储设备信息到本地存储
        this.saveDeviceInfo(deviceInfo);
    }

    /**
     * 跳转到移动端页面
     */
    redirectToMobile() {
        // 显示跳转提示
        this.showRedirectNotification('正在跳转到移动端页面...', () => {
            const mobileUrl = this.getMobileUrl();
            // console.log('跳转到移动端:', mobileUrl);
            window.location.href = mobileUrl;
        });
    }

    /**
     * 跳转到桌面端页面
     */
    redirectToDesktop() {
        // 显示跳转提示
        this.showRedirectNotification('正在跳转到桌面端页面...', () => {
            const desktopUrl = this.getDesktopUrl();
            // console.log('跳转到桌面端:', desktopUrl);
            window.location.href = desktopUrl;
        });
    }

    /**
     * 获取移动端URL
     */
    getMobileUrl() {
        const currentPath = window.location.pathname;
        const currentSearch = window.location.search;
        
        // 如果已经在移动端，直接返回当前URL
        if (currentPath.includes('/mobile/')) {
            return window.location.href;
        }
        
        // 构建移动端URL
        const basePath = currentPath.replace(/\/[^\/]*$/, '');
        return `${basePath}/mobile/index.html${currentSearch}`;
    }

    /**
     * 获取桌面端URL
     */
    getDesktopUrl() {
        const currentPath = window.location.pathname;
        const currentSearch = window.location.search;
        
        // 如果不在移动端，直接返回根目录
        if (!currentPath.includes('/mobile/')) {
            return '/';
        }
        
        // 构建桌面端URL
        const basePath = currentPath.replace(/\/mobile\/.*$/, '');
        return `${basePath}/index.html${currentSearch}`;
    }

    /**
     * 显示跳转通知
     */
    showRedirectNotification(message, callback) {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 20px 30px;
            border-radius: 10px;
            font-size: 16px;
            z-index: 10000;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        `;
        notification.textContent = message;
        
        // 添加到页面
        document.body.appendChild(notification);
        
        // 1.5秒后执行跳转
        setTimeout(() => {
            document.body.removeChild(notification);
            callback();
        }, 1500);
    }

    /**
     * 保存设备信息到本地存储
     */
    saveDeviceInfo(deviceInfo) {
        try {
            localStorage.setItem('deviceInfo', JSON.stringify(deviceInfo));
            localStorage.setItem('lastDetectionTime', Date.now().toString());
        } catch (error) {
            console.warn('无法保存设备信息到本地存储:', error);
        }
    }

    /**
     * 从本地存储获取设备信息
     */
    static getStoredDeviceInfo() {
        try {
            const deviceInfo = localStorage.getItem('deviceInfo');
            const lastDetectionTime = localStorage.getItem('lastDetectionTime');
            
            if (deviceInfo && lastDetectionTime) {
                const timeDiff = Date.now() - parseInt(lastDetectionTime);
                // 如果检测时间超过1小时，重新检测
                if (timeDiff < 3600000) {
                    return JSON.parse(deviceInfo);
                }
            }
        } catch (error) {
            console.warn('无法从本地存储获取设备信息:', error);
        }
        
        return null;
    }
}

// 页面加载完成后自动执行设备检测
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否有存储的设备信息
    const storedInfo = DeviceDetector.getStoredDeviceInfo();
    
    if (storedInfo) {
        // console.log('使用存储的设备信息:', storedInfo);
    }
    
    // 创建设备检测器实例
    window.deviceDetector = new DeviceDetector();
});

// 监听屏幕方向变化
window.addEventListener('orientationchange', function() {
    setTimeout(() => {
        if (window.deviceDetector) {
            // console.log('屏幕方向改变，重新检测设备信息');
            window.deviceDetector.checkAndRedirect();
        }
    }, 500);
});

// 监听窗口大小变化
window.addEventListener('resize', function() {
    if (window.deviceDetector) {
        const deviceInfo = window.deviceDetector.getDeviceInfo();
        // console.log('窗口大小改变，当前设备信息:', deviceInfo);
    }
});