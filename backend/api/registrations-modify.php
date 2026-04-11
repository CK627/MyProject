<?php
/**
 * 报名修改API接口
 * 福建师范大学广东校友会一周年庆典晚会系统
 * 专门处理报名数据的修改操作
 */

// 引入数据库配置
require_once 'database.php';

// 设置响应头
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

/**
 * 报名修改API类
 */
class RegistrationModifyAPI {
    private $db;
    
    public function __construct() {
        $this->db = Database::getInstance();
    }
    
    /**
     * 处理API请求
     */
    public function handleRequest() {
        try {
            $method = $_SERVER['REQUEST_METHOD'];
            $action = $_GET['action'] ?? $_POST['action'] ?? $this->getInputData()['action'] ?? '';
            
            switch ($method) {
                case 'POST':
                    $this->handlePostRequest($action);
                    break;
                case 'PUT':
                    $this->handlePutRequest($action);
                    break;
                case 'DELETE':
                    $this->handleDeleteRequest($action);
                    break;
                default:
                    $this->sendError('不支持的请求方法', 405);
                    break;
            }
        } catch (Exception $e) {
            error_log('报名修改API错误: ' . $e->getMessage());
            $this->sendError('服务器内部错误: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 处理POST请求（创建和更新操作）
     */
    private function handlePostRequest($action) {
        switch ($action) {
            case 'update':
                $this->updateRegistration();
                break;
            case 'batch_update':
                $this->batchUpdateRegistrations();
                break;
            case 'update_status':
                $this->updateRegistrationStatus();
                break;
            default:
                $this->sendError('不支持的POST操作', 400);
                break;
        }
    }
    
    /**
     * 处理PUT请求（更新操作）
     */
    private function handlePutRequest($action) {
        switch ($action) {
            case 'update':
                $this->updateRegistration();
                break;
            case 'update_field':
                $this->updateSingleField();
                break;
            case 'remove_screenshot':
                $this->removeScreenshot();
                break;
            default:
                $this->sendError('不支持的PUT操作', 400);
                break;
        }
    }
    
    /**
     * 处理DELETE请求（删除操作）
     */
    private function handleDeleteRequest($action) {
        switch ($action) {
            case 'delete':
                $this->deleteRegistration();
                break;
            case 'batch_delete':
                $this->batchDeleteRegistrations();
                break;
            case 'delete_by_condition':
                $this->deleteByCondition();
                break;
            default:
                $this->sendError('不支持的DELETE操作', 400);
                break;
        }
    }
    
    /**
     * 更新单个报名记录
     */
    private function updateRegistration() {
        $data = $this->getInputData();
        
        if (empty($data['id'])) {
            $this->sendError('缺少报名ID', 400);
            return;
        }
        
        // 允许更新的字段白名单
        $allowedFields = [
            'name', 'phone', 'education_info', 'family_count', 
            'is_2025_student', 'payment_amount',
            'talent_show', 'talent_description', 'material_sponsorship', 
            'remarks', 'payment_method'
        ];
        
        $updateFields = [];
        $updateParams = ['id' => $data['id']];
        
        foreach ($allowedFields as $field) {
            if (isset($data[$field])) {
                // 字段映射：payment_amount -> total_amount
                $dbField = ($field === 'payment_amount') ? 'total_amount' : $field;
                $updateFields[] = "$dbField = :$field";
                $updateParams[$field] = $data[$field];
            }
        }
        
        try {
            $this->db->beginTransaction();
            
            // 处理付款凭证上传
            $uploadedFiles = [];
            
            // 处理付款凭证1
            if (isset($_FILES['payment_screenshot']) && $_FILES['payment_screenshot']['error'] === UPLOAD_ERR_OK) {
                $uploadResult = $this->handleFileUpload($_FILES['payment_screenshot'], 'payment_screenshot', $data['id']);
                if ($uploadResult['success']) {
                    $updateFields[] = "payment_screenshot = :payment_screenshot";
                    $updateParams['payment_screenshot'] = $uploadResult['file_path'];
                    $uploadedFiles[] = $uploadResult['file_path'];
                } else {
                    $this->db->rollback();
                    $this->sendError('付款凭证1上传失败: ' . $uploadResult['error'], 400);
                    return;
                }
            }
            
            // 处理付款凭证2
            if (isset($_FILES['payment_screenshot_2']) && $_FILES['payment_screenshot_2']['error'] === UPLOAD_ERR_OK) {
                $uploadResult = $this->handleFileUpload($_FILES['payment_screenshot_2'], 'payment_screenshot_2', $data['id']);
                if ($uploadResult['success']) {
                    $updateFields[] = "payment_screenshot_2 = :payment_screenshot_2";
                    $updateParams['payment_screenshot_2'] = $uploadResult['file_path'];
                    $uploadedFiles[] = $uploadResult['file_path'];
                } else {
                    $this->db->rollback();
                    // 清理已上传的文件
                    foreach ($uploadedFiles as $filePath) {
                        $this->deleteUploadedFile($filePath);
                    }
                    $this->sendError('付款凭证2上传失败: ' . $uploadResult['error'], 400);
                    return;
                }
            }
            
            if (empty($updateFields)) {
                $this->sendError('没有可更新的字段', 400);
                return;
            }
            
            $sql = "UPDATE registrations SET " . implode(', ', $updateFields) . " WHERE id = :id";
            $result = $this->db->execute($sql, $updateParams);
            
            if ($result) {
                $this->db->commit();
                $this->sendSuccess(['message' => '更新成功', 'affected_rows' => 1]);
            } else {
                $this->db->rollback();
                // 清理已上传的文件
                foreach ($uploadedFiles as $filePath) {
                    $this->deleteUploadedFile($filePath);
                }
                $this->sendError('更新失败', 500);
            }
        } catch (Exception $e) {
            $this->db->rollback();
            // 清理已上传的文件
            foreach ($uploadedFiles as $filePath) {
                $this->deleteUploadedFile($filePath);
            }
            $this->sendError('更新失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 批量更新报名记录
     */
    private function batchUpdateRegistrations() {
        $data = $this->getInputData();
        
        if (empty($data['ids']) || !is_array($data['ids'])) {
            $this->sendError('缺少报名ID列表', 400);
            return;
        }
        
        if (empty($data['updates'])) {
            $this->sendError('缺少更新数据', 400);
            return;
        }
        
        // 允许更新的字段白名单
        $allowedFields = [
            'name', 'phone', 'education_info', 'family_count', 
            'is_2025_student', 'payment_amount',
            'talent_show', 'talent_description', 'material_sponsorship', 
            'remarks', 'payment_method'
        ];
        
        $updateFields = [];
        $updateParams = [];
        
        foreach ($data['updates'] as $field => $value) {
            if (in_array($field, $allowedFields)) {
                // 字段映射：payment_amount -> total_amount
                $dbField = ($field === 'payment_amount') ? 'total_amount' : $field;
                $updateFields[] = "$dbField = :$field";
                $updateParams[$field] = $value;
            }
        }
        
        if (empty($updateFields)) {
            $this->sendError('没有可更新的字段', 400);
            return;
        }
        
        try {
            $this->db->beginTransaction();
            
            $placeholders = implode(',', array_fill(0, count($data['ids']), '?'));
            $sql = "UPDATE registrations SET " . implode(', ', $updateFields) . " WHERE id IN ($placeholders)";
            
            $params = array_merge(array_values($updateParams), $data['ids']);
            $result = $this->db->execute($sql, $params);
            
            if ($result) {
                $this->db->commit();
                $this->sendSuccess(['message' => '批量更新成功', 'affected_rows' => count($data['ids'])]);
            } else {
                $this->db->rollback();
                $this->sendError('批量更新失败', 500);
            }
        } catch (Exception $e) {
            $this->db->rollback();
            $this->sendError('批量更新失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 更新报名状态
     */
    private function updateRegistrationStatus() {
        $data = $this->getInputData();
        
        if (empty($data['id'])) {
            $this->sendError('缺少报名ID', 400);
            return;
        }
        
        if (!isset($data['status'])) {
            $this->sendError('缺少状态值', 400);
            return;
        }
        
        try {
            $this->db->beginTransaction();
            
            $sql = "UPDATE registrations SET status = :status WHERE id = :id";
            $result = $this->db->execute($sql, [
                'status' => $data['status'],
                'id' => $data['id']
            ]);
            
            if ($result) {
                $this->db->commit();
                $this->sendSuccess(['message' => '状态更新成功']);
            } else {
                $this->db->rollback();
                $this->sendError('状态更新失败', 500);
            }
        } catch (Exception $e) {
            $this->db->rollback();
            $this->sendError('状态更新失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 更新单个字段
     */
    private function updateSingleField() {
        $data = $this->getInputData();
        
        if (empty($data['id'])) {
            $this->sendError('缺少报名ID', 400);
            return;
        }
        
        if (empty($data['field'])) {
            $this->sendError('缺少字段名', 400);
            return;
        }
        
        if (!isset($data['value'])) {
            $this->sendError('缺少字段值', 400);
            return;
        }
        
        // 允许更新的字段白名单
        $allowedFields = [
            'name', 'phone', 'education_info', 'family_count', 
            'is_2025_student', 'payment_amount',
            'talent_show', 'talent_description', 'material_sponsorship', 
            'remarks', 'payment_method'
        ];
        
        if (!in_array($data['field'], $allowedFields)) {
            $this->sendError('不允许更新该字段', 400);
            return;
        }
        
        try {
            $this->db->beginTransaction();
            
            $sql = "UPDATE registrations SET {$data['field']} = :value WHERE id = :id";
            $result = $this->db->execute($sql, [
                'value' => $data['value'],
                'id' => $data['id']
            ]);
            
            if ($result) {
                $this->db->commit();
                $this->sendSuccess(['message' => '字段更新成功']);
            } else {
                $this->db->rollback();
                $this->sendError('字段更新失败', 500);
            }
        } catch (Exception $e) {
            $this->db->rollback();
            $this->sendError('字段更新失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 删除单个报名记录
     */
    private function deleteRegistration() {
        $data = $this->getInputData();
        $id = $data['id'] ?? $_GET['id'] ?? null;
        
        if (empty($id)) {
            $this->sendError('缺少报名ID', 400);
            return;
        }
        
        try {
            $this->db->beginTransaction();
            
            // 先获取付款凭证路径，用于删除文件
            $registration = $this->db->fetchOne("SELECT payment_screenshot, payment_screenshot_2 FROM registrations WHERE id = :id", ['id' => $id]);
            
            // 删除记录
            $sql = "DELETE FROM registrations WHERE id = :id";
            $result = $this->db->execute($sql, ['id' => $id]);
            
            if ($result) {
                // 删除付款凭证文件
                if (!empty($registration['payment_screenshot'])) {
                    $this->deletePaymentScreenshot($registration['payment_screenshot']);
                }
                if (!empty($registration['payment_screenshot_2'])) {
                    $this->deletePaymentScreenshot($registration['payment_screenshot_2']);
                }
                
                $this->db->commit();
                $this->sendSuccess(['message' => '删除成功']);
            } else {
                $this->db->rollback();
                $this->sendError('删除失败', 500);
            }
        } catch (Exception $e) {
            $this->db->rollback();
            $this->sendError('删除失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 批量删除报名记录
     */
    private function batchDeleteRegistrations() {
        $data = $this->getInputData();
        
        if (empty($data['ids']) || !is_array($data['ids'])) {
            $this->sendError('缺少报名ID列表', 400);
            return;
        }
        
        try {
            $this->db->beginTransaction();
            
            // 先获取所有付款凭证路径
            $placeholders = implode(',', array_fill(0, count($data['ids']), '?'));
            $screenshots = $this->db->fetchAll("SELECT payment_screenshot, payment_screenshot_2 FROM registrations WHERE id IN ($placeholders)", $data['ids']);
            
            // 删除记录
            $sql = "DELETE FROM registrations WHERE id IN ($placeholders)";
            $result = $this->db->execute($sql, $data['ids']);
            
            if ($result) {
                // 删除付款凭证文件
                foreach ($screenshots as $screenshot) {
                    if (!empty($screenshot['payment_screenshot'])) {
                        $this->deletePaymentScreenshot($screenshot['payment_screenshot']);
                    }
                    if (!empty($screenshot['payment_screenshot_2'])) {
                        $this->deletePaymentScreenshot($screenshot['payment_screenshot_2']);
                    }
                }
                
                $this->db->commit();
                $this->sendSuccess(['message' => '批量删除成功', 'affected_rows' => count($data['ids'])]);
            } else {
                $this->db->rollback();
                $this->sendError('批量删除失败', 500);
            }
        } catch (Exception $e) {
            $this->db->rollback();
            $this->sendError('批量删除失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 根据条件删除报名记录
     */
    private function deleteByCondition() {
        $data = $this->getInputData();
        
        if (empty($data['conditions'])) {
            $this->sendError('缺少删除条件', 400);
            return;
        }
        
        // 允许的条件字段白名单
        $allowedFields = [
            'payment_method', 'talent_show', 'created_at'
        ];
        
        $conditions = [];
        $params = [];
        
        foreach ($data['conditions'] as $field => $value) {
            if (in_array($field, $allowedFields)) {
                $conditions[] = "$field = :$field";
                $params[$field] = $value;
            }
        }
        
        if (empty($conditions)) {
            $this->sendError('没有有效的删除条件', 400);
            return;
        }
        
        try {
            $this->db->beginTransaction();
            
            // 先获取要删除的记录的付款凭证
            $whereClause = implode(' AND ', $conditions);
            $screenshots = $this->db->fetchAll("SELECT payment_screenshot, payment_screenshot_2 FROM registrations WHERE $whereClause", $params);
            
            // 删除记录
            $sql = "DELETE FROM registrations WHERE $whereClause";
            $result = $this->db->execute($sql, $params);
            
            if ($result) {
                // 删除付款凭证文件
                foreach ($screenshots as $screenshot) {
                    if (!empty($screenshot['payment_screenshot'])) {
                        $this->deletePaymentScreenshot($screenshot['payment_screenshot']);
                    }
                    if (!empty($screenshot['payment_screenshot_2'])) {
                        $this->deletePaymentScreenshot($screenshot['payment_screenshot_2']);
                    }
                }
                
                $this->db->commit();
                $this->sendSuccess(['message' => '条件删除成功', 'affected_rows' => count($screenshots)]);
            } else {
                $this->db->rollback();
                $this->sendError('条件删除失败', 500);
            }
        } catch (Exception $e) {
            $this->db->rollback();
            $this->sendError('条件删除失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 删除付款凭证
     */
    private function removeScreenshot() {
        $data = $this->getInputData();
        
        if (empty($data['id'])) {
            $this->sendError('缺少报名ID', 400);
            return;
        }
        
        if (empty($data['field'])) {
            $this->sendError('缺少字段名', 400);
            return;
        }
        
        $id = $data['id'];
        $field = $data['field'];
        
        // 验证字段名
        if (!in_array($field, ['payment_screenshot', 'payment_screenshot_2'])) {
            $this->sendError('无效的字段名', 400);
            return;
        }
        
        try {
            $this->db->beginTransaction();
            
            // 获取当前的凭证路径
            $currentData = $this->db->fetchOne("SELECT $field FROM registrations WHERE id = :id", ['id' => $id]);
            
            if (!$currentData) {
                $this->db->rollback();
                $this->sendError('报名记录不存在', 404);
                return;
            }
            
            $currentScreenshot = $currentData[$field];
            
            // 更新数据库，将字段设为NULL
            $sql = "UPDATE registrations SET $field = NULL WHERE id = :id";
            $result = $this->db->execute($sql, ['id' => $id]);
            
            if ($result) {
                // 删除文件
                if (!empty($currentScreenshot)) {
                    $this->deletePaymentScreenshot($currentScreenshot);
                }
                
                $this->db->commit();
                $this->sendSuccess(['message' => '凭证删除成功']);
            } else {
                $this->db->rollback();
                $this->sendError('凭证删除失败', 500);
            }
        } catch (Exception $e) {
            $this->db->rollback();
            $this->sendError('凭证删除失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 删除付款凭证文件
     */
    private function deletePaymentScreenshot($screenshotPath) {
        if (empty($screenshotPath)) {
            return;
        }
        
        // 构建完整的文件路径
        $fullPath = "../../frontend/" . $screenshotPath;
        
        if (file_exists($fullPath)) {
            unlink($fullPath);
        }
    }
    
    /**
     * 处理文件上传
     */
    private function handleFileUpload($file, $fieldName, $registrationId = null) {
        // 检查文件是否上传成功
        if ($file['error'] !== UPLOAD_ERR_OK) {
            return ['success' => false, 'error' => '文件上传失败'];
        }
        
        // 检查文件类型
        $allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
        $fileType = $file['type'];
        
        if (!in_array($fileType, $allowedTypes)) {
            return ['success' => false, 'error' => '不支持的文件类型，请上传图片文件'];
        }
        
        // 检查文件大小（限制为5MB）
        $maxSize = 5 * 1024 * 1024; // 5MB
        if ($file['size'] > $maxSize) {
            return ['success' => false, 'error' => '文件大小不能超过5MB'];
        }
        
        // 生成文件名：姓名_电话（已移除缴费金额）
        $extension = pathinfo($file['name'], PATHINFO_EXTENSION);
        $fileName = '';
        
        // 如果有注册ID，获取用户信息生成文件名
        if ($registrationId) {
            try {
                $userInfo = $this->db->fetchOne(
                    "SELECT name, phone FROM registrations WHERE id = :id", 
                    ['id' => $registrationId]
                );
                
                if ($userInfo) {
                    $name = $userInfo['name'] ?? 'unknown';
                    $phone = $userInfo['phone'] ?? 'unknown';
                    
                    // 为凭证2添加后缀以区分
                    $suffix = ($fieldName === 'payment_screenshot_2') ? '_2' : '';
                    $fileName = $name . '_' . $phone . $suffix . '.' . $extension;
                } else {
                    // 如果获取用户信息失败，使用原来的命名方式
                    $fileName = uniqid($fieldName . '_') . '.' . $extension;
                }
            } catch (Exception $e) {
                // 如果查询失败，使用原来的命名方式
                $fileName = uniqid($fieldName . '_') . '.' . $extension;
            }
        } else {
            // 没有注册ID，使用原来的命名方式
            $fileName = uniqid($fieldName . '_') . '.' . $extension;
        }
        
        // 设置上传目录 - 改为与前端一致的目录
        $uploadDir = '../../frontend/pages/payment-records/';
        
        // 确保上传目录存在
        if (!is_dir($uploadDir)) {
            if (!mkdir($uploadDir, 0755, true)) {
                return ['success' => false, 'error' => '无法创建上传目录'];
            }
        }
        
        // 完整的文件路径
        $filePath = $uploadDir . $fileName;
        
        // 移动上传的文件
        if (move_uploaded_file($file['tmp_name'], $filePath)) {
            // 返回相对路径（用于数据库存储）
            $relativePath = 'pages/payment-records/' . $fileName;
            return ['success' => true, 'file_path' => $relativePath];
        } else {
            return ['success' => false, 'error' => '文件保存失败'];
        }
    }
    
    /**
     * 删除已上传的文件
     */
    private function deleteUploadedFile($filePath) {
        if (empty($filePath)) {
            return;
        }
        
        $fullPath = "../../frontend/" . $filePath;
        
        if (file_exists($fullPath)) {
            unlink($fullPath);
        }
    }
    
    /**
     * 获取输入数据
     */
    private function getInputData() {
        $input = file_get_contents('php://input');
        if (!empty($input)) {
            $data = json_decode($input, true);
            if (json_last_error() === JSON_ERROR_NONE) {
                return $data;
            }
        }
        return $_POST;
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
        exit();
    }
    
    /**
     * 发送错误响应
     */
    private function sendError($message, $code = 400) {
        http_response_code($code);
        echo json_encode([
            'success' => false,
            'error' => $message
        ], JSON_UNESCAPED_UNICODE);
        exit();
    }
}

// 创建API实例并处理请求
$api = new RegistrationModifyAPI();
$api->handleRequest();
?>