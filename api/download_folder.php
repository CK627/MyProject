<?php
/**
 * 文件夹下载接口（打包为 ZIP 并下载）
 * - GET: username(纯数字), dir(相对目录，可空), name(文件夹名)
 * - 行为：将 /File/{username}/{dir}/{name} 整个目录打包为 ZIP 并返回附件下载
 * - 过滤：跳过隐藏项（任意路径段以 '.' 开头）以及特殊目录 .chunks
 */

require_once __DIR__ . '/util.php';

setApiHeaders('GET, OPTIONS');
handleOptionsRequest();
requireMethod('GET');

$username = trim((string)($_GET['username'] ?? ''));
$dir = trim((string)($_GET['dir'] ?? ''));
$name = trim((string)($_GET['name'] ?? ''));

$username = validateUsername($username);

// 规范化与安全校验
$dir = str_replace(['\\'], '/', $dir);
$dir = trim($dir, '/');
if (strpos($dir, '..') !== false) { $dir = ''; }
$safeName = basename($name);
if ($safeName === '' || strpos($safeName, '/') !== false) {
  jsonError('非法文件夹名');
}

// 隐藏项判断：任意段以 '.' 开头则视为隐藏
function isHiddenPathSeg(string $seg): bool { return $seg !== '' && $seg[0] === '.'; }
function pathHasHidden(string $path): bool {
  $path = str_replace('\\', '/', $path);
  foreach (explode('/', trim($path, '/')) as $seg) {
    if ($seg === '.chunks') return true;
    if (isHiddenPathSeg($seg)) return true;
  }
  return false;
}

try {
  $root = realpath(__DIR__ . '/..');
  $base = $root . DIRECTORY_SEPARATOR . 'File' . DIRECTORY_SEPARATOR . $username;
  $src = $base . ($dir !== '' ? DIRECTORY_SEPARATOR . $dir : '') . DIRECTORY_SEPARATOR . $safeName;
  if (!is_dir($src)) {
    jsonError('文件夹不存在', 404);
  }

  if (!class_exists('ZipArchive')) {
    jsonError('服务器未启用 ZipArchive 扩展', 500);
  }
  $tmp = tempnam(sys_get_temp_dir(), 'zip_');
  $zipPath = $tmp . '.zip';
  @unlink($tmp);
  $zip = new ZipArchive();
  if ($zip->open($zipPath, ZipArchive::CREATE) !== true) {
    jsonError('创建压缩包失败', 500);
  }

  $rootLocal = $safeName;
  $zip->addEmptyDir($rootLocal);

  $addDir = function (string $abs, string $localBase) use (&$zip, &$addDir) {
    $entries = @scandir($abs);
    if ($entries === false) return;
    foreach ($entries as $entry) {
      if ($entry === '.' || $entry === '..') continue;
      if ($entry === '.chunks') continue;
      if (pathHasHidden($entry)) continue;
      $absPath = $abs . DIRECTORY_SEPARATOR . $entry;
      $localPath = $localBase . '/' . $entry;
      if (is_dir($absPath)) {
        $zip->addEmptyDir($localPath);
        $addDir($absPath, $localPath);
      } else if (is_file($absPath)) {
        $zip->addFile($absPath, $localPath);
      }
    }
  };
  $addDir($src, $rootLocal);
  $zip->close();

  // 输出 ZIP 并清理
  $downloadName = $safeName . '.zip';
  header('Content-Description: File Transfer');
  header('Content-Type: application/zip');
  header('Content-Disposition: attachment; filename="' . rawurlencode($downloadName) . '"');
  header('Content-Length: ' . filesize($zipPath));
  header('Cache-Control: no-cache');
  readfile($zipPath);
  @unlink($zipPath);
} catch (Throwable $e) {
  jsonServerError($e);
}