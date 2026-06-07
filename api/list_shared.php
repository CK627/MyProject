<?php
/**
 * 获取共享文件列表
 * - 直接从所有用户表（user_%）中查询 is_public=1 的文件
 * - 步骤：
 *   1. 获取所有 user_ 开头的表名
 *   2. 遍历这些表，查询 is_public = 1 的记录
 *   3. 合并结果
 * - 注意：这种全表遍历性能较低，但在没有全局索引表的情况下是唯一解法。
 */

require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_files.php';
require_once __DIR__ . '/db.php';

initApiRequest('GET, POST');

try {
  $data = parseRequestBody();
  // 支持传入 dir 参数以浏览子目录（用于共享文件夹内部浏览）
  // 格式：{ "dir": "Docs/2024", "target_user": "12345" }
  // 如果提供了 target_user 和 dir，则我们只查询该用户的特定目录
  $targetUser = isset($data['target_user']) ? trim((string)$data['target_user']) : '';
  $dir = isset($data['dir']) ? trim((string)$data['dir']) : '';
  
  if ($targetUser !== '') {
    // 浏览模式：列出特定用户的共享子目录内容
    // 类似于 list.php，但只列出 is_public=1 的
    $filesDb = getFilesDb();
    $table = 'user_' . $targetUser;
    // 检查表是否存在
    $check = $filesDb->query("SHOW TABLES LIKE '{$table}'");
    if ($check->num_rows === 0) { jsonSuccess(['items' => []]); }
    
    // 前缀构建
    $prefix = "/File/{$targetUser}/" . ($dir ? $dir . '/' : '');
    // 查询该目录下的所有公开文件
    // 我们需要列出直接子文件和子文件夹
    // 类似于 list.php 的逻辑
    $sql = "SELECT id, file_path, upload_at FROM `{$table}` WHERE is_public = 1 AND file_path LIKE '" . $filesDb->real_escape_string($prefix) . "%' ORDER BY upload_at DESC";
    $res = $filesDb->query($sql);
    
    $items = [];
    $childFolders = []; // 收集子目录名
    
    while ($row = $res->fetch_assoc()) {
      $path = $row['file_path'];
      $rel = substr($path, strlen($prefix));
      $parts = explode('/', $rel, 2);
      
      if (count($parts) > 1) {
        // 是子文件夹
        $subFolder = $parts[0];
        $childFolders[$subFolder] = max($childFolders[$subFolder] ?? '', $row['upload_at']);
      } else {
        // 是当前目录下的文件
        $items[] = [
          'type' => 'file',
          'id' => $row['id'],
          'username' => $targetUser,
          'sharer_name' => $targetUser, // 暂不查名字，由前端上下文知晓
          'name' => $parts[0],
          'file_path' => $path,
          'upload_at' => $row['upload_at']
        ];
      }
    }
    
    // 合并文件夹结果
    foreach ($childFolders as $name => $time) {
      $items[] = [
        'type' => 'folder',
        'id' => 'folder_' . md5($targetUser . $dir . '/' . $name),
        'username' => $targetUser,
        'sharer_name' => $targetUser,
        'name' => $name,
        'path' => ($dir ? $dir . '/' : '') . $name, // 相对路径
        'upload_at' => $time
      ];
    }
    
    // 获取真实姓名
    $userDb = getDb();
    // 检查列
    $hasRealName = false; $hasName = false;
    $c1 = $userDb->query("SHOW COLUMNS FROM Users LIKE 'real_name'"); if($c1 && $c1->num_rows>0) $hasRealName=true;
    $c2 = $userDb->query("SHOW COLUMNS FROM Users LIKE 'name'"); if($c2 && $c2->num_rows>0) $hasName=true;
    $realName = $targetUser;
    if ($hasRealName) {
      $stmt = $userDb->prepare("SELECT real_name FROM Users WHERE username = ?");
      $stmt->bind_param('s', $targetUser); $stmt->execute(); $stmt->bind_result($r); if($stmt->fetch()) $realName = $r; $stmt->close();
    } elseif ($hasName) {
      $stmt = $userDb->prepare("SELECT name FROM Users WHERE username = ?");
      $stmt->bind_param('s', $targetUser); $stmt->execute(); $stmt->bind_result($r); if($stmt->fetch()) $realName = $r; $stmt->close();
    }
    
    // 补全名字
    foreach ($items as &$it) { $it['sharer_name'] = $realName ?: $targetUser; }
    
    // 排序
    usort($items, function($a, $b) {
      // 文件夹优先？或者时间倒序
      return strtotime($b['upload_at']) - strtotime($a['upload_at']);
    });
    
    jsonSuccess(['items' => $items]);
  }

  // 以下为原有的“列出所有根目录共享”逻辑
  $filesDb = getFilesDb();
  
  // 1. 获取所有拥有 is_public 字段的用户表
  // 通过 information_schema 一次性过滤，避免对每个表单独 SHOW COLUMNS，也避免 UNION 报错
  $tables = [];
  // 获取当前数据库名
  $dbNameRes = $filesDb->query("SELECT DATABASE()");
  $dbName = $dbNameRes->fetch_row()[0];
  
  $metaSql = "SELECT TABLE_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = ? AND COLUMN_NAME = 'is_public' AND TABLE_NAME LIKE 'user_%'";
  $stmt = $filesDb->prepare($metaSql);
  $stmt->bind_param('s', $dbName);
  $stmt->execute();
  $res = $stmt->get_result();
  while ($row = $res->fetch_assoc()) {
    $tables[] = $row['TABLE_NAME'];
  }
  $stmt->close();

  $items = [];
  $usernames = [];

  // 2. 批量并发查询 (Batch Union)
  // 将表分批，每批构建一个 UNION ALL 查询
  $chunks = array_chunk($tables, 50); // 每批 50 张表
  
  foreach ($chunks as $chunk) {
    $unionParts = [];
    foreach ($chunk as $table) {
      if (preg_match('/^user_([0-9]+)$/', $table, $matches)) {
        $u = $matches[1];
        // 检查 is_public 列 (这里假设如果一个表有，其他表大概率也有，或者为了性能忽略单表检查，
        // 但为了稳妥，我们可以先 DESCRIBE 一次，或者直接 try-catch SQL 错误。
        // 为了极致性能，我们假定结构一致。如果担心旧表报错，可以在 UNION 内部加个简单的 IFNULL 或 忽略错误)
        // 更稳妥的做法：我们只在第一次知道结构后就默认。
        // 这里简单处理：构建 SQL，让数据库去跑。
        
        // 注意：UNION ALL 需要列数一致。
        // SELECT id, file_path, upload_at, 'username' as u FROM table WHERE is_public=1
        $unionParts[] = "SELECT id, file_path, upload_at, '{$u}' as username FROM `{$table}` WHERE is_public = 1";
      }
    }
    
    if (empty($unionParts)) continue;
    
    $unionSql = implode(" UNION ALL ", $unionParts);
    // 限制每批返回数量，防止内存爆炸
    $unionSql .= " ORDER BY upload_at DESC LIMIT 500";
    
    try {
      $qRes = $filesDb->query($unionSql);
      if ($qRes) {
        while ($row = $qRes->fetch_assoc()) {
          $items[] = [
            'id' => $row['id'],
            'username' => $row['username'],
            'file_path' => $row['file_path'],
            'upload_at' => $row['upload_at']
          ];
          $usernames[$row['username']] = true;
        }
      }
    } catch (Throwable $ignore) {
      // 忽略单批次错误（如某些表缺少列）
      // 可以在这里记录日志
    }
  }
  
  // 按时间倒序排序
  usort($items, function($a, $b) {
    return strtotime($b['upload_at']) - strtotime($a['upload_at']);
  });
  
  // 截取前 500 条
  $items = array_slice($items, 0, 500);

  // 3. 获取用户真实姓名
  $userMap = [];
  if (!empty($usernames)) {
    $userDb = getDb();
    $uList = array_keys($usernames);
    // 安全构建 IN 查询
    $in = implode(',', array_fill(0, count($uList), '?'));
    $types = str_repeat('s', count($uList));
    // 注意：Users 表结构可能因环境而异，若无 real_name 则仅查 username
    // 检查 Users 表列
    $hasRealName = false;
    $hasName = false;
    
    $colCheck = $userDb->query("SHOW COLUMNS FROM Users LIKE 'real_name'");
    if ($colCheck && $colCheck->num_rows > 0) $hasRealName = true;
    
    $colCheck2 = $userDb->query("SHOW COLUMNS FROM Users LIKE 'name'");
    if ($colCheck2 && $colCheck2->num_rows > 0) $hasName = true;

    if ($hasRealName) {
      $stmt = $userDb->prepare("SELECT username, real_name FROM Users WHERE username IN ($in)");
    } else if ($hasName) {
      $stmt = $userDb->prepare("SELECT username, name AS real_name FROM Users WHERE username IN ($in)");
    } else {
      // 都没有，只查 username，后续逻辑会处理 real_name 为 null 的情况
      $stmt = $userDb->prepare("SELECT username FROM Users WHERE username IN ($in)");
    }
    
    if ($stmt) {
      $stmt->bind_param($types, ...$uList);
      $stmt->execute();
      $uRes = $stmt->get_result();
      while ($u = $uRes->fetch_assoc()) {
        $val = $u['real_name'] ?? null;
        if ($val === null && isset($u['name'])) $val = $u['name'];
        $userMap[$u['username']] = $val;
      }
      $stmt->close();
    }
  }

  // 4. 组装结果，增加文件夹聚合逻辑
  $result = [];
  
  // 预处理：识别文件夹结构
  // 我们将所有文件路径按层级聚合。
  // 但是，这是一个平铺的列表（按时间排序）。
  // 用户的需求是：如果共享的是文件夹，需要在共享文件里显示文件夹。
  // 但我们数据库存的是文件粒度的 is_public。并没有“共享文件夹”这个元数据。
  // 所谓的“共享文件夹”，其实是该文件夹下的所有（或部分）文件都被设为 is_public=1。
  // 既然如此，我们应该如何展示？
  // 策略：如果一个目录下有多个文件被共享，我们可以尝试折叠它们为一个文件夹条目？
  // 或者，简单点：我们保留文件列表，但如果发现某个路径包含文件夹，我们可以模拟一个文件夹项。
  // 但问题是：这是跨用户的全局列表。
  // 更好的方式：
  // 遍历所有 items，按 "username + 顶级目录" 进行分组。
  // 如果某个顶级目录下有多个文件，就显示该顶级目录（作为文件夹）；
  // 否则直接显示文件。
  
  // 实现逻辑：
  // 1. 遍历 items，构建树形结构（或至少是一级聚合）。
  // key = username + "/" + topLevelFolder
  $grouped = [];
  
  foreach ($items as $item) {
    $u = $item['username'];
    $path = $item['file_path']; // e.g. /File/123/Docs/a.txt
    // 去掉前缀 /File/username/
    $prefix = "/File/{$u}/";
    if (strpos($path, $prefix) === 0) {
      $rel = substr($path, strlen($prefix));
    } else {
      $rel = basename($path); // Fallback
    }
    
    // 检查是否有子目录
    $parts = explode('/', $rel, 2);
    $topName = $parts[0];
    
    // 构造唯一键：用户+顶层名
    $key = "{$u}|{$topName}";
    
    if (!isset($grouped[$key])) {
      $grouped[$key] = [
        'username' => $u,
        'name' => $topName,
        'is_folder' => (count($parts) > 1), // 如果有第二部分，说明肯定是文件夹
        'files' => [],
        'latest_at' => $item['upload_at']
      ];
    }
    
    // 即使当前看起来是文件（没有/），但如果后续发现同名文件夹（不可能，文件系统互斥），或者
    // 如果它就是个文件，那就存为文件。
    // 如果它是个文件夹内的文件，标记该组为文件夹。
    if (count($parts) > 1) {
      $grouped[$key]['is_folder'] = true;
    }
    
    // 更新最新时间
    if ($item['upload_at'] > $grouped[$key]['latest_at']) {
      $grouped[$key]['latest_at'] = $item['upload_at'];
    }
    
    $grouped[$key]['files'][] = $item;
  }
  
  // 展开分组
  $finalList = [];
  foreach ($grouped as $g) {
    $u = $g['username'];
    $realName = $userMap[$u] ?? $u;
    $displayName = $realName ?: $u;
    
    if ($g['is_folder']) {
      // 作为一个文件夹条目
      $finalList[] = [
        'type' => 'folder',
        'id' => 'folder_' . md5($u . $g['name']), // 虚拟ID
        'username' => $u,
        'sharer_name' => $displayName,
        'name' => $g['name'], // 显示文件夹名
        'path' => $g['name'], // 相对路径
        'upload_at' => $g['latest_at']
      ];
    } else {
      // 单个文件，或者根目录下的文件
      // 注意：如果有多个文件在根目录下，它们会被聚合吗？
      // 上面的逻辑是按 topName 分组。
      // 如果根目录下有 a.txt 和 b.txt，它们是不同的 topName，所以是两个条目。
      // 只有当 a/b.txt 和 a/c.txt 时，它们共享 topName "a"，才会被聚合。
      // 所以这里可以直接取出第一个文件作为条目。
      $fileItem = $g['files'][0];
      $finalList[] = [
        'type' => 'file',
        'id' => $fileItem['id'],
        'username' => $u,
        'sharer_name' => $displayName,
        'name' => basename($fileItem['file_path']),
        'file_path' => $fileItem['file_path'],
        'upload_at' => $fileItem['upload_at']
      ];
    }
  }
  
  // 再次按时间排序
  usort($finalList, function($a, $b) {
    return strtotime($b['upload_at']) - strtotime($a['upload_at']);
  });

  jsonSuccess(['items' => $finalList]);

} catch (Throwable $e) {
  jsonServerError($e);
}
