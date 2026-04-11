<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    exit(0);
}

// 加载微信配置
$config = include 'weixin-secret.php';
$appId = $config['appId'];
$appSecret = $config['appSecret'];

// 获取access_token
function getAccessToken($appId, $appSecret) {
    $url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={$appId}&secret={$appSecret}";
    $result = file_get_contents($url);
    $data = json_decode($result, true);
    return $data['access_token'] ?? '';
}

// 获取jsapi_ticket
function getJsApiTicket($accessToken) {
    $url = "https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={$accessToken}&type=jsapi";
    $result = file_get_contents($url);
    $data = json_decode($result, true);
    return $data['ticket'] ?? '';
}

// 生成签名
function generateSignature($jsapiTicket, $nonceStr, $timestamp, $url) {
    $string = "jsapi_ticket={$jsapiTicket}&noncestr={$nonceStr}&timestamp={$timestamp}&url={$url}";
    return sha1($string);
}

// 生成随机字符串
function generateNonceStr($length = 16) {
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    $str = "";
    for ($i = 0; $i < $length; $i++) {
        $str .= substr($chars, mt_rand(0, strlen($chars) - 1), 1);
    }
    return $str;
}

try {
    // 获取当前页面URL
    $url = $_GET['url'] ?? '';
    if (empty($url)) {
        throw new Exception('URL参数不能为空');
    }

    // 生成配置参数
    $nonceStr = generateNonceStr();
    $timestamp = time();
    
    if (empty($appSecret)) {
        throw new Exception('AppSecret未配置');
    }
    
    // 获取access_token
    $accessToken = getAccessToken($appId, $appSecret);
    if (empty($accessToken)) {
        // 检查是否是IP白名单问题
        $tokenUrl = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={$appId}&secret={$appSecret}";
        $result = file_get_contents($tokenUrl);
        $data = json_decode($result, true);
        
        if (isset($data['errcode']) && $data['errcode'] == 40164) {
            // IP白名单问题，返回降级配置
            $response = [
                'success' => true,
                'data' => [
                    'appId' => $appId,
                    'timestamp' => $timestamp,
                    'nonceStr' => $nonceStr,
                    'signature' => '',
                    'jsApiList' => ['openLocation']
                ],
                'message' => '微信配置获取成功（IP白名单限制）'
            ];
        } else {
            throw new Exception('获取access_token失败');
        }
    } else {
        $jsapiTicket = getJsApiTicket($accessToken);
        if (empty($jsapiTicket)) {
            throw new Exception('获取jsapi_ticket失败');
        }
        
        // 生成签名
        $signature = generateSignature($jsapiTicket, $nonceStr, $timestamp, $url);
        
        $response = [
            'success' => true,
            'data' => [
                'appId' => $appId,
                'timestamp' => $timestamp,
                'nonceStr' => $nonceStr,
                'signature' => $signature,
                'jsApiList' => ['openLocation']
            ],
            'message' => '微信配置获取成功'
        ];
    }
    
} catch (Exception $e) {
    $response = [
        'success' => false,
        'message' => $e->getMessage()
    ];
}

echo json_encode($response, JSON_UNESCAPED_UNICODE);
?>