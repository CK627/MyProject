-- FileUpload 数据库初始化脚本
-- 目的：创建用于文件上传系统的基础库与用户表
-- 设计说明：存储用户登录认证信息、教师管理员、毕业生信息
-- 版本：v3.1 (数据库合并后)

CREATE DATABASE IF NOT EXISTS `FileUpload`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Users 表：系统用户表，存储登录认证信息
CREATE TABLE IF NOT EXISTS `FileUpload`.`Users` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID，唯一标识用户',
  `username` VARCHAR(64) NOT NULL COMMENT '登录用户名，唯一',
  `password` VARCHAR(255) NOT NULL COMMENT '密码哈希（不存明文）',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `last_login_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最近一次登录时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='系统用户表，存储登录认证信息';

-- 使用建议：
-- 1) `password` 字段仅保存加盐哈希（如 bcrypt/argon2），不要保存明文。
-- 2) `username` 设为唯一键，避免重复注册与账号冲突。
-- 3) 统一使用 utf8mb4_unicode_ci 排序规则，兼容多语言用户名与显示。
-- 4) 时间字段选用 TIMESTAMP，`created_at` 默认当前时间，`last_login_at` 可为空。

-- admins 表：教师/管理员表
CREATE TABLE IF NOT EXISTS `FileUpload`.`admins` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username` VARCHAR(64) NOT NULL COMMENT '管理员用户名',
  `class` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '负责班级（空表示超级管理员）',
  `password` VARCHAR(255) NOT NULL COMMENT '密码哈希',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `last_login_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最近一次登录时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_admin_username` (`username`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='教师/管理员表';

-- 运行方式（生产中请使用环境变量，而非明文密码）：
-- mysql -h ${DB_HOST} -u ${DB_USER} -p${DB_PASSWORD} < docs/database-schema.sql

-- Settings 表：按用户存储个性化设置（当前仅保留 id 与 user 字段）
CREATE TABLE IF NOT EXISTS `FileUpload`.`Settings` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user` VARCHAR(64) NOT NULL COMMENT '对应用户名（唯一）',
  `HomepageSettings` VARCHAR(32) NOT NULL DEFAULT 'list' COMMENT '默认首页目标（如 upload/list/...）',
  `HiddenFile` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '上传是否跳过隐藏文件（1=True=跳过，0=False=不跳过）',
  `ShowHiddenFiles` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '文件列表是否显示隐藏文件（1=True=显示，0=False=隐藏）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_settings_user` (`user`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='用户设置表，每个用户一条记录（后续可扩展更多设置项）';

-- 后续应用侧加载设置时：若不存在对应用户记录，应插入默认记录
-- 示例：INSERT IGNORE INTO `FileUpload`.`Settings`(`user`) VALUES('some-username');

-- 生产/已有库的迁移指引（MySQL 8+ 支持 IF NOT EXISTS）：
-- 1) 将 HomepageSettings 改为字符串存储默认页面：
-- ALTER TABLE `FileUpload`.`Settings`
--   MODIFY COLUMN `HomepageSettings` VARCHAR(32) NOT NULL DEFAULT 'list' COMMENT '默认首页目标（如 upload/list/...）';
-- 2) 将历史 0/1 映射为 list/upload：
-- UPDATE `FileUpload`.`Settings` SET `HomepageSettings` = 'upload' WHERE `HomepageSettings` IN ('1', 'true');
-- UPDATE `FileUpload`.`Settings` SET `HomepageSettings` = 'list' WHERE `HomepageSettings` IN ('0', 'false');
-- ALTER TABLE `FileUpload`.`Settings`
--   ADD COLUMN IF NOT EXISTS `HiddenFile` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '上传是否跳过隐藏文件（1=True=跳过，0=False=不跳过）';
-- ALTER TABLE `FileUpload`.`Settings`
--   ADD COLUMN IF NOT EXISTS `ShowHiddenFiles` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '文件列表是否显示隐藏文件（1=True=显示，0=False=隐藏）';

-- graduation_information 表：毕业生信息与提交状态
-- 该表结构较复杂，包含 12 种文档类型的字段，详见 USAGE.md 或 api/graduation_config.php
-- 基础字段示例：
CREATE TABLE IF NOT EXISTS `FileUpload`.`graduation_information` (
  `ID` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `studentID` VARCHAR(32) NOT NULL COMMENT '学号',
  `name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '姓名',
  `class` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '班级',
  -- 各文档类型字段（路径、提交时间、下载次数等）请参考 graduation_config.php 配置
  -- 示例：`Application Form for Internship Unit` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `uk_studentID` (`studentID`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='毕业生信息与提交状态表（原 FileUploadGraduationSubmission.Users 已迁移至此）';

-- config_file_types 表：文件上传类型配置表
CREATE TABLE IF NOT EXISTS `FileUpload`.`config_file_types` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `type_key` VARCHAR(32) NOT NULL COMMENT '配置键名，如 thesis',
  `allowed_extensions` VARCHAR(255) NOT NULL COMMENT '允许的扩展名，逗号分隔，如 pdf,doc',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_type_key` (`type_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件上传类型配置表';

-- FileUploadS 文件库（用户私有文件索引）
CREATE DATABASE IF NOT EXISTS `FileUploadS`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 注：FileUploadS 中不需预先建表，系统会在用户首次登录或上传时自动创建 user_{username} 表