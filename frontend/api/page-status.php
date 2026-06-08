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
    
    // 页面名称到数据库字段名的映射（桌面端和移动端页面）
    $pageMapping = [
        // 桌面端页面
        'registration' => 'registration_page_status',
        'agenda' => 'agenda_page_status',
        'photo-live' => 'photo_live_page_status',
        'video-live' => 'video_live_page_status',
        'transport' => 'transport_page_status',
        'seating' => 'seating_page_status',
        // 移动端页面（映射到对应的桌面端状态）
        'registrations' => 'registration_page_status',  // 移动端报名页面
        'live_photos' => 'photo_live_page_status',      // 移动端图片直播
        'live' => 'video_live_page_status'              // 移动端视频直播
    ];
    
    // 检查是否为支持的页面
    if (!isset($pageMapping[$page])) {
        echo json_encode(['success' => false, 'message' => '不支持的页面: ' . $page]);
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
            
            // 状态转换：active = 正常显示，maintenance = 重定向到建设中页面
            $status = ($settingValue === 'active') ? 'active' : 'maintenance';
            
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
                'status' => 'maintenance'
            ]);
        }
    } catch (Exception $dbError) {
        // 数据库连接失败时，返回默认状态
        echo json_encode([
            'success' => true,
            'page' => $page,
            'setting_key' => $settingKey,
            'status' => 'maintenance',
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