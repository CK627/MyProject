<?php
/**
 * 模拟数据导出API
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// 处理预检请求
if (isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// 模拟报名数据（已移除缴费金额相关字段）
$mockData = [
    [
        'id' => 1,
        'name' => '张三',
        'phone' => '13800138001',
        'family_count' => 2,
        'talent_show' => 'yes',
        'talent_description' => '唱歌',
        'payment_method' => 'wechat',
        'created_at' => '2025-01-15 10:30:00'
    ],
    [
        'id' => 2,
        'name' => '赵六',
        'phone' => '13800138002',
        'family_count' => 1,
        'talent_show' => 'no',
        'talent_description' => '',
        'payment_method' => 'alipay',
        'created_at' => '2025-01-16 14:20:00'
    ],
    [
        'id' => 3,
        'name' => '孙八',
        'phone' => '13800138003',
        'family_count' => 3,
        'talent_show' => 'yes',
        'talent_description' => '舞蹈',
        'payment_method' => 'bank',
        'created_at' => '2025-01-17 09:15:00'
    ]
];

echo json_encode([
    'success' => true,
    'data' => $mockData,
    'total' => count($mockData)
]);
?>