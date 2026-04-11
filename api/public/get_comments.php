<?php
/**
 * 获取评论列表（公开接口）
 * GET /api/public/get_comments.php?type=spot&id=1
 */

require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    errorResponse('请求方法不允许', 405);
}

$contentType = isset($_GET['type']) ? sanitizeInput($_GET['type']) : '';
$contentId = isset($_GET['id']) ? intval($_GET['id']) : 0;

$allowedTypes = ['spot', 'food', 'accommodation', 'transport', 'strategy'];
if (!in_array($contentType, $allowedTypes)) {
    errorResponse('无效的内容类型', 400);
}
if ($contentId <= 0) {
    errorResponse('缺少内容ID', 400);
}

try {
    $db = getDB();

    // 获取总数
    $countStmt = $db->prepare("SELECT COUNT(*) as total FROM comments WHERE content_type = :type AND content_id = :id");
    $countStmt->execute([':type' => $contentType, ':id' => $contentId]);
    $total = $countStmt->fetch()['total'];

    // 获取评论列表
    $sql = "SELECT id, name, content, created_at FROM comments WHERE content_type = :type AND content_id = :id ORDER BY created_at DESC LIMIT 100";
    $stmt = $db->prepare($sql);
    $stmt->execute([':type' => $contentType, ':id' => $contentId]);
    $comments = $stmt->fetchAll();

    successResponse([
        'list'  => $comments,
        'total' => (int)$total
    ], '获取成功');

} catch (PDOException $e) {
    errorResponse('数据库查询失败: ' . $e->getMessage(), 500);
}
