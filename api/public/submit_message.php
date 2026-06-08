<?php
/**
 * 提交留言（公开接口）
 * POST /api/public/submit_message.php
 * 参数（POST）：
 *   name    - 必填，昵称（最大50字符）
 *   content - 必填，留言内容（最大500字符）
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

// 仅允许 POST 请求
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    errorResponse('请求方法不允许', 405);
}

try {
    // 获取请求数据（支持 JSON 和表单提交）
    $contentType = isset($_SERVER['CONTENT_TYPE']) ? $_SERVER['CONTENT_TYPE'] : '';

    if (strpos($contentType, 'application/json') !== false) {
        $input = json_decode(file_get_contents('php://input'), true);
    } else {
        $input = $_POST;
    }

    // 验证必填字段
    $missing = validateRequired(['name', 'content'], $input);
    if ($missing !== null) {
        errorResponse("字段 '{$missing}' 不能为空");
    }

    // 过滤输入
    $name = sanitizeInput($input['name']);
    $content = sanitizeInput($input['content']);

    // 验证长度
    if (mb_strlen($name) > 50) {
        errorResponse('昵称不能超过50个字符');
    }
    if (mb_strlen($content) > 500) {
        errorResponse('留言内容不能超过500个字符');
    }
    if (mb_strlen($name) < 1) {
        errorResponse('请输入昵称');
    }
    if (mb_strlen($content) < 1) {
        errorResponse('请输入留言内容');
    }

    $db = getDB();

    // 插入留言
    $sql = "INSERT INTO messages (name, content, created_at) VALUES (:name, :content, NOW())";
    $stmt = $db->prepare($sql);
    $stmt->bindValue(':name', $name);
    $stmt->bindValue(':content', $content);
    $stmt->execute();

    $newId = $db->lastInsertId();

    // 返回新插入的留言数据
    $query = $db->prepare("SELECT id, name, content, created_at FROM messages WHERE id = :id");
    $query->bindValue(':id', $newId, PDO::PARAM_INT);
    $query->execute();
    $message = $query->fetch();

    successResponse($message, '留言提交成功');

} catch (PDOException $e) {
    errorResponse('留言提交失败: ' . $e->getMessage(), 500);
}
