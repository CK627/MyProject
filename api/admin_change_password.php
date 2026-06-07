<?php
/**
 * 管理员修改密码接口
 * 请求：POST JSON { username, oldPassword, newPassword }
 * 校验旧密码、长度要求，更新为新哈希
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

initApiRequest('POST');

$data = parseRequestBody();
$username = trim((string)($data['username'] ?? ''));
$oldPassword = (string)($data['oldPassword'] ?? '');
$newPassword = (string)($data['newPassword'] ?? '');

if ($username === '' || $oldPassword === '' || $newPassword === '') {
  jsonError('请填写完整的用户名与密码');
}

// 简单校验
if (strlen($newPassword) < 6) {
  jsonError('新密码长度至少 6 位');
}

try {
  $db = getDb();
  // 注意：这里查询的是 admins 表
  $stmt = $db->prepare('SELECT id, password FROM admins WHERE username = ? LIMIT 1');
  $stmt->bind_param('s', $username);
  $stmt->execute();
  $result = $stmt->get_result();
  $row = $result->fetch_assoc();
  $stmt->close();

  if (!$row || !password_verify($oldPassword, $row['password'])) {
    jsonError('当前密码不正确', 401);
  }

  $hash = password_hash($newPassword, PASSWORD_DEFAULT);
  $stmt = $db->prepare('UPDATE admins SET password = ? WHERE id = ?');
  $stmt->bind_param('si', $hash, $row['id']);
  $stmt->execute();
  $stmt->close();

  jsonSuccess(['message' => '密码已更新']);
} catch (Throwable $e) {
  jsonServerError($e);
}
