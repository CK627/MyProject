<?php
/**
 * 管理员退出登录
 */

require_once __DIR__ . '/../includes/auth.php';

destroyLoginSession();
header('Location: login.php');
exit;
