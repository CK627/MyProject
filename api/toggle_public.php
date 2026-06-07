<?php
/**
 * 切换文件或文件夹公开状态接口
 * - 入参：username, type ('file'|'folder'), id (文件ID), path (文件夹路径)
 * - 逻辑：
 *   1. 直接更新用户表中的 is_public 状态
 *   2. 如果是文件夹，递归更新该路径下所有文件的 is_public
 *   3. 不再维护 public_files_index 表
 * - 认证：优先使用 Session，回退到 username 参数
 */

require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

setAuthApiHeaders('POST, OPTIONS');
handleOptionsRequest();
requireMethod('POST');

$data = parseRequestBody();
$requestUsername = (string)($data['username'] ?? '');
$username = getAuthenticatedUser($requestUsername);

$type = $data['type'] ?? 'file'; // 'file' or 'folder'
$id = (int)($data['id'] ?? 0);
$path = trim((string)($data['path'] ?? '')); // 相对路径，如 'foo/bar'

// Session 认证已经验证身份
try {
  $db = getFilesDb();
  $table = ensureUserTable($db, $username);

  // 删除旧的索引表（如果存在），清理历史遗留
  $db->query("DROP TABLE IF EXISTS `public_files_index`");

  if ($type === 'file') {
    if ($id <= 0) {
      jsonError('文件ID无效');
    }
    // 查询当前状态
    $stmt = $db->prepare("SELECT is_public FROM `{$table}` WHERE id = ?");
    $stmt->bind_param('i', $id);
    $stmt->execute();
    $res = $stmt->get_result();
    $row = $res->fetch_assoc();
    $stmt->close();

    if (!$row) {
      jsonError('文件不存在');
    }

    $newStatus = $row['is_public'] ? 0 : 1;
    
    // 更新状态
    $upStmt = $db->prepare("UPDATE `{$table}` SET is_public = ? WHERE id = ?");
    $upStmt->bind_param('ii', $newStatus, $id);
    $upStmt->execute();
    $upStmt->close();

    jsonSuccess(['is_public' => $newStatus]);

  } else if ($type === 'folder') {
    // 文件夹处理：批量更新
    // 目标状态：如果当前文件夹下大部分是私有，则全设为公有；如果大部分是公有（或全部公有），则全设为私有？
    // 或者简单点：前端传 target_status
    // 这里我们采用：如果前端没传 target_status，则根据“只要有一个是私有，就全设为公有；全公有则设为私有”的逻辑？
    // 为了明确，还是由前端决定吧。但在没有参数的情况下，我们默认：Toggle。
    // 这里简化为：前端必须明确意图，或者我们查询一下。
    // 让我们先查询该文件夹下的统计信息
    
    $prefix = '/File/' . $username . '/' . ($path ? $path . '/' : '');
    $likePattern = $prefix . '%';
    
    // 使用预处理语句防止 SQL 注入
    $countStmt = $db->prepare("SELECT COUNT(*) as total, SUM(is_public) as public_cnt FROM `{$table}` WHERE file_path LIKE ?");
    $countStmt->bind_param('s', $likePattern);
    $countStmt->execute();
    $cRes = $countStmt->get_result();
    $cRow = $cRes->fetch_assoc();
    $countStmt->close();
    
    $total = (int)$cRow['total'];
    $publicCnt = (int)$cRow['public_cnt'];
    
    if ($total === 0) {
      jsonError('文件夹为空或不存在');
    }
    
    // 逻辑：只要不是全部公开，就设为全部公开；如果是全部公开，就设为全部私有
    $targetStatus = ($publicCnt < $total) ? 1 : 0;
    
    // 使用预处理语句更新
    $upStmt = $db->prepare("UPDATE `{$table}` SET is_public = ? WHERE file_path LIKE ?");
    $upStmt->bind_param('is', $targetStatus, $likePattern);
    $upStmt->execute();
    $affectedRows = $upStmt->affected_rows;
    $upStmt->close();
    
    jsonSuccess(['is_public' => $targetStatus, 'updated_count' => $affectedRows]);
    
  } else {
    jsonError('类型无效');
  }

} catch (Throwable $e) {
  jsonServerError($e);
}
