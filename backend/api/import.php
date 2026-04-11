<?php
// 数据导入API接口
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// 只允许POST请求
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'message' => '只允许POST请求']);
    exit();
}

require_once 'database.php';

try {
    // 获取数据库连接
    $db = Database::getInstance();
    $pdo = $db->getConnection();
    
    // 获取POST数据
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if (!$data || !isset($data['importData']) || !is_array($data['importData'])) {
        throw new Exception('无效的导入数据格式');
    }
    
    $importData = $data['importData'];
    $totalCount = count($importData);
    $successCount = 0;
    $skipCount = 0;
    $errorCount = 0;
    $errors = [];
    $warnings = [];
    
    // 开始事务
    $pdo->beginTransaction();
    
    // 字段映射
    $fieldMappings = [
        'name' => ['姓名', '名字', 'name', 'Name', '参会人员', '人员姓名'],
        'phone' => ['手机号', '电话', '手机', 'phone', 'Phone', '联系电话', '手机号码'],
        'seat_number' => ['座位号', '座位', 'seat', 'Seat', '座位编号', '席位号']
    ];
    
    // 准备插入语句
    $insertStmt = $pdo->prepare("
        INSERT INTO import_info (name, phone, seat_number, is_checked_in, created_at, updated_at) 
        VALUES (?, ?, ?, 0, NOW(), NOW())
    ");
    
    // 准备检查重复的语句
    $checkStmt = $pdo->prepare("SELECT COUNT(*) FROM import_info WHERE name = ?");
    $checkPhoneStmt = $pdo->prepare("SELECT COUNT(*) FROM import_info WHERE phone = ? AND phone IS NOT NULL AND phone != ''");
    
    // 准备检查registrations表的语句
    $checkRegistrationStmt = $pdo->prepare("SELECT id, seat_number FROM registrations WHERE name = ?");
    $updateRegistrationStmt = $pdo->prepare("UPDATE registrations SET seat_number = ? WHERE id = ?");
    
    foreach ($importData as $index => $row) {
        try {
            $rowNumber = $row['_rowIndex'] ?? ($index + 2);
            
            // 提取字段值
            $name = null;
            $phone = null;
            $seatNumber = null;
            
            // 查找姓名字段
            foreach ($row as $field => $value) {
                if (in_array($field, $fieldMappings['name']) && $value) {
                    $name = trim($value);
                    break;
                }
            }
            
            // 查找手机号字段
            foreach ($row as $field => $value) {
                if (in_array($field, $fieldMappings['phone']) && $value) {
                    $phone = trim($value);
                    break;
                }
            }
            
            // 查找座位号字段
            foreach ($row as $field => $value) {
                if (in_array($field, $fieldMappings['seat_number']) && $value) {
                    $seatNumber = trim($value);
                    break;
                }
            }
            
            // 验证必填字段
            if (empty($name)) {
                $skipCount++;
                $warnings[] = "第{$rowNumber}行：姓名为空，已跳过";
                continue;
            }
            
            // 验证手机号格式（如果提供）
            if ($phone && !preg_match('/^1[3-9]\d{9}$/', $phone)) {
                $warnings[] = "第{$rowNumber}行：手机号\"{$phone}\"格式不正确，但仍会导入";
            }
            
            // 首先检查registrations表中是否存在该姓名
            $checkRegistrationStmt->execute([$name]);
            $registrationData = $checkRegistrationStmt->fetch(PDO::FETCH_ASSOC);
            
            if ($registrationData) {
                // 如果在registrations表中找到了对应的姓名，更新座位号
                if ($seatNumber) {
                    $updateRegistrationStmt->execute([$seatNumber, $registrationData['id']]);
                    $successCount++;
                    $warnings[] = "第{$rowNumber}行：已更新registrations表中\"{$name}\"的座位号为\"{$seatNumber}\"";
                } else {
                    $skipCount++;
                    $warnings[] = "第{$rowNumber}行：\"{$name}\"在registrations表中存在，但未提供座位号，已跳过";
                }
            } else {
                // 如果在registrations表中没有找到，则插入到import_info表
                
                // 检查import_info表中姓名是否已存在
                $checkStmt->execute([$name]);
                $existCount = $checkStmt->fetchColumn();
                
                if ($existCount > 0) {
                    $skipCount++;
                    $warnings[] = "第{$rowNumber}行：姓名\"{$name}\"在import_info表中已存在，已跳过";
                    continue;
                }
                
                // 检查import_info表中手机号是否已存在（如果提供了手机号）
                if ($phone) {
                    $checkPhoneStmt->execute([$phone]);
                    $phoneExistCount = $checkPhoneStmt->fetchColumn();
                    
                    if ($phoneExistCount > 0) {
                        $skipCount++;
                        $warnings[] = "第{$rowNumber}行：手机号\"{$phone}\"在import_info表中已存在，已跳过";
                        continue;
                    }
                }
                
                // 插入数据到import_info表
                $insertStmt->execute([
                    $name,
                    $phone ?: null,
                    $seatNumber ?: null
                ]);
                
                $successCount++;
                $warnings[] = "第{$rowNumber}行：\"{$name}\"已添加到import_info表";
            }
            
        } catch (Exception $e) {
            $errorCount++;
            $errors[] = "第{$rowNumber}行导入失败：" . $e->getMessage();
        }
    }
    
    // 提交事务
    $pdo->commit();
    
    // 返回结果
    $result = [
        'success' => true,
        'message' => "导入完成！共处理 {$totalCount} 条记录",
        'stats' => [
            'total' => $totalCount,
            'success' => $successCount,
            'skip' => $skipCount,
            'error' => $errorCount
        ],
        'warnings' => $warnings,
        'errors' => $errors
    ];
    
    echo json_encode($result, JSON_UNESCAPED_UNICODE);
    
} catch (Exception $e) {
    // 回滚事务
    if ($pdo->inTransaction()) {
        $pdo->rollBack();
    }
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => '导入失败：' . $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}
?>