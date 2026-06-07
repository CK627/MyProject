<?php
/**
 * 重命名文件接口
 * - POST JSON：{ username(纯数字), id(记录ID), newName(新文件名) }
 * - 行为：将文件重命名为新名称，同步更新数据库 file_path
 * - 校验：新名称不能包含路径分隔符，不能与同目录下其他文件重名
 * - 认证：优先使用 Session，回退到 username 参数
 */

require_once __DIR__ . '/util.php';

setAuthApiHeaders('POST, OPTIONS');
handleOptionsRequest();
requireMethod('POST');

$data = parseRequestBody();
$requestUsername = (string)($data['username'] ?? '');
$username = getAuthenticatedUser($requestUsername);

$id = (int)($data['id'] ?? 0);
$newName = trim((string)($data['newName'] ?? ''));

if ($id <= 0) {
  jsonError('参数错误');
}

// 校验新文件名
$safeName = basename($newName);
if ($safeName === '' || $safeName !== $newName || strpos($newName, '/') !== false || strpos($newName, '\\') !== false) {
  jsonError('非法文件名');
}
// 禁止 .. 等危险字符
if (strpos($safeName, '..') !== false) {
  jsonError('非法文件名');
}

try {
  $db = getFilesDb();
  $table = ensureUserTable($db, $username);
  
  // 查询当前文件路径
  $stmt = $db->prepare("SELECT file_path FROM `{$table}` WHERE id = ? LIMIT 1");
  $stmt->bind_param('i', $id);
  $stmt->execute();
  $res = $stmt->get_result();
  $row = $res->fetch_assoc();
  $stmt->close();
  
  if (!$row) { 
    jsonError('记录不存在', 404); 
  }

  $relative = $row['file_path'];
  $expectedPrefix = '/File/' . $username . '/';
  if (strpos($relative, $expectedPrefix) !== 0) {
    jsonError('非法路径', 403);
  }

  $root = realpath(__DIR__ . '/..');
  $oldFullPath = $root . $relative;
  
  if (!is_file($oldFullPath)) {
    jsonError('文件不存在', 404);
  }

  // 计算新路径
  $oldDir = dirname($relative);
  $newRelative = $oldDir . '/' . $safeName;
  $newFullPath = $root . $newRelative;

  // 检查目标是否已存在
  if (file_exists($newFullPath)) {
    jsonError('目标文件名已存在', 409);
  }

  // 检查数据库中是否有同名记录
  $stmt2 = $db->prepare("SELECT id FROM `{$table}` WHERE file_path = ? LIMIT 1");
  $stmt2->bind_param('s', $newRelative);
  $stmt2->execute();
  $res2 = $stmt2->get_result();
  if ($res2->fetch_assoc()) {
    $stmt2->close();
    jsonError('目标文件名已存在', 409);
  }
  $stmt2->close();

  // 执行重命名
  if (!rename($oldFullPath, $newFullPath)) {
    throw new RuntimeException('重命名失败');
  }

  // 更新数据库
  $stmt3 = $db->prepare("UPDATE `{$table}` SET file_path = ? WHERE id = ?");
  $stmt3->bind_param('si', $newRelative, $id);
  $stmt3->execute();
  $stmt3->close();

  // 记录审计日志
  logAudit($username, AUDIT_RENAME, "{$relative} -> {$newRelative}");

  jsonSuccess(['newPath' => $newRelative]);
} catch (Throwable $e) {
  jsonServerError($e);
}
