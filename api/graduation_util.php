<?php
/**
 * 毕业提交相关工具函数
 */
require_once __DIR__ . '/db_graduation.php';

/**
 * 生成毕业文件的最终文件名
 * 格式：学号 + 姓名 + 类型后缀 + 扩展名
 * 
 * @param string $studentID 学号
 * @param string $originalFilename 原始文件名
 * @param string $typeSuffix 类型后缀（如 '毕业设计论文' 或 '实习证明'）
 * @return string 最终文件名
 */
function generateGraduationFileName(string $studentID, string $originalFilename, string $typeSuffix): string {
    $dbName = '';
    try {
        $db = getGraduationDb();
        $stmt = $db->prepare('SELECT `name` FROM `graduation_information` WHERE `studentID` = ? LIMIT 1');
        $stmt->bind_param('s', $studentID);
        $stmt->execute();
        $res = $stmt->get_result();
        $row = $res ? $res->fetch_assoc() : null;
        $stmt->close();
        $dbName = trim((string)($row['name'] ?? ''));
    } catch (Throwable $__) {}
    
    $ext = pathinfo($originalFilename, PATHINFO_EXTENSION);
    // 移除文件名中的非法字符
    $safeName = preg_replace('/[\\\\\/:*?"<>|]+/', '', $dbName);
    
    return $studentID . $safeName . $typeSuffix . ($ext ? ('.' . $ext) : '');
}

/**
 * 删除旧的毕业文件（在替换模式下）
 * 
 * @param mysqli $db 数据库连接
 * @param string $studentID 学号
 * @param string $column 数据库字段名（如 'Graduation Thesis' 或 'Internship Certificate'）
 * @param string $newRelativePath 新文件的相对路径
 * @param string $root 项目根目录
 */
function deleteOldGraduationFile(mysqli $db, string $studentID, string $column, string $newRelativePath, string $root): void {
    try {
        $stmt = $db->prepare("SELECT `{$column}` FROM `graduation_information` WHERE `studentID` = ? LIMIT 1");
        $stmt->bind_param('s', $studentID);
        $stmt->execute();
        $res = $stmt->get_result();
        $row = $res ? $res->fetch_assoc() : null;
        $stmt->close();
        
        $prevRel = trim((string)($row[$column] ?? ''));
        
        // 如果旧文件存在且与新文件不同，删除旧文件
        if ($prevRel !== '' && $prevRel !== $newRelativePath) {
            $prevPath = $root . DIRECTORY_SEPARATOR . str_replace(['/', '\\'], DIRECTORY_SEPARATOR, $prevRel);
            if (is_file($prevPath)) {
                @unlink($prevPath);
            }
        }
    } catch (Throwable $__) {}
}
function sanitizeGraduationTableName(string $username): string {
  $lower = strtolower(trim($username));
  $san = preg_replace('/[^a-z0-9_]+/', '_', $lower);
  if ($san === '') { $san = 'user'; }
  return substr($san, 0, 48);
}
function ensureGraduationTable(mysqli $db, string $username): string {
  $table = sanitizeGraduationTableName($username);
  $stmt = $db->prepare('SELECT COUNT(*) AS c FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ?');
  $stmt->bind_param('s', $table);
  $stmt->execute();
  $res = $stmt->get_result();
  $row = $res->fetch_assoc();
  $stmt->close();
  if ((int)$row['c'] === 0) {
    $sql = "CREATE TABLE IF NOT EXISTS `{$table}` (\n"
         . "  `ID` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,\n"
         . "  `name` VARCHAR(64) NOT NULL,\n"
         . "  `class` VARCHAR(64) NOT NULL DEFAULT '',\n"
         . "  PRIMARY KEY (`ID`)\n"
         . ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
    $db->query($sql);
  } else {
    $db->query("ALTER TABLE `{$table}` MODIFY `ID` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT");
    // 迁移旧列到新列
    $hasName = $db->query("SELECT COUNT(*) AS c FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{$db->real_escape_string($table)}' AND COLUMN_NAME = 'name'");
    $hasClass = $db->query("SELECT COUNT(*) AS c FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{$db->real_escape_string($table)}' AND COLUMN_NAME = 'class'");
    $cName = $hasName->fetch_assoc(); $cClass = $hasClass->fetch_assoc();
    if ((int)$cName['c'] === 0) {
      $db->query("ALTER TABLE `{$table}` ADD COLUMN `name` VARCHAR(64) NOT NULL");
      // 若存在旧的 Name 列，拷贝数据
      $db->query("UPDATE `{$table}` SET `name` = `Name` WHERE `name` IS NULL OR `name` = ''");
    } else {
      $db->query("ALTER TABLE `{$table}` MODIFY `name` VARCHAR(64) NOT NULL");
    }
    if ((int)$cClass['c'] === 0) {
      $db->query("ALTER TABLE `{$table}` ADD COLUMN `class` VARCHAR(64) NOT NULL DEFAULT ''");
      $db->query("UPDATE `{$table}` SET `class` = `Class` WHERE `class` IS NULL OR `class` = ''");
    } else {
      $db->query("ALTER TABLE `{$table}` MODIFY `class` VARCHAR(64) NOT NULL DEFAULT ''");
    }
  }
  return $table;
}
