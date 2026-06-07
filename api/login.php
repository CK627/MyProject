<?php
/**
 * 登录与注册接口（单文件）
 * - 仅接受 POST 方法，JSON 请求体：{ action: 'login'|'register', username, password }
 * - 使用 password_hash/password_verify 进行密码哈希与校验
 * - 登录成功时创建 Session 并更新 last_login_at
 */

require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

// 使用支持跨域 Cookie 的响应头
setAuthApiHeaders('POST, OPTIONS');
handleOptionsRequest();
requireMethod('POST');

$raw = file_get_contents('php://input');
$data = json_decode($raw, true);
if (!is_array($data)) {
  // 兼容 x-www-form-urlencoded
  $data = $_POST;
}

$action = $data['action'] ?? '';
$username = trim((string)($data['username'] ?? ''));
$password = (string)($data['password'] ?? '');

if ($action !== 'login' && $action !== 'register') {
  http_response_code(400);
  echo json_encode(['error' => '缺少或非法 action 参数']);
  exit;
}
if ($username === '' || $password === '') {
  http_response_code(400);
  echo json_encode(['error' => '请填写用户名与密码']);
  exit;
}

try {
  $db = getDb();

  if ($action === 'register') {
    if (mb_strlen($username) > 64) {
      http_response_code(400);
      echo json_encode(['error' => '用户名过长']);
      exit;
    }
    // 仅允许纯数字用户名，避免在 FileUploadS 中生成中文表名
    if (!preg_match('/^[0-9]+$/', $username)) {
      http_response_code(400);
      echo json_encode(['error' => '用户名必须为纯数字']);
      exit;
    }
    if (strlen($password) < 6) {
      http_response_code(400);
      echo json_encode(['error' => '密码长度至少 6 位']);
      exit;
    }

    // 检查是否存在
    $stmt = $db->prepare('SELECT id FROM Users WHERE username = ? LIMIT 1');
    $stmt->bind_param('s', $username);
    $stmt->execute();
    $stmt->store_result();
    if ($stmt->num_rows > 0) {
      http_response_code(409);
      echo json_encode(['error' => '用户名已存在']);
      exit;
    }
    $stmt->close();

    // 写入新用户（保存密码哈希）
    $hash = password_hash($password, PASSWORD_DEFAULT);
    $stmt = $db->prepare('INSERT INTO Users (username, password) VALUES (?, ?)');
    $stmt->bind_param('ss', $username, $hash);
    $stmt->execute();
    $stmt->close();

    echo json_encode(['ok' => true, 'message' => '注册成功']);
    exit;
  }

  // 登录逻辑
  $stmt = $db->prepare('SELECT id, password FROM Users WHERE username = ? LIMIT 1');
  $stmt->bind_param('s', $username);
  $stmt->execute();
  $result = $stmt->get_result();
  $row = $result->fetch_assoc();
  $stmt->close();

  if (!$row || !password_verify($password, $row['password'])) {
    http_response_code(401);
    echo json_encode(['error' => '用户名或密码错误']);
    exit;
  }

  // 更新最近一次登录时间
  $stmt = $db->prepare('UPDATE Users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?');
  $stmt->bind_param('i', $row['id']);
  $stmt->execute();
  $stmt->close();
  
  // 创建 Session 登录
  sessionLogin((int)$row['id'], $username, 'user');
  
  // 记录审计日志
  logAudit($username, AUDIT_LOGIN, null, ['userId' => (int)$row['id']]);
  
  echo json_encode(['ok' => true, 'message' => '登录成功', 'userId' => (int)$row['id'], 'username' => $username]);
} catch (Throwable $e) {
  http_response_code(500);
  echo json_encode(['error' => '服务器内部错误', 'detail' => $e->getMessage()]);
}