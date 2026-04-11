<?php
/**
 * 会话验证API
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
        "SELECT al.admin_id, al.username, al.login_time, al.session_id, a.last_login 
         FROM admins_logs al 
         JOIN admins a ON al.admin_id = a.id 
         WHERE al.session_id = :session_id 
         AND al.login_status = 'success' 
         AND al.logout_time IS NULL 
         ORDER BY al.login_time DESC 
         LIMIT 1",
        ['session_id' => $sessionId]
    );
    
    if (!$session) {
        sendResponse(false, '无效的会话ID', null, 401);
    }
    
    // 检查会话是否过期（24小时）
    $loginTime = strtotime($session['login_time']);
    $currentTime = time();
    $sessionDuration = 24 * 60 * 60; // 24小时
    
    if (($currentTime - $loginTime) > $sessionDuration) {
        // 标记会话为已登出
        $db->update(
            'admins_logs',
            ['logout_time' => date('Y-m-d H:i:s')],
            'session_id = :session_id',
            ['session_id' => $sessionId]
        );
        
        sendResponse(false, '会话已过期，请重新登录', null, 401);
    }
    
    // 返回会话信息
    sendResponse(true, '会话有效', [
        'admin_id' => $session['admin_id'],
        'username' => $session['username'],
        'login_time' => $session['login_time'],
        'last_login' => $session['last_login'],
        'session_remaining' => $sessionDuration - ($currentTime - $loginTime)
    ]);
    
} catch (Exception $e) {
    error_log("会话验证API错误: " . $e->getMessage());
    sendResponse(false, '服务器内部错误，请稍后重试', null, 500);
}
?>