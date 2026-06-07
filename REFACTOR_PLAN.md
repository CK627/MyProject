# FileUpload 项目架构重构规划文档

## 1. 目标与背景

目前 `FileUpload` 项目的后端 API 存在近 60 个 PHP 文件直接堆积在 `api/` 目录下的情况。这种传统的“单一脚本处理单一请求（One-File-Per-Route）”模式在项目初期便于快速开发，但随着项目规模的扩大（引入了复杂的毕业设计提交流程、审批流程、角色管理等），暴露出了以下痛点：
1. **路由分散**：没有统一的入口，难以实现全局权限校验、日志记录和跨域控制。
2. **逻辑耦合**：数据库操作、参数校验和业务逻辑全部混在一个文件中，代码难以复用。
3. **命名混乱**：数据库连接文件存在冗余（`db.php`, `db_files.php`, `db_graduation.php` 等），且文件命名规范不统一。

本规划旨在通过引入**轻量级的 MVC 架构**（基于原生 PHP 或轻量级路由库），重构前后端代码，使其具备更高的可维护性、扩展性和安全性。

---

## 2. 后端 (PHP) 重构规划

### 2.1 目录结构调整

将原来扁平化的 `api/` 目录重新组织为分层结构。

**重构后预期的 `api/` 目录结构：**
```text
api/
├── index.php                 # 统一前端控制器 (Front Controller)，拦截所有请求
├── .htaccess                 # (或 nginx.conf) 配合路由使用的重写规则
├── config/                   # 配置文件
│   ├── database.php          # 统一数据库配置
│   └── app.php               # 应用全局配置
├── core/                     # 核心组件
│   ├── Router.php            # 轻量级路由类
│   ├── Database.php          # 单例数据库连接类 (已存在，需整合)
│   ├── Request.php           # 请求封装类
│   ├── Response.php          # 响应封装类 (统一返回 JSON 格式)
│   └── ExceptionHandler.php  # 全局异常处理
├── controllers/              # 控制器层 (处理 HTTP 请求与响应)
│   ├── AuthController.php    # 登录、登出、密码修改
│   ├── FileController.php    # 基础网盘文件操作 (上传、列表、删除、移动)
│   ├── ClassController.php   # 班级/学生名单管理
│   ├── GradFileController.php# 毕业/实习文件提交与下载
│   ├── ReviewController.php  # 教师审批相关
│   └── SystemController.php  # 系统设置与日志
└── services/                 # 业务逻辑层 (复用代码)
    ├── AuthService.php
    ├── FileService.php
    ├── ClassService.php
    └── ReviewService.php
```

### 2.2 核心改造步骤

#### 步骤一：建立统一入口与路由 (Front Controller)
1. 新建 `api/index.php`，捕获所有发往 `/api/*` 的请求。
2. 配置 Web 服务器（如 Vercel 或 Apache/Nginx）将 `/api/` 下的所有请求重写到 `/api/index.php`。
3. 在 `index.php` 中引入一个轻量级的 Router，定义 RESTful 风格的 API 路径。例如：
   - `POST /api/auth/login` -> `AuthController@login`
   - `GET /api/graduation/status` -> `GradFileController@getMyStatus`

#### 步骤二：统一全局中间件 (Middleware)
1. **跨域 (CORS)**：统一在 `index.php` 顶部处理跨域头部，不再每个文件写一遍。
2. **鉴权 (Auth)**：实现一个拦截器，对于需要登录的路由，在进入 Controller 之前检查 Session，失败直接返回 `401 Unauthorized`。
3. **异常处理**：注册 `set_exception_handler`，确保任何 PHP Fatal Error 或抛出的 Exception 都会被转化为标准格式的 `500 Internal Server Error` JSON 响应。

#### 步骤三：整合数据库连接
1. 清理冗余的 `db.php`, `db_files.php`, `db_graduation.php`。
2. 强化现有的 `Database.php`，作为唯一的数据库访问入口。

#### 步骤四：按模块迁移接口
逐步将原有的独立 PHP 文件迁移到对应的 Controller 中。
*(示例映射关系)*
- `login.php` -> `AuthController::login()`
- `upload_universal.php` -> `GradFileController::upload()`
- `get_my_status.php` -> `GradFileController::getMyStatus()`
- `class_list.php` -> `ClassController::getList()`

---

## 3. 前端 (JS) 重构规划

后端的 API 路径发生改变后，前端的 JS 请求代码也需要同步进行改造。

### 3.1 统一网络请求封装 (Axios / Fetch Wrapper)

目前前端有大量的分散 `fetch()` 调用（如 `js/upload.js`, `js/files-core.js`, `js/teacher-class.js`），错误处理和参数拼接比较零散。

**改造方案：**
在 `js/` 目录下新建一个 `request.js` (或 `api.js`) 文件，封装全局的 `fetch` 请求：

```javascript
// js/request.js 示例
const apiClient = async (url, options = {}) => {
    const defaultOptions = {
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    // 如果是 FormData，不要手动设置 Content-Type，让浏览器自动设置 Boundary
    if (options.body instanceof FormData) {
        delete defaultOptions.headers['Content-Type'];
    }

    const finalOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, finalOptions);
        
        // 全局拦截 401 未登录
        if (response.status === 401) {
            window.location.href = '/index.html';
            return { ok: false, error: '请先登录' };
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Request Error:', error);
        return { ok: false, error: '网络请求异常' };
    }
};
```

### 3.2 更新 API 路由映射

将分散在各个 JS 文件中的硬编码 URL 替换为新的 RESTful URL，并使用封装好的 `apiClient`。

**涉及改造的文件列表及大致改动：**
1. **`js/files-graduation.js`**: 
   - `fetch('/api/get_my_status.php')` -> `apiClient('/api/graduation/status', { method: 'GET' })`
   - `fetch('/api/upload_universal.php')` -> 调整为新的上传端点。
2. **`js/teacher-class.js`**:
   - `fetch('/api/class_list.php')` -> `apiClient('/api/class/list', { method: 'GET' })`
   - `fetch('/api/class_add.php')` -> `apiClient('/api/class/add', { method: 'POST', body: JSON.stringify(...) })`
3. **`js/files-list.js` & `js/files-core.js`**:
   - `fetch('/api/list.php')` -> `apiClient('/api/file/list')`
   - `fetch('/api/delete.php')` -> `apiClient('/api/file/delete')`
4. **`js/teacher-filestat.js` & `js/teacher-review.js`**:
   - `fetch('/api/reject_universal.php')` -> `apiClient('/api/review/reject')`

### 3.3 其他前端优化建议
- **常量集中管理**：将所有的 API URL 提取到一个配置文件（如 `config.js`）中统一管理，避免魔法字符串。
- **状态管理**：对于 `teacher-core.js` 中的全局状态（如当前的教师信息），可以考虑引入一个极简的状态管理模式，避免在多个文件间互相传递。

---

## 4. 实施策略与建议顺序

为了避免大规模重构导致系统崩溃，建议采用**渐进式重构（Strangler Fig Pattern）**：

1. **第一阶段：基建搭建**
   - 在后端建立 `index.php`、`Router` 和基础的 `Controller` 结构。
   - 在前端建立 `request.js` 统一请求拦截器。
2. **第二阶段：边缘模块迁移**
   - 挑选相对独立的模块（如：`设置模块`、`班级管理模块`）进行试点。
   - 后端把对应的 PHP 脚本迁移进 Controller。
   - 前端把相关页面的 `fetch` 替换为 `apiClient`，验证功能正常。
3. **第三阶段：核心模块迁移**
   - 迁移最核心的“毕业文件提交流程”和“分片上传”模块。这部分逻辑最复杂，需要编写完备的测试用例进行比对。
4. **第四阶段：清理战场**
   - 删除根目录 `api/` 下所有旧的、独立的 PHP 脚本。
   - 清理旧的数据库连接文件。

---

*文档生成时间：2026-04-21*
