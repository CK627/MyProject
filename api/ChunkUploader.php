<?php
/**
 * 分片上传公共类
 * 统一处理分片上传的通用逻辑：参数验证、分片保存、分片合并、清理
 * 
 * 使用方式：
 * 1. 创建实例并配置
 * 2. 调用 handleRequest() 处理请求
 * 3. 如果是最后一片，调用 onMergeComplete 回调处理业务逻辑
 */
class ChunkUploader {
    // 配置项
    private string $baseDir;           // 基础存储目录
    private string $username;          // 用户名
    private string $filename;          // 原始文件名
    private string $uploadId;          // 上传ID
    private int $chunkIndex;           // 当前分片索引
    private int $totalChunks;          // 分片总数
    private bool $replace;             // 是否替换
    private string $chunksDir;         // 分片临时目录
    private string $root;              // 项目根目录

    // 回调函数
    private $onMergeComplete = null;   // 合并完成回调
    private $generateFinalName = null; // 生成最终文件名回调

    /**
     * 设置通用响应头
     */
    public static function setHeaders(): void {
        header('Content-Type: application/json; charset=utf-8');
        // 支持跨域 Cookie：Origin 必须是具体值（不能是 *）
        $origin = $_SERVER['HTTP_ORIGIN'] ?? '';
        if ($origin !== '') {
            header('Access-Control-Allow-Origin: ' . $origin);
        } else {
            header('Access-Control-Allow-Origin: *');
        }
        header('Access-Control-Allow-Methods: POST, OPTIONS');
        header('Access-Control-Allow-Credentials: true');
        header('Access-Control-Allow-Headers: Content-Type, X-Requested-With');
    }

    /**
     * 处理 OPTIONS 预检请求
     */
    public static function handleOptions(): bool {
        if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
            http_response_code(204);
            exit;
        }
        return true;
    }

    /**
     * 验证请求方法
     */
    public static function validateMethod(): bool {
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            self::error(405, 'Method Not Allowed');
            return false;
        }
        return true;
    }

    /**
     * 从 POST 读取并验证通用参数
     * @return array|null 参数数组，验证失败返回 null
     */
    public static function parseParams(): ?array {
        $username = trim((string)($_POST['username'] ?? ''));
        $studentID = trim((string)($_POST['studentID'] ?? $username));
        $filename = basename((string)($_POST['filename'] ?? ''));
        $uploadId = trim((string)($_POST['upload_id'] ?? ''));
        $chunkIndex = (int)($_POST['chunk_index'] ?? -1);
        $totalChunks = (int)($_POST['total_chunks'] ?? 0);
        $replace = isset($_POST['replace']) ? (bool)(int)$_POST['replace'] : false;
        $dir = trim((string)($_POST['dir'] ?? ''));

        // 验证用户名
        if ($username === '' || !preg_match('/^[0-9]+$/', $username)) {
            self::error(400, '用户名必须为纯数字');
            return null;
        }

        // 验证分片参数
        if ($filename === '' || $uploadId === '' || $chunkIndex < 0 || $totalChunks <= 0 || $chunkIndex >= $totalChunks) {
            self::error(400, '分片参数错误');
            return null;
        }

        // 验证分片文件
        if (!isset($_FILES['chunk'])) {
            self::error(400, '缺少分片内容');
            return null;
        }
        if ((int)$_FILES['chunk']['error'] !== UPLOAD_ERR_OK) {
            self::error(400, '分片上传失败');
            return null;
        }

        return [
            'username' => $username,
            'studentID' => $studentID,
            'filename' => $filename,
            'uploadId' => $uploadId,
            'chunkIndex' => $chunkIndex,
            'totalChunks' => $totalChunks,
            'replace' => $replace,
            'dir' => $dir,
        ];
    }

    /**
     * 构造函数
     * @param array $params 参数数组（来自 parseParams）
     * @param string $storageFolder 存储文件夹名（如 'File', 'FileUploadGraduationSubmission'）
     * @param string $subDir 子目录（可选）
     */
    public function __construct(array $params, string $storageFolder, string $subDir = '') {
        $this->username = $params['username'];
        $this->filename = $params['filename'];
        $this->uploadId = $params['uploadId'];
        $this->chunkIndex = $params['chunkIndex'];
        $this->totalChunks = $params['totalChunks'];
        $this->replace = $params['replace'];

        $this->root = realpath(__DIR__ . '/..');
        
        // 构建基础目录
        $this->baseDir = $this->root . DIRECTORY_SEPARATOR . $storageFolder . DIRECTORY_SEPARATOR . $this->username . DIRECTORY_SEPARATOR;
        if ($subDir !== '') {
            $relDir = trim(str_replace(['\\'], '/', $subDir), '/');
            $this->baseDir .= $relDir . DIRECTORY_SEPARATOR;
        }

        // 分片临时目录
        $userBaseDir = $this->root . DIRECTORY_SEPARATOR . $storageFolder . DIRECTORY_SEPARATOR . $this->username . DIRECTORY_SEPARATOR;
        $this->chunksDir = $userBaseDir . '.chunks' . DIRECTORY_SEPARATOR . $this->uploadId . DIRECTORY_SEPARATOR;
    }

    /**
     * 设置最终文件名生成回调
     * @param callable $callback function(string $originalFilename): string
     */
    public function setFinalNameGenerator(callable $callback): self {
        $this->generateFinalName = $callback;
        return $this;
    }

    /**
     * 设置合并完成回调
     * @param callable $callback function(string $finalPath, string $relativePath): void
     */
    public function setMergeCompleteCallback(callable $callback): self {
        $this->onMergeComplete = $callback;
        return $this;
    }

    /**
     * 处理分片上传请求
     * @return bool 成功返回 true
     */
    public function handle(): bool {
        // 1. 保存分片
        if (!$this->saveChunk()) {
            return false;
        }

        // 2. 非最后一片，返回成功
        if ($this->chunkIndex < $this->totalChunks - 1) {
            self::success(['received' => $this->chunkIndex]);
            return true;
        }

        // 3. 最后一片，合并分片
        return $this->mergeChunks();
    }

    /**
     * 保存当前分片
     */
    private function saveChunk(): bool {
        // 创建分片目录
        if (!is_dir($this->chunksDir)) {
            if (!mkdir($this->chunksDir, 0755, true) && !is_dir($this->chunksDir)) {
                self::error(500, '无法创建分片目录');
                return false;
            }
        }

        // 保存分片
        $chunkPath = $this->chunksDir . 'chunk_' . $this->chunkIndex;
        if (!move_uploaded_file($_FILES['chunk']['tmp_name'], $chunkPath)) {
            self::error(500, '分片保存失败');
            return false;
        }

        return true;
    }

    /**
     * 合并所有分片
     */
    private function mergeChunks(): bool {
        try {
            // 创建目标目录
            if (!is_dir($this->baseDir)) {
                if (!mkdir($this->baseDir, 0755, true) && !is_dir($this->baseDir)) {
                    throw new RuntimeException('无法创建目标目录');
                }
            }

            // 生成最终文件名
            $finalName = $this->filename;
            if ($this->generateFinalName !== null) {
                $finalName = call_user_func($this->generateFinalName, $this->filename);
            }

            $finalPath = $this->baseDir . $finalName;

            // 检查文件是否存在
            if (file_exists($finalPath)) {
                if (!$this->replace) {
                    self::error(409, '文件已存在');
                    return false;
                }
                @unlink($finalPath);
            }

            // 合并分片
            $out = fopen($finalPath, 'wb');
            if (!$out) {
                throw new RuntimeException('无法打开目标文件');
            }

            for ($i = 0; $i < $this->totalChunks; $i++) {
                $part = $this->chunksDir . 'chunk_' . $i;
                $in = fopen($part, 'rb');
                if (!$in) {
                    fclose($out);
                    throw new RuntimeException('读取分片失败: ' . $i);
                }
                stream_copy_to_stream($in, $out);
                fclose($in);
            }
            fclose($out);
            @chmod($finalPath, 0444);

            // 清理分片
            $this->cleanupChunks();

            // 计算相对路径
            $relativePath = str_replace($this->root . DIRECTORY_SEPARATOR, '', $finalPath);
            $relativePath = str_replace(DIRECTORY_SEPARATOR, '/', $relativePath);

            // 调用合并完成回调
            if ($this->onMergeComplete !== null) {
                call_user_func($this->onMergeComplete, $finalPath, $relativePath);
            } else {
                self::success(['path' => $relativePath]);
            }

            return true;

        } catch (Throwable $e) {
            self::error(500, '合并失败');
            return false;
        }
    }

    /**
     * 清理分片文件
     */
    private function cleanupChunks(): void {
        for ($i = 0; $i < $this->totalChunks; $i++) {
            @unlink($this->chunksDir . 'chunk_' . $i);
        }
        @rmdir($this->chunksDir);
    }

    /**
     * 获取项目根目录
     */
    public function getRoot(): string {
        return $this->root;
    }

    /**
     * 获取用户名
     */
    public function getUsername(): string {
        return $this->username;
    }

    /**
     * 获取是否替换标志
     */
    public function isReplace(): bool {
        return $this->replace;
    }

    /**
     * 输出成功响应
     */
    public static function success(array $data = []): void {
        echo json_encode(array_merge(['ok' => true], $data));
    }

    /**
     * 输出错误响应
     */
    public static function error(int $code, string $message): void {
        http_response_code($code);
        echo json_encode(['ok' => false, 'error' => $message]);
        exit;
    }
}
