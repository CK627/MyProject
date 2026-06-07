<?php
/**
 * 删除文件接口
 * - POST JSON：{ username(纯数字), id(记录ID) }
 * - 行为：验证记录归属，删除磁盘文件（若存在），删除数据库记录
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
if ($id <= 0) {
  jsonError('参数错误');
}

try {
  $db = getFilesDb();
  $table = ensureUserTable($db, $username);
  // 查询路径
  $stmt = $db->prepare("SELECT file_path FROM `{$table}` WHERE id = ? LIMIT 1");
  $stmt->bind_param('i', $id);
  $stmt->execute();
  $res = $stmt->get_result();
  $row = $res->fetch_assoc();
  $stmt->close();
  if (!$row) { jsonError('记录不存在', 404); }

  $relative = $row['file_path'];
  $expectedPrefix = '/File/' . $username . '/';
  if (strpos($relative, $expectedPrefix) !== 0) {
    jsonError('非法路径', 403);
  }

  $root = realpath(__DIR__ . '/..');
  $full = $root . $relative;
  if (is_file($full)) { @unlink($full); }

  // 删除记录
  $stmt = $db->prepare("DELETE FROM `{$table}` WHERE id = ?");
  $stmt->bind_param('i', $id);
  $stmt->execute();
  $stmt->close();

  // 记录审计日志
  logAudit($username, AUDIT_DELETE, $relative);

  jsonSuccess();
} catch (Throwable $e) {
  jsonServerError($e);
}