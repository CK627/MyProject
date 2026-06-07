<?php
/**
 * 登出接口
 * - POST 请求销毁当前 Session
 * - 返回 { ok: true }
 */

require_once __DIR__ . '/util.php';

// 设置支持跨域 Cookie 的响应头
setAuthApiHeaders('POST, OPTIONS');
handleOptionsRequest();
requireMethod('POST');

// 获取当前用户信息用于审计日志
$user = getCurrentUser();
$username = $user ? $user['username'] : 'unknown';

// 执行登出
sessionLogout();

// 记录审计日志
if ($user) {
    logAudit($username, AUDIT_LOGOUT, null, ['userId' => $user['user_id']]);
}

jsonSuccess(['message' => '已登出']);
