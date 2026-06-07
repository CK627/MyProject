<?php
/**
 * Settings 读取或初始化接口
 * - 支持 GET/POST/OPTIONS
 * - 参数：username（纯数字）
 * - 行为：
 *   1) 验证用户是否存在于 Users 表
 *   2) 查询 Settings 表中是否存在对应 `user` 记录；不存在则插入默认记录
 *   3) 返回该用户的设置（id, user, HomepageSettings 作为字符串目标）
 */

require_once __DIR__ . '/db.php';

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'GET' && $_SERVER['REQUEST_METHOD'] !== 'POST') {
  http_response_code(405);
  echo json_encode(['error' => 'Method Not Allowed']);
  exit;
}

// 读取参数
$username = '';
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
  $username = trim((string)($_GET['username'] ?? ''));
} else {
  $raw = file_get_contents('php://input');
  $data = json_decode($raw, true);
  if (!is_array($data)) { $data = $_POST; }
  $username = trim((string)($data['username'] ?? ''));
}

// 基本校验
if ($username === '' || !preg_match('/^[0-9]+$/', $username)) {
  http_response_code(400);
  echo json_encode(['error' => '用户名必须为纯数字']);
  exit;
}

try {
  $db = getDb();

  // 确认用户存在
  $stmt = $db->prepare('SELECT id FROM Users WHERE username = ? LIMIT 1');
  $stmt->bind_param('s', $username);
  $stmt->execute();
  $res = $stmt->get_result();
  $userRow = $res->fetch_assoc();
  $stmt->close();
  if (!$userRow) {
    http_response_code(401);
    echo json_encode(['error' => '未登录或用户不存在']);
    exit;
  }

  // 若为 POST 且包含 HomepageSettings(字符串)/HiddenFile/ShowHiddenFiles，则执行更新
  if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = file_get_contents('php://input');
    $payload = json_decode($raw, true);
    if (!is_array($payload)) { $payload = $_POST; }
    // 确保存在记录：没有则插入默认后再更新
    $stmt = $db->prepare('SELECT id FROM Settings WHERE `user` = ? LIMIT 1');
    $stmt->bind_param('s', $username);
    $stmt->execute();
    $res = $stmt->get_result();
    $row0 = $res->fetch_assoc();
    $stmt->close();
    if (!$row0) {
      $stmt = $db->prepare('INSERT INTO Settings (`user`, `HomepageSettings`, `HiddenFile`, `ShowHiddenFiles`) VALUES (?, "list", 1, 0)');
      $stmt->bind_param('s', $username);
      $stmt->execute();
      $stmt->close();
    }

    // 更新 HomepageSettings（可选，字符串，如 upload/list/...）
    if (array_key_exists('HomepageSettings', $payload)) {
      $target = trim((string)$payload['HomepageSettings']);
      // 简单白名单：仅允许由前端侧边栏生成的标识（例如 upload/list），长度限制 1..32
      if ($target === '' || strlen($target) > 32) { $target = 'list'; }
      $stmt = $db->prepare('UPDATE Settings SET `HomepageSettings` = ? WHERE `user` = ?');
      $stmt->bind_param('ss', $target, $username);
      $stmt->execute();
      $stmt->close();
    }

    // 更新 HiddenFile（可选）
    if (array_key_exists('HiddenFile', $payload)) {
      $v2 = $payload['HiddenFile'];
      $isTrue2 = (is_bool($v2) ? $v2 : (is_string($v2) ? strtolower($v2) === 'true' : (int)$v2 === 1));
      $hiddenInt = $isTrue2 ? 1 : 0;
      $stmt = $db->prepare('UPDATE Settings SET `HiddenFile` = ? WHERE `user` = ?');
      $stmt->bind_param('is', $hiddenInt, $username);
      $stmt->execute();
      $stmt->close();
    }

    // 更新 ShowHiddenFiles（可选）
    if (array_key_exists('ShowHiddenFiles', $payload)) {
      $v3 = $payload['ShowHiddenFiles'];
      $isTrue3 = (is_bool($v3) ? $v3 : (is_string($v3) ? strtolower($v3) === 'true' : (int)$v3 === 1));
      $showInt = $isTrue3 ? 1 : 0;
      $stmt = $db->prepare('UPDATE Settings SET `ShowHiddenFiles` = ? WHERE `user` = ?');
      $stmt->bind_param('is', $showInt, $username);
      $stmt->execute();
      $stmt->close();
    }
  }

  // 读取或初始化 Settings
  $stmt = $db->prepare('SELECT id, `user`, `HomepageSettings`, `HiddenFile`, `ShowHiddenFiles` FROM Settings WHERE `user` = ? LIMIT 1');
  $stmt->bind_param('s', $username);
  $stmt->execute();
  $res = $stmt->get_result();
  $row = $res->fetch_assoc();
  $stmt->close();

  if (!$row) {
    // 不存在则插入默认记录
    $stmt = $db->prepare('INSERT INTO Settings (`user`, `HomepageSettings`, `HiddenFile`, `ShowHiddenFiles`) VALUES (?, "list", 1, 0)');
    $stmt->bind_param('s', $username);
    $stmt->execute();
    $stmt->close();

    // 再次读取
    $stmt = $db->prepare('SELECT id, `user`, `HomepageSettings`, `HiddenFile`, `ShowHiddenFiles` FROM Settings WHERE `user` = ? LIMIT 1');
    $stmt->bind_param('s', $username);
    $stmt->execute();
    $res = $stmt->get_result();
    $row = $res->fetch_assoc();
    $stmt->close();
  }

  echo json_encode([
    'ok' => true,
    'settings' => [
      'id' => (int)$row['id'],
      'user' => $row['user'],
      'HomepageSettings' => (string)$row['HomepageSettings'],
      'HiddenFile' => ((int)$row['HiddenFile'] === 1),
      'ShowHiddenFiles' => ((int)$row['ShowHiddenFiles'] === 1)
    ]
  ]);
} catch (Throwable $e) {
  http_response_code(500);
  echo json_encode(['error' => '服务器内部错误', 'detail' => $e->getMessage()]);
}