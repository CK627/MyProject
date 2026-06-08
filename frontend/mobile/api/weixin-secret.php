<?php
// 微信公众号配置
// 注意：此文件包含敏感信息，请确保不要提交到版本控制系统

return [
    'appId' => '<WECHAT_APP_ID>',
    'appSecret' => '<WECHAT_APP_SECRET>', // AppSecret已配置
    
    // 微信支付配置（如果需要）
    'mchId' => '<WECHAT_MCH_ID>', // 商户号
    'apiKey' => '<WECHAT_API_KEY>', // API密钥
    
    // 证书路径
    'certPath' => __DIR__ . '/开放平台证书.cer',
    'keyPath' => __DIR__ . '/非对称密钥.txt',
    'symmetricKey' => file_get_contents(__DIR__ . '/对称密钥.txt'),
    
    // 其他配置
    'debug' => false, // 是否开启调试模式
];
?>