<?php
/**
 * 获取单个住宿详情（公开接口）
 * GET /api/public/get_accommodation.php?id=1
 */

require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    errorResponse('请求方法不允许', 405);
}

$id = isset($_GET['id']) ? intval($_GET['id']) : 0;
if ($id <= 0) {
    errorResponse('参数错误：缺少住宿ID', 400);
}

try {
    $db = getDB();
    $stmt = $db->prepare("SELECT id, name, category, description, image, price, rating, address, detail_content FROM accommodations WHERE id = :id");
    $stmt->execute([':id' => $id]);
    $accommodation = $stmt->fetch();

    if (!$accommodation) {
        errorResponse('住宿不存在', 404);
    }

    successResponse($accommodation, '获取成功');

} catch (PDOException $e) {
    errorResponse('数据库查询失败: ' . $e->getMessage(), 500);
}
