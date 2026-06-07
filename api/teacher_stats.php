<?php
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_config.php';
require_once __DIR__ . '/ReviewHelper.php';

// 使用支持跨域 Cookie 的响应头
setAuthApiHeaders('GET, OPTIONS');
handleOptionsRequest();
requireMethod('GET');

try {
  // 获取当前登录教师的班级
  $adminClass = '';
  initSession();
  if (isset($_SESSION['admin_class']) && $_SESSION['admin_class'] !== '') {
    $adminClass = $_SESSION['admin_class'];
  }
  
  $db = getGraduationDb();
  $config = getGraduationConfig();
  
  // Initialize counts
  $counts = [];
  $totalUsers = 0;
  
  if ($adminClass !== '') {
    // Total users in class
    $stmt = $db->prepare('SELECT COUNT(*) AS c FROM `graduation_information` WHERE `class` = ?');
    $stmt->bind_param('s', $adminClass);
    $stmt->execute();
    $res = $stmt->get_result();
    $totalUsers = (int)($res->fetch_assoc()['c'] ?? 0);
    $stmt->close();
    
    // Count per type
    foreach ($config as $typeId => $conf) {
        $colPath = $conf['col_path'];
        $reviewCol = ReviewHelper::getReviewColumn($typeId);
        
        $sql = "SELECT COUNT(*) AS c FROM `graduation_information` WHERE `class` = ? AND `{$colPath}` <> '' AND `{$colPath}` IS NOT NULL";
        
        // Exclude '不通过'
        if ($reviewCol) {
            $sql .= " AND (`{$reviewCol}` IS NULL OR `{$reviewCol}` <> '不通过')";
        }
        
        $stmt = $db->prepare($sql);
        $stmt->bind_param('s', $adminClass);
        $stmt->execute();
        $res = $stmt->get_result();
        $counts[$typeId] = (int)($res->fetch_assoc()['c'] ?? 0);
        $stmt->close();
    }
    
    // 获取本班学生 ID 列表
    $stmt = $db->prepare('SELECT `studentID` FROM `graduation_information` WHERE `class` = ?');
    $stmt->bind_param('s', $adminClass);
    $stmt->execute();
    $res2 = $stmt->get_result();
    $userIds = [];
    while ($res2 && ($r2 = $res2->fetch_assoc())) { $userIds[] = (string)$r2['studentID']; }
    $stmt->close();
    
  } else {
    // Admin: Total users
    $res = $db->query('SELECT COUNT(*) AS c FROM `graduation_information`');
    $totalUsers = (int)($res->fetch_assoc()['c'] ?? 0);
    
    // Count per type
    foreach ($config as $typeId => $conf) {
        $colPath = $conf['col_path'];
        $reviewCol = ReviewHelper::getReviewColumn($typeId);
        
        $sql = "SELECT COUNT(*) AS c FROM `graduation_information` WHERE `{$colPath}` <> '' AND `{$colPath}` IS NOT NULL";
        
        // Exclude '不通过'
        if ($reviewCol) {
            $sql .= " AND (`{$reviewCol}` IS NULL OR `{$reviewCol}` <> '不通过')";
        }
        
        $res = $db->query($sql);
        $counts[$typeId] = (int)($res->fetch_assoc()['c'] ?? 0);
    }
    
    $res2 = $db->query('SELECT `studentID` FROM `graduation_information`');
    $userIds = [];
    while ($res2 && ($r2 = $res2->fetch_assoc())) { $userIds[] = (string)$r2['studentID']; }
  }
  
  $summary = [
    'total_users' => $totalUsers,
    'not_submitted_users' => max(0, $totalUsers - ($counts['thesis'] ?? 0)),
    'submit_rate' => $totalUsers > 0 ? round((($counts['thesis'] ?? 0) / $totalUsers) * 100, 1) : 0,
  ];
  
  // Add dynamic project counts
  foreach ($counts as $k => $v) {
      $summary[$k . '_users'] = $v;
  }
  
  // Legacy support for thesis -> submitted_users
  if (isset($counts['thesis'])) {
      $summary['submitted_users'] = $counts['thesis'];
  }
  
  // 初始化统计变量
  $totalRecords = 0;
  $root = realpath(__DIR__ . '/..');
  $typeCounts = [];
  $trendCounts = [];
  $days = 7;
  for ($i = 0; $i < $days; $i++) {
    $d = date('Y-m-d', strtotime("-{$i} day"));
    $trendCounts[$d] = 0;
  }
  
  foreach ($userIds as $username) {
    $userDir = $root . DIRECTORY_SEPARATOR . 'FileUploadGraduationSubmission' . DIRECTORY_SEPARATOR . $username;
    if (is_dir($userDir)) {
      $files = @glob($userDir . DIRECTORY_SEPARATOR . '*');
      foreach ($files ?: [] as $f) {
        $ext = strtolower(pathinfo($f, PATHINFO_EXTENSION));
        if ($ext === '') { $ext = 'other'; }
        $typeCounts[$ext] = ($typeCounts[$ext] ?? 0) + 1;
        $dt = date('Y-m-d', @filemtime($f) ?: time());
        if (isset($trendCounts[$dt])) { $trendCounts[$dt]++; }
        $totalRecords++;
      }
    }
  }
  
  $trend = [];
  $keys = array_keys($trendCounts);
  usort($keys, function($a,$b){ return strcmp($a,$b); });
  foreach ($keys as $k) { $trend[] = ['date' => $k, 'count' => (int)$trendCounts[$k]]; }
  echo json_encode([
    'ok' => true,
    'summary' => $summary,
    'tables' => $totalUsers,
    'submissions' => $totalRecords,
    'trend' => $trend,
    'types' => $typeCounts
  ]);
} catch (Throwable $e) {
  http_response_code(500);
  echo json_encode(['ok'=>false]);
}
