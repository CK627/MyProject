<?php
require_once __DIR__ . '/db_graduation.php';
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'GET') { http_response_code(405); echo 'Method Not Allowed'; exit; }
$sid = trim((string)($_GET['studentID'] ?? ''));
$path = trim((string)($_GET['path'] ?? ''));
if ($sid === '' || !preg_match('/^[0-9]+$/', $sid)) { http_response_code(400); echo 'Bad Request'; exit; }
try {
  $root = realpath(__DIR__ . '/..');
  $base = $root . DIRECTORY_SEPARATOR . 'FileUploadGraduationSubmission' . DIRECTORY_SEPARATOR . $sid;
  $rel = str_replace(['..','\\'], ['', DIRECTORY_SEPARATOR], $path);
  $full = rtrim($base, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . ltrim($rel, DIRECTORY_SEPARATOR);
  if (!is_file($full)) { http_response_code(404); echo 'Not Found'; exit; }
  $fn = basename($full);
  $mime = 'application/octet-stream';
  if (function_exists('mime_content_type')) { $m = @mime_content_type($full); if ($m) $mime = $m; }
  header('Content-Type: ' . $mime);
  header('Content-Disposition: attachment; filename="' . rawurlencode($fn) . '"');
  header('Content-Length: ' . filesize($full));
  readfile($full);
} catch (Throwable $e) { http_response_code(500); echo 'Internal Server Error'; }

