<?php
/**
 * 获取毕业生文件配置接口
 * GET /api/graduation_config_public.php
 * 
 * 返回: { ok: true, config: { [type]: { name, allowed_extensions: [] } } }
 */
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/graduation_config.php';

// 允许所有用户访问（包括未登录）
setApiHeaders('GET, OPTIONS');
handleOptionsRequest();
requireMethod('GET');

try {
    $fullConfig = getGraduationConfig();
    $publicConfig = [];
    
    foreach ($fullConfig as $key => $conf) {
        $publicConfig[$key] = [
            'name' => $conf['name'],
            'allowed_extensions' => $conf['allowed_extensions'] ?? []
        ];
    }
    
    jsonSuccess(['config' => $publicConfig]);
} catch (Throwable $e) {
    jsonServerError($e);
}
