<?php
// api/ReviewHelper.php

require_once __DIR__ . '/graduation_config.php';

class ReviewHelper {
    public static function getReviewColumn($type) {
        $config = getGraduationConfig();
        if (!isset($config[$type])) {
            return null;
        }
        
        $colPath = $config[$type]['col_path'];
        $reviewCol = $colPath . '_review_result';
        
        // Handle MySQL column name length limit (64 characters)
        if (strlen($reviewCol) > 64) {
            $maxLen = 64 - strlen('_review_result');
            $reviewCol = substr($colPath, 0, $maxLen) . '_review_result';
        }
        
        return $reviewCol;
    }

    public static function getAnnotationColumn($type) {
        $config = getGraduationConfig();
        if (!isset($config[$type])) {
            return null;
        }
        
        $colPath = $config[$type]['col_path'];
        $annoCol = $colPath . ' Annotation';
        
        // Handle MySQL column name length limit (64 characters)
        if (strlen($annoCol) > 64) {
            $maxLen = 64 - strlen(' Annotation');
            $annoCol = substr($colPath, 0, $maxLen) . ' Annotation';
        }
        
        return $annoCol;
    }

    public static function validateResult($result) {
        return in_array($result, ['未批阅', '不通过', '通过']);
    }
}
