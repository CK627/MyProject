<?php
/**
 * 审计日志查询接口（仅管理员可用）
 * - GET: 查询审计日志列表
 * - 参数: username, action, start_date, end_date, limit, offset
 */

require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

initApiRequest('GET');

// 验证管理员权限（简单实现：通过 header 传递管理员用户名）
$adminUser = $_GET['admin'] ?? '';
if ($adminUser === '') {
    jsonError('需要管理员权限', 403);
}

// 验证是否为管理员
try {
    $db = getDb();
    $stmt = $db->prepare('SELECT id FROM admins WHERE username = ? LIMIT 1');
    $stmt->bind_param('s', $adminUser);
    $stmt->execute();
    $res = $stmt->get_result();
    $row = $res->fetch_assoc();
    $stmt->close();
    
    if (!$row) {
        jsonError('非管理员用户', 403);
    }
} catch (Throwable $e) {
    jsonServerError($e);
}

// 解析筛选参数
$filters = [];
if (!empty($_GET['username'])) {
    $filters['username'] = $_GET['username'];
}
if (!empty($_GET['action'])) {
    $filters['action'] = $_GET['action'];
}
if (!empty($_GET['start_date'])) {
    $filters['start_date'] = $_GET['start_date'];
}
if (!empty($_GET['end_date'])) {
    $filters['end_date'] = $_GET['end_date'];
}

$limit = min(500, max(1, (int)($_GET['limit'] ?? 100)));
$offset = max(0, (int)($_GET['offset'] ?? 0));

try {
    $logs = getAuditLogs($filters, $limit, $offset);
    jsonSuccess(['items' => $logs, 'count' => count($logs)]);
} catch (Throwable $e) {
    jsonServerError($e);
}
