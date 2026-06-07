<?php
require_once __DIR__ . '/db_graduation.php';
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'GET') { http_response_code(405); echo 'Method Not Allowed'; exit; }
$sid = trim((string)($_GET['studentID'] ?? ''));
if ($sid === '' || !preg_match('/^[0-9]+$/', $sid)) { http_response_code(400); echo 'Bad Request'; exit; }
try {
  $root = realpath(__DIR__ . '/..');
  $db = getGraduationDb();
  $nameRow = '';
  $classRow = '';
  try {
    $ps = $db->prepare('SELECT `name`, `class` FROM `graduation_information` WHERE `studentID` = ? LIMIT 1');
    $ps->bind_param('s', $sid);
    $ps->execute();
    $rs = $ps->get_result();
    $row = $rs ? $rs->fetch_assoc() : null;
    $ps->close();
    $nameRow = trim((string)($row['name'] ?? ''));
    $classRow = trim((string)($row['class'] ?? ''));
  } catch (Throwable $_) {}
  $safeNm = preg_replace('/[\/\\:*?"<>|]+/', '', $nameRow);
  $safeCls = preg_replace('/[\/\\:*?"<>|]+/', '', $classRow);
  $base = $root . DIRECTORY_SEPARATOR . 'FileUploadGraduationSubmission' . DIRECTORY_SEPARATOR . $sid;

  // 生成临时 ZIP 路径（与普通文件下载一致的策略）
  if (!class_exists('ZipArchive')) { http_response_code(500); echo 'Internal Server Error'; exit; }
  $tmp = tempnam(sys_get_temp_dir(), 'zip_');
  $zipPath = $tmp . '.zip';
  @unlink($tmp);
  $zip = new ZipArchive();
  if ($zip->open($zipPath, ZipArchive::CREATE) !== true) { http_response_code(500); echo 'Internal Server Error'; exit; }

  // 顶层目录：学号+姓名
  $rootLocal = $sid . $safeNm;
  if ($rootLocal === '') { $rootLocal = $sid; }
  $zip->addEmptyDir($rootLocal);

  // 过滤函数：隐藏项或 .chunks
  $isHiddenSeg = function (string $seg): bool { return $seg !== '' && $seg[0] === '.'; };
  $pathHasHidden = function (string $path) use ($isHiddenSeg): bool {
    $path = str_replace('\\', '/', $path);
    foreach (explode('/', trim($path, '/')) as $seg) {
      if ($seg === '.chunks') return true;
      if ($isHiddenSeg($seg)) return true;
    }
    return false;
  };

  // 递归添加（若目录不存在则仅保留空顶层目录）
  if (is_dir($base)) {
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
    $addDir($base, $rootLocal);
  }

  $zip->close();
  if (function_exists('set_time_limit')) { @set_time_limit(0); }
  while (ob_get_level()) { @ob_end_clean(); }
  header('Content-Description: File Transfer');
  header('Content-Type: application/zip');
  
  // Naming: ClassStudentIDName_xxxxxx_xxxxx
  $timestamp = date('Ymd_His');
  $zipName = $safeCls . $sid . $safeNm . '_' . $timestamp . '.zip';
  
  header('Content-Disposition: attachment; filename="' . rawurlencode($zipName) . '"');
  header('Content-Length: ' . filesize($zipPath));
  header('Cache-Control: no-cache');
  $fp = fopen($zipPath, 'rb');
  if ($fp) { while (!feof($fp)) { echo fread($fp, 8192); } fclose($fp); }
  @unlink($zipPath);
} catch (Throwable $e) { http_response_code(500); echo 'Internal Server Error'; }
