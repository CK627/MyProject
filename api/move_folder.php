<?php
/**
 * 移动文件夹接口（将整个文件夹移动到目标目录）
 * - POST JSON：{ username(纯数字), dir(源父目录，相对，可空), name(文件夹名), to(目标目录，相对，可空) }
 * - 行为：将 /File/{username}/{dir}/{name}/ 移动到 /File/{username}/{to}/{name}/
 * - 同步更新数据库中所有以该文件夹为前缀的文件路径
 */

require_once __DIR__ . '/util.php';

initApiRequest('POST');

$data = parseRequestBody();
$username = validateUsername((string)($data['username'] ?? ''));
$dir = trim((string)($data['dir'] ?? ''));
$name = trim((string)($data['name'] ?? ''));
$to = trim((string)($data['to'] ?? ''));

// 规范化与安全校验
$dir = str_replace(['\\'], '/', $dir);
$dir = trim($dir, '/');
if (strpos($dir, '..') !== false) { $dir = ''; }
$to = str_replace(['\\'], '/', $to);
$to = trim($to, '/');
if (strpos($to, '..') !== false) { $to = ''; }
$safeName = basename($name);
if ($safeName === '' || strpos($safeName, '/') !== false) {
  jsonError('非法文件夹名');
}

try {
  $db = getFilesDb();
  $table = ensureUserTable($db, $username);
  $root = realpath(__DIR__ . '/..');
  $base = $root . DIRECTORY_SEPARATOR . 'File' . DIRECTORY_SEPARATOR . $username;
  $src = $base . ($dir !== '' ? DIRECTORY_SEPARATOR . $dir : '') . DIRECTORY_SEPARATOR . $safeName;
  $dstParent = $base . ($to !== '' ? DIRECTORY_SEPARATOR . $to : '');
  $dst = $dstParent . DIRECTORY_SEPARATOR . $safeName;

  if (!is_dir($src)) {
    jsonError('源文件夹不存在', 404);
  }
  if (!is_dir($dstParent)) {
    // 创建目标父目录
    if (!mkdir($dstParent, 0777, true) && !is_dir($dstParent)) {
      throw new RuntimeException('创建目标目录失败');
    }
  }
  if (file_exists($dst)) {
    jsonError('目标位置已存在同名文件夹', 409);
  }

  if (!@rename($src, $dst)) {
    throw new RuntimeException('移动文件夹失败');
  }

  // 更新数据库路径前缀
  $oldPrefix = '/File/' . $username . '/' . ($dir !== '' ? $dir . '/' : '') . $safeName . '/';
  $newPrefix = '/File/' . $username . '/' . ($to !== '' ? $to . '/' : '') . $safeName . '/';
  $like = $oldPrefix . '%';
  $stmt = $db->prepare("UPDATE `{$table}` SET file_path = REPLACE(file_path, ?, ?) WHERE file_path LIKE ?");
  $stmt->bind_param('sss', $oldPrefix, $newPrefix, $like);
  $stmt->execute();
  $stmt->close();

  jsonSuccess();
} catch (Throwable $e) {
  jsonServerError($e);
}