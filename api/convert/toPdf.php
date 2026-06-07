<?php
// api/convert/toPdf.php

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method Not Allowed']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);
$filePath = $input['filePath'] ?? null;

if (!$filePath) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing filePath']);
    exit;
}

// Generate a mock task ID
$taskId = uniqid('task_', true);
$tempDir = sys_get_temp_dir();
$taskFile = $tempDir . '/' . $taskId . '.json';

$data = [
    'taskId' => $taskId,
    'status' => 'processing',
    'progress' => 0,
    'startTime' => time(),
    'filePath' => $filePath,
    // Mock result PDF path (in a real app, this would be generated)
    'pdfUrl' => '/assets/mock_converted.pdf' 
];

file_put_contents($taskFile, json_encode($data));

// Simulate "processing started"
http_response_code(202); // Accepted
echo json_encode([
    'taskId' => $taskId,
    'message' => 'Conversion started'
]);
