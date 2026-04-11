<?php
require_once 'database.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');
header('Access-Control-Allow-Headers: Content-Type');

try {
    // 获取页面参数
    $page = $_GET['page'] ?? '';
    
    if (empty($page)) {
        echo json_encode(['success' => false, 'message' => '页面参数不能为空']);
        exit;
    }
    
    // 页面名称到数据库字段名的映射（手机端页面）
    $pageMapping = [
        'registration' => 'mobile_registration_status',
        'agenda' => 'mobile_agenda_status',
        'photo-live' => 'mobile_live_photos_status',
        'video-live' => 'mobile_live_status',
        'transport' => 'mobile_transport_status',
        'live' => 'mobile_live_status',
        'live_photos' => 'mobile_live_photos_status',
        'seating' => 'mobile_seating_status'
    ];
    
    // 检查是否为支持的手机端页面
    if (!isset($pageMapping[$page])) {
        echo json_encode(['success' => false, 'message' => '不支持的页面']);
        exit;
    }
    
    $settingKey = $pageMapping[$page];
    
    // 尝试连接数据库
    try {
        $db = Database::getInstance();
        
        // 查询页面状态 - 从systems表的setting_value字段获取
        $query = "SELECT setting_value FROM systems WHERE setting_key = ?";
        $result = $db->fetchOne($query, [$settingKey]);
        
        if ($result && isset($result['setting_value'])) {
            $settingValue = $result['setting_value'];
            
            // 状态转换：open = 正常显示，under_construction = 重定向到建设中页面
            $status = ($settingValue === 'open') ? 'open' : 'under_construction';
            
            echo json_encode([
                'success' => true,
                'page' => $page,
                'setting_key' => $settingKey,
                'status' => $status
            ]);
        } else {
            // 如果没有找到记录，默认为维护状态
            echo json_encode([
                'success' => true,
                'page' => $page,
                'setting_key' => $settingKey,
                'status' => 'under_construction'
            ]);
        }
    } catch (Exception $dbError) {
        // 数据库连接失败时，返回默认状态
        echo json_encode([
            'success' => true,
            'page' => $page,
            'setting_key' => $settingKey,
            'status' => 'under_construction',
            'note' => 'Database connection failed, using default status'
        ]);
    }
    
} catch (Exception $e) {
    echo json_encode([
        'success' => false,
        'message' => '服务器错误: ' . $e->getMessage()
    ]);
}
?>