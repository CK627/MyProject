<?php
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_config.php';
require_once __DIR__ . '/ReviewHelper.php';

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); echo json_encode(['ok'=>false,'error'=>'Method Not Allowed']); exit; }

$input = file_get_contents('php://input');
$payload = json_decode($input, true);
$studentID = isset($payload['studentID']) ? trim((string)$payload['studentID']) : '';
$type = isset($payload['type']) ? trim((string)$payload['type']) : '';
$config = getGraduationConfig();

if ($studentID === '' || !preg_match('/^[0-9]+$/', $studentID)) { http_response_code(400); echo json_encode(['ok'=>false,'error'=>'学号无效']); exit; }
if (!isset($config[$type])) { http_response_code(400); echo json_encode(['ok'=>false,'error'=>'无效的文件类型']); exit; }

$conf = $config[$type];
$colPath = $conf['col_path'];
$colDlCount = $conf['col_dl_count'];
$colDlTime = $conf['col_dl_time'];
$colFinalTime = $conf['col_final_time'];

try {
  $db = getGraduationDb();
  $stmt = $db->prepare("SELECT `$colPath` FROM `graduation_information` WHERE `studentID` = ? LIMIT 1");
  $stmt->bind_param('s', $studentID);
  $stmt->execute();
  $res = $stmt->get_result();
  $row = $res ? $res->fetch_assoc() : null;
  $stmt->close();
  
  if (!$row) { http_response_code(404); echo json_encode(['ok'=>false,'error'=>'学生不存在']); exit; }
  
  $rel = trim((string)($row[$colPath] ?? ''));
  if ($rel !== '') {
    $root = realpath(__DIR__ . '/..');
    $path = $root . DIRECTORY_SEPARATOR . str_replace(['/', '\\'], DIRECTORY_SEPARATOR, $rel);
    if (is_file($path)) { @unlink($path); }
  }
  
  $reviewCol = ReviewHelper::getReviewColumn($type);
  $annoCol = ReviewHelper::getAnnotationColumn($type);
  
  // Update DB: clear path but SET REVIEW RESULT TO '不通过'
  $sql = "UPDATE `graduation_information` SET `$colPath` = '', `$colDlTime` = NULL, `$colDlCount` = 0, `$colFinalTime` = NULL";
  
  if ($reviewCol) {
      $sql .= ", `$reviewCol` = '不通过'";
  }
  // We keep the annotation if it exists, or maybe set a default '已打回' if empty?
  // Usually teacher sets annotation before or during reject. If they use the 'Reject' button in list, they might not set annotation.
  // The list view 'Reject' button (js/teacher-filestat.js) calls this API. 
  // It doesn't prompt for annotation currently.
  // Let's set a default annotation if empty, or just leave it.
  
  $sql .= " WHERE `studentID` = ?";

  $upd = $db->prepare($sql);
  $upd->bind_param('s', $studentID);
  $upd->execute();
  $upd->close();
  
  echo json_encode(['ok'=>true]);
} catch (Throwable $e) { 
  http_response_code(500); 
  echo json_encode(['ok'=>false,'error'=>'服务器内部错误']); 
}
