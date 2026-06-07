<?php
/**
 * 用户文件记录库初始化接口
 * - 仅负责根据用户名创建对应的用户表（如 user_xxx），如果不存在则创建；存在则直接返回。
 * - 表结构：id, file_path, upload_at, last_download_at
 * - 安全：对用户名进行严格清洗用于生成表名，避免 SQL 注入。
 */

require_once __DIR__ . '/util.php';

initApiRequest('POST');

$data = parseRequestBody();
$username = trim((string)($data['username'] ?? ''));
$username = validateUsername($username);

$fragment = sanitizeUserFragment($username);
$table = 'user_' . $fragment;

try {
  $db = getFilesDb();
  // 检查是否存在该表
  $stmt = $db->prepare('SELECT COUNT(*) AS cnt FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ?');
  $stmt->bind_param('s', $table);
  $stmt->execute();
  $res = $stmt->get_result();
  $row = $res->fetch_assoc();
  $stmt->close();

  if ((int)$row['cnt'] === 0) {
    // 创建用户专属表
    $sql = "CREATE TABLE IF NOT EXISTS `{$table}` (\n"
         . "  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',\n"
         . "  `file_path` VARCHAR(1024) NOT NULL COMMENT '文件路径',\n"
         . "  `is_public` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否公开',\n"
         . "  `upload_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',\n"
         . "  `last_download_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最近一次下载时间',\n"
         . "  PRIMARY KEY (`id`)\n"
         . ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';";
    $db->query($sql);
    jsonSuccess(['created' => true, 'table' => $table]);
  } else {
    // 表已存在：补充/校正列与表注释
    $db->query("ALTER TABLE `{$table}` COMMENT='用户文件记录表'");
    $db->query("ALTER TABLE `{$table}` MODIFY `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID'");
    $db->query("ALTER TABLE `{$table}` MODIFY `file_path` VARCHAR(1024) NOT NULL COMMENT '文件路径'");
    
    // 检查 is_public 列是否存在
    $colRes = $db->query("SHOW COLUMNS FROM `{$table}` LIKE 'is_public'");
    if ($colRes && $colRes->num_rows === 0) {
      $db->query("ALTER TABLE `{$table}` ADD COLUMN `is_public` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否公开' AFTER `file_path`");
    }

    $db->query("ALTER TABLE `{$table}` MODIFY `upload_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间'");
    $db->query("ALTER TABLE `{$table}` MODIFY `last_download_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最近一次下载时间'");
    jsonSuccess(['created' => false, 'table' => $table]);
  }
} catch (Throwable $e) {
  jsonServerError($e);
}