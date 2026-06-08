<?php
/**
 * 获取留言列表（公开接口）
 * GET /api/public/get_messages.php
 * 参数：
 *   page     - 可选，页码（默认1）
 *   pageSize - 可选，每页条数（默认20）
 */

require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

// 仅允许 GET 请求
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    errorResponse('请求方法不允许', 405);
}

try {
    $db = getDB();

    // 获取总数
    $countStmt = $db->query("SELECT COUNT(*) as total FROM messages");
    $total = $countStmt->fetch()['total'];

    // 分页
    list($page, $pageSize, $offset) = getPagination();

    // 查询留言列表（按时间倒序）
    $sql = "SELECT id, name, content, created_at 
            FROM messages 
            ORDER BY created_at DESC 
            LIMIT :limit OFFSET :offset";

    $stmt = $db->prepare($sql);
    $stmt->bindValue(':limit', $pageSize, PDO::PARAM_INT);
    $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
    $stmt->execute();

    $messages = $stmt->fetchAll();

    successResponse([
        'list'     => $messages,
        'total'    => (int)$total,
        'page'     => $page,
        'pageSize' => $pageSize
    ], '获取成功');

} catch (PDOException $e) {
    errorResponse('数据库查询失败: ' . $e->getMessage(), 500);
}
