<?php
/**
 * 获取毕业生文件列表接口
 * POST JSON: { studentID: string, dir?: string }
 * 
 * 从数据库 graduation_information 表读取已提交的文件记录
 * 返回: { ok: true, items: [{name, upload_at, type, typeName}], folders: [] }
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_config.php';
require_once __DIR__ . '/ReviewHelper.php';

initApiRequest('POST');

$data = parseRequestBody();
$sid = trim((string)($data['studentID'] ?? $data['username'] ?? ''));
$dir = trim((string)($data['dir'] ?? ''));

// 验证学号格式
if ($sid === '' || !preg_match('/^[0-9]+$/', $sid)) {
    jsonError('学号无效', 400);
}

try {
    $db = getGraduationDb();
    $config = getGraduationConfig();
    
    // 构建查询字段列表
    $columns = ['studentID', 'name'];
    $reviewCols = [];

    foreach ($config as $typeId => $typeCfg) {
        $colPath = $typeCfg['col_path'];
        $columns[] = '`' . $colPath . '`';
        $columns[] = '`' . $typeCfg['col_final_time'] . '`';
        
        $reviewCol = ReviewHelper::getReviewColumn($typeId);
        if ($reviewCol) {
            $columns[] = '`' . $reviewCol . '`';
            $reviewCols[$typeId] = $reviewCol;
        }
    }
    
    $sql = 'SELECT ' . implode(', ', $columns) . ' FROM `' . GRADUATION_TABLE . '` WHERE studentID = ? LIMIT 1';
    $stmt = $db->prepare($sql);
    $stmt->bind_param('s', $sid);
    $stmt->execute();
    $res = $stmt->get_result();
    $row = $res->fetch_assoc();
    $stmt->close();
    
    if (!$row) {
        // 学生不存在
        jsonSuccess(['items' => [], 'folders' => []]);
    }
    
    $items = [];
    
    // 如果没有指定子目录，列出所有已提交的文件
    if ($dir === '') {
        foreach ($config as $typeId => $typeCfg) {
            $path = $row[$typeCfg['col_path']] ?? '';
            $finalTime = $row[$typeCfg['col_final_time']] ?? null;
            $reviewCol = $reviewCols[$typeId] ?? null;
            $reviewStatus = ($reviewCol && isset($row[$reviewCol])) ? $row[$reviewCol] : '未批阅';
            
            if ($path !== '' && $path !== null) {
                // 从路径提取文件名
                $filename = basename($path);
                
                // 格式化提交时间
                $uploadAt = '-';
                if ($finalTime) {
                    if ($finalTime instanceof DateTime) {
                        $uploadAt = $finalTime->format('Y-m-d H:i:s');
                    } else {
                        $uploadAt = date('Y-m-d H:i:s', strtotime($finalTime));
                    }
                }
                
                $items[] = [
                    'name' => $filename,
                    'upload_at' => $uploadAt,
                    'type' => $typeId,
                    'typeName' => $typeCfg['name'],
                    'path' => $path,
                    'reviewResult' => $reviewStatus
                ];
            }
        }
    } else {
        // 如果指定了子目录，扫描文件系统（保留原有逻辑用于子目录浏览）
        $root = realpath(__DIR__ . '/..');
        $base = $root . DIRECTORY_SEPARATOR . 'FileUploadGraduationSubmission' . DIRECTORY_SEPARATOR . $sid;
        $safeDir = str_replace(['..', '\\'], ['', DIRECTORY_SEPARATOR], $dir);
        $cur = rtrim($base . DIRECTORY_SEPARATOR . $safeDir, DIRECTORY_SEPARATOR);
        
        if (is_dir($cur)) {
            $list = @scandir($cur) ?: [];
            foreach ($list as $name) {
                if ($name === '.' || $name === '..') continue;
                if (strpos($name, '.') === 0) continue;
                $full = $cur . DIRECTORY_SEPARATOR . $name;
                if (!is_dir($full)) {
                    $mtime = @filemtime($full) ?: null;
                    $items[] = [
                        'name' => $name,
                        'upload_at' => $mtime ? date('Y-m-d H:i:s', $mtime) : '-',
                        'reviewResult' => '未知' // 这种模式下无法获取数据库状态
                    ];
                }
            }
        }
    }
    
    // 毕业生文件系统不使用文件夹结构，返回空数组
    jsonSuccess(['items' => $items, 'folders' => []]);
    
} catch (Throwable $e) {
    jsonServerError($e);
}
