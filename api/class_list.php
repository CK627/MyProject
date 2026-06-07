<?php
/**
 * 获取学生列表接口
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_config.php';
require_once __DIR__ . '/ReviewHelper.php';

initApiRequest('GET');

$class = isset($_GET['class']) ? trim((string)$_GET['class']) : '';

try {
  $db = getGraduationDb();
  $config = getGraduationConfig();
  
  // Build query columns
  $columns = ['`studentID`', '`name`', '`class`'];
  $reviewCols = []; // Map typeId to review column name

  foreach ($config as $typeId => $typeCfg) {
      $colPath = $typeCfg['col_path'];
      $columns[] = '`' . $colPath . '`';
      
      // Add review column
      $reviewCol = ReviewHelper::getReviewColumn($typeId);
      if ($reviewCol) {
          $columns[] = '`' . $reviewCol . '`';
          $reviewCols[$typeId] = $reviewCol;
      }
  }
  $colStr = implode(',', $columns);

  $items = [];
  if ($class !== '') {
    $stmt = $db->prepare("SELECT $colStr FROM `graduation_information` WHERE `class` = ?");
    $stmt->bind_param('s', $class);
    $stmt->execute();
    $res = $stmt->get_result();
  } else {
    $res = $db->query("SELECT $colStr FROM `graduation_information`");
  }
  
  while ($res && ($r = $res->fetch_assoc())) {
    $missing = [];
    foreach ($config as $typeId => $typeCfg) {
        $path = $r[$typeCfg['col_path']] ?? '';
        $reviewCol = $reviewCols[$typeId] ?? null;
        $reviewStatus = ($reviewCol && isset($r[$reviewCol])) ? $r[$reviewCol] : '未批阅';

        // Treat as missing if path is empty OR review status is '不通过'
        if ($path === '' || $path === null || $reviewStatus === '不通过') {
            $missing[] = $typeCfg['name']; // Use name for display
        }
    }

    $items[] = [
      'username' => strval($r['studentID'] ?? ''),
      'name' => trim((string)($r['name'] ?? '')),
      'class' => trim((string)($r['class'] ?? '')),
      'submitted' => empty($missing),
      'missing' => $missing
    ];
  }
  if (isset($stmt)) {
    $stmt->close();
  }
  jsonSuccess(['items' => $items]);
} catch (Throwable $e) {
  jsonServerError($e);
}
