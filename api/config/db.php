<?php
/**
 * 数据库连接配置
 * 使用 PDO 连接 MySQL 数据库
 */

// 数据库配置
define('DB_HOST', '<DB_HOST>');
define('DB_NAME', '<DB_NAME>');
define('DB_USER', '<DB_USER>');
define('DB_PASS', '<DB_PASSWORD>');
define('DB_CHARSET', 'utf8mb4');

/**
 * 获取 PDO 数据库连接实例
 * @return PDO
 */
function getDB() {
    static $pdo = null;
    if ($pdo === null) {
        $dsn = 'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=' . DB_CHARSET;
        $options = [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ];
        try {
            $pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
        } catch (PDOException $e) {
            http_response_code(500);
            echo json_encode(['error' => '数据库连接失败: ' . $e->getMessage()]);
            exit;
        }
    }
    return $pdo;
}
