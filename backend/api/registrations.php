<?php
/**
 * 报名查询API接口
 * 福建师范大学广东校友会一周年庆典晚会系统
 */

// 引入数据库配置
require_once 'database.php';

// 设置响应头
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

/**
 * 报名查询和修改API类
 * 福建师范大学广东校友会一周年庆典晚会系统
 * 支持查询和修改功能的统一接口
 */
class RegistrationQueryAPI {
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
            $action = $_GET['action'] ?? $_POST['action'] ?? 'list';
            
            switch ($method) {
                case 'GET':
                    $this->handleGetRequest($action);
                    break;
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
            error_log('报名API错误: ' . $e->getMessage());
            $this->sendError('服务器内部错误', 500);
        }
    }
    
    /**
     * 处理GET请求（查询操作）
     */
    private function handleGetRequest($action) {
        switch ($action) {
            case 'list':
                $this->getRegistrationList();
                break;
            case 'detail':
                $this->getRegistrationDetail();
                break;
            case 'stats':
                $this->getRegistrationStats();
                break;
            case 'search':
                $this->searchRegistrations();
                break;
            case 'export':
                $this->exportRegistrations();
                break;
            default:
                $this->sendError('不支持的查询操作', 400);
                break;
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
     * 获取报名列表
     */
    private function getRegistrationList() {
        try {
            $page = max(1, intval($_GET['page'] ?? 1));
            $limit = max(1, min(100, intval($_GET['limit'] ?? 20)));
            $offset = ($page - 1) * $limit;
            
            // 构建查询条件
            $conditions = [];
            $queryParams = [];
            
            // 搜索条件
            if (!empty($_GET['search'])) {
                $conditions[] = "(name LIKE :search OR phone LIKE :search)";
                $queryParams['search'] = '%' . $_GET['search'] . '%';
            }
            

            
            // 付款方式筛选
            if (!empty($_GET['payment_method'])) {
                $conditions[] = "payment_method = :payment_method";
                $queryParams['payment_method'] = $_GET['payment_method'];
            }
            
            // 才艺表演筛选
            if (!empty($_GET['talent_show'])) {
                $conditions[] = "talent_show = :talent_show";
                $queryParams['talent_show'] = $_GET['talent_show'];
            }
            
            // 构建WHERE子句
            $whereClause = '';
            if (!empty($conditions)) {
                $whereClause = " WHERE " . implode(" AND ", $conditions);
            }
            
            // 获取总数
            $countSql = "SELECT COUNT(*) as total FROM registrations" . $whereClause;
            $totalResult = $this->db->fetchOne($countSql, $queryParams);
            $total = $totalResult['total'];
            
            // 获取列表数据 - 包含所有字段
            $sql = "SELECT id, name, phone, education_info, total_amount, family_count, 
                           talent_show, talent_description, material_sponsorship, remarks, 
                           payment_method, payment_screenshot, payment_screenshot_2, created_at,
                           seat_number, is_checked_in, checkin_time
                    FROM registrations" . $whereClause . " 
                    ORDER BY created_at DESC 
                    LIMIT :limit OFFSET :offset";
            
            $queryParams['limit'] = $limit;
            $queryParams['offset'] = $offset;
            
            $registrations = $this->db->fetchAll($sql, $queryParams);
            
            $this->sendSuccess([
                'list' => $registrations,
                'pagination' => [
                    'total' => $total,
                    'page' => $page,
                    'limit' => $limit,
                    'pages' => ceil($total / $limit)
                ]
            ]);
            
        } catch (Exception $e) {
            $this->sendError('获取报名列表失败: ' . $e->getMessage(), 500);
        }
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
        
        try {
            $sql = "SELECT * FROM registrations WHERE id = :id";
            $registration = $this->db->fetchOne($sql, ['id' => $id]);
            
            if (!$registration) {
                $this->sendError('报名信息不存在', 404);
                return;
            }
            
            $this->sendSuccess($registration);
            
        } catch (Exception $e) {
            $this->sendError('获取报名详情失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 获取报名统计
     */
    private function getRegistrationStats() {
        try {
            $sql = "SELECT 
                        COUNT(*) as total_registrations,
                        SUM(1 + family_count) as total_people
                    FROM registrations";
            
            $stats = $this->db->fetchOne($sql);
            
            $this->sendSuccess($stats);
            
        } catch (Exception $e) {
            $this->sendError('获取统计数据失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 搜索报名记录
     */
    private function searchRegistrations() {
        try {
            $keyword = $_GET['keyword'] ?? '';
            if (empty($keyword)) {
                $this->sendError('请提供搜索关键词', 400);
                return;
            }
            
            $searchKeyword = '%' . $keyword . '%';
            $sql = "SELECT id, name, phone, education_info, total_amount, family_count, 
                           talent_show, talent_description, material_sponsorship, remarks, 
                           payment_method, created_at, seat_number, is_checked_in, checkin_time
                    FROM registrations 
                    WHERE name LIKE :keyword1 
                       OR phone LIKE :keyword2 
                       OR education_info LIKE :keyword3
                       OR talent_description LIKE :keyword4
                       OR remarks LIKE :keyword5
                    ORDER BY created_at DESC";
            
            $results = $this->db->fetchAll($sql, [
                'keyword1' => $searchKeyword,
                'keyword2' => $searchKeyword,
                'keyword3' => $searchKeyword,
                'keyword4' => $searchKeyword,
                'keyword5' => $searchKeyword
            ]);
            
            $this->sendSuccess([
                'keyword' => $keyword,
                'count' => count($results),
                'list' => $results
            ]);
            
        } catch (Exception $e) {
            $this->sendError('搜索失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 导出报名数据
     */
    private function exportRegistrations() {
        try {
            $format = $_GET['format'] ?? 'json';
            
            $sql = "SELECT id, name, phone, education_info, total_amount, family_count, 
                           talent_show, talent_description, material_sponsorship, remarks, 
                           payment_method, created_at, seat_number, is_checked_in, checkin_time
                    FROM registrations 
                    ORDER BY created_at DESC";
            
            $registrations = $this->db->fetchAll($sql);
            
            if ($format === 'csv') {
                $this->exportAsCSV($registrations);
            } else {
                $this->sendSuccess([
                    'format' => $format,
                    'count' => count($registrations),
                    'data' => $registrations
                ]);
            }
            
        } catch (Exception $e) {
            $this->sendError('导出失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 导出为CSV格式
     */
    private function exportAsCSV($data) {
        header('Content-Type: text/csv; charset=utf-8');
        header('Content-Disposition: attachment; filename="registrations_' . date('Y-m-d') . '.csv"');
        
        $output = fopen('php://output', 'w');
        
        // 写入BOM以支持中文
        fwrite($output, "\xEF\xBB\xBF");
        
        // 写入表头
        $headers = ['ID', '姓名', '手机号', '年级/学院', '缴费金额', '家属人数', 
                   '才艺表演', '才艺描述', '物资赞助', '备注', '付款方式', '报名时间',
                   '座位号', '签到状态', '签到时间'];
        fputcsv($output, $headers);
        
        // 写入数据
        foreach ($data as $row) {
            fputcsv($output, [
                $row['id'],
                $row['name'],
                $row['phone'],
                $row['education_info'] ?? '未填写',
                $row['total_amount'] ?? '0.00',
                $row['family_count'],
                $row['talent_show'],
                $row['talent_description'],
                $row['material_sponsorship'],
                $row['remarks'],
                $row['payment_method'],
                $row['created_at'],
                $row['seat_number'] ?? '未分配',
                ($row['is_checked_in'] == 1) ? '已签到' : '未签到',
                $row['checkin_time'] ?? '未签到'
            ]);
        }
        
        fclose($output);
        exit();
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
    
    // ==================== 修改功能方法 ====================
    
    /**
     * 更新单个报名记录
     */
    private function updateRegistration() {
        $input = $this->getInputData();
        $id = $input['id'] ?? $_GET['id'] ?? null;
        
        if (!$id) {
            $this->sendError('缺少报名ID', 400);
            return;
        }
        
        try {
            // 首先检查记录是否存在
            $checkSql = "SELECT id FROM registrations WHERE id = :id";
            $existing = $this->db->fetchOne($checkSql, ['id' => $id]);
            
            if (!$existing) {
                $this->sendError('报名记录不存在', 404);
                return;
            }
            
            // 构建更新字段
            $updateFields = [];
            $updateParams = ['id' => $id];
            
            // 允许更新的字段列表（包含缴费金额字段）
            $allowedFields = [
                'name', 'phone', 'education_info', 'family_count', 'total_amount',
                'talent_show', 'talent_description', 'material_sponsorship',
                'remarks', 'payment_method', 'seat_number', 'is_checked_in', 'checkin_time'
            ];
            
            foreach ($allowedFields as $field) {
                if (isset($input[$field])) {
                    $updateFields[] = "$field = :$field";
                    $updateParams[$field] = $input[$field];
                }
            }
            
            if (empty($updateFields)) {
                $this->sendError('没有提供要更新的字段', 400);
                return;
            }
            
            // 添加更新时间
            $updateFields[] = "updated_at = NOW()";
            
            // 执行更新
            $sql = "UPDATE registrations SET " . implode(', ', $updateFields) . " WHERE id = :id";
            $result = $this->db->execute($sql, $updateParams);
            
            if ($result) {
                // 获取更新后的记录
                $updatedRecord = $this->db->fetchOne("SELECT * FROM registrations WHERE id = :id", ['id' => $id]);
                
                $this->sendSuccess([
                    'message' => '报名信息更新成功',
                    'id' => $id,
                    'updated_fields' => array_keys($input),
                    'data' => $updatedRecord
                ]);
            } else {
                $this->sendError('更新失败', 500);
            }
            
        } catch (Exception $e) {
            $this->sendError('更新报名信息失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 批量更新报名记录
     */
    private function batchUpdateRegistrations() {
        $input = $this->getInputData();
        $ids = $input['ids'] ?? [];
        $updateData = $input['update_data'] ?? [];
        
        if (empty($ids) || !is_array($ids)) {
            $this->sendError('缺少要更新的ID列表', 400);
            return;
        }
        
        if (empty($updateData)) {
            $this->sendError('缺少更新数据', 400);
            return;
        }
        
        try {
            $this->db->beginTransaction();
            
            $successCount = 0;
            $failedIds = [];
            
            foreach ($ids as $id) {
                try {
                    // 构建更新字段
                    $updateFields = [];
                    $updateParams = ['id' => $id];
                    
                    $allowedFields = [
                        'name', 'phone', 'education_info', 'family_count', 'total_amount',
                        'talent_show', 'talent_description', 'material_sponsorship',
                        'remarks', 'payment_method', 'seat_number', 'is_checked_in', 'checkin_time'
                    ];
                    
                    foreach ($allowedFields as $field) {
                        if (isset($updateData[$field])) {
                            $updateFields[] = "$field = :$field";
                            $updateParams[$field] = $updateData[$field];
                        }
                    }
                    
                    if (!empty($updateFields)) {
                        $updateFields[] = "updated_at = NOW()";
                        $sql = "UPDATE registrations SET " . implode(', ', $updateFields) . " WHERE id = :id";
                        
                        if ($this->db->execute($sql, $updateParams)) {
                            $successCount++;
                        } else {
                            $failedIds[] = $id;
                        }
                    }
                    
                } catch (Exception $e) {
                    $failedIds[] = $id;
                    error_log("批量更新失败 ID $id: " . $e->getMessage());
                }
            }
            
            $this->db->commit();
            
            $this->sendSuccess([
                'message' => '批量更新完成',
                'total' => count($ids),
                'success_count' => $successCount,
                'failed_count' => count($failedIds),
                'failed_ids' => $failedIds
            ]);
            
        } catch (Exception $e) {
            $this->db->rollback();
            $this->sendError('批量更新失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 更新报名状态
     */
    private function updateRegistrationStatus() {
        $input = $this->getInputData();
        $id = $input['id'] ?? $_GET['id'] ?? null;
        $status = $input['status'] ?? null;
        
        if (!$id || !$status) {
            $this->sendError('缺少ID或状态', 400);
            return;
        }
        
        try {
            $sql = "UPDATE registrations SET status = :status, updated_at = NOW() WHERE id = :id";
            $result = $this->db->execute($sql, ['id' => $id, 'status' => $status]);
            
            if ($result) {
                $this->sendSuccess([
                    'message' => '状态更新成功',
                    'id' => $id,
                    'status' => $status
                ]);
            } else {
                $this->sendError('状态更新失败', 500);
            }
            
        } catch (Exception $e) {
            $this->sendError('更新状态失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 更新单个字段
     */
    private function updateSingleField() {
        $input = $this->getInputData();
        $id = $input['id'] ?? $_GET['id'] ?? null;
        $field = $input['field'] ?? null;
        $value = $input['value'] ?? null;
        
        if (!$id || !$field) {
            $this->sendError('缺少ID或字段名', 400);
            return;
        }
        
        // 验证字段名（包含缴费金额字段）
        $allowedFields = [
            'name', 'phone', 'education_info', 'family_count', 'total_amount',
            'talent_show', 'talent_description', 'material_sponsorship',
            'remarks', 'payment_method', 'seat_number', 'is_checked_in', 'checkin_time'
        ];
        
        if (!in_array($field, $allowedFields)) {
            $this->sendError('不允许更新的字段: ' . $field, 400);
            return;
        }
        
        try {
            $sql = "UPDATE registrations SET $field = :value, updated_at = NOW() WHERE id = :id";
            $result = $this->db->execute($sql, ['id' => $id, 'value' => $value]);
            
            if ($result) {
                $this->sendSuccess([
                    'message' => '字段更新成功',
                    'id' => $id,
                    'field' => $field,
                    'value' => $value
                ]);
            } else {
                $this->sendError('字段更新失败', 500);
            }
            
        } catch (Exception $e) {
            $this->sendError('更新字段失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 删除单个报名记录
     */
    private function deleteRegistration() {
        $input = $this->getInputData();
        $id = $input['id'] ?? $_GET['id'] ?? null;
        
        if (!$id) {
            $this->sendError('缺少报名ID', 400);
            return;
        }
        
        try {
            // 首先获取记录信息（用于返回）
            $record = $this->db->fetchOne("SELECT * FROM registrations WHERE id = :id", ['id' => $id]);
            
            if (!$record) {
                $this->sendError('报名记录不存在', 404);
                return;
            }
            
            // 删除付款凭证文件（如果存在）
            if (!empty($record['payment_screenshot'])) {
                $this->deletePaymentScreenshot($record['payment_screenshot']);
            }
            
            // 删除记录
            $sql = "DELETE FROM registrations WHERE id = :id";
            $result = $this->db->execute($sql, ['id' => $id]);
            
            if ($result) {
                $this->sendSuccess([
                    'message' => '报名记录删除成功',
                    'id' => $id,
                    'deleted_record' => $record
                ]);
            } else {
                $this->sendError('删除失败', 500);
            }
            
        } catch (Exception $e) {
            $this->sendError('删除报名记录失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 批量删除报名记录
     */
    private function batchDeleteRegistrations() {
        $input = $this->getInputData();
        $ids = $input['ids'] ?? [];
        
        if (empty($ids) || !is_array($ids)) {
            $this->sendError('缺少要删除的ID列表', 400);
            return;
        }
        
        try {
            $this->db->beginTransaction();
            
            $successCount = 0;
            $failedIds = [];
            $deletedRecords = [];
            
            foreach ($ids as $id) {
                try {
                    // 获取记录信息
                    $record = $this->db->fetchOne("SELECT * FROM registrations WHERE id = :id", ['id' => $id]);
                    
                    if ($record) {
                        // 删除付款凭证文件
                        if (!empty($record['payment_screenshot'])) {
                            $this->deletePaymentScreenshot($record['payment_screenshot']);
                        }
                        
                        // 删除记录
                        $sql = "DELETE FROM registrations WHERE id = :id";
                        if ($this->db->execute($sql, ['id' => $id])) {
                            $successCount++;
                            $deletedRecords[] = $record;
                        } else {
                            $failedIds[] = $id;
                        }
                    } else {
                        $failedIds[] = $id;
                    }
                    
                } catch (Exception $e) {
                    $failedIds[] = $id;
                    error_log("批量删除失败 ID $id: " . $e->getMessage());
                }
            }
            
            $this->db->commit();
            
            $this->sendSuccess([
                'message' => '批量删除完成',
                'total' => count($ids),
                'success_count' => $successCount,
                'failed_count' => count($failedIds),
                'failed_ids' => $failedIds,
                'deleted_records' => $deletedRecords
            ]);
            
        } catch (Exception $e) {
            $this->db->rollback();
            $this->sendError('批量删除失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 根据条件删除记录
     */
    private function deleteByCondition() {
        $input = $this->getInputData();
        
        // 构建删除条件
        $conditions = [];
        $queryParams = [];
        
        // 支持的删除条件
        
        if (!empty($input['payment_method'])) {
            $conditions[] = "payment_method = :payment_method";
            $queryParams['payment_method'] = $input['payment_method'];
        }
        
        if (!empty($input['talent_show'])) {
            $conditions[] = "talent_show = :talent_show";
            $queryParams['talent_show'] = $input['talent_show'];
        }
        
        if (!empty($input['date_range'])) {
            if (!empty($input['date_range']['start'])) {
                $conditions[] = "created_at >= :start_date";
                $queryParams['start_date'] = $input['date_range']['start'];
            }
            if (!empty($input['date_range']['end'])) {
                $conditions[] = "created_at <= :end_date";
                $queryParams['end_date'] = $input['date_range']['end'];
            }
        }
        
        if (empty($conditions)) {
            $this->sendError('必须提供删除条件', 400);
            return;
        }
        
        try {
            $whereClause = " WHERE " . implode(" AND ", $conditions);
            
            // 首先获取要删除的记录
            $selectSql = "SELECT * FROM registrations" . $whereClause;
            $recordsToDelete = $this->db->fetchAll($selectSql, $queryParams);
            
            if (empty($recordsToDelete)) {
                $this->sendSuccess([
                    'message' => '没有找到符合条件的记录',
                    'deleted_count' => 0
                ]);
                return;
            }
            
            // 删除付款凭证文件
            foreach ($recordsToDelete as $record) {
                if (!empty($record['payment_screenshot'])) {
                    $this->deletePaymentScreenshot($record['payment_screenshot']);
                }
            }
            
            // 执行删除
            $deleteSql = "DELETE FROM registrations" . $whereClause;
            $result = $this->db->execute($deleteSql, $queryParams);
            
            if ($result) {
                $this->sendSuccess([
                    'message' => '条件删除完成',
                    'deleted_count' => count($recordsToDelete),
                    'conditions' => $input,
                    'deleted_records' => $recordsToDelete
                ]);
            } else {
                $this->sendError('条件删除失败', 500);
            }
            
        } catch (Exception $e) {
            $this->sendError('条件删除失败: ' . $e->getMessage(), 500);
        }
    }
    
    /**
     * 删除付款凭证文件
     */
    private function deletePaymentScreenshot($screenshotPath) {
        try {
            if ($screenshotPath) {
                $frontendDir = dirname(__DIR__, 2) . '/frontend/';
                $fullPath = $frontendDir . $screenshotPath;
                
                if (file_exists($fullPath)) {
                    unlink($fullPath);
                }
            }
        } catch (Exception $e) {
            error_log('删除付款凭证文件失败: ' . $e->getMessage());
        }
    }
    
    /**
     * 获取输入数据
     */
    private function getInputData() {
        $contentType = $_SERVER['CONTENT_TYPE'] ?? '';
        
        if (strpos($contentType, 'application/json') !== false) {
            $input = json_decode(file_get_contents('php://input'), true);
            return $input ?: [];
        } else {
            return $_POST;
        }
    }
}

// 执行API
$api = new RegistrationQueryAPI();
$api->handleRequest();
?>