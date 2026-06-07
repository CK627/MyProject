<?php
// api/convert/status.php

header('Content-Type: application/json');

$taskId = $_GET['taskId'] ?? null;
// Handle /status/{taskId} style if path info is used
if (!$taskId && isset($_SERVER['PATH_INFO'])) {
    $taskId = ltrim($_SERVER['PATH_INFO'], '/');
}

if (!$taskId) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing taskId']);
    exit;
}

$tempDir = sys_get_temp_dir();
$taskFile = $tempDir . '/' . $taskId . '.json';

if (!file_exists($taskFile)) {
    http_response_code(404);
    echo json_encode(['error' => 'Task not found']);
    exit;
}

$data = json_decode(file_get_contents($taskFile), true);
$startTime = $data['startTime'];
$elapsed = time() - $startTime;

if ($data['status'] !== 'completed') {
    if ($elapsed < 2) {
        $data['progress'] = 20;
    } elseif ($elapsed < 4) {
        $data['progress'] = 60;
    } else {
        $data['progress'] = 100;
        $data['status'] = 'completed';
        // In a real app, here we would verify the file exists
    }
    
    // Update task file
    file_put_contents($taskFile, json_encode($data));
}

echo json_encode($data);
