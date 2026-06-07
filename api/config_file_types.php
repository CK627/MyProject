<?php
/**
 * 配置文件类型接口
 * GET: 获取所有配置
 * POST: 更新配置
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';

// 允许教师管理员访问
setAuthApiHeaders('GET, POST, OPTIONS');
handleOptionsRequest();
initSession();
requireAuth(['admin']); // 仅允许管理员

$db = getGraduationDb();

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    // 获取配置
    $sql = "SELECT type_key, allowed_extensions FROM config_file_types";
    $res = $db->query($sql);
    $items = [];
    while ($row = $res->fetch_assoc()) {
        $items[$row['type_key']] = explode(',', $row['allowed_extensions']);
    }
    jsonSuccess(['items' => $items]);
} elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // 更新配置
    $data = parseRequestBody();
    $typeKey = $data['type_key'] ?? '';
    $exts = $data['allowed_extensions'] ?? []; // Array of extensions
    
    if (!$typeKey || !is_array($exts)) {
        jsonError('参数无效', 400);
    }
    
    // Clean extensions
    $cleanExts = array_map(function($e) {
        return strtolower(trim(preg_replace('/[^a-zA-Z0-9]/', '', $e)));
    }, $exts);
    $cleanExts = array_filter($cleanExts); // Remove empty
    $extStr = implode(',', $cleanExts);
    
    $stmt = $db->prepare("INSERT INTO config_file_types (type_key, allowed_extensions) VALUES (?, ?) ON DUPLICATE KEY UPDATE allowed_extensions = ?");
    $stmt->bind_param('sss', $typeKey, $extStr, $extStr);
    
    if ($stmt->execute()) {
        jsonSuccess(['message' => '配置已更新', 'type' => $typeKey, 'extensions' => $cleanExts]);
    } else {
        jsonServerError(new Exception($stmt->error));
    }
}
