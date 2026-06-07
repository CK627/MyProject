<?php
require_once __DIR__ . '/db_graduation.php';
require_once __DIR__ . '/ReviewHelper.php';

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'GET') { http_response_code(405); echo json_encode(['ok'=>false,'error'=>'Method Not Allowed']); exit; }

$cls = trim((string)($_GET['class'] ?? ''));
$type = trim((string)($_GET['type'] ?? 'thesis'));
$reviewResult = trim((string)($_GET['reviewResult'] ?? 'all'));
$sid = trim((string)($_GET['studentID'] ?? ''));

// Map frontend types to DB columns prefix/names
$map = [
    'thesis' => [
        'path' => 'Application Form for Internship Unit',
        'count' => 'Application Form for Internship Unit download count',
        'time' => 'Application Form for Internship Unit download time',
        'final' => 'Application Form for Internship Unit Final Submission Time',
        'key' => 'thesis'
    ],
    'internship' => [
        'path' => 'Tripartite Agreement for Student Position',
        'count' => 'Tripartite Agreement for Student Position download count',
        'time' => 'Tripartite Agreement for Student Position download time',
        'final' => 'Tripartite Agreement for Student Position Final Submission Time',
        'key' => 'internship'
    ],
    'opinion' => [
        'path' => 'Opinions of the internship unit',
        'count' => 'Opinions of the internship unit download count',
        'time' => 'Opinions of the internship unit download time',
        'final' => 'Opinions of the internship unit Final Submission Time',
        'key' => 'opinion'
    ],
    'commitment' => [
        'path' => 'Internship Self-Accommodation Commitment',
        'count' => 'Internship Self-Accommodation Commitment download count',
        'time' => 'Internship Self-Accommodation Commitment download time',
        'final' => 'Internship Self-Accommodation Commitment Final Submission Time',
        'key' => 'commitment'
    ],
    'parental' => [
        'path' => 'parental opinion',
        'count' => 'parental opinion download count',
        'time' => 'parental opinion download time',
        'final' => 'parental opinion Final Submission Time',
        'key' => 'parental'
    ],
    'guardian' => [
        'path' => 'Informed Consent Form for Legal Guardian',
        'count' => 'Informed Consent Form for Legal Guardian download count',
        'time' => 'Informed Consent Form for Legal Guardian download time',
        'final' => 'Informed Consent Form for Legal Guardian Final Submission Time',
        'key' => 'guardian'
    ],
    'report' => [
        'path' => 'Student Internship Company Inspection Report Form',
        'count' => 'Student Internship Company Inspection Report Form download count',
        'time' => 'Student Internship Company Inspection Report Form download time',
        'final' => 'Student Internship Company Inspection Report Form Final Time',
        'key' => 'report'
    ],
    'summary' => [
        'path' => 'Summary Table of Student Internship Enterprise Inspection',
        'count' => 'Summary Table of Student Internship Enterprise Inspection Count',
        'time' => 'Summary Table of Student Internship Enterprise Inspection DlTime',
        'final' => 'Summary Table of Student Internship Enterprise Inspection Final',
        'key' => 'summary'
    ],
    'license' => [
        'path' => 'Business license',
        'count' => 'Business license download count',
        'time' => 'Business license download time',
        'final' => 'Business license Final Submission Time',
        'key' => 'license'
    ],
    'credit' => [
        'path' => 'Corporate credit report',
        'count' => 'Corporate credit report download count',
        'time' => 'Corporate credit report download time',
        'final' => 'Corporate credit report Final Submission Time',
        'key' => 'credit'
    ],
    'safety' => [
        'path' => 'Safety Responsibility Agreement',
        'count' => 'Safety Responsibility Agreement download count',
        'time' => 'Safety Responsibility Agreement download time',
        'final' => 'Safety Responsibility Agreement Final Submission Time',
        'key' => 'safety'
    ],
    'assessment' => [
        'path' => 'Internship Report and Assessment Form',
        'count' => 'Internship Report and Assessment Form download count',
        'time' => 'Internship Report and Assessment Form download time',
        'final' => 'Internship Report and Assessment Form Final Submission Time',
        'key' => 'assessment'
    ],
    'names_summary' => [
        'path' => 'Internship Student Info and Instructor Summary',
        'count' => 'Internship Student Info and Instructor Summary download count',
        'time' => 'Internship Student Info and Instructor Summary download time',
        'final' => 'Internship Student Info and Instructor Summary Final Time',
        'key' => 'names_summary'
    ]
];

// Default to thesis if invalid type
if (!isset($map[$type])) {
    $type = 'thesis';
}

$target = $map[$type];

$reviewCol = ReviewHelper::getReviewColumn($type);
$annoCol = ReviewHelper::getAnnotationColumn($type);

try {
    $db = getGraduationDb();
    // Removed ensureFinalColumns($db) for performance

    $where = [];
    $params = [];
    $typesStr = '';
    
    if ($cls !== '') { 
        $where[] = '`class` = ?'; 
        $params[] = $cls; 
        $typesStr .= 's'; 
    }
    
    if ($sid !== '') {
        $where[] = '`studentID` = ?';
        $params[] = $sid;
        $typesStr .= 's';
    }

    if ($reviewResult !== 'all' && $reviewCol) {
        $where[] = "`$reviewCol` = ?";
        $params[] = $reviewResult;
        $typesStr .= 's';
    }

    $whereClause = '';
    if (count($where) > 0) {
        $whereClause = ' WHERE ' . implode(' AND ', $where);
    }

    // Dynamic selection
    $sql = "SELECT `studentID`, `name`, `class`, 
            `{$target['path']}` as path, 
            `{$target['count']}` as count, 
            `{$target['time']}` as time, 
            `{$target['final']}` as final,
            `{$reviewCol}` as review_result,
            `{$annoCol}` as annotation
            FROM `graduation_information`" . $whereClause;

    if ($whereClause !== '') {
        $stmt = $db->prepare($sql);
        $stmt->bind_param($typesStr, ...$params);
        $stmt->execute();
        $res = $stmt->get_result();
    } else {
        $res = $db->query($sql);
    }

    $items = [];
    while ($res && ($row = $res->fetch_assoc())) {
        $username = (string)($row['studentID'] ?? '');
        $name = (string)($row['name'] ?? '');
        $class = (string)($row['class'] ?? '');
        
        $path = (string)($row['path'] ?? '');
        $cnt = (int)($row['count'] ?? 0);
        $time = (string)($row['time'] ?? '');
        $final = (string)($row['final'] ?? '');
        $review = (string)($row['review_result'] ?? '未批阅');
        $annotation = (string)($row['annotation'] ?? '');

        // Construct item with generic keys that frontend expects for THIS type
        // The frontend expects specific keys like 'thesisSubmitted', etc.
        // We will construct an object that has ONLY the keys for the current type.
        
        $item = [
            'username' => $username,
            'name' => $name,
            'class' => $class
        ];
        
        $key = $target['key']; // e.g., 'thesis'
        $review = (string)($row['review_result'] ?? '未批阅');
        
        // Modified Logic: If review result is '不通过', treat as NOT submitted
        $isSubmitted = ($path !== '') && ($review !== '不通过');
        
        $item[$key . 'Submitted'] = $isSubmitted;
        $item[$key . 'Path'] = $path;
        $item[$key . 'DownloadCount'] = $cnt;
        $item[$key . 'LatestDownloadTime'] = $time;
        $item[$key . 'FinalSubmissionTime'] = $final;
        $item[$key . 'ReviewResult'] = $review;
        $item[$key . 'Annotation'] = $annotation;

        $items[] = $item;
    }

    echo json_encode(['ok' => true, 'items' => $items]);

} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => '服务器内部错误: ' . $e->getMessage()]);
}
