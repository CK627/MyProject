<?php
// 简单的路由器
$request_uri = $_SERVER['REQUEST_URI'];
$path = parse_url($request_uri, PHP_URL_PATH);

// 移除查询参数
$path = strtok($path, '?');

// 处理后端API路由
if (strpos($path, '/backend/api/') !== false) {
    $api_file = str_replace('/backend/api/', 'api/', $path);
    $full_path = __DIR__ . '/' . $api_file;
    
    if (file_exists($full_path)) {
        include $full_path;
        exit;
    }
}

// 处理后端文件路由
if (strpos($path, '/backend/') !== false) {
    $backend_file = str_replace('/backend/', '', $path);
    $full_path = __DIR__ . '/' . $backend_file;
    
    if (file_exists($full_path)) {
        // 如果是PHP文件，直接包含
        if (pathinfo($full_path, PATHINFO_EXTENSION) === 'php') {
            include $full_path;
            exit;
        }
        // 其他文件类型，设置正确的Content-Type并输出
        $mime_type = mime_content_type($full_path);
        header('Content-Type: ' . $mime_type);
        readfile($full_path);
        exit;
    }
}

// 处理前端文件路由
if (strpos($path, '/frontend/') !== false) {
    $frontend_file = $_SERVER['DOCUMENT_ROOT'] . $path;
    
    if (file_exists($frontend_file)) {
        // 如果是PHP文件，直接包含
        if (pathinfo($frontend_file, PATHINFO_EXTENSION) === 'php') {
            include $frontend_file;
            exit;
        }
        // 其他文件类型，设置正确的Content-Type并输出
        $mime_type = mime_content_type($frontend_file);
        header('Content-Type: ' . $mime_type);
        readfile($frontend_file);
        exit;
    }
}

// 默认处理：尝试直接访问文件
$file_path = $_SERVER['DOCUMENT_ROOT'] . $path;
if (file_exists($file_path)) {
    if (pathinfo($file_path, PATHINFO_EXTENSION) === 'php') {
        include $file_path;
        exit;
    }
    $mime_type = mime_content_type($file_path);
    header('Content-Type: ' . $mime_type);
    readfile($file_path);
    exit;
}

// 404错误
http_response_code(404);
echo '404 Not Found';
?>