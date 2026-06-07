<?php
/**
 * 查询已上传分片接口（支持断点续传）
 * - POST JSON: { username, upload_id }
 * - 返回: { ok: true, uploaded_chunks: [0,1,2,...], total_expected: int|null }
 */

require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

initApiRequest('POST');

$data = parseRequestBody();
$username = validateUsername((string)($data['username'] ?? ''));
$uploadId = trim((string)($data['upload_id'] ?? ''));

if ($uploadId === '') {
    jsonError('缺少 upload_id 参数');
}

// 验证用户存在
try {
    $db = getDb();
    $stmt = $db->prepare('SELECT id FROM Users WHERE username = ? LIMIT 1');
    $stmt->bind_param('s', $username);
    $stmt->execute();
    $res = $stmt->get_result();
    $row = $res->fetch_assoc();
    $stmt->close();
    if (!$row) {
        jsonError('未登录或用户不存在', 401);
    }
} catch (Throwable $e) {
    jsonServerError($e);
}

// 查找分片目录
$root = realpath(__DIR__ . '/..');
$chunksDir = $root . DIRECTORY_SEPARATOR . 'File' . DIRECTORY_SEPARATOR . $username . DIRECTORY_SEPARATOR . '.chunks' . DIRECTORY_SEPARATOR . $uploadId . DIRECTORY_SEPARATOR;

$uploadedChunks = [];
if (is_dir($chunksDir)) {
    $files = scandir($chunksDir);
    foreach ($files as $file) {
        if (preg_match('/^chunk_(\d+)$/', $file, $matches)) {
            $uploadedChunks[] = (int)$matches[1];
        }
    }
    sort($uploadedChunks);
}

jsonSuccess([
    'uploaded_chunks' => $uploadedChunks,
    'count' => count($uploadedChunks)
]);
