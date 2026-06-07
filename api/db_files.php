<?php
/**
 * FileUploadS 库连接助手
 * 已改为使用 Database 单例类，确保连接复用。
 * 
 * 保留此函数以兼容现有代码，内部委托给 Database 类。
 *
 * @return mysqli
 */
require_once __DIR__ . '/Database.php';

function getFilesDb(): mysqli {
    return Database::getFiles();
}