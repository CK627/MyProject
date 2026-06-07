<?php
/**
 * 文件下载接口
 * - GET: username(纯数字), id(记录ID)
 * - 行为：验证用户与记录，更新 last_download_at，返回文件内容（attachment）
 * - 设计：通过数据库路径确保只访问用户目录下的文件
 */

require_once __DIR__ . '/util.php';

setApiHeaders('GET, OPTIONS');
handleOptionsRequest();
requireMethod('GET');

$username = trim((string)($_GET['username'] ?? ''));
$id = (int)($_GET['id'] ?? 0);

$username = validateUsername($username);
if ($id <= 0) {
  jsonError('参数错误');
}

try {
  $db = getFilesDb();
  $table = ensureUserTable($db, $username);
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
  $full = $root . $relative;
  if (!is_file($full)) {
    jsonError('文件不存在', 404);
  }

  // 更新下载时间
  $stmt = $db->prepare("UPDATE `{$table}` SET last_download_at = CURRENT_TIMESTAMP WHERE id = ?");
  $stmt->bind_param('i', $id);
  $stmt->execute();
  $stmt->close();

  // 输出文件
  $filename = basename($full);
  $mime = function_exists('mime_content_type') ? mime_content_type($full) : 'application/octet-stream';
  header('Content-Description: File Transfer');
  header('Content-Type: ' . $mime);
  header('Content-Disposition: attachment; filename="' . rawurlencode($filename) . '"');
  header('Content-Length: ' . filesize($full));
  header('Cache-Control: no-cache');
  readfile($full);
} catch (Throwable $e) {
  jsonServerError($e);
}