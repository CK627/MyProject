<?php
/**
 * 移动文件接口
 * - POST JSON：{ username(纯数字), id(记录ID), to(目标相对目录) }
 * - 行为：将文件从当前路径移动到 /File/{username}/{to}/ 下，同步更新数据库 file_path。
 * - 设计原因：保持数据库与文件系统一致，避免覆盖已存在同名文件。
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
$to = trim((string)($data['to'] ?? ''));

if ($id <= 0) {
  jsonError('参数错误');
}

// 目标目录清洗
$to = str_replace(['\\'], '/', $to);
$to = trim($to, '/');
if (strpos($to, '..') !== false) { $to = ''; }

try {
  $db = getFilesDb();
  $table = ensureUserTable($db, $username);
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
  $fullFrom = $root . $relative;
  if (!is_file($fullFrom)) { jsonError('文件不存在', 404); }

  $filename = basename($fullFrom);
  $base = $root . $expectedPrefix; // /File/{username}/
  $targetDir = $base . ($to !== '' ? $to . '/' : '');
  if (!is_dir($targetDir)) {
    if (!mkdir($targetDir, 0755, true) && !is_dir($targetDir)) {
      throw new RuntimeException('无法创建目标目录');
    }
  }
  $fullTo = $targetDir . $filename;
  if (file_exists($fullTo)) {
    jsonError('目标目录已存在同名文件', 409);
  }

  if (!rename($fullFrom, $fullTo)) {
    throw new RuntimeException('移动失败');
  }

  // 重置目标文件权限为只读（0444），保持安全策略一致
  @chmod($fullTo, 0444);

  $newRelative = $expectedPrefix . ($to !== '' ? $to . '/' : '') . $filename;
  $stmt = $db->prepare("UPDATE `{$table}` SET file_path = ? WHERE id = ?");
  $stmt->bind_param('si', $newRelative, $id);
  $stmt->execute();
  $stmt->close();

  jsonSuccess(['path' => $newRelative]);
} catch (Throwable $e) {
  jsonServerError($e);
}