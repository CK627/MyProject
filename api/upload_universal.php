<?php
/**
 * 通用分片上传接口
 */

require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/ChunkUploader.php';
require_once __DIR__ . '/graduation_util.php';
require_once __DIR__ . '/graduation_config.php';
require_once __DIR__ . '/ReviewHelper.php';

// 设置响应头并处理预检
ChunkUploader::setHeaders();
ChunkUploader::handleOptions();
ChunkUploader::validateMethod();

// 解析参数
$params = ChunkUploader::parseParams();
if ($params === null) {
    exit;
}

// 获取额外的 type 参数
$type = $_POST['file_type'] ?? '';
$config = getGraduationConfig();

if (!isset($config[$type])) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => '无效的文件类型']);
    exit;
}

$conf = $config[$type];
$studentID = $params['studentID'];
$colPath = $conf['col_path'];
$colFinalTime = $conf['col_final_time'];
$suffix = $conf['suffix'];

// 检查文件扩展名限制
if (isset($conf['allowed_extensions']) && is_array($conf['allowed_extensions'])) {
    $filename = $params['filename'];
    $ext = strtolower(pathinfo($filename, PATHINFO_EXTENSION));
    if (!in_array($ext, $conf['allowed_extensions'])) {
        http_response_code(400);
        $allowed = implode(', ', $conf['allowed_extensions']);
        echo json_encode(['ok' => false, 'error' => "仅允许上传以下格式: {$allowed}"]);
        exit;
    }
}

// 创建上传器
$uploader = new ChunkUploader($params, 'FileUploadGraduationSubmission');

// 设置最终文件名生成器
$uploader->setFinalNameGenerator(function(string $filename) use ($studentID, $suffix) {
    return generateGraduationFileName($studentID, $filename, $suffix);
});

// 设置合并完成回调
$uploader->setMergeCompleteCallback(function(string $finalPath, string $relativePath) use ($params, $studentID, $uploader, $colPath, $colFinalTime, $suffix, $type) {
    $db = getGraduationDb();
    
    // 确保字段存在 (仅做简单的尝试，不强制，因为之前的脚本已经处理过)
    try {
        $db->query("ALTER TABLE `graduation_information` ADD COLUMN IF NOT EXISTS `$colFinalTime` DATETIME NULL COMMENT '{$suffix}最终提交时间'");
    } catch (Throwable $__) {}
    
    // 如果是替换模式，删除旧文件
    if ($uploader->isReplace()) {
        deleteOldGraduationFile($db, $studentID, $colPath, $relativePath, $uploader->getRoot());
    }
    
    // 更新数据库 - 同时重置审查结果和批注
    $reviewCol = ReviewHelper::getReviewColumn($type);
    $annoCol = ReviewHelper::getAnnotationColumn($type);
    
    $sql = "UPDATE `graduation_information` SET `$colPath` = ?, `$colFinalTime` = NOW()";
    
    // 如果有审查字段，则重置为默认值
    if ($reviewCol) {
        $sql .= ", `$reviewCol` = '未批阅'";
    }
    if ($annoCol) {
        $sql .= ", `$annoCol` = NULL";
    }
    
    $sql .= " WHERE `studentID` = ?";
    
    $stmt = $db->prepare($sql);
    $stmt->bind_param('ss', $relativePath, $studentID);
    $stmt->execute();
    $stmt->close();
    
    ChunkUploader::success(['path' => $relativePath]);
});

// 处理上传
$uploader->handle();
