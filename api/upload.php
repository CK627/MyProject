<?php
/**
 * 文件上传接口
 * - 路径存储：项目根目录下 /File/{username}/
 * - 数据库记录：FileUploadS.user_{username} 表中的 `file_path` 保存为 /File/{username}/{filename}
 * - 仅允许纯数字用户名（与注册规则保持一致），并确保用户表存在
 * - 为什么这样设计：避免中文或非法字符进入表名与路径，保证安全与一致性
 * - 认证：优先使用 Session，回退到 username 参数
 */

require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

// 设置支持 Session Cookie 的 CORS 头
setAuthApiHeaders('POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  http_response_code(405);
  echo json_encode(['error' => 'Method Not Allowed']);
  exit;
}

/**
 * 将 ini 尺寸字符串（如 2M、512K、1G）解析为字节数
 * @param string $val
 * @return int
 */
function parseIniBytes(string $val): int {
  $trim = trim($val);
  if ($trim === '') return 0;
  $num = (int)$trim;
  $unit = strtoupper(substr($trim, -1));
  switch ($unit) {
    case 'G': return $num * 1024 * 1024 * 1024;
    case 'M': return $num * 1024 * 1024;
    case 'K': return $num * 1024;
    default: return (int)$trim;
  }
}

// 若请求体超过 post_max_size，PHP 通常会丢弃内容导致 $_POST/$_FILES 为空，这里提前返回 413
$contentLen = isset($_SERVER['CONTENT_LENGTH']) ? (int)$_SERVER['CONTENT_LENGTH'] : 0;
$postMax = parseIniBytes((string)ini_get('post_max_size'));
if ($postMax > 0 && $contentLen > $postMax) {
  http_response_code(413);
  echo json_encode(['error' => '请求体过大，超过服务器 post_max_size 限制']);
  exit;
}

// 优先从 Session 获取用户，回退到请求参数
$requestUsername = trim((string)($_POST['username'] ?? ''));
$username = getAuthenticatedUser($requestUsername !== '' ? $requestUsername : null);

// 收集上传文件（支持 files[] 或 file）
$files = [];
if (isset($_FILES['files'])) { $files = $_FILES['files']; }
elseif (isset($_FILES['file'])) { $files = $_FILES['file']; }
else {
  http_response_code(400);
  echo json_encode(['error' => '缺少上传文件']);
  exit;
}

// 规范化为数组结构
$count = is_array($files['name']) ? count($files['name']) : 1;

try {
  $db = getFilesDb();
  $table = ensureUserTable($db, $username);

  $root = realpath(__DIR__ . '/..');
  $destDir = $root . DIRECTORY_SEPARATOR . 'File' . DIRECTORY_SEPARATOR . $username;
  if (!is_dir($destDir)) {
    if (!mkdir($destDir, 0755, true) && !is_dir($destDir)) {
      throw new RuntimeException('无法创建用户目录');
    }
  }

  $saved = [];
  for ($i = 0; $i < $count; $i++) {
    $name = is_array($files['name']) ? $files['name'][$i] : $files['name'];
    $tmp  = is_array($files['tmp_name']) ? $files['tmp_name'][$i] : $files['tmp_name'];
    $err  = is_array($files['error']) ? $files['error'][$i] : $files['error'];

    if ($err !== UPLOAD_ERR_OK) {
      // 更明确的错误提示，便于前端区分“大文件导致失败”等场景
      $errMap = [
        UPLOAD_ERR_INI_SIZE   => '文件超过服务器大小限制',
        UPLOAD_ERR_FORM_SIZE  => '文件超过表单大小限制',
        UPLOAD_ERR_PARTIAL    => '文件仅部分上传',
        UPLOAD_ERR_NO_FILE    => '未选择文件',
        UPLOAD_ERR_NO_TMP_DIR => '服务器临时目录缺失',
        UPLOAD_ERR_CANT_WRITE => '服务器写入失败',
        UPLOAD_ERR_EXTENSION  => '服务器扩展阻止上传',
      ];
      $msg = $errMap[$err] ?? '上传失败';
      $saved[] = ['ok' => false, 'name' => $name, 'error' => $msg, 'error_code' => $err];
      continue;
    }

    // 保留原始文件名（仅移除路径部分），不修改名称
    $safeName = basename($name);
    if ($safeName === '') {
      $saved[] = ['ok' => false, 'name' => $name, 'error' => '非法文件名'];
      continue;
    }
    // 若同名已存在，则报错（不改名）
    $target = $destDir . DIRECTORY_SEPARATOR . $safeName;
    if (file_exists($target)) {
      $saved[] = ['ok' => false, 'name' => $safeName, 'error' => '文件已存在'];
      continue;
    }

    if (!move_uploaded_file($tmp, $target)) {
      $saved[] = ['ok' => false, 'name' => $name, 'error' => '保存失败'];
      continue;
    }

    // 安全权限：仅可读（不可执行、不可写）
    // 说明：删除/移动依赖目录权限，不依赖文件写权限
    @chmod($target, 0444);

    // 记录相对路径 /File/{username}/{filename}
    $relative = '/File/' . $username . '/' . $safeName;
    $stmt = $db->prepare("INSERT INTO `{$table}` (file_path) VALUES (?)");
    $stmt->bind_param('s', $relative);
    $stmt->execute();
    $stmt->close();

    $saved[] = ['ok' => true, 'name' => $safeName, 'path' => $relative];
  }

  echo json_encode(['ok' => true, 'items' => $saved, 'limits' => [
    'upload_max_bytes' => parseIniBytes((string)ini_get('upload_max_filesize')),
    'post_max_bytes' => $postMax
  ]]);
} catch (Throwable $e) {
  http_response_code(500);
  echo json_encode(['error' => '服务器内部错误', 'detail' => $e->getMessage()]);
}