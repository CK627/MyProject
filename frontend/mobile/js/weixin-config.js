/**
 * 微信JS-SDK配置文件
 * 用于配置微信公众号相关参数
 */

// 微信JS-SDK配置函数
function initWeChatConfig() {
    // 注意：在实际使用时，需要从后端获取这些参数
    // 这里提供的是示例配置，需要根据实际的微信公众号信息进行配置
    
    if (typeof wx !== 'undefined') {
        wx.config({
            debug: false, // 开启调试模式,调用的所有api的返回值会在客户端alert出来
            appId: '', // 必填，公众号的唯一标识，需要从微信公众平台获取
            timestamp: Math.floor(Date.now() / 1000), // 必填，生成签名的时间戳
            nonceStr: generateNonceStr(), // 必填，生成签名的随机串
            signature: '', // 必填，签名，需要后端根据微信公众号的secret生成
            jsApiList: [
                'openLocation', // 查看地理位置
                'onMenuShareTimeline', // 分享到朋友圈
                'onMenuShareAppMessage', // 分享给朋友
                'onMenuShareQQ', // 分享到QQ
                'onMenuShareQZone' // 分享到QQ空间
            ]
        });

        wx.ready(function () {
            // 配置分享内容
            configWeChatShare();
        });

        wx.error(function (res) {
            // 微信JS-SDK配置失败
        });
    }
}

// 生成随机字符串
function generateNonceStr() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < 16; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

// 配置微信分享内容
function configWeChatShare() {
    const shareConfig = {
        title: '福建师范大学广东校友会一周年庆典晚会',
        desc: '诚邀您参加福建师范大学广东校友会一周年庆典晚会，地点：笑傲江湖庄园营地',
        link: window.location.href,
        imgUrl: window.location.origin + '/mobile/images/share-logo.png', // 分享图标
        success: function () {
                // 分享成功
            },
            cancel: function () {
                // 取消分享
            }
    };

    // 分享到朋友圈
    if (wx.onMenuShareTimeline) {
        wx.onMenuShareTimeline(shareConfig);
    }

    // 分享给朋友
    if (wx.onMenuShareAppMessage) {
        wx.onMenuShareAppMessage(shareConfig);
    }

    // 分享到QQ
    if (wx.onMenuShareQQ) {
        wx.onMenuShareQQ(shareConfig);
    }

    // 分享到QQ空间
    if (wx.onMenuShareQZone) {
        wx.onMenuShareQZone(shareConfig);
    }
}

// 页面加载完成后初始化微信配置
document.addEventListener('DOMContentLoaded', function() {
    initWeChatConfig();
});

// 微信环境下的特殊处理
document.addEventListener("WeixinJSBridgeReady", function() {
    initWeChatConfig();
}, false);