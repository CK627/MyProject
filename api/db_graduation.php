<?php
/**
 * 毕业生信息库连接助手
 * 
 * 数据库合并后，毕业生数据已迁移到主库 FileUpload.graduation_information 表
 * 保留此函数以兼容现有代码，实际返回主库连接
 *
 * @return mysqli
 */
require_once __DIR__ . '/Database.php';

function getGraduationDb(): mysqli {
    // 数据库合并后，毕业生数据已迁移到主库
    return Database::getMain();
}

// 毕业生信息表名常量
define('GRADUATION_TABLE', 'graduation_information');