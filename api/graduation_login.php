<?php
/**
 * 毕业学生登录接口
 * - POST 请求，通过学号验证后创建 Session
 * - 注意：毕业登录不需要密码，只需学号存在于毕业库中
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';

// 使用支持跨域 Cookie 的响应头
setAuthApiHeaders('POST, OPTIONS');
handleOptionsRequest();
requireMethod('POST');

$data = parseRequestBody();
$username = trim((string)($data['username'] ?? ''));

if ($username === '' || !preg_match('/^[0-9]+$/', $username)) {
  jsonError('学号必须为纯数字');
}

try {
  $db = getGraduationDb();
  $stmt = $db->prepare('SELECT `ID`, `name`, `class` FROM `graduation_information` WHERE `studentID` = ? LIMIT 1');
  $stmt->bind_param('s', $username);
  $stmt->execute();
  $res = $stmt->get_result();
  if (!$res || $res->num_rows === 0) {
    jsonError('毕业学生记录不存在', 404);
  }
  $row = $res->fetch_assoc();
  $stmt->close();
  
  $name = (string)($row['name'] ?? '');
  $class = (string)($row['class'] ?? '');
  
  // 创建 Session 登录（毕业生角色）
  sessionLogin((int)$row['ID'], $username, 'graduation');
  
  // 存储额外信息到 Session
  initSession();
  $_SESSION['real_name'] = $name;
  $_SESSION['class'] = $class;
  
  // 记录审计日志
  logAudit($username, AUDIT_LOGIN, null, ['role' => 'graduation', 'name' => $name]);
  
  jsonSuccess(['name' => $name, 'class' => $class, 'username' => $username]);
} catch (Throwable $e) {
  jsonServerError($e, false);
}
