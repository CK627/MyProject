<?php
/**
 * 辅助函数：用户名片段清洗、按需建表、统一响应处理、日志记录
 * 说明：为何分离？为了避免重复实现并在多个接口复用；保持单一职责与易维护。
 */

// =========================
// 全局错误处理（确保所有错误输出为 JSON）
// =========================

// 禁止 PHP 直接输出错误到页面
ini_set('display_errors', '0');
ini_set('display_startup_errors', '0');
error_reporting(E_ALL);

// 注册全局错误处理器
set_error_handler(function($errno, $errstr, $errfile, $errline) {
    // 记录到日志
    $logDir = __DIR__ . '/../logs';
    if (!is_dir($logDir)) @mkdir($logDir, 0755, true);
    $logFile = $logDir . '/php_errors_' . date('Y-m-d') . '.log';
    $msg = sprintf("[%s] PHP Error (%d): %s in %s:%d\n", date('Y-m-d H:i:s'), $errno, $errstr, $errfile, $errline);
    @file_put_contents($logFile, $msg, FILE_APPEND | LOCK_EX);
    
    // 不输出任何内容，让异常处理器来处理
    return true;
});

// 注册全局异常处理器
set_exception_handler(function($e) {
    // 记录到日志
    $logDir = __DIR__ . '/../logs';
    if (!is_dir($logDir)) @mkdir($logDir, 0755, true);
    $logFile = $logDir . '/php_errors_' . date('Y-m-d') . '.log';
    $msg = sprintf("[%s] Uncaught Exception: %s in %s:%d\n%s\n", 
        date('Y-m-d H:i:s'), $e->getMessage(), $e->getFile(), $e->getLine(), $e->getTraceAsString());
    @file_put_contents($logFile, $msg, FILE_APPEND | LOCK_EX);
    
    // 输出 JSON 错误响应
    if (!headers_sent()) {
        header('Content-Type: application/json; charset=utf-8');
        http_response_code(500);
    }
    echo json_encode(['ok' => false, 'error' => '服务器内部错误']);
    exit;
});

// 注册关闭函数处理致命错误
register_shutdown_function(function() {
    $error = error_get_last();
    if ($error && in_array($error['type'], [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR])) {
        // 记录到日志
        $logDir = __DIR__ . '/../logs';
        if (!is_dir($logDir)) @mkdir($logDir, 0755, true);
        $logFile = $logDir . '/php_errors_' . date('Y-m-d') . '.log';
        $msg = sprintf("[%s] Fatal Error: %s in %s:%d\n", 
            date('Y-m-d H:i:s'), $error['message'], $error['file'], $error['line']);
        @file_put_contents($logFile, $msg, FILE_APPEND | LOCK_EX);
        
        // 清除已输出的内容
        if (ob_get_level()) ob_end_clean();
        
        // 输出 JSON 错误响应
        if (!headers_sent()) {
            header('Content-Type: application/json; charset=utf-8');
            http_response_code(500);
        }
        echo json_encode(['ok' => false, 'error' => '服务器内部错误']);
    }
});

require_once __DIR__ . '/db_files.php';

// =========================
// 环境与常量配置
// =========================

/**
 * 是否为生产环境
 * 可通过环境变量 APP_ENV=production 或在此处直接配置
 */
define('IS_PRODUCTION', getenv('APP_ENV') === 'production');

/**
 * 分片大小（字节）- 2MB
 */
define('CHUNK_SIZE', 2 * 1024 * 1024);

/**
 * 分片大小（可读格式）
 */
define('CHUNK_SIZE_MB', 2);

// =========================
// Session 认证功能
// =========================

/**
 * Session 配置常量
 */
define('SESSION_LIFETIME', 7200);      // Session 有效期 2 小时
define('SESSION_NAME', 'FUSESSION');   // Session Cookie 名称

/**
 * 初始化 Session（安全配置）
 */
function initSession(): void {
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }
    
    // 配置 Session
    ini_set('session.use_strict_mode', '1');
    ini_set('session.use_only_cookies', '1');
    ini_set('session.cookie_httponly', '1');
    ini_set('session.gc_maxlifetime', (string)SESSION_LIFETIME);
    
    // 生产环境启用 Secure Cookie
    if (IS_PRODUCTION) {
        ini_set('session.cookie_secure', '1');
    }
    
    session_name(SESSION_NAME);
    session_set_cookie_params([
        'lifetime' => SESSION_LIFETIME,
        'path' => '/',
        'httponly' => true,
        'samesite' => 'Lax'
    ]);
    
    session_start();
}

/**
 * 登录用户（创建 Session）
 * @param int $userId 用户 ID
 * @param string $username 用户名
 * @param string $role 角色：user/admin/graduation
 */
function sessionLogin(int $userId, string $username, string $role = 'user'): void {
    initSession();
    
    // 重生 Session ID 防止固定攻击
    session_regenerate_id(true);
    
    $_SESSION['user_id'] = $userId;
    $_SESSION['username'] = $username;
    $_SESSION['role'] = $role;
    $_SESSION['login_time'] = time();
    $_SESSION['last_activity'] = time();
    $_SESSION['ip'] = $_SERVER['REMOTE_ADDR'] ?? '';
}

/**
 * 登出用户（销毁 Session）
 */
function sessionLogout(): void {
    initSession();
    
    // 清空 Session 数据
    $_SESSION = [];
    
    // 删除 Session Cookie
    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(
            session_name(),
            '',
            time() - 42000,
            $params['path'],
            $params['domain'],
            $params['secure'],
            $params['httponly']
        );
    }
    
    // 销毁 Session
    session_destroy();
}

/**
 * 检查是否已登录
 * @return bool
 */
function isLoggedIn(): bool {
    initSession();
    
    if (empty($_SESSION['user_id']) || empty($_SESSION['username'])) {
        return false;
    }
    
    // 检查 Session 是否过期
    $lastActivity = $_SESSION['last_activity'] ?? 0;
    if (time() - $lastActivity > SESSION_LIFETIME) {
        sessionLogout();
        return false;
    }
    
    // 更新最后活动时间
    $_SESSION['last_activity'] = time();
    
    return true;
}

/**
 * 获取当前登录用户信息
 * @return array|null ['user_id', 'username', 'role']
 */
function getCurrentUser(): ?array {
    if (!isLoggedIn()) {
        return null;
    }
    
    return [
        'user_id' => $_SESSION['user_id'],
        'username' => $_SESSION['username'],
        'role' => $_SESSION['role'] ?? 'user',
        'login_time' => $_SESSION['login_time'] ?? 0
    ];
}

/**
 * 要求必须登录（未登录则返回 401 错误）
 * @param array $allowedRoles 允许的角色，空数组表示允许所有角色
 * @return array 当前用户信息
 */
function requireAuth(array $allowedRoles = []): array {
    $user = getCurrentUser();
    
    if ($user === null) {
        jsonError('未登录或会话已过期，请重新登录', 401);
    }
    
    // 检查角色权限
    if (!empty($allowedRoles) && !in_array($user['role'], $allowedRoles, true)) {
        jsonError('无权访问', 403);
    }
    
    return $user;
}

/**
 * 要求管理员登录
 * @return array 当前管理员信息
 */
function requireAdmin(): array {
    return requireAuth(['admin']);
}

/**
 * 渐进式认证：优先使用 Session，回退到请求参数
 * 这种方式保持向后兼容，同时支持新的 Session 认证
 * @param string|null $requestUsername 请求中传入的用户名
 * @return string 经过验证的用户名
 */
function getAuthenticatedUser(?string $requestUsername = null): string {
    // 优先检查 Session
    $sessionUser = getCurrentUser();
    
    if ($sessionUser !== null) {
        $sessionUsername = $sessionUser['username'];
        
        // 如果请求中也有 username，验证一致性
        if ($requestUsername !== null && $requestUsername !== '' && $requestUsername !== $sessionUsername) {
            // 允许管理员代操作
            if ($sessionUser['role'] !== 'admin') {
                jsonError('用户身份不匹配', 403);
            }
            // 管理员可以代操作其他用户
            return validateUsername($requestUsername);
        }
        
        return $sessionUsername;
    }
    
    // 回退到请求参数（向后兼容）
    if ($requestUsername === null || $requestUsername === '') {
        jsonError('未登录或会话已过期', 401);
    }
    
    return validateUsername($requestUsername);
}

/**
 * 渐进式管理员认证：优先使用 Session，回退到请求参数
 * @param string|null $requestAdminUsername 请求中传入的管理员用户名
 * @return string 经过验证的管理员用户名
 */
function getAuthenticatedAdmin(?string $requestAdminUsername = null): string {
    // 优先检查 Session
    $sessionUser = getCurrentUser();
    
    if ($sessionUser !== null) {
        if ($sessionUser['role'] !== 'admin') {
            jsonError('需要管理员权限', 403);
        }
        return $sessionUser['username'];
    }
    
    // 回退到请求参数（向后兼容）
    if ($requestAdminUsername === null || $requestAdminUsername === '') {
        jsonError('未登录或会话已过期', 401);
    }
    
    return trim($requestAdminUsername);
}

/**
 * 设置 CORS 头（支持跨域携带 Cookie）
 * @param string $methods 允许的 HTTP 方法
 */
function setAuthApiHeaders(string $methods = 'POST, OPTIONS'): void {
    // 获取请求来源
    $origin = $_SERVER['HTTP_ORIGIN'] ?? '';
    
    // 开发环境允许 localhost
    $allowedOrigins = ['http://localhost:8080', 'http://127.0.0.1:8080'];
    
    // 生产环境应配置具体域名
    if (IS_PRODUCTION) {
        // TODO: 配置生产环境允许的域名
        $allowedOrigins = [];
    }
    
    // 设置 CORS 头
    if (empty($allowedOrigins) || in_array($origin, $allowedOrigins, true)) {
        header('Access-Control-Allow-Origin: ' . ($origin ?: '*'));
    } else {
        header('Access-Control-Allow-Origin: ' . $origin);
    }
    
    header('Access-Control-Allow-Credentials: true');
    header('Access-Control-Allow-Methods: ' . $methods);
    header('Access-Control-Allow-Headers: Content-Type, X-Requested-With');
    header('Content-Type: application/json; charset=utf-8');
}

// =========================
// 日志记录功能
// =========================

/**
 * 日志级别常量
 */
define('LOG_LEVEL_DEBUG', 0);
define('LOG_LEVEL_INFO', 1);
define('LOG_LEVEL_WARNING', 2);
define('LOG_LEVEL_ERROR', 3);

/**
 * 获取日志文件路径
 * @return string
 */
function getLogPath(): string {
    $logDir = __DIR__ . '/../logs';
    if (!is_dir($logDir)) {
        @mkdir($logDir, 0755, true);
    }
    return $logDir . '/app_' . date('Y-m-d') . '.log';
}

/**
 * 写入日志
 * @param string $message 日志消息
 * @param int $level 日志级别
 * @param array $context 上下文数据
 */
function writeLog(string $message, int $level = LOG_LEVEL_INFO, array $context = []): void {
    $levelNames = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];
    $levelName = $levelNames[$level] ?? 'UNKNOWN';
    
    $timestamp = date('Y-m-d H:i:s');
    $requestId = substr(md5(uniqid('', true)), 0, 8);
    
    $logEntry = sprintf(
        "[%s] [%s] [%s] %s",
        $timestamp,
        $levelName,
        $requestId,
        $message
    );
    
    if (!empty($context)) {
        $logEntry .= ' ' . json_encode($context, JSON_UNESCAPED_UNICODE);
    }
    
    $logEntry .= PHP_EOL;
    
    @file_put_contents(getLogPath(), $logEntry, FILE_APPEND | LOCK_EX);
}

/**
 * 记录调试日志
 */
function logDebug(string $message, array $context = []): void {
    writeLog($message, LOG_LEVEL_DEBUG, $context);
}

/**
 * 记录信息日志
 */
function logInfo(string $message, array $context = []): void {
    writeLog($message, LOG_LEVEL_INFO, $context);
}

/**
 * 记录警告日志
 */
function logWarning(string $message, array $context = []): void {
    writeLog($message, LOG_LEVEL_WARNING, $context);
}

/**
 * 记录错误日志
 */
function logError(string $message, array $context = []): void {
    writeLog($message, LOG_LEVEL_ERROR, $context);
}

/**
 * 记录异常日志
 * @param Throwable $e 异常对象
 * @param string $prefix 前缀消息
 */
function logException(Throwable $e, string $prefix = ''): void {
    $message = $prefix ? $prefix . ': ' : '';
    $message .= $e->getMessage();
    
    writeLog($message, LOG_LEVEL_ERROR, [
        'exception' => get_class($e),
        'file' => $e->getFile(),
        'line' => $e->getLine(),
        'trace' => $e->getTraceAsString()
    ]);
}

// =========================
// 审计日志功能
// =========================

/**
 * 审计操作类型常量
 */
define('AUDIT_LOGIN', 'login');
define('AUDIT_LOGOUT', 'logout');
define('AUDIT_UPLOAD', 'upload');
define('AUDIT_DOWNLOAD', 'download');
define('AUDIT_DELETE', 'delete');
define('AUDIT_MOVE', 'move');
 define('AUDIT_RENAME', 'rename');
define('AUDIT_SHARE', 'share');
define('AUDIT_PASSWORD_CHANGE', 'password_change');
define('AUDIT_PASSWORD_RESET', 'password_reset');
define('AUDIT_GRADUATION_SUBMIT', 'graduation_submit');
define('AUDIT_INTERNSHIP_SUBMIT', 'internship_submit');
define('AUDIT_REJECT', 'reject');

/**
 * 确保审计日志表存在
 * @param mysqli $db 数据库连接
 */
function ensureAuditTable(mysqli $db): void {
    static $checked = false;
    if ($checked) return;
    
    $sql = "CREATE TABLE IF NOT EXISTS `audit_logs` (
        `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
        `username` VARCHAR(64) NOT NULL COMMENT '操作用户',
        `action` VARCHAR(32) NOT NULL COMMENT '操作类型',
        `target` VARCHAR(1024) DEFAULT NULL COMMENT '操作目标',
        `details` TEXT DEFAULT NULL COMMENT '详细信息(JSON)',
        `ip_address` VARCHAR(45) DEFAULT NULL COMMENT 'IP地址',
        `user_agent` VARCHAR(512) DEFAULT NULL COMMENT '用户代理',
        `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        PRIMARY KEY (`id`),
        KEY `idx_username` (`username`),
        KEY `idx_action` (`action`),
        KEY `idx_created_at` (`created_at`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表';";
    
    $db->query($sql);
    $checked = true;
}

/**
 * 记录审计日志
 * @param string $username 操作用户
 * @param string $action 操作类型
 * @param string|null $target 操作目标（文件路径等）
 * @param array $details 额外详情
 */
function logAudit(string $username, string $action, ?string $target = null, array $details = []): void {
    try {
        require_once __DIR__ . '/db.php';
        $db = getDb();
        ensureAuditTable($db);
        
        $ip = $_SERVER['REMOTE_ADDR'] ?? null;
        $ua = isset($_SERVER['HTTP_USER_AGENT']) ? substr($_SERVER['HTTP_USER_AGENT'], 0, 512) : null;
        $detailsJson = !empty($details) ? json_encode($details, JSON_UNESCAPED_UNICODE) : null;
        
        $stmt = $db->prepare('INSERT INTO audit_logs (username, action, target, details, ip_address, user_agent) VALUES (?, ?, ?, ?, ?, ?)');
        $stmt->bind_param('ssssss', $username, $action, $target, $detailsJson, $ip, $ua);
        $stmt->execute();
        $stmt->close();
    } catch (Throwable $e) {
        // 审计日志失败不影响主流程，仅记录错误日志
        logError('审计日志写入失败', ['error' => $e->getMessage(), 'action' => $action]);
    }
}

/**
 * 获取审计日志列表
 * @param array $filters 筛选条件 ['username'=>..., 'action'=>..., 'start_date'=>..., 'end_date'=>...]
 * @param int $limit 限制数量
 * @param int $offset 偏移量
 * @return array
 */
function getAuditLogs(array $filters = [], int $limit = 100, int $offset = 0): array {
    require_once __DIR__ . '/db.php';
    $db = getDb();
    ensureAuditTable($db);
    
    $where = ['1=1'];
    $params = [];
    $types = '';
    
    if (!empty($filters['username'])) {
        $where[] = 'username = ?';
        $params[] = $filters['username'];
        $types .= 's';
    }
    if (!empty($filters['action'])) {
        $where[] = 'action = ?';
        $params[] = $filters['action'];
        $types .= 's';
    }
    if (!empty($filters['start_date'])) {
        $where[] = 'created_at >= ?';
        $params[] = $filters['start_date'];
        $types .= 's';
    }
    if (!empty($filters['end_date'])) {
        $where[] = 'created_at <= ?';
        $params[] = $filters['end_date'];
        $types .= 's';
    }
    
    $sql = 'SELECT * FROM audit_logs WHERE ' . implode(' AND ', $where) . ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
    $params[] = $limit;
    $params[] = $offset;
    $types .= 'ii';
    
    $stmt = $db->prepare($sql);
    $stmt->bind_param($types, ...$params);
    $stmt->execute();
    $result = $stmt->get_result();
    $logs = [];
    while ($row = $result->fetch_assoc()) {
        $logs[] = $row;
    }
    $stmt->close();
    
    return $logs;
}

// =========================
// 响应处理辅助函数
// =========================

/**
 * 设置通用 API 响应头（CORS + JSON）
 * @param string $methods 允许的 HTTP 方法，逗号分隔
 */
function setApiHeaders(string $methods = 'POST, OPTIONS'): void {
    header('Content-Type: application/json; charset=utf-8');
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: ' . $methods);
}

/**
 * 处理 OPTIONS 预检请求
 */
function handleOptionsRequest(): void {
    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
        http_response_code(204);
        exit;
    }
}

/**
 * 检查请求方法，不匹配则返回 405
 * @param string|array $allowed 允许的方法（字符串或数组）
 */
function requireMethod($allowed): void {
    $methods = is_array($allowed) ? $allowed : [$allowed];
    if (!in_array($_SERVER['REQUEST_METHOD'], $methods, true)) {
        jsonError('Method Not Allowed', 405);
    }
}

/**
 * 返回成功的 JSON 响应
 * @param array $data 要返回的数据，会合并 ['ok' => true]
 */
function jsonSuccess(array $data = []): void {
    echo json_encode(array_merge(['ok' => true], $data));
    exit;
}

/**
 * 返回错误的 JSON 响应
 * @param string $message 错误消息
 * @param int $httpCode HTTP 状态码，默认 400
 * @param array $extra 额外的错误信息
 */
function jsonError(string $message, int $httpCode = 400, array $extra = []): void {
    http_response_code($httpCode);
    echo json_encode(array_merge(['ok' => false, 'error' => $message], $extra));
    exit;
}

/**
 * 返回服务器内部错误
 * @param Throwable $e 异常对象
 * @param bool|null $includeDetail 是否包含详细错误信息（null 表示根据环境自动决定）
 */
function jsonServerError(Throwable $e, ?bool $includeDetail = null): void {
    // 记录错误日志
    logException($e, 'API Error');
    
    // 根据环境决定是否显示详细信息
    if ($includeDetail === null) {
        $includeDetail = !IS_PRODUCTION;
    }
    
    $extra = $includeDetail ? ['detail' => $e->getMessage()] : [];
    jsonError('服务器内部错误', 500, $extra);
}

// =========================
// 输入解析辅助函数
// =========================

/**
 * 解析请求体（JSON 或 POST 表单）
 * @return array 解析后的数据
 */
function parseRequestBody(): array {
    $raw = file_get_contents('php://input');
    $data = json_decode($raw, true);
    if (!is_array($data)) {
        $data = $_POST;
    }
    return $data;
}

/**
 * 验证用户名格式（必须为纯数字）
 * @param string $username 用户名
 * @return string 清洗后的用户名
 */
function validateUsername(string $username): string {
    $username = trim($username);
    if ($username === '' || !preg_match('/^[0-9]+$/', $username)) {
        jsonError('用户名必须为纯数字');
    }
    return $username;
}

/**
 * 验证用户是否存在于 Users 表
 * @param string $username 用户名（纯数字）
 * @return int 用户 ID
 */
function requireUserExists(string $username): int {
    require_once __DIR__ . '/db.php';
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
        return (int)$row['id'];
    } catch (Throwable $e) {
        jsonServerError($e);
    }
    return 0; // 不会执行到这里
}

/**
 * 初始化 API 请求（设置头、处理 OPTIONS、检查方法）
 * @param string $methods 允许的 HTTP 方法
 */
function initApiRequest(string $methods = 'POST'): void {
    setApiHeaders($methods . ', OPTIONS');
    handleOptionsRequest();
    requireMethod(explode(', ', $methods));
}

/**
 * 清洗用户名以生成安全的表名片段
 * 仅保留 a-z、0-9 和下划线；其余替换为下划线；截断到 48 长度。
 * @param string $username
 * @return string
 */
function sanitizeUserFragment(string $username): string {
  $lower = strtolower(trim($username));
  $san = preg_replace('/[^a-z0-9_]+/', '_', $lower);
  if ($san === '') { $san = 'user'; }
  return substr($san, 0, 48);
}

/**
 * 验证表名格式是否安全（白名单校验）
 * 只允许 user_ + 纯数字 格式的表名
 * @param string $table 表名
 * @return bool
 */
function isValidTableName(string $table): bool {
  return (bool)preg_match('/^user_[0-9]+$/', $table);
}

/**
 * 获取安全的用户表名
 * @param string $username 用户名（必须为纯数字）
 * @return string 表名
 * @throws InvalidArgumentException 如果用户名格式不合法
 */
function getSafeTableName(string $username): string {
  if (!preg_match('/^[0-9]+$/', $username)) {
    throw new InvalidArgumentException('用户名必须为纯数字');
  }
  $table = 'user_' . $username;
  if (!isValidTableName($table)) {
    throw new InvalidArgumentException('生成的表名格式不合法');
  }
  return $table;
}

/**
 * 确保用户表存在（FileUploadS）
 * @param mysqli $db 已连接的文件库连接
 * @param string $username 原始用户名（期望纯数字）
 * @return string 表名
 * @throws InvalidArgumentException 如果用户名格式不合法
 */
function ensureUserTable(mysqli $db, string $username): string {
  // 使用白名单校验获取安全表名
  $table = getSafeTableName($username);
  
  // 再次确认表名符合白名单规则
  if (!isValidTableName($table)) {
    throw new InvalidArgumentException('表名格式不合法');
  }
  
  $stmt = $db->prepare('SELECT COUNT(*) AS cnt FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ?');
  $stmt->bind_param('s', $table);
  $stmt->execute();
  $res = $stmt->get_result();
  $row = $res->fetch_assoc();
  $stmt->close();

  if ((int)$row['cnt'] === 0) {
    $sql = "CREATE TABLE IF NOT EXISTS `{$table}` (\n"
         . "  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',\n"
         . "  `file_path` VARCHAR(1024) NOT NULL COMMENT '文件路径',\n"
         . "  `is_public` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否公开',\n"
         . "  `upload_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',\n"
         . "  `last_download_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最近一次下载时间',\n"
         . "  PRIMARY KEY (`id`)\n"
         . ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';";
    $db->query($sql);
  } else {
    $db->query("ALTER TABLE `{$table}` COMMENT='用户文件记录表'");
    $db->query("ALTER TABLE `{$table}` MODIFY `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID'");
    $db->query("ALTER TABLE `{$table}` MODIFY `file_path` VARCHAR(1024) NOT NULL COMMENT '文件路径'");
    
    // 检查 is_public 列是否存在，不存在则添加
    $colRes = $db->query("SHOW COLUMNS FROM `{$table}` LIKE 'is_public'");
    if ($colRes && $colRes->num_rows === 0) {
      $db->query("ALTER TABLE `{$table}` ADD COLUMN `is_public` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否公开' AFTER `file_path`");
    }

    $db->query("ALTER TABLE `{$table}` MODIFY `upload_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间'");
    $db->query("ALTER TABLE `{$table}` MODIFY `last_download_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最近一次下载时间'");
  }
  return $table;
}