<?php
/**
 * 按文件类型列出所有学生已提交的文件
 * GET /api/graduation_list_by_type.php?type=thesis&class=xxx
 * 
 * 返回: { ok: true, items: [{ studentID, name, class, path, finalTime }] }
 */

require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_config.php';
require_once __DIR__ . '/ReviewHelper.php';

// CORS 和请求处理
setApiHeaders('GET, OPTIONS');
handleOptionsRequest();
requireMethod('GET');

$type = trim((string)($_GET['type'] ?? ''));
$cls = trim((string)($_GET['class'] ?? ''));

// 验证类型参数
$config = getGraduationConfig();
if (!isset($config[$type])) {
    jsonError('无效的文件类型', 400);
}

$conf = $config[$type];
$colPath = $conf['col_path'];
$colFinalTime = $conf['col_final_time'];
$typeName = $conf['name'];
$colReview = ReviewHelper::getReviewColumn($type);

try {
    $db = getGraduationDb();
    
    // 构建查询 - 只查询有提交文件的学生
    $sql = "SELECT `studentID`, `name`, `class`, 
            `{$colPath}` as path, 
            `{$colFinalTime}` as finalTime,
            `{$colReview}` as reviewResult
            FROM `graduation_information` 
            WHERE `{$colPath}` IS NOT NULL AND `{$colPath}` != ''";
    
    $params = [];
    $types = '';
    
    if ($cls !== '') {
        $sql .= ' AND `class` = ?';
        $params[] = $cls;
        $types .= 's';
    }
    
    $sql .= ' ORDER BY `class`, `studentID`';
    
    if (count($params) > 0) {
        $stmt = $db->prepare($sql);
        $stmt->bind_param($types, ...$params);
        $stmt->execute();
        $res = $stmt->get_result();
    } else {
        $res = $db->query($sql);
    }
    
    $items = [];
    while ($res && ($row = $res->fetch_assoc())) {
        $path = (string)($row['path'] ?? '');
        // 只返回有路径的记录
        if ($path === '') continue;
        
        $items[] = [
            'studentID' => (string)($row['studentID'] ?? ''),
            'name' => (string)($row['name'] ?? ''),
            'class' => (string)($row['class'] ?? ''),
            'path' => $path,
            'filename' => basename($path),
            'finalTime' => (string)($row['finalTime'] ?? ''),
            'reviewResult' => (string)($row['reviewResult'] ?? '未批阅')
        ];
    }
    
    jsonSuccess([
        'items' => $items,
        'type' => $type,
        'typeName' => $typeName,
        'total' => count($items)
    ]);
    
} catch (Throwable $e) {
    jsonServerError($e, false);
}
