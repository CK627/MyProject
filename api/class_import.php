<?php
/**
 * 批量导入学生接口（支持 Excel/CSV）
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_util.php';
require_once __DIR__ . '/db.php';

initApiRequest('POST');

$admin = trim((string)($_POST['adminUsername'] ?? ''));
$class = '';

try {
  $main = getDb();
  if ($admin !== '') {
    $stmt = $main->prepare('SELECT `class` FROM `admins` WHERE `username` = ? LIMIT 1');
    $stmt->bind_param('s', $admin);
    $stmt->execute();
    $res = $stmt->get_result();
    $row = $res->fetch_assoc();
    $stmt->close();
    if ($row) {
      $class = trim((string)($row['class'] ?? ''));
    }
  }
} catch (Throwable $e) {
  $class = '';
}

if (!isset($_FILES['file'])) {
  jsonError('请上传文件');
}
$file = $_FILES['file'];
if ($file['error'] !== UPLOAD_ERR_OK) {
  jsonError('文件上传失败');
}

try {
  $db = getGraduationDb();
  $ok = 0;
  $fail = 0;
  $nameLower = strtolower((string)$file['name']);
  $isXlsx = substr($nameLower, -5) === '.xlsx';
  
  if ($isXlsx) {
    if (!class_exists('ZipArchive')) {
      jsonError('服务器不支持Excel解析');
    }
    $zip = new ZipArchive();
    if ($zip->open($file['tmp_name']) !== true) {
      jsonError('Excel文件解析失败');
    }
    $shared = [];
    $ss = $zip->getFromName('xl/sharedStrings.xml');
    if ($ss !== false) {
      $xml = @simplexml_load_string($ss);
      if ($xml && isset($xml->si)) {
        foreach ($xml->si as $i => $si) {
          $text = '';
          if (isset($si->t)) {
            $text = (string)$si->t;
          } else if (isset($si->r)) {
            foreach ($si->r as $r) {
              $text .= (string)$r->t;
            }
          }
          $shared[(int)$i] = trim($text);
        }
      }
    }
    $sheetXml = $zip->getFromName('xl/worksheets/sheet1.xml');
    if ($sheetXml === false) {
      for ($idx = 1; $idx <= 10; $idx++) {
        $sheetXml = $zip->getFromName("xl/worksheets/sheet{$idx}.xml");
        if ($sheetXml !== false) break;
      }
    }
    if ($sheetXml === false) {
      $zip->close();
      jsonError('找不到工作表');
    }
    $sx = @simplexml_load_string($sheetXml);
    if ($sx && isset($sx->sheetData) && isset($sx->sheetData->row)) {
      foreach ($sx->sheetData->row as $row) {
        // Skip header row (row 1)
        if (isset($row['r']) && (int)$row['r'] == 1) continue;

        $a = '';
        $b = '';
        foreach ($row->c as $c) {
          $ref = (string)$c['r'];
          $t = (string)$c['t'];
          $v = isset($c->v) ? (string)$c->v : '';
          $val = '';
          if ($t === 's') {
            $idx = (int)$v;
            $val = isset($shared[$idx]) ? $shared[$idx] : '';
          } else if ($t === 'inlineStr') {
             if (isset($c->is->t)) {
                 $val = (string)$c->is->t;
             }
          } else {
            $val = trim($v);
          }
          if (strpos($ref, 'A') === 0) {
            $a = $val;
          } else if (strpos($ref, 'B') === 0) {
            $b = $val;
          }
        }
        $col1 = trim($a);
        $col2 = trim($b);
        
        // 智能识别：纯数字的作为学号
        $username = '';
        $name = '';
        
        if (preg_match('/^[0-9]+$/', $col1) && !preg_match('/^[0-9]+$/', $col2)) {
            // A是学号，B是姓名
            $username = $col1;
            $name = $col2;
        } else if (preg_match('/^[0-9]+$/', $col2)) {
            // B是学号（A可能是姓名，或者A也是数字但优先B作为学号如果符合用户描述的姓名+学号格式，不过这里简化逻辑，只要B是数字就认为B是学号）
            // 用户指定格式：姓名 学号。即 A=姓名, B=学号
            $username = $col2;
            $name = $col1;
        } else {
            // 都不是数字，可能是表头或无效行
            $fail++;
            continue;
        }

        if ($username === '') {
          $fail++;
          continue;
        }
        $stmt = $db->prepare("INSERT INTO `graduation_information`(`studentID`,`name`,`class`) VALUES(?,?,?) ON DUPLICATE KEY UPDATE `name`=VALUES(`name`),`class`=VALUES(`class`)");
        $stmt->bind_param('sss', $username, $name, $class);
        $stmt->execute();
        $stmt->close();
        $ok++;
      }
    }
    $zip->close();
  } else {
    $content = file_get_contents($file['tmp_name']);
    
    // 尝试检测编码并转换为 UTF-8
    $enc = mb_detect_encoding($content, ['UTF-8', 'GBK', 'GB2312', 'BIG5'], true);
    if ($enc && $enc !== 'UTF-8') {
        $content = mb_convert_encoding($content, 'UTF-8', $enc);
    }
     
     $lines = preg_split('/\r?\n/', (string)$content);
     foreach ($lines as $index => $line) {
       if ($index === 0) continue; // Skip header line
       $line = trim($line);
       if ($line === '') continue;
      $parts = preg_split('/[,\t]/', $line);
      $col1 = trim((string)($parts[0] ?? ''));
      $col2 = trim((string)($parts[1] ?? ''));
      
      $username = '';
      $name = '';
      
      if (preg_match('/^[0-9]+$/', $col1) && !preg_match('/^[0-9]+$/', $col2)) {
          $username = $col1;
          $name = $col2;
      } else if (preg_match('/^[0-9]+$/', $col2)) {
          $username = $col2;
          $name = $col1;
      } else {
          $fail++;
          continue;
      }
      
      if ($username === '') {
        $fail++;
        continue;
      }
      $stmt = $db->prepare("INSERT INTO `graduation_information`(`studentID`,`name`,`class`) VALUES(?,?,?) ON DUPLICATE KEY UPDATE `name`=VALUES(`name`),`class`=VALUES(`class`)");
      $stmt->bind_param('sss', $username, $name, $class);
      $stmt->execute();
      $stmt->close();
      $ok++;
    }
  }
  jsonSuccess(['ok_count' => $ok, 'fail_count' => $fail]);
} catch (Throwable $e) {
  jsonServerError($e);
}
