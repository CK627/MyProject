<?php
/**
 * 提交评论（公开接口）
 * POST /api/public/submit_comment.php
 * 参数：
 *   content_type - 必填，内容类型（spot/food/accommodation/transport/strategy）
 *   content_id   - 必填，内容ID
 *   name         - 必填，昵称（最大50字符）
 *   content      - 必填，评论内容（最大500字符）
 */

require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

// 处理 OPTIONS 预检请求（CORS）
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    http_response_code(204);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    errorResponse('请求方法不允许', 405);
}

try {
    // 获取请求数据
    $contentTypeHeader = isset($_SERVER['CONTENT_TYPE']) ? $_SERVER['CONTENT_TYPE'] : '';
    if (strpos($contentTypeHeader, 'application/json') !== false) {
        $input = json_decode(file_get_contents('php://input'), true);
    } else {
        $input = $_POST;
    }

    // 验证必填字段
    $missing = validateRequired(['content_type', 'content_id', 'name', 'content'], $input);
    if ($missing !== null) {
        errorResponse("字段 '{$missing}' 不能为空");
    }

    $contentType = sanitizeInput($input['content_type']);
    $contentId = intval($input['content_id']);
    $name = sanitizeInput($input['name']);
    $content = sanitizeInput($input['content']);

    // 验证内容类型
    $allowedTypes = ['spot', 'food', 'accommodation', 'transport', 'strategy'];
    if (!in_array($contentType, $allowedTypes)) {
        errorResponse('无效的内容类型');
    }

    if ($contentId <= 0) {
        errorResponse('无效的内容ID');
    }

    // 验证长度
    if (mb_strlen($name) > 50) {
        errorResponse('昵称不能超过50个字符');
    }
    if (mb_strlen($content) > 500) {
        errorResponse('评论内容不能超过500个字符');
    }
    if (mb_strlen($name) < 1) {
        errorResponse('请输入昵称');
    }
    if (mb_strlen($content) < 1) {
        errorResponse('请输入评论内容');
    }

    $db = getDB();

    $sql = "INSERT INTO comments (content_type, content_id, name, content, created_at) VALUES (:type, :id, :name, :content, NOW())";
    $stmt = $db->prepare($sql);
    $stmt->execute([
        ':type' => $contentType,
        ':id' => $contentId,
        ':name' => $name,
        ':content' => $content
    ]);

    $newId = $db->lastInsertId();

    $query = $db->prepare("SELECT id, name, content, created_at FROM comments WHERE id = :id");
    $query->execute([':id' => $newId]);
    $comment = $query->fetch();

    successResponse($comment, '评论提交成功');

} catch (PDOException $e) {
    errorResponse('评论提交失败: ' . $e->getMessage(), 500);
}
