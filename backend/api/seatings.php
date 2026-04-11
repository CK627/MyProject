<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

// 引入数据库配置
require_once 'database.php';

// 获取数据库连接
$db = Database::getInstance();
$pdo = $db->getConnection();

// 获取请求方法和操作类型
$method = $_SERVER['REQUEST_METHOD'];
$action = $_GET['action'] ?? '';

try {
    switch ($method) {
        case 'GET':
            handleGetRequest($action);
            break;
        case 'POST':
            handlePostRequest($action);
            break;
        case 'PUT':
            handlePutRequest($action);
            break;
        case 'DELETE':
            handleDeleteRequest($action);
            break;
        default:
            throw new Exception('不支持的请求方法');
    }
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage()
    ]);
}

function handleGetRequest($action) {
    global $pdo;
    
    switch ($action) {
        case 'list':
            getSeatings();
            break;
        case 'search':
            searchSeatings();
            break;
        default:
            throw new Exception('无效的操作');
    }
}

function handlePostRequest($action) {
    global $pdo;
    
    switch ($action) {
        case 'import':
            importSeatings();
            break;
        case 'batch_assign':
            batchAssignSeats();
            break;
        default:
            throw new Exception('无效的操作');
    }
}

function handlePutRequest($action) {
    global $pdo;
    
    switch ($action) {
        case 'update':
            updateSeating();
            break;
        default:
            throw new Exception('无效的操作');
    }
}

function handleDeleteRequest($action) {
    global $pdo;
    
    switch ($action) {
        case 'delete':
            deleteSeating();
            break;
        default:
            throw new Exception('无效的操作');
    }
}

function getSeatings() {
    global $pdo;
    
    $page = intval($_GET['page'] ?? 1);
    $pageSize = intval($_GET['pageSize'] ?? 20);
    $dataSource = $_GET['dataSource'] ?? 'registrations';
    $seatStatus = $_GET['seatStatus'] ?? '';
    $checkinStatus = $_GET['checkinStatus'] ?? '';
    
    $offset = ($page - 1) * $pageSize;
    
    // 根据数据源选择表名
    $tableName = ($dataSource === 'import_info') ? 'import_info' : 'registrations';
    
    // 构建查询条件
    $whereConditions = [];
    $params = [];
    
    if ($seatStatus === 'assigned') {
        $whereConditions[] = "seat_number IS NOT NULL AND seat_number != ''";
    } elseif ($seatStatus === 'unassigned') {
        $whereConditions[] = "(seat_number IS NULL OR seat_number = '')";
    }
    
    if ($checkinStatus === 'checked_in') {
        $whereConditions[] = "is_checked_in = 1";
    } elseif ($checkinStatus === 'not_checked_in') {
        $whereConditions[] = "is_checked_in = 0";
    }
    
    $whereClause = '';
    if (!empty($whereConditions)) {
        $whereClause = 'WHERE ' . implode(' AND ', $whereConditions);
    }
    
    // 获取总记录数
    $countSql = "SELECT COUNT(*) FROM $tableName $whereClause";
    $countStmt = $pdo->prepare($countSql);
    $countStmt->execute($params);
    $totalRecords = $countStmt->fetchColumn();
    
    // 获取分页数据
    if ($tableName === 'import_info') {
        $sql = "SELECT id, name, phone, seat_number, is_checked_in, checkin_time
                FROM $tableName 
                $whereClause 
                ORDER BY created_at DESC 
                LIMIT :offset, :pageSize";
    } else {
        $sql = "SELECT id, name, phone, seat_number, is_checked_in, checkin_time
                FROM $tableName 
                $whereClause 
                ORDER BY created_at DESC 
                LIMIT :offset, :pageSize";
    }
    
    $stmt = $pdo->prepare($sql);
    foreach ($params as $key => $value) {
        $stmt->bindValue($key, $value);
    }
    $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
    $stmt->bindValue(':pageSize', $pageSize, PDO::PARAM_INT);
    $stmt->execute();
    
    $seatings = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    // 格式化数据
    foreach ($seatings as &$seating) {
        $seating['seat_number'] = $seating['seat_number'] ?: '未安排座位';
        $seating['is_checked_in'] = intval($seating['is_checked_in']);
        $seating['checkin_status_text'] = $seating['is_checked_in'] ? '已签到' : '未签到';
        $seating['checkin_time'] = $seating['checkin_time'] ? date('Y-m-d H:i', strtotime($seating['checkin_time'])) : '未签到';
    }
    
    echo json_encode([
        'success' => true,
        'data' => $seatings,
        'pagination' => [
            'page' => $page,
            'pageSize' => $pageSize,
            'totalRecords' => intval($totalRecords),
            'totalPages' => ceil($totalRecords / $pageSize)
        ]
    ]);
}

function searchSeatings() {
    global $pdo;
    
    $keyword = $_GET['keyword'] ?? '';
    $dataSource = $_GET['dataSource'] ?? 'registrations';
    $page = intval($_GET['page'] ?? 1);
    $pageSize = intval($_GET['pageSize'] ?? 20);
    
    if (empty($keyword)) {
        getSeatings();
        return;
    }
    
    $offset = ($page - 1) * $pageSize;
    
    // 根据数据源选择表名
    $tableName = ($dataSource === 'import_info') ? 'import_info' : 'registrations';
    
    // 构建搜索条件
    $searchCondition = "(name LIKE ? OR phone LIKE ? OR seat_number LIKE ?)";
    $searchKeyword = "%$keyword%";
    
    // 获取总记录数
    $countSql = "SELECT COUNT(*) FROM $tableName WHERE $searchCondition";
    $countStmt = $pdo->prepare($countSql);
    $countStmt->execute([$searchKeyword, $searchKeyword, $searchKeyword]);
    $totalRecords = $countStmt->fetchColumn();
    
    // 获取分页数据
    if ($tableName === 'import_info') {
        $sql = "SELECT id, name, phone, seat_number, is_checked_in, checkin_time
                FROM $tableName 
                WHERE $searchCondition 
                ORDER BY created_at DESC 
                LIMIT ?, ?";
    } else {
        $sql = "SELECT id, name, phone, seat_number, is_checked_in, checkin_time
                FROM $tableName 
                WHERE $searchCondition 
                ORDER BY created_at DESC 
                LIMIT ?, ?";
    }
    
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$searchKeyword, $searchKeyword, $searchKeyword, $offset, $pageSize]);
    
    $seatings = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    // 格式化数据
    foreach ($seatings as &$seating) {
        $seating['seat_number'] = $seating['seat_number'] ?: '未安排座位';
        $seating['is_checked_in'] = intval($seating['is_checked_in']);
        $seating['checkin_status_text'] = $seating['is_checked_in'] ? '已签到' : '未签到';
        $seating['checkin_time'] = $seating['checkin_time'] ? date('Y-m-d H:i', strtotime($seating['checkin_time'])) : '未签到';
    }
    
    echo json_encode([
        'success' => true,
        'data' => $seatings,
        'pagination' => [
            'page' => $page,
            'pageSize' => $pageSize,
            'totalRecords' => intval($totalRecords),
            'totalPages' => ceil($totalRecords / $pageSize)
        ]
    ]);
}

function updateSeating() {
    global $pdo;
    
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!isset($input['id'])) {
        throw new Exception('缺少记录ID');
    }
    
    $id = intval($input['id']);
    $dataSource = $input['dataSource'] ?? 'registrations';
    $seatNumber = trim($input['seat_number'] ?? '');
    $isCheckedIn = intval($input['is_checked_in'] ?? 0);
    
    // 根据数据源选择表名
    $tableName = ($dataSource === 'import_info') ? 'import_info' : 'registrations';
    
    // 如果座位号为空，设置为NULL
    if (empty($seatNumber)) {
        $seatNumber = null;
    }
    
    // 获取当前记录的座位号
    $getCurrentSql = "SELECT seat_number FROM $tableName WHERE id = :id";
    $getCurrentStmt = $pdo->prepare($getCurrentSql);
    $getCurrentStmt->execute([':id' => $id]);
    $currentRecord = $getCurrentStmt->fetch(PDO::FETCH_ASSOC);
    
    if (!$currentRecord) {
        throw new Exception('记录不存在');
    }
    
    $currentSeatNumber = $currentRecord['seat_number'];
    
    // 允许座位号重复，不进行重复检查
    
    // 更新座位信息
    // 如果清除签到状态，同时清除签到时间
    if ($isCheckedIn == 0) {
        $sql = "UPDATE $tableName SET seat_number = :seat_number, is_checked_in = :is_checked_in, checkin_time = NULL WHERE id = :id";
        $stmt = $pdo->prepare($sql);
        $result = $stmt->execute([
            ':seat_number' => $seatNumber,
            ':is_checked_in' => $isCheckedIn,
            ':id' => $id
        ]);
    } else {
        // 如果设置为已签到，更新签到时间为当前时间
        $sql = "UPDATE $tableName SET seat_number = :seat_number, is_checked_in = :is_checked_in, checkin_time = CURRENT_TIMESTAMP WHERE id = :id";
        $stmt = $pdo->prepare($sql);
        $result = $stmt->execute([
            ':seat_number' => $seatNumber,
            ':is_checked_in' => $isCheckedIn,
            ':id' => $id
        ]);
    }
    
    if (!$result) {
        throw new Exception('更新失败');
    }
    
    echo json_encode([
        'success' => true,
        'message' => '座位信息更新成功'
    ]);
}

function importSeatings() {
    global $pdo;
    
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!isset($input['data']) || !is_array($input['data'])) {
        throw new Exception('无效的导入数据');
    }
    
    $importData = $input['data'];
    $successCount = 0;
    $errorCount = 0;
    $errors = [];
    
    $pdo->beginTransaction();
    
    try {
        foreach ($importData as $index => $row) {
            $rowNumber = $index + 1;
            
            // 验证必要字段
            if (empty($row['name']) || empty($row['phone']) || empty($row['seat_number'])) {
                $errors[] = "第{$rowNumber}行：姓名、手机号和座位号不能为空";
                $errorCount++;
                continue;
            }
            
            $name = trim($row['name']);
            $phone = trim($row['phone']);
            $seatNumber = trim($row['seat_number']);
            
            // 验证手机号格式
            if (!preg_match('/^1[3-9]\d{9}$/', $phone)) {
                $errors[] = "第{$rowNumber}行：手机号格式不正确";
                $errorCount++;
                continue;
            }
            
            // 检查用户是否存在
            $checkUserSql = "SELECT id FROM registrations WHERE phone = :phone";
            $checkUserStmt = $pdo->prepare($checkUserSql);
            $checkUserStmt->execute([':phone' => $phone]);
            $user = $checkUserStmt->fetch();
            
            if (!$user) {
                $errors[] = "第{$rowNumber}行：手机号 {$phone} 对应的用户不存在";
                $errorCount++;
                continue;
            }
            
            // 允许座位号重复，不进行重复检查
            
            // 更新座位号
            $updateSql = "UPDATE registrations SET seat_number = :seat_number WHERE id = :id";
            $updateStmt = $pdo->prepare($updateSql);
            $result = $updateStmt->execute([
                ':seat_number' => $seatNumber,
                ':id' => $user['id']
            ]);
            
            if ($result) {
                $successCount++;
            } else {
                $errors[] = "第{$rowNumber}行：更新失败";
                $errorCount++;
            }
        }
        
        $pdo->commit();
        
        echo json_encode([
            'success' => true,
            'message' => "导入完成：成功 {$successCount} 条，失败 {$errorCount} 条",
            'details' => [
                'successCount' => $successCount,
                'errorCount' => $errorCount,
                'errors' => $errors
            ]
        ]);
        
    } catch (Exception $e) {
        $pdo->rollBack();
        throw $e;
    }
}

function batchAssignSeats() {
    global $pdo;
    
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!isset($input['ids']) || !is_array($input['ids'])) {
        throw new Exception('缺少用户ID列表');
    }
    
    $ids = array_map('intval', $input['ids']);
    $prefix = trim($input['prefix'] ?? '');
    $startNumber = intval($input['startNumber'] ?? 1);
    
    if (empty($ids)) {
        throw new Exception('未选择任何用户');
    }
    
    $pdo->beginTransaction();
    
    try {
        $successCount = 0;
        $currentNumber = $startNumber;
        
        foreach ($ids as $id) {
            // 生成座位号
            $seatNumber = $prefix . $currentNumber;
            
            // 允许座位号重复，直接按顺序分配
            
            // 更新座位号
            $updateSql = "UPDATE registrations SET seat_number = :seat_number WHERE id = :id";
            $updateStmt = $pdo->prepare($updateSql);
            $result = $updateStmt->execute([
                ':seat_number' => $seatNumber,
                ':id' => $id
            ]);
            
            if ($result) {
                $successCount++;
            }
            
            $currentNumber++;
        }
        
        $pdo->commit();
        
        echo json_encode([
            'success' => true,
            'message' => "批量分配完成：成功分配 {$successCount} 个座位"
        ]);
        
    } catch (Exception $e) {
        $pdo->rollBack();
        throw $e;
    }
}

function deleteSeating() {
    global $pdo;
    
    $id = intval($_GET['id'] ?? 0);
    $dataSource = $_GET['dataSource'] ?? 'registrations';
    
    if ($id <= 0) {
        throw new Exception('无效的记录ID');
    }
    
    // 根据数据源选择表名
    $tableName = ($dataSource === 'import_info') ? 'import_info' : 'registrations';
    
    // 清除座位号（不删除用户记录，只清除座位分配）
    $sql = "UPDATE $tableName SET seat_number = NULL WHERE id = :id";
    $stmt = $pdo->prepare($sql);
    $result = $stmt->execute([':id' => $id]);
    
    if (!$result) {
        throw new Exception('清除座位分配失败');
    }
    
    echo json_encode([
        'success' => true,
        'message' => '座位分配已清除'
    ]);
}
?>