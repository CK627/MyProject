<?php
/**
 * 管理员登出API
 * 福建师范大学广东校友会一周年庆典晚会系统
 */

// 引入数据库配置
require_once 'database.php';

// 设置响应头
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// 只允许POST请求
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'success' => false,
        'message' => '只允许POST请求'
    ]);
    exit();
}

/**
 * 响应函数
 */
function sendResponse($success, $message, $data = null, $code = 200) {
    http_response_code($code);
    $response = [
        'success' => $success,
        'message' => $message,
        'timestamp' => date('Y-m-d H:i:s')
    ];
    
    if ($data !== null) {
        $response['data'] = $data;
    }
    
    echo json_encode($response, JSON_UNESCAPED_UNICODE);
    exit();
}

try {
    // 获取POST数据
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        sendResponse(false, '无效的JSON数据', null, 400);
    }
    
    if (empty($data['session_id'])) {
        sendResponse(false, '会话ID不能为空', null, 400);
    }
    
    $sessionId = trim($data['session_id']);
    
    // 获取数据库连接
    $db = Database::getInstance();
    
    // 查询会话信息
    $session = $db->fetchOne(
        "SELECT admin_id, username FROM admins_logs 
         WHERE session_id = :session_id 
         AND login_status = 'success' 
         AND logout_time IS NULL",
        ['session_id' => $sessionId]
    );
    
    if (!$session) {
        sendResponse(false, '无效的会话ID或已登出', null, 400);
    }
    
    // 更新登出时间
    $affectedRows = $db->update(
        'admins_logs',
        ['logout_time' => date('Y-m-d H:i:s')],
        'session_id = :session_id AND logout_time IS NULL',
        ['session_id' => $sessionId]
    );
    
    if ($affectedRows > 0) {
        sendResponse(true, '登出成功', [
            'username' => $session['username'],
            'logout_time' => date('Y-m-d H:i:s')
        ]);
    } else {
        sendResponse(false, '登出失败，会话可能已过期', null, 400);
    }
    
} catch (Exception $e) {
    error_log("登出API错误: " . $e->getMessage());
    sendResponse(false, '服务器内部错误，请稍后重试', null, 500);
}
?>