<?php
require_once __DIR__ . '/db_graduation.php';
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'GET') { http_response_code(405); echo 'Method Not Allowed'; exit; }
$cls = trim((string)($_GET['class'] ?? ''));
if ($cls === '') { http_response_code(400); echo 'Bad Request'; exit; }
try {
  $db = getGraduationDb();
  $stmt = $db->prepare('SELECT `studentID`,`name` FROM `graduation_information` WHERE `class` = ?');
  $stmt->bind_param('s', $cls);
  $stmt->execute();
  $res = $stmt->get_result();
  $students = [];
  while ($res && ($row = $res->fetch_assoc())) { $students[] = [(string)($row['studentID'] ?? ''),(string)($row['name'] ?? '')]; }
  $stmt->close();
  $root = realpath(__DIR__ . '/..');
  if (!class_exists('ZipArchive')) { http_response_code(500); echo 'Internal Server Error'; exit; }
  $tmp = tempnam(sys_get_temp_dir(), 'zip_');
  $zipPath = $tmp . '.zip';
  @unlink($tmp);
  $zip = new ZipArchive();
  if ($zip->open($zipPath, ZipArchive::CREATE) !== true) { http_response_code(500); echo 'Internal Server Error'; exit; }

  $safeClass = preg_replace('/[\/\\:*?"<>|]+/', '', $cls);
  if ($safeClass === '') { $safeClass = 'class'; }
  $zip->addEmptyDir($safeClass);
  $isHiddenSeg = function (string $seg): bool { return $seg !== '' && $seg[0] === '.'; };
  $pathHasHidden = function (string $path) use ($isHiddenSeg): bool {
    $path = str_replace('\\', '/', $path);
    foreach (explode('/', trim($path, '/')) as $seg) {
      if ($seg === '.chunks') return true;
      if ($isHiddenSeg($seg)) return true;
    }
    return false;
  };

  foreach ($students as [$sid, $name]) {
    if ($sid === '') continue;
    $safeName = preg_replace('/[\/\\:*?"<>|]+/', '', $name);
    $studentLabel = $sid . $safeName;
    $studentPrefix = $safeClass . '/' . $studentLabel;
    $base = $root . DIRECTORY_SEPARATOR . 'FileUploadGraduationSubmission' . DIRECTORY_SEPARATOR . $sid;
    if (!is_dir($base)) { $zip->addEmptyDir($studentPrefix); continue; }
    $zip->addEmptyDir($studentPrefix);
    $addDir = function (string $abs, string $localBase) use (&$zip, &$addDir, $pathHasHidden) {
      $entries = @scandir($abs);
      if ($entries === false) return;
      foreach ($entries as $entry) {
        if ($entry === '.' || $entry === '..') continue;
        if ($pathHasHidden($entry)) continue;
        $absPath = $abs . DIRECTORY_SEPARATOR . $entry;
        $localPath = $localBase . '/' . $entry;
        if (is_dir($absPath)) { $zip->addEmptyDir($localPath); $addDir($absPath, $localPath); }
        else if (is_file($absPath)) { $zip->addFile($absPath, $localPath); }
      }
    };
    $addDir($base, $studentPrefix);
  }
  $zip->close();
  $name = $cls . '.zip';
  if (function_exists('set_time_limit')) { @set_time_limit(0); }
  while (ob_get_level()) { @ob_end_clean(); }
  header('Content-Description: File Transfer');
  header('Content-Type: application/zip');
  header('Content-Disposition: attachment; filename="' . rawurlencode($name) . '"');
  header('Content-Length: ' . filesize($zipPath));
  header('Cache-Control: no-cache');
  $fp = fopen($zipPath, 'rb');
  if ($fp) { while (!feof($fp)) { echo fread($fp, 8192); } fclose($fp); }
  @unlink($zipPath);
} catch (Throwable $e) { http_response_code(500); echo 'Internal Server Error'; }
