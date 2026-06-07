<?php
/**
 * 文件列表接口（支持目录）
 * - 入参：username（纯数字）, dir（相对目录，可选）
 * - 输出：
 *   - items：当前目录下的文件（仅当前层级，非递归）
 *   - folders：当前目录下的子文件夹列表（包含空文件夹，来自文件系统）
 * - 设计原因：在保持数据库为文件来源的同时，以文件系统补充空目录可见性。
 * - 认证：优先使用 Session，回退到 username 参数
 */

require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

setAuthApiHeaders('GET, POST, OPTIONS');
handleOptionsRequest();

$requestUsername = '';
$dir = '';
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
  $requestUsername = trim((string)($_GET['username'] ?? ''));
  $dir = trim((string)($_GET['dir'] ?? ''));
} else {
  $data = parseRequestBody();
  $requestUsername = trim((string)($data['username'] ?? ''));
  $dir = trim((string)($data['dir'] ?? ''));
}

$username = getAuthenticatedUser($requestUsername);

// 额外校验：仅允许已存在用户查询列表（Session 认证已经验证身份）
try {
  $db = getFilesDb();
  $table = ensureUserTable($db, $username);
  // 目录清洗与前缀
  $dir = str_replace(['\\'], '/', $dir);
  $dir = trim($dir, '/');
  if (strpos($dir, '..') !== false) { $dir = ''; }
  $prefix = '/File/' . $username . '/';

  // 增加 is_public 查询字段
  $sql = "SELECT id, file_path, is_public, upload_at, last_download_at FROM `{$table}` WHERE file_path LIKE CONCAT(?, '%') ORDER BY id DESC LIMIT 1000";
  $stmt = $db->prepare($sql);
  $like = $prefix . ($dir !== '' ? $dir . '/' : '');
  $stmt->bind_param('s', $like);
  $stmt->execute();
  $res = $stmt->get_result();
  $items = [];
  $childFiles = [];
  // 收集子文件夹名称（集合）及其中包含的公开文件数和最早上传时间
  $childFolderNames = [];
  
  while ($row = $res->fetch_assoc()) {
    $rel = substr($row['file_path'], strlen($like));
    if ($rel === false) { $rel = ''; }
    $pos = strpos($rel, '/');
    if ($pos === false || $pos === null) {
      // 没有进一步的斜杠：当前目录下的文件
      $childFiles[] = [
        'id' => (int)$row['id'],
        'file_path' => $row['file_path'],
        'is_public' => (int)($row['is_public'] ?? 0),
        'upload_at' => $row['upload_at'],
        'last_download_at' => $row['last_download_at'],
      ];
    } else {
      $folder = substr($rel, 0, $pos);
      if ($folder !== '') {
        if (!isset($childFolderNames[$folder])) {
          $childFolderNames[$folder] = ['hasPublic' => false, 'hasPrivate' => false, 'earliest_at' => null];
        }
        if ((int)($row['is_public'] ?? 0) === 1) {
          $childFolderNames[$folder]['hasPublic'] = true;
        } else {
          $childFolderNames[$folder]['hasPrivate'] = true;
        }
        // 记录最早的上传时间
        $uploadTime = $row['upload_at'];
        if ($uploadTime && (!$childFolderNames[$folder]['earliest_at'] || $uploadTime < $childFolderNames[$folder]['earliest_at'])) {
          $childFolderNames[$folder]['earliest_at'] = $uploadTime;
        }
      }
    }
  }
  $stmt->close();

  // 文件系统列出空子文件夹（当前层级）
  $root = realpath(__DIR__ . '/..');
  $baseDir = $root . DIRECTORY_SEPARATOR . 'File' . DIRECTORY_SEPARATOR . $username . ($dir !== '' ? DIRECTORY_SEPARATOR . $dir : '');
  if (is_dir($baseDir)) {
    $entries = scandir($baseDir);
    foreach ($entries as $en) {
      if ($en === '.' || $en === '..') continue;
      $full = $baseDir . DIRECTORY_SEPARATOR . $en;
      if (is_dir($full)) {
        if (!isset($childFolderNames[$en])) {
          $childFolderNames[$en] = ['hasPublic' => false, 'hasPrivate' => false, 'earliest_at' => null];
        }
      }
    }
  }

  // 计算文件夹创建时间与共享状态
  $folders = [];
  foreach ($childFolderNames as $name => $status) {
    // 优先使用数据库中最早的上传时间，否则回退到文件系统时间
    $created = $status['earliest_at'];
    if (!$created) {
      $full = $baseDir . DIRECTORY_SEPARATOR . $name;
      $ctime = @filectime($full);
      $mtime = @filemtime($full);
      $ts = $ctime ?: $mtime ?: 0;
      $created = $ts ? date('Y-m-d H:i:s', $ts) : '-';
    }
    
    // 推断文件夹共享状态
    $publicState = 0;
    if (!$status['hasPublic'] && !$status['hasPrivate']) {
      $publicState = -1;
    } else if ($status['hasPublic'] && !$status['hasPrivate']) {
      $publicState = 1;
    } else if (!$status['hasPublic'] && $status['hasPrivate']) {
      $publicState = 0;
    } else {
      $publicState = 2;
    }

    $folders[] = [ 
      'name' => $name, 
      'created_at' => $created,
      'public_state' => $publicState
    ];
  }

  jsonSuccess(['items' => $childFiles, 'folders' => $folders, 'dir' => $dir]);
} catch (Throwable $e) {
  jsonServerError($e);
}