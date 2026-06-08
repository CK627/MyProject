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

function getChartsData($db) {
    try {
        
        $data = [
            'registration_trend' => getRegistrationTrend($db),
            'payment_distribution' => getPaymentDistribution($db),
            'talent_show_stats' => getTalentShowStats($db),
            'sponsorship_trend' => getSponsorshipTrend($db)
        ];
        
        return [
            'success' => true,
            'data' => $data
        ];
    } catch (Exception $e) {
        return [
            'success' => false,
            'message' => '获取图表数据失败: ' . $e->getMessage()
        ];
    }
}

// 获取报名人数趋势（按天统计）
function getRegistrationTrend($db) {
    try {
        $sql = "SELECT DATE(created_at) as date, COUNT(*) as count 
                FROM registrations 
                /* WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) */
                GROUP BY DATE(created_at) 
                ORDER BY date ASC";
        
        $result = $db->fetchAll($sql);
        
        // 如果没有数据，返回空数组
        if (empty($result)) {
            return [];
        }
        
        return $result;
    } catch (Exception $e) {
        // 返回空数组
        return [];
    }
}

// 获取付款方式分布统计（已移除缴费金额统计）
function getPaymentDistribution($db) {
    try {
        $sql = "SELECT payment_method as category, 
                       COUNT(*) as count
                FROM registrations 
                WHERE payment_method IS NOT NULL
                GROUP BY payment_method";
        
        $result = $db->fetchAll($sql);
        
        // 如果没有数据，返回空数组
        if (empty($result)) {
            return [];
        }
        
        return $result;
    } catch (Exception $e) {
        // 返回空数组
        return [];
    }
}

// 获取才艺表演统计
function getTalentShowStats($db) {
    try {
        $sql = "SELECT talent_show as category, COUNT(*) as count 
                FROM registrations 
                WHERE talent_show IS NOT NULL AND talent_show != '' 
                GROUP BY talent_show";
        
        $result = $db->fetchAll($sql);
        
        // 如果没有数据，返回空数组
        if (empty($result)) {
            return [];
        }
        
        return $result;
    } catch (Exception $e) {
        // 返回空数组
        return [];
    }
}

// 获取缴费金额趋势（由于没有sponsors表，返回0值数据）
function getSponsorshipTrend($db) {
    // 由于已移除赞助功能，返回全为0的缴费金额趋势数据
    $mockData = [];
    for ($i = 6; $i >= 0; $i--) {
        $date = date('Y-m-d', strtotime("-$i days"));
        $mockData[] = [
            'date' => $date,
            'amount' => 0
        ];
    }
    return $mockData;
}

// 处理请求
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    try {
        $db = Database::getInstance();
        $result = getChartsData($db);
        echo json_encode($result, JSON_UNESCAPED_UNICODE);
    } catch (Exception $e) {
        echo json_encode([
            'success' => false,
            'message' => 'Error: ' . $e->getMessage()
        ], JSON_UNESCAPED_UNICODE);
    }
} else {
    echo json_encode([
        'success' => false,
        'message' => '不支持的请求方法'
    ], JSON_UNESCAPED_UNICODE);
}
?>