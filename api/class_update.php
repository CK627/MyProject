<?php
/**
 * 更新学生信息接口
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/db.php';

initApiRequest('POST');

$data = parseRequestBody();
$admin = trim((string)($data['adminUsername'] ?? ''));
$username = trim((string)($data['username'] ?? ''));
$name = trim((string)($data['name'] ?? ''));
$class = trim((string)($data['class'] ?? ''));

$username = validateUsername($username);

try {
  if ($class === '') {
    $main = getDb();
    if ($admin !== '') {
      $stmt = $main->prepare('SELECT `class` FROM `admins` WHERE `username` = ? LIMIT 1');
      $stmt->bind_param('s', $admin);
      $stmt->execute();
      $res = $stmt->get_result();
      $row = $res->fetch_assoc();
      $stmt->close();
      if ($row) {
        $class = trim((string)($row['class'] ?? ''));
      }
    }
  }
  $db = getGraduationDb();
  $stmt2 = $db->prepare("INSERT INTO `graduation_information`(`studentID`,`name`,`class`) VALUES(?,?,?) ON DUPLICATE KEY UPDATE `name`=VALUES(`name`),`class`=VALUES(`class`)");
  $stmt2->bind_param('sss', $username, $name, $class);
  $stmt2->execute();
  $stmt2->close();
  jsonSuccess();
} catch (Throwable $e) {
  jsonServerError($e);
}
