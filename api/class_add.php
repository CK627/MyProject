<?php
/**
 * 添加学生到班级接口
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/db.php';

initApiRequest('POST');

$data = parseRequestBody();
$admin = trim((string)($data['adminUsername'] ?? ''));
$username = trim((string)($data['username'] ?? ''));
$name = trim((string)($data['name'] ?? ''));

$username = validateUsername($username);

try {
  // 从 FileUpload.admins 获取当前教师的班级
  $main = getDb();
  $class = '';
  if ($admin !== '') {
    $stmt = $main->prepare('SELECT `class` FROM `admins` WHERE `username` = ? LIMIT 1');
    $stmt->bind_param('s', $admin);
    $stmt->execute();
    $res = $stmt->get_result();
    $row = $res->fetch_assoc();
    $stmt->close();
    if (!$row) {
      jsonError('教师不存在', 401);
    }
    $class = trim((string)($row['class'] ?? ''));
  }
  $db = getGraduationDb();
  $stmt = $db->prepare("INSERT INTO `graduation_information`(`studentID`,`name`,`class`) VALUES(?,?,?) ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `class`=VALUES(`class`)");
  $stmt->bind_param('sss', $username, $name, $class);
  $stmt->execute();
  $stmt->close();
  jsonSuccess();
} catch (Throwable $e) {
  jsonServerError($e);
}
