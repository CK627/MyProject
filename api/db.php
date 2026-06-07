<?php
/**
 * 数据库连接助手（主库 FileUpload）
 * 已改为使用 Database 单例类，确保连接复用。
 * 
 * 保留此函数以兼容现有代码，内部委托给 Database 类。
 *
 * @return mysqli 已连接的数据库连接
 * @throws RuntimeException 当配置文件缺失或连接失败时抛出异常
 */
require_once __DIR__ . '/Database.php';

function getDb(): mysqli {
    return Database::getMain();
}