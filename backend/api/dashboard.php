<?php
/**
 * 仪表盘API接口
 * 福建师范大学广东校友会一周年庆典晚会系统
 */

// 设置响应头
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// 引入数据库配置
require_once 'database.php';

try {
    // 获取数据库实例
    $db = Database::getInstance();
    
    // 只允许GET请求
    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        throw new Exception('只允许GET请求');
    }
    
    // 获取统计数据
    $stats = getDashboardStats($db);
    
    // 返回成功响应
    echo json_encode([
        'success' => true,
        'data' => $stats,
        'timestamp' => date('Y-m-d H:i:s')
    ], JSON_UNESCAPED_UNICODE);
    
} catch (Exception $e) {
    // 返回错误响应
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage(),
        'timestamp' => date('Y-m-d H:i:s')
    ], JSON_UNESCAPED_UNICODE);
}

/**
 * 获取仪表盘统计数据
 */
function getDashboardStats($db) {
    $stats = [];
    
    // 1. 总报名人数
    $sql = "SELECT COUNT(*) as total FROM registrations";
    $result = $db->fetchOne($sql);
    $stats['total_registrations'] = (int)$result['total'];
    
    // 已移除缴费金额相关统计功能
    
    // 4. 总节目数量（统计才艺表演的数量）
    $sql = "SELECT COUNT(*) as total FROM registrations WHERE talent_show != '不才艺表演' AND talent_show IS NOT NULL AND talent_show != ''";
    $result = $db->fetchOne($sql);
    $stats['total_programs'] = (int)$result['total'];
    
    // 5. 额外统计信息
    // 今日新增报名数
    $sql = "SELECT COUNT(*) as total FROM registrations WHERE DATE(created_at) = CURDATE()";
    $result = $db->fetchOne($sql);
    $stats['today_registrations'] = (int)$result['total'];
    
    // 本周新增报名数
    $sql = "SELECT COUNT(*) as total FROM registrations WHERE YEARWEEK(created_at) = YEARWEEK(NOW())";
    $result = $db->fetchOne($sql);
    $stats['week_registrations'] = (int)$result['total'];
    
    // 本月新增报名数
    $sql = "SELECT COUNT(*) as total FROM registrations WHERE YEAR(created_at) = YEAR(NOW()) AND MONTH(created_at) = MONTH(NOW())";
    $result = $db->fetchOne($sql);
    $stats['month_registrations'] = (int)$result['total'];
    
    // 有支付凭证的报名数
    $sql = "SELECT COUNT(*) as total FROM registrations WHERE payment_screenshot IS NOT NULL AND payment_screenshot != ''";
    $result = $db->fetchOne($sql);
    $stats['paid_registrations'] = (int)$result['total'];
    
    // 已移除平均报名费用统计功能
    
    // 6. 签到统计信息
    // 已签到人数
    $sql = "SELECT COUNT(*) as total FROM registrations WHERE is_checked_in = 1";
    $result = $db->fetchOne($sql);
    $stats['checked_in_count'] = (int)$result['total'];
    
    // 未签到人数
    $sql = "SELECT COUNT(*) as total FROM registrations WHERE is_checked_in = 0";
    $result = $db->fetchOne($sql);
    $stats['not_checked_in_count'] = (int)$result['total'];
    
    // 签到率
    if ($stats['total_registrations'] > 0) {
        $stats['checkin_rate'] = round(($stats['checked_in_count'] / $stats['total_registrations']) * 100, 1);
    } else {
        $stats['checkin_rate'] = 0;
    }
    
    // 今日签到人数
    $sql = "SELECT COUNT(*) as total FROM registrations WHERE is_checked_in = 1 AND DATE(checkin_time) = CURDATE()";
    $result = $db->fetchOne($sql);
    $stats['today_checkin_count'] = (int)$result['total'];
    
    return $stats;
}
?>