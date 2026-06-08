<?php
/**
 * 主页 API - 简化版
 * 福建师范大学广东校友会一周年庆典晚会系统
 * 只提供报名人数统计
 */

require_once 'database.php';

// 设置响应头
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

try {
    // 只处理GET请求
    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        http_response_code(405);
        echo json_encode([
            'success' => false,
            'error' => '仅支持GET请求'
        ], JSON_UNESCAPED_UNICODE);
        exit();
    }
    
    // 获取数据库连接
    $db = Database::getInstance();
    
    // 简单查询：获取总报名人数
    $sql = "SELECT COUNT(*) as total_registrations FROM registrations";
    $result = $db->fetchOne($sql);
    
    $totalRegistrations = $result ? intval($result['total_registrations']) : 0;
    
    // 返回结果
    echo json_encode([
        'success' => true,
        'data' => [
            'total_registrations' => $totalRegistrations
        ]
    ], JSON_UNESCAPED_UNICODE);
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => '服务器内部错误: ' . $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}
?>