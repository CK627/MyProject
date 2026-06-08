<?php
/**
 * 获取单个景点详情（公开接口）
 * GET /api/public/get_spot.php?id=1
 */

require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    errorResponse('请求方法不允许', 405);
}

$id = isset($_GET['id']) ? intval($_GET['id']) : 0;
if ($id <= 0) {
    errorResponse('参数错误：缺少景点ID', 400);
}

try {
    $db = getDB();
    $stmt = $db->prepare("SELECT id, name, category, description, image, address, ticket, level, detail_content FROM spots WHERE id = :id");
    $stmt->execute([':id' => $id]);
    $spot = $stmt->fetch();

    if (!$spot) {
        errorResponse('景点不存在', 404);
    }

    successResponse($spot, '获取成功');

} catch (PDOException $e) {
    errorResponse('数据库查询失败: ' . $e->getMessage(), 500);
}
