<?php
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_config.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'GET') { http_response_code(405); echo 'Method Not Allowed'; exit; }

$sid = trim((string)($_GET['studentID'] ?? ''));
$type = trim((string)($_GET['type'] ?? ''));
$config = getGraduationConfig();

if ($sid === '' || !preg_match('/^[0-9]+$/', $sid)) { http_response_code(400); echo 'Bad Request'; exit; }
if (!isset($config[$type])) { http_response_code(400); echo 'Invalid File Type'; exit; }

$conf = $config[$type];
$colPath = $conf['col_path'];
$colDlCount = $conf['col_dl_count'];
$colDlTime = $conf['col_dl_time'];

try {
  $db = getGraduationDb();
  $stmt = $db->prepare("SELECT `$colPath` FROM `graduation_information` WHERE `studentID` = ? LIMIT 1");
  $stmt->bind_param('s', $sid);
  $stmt->execute();
  $res = $stmt->get_result();
  $row = $res ? $res->fetch_assoc() : null;
  $stmt->close();
  
  if (!$row) { http_response_code(404); echo 'Not Found'; exit; }
  
  $rel = trim((string)($row[$colPath] ?? ''));
  if ($rel === '') { http_response_code(404); echo 'Not Found'; exit; }
  
  $root = realpath(__DIR__ . '/..');
  $full = $root . DIRECTORY_SEPARATOR . str_replace(['\\','/'], DIRECTORY_SEPARATOR, $rel);
  
  if (!is_file($full)) { http_response_code(404); echo 'Not Found'; exit; }
  
  // Get student name for filename
  $name = '';
  $stmtName = $db->prepare("SELECT `name` FROM `graduation_information` WHERE `studentID` = ? LIMIT 1");
  $stmtName->bind_param('s', $sid);
  $stmtName->execute();
  $resName = $stmtName->get_result();
  if ($resName && $rowName = $resName->fetch_assoc()) {
      $name = trim($rowName['name']);
  }
  $stmtName->close();

  // Construct filename: StudentID + Name + ProjectName + Extension
  $ext = pathinfo($full, PATHINFO_EXTENSION);
  $projectName = $conf['name'] ?? $type;
  // Handle empty suffix case (like labor form) where suffix is empty but we want project name
  // The user requested: LongStudentID + Name + ProjectName
  // Example: 2020001张三劳动教育周成绩认定表.docx
  $fn = $sid . $name . $projectName . '.' . $ext;
  
  $mime = 'application/octet-stream';
  if (function_exists('mime_content_type')) { $m = @mime_content_type($full); if ($m) $mime = $m; }
  
  header('Content-Type: ' . $mime);
  header('Content-Disposition: attachment; filename="' . rawurlencode($fn) . '"');
  header('Content-Length: ' . filesize($full));
  
  // 更新下载次数和时间
  $stmt2 = $db->prepare("UPDATE `graduation_information` SET `$colDlCount` = COALESCE(`$colDlCount`,0) + 1, `$colDlTime` = NOW() WHERE `studentID` = ?");
  $stmt2->bind_param('s', $sid);
  $stmt2->execute();
  $stmt2->close();
  
  readfile($full);
} catch (Throwable $e) {
  http_response_code(500);
  echo 'Internal Server Error';
}
