-- MySQL dump 10.13  Distrib 8.0.44, for Linux (x86_64)
--
-- Host: localhost    Database: FileUploadS
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
-- Table structure for table `user_000`
--

DROP TABLE IF EXISTS `user_000`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_000` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公开',
  `upload_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `last_download_at` timestamp NULL DEFAULT NULL COMMENT '最近一次下载时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_123456`
--

DROP TABLE IF EXISTS `user_123456`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_123456` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公开',
  `upload_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `last_download_at` timestamp NULL DEFAULT NULL COMMENT '最近一次下载时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_157`
--

DROP TABLE IF EXISTS `user_157`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_157` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公开',
  `upload_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `last_download_at` timestamp NULL DEFAULT NULL COMMENT '最近一次下载时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_2402410110`
--

DROP TABLE IF EXISTS `user_2402410110`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_2402410110` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公开',
  `upload_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `last_download_at` timestamp NULL DEFAULT NULL COMMENT '最近一次下载时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_2402410203`
--

DROP TABLE IF EXISTS `user_2402410203`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_2402410203` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公开',
  `upload_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `last_download_at` timestamp NULL DEFAULT NULL COMMENT '最近一次下载时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_2402410217`
--

DROP TABLE IF EXISTS `user_2402410217`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_2402410217` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公开',
  `upload_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `last_download_at` timestamp NULL DEFAULT NULL COMMENT '最近一次下载时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2949 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_2402410220`
--

DROP TABLE IF EXISTS `user_2402410220`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_2402410220` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公开',
  `upload_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `last_download_at` timestamp NULL DEFAULT NULL COMMENT '最近一次下载时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_2402410241`
--

DROP TABLE IF EXISTS `user_2402410241`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_2402410241` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公开',
  `upload_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `last_download_at` timestamp NULL DEFAULT NULL COMMENT '最近一次下载时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_2402410252`
--

DROP TABLE IF EXISTS `user_2402410252`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_2402410252` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公开',
  `upload_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `last_download_at` timestamp NULL DEFAULT NULL COMMENT '最近一次下载时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_244202442`
--

DROP TABLE IF EXISTS `user_244202442`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_244202442` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公开',
  `upload_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `last_download_at` timestamp NULL DEFAULT NULL COMMENT '最近一次下载时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_666`
--

DROP TABLE IF EXISTS `user_666`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_666` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `is_public` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否公开',
  `upload_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `last_download_at` timestamp NULL DEFAULT NULL COMMENT '最近一次下载时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-02-18  2:21:18
