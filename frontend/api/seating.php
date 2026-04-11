<?php
/**
 * 前端座位查询 API
 * 福建师范大学广东校友会一周年庆典晚会系统
 * 支持报名数据和导入数据的自动切换查询
 */

require_once 'database.php';

// 设置响应头
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

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
        
        // 首先查询报名数据
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
                created_at,
                'registrations' as data_source
            FROM registrations 
            WHERE {$whereClause}
        ");
        $stmt->execute([$searchValue]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
        
        // 如果在报名数据中找到用户但座位号为空，尝试从导入数据中获取座位信息
        if ($user && empty($user['seat_number'])) {
            $stmt = $pdo->prepare("
                SELECT seat_number 
                FROM import_info 
                WHERE {$whereClause}
            ");
            $stmt->execute([$searchValue]);
            $importSeat = $stmt->fetch(PDO::FETCH_ASSOC);
            if ($importSeat && !empty($importSeat['seat_number'])) {
                $user['seat_number'] = $importSeat['seat_number'];
            }
        }
        
        // 如果报名数据中没有找到，则搜索导入数据
        if (!$user) {
            $stmt = $pdo->prepare("
                SELECT 
                    id,
                    name,
                    phone,
                    seat_number,
                    is_checked_in,
                    checkin_time,
                    0 as family_count,
                    '' as education_info,
                    created_at,
                    'import_info' as data_source
                FROM import_info 
                WHERE {$whereClause}
            ");
            $stmt->execute([$searchValue]);
            $user = $stmt->fetch(PDO::FETCH_ASSOC);
        }
        
        if (!$user) {
            $errorMsg = $searchType === 'phone' ? '未找到该手机号的座位信息' : '未找到该姓名的座位信息';
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
                'registration_time' => $user['created_at'],
                'data_source' => $user['data_source']
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
        
        if ($phone && !preg_match('/^1[3-9]\d{9}$/', $phone)) {
            throw new Exception('手机号格式不正确');
        }
        
        if ($name && !preg_match('/^[\x{4e00}-\x{9fa5}a-zA-Z\s]{2,10}$/u', $name)) {
            throw new Exception('姓名格式不正确');
        }
        
        // 设置搜索值和类型
        $searchValue = $phone ?: $name;
        $searchType = $phone ? 'phone' : 'name';
        
        // 检查签到时间限制
        $stmt = $pdo->prepare("SELECT setting_key, setting_value FROM systems WHERE setting_key IN ('checkin_start_time', 'checkin_end_time')");
        $stmt->execute();
        $timeSettings = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
        
        $currentTime = date('Y-m-d H:i:s');
        $checkinStartTime = $timeSettings['checkin_start_time'] ?? null;
        $checkinEndTime = $timeSettings['checkin_end_time'] ?? null;
        
        if ($checkinStartTime && $currentTime < $checkinStartTime) {
            throw new Exception('签到时间未到，签到开始时间：' . $checkinStartTime);
        }
        
        if ($checkinEndTime && $currentTime > $checkinEndTime) {
            throw new Exception('签到时间已过，签到结束时间：' . $checkinEndTime);
        }
        
        // 智能查找用户：先查registrations表，再查import_info表
        $whereClause = $searchType === 'phone' ? 'phone = ?' : 'name = ?';
        $user = null;
        $tableName = '';
        
        // 先在registrations表中查找
        $stmt = $pdo->prepare("SELECT id, name, phone, is_checked_in FROM registrations WHERE {$whereClause}");
        $stmt->execute([$searchValue]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if ($user) {
            $tableName = 'registrations';
        } else {
            // 如果registrations表中没有，再在import_info表中查找
            $stmt = $pdo->prepare("SELECT id, name, phone, is_checked_in FROM import_info WHERE {$whereClause}");
            $stmt->execute([$searchValue]);
            $user = $stmt->fetch(PDO::FETCH_ASSOC);
            
            if ($user) {
                $tableName = 'import_info';
            }
        }
        
        if (!$user) {
            $errorMsg = $searchType === 'phone' ? '未找到该手机号的信息' : '未找到该姓名的信息';
            throw new Exception($errorMsg);
        }
        
        if ($user['is_checked_in']) {
            throw new Exception('您已经签到过了');
        }
        
        // 执行签到更新
        $stmt = $pdo->prepare("UPDATE {$tableName} SET is_checked_in = 1, checkin_time = NOW() WHERE {$whereClause}");
        $stmt->execute([$searchValue]);
        
        echo json_encode([
            'success' => true,
            'message' => '签到成功',
            'data' => [
                'name' => $user['name'],
                'checkin_time' => date('Y-m-d H:i:s')
            ]
        ], JSON_UNESCAPED_UNICODE);
        
    } else {
        throw new Exception('无效的请求');
    }
    
} catch (Exception $e) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}
?>