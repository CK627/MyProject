<?php
/**
 * 获取攻略列表（公开接口）
 * GET /api/public/get_strategies.php
 */

require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    errorResponse('请求方法不允许', 405);
}

try {
    $db = getDB();
    
    $where = [];
    $params = [];

    if (!empty($_GET['category'])) {
        $where[] = 'category = :category';
        $params[':category'] = sanitizeInput($_GET['category']);
    }

    $whereClause = !empty($where) ? 'WHERE ' . implode(' AND ', $where) : '';

    $countStmt = $db->prepare("SELECT COUNT(*) as total FROM strategies $whereClause");
    $countStmt->execute($params);
    $total = $countStmt->fetch()['total'];

    list($page, $pageSize, $offset) = getPagination();

    $sql = "SELECT id, name, category, description, image, sort_order 
            FROM strategies 
            $whereClause 
            ORDER BY sort_order ASC, id DESC 
            LIMIT :limit OFFSET :offset";

    $stmt = $db->prepare($sql);
    foreach ($params as $key => $value) {
        $stmt->bindValue($key, $value);
    }
    $stmt->bindValue(':limit', $pageSize, PDO::PARAM_INT);
    $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
    $stmt->execute();

    $strategies = $stmt->fetchAll();

    successResponse([
        'list'     => $strategies,
        'total'    => (int)$total,
        'page'     => $page,
        'pageSize' => $pageSize
    ], '获取成功');

} catch (PDOException $e) {
    errorResponse('数据库查询失败: ' . $e->getMessage(), 500);
}
