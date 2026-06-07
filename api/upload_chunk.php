<?php
/**
 * 分片上传接口
 * 目的：绕过 post_max_size / upload_max_filesize 限制，通过小分片逐个上传并在服务器端合并。
 * 请求：multipart/form-data
 *   - username: 纯数字用户名
 *   - dir: 目标相对目录（可为空，表示根）
 *   - filename: 原始文件名
 *   - upload_id: 客户端生成的唯一 ID（用于分片目录）
 *   - chunk_index: 当前分片索引（从 0 开始）
 *   - total_chunks: 分片总数
 *   - chunk: 当前分片二进制内容（文件字段）
 * 响应：
 *   - 非最后一片：{ ok: true, received: chunk_index }
 *   - 最后一片：{ ok: true, path: '/File/{username}/{dir}/{filename}' }
 */

require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/ChunkUploader.php';

// 设置响应头并处理预检
ChunkUploader::setHeaders();
ChunkUploader::handleOptions();
ChunkUploader::validateMethod();

// 解析参数
$params = ChunkUploader::parseParams();
if ($params === null) {
    exit;
}

// 确认用户存在
try {
    $userDb = getDb();
    $stmt = $userDb->prepare('SELECT id FROM Users WHERE username = ? LIMIT 1');
    $stmt->bind_param('s', $params['username']);
    $stmt->execute();
    $res = $stmt->get_result();
    $row = $res->fetch_assoc();
    $stmt->close();
    if (!$row) {
        ChunkUploader::error(401, '未登录或用户不存在');
    }
} catch (Throwable $e) {
    ChunkUploader::error(500, '服务器内部错误');
}

// 创建上传器
$uploader = new ChunkUploader($params, 'File', $params['dir']);

// 设置合并完成回调
$uploader->setMergeCompleteCallback(function(string $finalPath, string $relativePath) use ($params) {
    // 写入数据库
    $filesDb = getFilesDb();
    $table = ensureUserTable($filesDb, $params['username']);
    $relative = '/' . $relativePath;
    
    $stmt = $filesDb->prepare("INSERT INTO `{$table}` (file_path) VALUES (?)");
    $stmt->bind_param('s', $relative);
    $stmt->execute();
    $stmt->close();

    // 记录审计日志
    logAudit($params['username'], AUDIT_UPLOAD, $relative, ['filename' => $params['filename']]);

    ChunkUploader::success(['path' => $relative]);
});

// 处理上传
$uploader->handle();