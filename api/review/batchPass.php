<?php
// api/review/batchPass.php

require_once __DIR__ . '/../db_graduation.php';
require_once __DIR__ . '/../ReviewHelper.php';

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method Not Allowed']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);

$studentIDs = $input['fileIds'] ?? []; // Using fileIds as per requirement, assuming they are studentIDs
$project = $input['projectType'] ?? null;

if (empty($studentIDs) || !is_array($studentIDs) || !$project) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing required parameters']);
    exit;
}

$column = ReviewHelper::getReviewColumn($project);
if (!$column) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid project type']);
    exit;
}

$db = getGraduationDb();
$table = GRADUATION_TABLE;

// Prepare placeholders for IN clause
$placeholders = implode(',', array_fill(0, count($studentIDs), '?'));
$types = str_repeat('s', count($studentIDs));

// Update query
$sql = "UPDATE `$table` SET `$column` = '通过' WHERE `studentID` IN ($placeholders)";
$stmt = $db->prepare($sql);

if (!$stmt) {
    http_response_code(500);
    echo json_encode(['error' => 'Database prepare failed: ' . $db->error]);
    exit;
}

$stmt->bind_param($types, ...$studentIDs);

if ($stmt->execute()) {
    echo json_encode(['success' => true, 'affected_rows' => $stmt->affected_rows]);
} else {
    http_response_code(500);
    echo json_encode(['error' => 'Update failed: ' . $stmt->error]);
}

$stmt->close();
