<?php
/**
 * 报名系统 API
 * 福建师范大学广东校友会一周年庆典晚会系统
 * 包含报名管理和系统设置功能
 */

require_once 'database.php';

// 设置响应头
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

class RegistrationsAPI {
    private $db;
    
    public function __construct() {
        $this->db = Database::getInstance();
    }
    
    /**
     * 检查报名时间是否有效
     */
    private function isRegistrationTimeValid() {
        $startTime = $this->getSetting('registration_start_time');
        $endTime = $this->getSetting('registration_end_time');
        
        if (!$startTime || !$endTime) {
            return false;
        }
        
        $currentTime = date('Y-m-d H:i:s');
        $startTimeValue = $startTime['value'];
        $endTimeValue = $endTime['value'];
        
        return ($currentTime >= $startTimeValue && $currentTime <= $endTimeValue);
    }
    
    /**
     * 验证报名数据
     */
    private function validateRegistrationData($data) {
        $required = ['name', 'phone', 'family_count', 'payment_method'];
        
        // 检查必填字段
        foreach ($required as $field) {
            if (!isset($data[$field])) {
                return ['valid' => false, 'message' => "缺少必填字段: {$field}"];
            }
            
            // 对于family_count字段，允许值为"0"
            if ($field === 'family_count') {
                if ($data[$field] === '' || $data[$field] === null) {
                    return ['valid' => false, 'message' => "缺少必填字段: {$field}"];
                }
            } else {
                // 其他字段使用empty()检查
                if (empty($data[$field])) {
                    return ['valid' => false, 'message' => "缺少必填字段: {$field}"];
                }
            }
        }
        
        // 验证姓名
        if (strlen($data['name']) < 2 || strlen($data['name']) > 20) {
            return ['valid' => false, 'message' => '姓名长度应在2-20个字符之间'];
        }
        
        // 验证手机号
        if (!preg_match('/^1[3-9]\d{9}$/', $data['phone'])) {
            return ['valid' => false, 'message' => '请输入正确的手机号码'];
        }
        
        // 验证家属人数
        $familyCount = intval($data['family_count']);
        if ($familyCount < 0 || $familyCount > 2) {
            return ['valid' => false, 'message' => '家属人数应在0-2人之间'];
        }
        
        // 验证缴费金额
        if (isset($data['payment_amount'])) {
            $paymentAmount = floatval($data['payment_amount']);
            if ($paymentAmount < 0 || $paymentAmount > 99999) {
                return ['valid' => false, 'message' => '缴费金额应在0-99999元之间'];
            }
        }
        
        // 验证付款方式
        if (!in_array($data['payment_method'], ['wechat', 'alipay', 'other'])) {
            return ['valid' => false, 'message' => '无效的付款方式'];
        }
        
        // 已移除额外捐赠功能相关验证
        
        return ['valid' => true];
    }
    
    /**
     * 检查手机号是否已存在
     */
    private function isPhoneExists($phone) {
        $sql = "SELECT COUNT(*) as count FROM registrations WHERE phone = :phone";
        $result = $this->db->fetchOne($sql, ['phone' => $phone]);
        return $result && $result['count'] > 0;
    }
    

    

    
    /**
     * 插入报名数据到数据库
     */
    private function insertRegistration($data, $totalAmount) {
        $calculatedAmount = floatval($data['payment_amount'] ?? 0);
        
        $insertData = [
            'name' => $data['name'],
            'phone' => $data['phone'],
            'is_2025_student' => intval($data['is_2025_student'] ?? 0),
            'education_info' => $data['education_info'] ?? null,
            'family_count' => intval($data['family_count'] ?? 0),
            'talent_show' => $data['talent_show'] ?? '',
            'talent_description' => $data['talent_description'] ?? null,
            'material_sponsorship' => $data['material_sponsorship'] ?? null,
            'remarks' => $data['remarks'] ?? null,
            'payment_method' => $data['payment_method'],
            'payment_screenshot' => $data['payment_screenshot'] ?? null,
            'total_amount' => $calculatedAmount
        ];
        
        return $this->db->insert('registrations', $insertData);
    }
    
    /**
     * 处理API请求
     */
    public function handleRequest() {
        try {
            $method = $_SERVER['REQUEST_METHOD'];
            $action = $_GET['action'] ?? 'registration';
            
            switch ($action) {
                case 'registration':
                    $this->handleRegistration($method);
                    break;
                case 'settings':
                case 'systems':
                    $this->handleSystemSettings($method);
                    break;
                default:
                    $this->sendError('不支持的操作类型', 400);
                    break;
            }
        } catch (Exception $e) {
            error_log('报名系统API错误: ' . $e->getMessage());
            $this->sendError('服务器内部错误', 500);
        }
    }
    
    /**
     * 处理报名相关请求
     */
    private function handleRegistration($method) {
        switch ($method) {
            case 'GET':
                $this->getRegistrations();
                break;
            case 'POST':
                $this->createRegistration();
                break;
            default:
                $this->sendError('不支持的请求方法', 405);
                break;
        }
    }
    
    /**
     * 处理系统设置相关请求
     */
    private function handleSystemSettings($method) {
        switch ($method) {
            case 'GET':
                $this->getSystemSettings();
                break;
            case 'POST':
                $this->updateSystemSettings();
                break;
            default:
                $this->sendError('不支持的请求方法', 405);
                break;
        }
    }
    
    /**
     * 获取报名信息
     */
    private function getRegistrations() {
        $action = $_GET['sub_action'] ?? 'list';
        
        switch ($action) {
            case 'list':
                $this->getRegistrationList();
                break;
            case 'stats':
                $this->getRegistrationStats();
                break;
            case 'detail':
                $this->getRegistrationDetail();
                break;
            default:
                $this->sendError('不支持的操作', 400);
                break;
        }
    }
    
    /**
     * 获取报名列表
     */
    private function getRegistrationList() {
        $page = intval($_GET['page'] ?? 1);
        $limit = intval($_GET['limit'] ?? 20);
        $offset = ($page - 1) * $limit;
        
        // 获取总数
        $countSql = "SELECT COUNT(*) as total FROM registrations";
        $totalResult = $this->db->fetchOne($countSql);
        $total = $totalResult['total'];
        
        // 获取列表数据（已移除total_amount字段）
        $sql = "SELECT id, name, phone, family_count, created_at 
                FROM registrations 
                ORDER BY created_at DESC 
                LIMIT :limit OFFSET :offset";
        
        $registrations = $this->db->fetchAll($sql, [
            'limit' => $limit,
            'offset' => $offset
        ]);
        
        $this->sendSuccess([
            'list' => $registrations,
            'pagination' => [
                'total' => $total,
                'page' => $page,
                'limit' => $limit,
                'pages' => ceil($total / $limit)
            ]
        ]);
    }
    
    /**
     * 获取报名统计
     */
    private function getRegistrationStats() {
        $sql = "SELECT 
                    COUNT(*) as total_registrations,
                    SUM(1 + family_count) as total_people
                FROM registrations";
        
        $stats = $this->db->fetchOne($sql);
        
        $this->sendSuccess($stats);
    }
    
    /**
     * 获取报名详情
     */
    private function getRegistrationDetail() {
        $id = $_GET['id'] ?? null;
        if (!$id) {
            $this->sendError('缺少报名ID', 400);
            return;
        }
        
        $sql = "SELECT * FROM registrations WHERE id = :id";
        $registration = $this->db->fetchOne($sql, ['id' => $id]);
        
        if (!$registration) {
            $this->sendError('报名信息不存在', 404);
            return;
        }
        
        $this->sendSuccess($registration);
    }
    
    /**
     * 创建报名
     */
    private function createRegistration() {
        try {
            // 1. 首先检查页面状态
            $pageStatus = $this->getSetting('registration_page_status');
            if ($pageStatus && $pageStatus['value'] === 'maintenance') {
                $this->sendError('报名系统正在维护中，请稍后再试', 503);
                return;
            }
            
            // 2. 检查报名时间是否在有效范围内
            if (!$this->isRegistrationTimeValid()) {
                $this->sendError('当前不在报名时间范围内，请在规定时间内进行报名', 403);
                return;
            }
            
            // 3. 获取并验证POST数据（支持FormData和JSON）
            $input = [];
            
            // 检查是否是FormData（包含文件上传）
            if (!empty($_POST)) {
                $input = $_POST;
            } else {
                // 尝试解析JSON数据
                $jsonInput = json_decode(file_get_contents('php://input'), true);
                if ($jsonInput) {
                    $input = $jsonInput;
                }
            }
            
            if (empty($input)) {
                $this->sendError('无效的请求数据', 400);
                return;
            }
            
            // 4. 验证必填字段（先验证数据，不处理文件）
            $validationResult = $this->validateRegistrationData($input);
            if (!$validationResult['valid']) {
                $this->sendError($validationResult['message'], 400);
                return;
            }
            
            // 5. 检查手机号是否已存在
            if ($this->isPhoneExists($input['phone'])) {
                $this->sendError('该手机号已报名，请勿重复报名', 409);
                return;
            }
            
            // 6. 验证文件上传（但不实际移动文件）
            if (!isset($_FILES['payment_screenshot']) || $_FILES['payment_screenshot']['error'] !== UPLOAD_ERR_OK) {
                $this->sendError('请上传付款凭证', 400);
                return;
            }
            
            // 验证文件类型和大小
            $file = $_FILES['payment_screenshot'];
            $allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
            if (!in_array($file['type'], $allowedTypes)) {
                $this->sendError('不支持的文件类型，请上传图片文件', 400);
                return;
            }
            
            $maxSize = 5 * 1024 * 1024; // 5MB
            if ($file['size'] > $maxSize) {
                $this->sendError('文件大小超过限制，请上传小于5MB的文件', 400);
                return;
            }
            
            // 7. 所有验证通过后，处理文件上传
            $paymentScreenshotPath = $this->handleFileUpload($file, $input);
            if (!$paymentScreenshotPath) {
                $this->sendError('付款凭证上传失败', 500);
                return;
            }
            
            // 8. 计算总金额（使用用户输入的缴费金额）
            $totalAmount = floatval($input['payment_amount'] ?? 0);
            
            // 9. 将文件路径添加到数据中
            $input['payment_screenshot'] = $paymentScreenshotPath;
            
            // 10. 插入数据库
            $registrationId = $this->insertRegistration($input, $totalAmount);
            
            if ($registrationId) {
                $this->sendSuccess([
                    'message' => '报名成功！',
                    'registration_id' => $registrationId,
                    'payment_screenshot' => $paymentScreenshotPath
                ]);
            } else {
                // 如果数据库插入失败，删除已上传的文件
                $this->deleteUploadedFile($paymentScreenshotPath);
                $this->sendError('报名失败，请稍后重试', 500);
            }
            
        } catch (Exception $e) {
            error_log('报名创建错误: ' . $e->getMessage() . ' - 堆栈: ' . $e->getTraceAsString());
            $this->sendError('服务器内部错误', 500);
        }
    }
    
    /**
     * 处理文件上传
     */
    private function handleFileUpload($file, $userData) {
        try {
            // 验证文件类型
            $allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
            if (!in_array($file['type'], $allowedTypes)) {
                throw new Exception('不支持的文件类型，请上传图片文件');
            }
            
            // 验证文件大小（最大5MB）
            $maxSize = 5 * 1024 * 1024; // 5MB
            if ($file['size'] > $maxSize) {
                throw new Exception('文件大小超过限制，请上传小于5MB的文件');
            }
            
            // 生成文件名：姓名_手机号（已移除缴费金额）
            $name = $userData['name'] ?? 'unknown';
            $phone = $userData['phone'] ?? 'unknown';
            $extension = pathinfo($file['name'], PATHINFO_EXTENSION);
            $filename = $name . '_' . $phone . '.' . $extension;
            
            // 确保目录存在
            $uploadDir = __DIR__ . '/../pages/payment-records/';
            if (!is_dir($uploadDir)) {
                mkdir($uploadDir, 0755, true);
            }
            
            // 直接覆盖同名文件
            $targetPath = $uploadDir . $filename;
            
            // 移动文件
            if (move_uploaded_file($file['tmp_name'], $targetPath)) {
                // 返回相对路径
                return 'pages/payment-records/' . $filename;
            } else {
                throw new Exception('文件保存失败');
            }
            
        } catch (Exception $e) {
            error_log('文件上传错误: ' . $e->getMessage());
            return false;
        }
    }
    
    /**
     * 删除已上传的文件
     */
    private function deleteUploadedFile($filePath) {
        try {
            if ($filePath && file_exists(__DIR__ . '/../' . $filePath)) {
                unlink(__DIR__ . '/../' . $filePath);
                return true;
            }
        } catch (Exception $e) {
            error_log('删除文件失败: ' . $e->getMessage());
        }
        return false;
    }

    
    /**
     * 获取系统设置
     */
    private function getSystemSettings() {
        $settingKey = $_GET['key'] ?? null;
        
        if ($settingKey) {
            // 获取单个设置
            $setting = $this->getSetting($settingKey);
            if ($setting) {
                $this->sendSuccess($setting);
            } else {
                $this->sendError('设置不存在', 404);
            }
        } else {
            // 获取所有设置
            $settings = $this->getAllSettings();
            $this->sendSuccess($settings);
        }
    }
    
    /**
     * 更新系统设置（预留功能）
     */
    private function updateSystemSettings() {
        // 这里可以添加更新设置的功能
        // 目前只是预留接口
        $this->sendError('暂不支持设置更新', 501);
    }
    
    /**
     * 获取单个设置
     */
    private function getSetting($key) {
        $sql = "SELECT * FROM systems WHERE setting_key = :key";
        $result = $this->db->fetchOne($sql, ['key' => $key]);
        
        if ($result) {
            return [
                'key' => $result['setting_key'],
                'value' => $result['setting_value'],
                'description' => $result['setting_description'],
                'updated_at' => $result['updated_at']
            ];
        }
        
        return null;
    }
    
    /**
     * 获取所有设置
     */
    private function getAllSettings() {
        $sql = "SELECT * FROM systems ORDER BY setting_key";
        $results = $this->db->fetchAll($sql);
        
        $settings = [];
        foreach ($results as $row) {
            $settings[] = [
                'setting_key' => $row['setting_key'],
                'setting_value' => $row['setting_value'],
                'setting_description' => $row['setting_description'],
                'updated_at' => $row['updated_at']
            ];
        }
        
        return $settings;
    }
    
    /**
     * 发送成功响应
     */
    private function sendSuccess($data) {
        $response = [
            'success' => true,
            'data' => $data,
            'timestamp' => date('Y-m-d H:i:s')
        ];
        
        echo json_encode($response, JSON_UNESCAPED_UNICODE);
        exit();
    }
    
    /**
     * 发送错误响应
     */
    private function sendError($message, $code = 400) {
        http_response_code($code);
        
        $response = [
            'success' => false,
            'error' => $message,
            'timestamp' => date('Y-m-d H:i:s')
        ];
        
        echo json_encode($response, JSON_UNESCAPED_UNICODE);
        exit();
    }
}

// 执行API
$api = new RegistrationsAPI();
$api->handleRequest();
?>