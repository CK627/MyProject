-- MySQL dump 10.13  Distrib 8.0.44, for Linux (x86_64)
--
-- Host: localhost    Database: FileUpload
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `Settings`
--

DROP TABLE IF EXISTS `Settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Settings` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '对应用户名（唯一）',
  `HomepageSettings` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'list' COMMENT '默认首页目标（如 upload/list/...)',
  `HiddenFile` tinyint(1) NOT NULL DEFAULT '1' COMMENT '上传是否跳过隐藏文件（1=True=跳过，0=False=不跳过）',
  `ShowHiddenFiles` tinyint(1) NOT NULL DEFAULT '0' COMMENT '文件列表是否显示隐藏文件（1=True=显示，0=False=隐藏）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_settings_user` (`user`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户设置表，每个用户一条记录（后续可扩展更多设置项）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `Users`
--

DROP TABLE IF EXISTS `Users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Users` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID，唯一标识用户',
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '登录用户名，唯一',
  `password` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码哈希（不存明文）',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `last_login_at` timestamp NULL DEFAULT NULL COMMENT '最近一次登录时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表，存储登录认证信息';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `admins`
--

DROP TABLE IF EXISTS `admins`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admins` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '管理员用户名，唯一',
  `class` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '所属班级',
  `password` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码哈希',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `last_login_at` timestamp NULL DEFAULT NULL COMMENT '最近登录时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_admin_username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理员账户表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_logs`
--

DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_logs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '操作用户',
  `action` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '操作类型',
  `target` varchar(1024) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '操作目标',
  `details` text COLLATE utf8mb4_unicode_ci COMMENT '详细信息(JSON)',
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'IP地址',
  `user_agent` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户代理',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_username` (`username`),
  KEY `idx_action` (`action`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=3052 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `graduation_information`
--

DROP TABLE IF EXISTS `graduation_information`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `graduation_information` (
  `ID` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `studentID` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '学生学号',
  `name` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '学生姓名',
  `class` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '班级',
  `Application Form for Internship Unit` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '岗位实习单位申请表-文件路径',
  `Application Form for Internship Unit Final Submission Time` datetime DEFAULT NULL COMMENT '岗位实习单位申请表-最近提交时间',
  `Application Form for Internship Unit download count` int NOT NULL DEFAULT '0' COMMENT '岗位实习单位申请表-下载次数',
  `Application Form for Internship Unit download time` datetime DEFAULT NULL COMMENT '岗位实习单位申请表-最近下载时间',
  `Application Form for Internship Unit_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '岗位实习单位申请表-批阅结果',
  `Application Form for Internship Unit Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '岗位实习单位申请表-批注',
  `Tripartite Agreement for Student Position` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学生岗位三方协议书-文件路径',
  `Tripartite Agreement for Student Position download count` int NOT NULL DEFAULT '0' COMMENT '学生岗位三方协议书-下载次数',
  `Tripartite Agreement for Student Position download time` datetime DEFAULT NULL COMMENT '学生岗位三方协议书-最近下载时间',
  `Tripartite Agreement for Student Position Final Submission Time` datetime DEFAULT NULL COMMENT '学生岗位三方协议书-最近提交时间',
  `Tripartite Agreement for Student Position_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '学生岗位三方协议书-批阅结果',
  `Tripartite Agreement for Student Position Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '学生岗位三方协议书-批注',
  `Opinions of the internship unit` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '实习单位意见-文件路径',
  `Opinions of the internship unit download count` int NOT NULL DEFAULT '0' COMMENT '实习单位意见-下载次数',
  `Opinions of the internship unit download time` datetime DEFAULT NULL COMMENT '实习单位意见-最近下载时间',
  `Opinions of the internship unit Final Submission Time` datetime DEFAULT NULL COMMENT '实习单位意见-最近提交时间',
  `Opinions of the internship unit_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '实习单位意见-批阅结果',
  `Opinions of the internship unit Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '实习单位意见-批注',
  `Internship Self-Accommodation Commitment` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '实习自主住宿承诺书及家长意见-文件路径',
  `Internship Self-Accommodation Commitment download count` int NOT NULL DEFAULT '0' COMMENT '实习自主住宿承诺书及家长意见-下载次数',
  `Internship Self-Accommodation Commitment download time` datetime DEFAULT NULL COMMENT '实习自主住宿承诺书及家长意见-最近下载时间',
  `Internship Self-Accommodation Commitment Final Submission Time` datetime DEFAULT NULL COMMENT '实习自主住宿承诺书及家长意见-最近提交时间',
  `Internship Self-Accommodation Commitment_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '实习自主住宿承诺书及家长意见-批阅结果',
  `Internship Self-Accommodation Commitment Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '实习自主住宿承诺书及家长意见-批注',
  `parental opinion` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '家长意见-文件路径',
  `parental opinion download count` int NOT NULL DEFAULT '0' COMMENT '家长意见-下载次数',
  `parental opinion download time` datetime DEFAULT NULL COMMENT '家长意见-最近下载时间',
  `parental opinion Final Submission Time` datetime DEFAULT NULL COMMENT '家长意见-最近提交时间',
  `parental opinion_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '家长意见-批阅结果',
  `parental opinion Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '家长意见-批注',
  `Informed Consent Form for Legal Guardian` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '丙方实习岗位实习法定监护人（或家长）知情同意书提交-文件路径',
  `Informed Consent Form for Legal Guardian download count` int NOT NULL DEFAULT '0' COMMENT '丙方实习岗位实习法定监护人（或家长）知情同意书提交-下载次数',
  `Informed Consent Form for Legal Guardian download time` datetime DEFAULT NULL COMMENT '丙方实习岗位实习法定监护人（或家长）知情同意书提交-最近下载时间',
  `Informed Consent Form for Legal Guardian Final Submission Time` datetime DEFAULT NULL COMMENT '丙方实习岗位实习法定监护人（或家长）知情同意书提交-最近提交时间',
  `Informed Consent Form for Legal Guardian_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '丙方实习岗位实习法定监护人（或家长）知情同意书提交-批阅结果',
  `Informed Consent Form for Legal Guardian Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '丙方实习岗位实习法定监护人（或家长）知情同意书提交-批注',
  `Student Internship Company Inspection Report Form` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学生实习企业考察报告表-文件路径',
  `Student Internship Company Inspection Report Form download count` int NOT NULL DEFAULT '0' COMMENT '学生实习企业考察报告表-下载次数',
  `Student Internship Company Inspection Report Form download time` datetime DEFAULT NULL COMMENT '学生实习企业考察报告表-最近下载时间',
  `Student Internship Company Inspection Report Form Final Time` datetime DEFAULT NULL COMMENT '学生实习企业考察报告表-最近提交时间',
  `Student Internship Company Inspection Report Form_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '学生实习企业考察报告表-批阅结果',
  `Student Internship Company Inspection Report Form Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '学生实习企业考察报告表-批注',
  `Summary Table of Student Internship Enterprise Inspection` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学生实习企业考察情况汇总表-文件路径',
  `Summary Table of Student Internship Enterprise Inspection Count` int NOT NULL DEFAULT '0' COMMENT '学生实习企业考察情况汇总表-下载次数',
  `Summary Table of Student Internship Enterprise Inspection DlTime` datetime DEFAULT NULL COMMENT '学生实习企业考察情况汇总表-最近下载时间',
  `Summary Table of Student Internship Enterprise Inspection Final` datetime DEFAULT NULL COMMENT '学生实习企业考察情况汇总表-最近提交时间',
  `Summary Table of Student Internship Enterprise Ins_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '学生实习企业考察情况汇总表-批阅结果',
  `Summary Table of Student Internship Enterprise Inspec Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '学生实习企业考察情况汇总表-批注',
  `Business license` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业营业执照-文件路径',
  `Business license download count` int DEFAULT '0' COMMENT '企业营业执照-下载次数',
  `Business license download time` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业营业执照-最近下载时间',
  `Business license Final Submission Time` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业营业执照-最近提交时间',
  `Business license_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '企业营业执照-批阅结果',
  `Business license Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '企业营业执照-批注',
  `Corporate credit report` varchar(1024) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业信用报告-文件路径',
  `Corporate credit report download count` int DEFAULT '0' COMMENT '企业信用报告-下载次数',
  `Corporate credit report_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '企业信用报告-批阅结果',
  `Corporate credit report download time` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业信用报告-最近下载时间',
  `Corporate credit report Final Submission Time` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业信用报告-最近提交时间',
  `Corporate credit report Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '企业信用报告-批注',
  `Safety Responsibility Agreement` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '毕业实习安全责任书-文件路径',
  `Safety Responsibility Agreement download count` int DEFAULT '0' COMMENT '毕业实习安全责任书-下载次数',
  `Safety Responsibility Agreement Final Submission Time` datetime DEFAULT NULL COMMENT '毕业实习安全责任书-最近提交时间',
  `Safety Responsibility Agreement download time` datetime DEFAULT NULL COMMENT '毕业实习安全责任书-最近下载时间',
  `Safety Responsibility Agreement_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '毕业实习安全责任书-批阅结果',
  `Safety Responsibility Agreement Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '毕业实习安全责任书-批注',
  `Internship Report and Assessment Form` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '岗位实习报告及考核表-文件路径',
  `Internship Report and Assessment Form download count` int DEFAULT '0' COMMENT '岗位实习报告及考核表-下载次数',
  `Internship Report and Assessment Form download time` datetime DEFAULT NULL COMMENT '岗位实习报告及考核表-最近下载时间',
  `Internship Report and Assessment Form Final Submission Time` datetime DEFAULT NULL COMMENT '岗位实习报告及考核表-最近提交时间',
  `Internship Report and Assessment Form_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '岗位实习报告及考核表-批阅结果',
  `Internship Report and Assessment Form Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '岗位实习报告及考核表-批注',
  `Internship Student Info and Instructor Summary` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '实习学生信息及指导教师名单汇总表-文件路径',
  `Internship Student Info and Instructor Summary download count` int DEFAULT '0' COMMENT '实习学生信息及指导教师名单汇总表-下载次数',
  `Internship Student Info and Instructor Summary download time` datetime DEFAULT NULL COMMENT '实习学生信息及指导教师名单汇总表-最近下载时间',
  `Internship Student Info and Instructor Summary Final Time` datetime DEFAULT NULL COMMENT '实习学生信息及指导教师名单汇总表-最近提交时间',
  `Internship Student Info and Instructor Summary_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '实习学生信息及指导教师名单汇总表-批阅结果',
  `Internship Student Info and Instructor Summary Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '实习学生信息及指导教师名单汇总表-批注',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `uniq_student` (`studentID`)
) ENGINE=InnoDB AUTO_INCREMENT=195 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='毕业实习相关文件提交信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `graduation_information_copy1`
--

DROP TABLE IF EXISTS `graduation_information_copy1`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `graduation_information_copy1` (
  `ID` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `studentID` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '学生学号',
  `name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '学生姓名',
  `class` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '班级',
  `Application Form for Internship Unit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '岗位实习单位申请表-文件路径',
  `Application Form for Internship Unit Final Submission Time` datetime DEFAULT NULL COMMENT '岗位实习单位申请表-最近提交时间',
  `Application Form for Internship Unit download count` int NOT NULL DEFAULT '0' COMMENT '岗位实习单位申请表-下载次数',
  `Application Form for Internship Unit download time` datetime DEFAULT NULL COMMENT '岗位实习单位申请表-最近下载时间',
  `Application Form for Internship Unit_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '岗位实习单位申请表-批阅结果',
  `Application Form for Internship Unit Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '岗位实习单位申请表-批注',
  `Tripartite Agreement for Student Position` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学生岗位三方协议书-文件路径',
  `Tripartite Agreement for Student Position download count` int NOT NULL DEFAULT '0' COMMENT '学生岗位三方协议书-下载次数',
  `Tripartite Agreement for Student Position download time` datetime DEFAULT NULL COMMENT '学生岗位三方协议书-最近下载时间',
  `Tripartite Agreement for Student Position Final Submission Time` datetime DEFAULT NULL COMMENT '学生岗位三方协议书-最近提交时间',
  `Tripartite Agreement for Student Position_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '学生岗位三方协议书-批阅结果',
  `Tripartite Agreement for Student Position Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '学生岗位三方协议书-批注',
  `Opinions of the internship unit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '实习单位意见-文件路径',
  `Opinions of the internship unit download count` int NOT NULL DEFAULT '0' COMMENT '实习单位意见-下载次数',
  `Opinions of the internship unit download time` datetime DEFAULT NULL COMMENT '实习单位意见-最近下载时间',
  `Opinions of the internship unit Final Submission Time` datetime DEFAULT NULL COMMENT '实习单位意见-最近提交时间',
  `Opinions of the internship unit_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '实习单位意见-批阅结果',
  `Opinions of the internship unit Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '实习单位意见-批注',
  `Internship Self-Accommodation Commitment` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '实习自主住宿承诺书及家长意见-文件路径',
  `Internship Self-Accommodation Commitment download count` int NOT NULL DEFAULT '0' COMMENT '实习自主住宿承诺书及家长意见-下载次数',
  `Internship Self-Accommodation Commitment download time` datetime DEFAULT NULL COMMENT '实习自主住宿承诺书及家长意见-最近下载时间',
  `Internship Self-Accommodation Commitment Final Submission Time` datetime DEFAULT NULL COMMENT '实习自主住宿承诺书及家长意见-最近提交时间',
  `Informed Consent Form for Legal Guardian_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '丙方实习岗位实习法定监护人（或家长）知情同意书-批阅结果',
  `Internship Self-Accommodation Commitment_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '实习自主住宿承诺书及家长意见-批阅结果',
  `Internship Self-Accommodation Commitment Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '实习自主住宿承诺书及家长意见-批注',
  `parental opinion` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '家长意见-文件路径',
  `parental opinion download count` int NOT NULL DEFAULT '0' COMMENT '家长意见-下载次数',
  `parental opinion download time` datetime DEFAULT NULL COMMENT '家长意见-最近下载时间',
  `parental opinion Final Submission Time` datetime DEFAULT NULL COMMENT '家长意见-最近提交时间',
  `parental opinion_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '家长意见-批阅结果',
  `parental opinion Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '家长意见-批注',
  `Informed Consent Form for Legal Guardian` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '法定监护人知情同意书-文件路径',
  `Informed Consent Form for Legal Guardian download count` int NOT NULL DEFAULT '0' COMMENT '法定监护人知情同意书-下载次数',
  `Informed Consent Form for Legal Guardian download time` datetime DEFAULT NULL COMMENT '法定监护人知情同意书-最近下载时间',
  `Informed Consent Form for Legal Guardian Final Submission Time` datetime DEFAULT NULL COMMENT '法定监护人知情同意书-最近提交时间',
  `Student Internship Company Inspection Report Form` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学生实习企业考察报告表-文件路径',
  `Student Internship Company Inspection Report Form download count` int NOT NULL DEFAULT '0' COMMENT '学生实习企业考察报告表-下载次数',
  `Student Internship Company Inspection Report Form download time` datetime DEFAULT NULL COMMENT '学生实习企业考察报告表-最近下载时间',
  `Student Internship Company Inspection Report Form Final Time` datetime DEFAULT NULL COMMENT '学生实习企业考察报告表-最近提交时间',
  `Student Internship Company Inspection Report Form_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '学生实习企业考察报告表-批阅结果',
  `Summary Table of Student Internship Enterprise Inspection` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学生实习企业考察情况汇总表-文件路径',
  `Summary Table of Student Internship Enterprise Inspection Count` int NOT NULL DEFAULT '0' COMMENT '学生实习企业考察情况汇总表-下载次数',
  `Summary Table of Student Internship Enterprise Inspection DlTime` datetime DEFAULT NULL COMMENT '学生实习企业考察情况汇总表-最近下载时间',
  `Summary Table of Student Internship Enterprise Inspection Final` datetime DEFAULT NULL COMMENT '学生实习企业考察情况汇总表-最近提交时间',
  `Business license` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业营业执照-文件路径',
  `Business license download count` int DEFAULT '0' COMMENT '企业营业执照-下载次数',
  `Business license download time` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业营业执照-最近下载时间',
  `Business license Final Submission Time` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业营业执照-最近提交时间',
  `Business license_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '企业营业执照-批阅结果',
  `Corporate credit report` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业信用报告-文件路径',
  `Corporate credit report download count` int DEFAULT '0' COMMENT '企业信用报告-下载次数',
  `Corporate credit report_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '企业信用报告-批阅结果',
  `Corporate credit report download time` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业信用报告-最近下载时间',
  `Corporate credit report Final Submission Time` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '企业信用报告-最近提交时间',
  `Business license Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '企业营业执照-批注',
  `Safety Responsibility Agreement` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '毕业实习安全责任书-文件路径',
  `Safety Responsibility Agreement download count` int DEFAULT '0' COMMENT '毕业实习安全责任书-下载次数',
  `Safety Responsibility Agreement Final Submission Time` datetime DEFAULT NULL COMMENT '毕业实习安全责任书-最近提交时间',
  `Safety Responsibility Agreement download time` datetime DEFAULT NULL COMMENT '毕业实习安全责任书-最近下载时间',
  `Safety Responsibility Agreement_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '毕业实习安全责任书-批阅结果',
  `Safety Responsibility Agreement Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '毕业实习安全责任书-批注',
  `Internship Report and Assessment Form` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '岗位实习报告及考核表-文件路径',
  `Internship Report and Assessment Form download count` int DEFAULT '0' COMMENT '岗位实习报告及考核表-下载次数',
  `Internship Report and Assessment Form download time` datetime DEFAULT NULL COMMENT '岗位实习报告及考核表-最近下载时间',
  `Internship Report and Assessment Form Final Submission Time` datetime DEFAULT NULL COMMENT '岗位实习报告及考核表-最近提交时间',
  `Summary Table of Student Internship Enterprise Ins_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '学生实习企业考察情况汇总表-批阅结果',
  `Internship Student Info and Instructor Summary` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '实习学生信息及指导教师名单汇总表-文件路径',
  `Internship Student Info and Instructor Summary download count` int DEFAULT '0' COMMENT '实习学生信息及指导教师名单汇总表-下载次数',
  `Internship Student Info and Instructor Summary download time` datetime DEFAULT NULL COMMENT '实习学生信息及指导教师名单汇总表-最近下载时间',
  `Internship Student Info and Instructor Summary Final Time` datetime DEFAULT NULL COMMENT '实习学生信息及指导教师名单汇总表-最近提交时间',
  `Internship Student Info and Instructor Summary_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '实习学生信息及指导教师名单汇总表-批阅结果',
  `Internship Student Info and Instructor Summary Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '实习学生信息及指导教师名单汇总表-批注',
  `Internship Report and Assessment Form_review_result` enum('未批阅','不通过','通过') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '未批阅' COMMENT '岗位实习报告及考核表-批阅结果',
  `Informed Consent Form for Legal Guardian Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '丙方实习岗位实习法定监护人（或家长）知情同意书-批注',
  `Student Internship Company Inspection Report Form Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '学生实习企业考察报告表-批注',
  `Summary Table of Student Internship Enterprise Inspec Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '学生实习企业考察情况汇总表-批注',
  `Corporate credit report Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '企业信用报告-批注',
  `Internship Report and Assessment Form Annotation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '岗位实习报告及考核表-批注',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `uniq_student` (`studentID`)
) ENGINE=InnoDB AUTO_INCREMENT=195 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='毕业实习相关文件提交信息表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-02-18  2:03:34
