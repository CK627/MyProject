<?php
/**
 * 图片上传处理（后台接口）
 * POST /api/admin/upload.php
 * 参数：
 *   image - 图片文件（multipart/form-data）
 *   dir   - 可选，上传目标目录（默认 scenic）
 */

require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/functions.php';

checkAuth();

// 仅允许 POST 请求
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    errorResponse('请求方法不允许', 405);
}

// 检查文件是否存在
if (!isset($_FILES['image']) || $_FILES['image']['error'] === UPLOAD_ERR_NO_FILE) {
    errorResponse('请选择要上传的图片');
}

// 确定上传目录
$dirMap = [
    'scenic'        => '../../images/scenic/',
    'food'          => '../../images/food/',
    'accommodation' => '../../images/accommodation/',
    'transport'     => '../../images/transport/',
    'strategy'      => '../../images/strategy/',
    'index'         => '../../images/index/',
];

$dir = isset($_POST['dir']) ? sanitizeInput($_POST['dir']) : 'scenic';
$uploadDir = isset($dirMap[$dir]) ? $dirMap[$dir] : $dirMap['scenic'];

// 处理上传
$result = handleImageUpload($_FILES['image'], $uploadDir);

if ($result) {
    // 返回相对路径（前端可直接使用）
    $relativePath = str_replace('../../', '', $result);
    successResponse([
        'path' => $relativePath,
        'url'  => '/' . $relativePath
    ], '上传成功');
} else {
    errorResponse('上传失败，请检查文件格式（仅支持 jpg/png/gif/webp）和大小（最大 5MB）');
}
