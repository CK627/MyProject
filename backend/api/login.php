<?php
/**
 * 管理员登录API
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

/**
 * 记录登录日志
 */
function logLoginAttempt($db, $adminId, $username, $status, $failureReason = null, $sessionId = null) {
    try {
        $logData = [
            'admin_id' => $adminId,
            'username' => $username,
            'login_time' => date('Y-m-d H:i:s'),
            'ip_address' => $_SERVER['REMOTE_ADDR'] ?? 'unknown',
            'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? 'unknown',
            'login_status' => $status,
            'failure_reason' => $failureReason,
            'session_id' => $sessionId
        ];
        
        $db->insert('admins_logs', $logData);
    } catch (Exception $e) {
        error_log("记录登录日志失败: " . $e->getMessage());
    }
}

/**
 * 生成会话ID
 */
function generateSessionId() {
    return bin2hex(random_bytes(32));
}

/**
 * 验证输入数据
 */
function validateInput($data) {
    $errors = [];
    
    if (empty($data['username'])) {
        $errors[] = '用户名不能为空';
    }
    
    if (empty($data['password'])) {
        $errors[] = '密码不能为空';
    }
    
    if (strlen($data['username']) > 50) {
        $errors[] = '用户名长度不能超过50个字符';
    }
    
    return $errors;
}

try {
    // 获取POST数据
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        sendResponse(false, '无效的JSON数据', null, 400);
    }
    
    // 验证输入
    $errors = validateInput($data);
    if (!empty($errors)) {
        sendResponse(false, implode(', ', $errors), null, 400);
    }
    
    $username = trim($data['username']);
    $password = trim($data['password']);
    
    // 获取数据库连接
    $db = Database::getInstance();
    
    // 查询管理员信息
    $admin = $db->fetchOne(
        "SELECT id, username, password, last_login FROM admins WHERE username = :username",
        ['username' => $username]
    );
    
    if (!$admin) {
        // 记录失败日志（用户名不存在）
        logLoginAttempt($db, null, $username, 'failed', '用户名不存在');
        sendResponse(false, '用户名或密码错误', null, 401);
    }
    
    // 验证密码（MD5）
    $hashedPassword = md5($password);
    if ($admin['password'] !== $hashedPassword) {
        // 记录失败日志（密码错误）
        logLoginAttempt($db, $admin['id'], $username, 'failed', '密码错误');
        sendResponse(false, '用户名或密码错误', null, 401);
    }
    
    // 登录成功，生成会话ID
    $sessionId = generateSessionId();
    
    // 更新最后登录时间
    $db->update(
        'admins',
        ['last_login' => date('Y-m-d H:i:s')],
        'id = :id',
        ['id' => $admin['id']]
    );
    
    // 记录成功日志
    logLoginAttempt($db, $admin['id'], $username, 'success', null, $sessionId);
    
    // 返回成功响应
    sendResponse(true, '登录成功', [
        'admin_id' => $admin['id'],
        'username' => $admin['username'],
        'session_id' => $sessionId,
        'last_login' => $admin['last_login']
    ]);
    
} catch (Exception $e) {
    error_log("登录API错误: " . $e->getMessage());
    sendResponse(false, '服务器内部错误，请稍后重试', null, 500);
}
?>