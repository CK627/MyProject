<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require_once 'database.php';

class SystemsAPI {
    private $pdo;
    
    public function __construct() {
        $database = Database::getInstance();
        $this->pdo = $database->getConnection();
    }
    
    public function handleRequest() {
        $method = $_SERVER['REQUEST_METHOD'];
        
        switch ($method) {
            case 'GET':
                $this->handleGet();
                break;
            case 'POST':
                $this->handlePost();
                break;
            case 'PUT':
                $this->handlePut();
                break;
            default:
                $this->sendError(405, '不支持的请求方法');
                break;
        }
    }
    
    private function handleGet() {
        $action = $_GET['action'] ?? '';
        
        switch ($action) {
            case 'registration_times':
                $this->getRegistrationTimes();
                break;
            case 'checkin_times':
                $this->getCheckinTimes();
                break;
            default:
                $this->sendError(400, '无效的操作');
                break;
        }
    }
    
    private function handlePost() {
        $rawInput = file_get_contents('php://input');
        $input = json_decode($rawInput, true);
        
        // 添加调试信息
        if (json_last_error() !== JSON_ERROR_NONE) {
            $this->sendError(400, 'JSON解析错误: ' . json_last_error_msg());
            return;
        }
        
        if (!$input) {
            $this->sendError(400, '请求数据为空');
            return;
        }
        
        $action = $input['action'] ?? '';
        
        switch ($action) {
            case 'update_registration_times':
                $this->updateRegistrationTimes($input);
                break;
            case 'update_checkin_times':
                $this->updateCheckinTimes($input);
                break;
            default:
                $this->sendError(400, '无效的操作: ' . $action);
                break;
        }
    }
    
    private function handlePut() {
        $input = json_decode(file_get_contents('php://input'), true);
        $this->updateRegistrationTimes($input);
    }
    
    /**
     * 获取报名时间设置
     */
    private function getRegistrationTimes() {
        try {
            $stmt = $this->pdo->prepare("
                SELECT setting_key, setting_value 
                FROM systems 
                WHERE setting_key IN ('registration_start_time', 'registration_end_time')
            ");
            $stmt->execute();
            $results = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            $times = [];
            foreach ($results as $row) {
                $times[$row['setting_key']] = $row['setting_value'];
            }
            
            // 检查当前时间是否在报名时间范围内
            $currentTime = date('Y-m-d H:i:s');
            $startTime = $times['registration_start_time'] ?? null;
            $endTime = $times['registration_end_time'] ?? null;
            
            $isValid = false;
            if ($startTime && $endTime) {
                $isValid = ($currentTime >= $startTime && $currentTime <= $endTime);
            }
            
            $this->sendSuccess([
                'registration_start_time' => $startTime,
                'registration_end_time' => $endTime,
                'current_time' => $currentTime,
                'is_registration_valid' => $isValid
            ]);
            
        } catch (Exception $e) {
            $this->sendError(500, '获取报名时间失败: ' . $e->getMessage());
        }
    }
    
    /**
     * 更新报名时间设置
     */
    private function updateRegistrationTimes($input) {
        $startTime = $input['registration_start_time'] ?? '';
        $endTime = $input['registration_end_time'] ?? '';
        
        if (!$startTime || !$endTime) {
            $this->sendError(400, '报名开始时间和结束时间不能为空');
            return;
        }
        
        // 验证时间格式
        if (!$this->validateDateTime($startTime) || !$this->validateDateTime($endTime)) {
            $this->sendError(400, '时间格式无效，请使用 YYYY-MM-DD HH:MM:SS 格式');
            return;
        }
        
        // 验证开始时间小于结束时间
        if ($startTime >= $endTime) {
            $this->sendError(400, '报名开始时间必须早于结束时间');
            return;
        }
        
        try {
            $this->pdo->beginTransaction();
            
            // 更新开始时间
            $stmt = $this->pdo->prepare("
                INSERT INTO systems (setting_key, setting_value) 
                VALUES ('registration_start_time', ?) 
                ON DUPLICATE KEY UPDATE setting_value = ?
            ");
            $stmt->execute([$startTime, $startTime]);
            
            // 更新结束时间
            $stmt = $this->pdo->prepare("
                INSERT INTO systems (setting_key, setting_value) 
                VALUES ('registration_end_time', ?) 
                ON DUPLICATE KEY UPDATE setting_value = ?
            ");
            $stmt->execute([$endTime, $endTime]);
            
            $this->pdo->commit();
            
            $this->sendSuccess([
                'message' => '报名时间更新成功',
                'registration_start_time' => $startTime,
                'registration_end_time' => $endTime
            ]);
            
        } catch (Exception $e) {
            $this->pdo->rollBack();
            $this->sendError(500, '更新报名时间失败: ' . $e->getMessage());
        }
    }
    
    /**
     * 获取签到时间设置
     */
    private function getCheckinTimes() {
        try {
            $stmt = $this->pdo->prepare("
                SELECT setting_key, setting_value 
                FROM systems 
                WHERE setting_key IN ('checkin_start_time', 'checkin_end_time')
            ");
            $stmt->execute();
            $results = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            $times = [];
            foreach ($results as $row) {
                $times[$row['setting_key']] = $row['setting_value'];
            }
            
            // 检查当前时间是否在签到时间范围内
            $currentTime = date('Y-m-d H:i:s');
            $startTime = $times['checkin_start_time'] ?? null;
            $endTime = $times['checkin_end_time'] ?? null;
            
            $isValid = false;
            if ($startTime && $endTime) {
                $isValid = ($currentTime >= $startTime && $currentTime <= $endTime);
            }
            
            $this->sendSuccess([
                'checkin_start_time' => $startTime,
                'checkin_end_time' => $endTime,
                'current_time' => $currentTime,
                'is_checkin_valid' => $isValid
            ]);
            
        } catch (Exception $e) {
            $this->sendError(500, '获取签到时间失败: ' . $e->getMessage());
        }
    }
    
    /**
     * 更新签到时间设置
     */
    private function updateCheckinTimes($input) {
        $startTime = $input['checkin_start_time'] ?? '';
        $endTime = $input['checkin_end_time'] ?? '';
        
        if (!$startTime || !$endTime) {
            $this->sendError(400, '签到开始时间和结束时间不能为空');
            return;
        }
        
        // 验证时间格式
        if (!$this->validateDateTime($startTime) || !$this->validateDateTime($endTime)) {
            $this->sendError(400, '时间格式无效，请使用 YYYY-MM-DD HH:MM:SS 格式');
            return;
        }
        
        // 验证开始时间小于结束时间
        if ($startTime >= $endTime) {
            $this->sendError(400, '签到开始时间必须早于结束时间');
            return;
        }
        
        try {
            $this->pdo->beginTransaction();
            
            // 更新开始时间
            $stmt = $this->pdo->prepare("
                INSERT INTO systems (setting_key, setting_value) 
                VALUES ('checkin_start_time', ?) 
                ON DUPLICATE KEY UPDATE setting_value = ?
            ");
            $stmt->execute([$startTime, $startTime]);
            
            // 更新结束时间
            $stmt = $this->pdo->prepare("
                INSERT INTO systems (setting_key, setting_value) 
                VALUES ('checkin_end_time', ?) 
                ON DUPLICATE KEY UPDATE setting_value = ?
            ");
            $stmt->execute([$endTime, $endTime]);
            
            $this->pdo->commit();
            
            $this->sendSuccess([
                'message' => '签到时间更新成功',
                'checkin_start_time' => $startTime,
                'checkin_end_time' => $endTime
            ]);
            
        } catch (Exception $e) {
            $this->pdo->rollBack();
            $this->sendError(500, '更新签到时间失败: ' . $e->getMessage());
        }
    }
    
    /**
     * 验证日期时间格式
     */
    private function validateDateTime($datetime) {
        $d = DateTime::createFromFormat('Y-m-d H:i:s', $datetime);
        return $d && $d->format('Y-m-d H:i:s') === $datetime;
    }
    
    /**
     * 发送成功响应
     */
    private function sendSuccess($data) {
        http_response_code(200);
        echo json_encode([
            'success' => true,
            'data' => $data
        ], JSON_UNESCAPED_UNICODE);
    }
    
    /**
     * 发送错误响应
     */
    private function sendError($code, $message) {
        http_response_code($code);
        echo json_encode([
            'success' => false,
            'error' => $message
        ], JSON_UNESCAPED_UNICODE);
    }
}

// 创建API实例并处理请求
$api = new SystemsAPI();
$api->handleRequest();
?>