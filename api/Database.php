<?php
/**
 * 数据库连接管理器（单例模式）
 * 
 * 功能：
 * - 统一管理数据库连接（主库、文件库）
 * - 使用单例模式确保同一请求内连接复用，避免重复创建
 * - 延迟加载：只在需要时才建立连接
 * - 统一的配置解析和错误处理
 * 
 * 注：毕业生数据已合并到主库 graduation_information 表
 * 
 * 使用示例：
 *   $db = Database::getMain();  // 获取主库连接
 *   $db = Database::getFiles(); // 获取文件库连接
 */
class Database {
    // 数据库类型常量
    const TYPE_MAIN = 'main';
    const TYPE_FILES = 'files';
    
    // 配置文件映射
    private static array $configFiles = [
        self::TYPE_MAIN => 'mysql.ini',
        self::TYPE_FILES => 'mysql_files.ini',
    ];
    
    // 连接实例缓存（单例）
    private static array $instances = [];
    
    // 配置缓存
    private static array $configs = [];
    
    /**
     * 私有构造函数，禁止外部实例化
     */
    private function __construct() {}
    
    /**
     * 禁止克隆
     */
    private function __clone() {}
    
    /**
     * 获取主库连接（FileUpload）
     * @return mysqli
     */
    public static function getMain(): mysqli {
        return self::getConnection(self::TYPE_MAIN);
    }
    
    /**
     * 获取文件库连接（FileUploadS）
     * @return mysqli
     */
    public static function getFiles(): mysqli {
        return self::getConnection(self::TYPE_FILES);
    }
    
    /**
     * 获取毕业生数据库连接（已合并到主库）
     * @deprecated 毕业生数据已迁移到主库 graduation_information 表，请使用 getMain()
     * @return mysqli
     */
    public static function getGraduation(): mysqli {
        // 数据库合并后，毕业生数据已迁移到主库
        return self::getMain();
    }
    
    /**
     * 获取数据库连接（核心方法）
     * 
     * @param string $type 数据库类型
     * @param bool $autoCreateDb 是否自动创建数据库（仅毕业库需要）
     * @return mysqli
     * @throws RuntimeException
     */
    private static function getConnection(string $type, bool $autoCreateDb = false): mysqli {
        // 检查是否已有有效连接
        if (isset(self::$instances[$type])) {
            $conn = self::$instances[$type];
            // 检查连接是否仍然有效（PHP 8.4+ 兼容方式）
            try {
                // 使用简单查询代替已废弃的 ping()
                $conn->query('SELECT 1');
                return $conn;
            } catch (Throwable $e) {
                // 连接已失效，关闭并重新创建
                @$conn->close();
                unset(self::$instances[$type]);
            }
        }
        
        // 解析配置
        $cfg = self::getConfig($type);
        
        // 设置 mysqli 错误报告模式
        mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
        
        // 如果需要自动创建数据库（毕业库）
        if ($autoCreateDb) {
            $adminConn = new mysqli($cfg['host'], $cfg['username'], $cfg['password'], '', $cfg['port']);
            $dbName = $cfg['database'];
            $charset = $cfg['charset'];
            $adminConn->query("CREATE DATABASE IF NOT EXISTS `{$dbName}` CHARACTER SET {$charset} COLLATE {$charset}_unicode_ci");
            $adminConn->close();
        }
        
        // 创建连接
        $conn = new mysqli(
            $cfg['host'],
            $cfg['username'],
            $cfg['password'],
            $cfg['database'],
            $cfg['port']
        );
        $conn->set_charset($cfg['charset']);
        
        // 缓存连接
        self::$instances[$type] = $conn;
        
        return $conn;
    }
    
    /**
     * 解析配置文件
     * 
     * @param string $type 数据库类型
     * @return array 配置数组
     * @throws RuntimeException
     */
    private static function getConfig(string $type): array {
        // 检查缓存
        if (isset(self::$configs[$type])) {
            return self::$configs[$type];
        }
        
        // 获取配置文件路径
        if (!isset(self::$configFiles[$type])) {
            throw new RuntimeException("未知的数据库类型: {$type}");
        }
        
        $configPath = __DIR__ . '/../config/' . self::$configFiles[$type];
        
        if (!is_file($configPath)) {
            throw new RuntimeException("缺少配置文件: config/" . self::$configFiles[$type]);
        }
        
        $cfg = parse_ini_file($configPath, false, INI_SCANNER_RAW);
        
        if ($cfg === false) {
            throw new RuntimeException("配置文件解析失败: config/" . self::$configFiles[$type]);
        }
        
        // 规范化配置
        $config = [
            'host' => $cfg['host'] ?? 'localhost',
            'port' => (int)($cfg['port'] ?? 3306),
            'username' => $cfg['username'] ?? '',
            'password' => $cfg['password'] ?? '',
            'database' => $cfg['database'] ?? '',
            'charset' => $cfg['charset'] ?? 'utf8mb4',
        ];
        
        // 缓存配置
        self::$configs[$type] = $config;
        
        return $config;
    }
    
    /**
     * 关闭所有连接（通常在脚本结束时自动调用）
     */
    public static function closeAll(): void {
        foreach (self::$instances as $type => $conn) {
            if ($conn instanceof mysqli) {
                @$conn->close();
            }
        }
        self::$instances = [];
    }
    
    /**
     * 关闭指定类型的连接
     * 
     * @param string $type 数据库类型
     */
    public static function close(string $type): void {
        if (isset(self::$instances[$type]) && self::$instances[$type] instanceof mysqli) {
            @self::$instances[$type]->close();
            unset(self::$instances[$type]);
        }
    }
    
    /**
     * 获取当前活动连接数
     * 
     * @return int
     */
    public static function getActiveCount(): int {
        return count(self::$instances);
    }
    
    /**
     * 检查指定类型是否有活动连接
     * 
     * @param string $type 数据库类型
     * @return bool
     */
    public static function hasConnection(string $type): bool {
        if (!isset(self::$instances[$type])) {
            return false;
        }
        try {
            // 使用简单查询代替已废弃的 ping()
            self::$instances[$type]->query('SELECT 1');
            return true;
        } catch (Throwable $e) {
            return false;
        }
    }
}

// 注册关闭函数，确保连接在脚本结束时关闭
register_shutdown_function([Database::class, 'closeAll']);
