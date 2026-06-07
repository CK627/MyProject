<?php
/**
 * 删除学生接口
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';

initApiRequest('POST');

$data = parseRequestBody();
$username = trim((string)($data['username'] ?? ''));
$username = validateUsername($username);

try {
  $db = getGraduationDb();
  $stmt = $db->prepare('DELETE FROM `graduation_information` WHERE `studentID` = ?');
  $stmt->bind_param('s', $username);
  $stmt->execute();
  $stmt->close();
  jsonSuccess();
} catch (Throwable $e) {
  jsonServerError($e);
}
