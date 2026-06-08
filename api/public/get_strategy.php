<?php
/**
 * 获取单个攻略详情（公开接口）
 * GET /api/public/get_strategy.php?id=1
 */

require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    errorResponse('请求方法不允许', 405);
}

$id = isset($_GET['id']) ? intval($_GET['id']) : 0;
if ($id <= 0) {
    errorResponse('参数错误：缺少攻略ID', 400);
}

try {
    $db = getDB();
    $stmt = $db->prepare("SELECT id, name, category, description, image, detail_content FROM strategies WHERE id = :id");
    $stmt->execute([':id' => $id]);
    $strategy = $stmt->fetch();

    if (!$strategy) {
        errorResponse('攻略不存在', 404);
    }

    successResponse($strategy, '获取成功');

} catch (PDOException $e) {
    errorResponse('数据库查询失败: ' . $e->getMessage(), 500);
}
