<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

require_once 'database.php';

// 获取数据库连接
$db = Database::getInstance();
$pdo = $db->getConnection();

// 获取请求方法和参数
$method = $_SERVER['REQUEST_METHOD'];
$input = json_decode(file_get_contents('php://input'), true);

try {
    if ($method === 'GET' && (isset($_GET['phone']) || isset($_GET['name']))) {
        // 查询座位信息
        $searchValue = '';
        $searchType = '';
        
        if (isset($_GET['phone'])) {
            $searchValue = $_GET['phone'];
            $searchType = 'phone';
            
            // 验证手机号格式
            if (!preg_match('/^1[3-9]\d{9}$/', $searchValue)) {
                throw new Exception('手机号格式不正确');
            }
        } elseif (isset($_GET['name'])) {
            $searchValue = $_GET['name'];
            $searchType = 'name';
            
            // 验证姓名格式
            if (!preg_match('/^[\x{4e00}-\x{9fa5}a-zA-Z\s]{2,10}$/u', $searchValue)) {
                throw new Exception('姓名格式不正确');
            }
        }
        
        // 构建查询语句
        $whereClause = $searchType === 'phone' ? 'phone = ?' : 'name = ?';
        
        // 查询用户信息
        $stmt = $pdo->prepare("
            SELECT 
                id,
                name,
                phone,
                seat_number,
                is_checked_in,
                checkin_time,
                family_count,
                education_info,
                created_at
            FROM registrations 
            WHERE {$whereClause}
        ");
        $stmt->execute([$searchValue]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if (!$user) {
            $errorMsg = $searchType === 'phone' ? '未找到该手机号的报名信息' : '未找到该姓名的报名信息';
            throw new Exception($errorMsg);
        }
        
        // 格式化返回数据
        $response = [
            'success' => true,
            'data' => [
                'id' => $user['id'],
                'name' => $user['name'],
                'phone' => $user['phone'],
                'seat_number' => $user['seat_number'] ?: '暂未分配',
                'is_checked_in' => (bool)$user['is_checked_in'],
                'checkin_status' => $user['is_checked_in'] ? '已签到' : '未签到',
                'checkin_time' => $user['checkin_time'],
                'family_count' => $user['family_count'],
                'education_info' => $user['education_info'],
                'registration_time' => $user['created_at']
            ]
        ];
        
        echo json_encode($response, JSON_UNESCAPED_UNICODE);
        
    } elseif ($method === 'POST' && isset($input['action']) && $input['action'] === 'checkin') {
        // 处理签到
        $phone = $input['phone'] ?? '';
        $name = $input['name'] ?? '';
        
        // 验证输入参数
        if (!$phone && !$name) {
            throw new Exception('请提供手机号或姓名');
        }
        
        $searchValue = '';
        $searchType = '';
        
        if ($phone) {
            // 验证手机号格式
            if (!preg_match('/^1[3-9]\d{9}$/', $phone)) {
                throw new Exception('手机号格式不正确');
            }
            $searchValue = $phone;
            $searchType = 'phone';
        } elseif ($name) {
            // 验证姓名格式
            if (!preg_match('/^[\x{4e00}-\x{9fa5}a-zA-Z\s]{2,10}$/u', $name)) {
                throw new Exception('姓名格式不正确');
            }
            $searchValue = $name;
            $searchType = 'name';
        }
        
        // 检查签到时间
        $stmt = $pdo->prepare("
            SELECT setting_key, setting_value 
            FROM systems 
            WHERE setting_key IN ('checkin_start_time', 'checkin_end_time')
        ");
        $stmt->execute();
        $settings = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
        
        $current_time = date('Y-m-d H:i:s');
        $checkin_start = $settings['checkin_start_time'] ?? null;
        $checkin_end = $settings['checkin_end_time'] ?? null;
        
        if ($checkin_start && $current_time < $checkin_start) {
            throw new Exception('签到时间未开始，请在 ' . $checkin_start . ' 后进行签到');
        }
        
        if ($checkin_end && $current_time > $checkin_end) {
            throw new Exception('签到时间已结束，签到截止时间为 ' . $checkin_end);
        }
        
        // 构建查询语句
        $whereClause = $searchType === 'phone' ? 'phone = ?' : 'name = ?';
        
        // 首先查询报名数据
        $stmt = $pdo->prepare("
            SELECT id, name, phone, is_checked_in, seat_number
            FROM registrations 
            WHERE {$whereClause}
        ");
        $stmt->execute([$searchValue]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
        
        // 如果报名数据中没有找到，则搜索导入数据
        if (!$user) {
            $stmt = $pdo->prepare("
                SELECT id, name, phone, is_checked_in, seat_number
                FROM import_info 
                WHERE {$whereClause}
            ");
            $stmt->execute([$searchValue]);
            $user = $stmt->fetch(PDO::FETCH_ASSOC);
        }
        
        if (!$user) {
            $errorMsg = $searchType === 'phone' ? '未找到该手机号的信息' : '未找到该姓名的信息';
            throw new Exception($errorMsg);
        }
        
        if ($user['is_checked_in']) {
            throw new Exception('您已经签到过了，无需重复签到');
        }
        
        // 执行签到 - 需要确定用户在哪个表中
        $updateTable = 'registrations';
        $checkStmt = $pdo->prepare("SELECT id FROM registrations WHERE {$whereClause}");
        $checkStmt->execute([$searchValue]);
        if (!$checkStmt->fetch()) {
            $updateTable = 'import_info';
        }
        
        $stmt = $pdo->prepare("
            UPDATE {$updateTable} 
            SET is_checked_in = 1, checkin_time = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
            WHERE {$whereClause}
        ");
        $result = $stmt->execute([$searchValue]);
        
        if ($result) {
            $response = [
                'success' => true,
                'message' => '签到成功！',
                'data' => [
                    'name' => $user['name'],
                    'seat_number' => $user['seat_number'] ?: '暂未分配',
                    'checkin_time' => $current_time
                ]
            ];
        } else {
            throw new Exception('签到失败，请重试');
        }
        
        echo json_encode($response, JSON_UNESCAPED_UNICODE);
        
    } else {
        throw new Exception('无效的请求');
    }
    
} catch (Exception $e) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}
?>