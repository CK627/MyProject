<?php
/**
 * 获取学生信息接口
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';

initApiRequest('GET');

$username = isset($_GET['username']) ? trim((string)$_GET['username']) : '';
$username = validateUsername($username);

try {
  $db = getGraduationDb();
  $name = '';
  $class = '';
  $stmt = $db->prepare('SELECT `name`,`class` FROM `graduation_information` WHERE `studentID` = ? LIMIT 1');
  $stmt->bind_param('s', $username);
  $stmt->execute();
  $qr = $stmt->get_result();
  if ($qr && $qr->num_rows > 0) {
    $row = $qr->fetch_assoc();
    $name = trim((string)($row['name'] ?? ''));
    $class = trim((string)($row['class'] ?? ''));
  }
  $stmt->close();
  jsonSuccess(['username' => $username, 'name' => $name, 'class' => $class]);
} catch (Throwable $e) {
  jsonServerError($e);
}
