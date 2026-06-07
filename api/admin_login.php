<?php
/**
 * 教师/管理员登录接口
 * - POST 请求，验证成功后创建 Session
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

// 使用支持跨域 Cookie 的响应头
setAuthApiHeaders('POST, OPTIONS');
handleOptionsRequest();
requireMethod('POST');

$data = parseRequestBody();
$username = trim((string)($data['username'] ?? ''));
$password = (string)($data['password'] ?? '');
if ($username === '' || $password === '') {
  jsonError('请填写用户名与密码');
}
try {
  $db = getDb();
  $stmt = $db->prepare('SELECT id, password, class FROM admins WHERE username = ? LIMIT 1');
  $stmt->bind_param('s', $username);
  $stmt->execute();
  $res = $stmt->get_result();
  $row = $res->fetch_assoc();
  $stmt->close();
  
  // 记录登录尝试日志（帮助调试）
  if (!$row) {
    logWarning('教师登录失败 - 用户不存在', ['username' => $username]);
    jsonError('用户名或密码错误', 401);
  }
  
  if (!password_verify($password, $row['password'])) {
    logWarning('教师登录失败 - 密码错误', ['username' => $username]);
    jsonError('用户名或密码错误', 401);
  }
  
  // 创建 Session 登录（管理员角色）
  sessionLogin((int)$row['id'], $username, 'admin');
  
  // 存储班级信息到 Session
  initSession();
  $_SESSION['admin_class'] = (string)($row['class'] ?? '');
  
  // 记录审计日志
  logAudit($username, AUDIT_LOGIN, null, ['adminId' => (int)$row['id'], 'role' => 'admin']);
  
  jsonSuccess(['adminId' => (int)$row['id'], 'class' => (string)($row['class'] ?? ''), 'username' => $username]);
} catch (Throwable $e) {
  jsonServerError($e, false);
}
