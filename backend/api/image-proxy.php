<?php
/**
 * 图片代理API - 用于获取前端目录中的付款凭证图片
 * Image Proxy API - For accessing payment screenshot images from frontend directory
 */

// 设置CORS头
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');
header('Access-Control-Allow-Headers: Content-Type');

// 获取图片路径参数
$imagePath = $_GET['path'] ?? '';

// 解码URL编码的路径
$imagePath = urldecode($imagePath);

if (empty($imagePath)) {
    http_response_code(400);
    echo json_encode(['error' => '缺少图片路径参数']);
    exit;
}

// 安全检查：防止路径遍历攻击
if (strpos($imagePath, '..') !== false || strpos($imagePath, '/') === 0) {
    http_response_code(403);
    echo json_encode(['error' => '非法路径']);
    exit;
}

// 构建完整的图片文件路径
$frontendDir = dirname(__DIR__, 2) . '/frontend/';
$fullImagePath = $frontendDir . $imagePath;

// 如果在桌面端目录找不到文件，尝试在移动端目录查找
if (!file_exists($fullImagePath)) {
    // 检查是否为 pages/payment-records/ 路径
    if (strpos($imagePath, 'pages/payment-records/') === 0) {
        // 尝试在移动端目录查找
        $mobileImagePath = $frontendDir . 'mobile/' . $imagePath;
        if (file_exists($mobileImagePath)) {
            $fullImagePath = $mobileImagePath;
        } else {
            http_response_code(404);
            echo json_encode(['error' => '图片文件不存在']);
            exit;
        }
    } else {
        http_response_code(404);
        echo json_encode(['error' => '图片文件不存在']);
        exit;
    }
}

// 检查是否为图片文件
// 抑制 getimagesize 可能产生的警告
$imageInfo = @getimagesize($fullImagePath);
if ($imageInfo === false) {
    // 尝试通过文件扩展名判断
    $ext = strtolower(pathinfo($fullImagePath, PATHINFO_EXTENSION));
    $validExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'];
    
    if (!in_array($ext, $validExts)) {
        http_response_code(400);
        echo json_encode(['error' => '不是有效的图片文件']);
        exit;
    }
    
    // 如果 getimagesize 失败但扩展名合法，根据扩展名设置 MIME 类型
    $mimeTypes = [
        'jpg' => 'image/jpeg',
        'jpeg' => 'image/jpeg',
        'png' => 'image/png',
        'gif' => 'image/gif',
        'webp' => 'image/webp',
        'bmp' => 'image/bmp'
    ];
    $mimeType = $mimeTypes[$ext] ?? 'application/octet-stream';
} else {
    $mimeType = $imageInfo['mime'];
}

// 设置适当的Content-Type头
header('Content-Type: ' . $mimeType);
header('Content-Length: ' . filesize($fullImagePath));

// 设置缓存头
header('Cache-Control: public, max-age=3600');
header('Expires: ' . gmdate('D, d M Y H:i:s', time() + 3600) . ' GMT');

// 输出图片内容
readfile($fullImagePath);
exit;
?>