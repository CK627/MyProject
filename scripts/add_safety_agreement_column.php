<?php
require_once __DIR__ . '/../api/db_graduation.php';

try {
    $mysqli = getGraduationDb();
    
    // Check if column exists
    // We use a shortened name because of MySQL 64 char limit
    // Base: Safety Responsibility Agreement
    $baseName = 'Safety Responsibility Agreement';
    
    $result = $mysqli->query("SHOW COLUMNS FROM Users LIKE '$baseName'");
    if ($result && $result->num_rows > 0) {
        echo "Column '$baseName' already exists.\n";
    } else {
        // Add columns
        $sql = "ALTER TABLE Users 
                ADD COLUMN `$baseName` VARCHAR(255) DEFAULT NULL,
                ADD COLUMN `$baseName download count` INT DEFAULT 0,
                ADD COLUMN `$baseName Final Submission Time` DATETIME DEFAULT NULL,
                ADD COLUMN `$baseName download time` DATETIME DEFAULT NULL";
        
        if ($mysqli->query($sql)) {
            echo "Added columns for $baseName.\n";
        } else {
            echo "Error adding columns: " . $mysqli->error . "\n";
        }
    }
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
?>
