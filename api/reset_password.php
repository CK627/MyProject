<?php
/**
 * 重置密码接口（按用户名）
 * - 仅接受 POST 方法，JSON：{ username, newPassword }
 * - 使用 password_hash 保存新密码
 * - 仅允许纯数字用户名（与注册规则一致）
 */

require __DIR__ . '/db.php';

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
  http_response_code(204);
  exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  http_response_code(405);
  echo json_encode(['error' => 'Method Not Allowed']);
  exit;
}

$raw = file_get_contents('php://input');
$data = json_decode($raw, true);
if (!is_array($data)) { $data = $_POST; }

$username = trim((string)($data['username'] ?? ''));
$newPassword = (string)($data['newPassword'] ?? '');

if ($username === '' || $newPassword === '') {
  http_response_code(400);
  echo json_encode(['error' => '请填写用户名与新密码']);
  exit;
}
if (!preg_match('/^[0-9]+$/', $username)) {
  http_response_code(400);
  echo json_encode(['error' => '用户名必须为纯数字']);
  exit;
}
if (strlen($newPassword) < 6) {
  http_response_code(400);
  echo json_encode(['error' => '新密码长度至少 6 位']);
  exit;
}

try {
  $db = getDb();
  // 检查用户是否存在
  $stmt = $db->prepare('SELECT id FROM Users WHERE username = ? LIMIT 1');
  $stmt->bind_param('s', $username);
  $stmt->execute();
  $res = $stmt->get_result();
  $user = $res->fetch_assoc();
  $stmt->close();

  if (!$user) {
    http_response_code(404);
    echo json_encode(['error' => '用户不存在']);
    exit;
  }

  // 更新密码哈希
  $hash = password_hash($newPassword, PASSWORD_DEFAULT);
  $stmt = $db->prepare('UPDATE Users SET password = ? WHERE id = ?');
  $stmt->bind_param('si', $hash, $user['id']);
  $stmt->execute();
  $stmt->close();

  echo json_encode(['ok' => true, 'message' => '密码已重置']);
} catch (Throwable $e) {
  http_response_code(500);
  echo json_encode(['error' => '服务器内部错误', 'detail' => $e->getMessage()]);
}