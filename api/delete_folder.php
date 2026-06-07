<?php
/**
 * 删除文件夹接口（递归删除其中文件与子文件夹）
 * - POST JSON：{ username(纯数字), dir(父目录，相对，可空), name(文件夹名) }
 * - 行为：删除 /File/{username}/{dir}/{name}/ 下的所有文件与子目录，并清理数据库记录
 * - 认证：优先使用 Session，回退到 username 参数
 */

require_once __DIR__ . '/util.php';

setAuthApiHeaders('POST, OPTIONS');
handleOptionsRequest();
requireMethod('POST');

$data = parseRequestBody();
$requestUsername = (string)($data['username'] ?? '');
$username = getAuthenticatedUser($requestUsername);

$dir = trim((string)($data['dir'] ?? ''));
$name = trim((string)($data['name'] ?? ''));

// 清洗目录与名称
$dir = str_replace(['\\'], '/', $dir);
$dir = trim($dir, '/');
if (strpos($dir, '..') !== false) { $dir = ''; }
$safeName = basename($name);
if ($safeName === '' || strpos($safeName, '/') !== false) {
  jsonError('非法文件夹名');
}

// 递归删除函数
function delTree(string $path): bool {
  if (!is_dir($path)) return false;
  $entries = scandir($path);
  foreach ($entries as $en) {
    if ($en === '.' || $en === '..') continue;
    $full = $path . DIRECTORY_SEPARATOR . $en;
    if (is_dir($full)) {
      delTree($full);
    } else {
      @unlink($full);
    }
  }
  return @rmdir($path);
}

try {
  $db = getFilesDb();
  $table = ensureUserTable($db, $username);
  $root = realpath(__DIR__ . '/..');
  $base = $root . DIRECTORY_SEPARATOR . 'File' . DIRECTORY_SEPARATOR . $username;
  $target = $base . ($dir !== '' ? DIRECTORY_SEPARATOR . $dir : '') . DIRECTORY_SEPARATOR . $safeName;

  if (!is_dir($target)) {
    jsonError('文件夹不存在', 404);
  }

  if (!delTree($target)) {
    throw new RuntimeException('删除文件夹失败');
  }

  // 清理数据库：删除该目录下的所有文件记录
  $prefix = '/File/' . $username . '/' . ($dir !== '' ? $dir . '/' : '') . $safeName . '/';
  $like = $prefix . '%';
  $stmt = $db->prepare("DELETE FROM `{$table}` WHERE file_path LIKE ?");
  $stmt->bind_param('s', $like);
  $stmt->execute();
  $stmt->close();

  jsonSuccess();
} catch (Throwable $e) {
  jsonServerError($e);
}