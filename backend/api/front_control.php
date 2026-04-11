<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// 处理预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// 检查请求方法
$method = $_SERVER['REQUEST_METHOD'];

define('FRONTEND_PATH', dirname(__DIR__, 2) . '/frontend/'); // 前端页面路径

try {
    if ($method === 'GET') {
        // 获取前端页面权限状态
        $status = getFrontendPermissionStatus();
        echo json_encode([
            'success' => true,
            'status' => $status['status'],
            'permission' => $status['permission'],
            'message' => '前端页面权限状态获取成功'
        ]);
        
    } elseif ($method === 'POST') {
        // 控制前端页面权限
        $rawInput = file_get_contents('php://input');
        $input = json_decode($rawInput, true);
        
        // 添加调试日志
        error_log('POST请求接收到的原始数据: ' . $rawInput);
        error_log('解析后的JSON数据: ' . print_r($input, true));
        
        if (!isset($input['action'])) {
            throw new Exception('缺少action参数，接收到的数据: ' . json_encode($input));
        }
        
        $action = $input['action'];
        
        if ($action === 'open') {
            $result = openFrontendPermission();
        } elseif ($action === 'close') {
            $result = closeFrontendPermission();
        } else {
            throw new Exception('无效的action参数: ' . $action);
        }
        
        echo json_encode([
            'success' => true,
            'message' => $result['message'],
            'status' => $result['status'],
            'permission' => $result['permission']
        ]);
        
    } else {
        throw new Exception('不支持的请求方法: ' . $method);
    }
    
} catch (Exception $e) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage()
    ]);
}

/**
 * 获取前端页面权限状态
 */
function getFrontendPermissionStatus() {
    $output = [];
    $returnCode = 0;
    // 使用 escapeshellarg 来处理路径中的空格等特殊字符
    $cmd = 'stat ' . escapeshellarg(FRONTEND_PATH) . ' 2>/dev/null';
    exec($cmd, $output, $returnCode);
    $permission = '未知';
    foreach ($output as $line) {
        if (strpos($line, 'Access: (') !== false) {
            // 匹配括号内的数字权限（支持三位和四位）
            if (preg_match('/Access: \((\d{3,4})/', $line, $matches)) {
                $permission = $matches[1];
                break;
            }
        }
    }
    // 支持三位和四位权限码
    if ($permission === '777' || $permission === '0777') {
        return ['status' => 'open', 'permission' => $permission];
    } elseif ($permission === '000' || $permission === '0000') {
        return ['status' => 'closed', 'permission' => $permission];
    } else {
        // 如果不是777也不是000，我们也认为它是某种开放状态（只要不是完全不可读）
        // 但为了严谨，这里返回 unknown，或者可以根据业务需求调整
        return ['status' => 'unknown', 'permission' => $permission];
    }
}

/**
 * 开启前端页面权限
 */
function openFrontendPermission() {
    $output = [];
    $returnCode = 0;
    // 首先检查当前状态
    $status = getFrontendPermissionStatus();
    if ($status['status'] === 'open') {
        return [
            'status' => 'open',
            'permission' => $status['permission'],
            'message' => '前端页面权限已经是开放状态'
        ];
    }
    // 修改权限为777
    exec('chmod -R 777 ' . FRONTEND_PATH . ' 2>&1', $output, $returnCode);
    sleep(1);
    $status = getFrontendPermissionStatus();
    if ($status['status'] === 'open') {
        return [
            'status' => 'open',
            'permission' => $status['permission'],
            'message' => '前端页面权限已开放'
        ];
    } else {
        throw new Exception('前端页面权限开放失败: ' . implode('\n', $output));
    }
}

/**
 * 关闭前端页面权限
 */
function closeFrontendPermission() {
    $output = [];
    $returnCode = 0;
    // 首先检查当前状态
    $status = getFrontendPermissionStatus();
    if ($status['status'] === 'closed') {
        return [
            'status' => 'closed',
            'permission' => $status['permission'],
            'message' => '前端页面权限已经是关闭状态'
        ];
    }
    // 修改权限为000
    exec('chmod -R 000 ' . FRONTEND_PATH . ' 2>&1', $output, $returnCode);
    sleep(1);
    $status = getFrontendPermissionStatus();
    if ($status['status'] === 'closed') {
        return [
            'status' => 'closed',
            'permission' => $status['permission'],
            'message' => '前端页面权限已关闭'
        ];
    } else {
        throw new Exception('前端页面权限关闭失败: ' . implode('\n', $output));
    }
}
?>