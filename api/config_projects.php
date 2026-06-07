<?php
/**
 * 项目管理接口
 * GET: 获取所有项目
 * POST: 添加新项目
 * PUT: 更新项目
 * DELETE: 删除项目
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_config.php';

setAuthApiHeaders('GET, POST, PUT, DELETE, OPTIONS');
handleOptionsRequest();
initSession();
requireAuth(['admin']);

$db = getGraduationDb();
$method = $_SERVER['REQUEST_METHOD'];

// Ensure config_projects table exists by calling getGraduationConfig() once
getGraduationConfig();

if ($method === 'GET') {
    $res = $db->query("SELECT * FROM config_projects ORDER BY id ASC");
    $items = [];
    while ($row = $res->fetch_assoc()) {
        $row['has_template'] = (bool)$row['has_template'];
        $items[] = $row;
    }
    jsonSuccess(['items' => $items]);
} elseif ($method === 'POST') {
    $data = parseRequestBody();
    $name = trim($data['name'] ?? '');
    $has_template = (int)($data['has_template'] ?? 0);
    $template_filename = trim($data['template_filename'] ?? '');
    
    if (!$name) {
        jsonError('项目名称不能为空', 400);
    }
    
    $type_key = 'proj_' . time() . '_' . rand(100, 999);
    $col_path = $type_key;
    $col_dl_count = $type_key . '_dl_count';
    $col_dl_time = $type_key . '_dl_time';
    $col_final_time = $type_key . '_final_time';
    $suffix = $name;
    
    // Add columns to graduation_information
    $review_col = $col_path . '_review_result';
    $anno_col = $col_path . ' Annotation';
    
    $alter_sql = "ALTER TABLE `graduation_information` 
        ADD COLUMN `$col_path` VARCHAR(255) DEFAULT NULL,
        ADD COLUMN `$col_dl_count` INT DEFAULT 0,
        ADD COLUMN `$col_dl_time` DATETIME DEFAULT NULL,
        ADD COLUMN `$col_final_time` DATETIME DEFAULT NULL,
        ADD COLUMN `$review_col` ENUM('未批阅','不通过','通过') DEFAULT '未批阅',
        ADD COLUMN `$anno_col` TEXT DEFAULT NULL";
        
    if (!$db->query($alter_sql)) {
        jsonServerError(new Exception("无法修改表结构: " . $db->error));
    }
    
    // Insert into config_projects
    $stmt = $db->prepare("INSERT INTO config_projects (type_key, name, has_template, template_filename, col_path, col_dl_count, col_dl_time, col_final_time, suffix) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)");
    $stmt->bind_param('ssissssss', $type_key, $name, $has_template, $template_filename, $col_path, $col_dl_count, $col_dl_time, $col_final_time, $suffix);
    
    if ($stmt->execute()) {
        jsonSuccess(['message' => '项目添加成功']);
    } else {
        jsonServerError(new Exception($stmt->error));
    }
} elseif ($method === 'PUT') {
    $data = parseRequestBody();
    $id = (int)($data['id'] ?? 0);
    $name = trim($data['name'] ?? '');
    $has_template = (int)($data['has_template'] ?? 0);
    $template_filename = trim($data['template_filename'] ?? '');
    
    if (!$id || !$name) {
        jsonError('参数无效', 400);
    }
    
    $stmt = $db->prepare("UPDATE config_projects SET name=?, has_template=?, template_filename=? WHERE id=?");
    $stmt->bind_param('sisi', $name, $has_template, $template_filename, $id);
    
    if ($stmt->execute()) {
        jsonSuccess(['message' => '项目更新成功']);
    } else {
        jsonServerError(new Exception($stmt->error));
    }
} elseif ($method === 'DELETE') {
    $data = parseRequestBody();
    $id = (int)($data['id'] ?? 0);
    
    if (!$id) {
        jsonError('参数无效', 400);
    }
    
    // Get col_path to drop columns
    $stmt = $db->prepare("SELECT type_key, col_path FROM config_projects WHERE id=?");
    $stmt->bind_param('i', $id);
    $stmt->execute();
    $res = $stmt->get_result();
    $project = $res->fetch_assoc();
    $stmt->close();
    
    if (!$project) {
        jsonError('项目不存在', 404);
    }
    
    $type_key = $project['type_key'];
    $col_path = $project['col_path'];
    $col_dl_count = $col_path . '_dl_count';
    $col_dl_time = $col_path . '_dl_time';
    $col_final_time = $col_path . '_final_time';
    $review_col = $col_path . '_review_result';
    $anno_col = $col_path . ' Annotation';
    
    // MySQL max column name length is 64 characters
    if (strlen($review_col) > 64) {
        $review_col = substr($col_path, 0, 64 - strlen('_review_result')) . '_review_result';
    }
    if (strlen($anno_col) > 64) {
        $anno_col = substr($col_path, 0, 64 - strlen(' Annotation')) . ' Annotation';
    }
    
    // Drop columns from graduation_information if they exist
    // We can do this in a single query or suppress errors if columns don't exist.
    $cols_to_drop = [$col_path, $col_dl_count, $col_dl_time, $col_final_time, $review_col, $anno_col];
    foreach ($cols_to_drop as $col) {
        $db->query("ALTER TABLE `graduation_information` DROP COLUMN `$col`");
    }
    
    // Delete from config_file_types as well
    $stmt = $db->prepare("DELETE FROM config_file_types WHERE type_key=?");
    $stmt->bind_param('s', $type_key);
    $stmt->execute();
    $stmt->close();
    
    // Delete from config_projects
    $stmt = $db->prepare("DELETE FROM config_projects WHERE id=?");
    $stmt->bind_param('i', $id);
    
    if ($stmt->execute()) {
        jsonSuccess(['message' => '项目删除成功']);
    } else {
        jsonServerError(new Exception($stmt->error));
    }
} else {
    jsonError('Method not allowed', 405);
}
