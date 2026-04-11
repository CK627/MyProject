<?php
// 引入数据库配置
require_once 'database.php';

// 设置响应头
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

try {
    $db = Database::getInstance();
    
    // 桌面端页面状态字段
    $desktopPages = [
        'registration_page_status',
        'agenda_page_status', 
        'photo_live_page_status',
        'video_live_page_status',
        'transport_page_status',
        'seating_page_status'
    ];
    
    // 手机端页面状态字段
    $mobilePages = [
        'mobile_registration_status',
        'mobile_agenda_status',
        'mobile_transport_status',
        'mobile_live_status',
        'mobile_live_photos_status',
        'mobile_seating_status'
    ];
    
    // 处理GET请求 - 获取页面状态
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $statuses = [];
        
        // 读取桌面端页面状态
        foreach ($desktopPages as $pageKey) {
            $sql = "SELECT setting_value FROM systems WHERE setting_key = :setting_key";
            $result = $db->fetchOne($sql, ['setting_key' => $pageKey]);
            
            if ($result) {
                $status = $result['setting_value']; // active=正常显示, maintenance=重定向到建设中页面
                // 将 active/maintenance 转换为 1/0 供前端使用
                $statuses[$pageKey] = ($status === 'active') ? 1 : 0;
            }
        }
        
        // 读取手机端页面状态
        foreach ($mobilePages as $pageKey) {
            $sql = "SELECT setting_value FROM systems WHERE setting_key = :setting_key";
            $result = $db->fetchOne($sql, ['setting_key' => $pageKey]);
            
            if ($result) {
                $status = $result['setting_value']; // open=开启, under_construction=建设中
                // 将 open/under_construction 转换为 1/0 供前端使用
                $statuses[$pageKey] = ($status === 'open') ? 1 : 0;
            } else {
                // 如果数据库中没有记录，默认为建设中状态
                $statuses[$pageKey] = 0;
            }
        }
        
        echo json_encode([
            'success' => true,
            'data' => $statuses
        ]);
        exit;
    }
    
    // 处理POST请求 - 状态更改功能
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $input = json_decode(file_get_contents('php://input'), true);
        $pageKey = $input['page_key'] ?? '';
        $newStatus = $input['status'] ?? '';
        
        // 合并所有有效的页面键
        $allPages = array_merge($desktopPages, $mobilePages);
        
        // 验证页面键是否有效
        if (!in_array($pageKey, $allPages)) {
            echo json_encode(['success' => false, 'message' => '无效的页面键']);
            exit;
        }
        
        // 根据页面类型验证状态值
        if (in_array($pageKey, $desktopPages)) {
            // 桌面端页面状态验证
            if (!in_array($newStatus, ['active', 'maintenance'])) {
                echo json_encode(['success' => false, 'message' => '桌面端页面状态值只能是 active 或 maintenance']);
                exit;
            }
        } else {
            // 手机端页面状态验证
            if (!in_array($newStatus, ['open', 'under_construction'])) {
                echo json_encode(['success' => false, 'message' => '手机端页面状态值只能是 open 或 under_construction']);
                exit;
            }
        }
        
        // 检查记录是否存在
        $checkSql = "SELECT setting_key FROM systems WHERE setting_key = :page_key";
        $existingRecord = $db->fetchOne($checkSql, ['page_key' => $pageKey]);
        
        if ($existingRecord) {
            // 更新现有记录
            $updateSql = "UPDATE systems SET setting_value = :status WHERE setting_key = :page_key";
            $updateResult = $db->query($updateSql, [
                'status' => $newStatus,
                'page_key' => $pageKey
            ]);
        } else {
            // 插入新记录
            $insertSql = "INSERT INTO systems (setting_key, setting_value) VALUES (:page_key, :status)";
            $updateResult = $db->query($insertSql, [
                'page_key' => $pageKey,
                'status' => $newStatus
            ]);
        }
        
        if ($updateResult) {
            echo json_encode([
                'success' => true, 
                'message' => '页面状态更新成功',
                'page_key' => $pageKey,
                'new_status' => $newStatus
            ]);
        } else {
            echo json_encode(['success' => false, 'message' => '状态更新失败']);
        }
        exit;
    }
    
} catch (Exception $e) {
    echo json_encode(['success' => false, 'message' => '数据库连接错误: ' . $e->getMessage()]);
    error_log("数据库连接错误: " . $e->getMessage());
}
?>