-- Auto-generated schema update for review system
ALTER TABLE `graduation_information` ADD COLUMN `Summary Table of Student Internship Enterprise Ins_review_result` ENUM('未批阅','不通过','通过') DEFAULT '未批阅' COMMENT '教师批阅结果';
