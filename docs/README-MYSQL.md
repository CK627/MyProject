# 数据库设计说明

## 数据库架构

本项目使用两个 MySQL 数据库：

1. **主库 `FileUpload`**（字符集 `utf8mb4`，排序规则 `utf8mb4_unicode_ci`）
   - `Users`：普通用户认证信息
   - `admins`：教师/管理员信息
   - `Settings`：用户个性化设置
   - `graduation_information`：毕业生信息与提交状态

2. **文件库 `FileUploadS`**
   - `user_{username}`：动态分表，每用户一张表

> **注**：旧版的 `FileUploadGraduationSubmission` 数据库已废弃，毕业生数据已迁移至主库的 `graduation_information` 表。

## Users 表字段与含义
- `id`：主键，自增；唯一标识用户。
- `username`：登录用户名；唯一索引防止重复注册与冲突。
- `password`：密码哈希，不存明文；建议使用 `bcrypt` 或 `argon2`。
- `created_at`：创建时间；默认当前时间。
- `last_login_at`：最近一次登录时间；首次登录前允许为空。

## 设计原则（为什么这样设计）
- 安全性：仅保存哈希与盐；防止明文泄漏与重放攻击。
- 一致性：统一字符集与排序规则，支持多语言用户名。
- 可维护性：通过列与表注释提高可读性，降低上手成本。

## 初始化与运行
- 详细部署请参考 `USAGE.md`
- 配置文件：`config/mysql.ini`（主库）、`config/mysql_files.ini`（文件库）
- 生产环境中将连接信息存入环境变量，避免在命令行直接暴露密码。

## 后续规划
- 增加审计日志表记录关键操作（登录、下载、权限变更）—— 已实现
- 毕业生数据合并至主库 —— 已实现（v3.1）
- 设计文件与文件夹相关表（文件元数据、层级关系、访问权限）。