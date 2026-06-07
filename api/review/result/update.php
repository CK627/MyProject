<?php
// api/review/result/update.php

require_once __DIR__ . '/../../db_graduation.php';
require_once __DIR__ . '/../../ReviewHelper.php';

header('Content-Type: application/json');

// Handle POST request
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method Not Allowed']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);

$studentID = $input['studentID'] ?? null;
$project = $input['project'] ?? null;
$result = $input['result'] ?? null;
$annotation = $input['annotation'] ?? '';

if (!$studentID || !$project || !$result) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing required parameters']);
    exit;
}

if (!ReviewHelper::validateResult($result)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid result value']);
    exit;
}

$reviewColumn = ReviewHelper::getReviewColumn($project);
$annoColumn = ReviewHelper::getAnnotationColumn($project);

if (!$reviewColumn || !$annoColumn) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid project type']);
    exit;
}

$db = getGraduationDb();
$table = GRADUATION_TABLE;

$stmt = $db->prepare("UPDATE `$table` SET `$reviewColumn` = ?, `$annoColumn` = ? WHERE `studentID` = ?");
if (!$stmt) {
    http_response_code(500);
    echo json_encode(['error' => 'Database prepare failed: ' . $db->error]);
    exit;
}

$stmt->bind_param('sss', $result, $annotation, $studentID);

if ($stmt->execute()) {
    echo json_encode(['success' => true]);
} else {
    http_response_code(500);
    echo json_encode(['error' => 'Update failed: ' . $stmt->error]);
}

$stmt->close();
