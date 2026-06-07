<?php
/**
 * 新建文件夹接口
 * - POST JSON：{ username(纯数字), dir(相对目录，可为空), name(新文件夹名) }
 * - 行为：在 /File/{username}/{dir}/ 下创建 name 文件夹；允许中文与常用字符；拒绝路径穿越。
 * - 设计原因：支持空文件夹可见性，通过文件系统创建并在列表接口中返回。
 */

require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

initApiRequest('POST');

$data = parseRequestBody();
$username = validateUsername((string)($data['username'] ?? ''));
$dir = trim((string)($data['dir'] ?? ''));
$name = trim((string)($data['name'] ?? ''));

// 校验该用户是否存在于 Users 表，避免伪造用户名创建目录
requireUserExists($username);
// 清洗目录与名称，避免路径穿越；允许中文与空格等，但不允许包含斜杠
$dir = str_replace(['\\'], '/', $dir);
$dir = trim($dir, '/');
if (strpos($dir, '..') !== false) { $dir = ''; }
$safeName = basename($name);
if ($safeName === '' || strpos($safeName, '/') !== false) {
  jsonError('非法文件夹名');
}

try {
  $root = realpath(__DIR__ . '/..');
  $base = $root . DIRECTORY_SEPARATOR . 'File' . DIRECTORY_SEPARATOR . $username;
  $target = $base . ($dir !== '' ? DIRECTORY_SEPARATOR . $dir : '') . DIRECTORY_SEPARATOR . $safeName;
  if (is_dir($target)) {
    jsonSuccess(['created' => false]);
  }
  if (!is_dir(dirname($target))) {
    // 父目录不存在则尝试创建（递归）
    if (!mkdir(dirname($target), 0755, true) && !is_dir(dirname($target))) {
      throw new RuntimeException('无法创建父目录');
    }
  }
  if (!mkdir($target, 0755) && !is_dir($target)) {
    throw new RuntimeException('创建文件夹失败');
  }
  jsonSuccess(['created' => true]);
} catch (Throwable $e) {
  jsonServerError($e);
}