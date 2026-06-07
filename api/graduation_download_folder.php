<?php
require_once __DIR__ . '/db_graduation.php';
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'GET') { http_response_code(405); echo 'Method Not Allowed'; exit; }
$sid = trim((string)($_GET['studentID'] ?? ''));
$dir = trim((string)($_GET['dir'] ?? ''));
$name = trim((string)($_GET['name'] ?? ''));
if ($sid === '' || !preg_match('/^[0-9]+$/', $sid)) { http_response_code(400); echo 'Bad Request'; exit; }
try {
  $root = realpath(__DIR__ . '/..');
  $base = $root . DIRECTORY_SEPARATOR . 'FileUploadGraduationSubmission' . DIRECTORY_SEPARATOR . $sid;
  $safeDir = str_replace(['..','\\'], ['', DIRECTORY_SEPARATOR], $dir);
  $safeName = basename($name);
  $folder = rtrim($base . ( $safeDir ? (DIRECTORY_SEPARATOR . $safeDir) : '' ), DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . $safeName;
  if (!is_dir($folder)) { http_response_code(404); echo 'Not Found'; exit; }
  $tmp = tempnam(sys_get_temp_dir(), 'zip');
  $zip = new ZipArchive();
  if ($zip->open($tmp, ZipArchive::OVERWRITE) !== true) { http_response_code(500); echo 'Internal Server Error'; exit; }
  $zip->addEmptyDir($safeName);
  $baseLen = strlen($folder) + 1;
  $iter = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($folder, FilesystemIterator::SKIP_DOTS));
  foreach ($iter as $file) {
    if ($file->isDir()) continue;
    $path = $file->getPathname();
    $rel = substr($path, $baseLen);
    if (preg_match('/(^|\/)\./', $rel)) continue;
    $zip->addFile($path, $safeName . '/' . $rel);
  }
  $zip->close();
  clearstatcache(true, $tmp);
  $zipName = $safeName !== '' ? ($safeName . '.zip') : 'folder.zip';
  while (ob_get_level()) { @ob_end_clean(); }
  header('Content-Description: File Transfer');
  header('Content-Type: application/zip');
  header('Content-Disposition: attachment; filename="' . rawurlencode($zipName) . '"');
  header('Content-Length: ' . filesize($tmp));
  header('Cache-Control: no-cache');
  $fp = fopen($tmp, 'rb');
  if ($fp) { while (!feof($fp)) { echo fread($fp, 8192); } fclose($fp); }
  @unlink($tmp);
} catch (Throwable $e) { http_response_code(500); echo 'Internal Server Error'; }
