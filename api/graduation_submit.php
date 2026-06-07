<?php
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_util.php';
$input = file_get_contents('php://input');
$payload = json_decode($input, true);
$username = isset($payload['username']) ? trim(strval($payload['username'])) : '';
$name = isset($payload['name']) ? trim(strval($payload['name'])) : '';
if ($username === '' || $name === '') {
  http_response_code(400);
  echo json_encode(['ok' => false, 'error' => '缺少用户名或真实姓名']);
  exit;
}
try {
  $db = getGraduationDb();
  $table = ensureGraduationTable($db, $username);
  $stmt = $db->prepare("INSERT INTO `{$table}` (`User`,`Name`) VALUES (?, ?)");
  $stmt->bind_param('ss', $username, $name);
  $stmt->execute();
  $id = $stmt->insert_id;
  $stmt->close();
  echo json_encode(['ok' => true, 'id' => $id]);
} catch (Throwable $e) {
  http_response_code(500);
  echo json_encode(['ok' => false, 'error' => '提交失败']);
}
