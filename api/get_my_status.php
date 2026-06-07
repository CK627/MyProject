<?php
/**
 * 获取当前登录用户的毕业提交状态
 */
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_config.php';
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/ReviewHelper.php';

// 设置响应头并处理预检
setAuthApiHeaders('GET, OPTIONS');
handleOptionsRequest();
requireMethod('GET');

try {
    initSession();
    $currentUser = getCurrentUser();
    
    // 为了安全性，我们优先使用 Session。如果 Session 不存在，返回 401
    if (!$currentUser) {
        http_response_code(401);
        echo json_encode(['ok' => false, 'error' => '未登录']);
        exit;
    }
    
    $studentID = $currentUser['username'];
    $db = getGraduationDb();
    
    $config = getGraduationConfig();
    $selectFields = [];
    
    // 构建查询字段
    foreach ($config as $key => $conf) {
        $pathCol = $conf['col_path'];
        $finalTimeCol = $conf['col_final_time'];

        $reviewCol = ReviewHelper::getReviewColumn($key);
        $annoCol = ReviewHelper::getAnnotationColumn($key);

        if ($pathCol) {
            $selectFields[] = "`$pathCol` as `{$key}_path`";
        }
        if ($finalTimeCol) {
            $selectFields[] = "`$finalTimeCol` as `{$key}_time`";
        }
        if ($reviewCol) {
            $selectFields[] = "`$reviewCol` as `{$key}_review`";
        }
        if ($annoCol) {
            $selectFields[] = "`$annoCol` as `{$key}_annotation`";
        }
    }
    
    $selectSql = implode(', ', $selectFields);
    $sql = "SELECT $selectSql FROM `graduation_information` WHERE `studentID` = ?";
    
    $stmt = $db->prepare($sql);
    $stmt->bind_param('s', $studentID);
    $stmt->execute();
    $res = $stmt->get_result();
    $row = $res ? $res->fetch_assoc() : null;
    
    if (!$row) {
        // 用户可能不存在于 Users 表中
        echo json_encode(['ok' => true, 'item' => []]);
        exit;
    }
    
    // 格式化输出，匹配前端期望的格式
    // 前端期望: { thesisSubmitted: true, thesisPath: '...', thesisFinalSubmissionTime: '...' }
    $item = [
        'username' => $studentID,
        'name' => '', // Session 中没有 name，暂时留空
        'class' => '' // Session 中没有 class，暂时留空
    ];
    
    foreach ($config as $key => $conf) {
        $path = $row["{$key}_path"] ?? '';
        $time = $row["{$key}_time"] ?? '';
        $review = $row["{$key}_review"] ?? '未批阅';
        $annotation = $row["{$key}_annotation"] ?? '';
        
        $item[$key . 'Submitted'] = ($path !== '' && $path !== null);
        $item[$key . 'Path'] = $path;
        $item[$key . 'FinalSubmissionTime'] = $time;
        
        // Return review and annotation to frontend
        $item[$key . '_review'] = $review;
        $item[$key . '_annotation'] = $annotation;
    }
    
    echo json_encode(['ok' => true, 'item' => $item]);

} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => '服务器内部错误: ' . $e->getMessage()]);
}
