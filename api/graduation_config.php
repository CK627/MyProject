<?php
// api/graduation_config.php

function getGraduationConfig() {
    $config = [
        'thesis' => [
            'col_path' => 'Application Form for Internship Unit',
            'col_dl_count' => 'Application Form for Internship Unit download count',
            'col_dl_time' => 'Application Form for Internship Unit download time',
            'col_final_time' => 'Application Form for Internship Unit Final Submission Time',
            'suffix' => '浙江工商职业技术学院学生自行联系岗位实习单位申请表',
            'name' => '岗位实习单位申请表',
            'allowed_extensions' => ['pdf']
        ],
        'internship' => [
            'col_path' => 'Tripartite Agreement for Student Position',
            'col_dl_count' => 'Tripartite Agreement for Student Position download count',
            'col_dl_time' => 'Tripartite Agreement for Student Position download time',
            'col_final_time' => 'Tripartite Agreement for Student Position Final Submission Time',
            'suffix' => '学生岗位实习三方协议',
            'name' => '学生岗位三方协议书',
            'allowed_extensions' => ['pdf']
        ],
        'opinion' => [
            'col_path' => 'Opinions of the internship unit',
            'col_dl_count' => 'Opinions of the internship unit download count',
            'col_dl_time' => 'Opinions of the internship unit download time',
            'col_final_time' => 'Opinions of the internship unit Final Submission Time',
            'suffix' => '浙实习单位意见',
            'name' => '实习单位意见',
            'allowed_extensions' => ['pdf']
        ],
        'commitment' => [
            'col_path' => 'Internship Self-Accommodation Commitment',
            'col_dl_count' => 'Internship Self-Accommodation Commitment download count',
            'col_dl_time' => 'Internship Self-Accommodation Commitment download time',
            'col_final_time' => 'Internship Self-Accommodation Commitment Final Submission Time',
            'suffix' => '学生实习自主住宿承诺书及家长意见',
            'name' => '实习自主住宿承诺书及家长意见',
            'allowed_extensions' => ['pdf']
        ],
        'parental' => [
            'col_path' => 'parental opinion',
            'col_dl_count' => 'parental opinion download count',
            'col_dl_time' => 'parental opinion download time',
            'col_final_time' => 'parental opinion Final Submission Time',
            'suffix' => '家长意见',
            'name' => '家长意见',
            'allowed_extensions' => ['pdf']
        ],
        'guardian' => [
            'col_path' => 'Informed Consent Form for Legal Guardian',
            'col_dl_count' => 'Informed Consent Form for Legal Guardian download count',
            'col_dl_time' => 'Informed Consent Form for Legal Guardian download time',
            'col_final_time' => 'Informed Consent Form for Legal Guardian Final Submission Time',
            'suffix' => '丙方实习岗位实习法定监护人知情同意书',
            'name' => '丙方实习岗位实习法定监护人知情同意书',
            'allowed_extensions' => ['pdf']
        ],
        'report' => [
            'col_path' => 'Student Internship Company Inspection Report Form',
            'col_dl_count' => 'Student Internship Company Inspection Report Form download count',
            'col_dl_time' => 'Student Internship Company Inspection Report Form download time',
            'col_final_time' => 'Student Internship Company Inspection Report Form Final Time',
            'suffix' => '浙江工商职业技术学院学生实习企业考察报告表',
            'name' => '学生实习企业考察报告表',
            'allowed_extensions' => ['pdf']
        ],
        'summary' => [
            'col_path' => 'Summary Table of Student Internship Enterprise Inspection',
            'col_dl_count' => 'Summary Table of Student Internship Enterprise Inspection Count',
            'col_dl_time' => 'Summary Table of Student Internship Enterprise Inspection DlTime',
            'col_final_time' => 'Summary Table of Student Internship Enterprise Inspection Final',
            'suffix' => '浙江工商职业技术学院学生实习企业考察情况汇总表',
            'name' => '学生实习企业考察情况汇总表',
            'allowed_extensions' => ['doc', 'docx']
        ],
        'license' => [
            'col_path' => 'Business license',
            'col_dl_count' => 'Business license download count',
            'col_dl_time' => 'Business license download time',
            'col_final_time' => 'Business license Final Submission Time',
            'suffix' => '企业营业执照',
            'name' => '企业营业执照',
            'allowed_extensions' => ['pdf']
        ],
        'credit' => [
            'col_path' => 'Corporate credit report',
            'col_dl_count' => 'Corporate credit report download count',
            'col_dl_time' => 'Corporate credit report download time',
            'col_final_time' => 'Corporate credit report Final Submission Time',
            'suffix' => '企业信用报告',
            'name' => '企业信用报告',
            'allowed_extensions' => ['pdf']
        ],
        'safety' => [
            'col_path' => 'Safety Responsibility Agreement',
            'col_dl_count' => 'Safety Responsibility Agreement download count',
            'col_dl_time' => 'Safety Responsibility Agreement download time',
            'col_final_time' => 'Safety Responsibility Agreement Final Submission Time',
            'suffix' => '浙江工商职业技术学院毕业实习安全责任书',
            'name' => '毕业实习安全责任书',
            'allowed_extensions' => ['pdf']
        ],
        'assessment' => [
            'col_path' => 'Internship Report and Assessment Form',
            'col_dl_count' => 'Internship Report and Assessment Form download count',
            'col_dl_time' => 'Internship Report and Assessment Form download time',
            'col_final_time' => 'Internship Report and Assessment Form Final Submission Time',
            'suffix' => '岗位实习报告及考核表',
            'name' => '岗位实习报告及考核表',
            'allowed_extensions' => ['doc', 'docx']
        ],
        'names_summary' => [
            'col_path' => 'Internship Student Info and Instructor Summary',
            'col_dl_count' => 'Internship Student Info and Instructor Summary download count',
            'col_dl_time' => 'Internship Student Info and Instructor Summary download time',
            'col_final_time' => 'Internship Student Info and Instructor Summary Final Time',
            'suffix' => '实习学生信息及指导教师名单汇总表',
            'name' => '实习学生信息及指导教师名单汇总表',
            'allowed_extensions' => ['xls', 'xlsx']
        ],
    ];

    // Check if table config_projects exists, if not create and populate it
    try {
        if (function_exists('getGraduationDb')) {
            $db = getGraduationDb();
            
            $res = $db->query("SHOW TABLES LIKE 'config_projects'");
            if ($res && $res->num_rows == 0) {
                // Create table
                $db->query("CREATE TABLE `config_projects` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `type_key` VARCHAR(64) UNIQUE NOT NULL,
                    `name` VARCHAR(64) NOT NULL,
                    `has_template` TINYINT(1) DEFAULT 0,
                    `template_filename` VARCHAR(255) DEFAULT '',
                    `col_path` VARCHAR(128) NOT NULL,
                    `col_dl_count` VARCHAR(128) NOT NULL,
                    `col_dl_time` VARCHAR(128) NOT NULL,
                    `col_final_time` VARCHAR(128) NOT NULL,
                    `suffix` VARCHAR(128) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

                // Insert default config
                $stmt = $db->prepare("INSERT INTO `config_projects` (`type_key`, `name`, `has_template`, `template_filename`, `col_path`, `col_dl_count`, `col_dl_time`, `col_final_time`, `suffix`) VALUES (?, ?, 0, '', ?, ?, ?, ?, ?)");
                foreach ($config as $k => $v) {
                    $stmt->bind_param('sssssss', $k, $v['name'], $v['col_path'], $v['col_dl_count'], $v['col_dl_time'], $v['col_final_time'], $v['suffix']);
                    $stmt->execute();
                }
                $stmt->close();
            } else {
                // Fetch config from table
                $res = $db->query("SELECT * FROM `config_projects`");
                if ($res) {
                    $db_config = [];
                    while ($row = $res->fetch_assoc()) {
                        $k = $row['type_key'];
                        $db_config[$k] = [
                            'col_path' => $row['col_path'],
                            'col_dl_count' => $row['col_dl_count'],
                            'col_dl_time' => $row['col_dl_time'],
                            'col_final_time' => $row['col_final_time'],
                            'suffix' => $row['suffix'],
                            'name' => $row['name'],
                            'has_template' => (int)$row['has_template'],
                            'template_filename' => $row['template_filename'],
                            'allowed_extensions' => ['pdf'] // Default, overridden below
                        ];
                        // Preserve original allowed_extensions if it was in the hardcoded array
                        if (isset($config[$k]['allowed_extensions'])) {
                            $db_config[$k]['allowed_extensions'] = $config[$k]['allowed_extensions'];
                        }
                    }
                    $config = $db_config;
                }
            }

            // Override allowed_extensions from config_file_types
            $res = $db->query("SHOW TABLES LIKE 'config_file_types'");
            if ($res && $res->num_rows > 0) {
                $res = $db->query("SELECT type_key, allowed_extensions FROM config_file_types");
                if ($res) {
                    while ($row = $res->fetch_assoc()) {
                        $k = $row['type_key'];
                        if (isset($config[$k])) {
                            $exts = explode(',', $row['allowed_extensions']);
                            $config[$k]['allowed_extensions'] = array_map('trim', $exts);
                        }
                    }
                }
            }
        }
    } catch (Throwable $e) {
        // Fallback to default config if DB fails
    }

    return $config;
}
