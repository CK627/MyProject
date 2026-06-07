<?php
/**
 * 重命名文件夹接口
 * - POST JSON：{ username(纯数字), dir(父目录，相对，可空), name(旧文件夹名), newName(新文件夹名) }
 * - 行为：将文件夹重命名为新名称，同步更新数据库中所有以该文件夹为前缀的 file_path
 * - 校验：新名称不能包含路径分隔符，不能与同级其他文件夹重名
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
$newName = trim((string)($data['newName'] ?? ''));

// 规范化与安全校验
$dir = str_replace(['\\'], '/', $dir);
$dir = trim($dir, '/');
if (strpos($dir, '..') !== false) { $dir = ''; }

$safeName = basename($name);
if ($safeName === '' || strpos($safeName, '/') !== false) {
  jsonError('非法文件夹名');
}

$safeNewName = basename($newName);
if ($safeNewName === '' || $safeNewName !== $newName || strpos($newName, '/') !== false || strpos($newName, '\\') !== false) {
  jsonError('非法新文件夹名');
}
if (strpos($safeNewName, '..') !== false) {
  jsonError('非法新文件夹名');
}

// 名称未变化
if ($safeName === $safeNewName) {
  jsonError('新名称与原名称相同');
}

try {
  $db = getFilesDb();
  $table = ensureUserTable($db, $username);
  $root = realpath(__DIR__ . '/..');
  $base = $root . DIRECTORY_SEPARATOR . 'File' . DIRECTORY_SEPARATOR . $username;
  
  // 计算路径
  $parentDir = $base . ($dir !== '' ? DIRECTORY_SEPARATOR . $dir : '');
  $oldPath = $parentDir . DIRECTORY_SEPARATOR . $safeName;
  $newPath = $parentDir . DIRECTORY_SEPARATOR . $safeNewName;

  // 检查源文件夹是否存在
  if (!is_dir($oldPath)) {
    jsonError('文件夹不存在', 404);
  }

  // 检查目标是否已存在
  if (file_exists($newPath)) {
    jsonError('目标文件夹名已存在', 409);
  }

  // 执行重命名
  if (!rename($oldPath, $newPath)) {
    throw new RuntimeException('重命名失败');
  }

  // 更新数据库中所有以该文件夹为前缀的 file_path
  $oldPrefix = '/File/' . $username . '/' . ($dir !== '' ? $dir . '/' : '') . $safeName . '/';
  $newPrefix = '/File/' . $username . '/' . ($dir !== '' ? $dir . '/' : '') . $safeNewName . '/';
  
  $stmt = $db->prepare("UPDATE `{$table}` SET file_path = REPLACE(file_path, ?, ?) WHERE file_path LIKE ?");
  $like = $oldPrefix . '%';
  $stmt->bind_param('sss', $oldPrefix, $newPrefix, $like);
  $stmt->execute();
  $affected = $stmt->affected_rows;
  $stmt->close();

  // 记录审计日志
  $oldRelative = ($dir !== '' ? $dir . '/' : '') . $safeName;
  $newRelative = ($dir !== '' ? $dir . '/' : '') . $safeNewName;
  logAudit($username, AUDIT_RENAME, "folder: {$oldRelative} -> {$newRelative}");

  jsonSuccess(['affected' => $affected]);
} catch (Throwable $e) {
  jsonServerError($e);
}
