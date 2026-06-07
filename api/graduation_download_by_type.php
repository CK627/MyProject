<?php
/**
 * 按文件类型打包下载所有学生的文件
 * GET /api/graduation_download_by_type.php?type=thesis&class=xxx
 * 
 * 生成 ZIP 包，文件名格式：{typeName}_{class/全部}.zip
 * ZIP 内结构：{班级}/{学号}_{姓名}_{文件名}
 */

require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_config.php';

// CORS 和请求处理
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { 
    http_response_code(204); 
    exit; 
}
if ($_SERVER['REQUEST_METHOD'] !== 'GET') { 
    http_response_code(405); 
    echo 'Method Not Allowed'; 
    exit; 
}

$type = trim((string)($_GET['type'] ?? ''));
$cls = trim((string)($_GET['class'] ?? ''));

// 验证类型参数
$config = getGraduationConfig();
if (!isset($config[$type])) {
    http_response_code(400);
    echo '无效的文件类型';
    exit;
}

$conf = $config[$type];
$colPath = $conf['col_path'];
$typeName = $conf['name'];

try {
    $db = getGraduationDb();
    $root = realpath(__DIR__ . '/..');
    
    // 查询有提交文件的学生
    $sql = "SELECT `studentID`, `name`, `class`, `{$colPath}` as path 
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
    
    // 收集文件
    $files = [];
    while ($res && ($row = $res->fetch_assoc())) {
        $path = (string)($row['path'] ?? '');
        if ($path === '') continue;
        
        $fullPath = $root . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $path);
        if (!file_exists($fullPath)) continue;
        
        $studentID = (string)($row['studentID'] ?? '');
        $name = (string)($row['name'] ?? '');
        $class = (string)($row['class'] ?? '未分班');
        $filename = basename($path);
        
        // 获取扩展名
        $ext = pathinfo($filename, PATHINFO_EXTENSION);
        // ZIP 内路径：班级/学号姓名项目名称.ext
        $project = $conf['name'] ?? $type;
        $zipPath = "{$class}/{$studentID}{$name}{$project}.{$ext}";
        
        $files[] = [
            'fullPath' => $fullPath,
            'zipPath' => $zipPath
        ];
    }
    
    if (count($files) === 0) {
        http_response_code(404);
        echo '没有找到已提交的文件';
        exit;
    }
    
    // 创建 ZIP
    $tmp = tempnam(sys_get_temp_dir(), 'zip');
    $zip = new ZipArchive();
    if ($zip->open($tmp, ZipArchive::OVERWRITE) !== true) {
        http_response_code(500);
        echo 'Internal Server Error';
        exit;
    }
    
    foreach ($files as $f) {
        $zip->addFile($f['fullPath'], $f['zipPath']);
    }
    
    $zip->close();
    
    // 输出文件
    $clsLabel = $cls !== '' ? $cls : '全部';
    $zipName = "{$typeName}_{$clsLabel}.zip";
    
    header('Content-Type: application/zip');
    header('Content-Disposition: attachment; filename="' . rawurlencode($zipName) . '"');
    header('Content-Length: ' . filesize($tmp));
    header('Cache-Control: no-cache');
    
    readfile($tmp);
    @unlink($tmp);
    
} catch (Throwable $e) {
    http_response_code(500);
    echo 'Internal Server Error';
}
