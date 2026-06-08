<?php
/**
 * 通用函数库
 * 包含输入过滤、响应输出、文件处理等公共方法
 */

/**
 * 过滤用户输入（防止 XSS）
 * @param string $input
 * @return string
 */
function sanitizeInput($input) {
    $input = trim($input);
    $input = stripslashes($input);
    $input = htmlspecialchars($input, ENT_QUOTES, 'UTF-8');
    return $input;
}

/**
 * 输出 JSON 响应
 * @param mixed  $data    响应数据
 * @param int    $code    HTTP 状态码
 */
function jsonResponse($data, $code = 200) {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    // 允许前端跨域访问（开发环境）
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

/**
 * 成功响应
 * @param mixed  $data    数据
 * @param string $message 提示信息
 */
function successResponse($data = null, $message = '操作成功') {
    jsonResponse([
        'code'    => 0,
        'message' => $message,
        'data'    => $data
    ]);
}

/**
 * 错误响应
 * @param string $message 错误信息
 * @param int    $code    HTTP 状态码
 */
function errorResponse($message = '操作失败', $code = 400) {
    jsonResponse([
        'code'    => -1,
        'message' => $message,
        'data'    => null
    ], $code);
}

/**
 * 验证必填字段
 * @param array $fields 字段名数组
 * @param array $data   数据数组
 * @return string|null  缺失的字段名，无缺失返回 null
 */
function validateRequired($fields, $data) {
    foreach ($fields as $field) {
        if (!isset($data[$field]) || trim($data[$field]) === '') {
            return $field;
        }
    }
    return null;
}

/**
 * 处理图片上传
 * @param array  $file       $_FILES 中的文件数组
 * @param string $uploadDir  上传目标目录
 * @return string|false      成功返回文件路径，失败返回 false
 */
function handleImageUpload($file, $uploadDir = '../images/scenic/') {
    // 允许的文件类型
    $allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    // 最大文件大小 5MB
    $maxSize = 5 * 1024 * 1024;

    // 检查上传错误
    if ($file['error'] !== UPLOAD_ERR_OK) {
        return false;
    }

    // 检查文件类型
    $finfo = new finfo(FILEINFO_MIME_TYPE);
    $mimeType = $finfo->file($file['tmp_name']);
    if (!in_array($mimeType, $allowedTypes)) {
        return false;
    }

    // 检查文件大小
    if ($file['size'] > $maxSize) {
        return false;
    }

    // 确保上传目录存在
    if (!is_dir($uploadDir)) {
        mkdir($uploadDir, 0755, true);
    }

    // 生成唯一文件名
    $ext = pathinfo($file['name'], PATHINFO_EXTENSION);
    $filename = uniqid('img_') . '.' . $ext;
    $filepath = $uploadDir . $filename;

    // 移动文件
    if (move_uploaded_file($file['tmp_name'], $filepath)) {
        return $filepath;
    }

    return false;
}

/**
 * 获取分页参数
 * @return array [page, pageSize, offset]
 */
function getPagination() {
    $page = isset($_GET['page']) ? max(1, intval($_GET['page'])) : 1;
    $pageSize = isset($_GET['pageSize']) ? min(50, max(1, intval($_GET['pageSize']))) : 10;
    $offset = ($page - 1) * $pageSize;
    return [$page, $pageSize, $offset];
}
