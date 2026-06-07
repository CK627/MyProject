<?php
/**
 * 检查会话状态接口
 * - GET/POST 请求检查当前用户是否已登录
 * - 返回 { ok: true, loggedIn: bool, user?: {...} }
 */

require_once __DIR__ . '/util.php';

// 设置支持跨域 Cookie 的响应头
setAuthApiHeaders('GET, POST, OPTIONS');
handleOptionsRequest();

$user = getCurrentUser();

if ($user) {
    $userData = [
        'userId' => $user['user_id'],
        'username' => $user['username'],
        'role' => $user['role']
    ];
    
    // 管理员返回班级信息
    if ($user['role'] === 'admin') {
        initSession();
        $userData['class'] = $_SESSION['admin_class'] ?? '';
    }
    
    jsonSuccess([
        'loggedIn' => true,
        'user' => $userData
    ]);
} else {
    jsonSuccess([
        'loggedIn' => false
    ]);
}
