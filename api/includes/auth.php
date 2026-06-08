<?php
/**
 * 登录验证模块
 * 用于后台管理页面的权限控制
 */

session_start();

/**
 * 检查管理员是否已登录
 * 未登录则跳转至登录页面
 */
function checkAuth() {
    if (!isset($_SESSION['admin_logged_in']) || $_SESSION['admin_logged_in'] !== true) {
        header('Location: login.php');
        exit;
    }
}

/**
 * 验证管理员登录凭据
 * @param string $username 用户名
 * @param string $password 密码
 * @return bool
 */
function verifyAdmin($username, $password) {
    // 实际项目中，建议改为从数据库读取，并使用 password_hash() 进行加密验证
    $adminUser = '<ADMIN_USER>';
    $adminPass = '<ADMIN_PASSWORD>';
    return ($username === $adminUser && $password === $adminPass);
}

/**
 * 设置登录 Session
 * @param string $username
 */
function setLoginSession($username) {
    $_SESSION['admin_logged_in'] = true;
    $_SESSION['admin_username'] = $username;
    $_SESSION['login_time'] = time();
}

/**
 * 销毁登录 Session
 */
function destroyLoginSession() {
    $_SESSION = [];
    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000,
            $params['path'], $params['domain'],
            $params['secure'], $params['httponly']
        );
    }
    session_destroy();
}
