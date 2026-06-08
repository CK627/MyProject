<?php
/**
 * 获取景点列表（公开接口）
 * GET /api/public/get_spots.php
 * 参数：
 *   category  - 可选，按分类筛选（自然风光/人文古迹/红色研学）
 *   keyword   - 可选，按关键词搜索
 *   page      - 可选，页码（默认1）
 *   pageSize  - 可选，每页条数（默认10）
 */

require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

// 仅允许 GET 请求
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    errorResponse('请求方法不允许', 405);
}

try {
    $db = getDB();

    // 构建查询条件
    $where = [];
    $params = [];

    // 按分类筛选
    if (!empty($_GET['category'])) {
        $category = sanitizeInput($_GET['category']);
        $where[] = 'category = :category';
        $params[':category'] = $category;
    }

    // 按关键词搜索
    if (!empty($_GET['keyword'])) {
        $keyword = sanitizeInput($_GET['keyword']);
        $where[] = '(name LIKE :keyword OR description LIKE :keyword2)';
        $params[':keyword'] = '%' . $keyword . '%';
        $params[':keyword2'] = '%' . $keyword . '%';
    }

    $whereClause = '';
    if (!empty($where)) {
        $whereClause = 'WHERE ' . implode(' AND ', $where);
    }

    // 获取总数
    $countSql = "SELECT COUNT(*) as total FROM spots $whereClause";
    $countStmt = $db->prepare($countSql);
    $countStmt->execute($params);
    $total = $countStmt->fetch()['total'];

    // 分页
    list($page, $pageSize, $offset) = getPagination();

    // 查询景点列表
    $sql = "SELECT id, name, category, description, image, address, ticket, level, sort_order 
            FROM spots 
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

    $spots = $stmt->fetchAll();

    successResponse([
        'list'     => $spots,
        'total'    => (int)$total,
        'page'     => $page,
        'pageSize' => $pageSize
    ], '获取成功');

} catch (PDOException $e) {
    errorResponse('数据库查询失败: ' . $e->getMessage(), 500);
}
