# 微信JS-SDK配置说明

## 概述
本项目的手机端交通指引页面集成了微信JS-SDK的地理位置导航功能，用户可以在微信中直接打开微信地图进行导航。

## 功能特性
- ✅ 微信地理位置导航
- ✅ 自动检测微信环境
- ✅ 降级处理（非微信环境自动切换到其他导航方式）
- ✅ 错误处理和用户提示
- ✅ 微信分享功能配置

## 配置步骤

### 1. 微信公众号配置
要使用微信JS-SDK功能，需要先在微信公众平台进行配置：

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 进入"设置与开发" -> "基本配置"
3. 获取 `AppID` 和 `AppSecret`
4. 配置 JS接口安全域名（添加您的网站域名）

### 2. 后端签名服务
微信JS-SDK需要后端生成签名，建议创建一个API接口：

```php
<?php
// 示例：weixin-signature.php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$appId = 'your_app_id';
$appSecret = 'your_app_secret';
$url = $_GET['url'] ?? '';

// 获取access_token
$tokenUrl = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={$appId}&secret={$appSecret}";
$tokenResponse = file_get_contents($tokenUrl);
$tokenData = json_decode($tokenResponse, true);
$accessToken = $tokenData['access_token'];

// 获取jsapi_ticket
$ticketUrl = "https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={$accessToken}&type=jsapi";
$ticketResponse = file_get_contents($ticketUrl);
$ticketData = json_decode($ticketResponse, true);
$ticket = $ticketData['ticket'];

// 生成签名
$timestamp = time();
$nonceStr = substr(md5(uniqid()), 0, 16);
$string = "jsapi_ticket={$ticket}&noncestr={$nonceStr}&timestamp={$timestamp}&url={$url}";
$signature = sha1($string);

echo json_encode([
    'appId' => $appId,
    'timestamp' => $timestamp,
    'nonceStr' => $nonceStr,
    'signature' => $signature
]);
?>
```

### 3. 前端配置
修改 `mobile/js/weixin-config.js` 文件：

```javascript
// 从后端获取签名信息
async function getWeChatSignature() {
    try {
        const response = await fetch(`/api/weixin-signature.php?url=${encodeURIComponent(window.location.href)}`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('获取微信签名失败:', error);
        return null;
    }
}

// 初始化微信配置
async function initWeChatConfig() {
    const signatureData = await getWeChatSignature();
    
    if (signatureData && typeof wx !== 'undefined') {
        wx.config({
            debug: false,
            appId: signatureData.appId,
            timestamp: signatureData.timestamp,
            nonceStr: signatureData.nonceStr,
            signature: signatureData.signature,
            jsApiList: ['openLocation', 'onMenuShareTimeline', 'onMenuShareAppMessage']
        });
        
        // ... 其他配置
    }
}
```

## 地理位置坐标
当前配置的地点坐标：
- **地点名称**: 笑傲江湖庄园营地
- **详细地址**: 广东省广州市黄埔区碧桂园凤凰城凤曦苑西区西北
- **纬度**: 23.102708
- **经度**: 113.370023

如需修改地点，请：
1. 访问 [腾讯位置服务](https://lbs.qq.com/getPoint/) 获取新的经纬度
2. 修改 `transport.html` 中的坐标信息

## 测试方法
1. 在微信中打开交通指引页面
2. 点击"微信导航"按钮
3. 应该会自动打开微信内置地图并显示目标位置
4. 用户可以选择导航方式（步行、驾车、公交等）

## 注意事项
- 微信JS-SDK只能在微信浏览器中使用
- 需要在微信公众平台配置安全域名
- 签名有效期为2小时，建议后端实现缓存机制
- 本地测试时可能无法正常使用，需要部署到配置的域名下

## 故障排除
1. **微信导航按钮无响应**
   - 检查是否在微信环境中打开
   - 确认JS接口安全域名配置正确
   - 查看浏览器控制台错误信息

2. **签名验证失败**
   - 检查AppID和AppSecret是否正确
   - 确认URL参数与当前页面URL一致
   - 验证时间戳是否在有效范围内

3. **地理位置无法打开**
   - 确认经纬度格式正确
   - 检查用户是否授权位置权限
   - 验证微信版本是否支持该功能