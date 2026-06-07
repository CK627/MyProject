<?php
/**
 * 批量删除学生接口
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';

initApiRequest('POST');

$data = parseRequestBody();
$list = isset($data['usernames']) && is_array($data['usernames']) ? $data['usernames'] : [];

try {
  $db = getGraduationDb();
  $ok = 0;
  $fail = 0;
  foreach ($list as $u) {
    $id = trim((string)$u);
    if ($id === '' || !preg_match('/^[0-9]+$/', $id)) {
      $fail++;
      continue;
    }
    $stmt = $db->prepare('DELETE FROM `graduation_information` WHERE `studentID` = ?');
    $stmt->bind_param('s', $id);
    $stmt->execute();
    $stmt->close();
    $ok++;
  }
  jsonSuccess(['ok_count' => $ok, 'fail_count' => $fail]);
} catch (Throwable $e) {
  jsonServerError($e);
}
