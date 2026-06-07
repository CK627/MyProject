# 文件上传系统（前后端一体版）

一个轻量的文件上传与管理系统，前端使用原生 HTML/CSS/JS，后端为同源 PHP 接口。支持用户认证、文件管理（含分片上传与目录操作）、毕业提交与教师侧统计/打回、Excel 导出等。

**核心设计要点**
- 同源部署，前端与接口无需额外代理。
- 所有接口统一 JSON 响应，参数化查询，避免 SQL 注入。
- 大文件分片上传，进度可视化；自动绕过 `post_max_size` 与 `upload_max_filesize` 限制。
- 毕业提交支持更新替换并删除旧文件（同/不同文件名均处理）。
- **最新改进**：已统一 API 响应格式、修复 SQL 注入风险、提取公共函数减少重复代码、添加表名白名单校验、生产环境异常信息脱敏、分片大小常量化、**审计日志**、**断点续传**、**移动端适配**、**PHP 8.4 兼容**、**全局错误处理器**、**PHP Session 认证**、**教师密码修改**、**毛玻璃UI**、**数据库合并**、**文件重命名**、**自定义弹窗**、**备案号页脚**、**岗位实习报告及考核表**、**实习学生信息及指导教师名单汇总表**、**审批流程优化（自动跳转/快捷审批/通过拒绝按钮/实时刷新）**、**会话自动续期与监控**、**审核逻辑优化（不通过即未收齐）**

## 项目拟解决的主要问题
- **毕业论文/实习提交过程分散、版本混乱**：统一在线提交与更新机制，文件名规范为“长学号+姓名+类型”（例如 `2020001张三岗位实习报告及考核表.docx`），避免重复与难以追踪。
- **大文件上传失败与不可视化**：采用分片上传与进度条反馈，提升稳定性与用户体验。
- **教师审核效率低**：提供“提交/未交”精准筛选（**审核不通过自动归为未交**）、最近提交时间展示、Excel 导出所选名单，快速定位问题学生。
- **审批流程繁琐**：新增快捷审批模式，支持“通过/不通过”一键操作并自动跳转下一个待办，大幅提升批阅效率。
- **资料下载组织混乱**：支持学生/子文件夹/班级打包下载，生成清晰的目录树（班级/长学号姓名项目名称.ext），并过滤隐藏项（.DS_Store、.chunks）。
- **查询与管理不便**：实现班级→学生→文件的层级浏览、双击进入与“..”返回、学号升序排序，方便定位与操作。
- **数据一致性与可审计**：数据库保留“最终提交时间”等字段并添加注释，前后端严格按同源接口交互，避免线下不可控流程。
- **安全与合规**：统一 JSON 响应、参数化查询、防止路径穿越与信息泄露，不在仓库中硬编码敏感信息。
- **兼容性与稳定下载**：使用 ZipArchive 构建临时压缩文件、流式输出并准确 Content-Length，避免压缩包损坏或无法解压。

---

## 模块一：认证与账户
支持用户登录、注册、修改密码及忘记密码重置。

**功能列表**
- 登录/注册、修改密码、按用户名重置密码
- 教师登录（如启用）
- 教师/管理员修改密码
- **会话监控**：自动检测 Session 有效性，过期自动跳转登录页

**API 接口**
- `POST /api/login.php` 登录/注册
- `POST /api/reset_password.php` 忘记密码重置
- `POST /api/change_password.php` 修改密码
- `POST /api/admin_change_password.php` 教师/管理员修改密码
- `GET /api/check_session.php` 检查会话状态

**核心代码索引**
- 会话读取（支持 Session 与 LocalStorage）：
```javascript
// js/files-core.js:98
async function init() {
  // 优先检查 Session 认证
  let user = null;
  try {
    const session = await checkSession();
    if (session.loggedIn && session.user) {
      user = {
        username: session.user.username,
        userId: session.user.userId,
        role: session.user.role,
        isGraduation: session.user.role === 'graduation'
      };
      // ...
    }
  } catch (e) { console.warn('[Session Check Failed]', e); }
  
  // 回退到 localStorage
  if (!user) { user = getSessionUser(); }
  // ...
}
```
- 用户文件表初始化：
```javascript
// js/files-core.js:36
async function ensureUserTable(username) {
  const res = await fetch("/api/files.php", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username })
  });
  if (res.ok) {
    const data = await res.json();
    if (data && data.ok) {
      showMessage(data.created ? "已创建用户文件表" : "用户文件表已存在", "success");
    } else {
      showMessage("初始化失败", "error");
    }
  } else {
    showMessage("服务不可用：初始化失败", "error");
  }
}
```

---

## 模块二：文件管理（普通用户）
用户私有网盘功能，支持文件与文件夹的增删改查。

**功能列表**
- 上传与自动分片重试、目录上传、隐藏文件过滤
- 下载单文件、打包下载文件夹
- 新建文件夹、移动文件/文件夹、删除文件/文件夹
- 多选、批量操作、当前位置导航

**API 接口 (库: FileUploadS)**
- `POST /api/upload.php` 普通上传
- `POST /api/upload_chunk.php` 分片上传合并
- `POST /api/list.php` 文件列表
- `POST /api/mkdir.php` 新建文件夹
- `POST /api/move.php` 移动文件
- `POST /api/move_folder.php` 移动文件夹
- `POST /api/delete.php` 删除文件
- `POST /api/delete_folder.php` 删除文件夹
- `GET /api/download.php` 下载单文件
- `GET /api/download_folder.php` 打包下载文件夹

**核心代码索引**
- 分片上传核心逻辑：
```javascript
// js/upload.js
async function uploadFileChunked(file, username, dir, chunkSize = 2 * 1024 * 1024, onProgress) {
  const total = Math.ceil(file.size / chunkSize) || 1;
  const uploadId = genUploadId();
  for (let i = 0; i < total; i++) {
    const start = i * chunkSize;
    const end = Math.min(file.size, start + chunkSize);
    const blob = file.slice(start, end);
    const fd = new FormData();
    // ...参数追加...
    const res = await fetch('/api/upload_chunk.php', { method: 'POST', body: fd });
    // ...错误处理与进度回调...
  }
  return { ok: false, name: file.name, error: '未知错误' };
}
```
- 文件列表渲染：
```javascript
// js/files-list.js:12
async function fetchList(username, dir = '') {
  // ...
  const res = await fetch("/api/list.php", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, dir })
  });
  // ...数据解析与渲染...
  const items = Array.isArray(data.items) ? data.items : [];
  const folders = Array.isArray(data.folders) ? data.folders : [];
  // ...
  renderFolderRows(folders).forEach(el => frag.appendChild(el));
  renderFileRows(items).forEach(el => frag.appendChild(el));
  // ...
}
```

---

## 模块三：毕业提交（毕业生）
专为毕业生设计的提交系统，支持多达 13 种文档类型的提交与管理。

**功能列表**
- 提交毕业论文、实习证明、安全责任书等 13 种文档
- 支持分片上传、进度条显示、断点续传
- 显示“已提交文件名”、最后提交时间
- “更新提交”：自动替换原文件并删除旧文件

**API 接口 (库: Graduation)**
- `POST /api/upload_universal.php` 通用分片上传（支持所有类型）
- `GET /api/download_universal.php` 通用下载接口
- `GET /api/get_my_status.php` 获取个人提交状态
- `GET /api/filestat_list.php` 个人状态查询（兼容）

**核心代码索引**
- 通用分片上传逻辑：
```javascript
// js/files-graduation.js:162
async function uploadGenericChunked(apiPath, file, username, replace, fileType, onProgress) {
  const total = Math.ceil(file.size / CHUNK_SIZE) || 1;
  const uploadId = `${Date.now()}-${Math.random().toString(36).slice(2,10)}`;
  for (let i = 0; i < total; i++) {
    const start = i * CHUNK_SIZE;
    const end = Math.min(file.size, start + CHUNK_SIZE);
    const blob = file.slice(start, end);
    const fd = new FormData();
    fd.append('username', username);
    fd.append('studentID', username);
    fd.append('filename', file.name);
    fd.append('upload_id', uploadId);
    fd.append('chunk_index', String(i));
    fd.append('total_chunks', String(total));
    fd.append('replace', replace ? '1' : '0');
    if (fileType) fd.append('file_type', fileType); // 关键：指定文件类型
    fd.append('chunk', blob, `${file.name}.part${i}`);
    
    const res = await fetch(apiPath, { method: 'POST', credentials: 'include', body: fd });
    if (!res.ok) return false;
    if (onProgress) onProgress((i + 1) / total);
  }
  return true;
}
```
- 配置化模块渲染（Vue）：
```javascript
// js/files-graduation.js:12
const moduleConfig = [
  { id: 'grad', title: '自行联系岗位实习单位申请表提交', fileType: 'thesis', ... },
  { id: 'intern', title: '学生岗位三方协议书提交', fileType: 'internship', ... },
  // ...共 13 种类型
];
```

---

## 模块四：共享文件管理
支持用户间文件共享与协作浏览。

**功能列表**
- 文件/文件夹共享（递归）
- 共享列表层级浏览（支持进入子目录）
- 双击进入目录或下载文件
- 打包下载共享文件夹

**API 接口**
- `POST /api/toggle_public.php` 切换共享状态
- `GET/POST /api/list_shared.php` 获取共享列表（支持子目录浏览）

**核心代码索引**
- 共享列表渲染与层级浏览：
```javascript
// js/files-shared.js:17
async function fetchSharedList(targetUser = '', dir = '') {
  // ...
  // 如果是根目录浏览模式（无 targetUser），用 GET；如果是子目录浏览，用 POST 传参
  if (targetUser) {
    options = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ target_user: targetUser, dir: dir })
    };
  } else {
    options = { method: "GET", credentials: "include" };
  }

  const res = await fetch(url, options);
  // ...渲染逻辑...
  if (it.type === 'folder') {
     // ...双击进入文件夹...
     tr.addEventListener('dblclick', () => {
        fetchSharedList(it.username, it.path || it.name);
     });
  }
  // ...
}
```

---

## 模块五：教师端管理
教师专用后台，用于管理班级与审核文件。

**功能列表**
- **班级管理**：导入/新增/删除/编辑班级名册
- **文件统计**：
  - 筛选未提交（12 种类型任意筛选，**审核不通过视为未提交**）
  - 多选导出 Excel（学号/姓名/班级/未交项）
  - 打回文件（删除并清空状态）
- **审批批阅**：
  - 在线预览 Word/Excel/PDF
  - 快捷审批（通过/不通过按钮），自动跳转下一个待办
  - 智能导航：仅显示未审批项，支持“上一个/下一个”切换
  - 实时数据同步：审批结果立即反映在列表，支持自动刷新
- **文件管理**：
  - 班级→学生→文件 三级浏览
  - 下载班级/学生/子文件夹压缩包（自动规范命名）

**API 接口 (库: Graduation)**
- `GET /api/teacher_stats.php` 统计总览
- `POST /api/reject_universal.php` 通用打回接口
- `GET /api/class_list.php` 等班级管理接口
- `POST /api/graduation_list.php` 列目录
- `GET /api/graduation_download_*.php` 系列打包下载接口
- `POST /api/review/result/update.php` 更新审批结果

**核心代码索引**
- 统计表渲染与筛选：
```javascript
// js/teacher-filestat.js:57
function renderFileStatTable() {
  // ...
  const arr = fsState.items.filter(it => {
    // ...多条件筛选逻辑...
    if (fsState.status === 'submitted') {
      if (fsState.view === 'thesis') okStatus = thSub;
      else if (fsState.view === 'internship') okStatus = inSub;
      // ...支持所有类型筛选
    }
    // ...
  });
  // ...
  arr.forEach(it => {
    // ...动态生成行 HTML...
    tr.innerHTML = `...<button class="btn-link danger" data-action="reject-thesis" ...>打回申请表</button>...`;
  });
  // ...绑定打回事件...
  tbody.querySelectorAll('button[data-action^="reject-"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      // ...调用 reject_universal.php ...
    });
  });
}
```

---

## 数据库结构

### 1. 主应用库 (`FileUpload`)
配置于 `config/mysql.ini`

**表名：Users (普通用户表)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | bigint unsigned | 主键，自增 |
| `username` | varchar(64) | 用户名（学号） |
| `password` | varchar(255) | 密码（哈希存储） |
| `created_at` | timestamp | 创建时间 |
| `last_login_at` | timestamp | 最后登录时间 |

**表名：admins (管理员/教师表)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | bigint unsigned | 主键，自增 |
| `username` | varchar(64) | 管理员用户名 |
| `class` | varchar(64) | 管理的班级（如有） |
| `password` | varchar(255) | 密码 |
| `created_at` | timestamp | 创建时间 |
| `last_login_at` | timestamp | 最后登录时间 |

**表名：Settings (用户设置表)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | bigint unsigned | 主键，自增 |
| `user` | varchar(64) | 关联用户名 |
| `HomepageSettings` | varchar(32) | 默认首页（list/upload/graduation等） |
| `HiddenFile` | tinyint(1) | 上传时是否跳过隐藏文件 |
| `ShowHiddenFiles` | tinyint(1) | 列表中是否显示隐藏文件 |

### 2. 用户文件库 (`FileUploadS`)
配置于 `config/mysql_files.ini`

**表名：user_{username} (动态分表)**
*每个用户对应一张独立表，例如 `user_2020001`*

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | bigint unsigned | 主键，自增 |
| `file_path` | varchar(1024) | 文件相对路径 |
| `is_public` | tinyint(1) | 是否共享 (0:私有, 1:共享) |
| `upload_at` | timestamp | 上传时间 |
| `last_download_at` | timestamp | 最后下载时间 |

### 3. 毕业生信息表 (`graduation_information`)
已合并至主库 `FileUpload`（旧版 `FileUploadGraduationSubmission.Users` 已废弃）

**表名：graduation_information (毕业生信息与提交状态表)**

基础字段：
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `ID` | bigint unsigned | 主键，自增 |
| `studentID` | varchar(32) | 学号 |
| `name` | varchar(64) | 姓名 |
| `class` | varchar(64) | 班级 |

文档类型字段（共 13 组，每组包含 4 个字段）：
*以“岗位实习单位申请表”为例，其他类型同理*

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `Application Form for Internship Unit` | varchar(255) | 文件路径 |
| `Application Form for Internship Unit Final Submission Time` | datetime | 最后提交时间 |
| `Application Form for Internship Unit download time` | datetime | 最近下载时间 |
| `Application Form for Internship Unit download count` | int unsigned | 下载次数 |

**支持的文档类型**：
1. 岗位实习单位申请表 (`thesis`)
2. 学生岗位三方协议书 (`internship`)
3. 实习单位意见 (`opinion`)
4. 实习自主住宿承诺书及家长意见 (`commitment`)
5. 家长意见 (`parental`)
6. 丙方实习岗位实习法定监护人（或家长）知情同意书 (`guardian`)
7. 学生实习企业考察报告表 (`report`)
8. 学生实习企业考察情况汇总表 (`summary`)
9. 企业营业执照 (`license`)
10. 企业信用报告 (`credit`)
11. 毕业实习安全责任书 (`safety`)
12. 岗位实习报告及考核表 (`assessment`)
13. 实习学生信息及指导教师名单汇总表 (`names_summary`)

**注**：所有页面底部已添加备案号：[浙ICP备2024065828号](https://beian.miit.gov.cn/)

---

## 快速开始
1. **环境准备**：PHP >= 7.4（已兼容 PHP 8.4+）, MySQL >= 5.7
2. **启动服务**：
   ```bash
   php -S localhost:8000 -t .
   ```
3. **访问**：
   - 登录：`http://localhost:8000/index.html`
   - 文件：`http://localhost:8000/files.html`

---

## 待改进项

### 一、安全性问题（高优先级）

| 问题 | 说明 | 建议方案 | 状态 |
| :--- | :--- | :--- | :--- |
| **身份验证机制薛弱** | 使用 localStorage 存储用户信息，无服务端 Session/Token 验证；API 接口只验证用户名存在，未验证请求者身份 | 引入 JWT Token 或 PHP Session 机制 | ✅ 已解决 |
| **密码重置无验证** | `reset_password.php` 任何人只需知道用户名即可重置密码，无需任何身份验证 | 增加邮箱/手机验证码，或要求管理员审批 | 待处理 |
| **毕业生登录无密码** | `graduation_login.php` 只需学号即可登录，无任何认证 | 至少增加简单密码或动态验证码 | 待处理 |
| **CORS 配置过宽** | 所有 API 都设置 `Access-Control-Allow-Origin: *`，允许任意来源 | 生产环境限制为具体域名 | 部分解决 |

### 二、架构设计问题

#### 1. 代码重复严重 - 已解决 ✅

**问题**：分片上传逻辑在多个接口中重复
- `upload_chunk.php` - 普通文件分片上传
- `graduation_chunk.php` - 毕业论文分片上传  
- `internship_chunk.php` - 实习证明分片上传

**解决方案**：创建 `ChunkUploader` 公共类

**实现详情**：

新增文件 [`api/ChunkUploader.php`](file:///var/www/html/FileUpload/api/ChunkUploader.php) （311 行），统一处理：

```php
/**
 * 分片上传公共类 - 统一处理分片上传的通用逻辑
 * 功能：
 * - 参数验证（用户名、分片索引、文件名等）
 * - 分片保存（创建临时目录、保存分片文件）
 * - 分片合并（合并所有分片、清理临时文件）
 * - 回调机制（支持自定义文件名生成、合并完成处理）
 */
class ChunkUploader {
    // 静态方法：通用操作
    public static function setHeaders(): void         // 设置响应头
    public static function handleOptions(): bool      // 处理 OPTIONS 预检
    public static function validateMethod(): bool     // 验证 POST 方法
    public static function parseParams(): ?array      // 解析并验证参数
    public static function success(array $data)       // 输出成功响应
    public static function error(int $code, string $msg) // 输出错误响应
    
    // 实例方法：业务流程
    public function __construct(array $params, string $storageFolder, string $subDir = '')
    public function setFinalNameGenerator(callable $callback)   // 设置文件名生成回调
    public function setMergeCompleteCallback(callable $callback) // 设置合并完成回调
    public function handle(): bool                   // 处理上传（保存→合并→回调）
}
```

**改进前后对比**：

| 指标 | 改进前 | 改进后 | 效果 |
| :--- | :--- | :--- | :--- |
| 代码行数 | 400+ 行（三文件） | 311 行（共享类） + 70 行（各接口） | 减少 20% |
| 分片参数验证 | 3 处独立验证逻辑 | 1 处共享验证 | 避免重复 |
| 错误处理 | 每个接口单独处理 | 统一通过 `ChunkUploader::error()` | 易维护 |
| 文件合并逻辑 | 3 处重复 | 1 处实现 | 修复 bug 更便捷 |

**新接口使用示例**：

```php
// api/upload_chunk.php
require_once __DIR__ . '/ChunkUploader.php';

// 1. 设置响应头与验证
ChunkUploader::setHeaders();
ChunkUploader::handleOptions();
ChunkUploader::validateMethod();

// 2. 解析参数
$params = ChunkUploader::parseParams();
if ($params === null) exit; // 验证失败已输出错误

// 3. 创建上传器
$uploader = new ChunkUploader($params, 'File', $params['dir']);

// 4. 注册合并完成回调（业务逻辑）
$uploader->setMergeCompleteCallback(function(string $finalPath, string $relativePath) use ($params) {
    // 写入数据库、发送通知等业务逻辑
    $filesDb = getFilesDb();
    $table = ensureUserTable($filesDb, $params['username']);
    $stmt = $filesDb->prepare("INSERT INTO `{$table}` (file_path) VALUES (?)");
    $stmt->bind_param('s', $relative);
    $stmt->execute();
    
    ChunkUploader::success(['path' => $relative]);
});

// 5. 处理请求（保存→合并→调用回调）
$uploader->handle();
```

**毕业论文上传的特殊处理**：

```php
// api/graduation_chunk.php
$uploader = new ChunkUploader($params, 'FileUploadGraduationSubmission');

// 设置自定义文件名生成（学号_姓名_类型）
$uploader->setFinalNameGenerator(function(string $filename) use ($studentID) {
    return generateGraduationFileName($studentID, $filename, '毕业设计论文');
});

// 设置替换时删除旧文件
$uploader->setMergeCompleteCallback(function(string $finalPath, string $relativePath) use ($params, $uploader) {
    $db = getGraduationDb();
    
    // 如果是替换模式，删除旧文件
    if ($uploader->isReplace()) {
        deleteOldGraduationFile($db, $studentID, 'Graduation Thesis', $relativePath, $uploader->getRoot());
    }
    
    // 更新数据库
    $stmt = $db->prepare('UPDATE `Users` SET `Graduation Thesis` = ?, `Graduation Thesis Final Submission Time` = NOW() WHERE `studentID` = ?');
    $stmt->bind_param('ss', $relativePath, $studentID);
    $stmt->execute();
});

$uploader->handle();
```

**关键优势**：
1. ✅ **减少重复代码** - 参数验证、分片保存、合并逻辑集中在一个类中
2. ✅ **灵活的回调机制** - 支持自定义文件名、自定义数据库操作
3. ✅ **易于维护** - 修复分片上传的 bug 只需改一个地方
4. ✅ **易于测试** - 公共逻辑可独立单元测试
5. ✅ **易于扩展** - 添加新的分片上传类型只需注册回调

---

#### 2. 其他架构问题 - 部分已解决 ✅

| 问题 | 说明 | 建议方案 | 状态 |
| :--- | :--- | :--- | :--- |
| **前端 JS 文件过大** | `files.js` 有 1685 行，职责不清晰 | 按功能模块拆分 | 待处理 |
| **缺少统一错误处理** | 每个 API 都独立处理错误，格式不完全统一 | 统一响应函数 + 日志记录 | ✅ 已解决 |
| **数据库连接无复用** | 每次请求都新建数据库连接 | 使用单例模式 | ✅ 已解决 |

**统一错误处理实现**：

已在 `util.php` 中添加日志记录功能，所有服务器错误自动记录到 `logs/` 目录：

```php
// 日志记录函数
function logDebug(string $msg, array $ctx = [])    // 调试日志
function logInfo(string $msg, array $ctx = [])     // 信息日志
function logWarning(string $msg, array $ctx = [])  // 警告日志
function logError(string $msg, array $ctx = [])    // 错误日志
function logException(Throwable $e, string $prefix) // 异常日志
```

日志格式示例：
```
[2025-12-25 14:30:00] [ERROR] [a1b2c3d4] API Error: Connection refused {"exception":"mysqli_sql_exception","file":"..."}
```

**数据库连接复用实现**：

新增 [`api/Database.php`](api/Database.php) 单例类，统一管理三个数据库的连接：

```php
class Database {
    // 获取各库连接（单例模式，同一请求内复用）
    public static function getMain(): mysqli       // 主库 FileUpload
    public static function getFiles(): mysqli      // 文件库 FileUploadS
    public static function getGraduation(): mysqli // 毕业库
    
    // 连接管理
    public static function closeAll(): void        // 关闭所有连接
    public static function hasConnection($type): bool // 检查连接状态
}
```

**关键特性**：
- ✅ **连接复用** - 同一请求内多次调用返回同一连接
- ✅ **延迟加载** - 只在需要时才建立连接
- ✅ **自动清理** - 脚本结束时自动关闭所有连接
- ✅ **断线重连** - 检测到连接失效时自动重建
- ✅ **向后兼容** - 原有 `getDb()` 等函数仍可用

---

### 三、代码质量问题 - 已解决 ✅

**已修复的问题：**

| 问题 | 原状态 | 解决方案 |
| :--- | :--- | :--- |
| **SQL 注入风险** | `toggle_public.php` 中直接拼接 SQL 字符串 | 改用预处理语句 `prepare/bind_param` |
| **重复的 CORS/方法检查代码** | 每个 API 都有 15+ 行相同的头设置代码 | 提取到 `util.php` 的 `initApiRequest()` 函数 |
| **JSON 响应格式不统一** | 有时 `['ok'=>true]`，有时 `['error'=>...]` | 统一使用 `jsonSuccess()` 和 `jsonError()` |
| **用户验证逻辑分散** | 多处重复的用户存在性验证代码 | 提取为 `requireUserExists()` 函数 |
| **重复的 require_once** | `graduation_upload.php` 中重复引入同一文件 | 已删除重复行 |

**新增统一辅助函数** ([`api/util.php`](api/util.php))：

```php
// 响应处理
function setApiHeaders(string $methods)     // 设置 CORS + JSON 头
function handleOptionsRequest()             // 处理 OPTIONS 预检
function requireMethod($allowed)            // 检查请求方法
function initApiRequest(string $methods)    // 一体化初始化
function jsonSuccess(array $data = [])      // 统一成功响应
function jsonError(string $msg, int $code)  // 统一错误响应
function jsonServerError(Throwable $e)      // 统一服务器错误

// 输入解析
function parseRequestBody(): array          // 解析 JSON/表单请求体
function validateUsername(string $u)        // 验证用户名格式
function requireUserExists(string $u): int  // 验证用户是否存在
```

**改进前后对比**：

| 文件 | 改进前行数 | 改进后行数 | 减少 | 备注 |
| :--- | :--- | :--- | :--- | :--- |
| `delete.php` | 66 | 50 | -25% | |
| `move.php` | 95 | 77 | -19% | |
| `mkdir.php` | 86 | 49 | -43% | |
| `delete_folder.php` | 90 | 68 | -24% | |
| `move_folder.php` | 93 | 69 | -26% | |
| `toggle_public.php` | 139 | 104 | -25% | |
| `admin_login.php` | 40 | 28 | -30% | |
| `list_shared.php` | 347 | 341 | -2% | |
| `change_password.php` | 68 | 42 | -38% | |
| `download.php` | 74 | 57 | -23% | |
| `download_folder.php` | 121 | 94 | -22% | |
| `files.php` | 89 | 60 | -33% | 删除重复的 sanitizeUserFragment |
| `list.php` | 169 | 132 | -22% | |
| `class_add.php` | 36 | 43 | +19% | 格式化+可读性 |
| `class_delete.php` | 20 | 23 | +15% | 格式化+可读性 |
| `class_get.php` | 25 | 29 | +16% | 格式化+可读性 |
| `class_bulk_delete.php` | 25 | 31 | +24% | 格式化+可读性 |
| `class_import.php` | 96 | 141 | +47% | 格式化+可读性 |
| `class_list.php` | 19 | 33 | +74% | 格式化+可读性 |
| `class_update.php` | 36 | 43 | +19% | 格式化+可读性 |

> **注**：部分文件行数增加是因为将压缩的单行代码展开为多行，提高了可读性和可维护性。

**关键优势**：
1. ✅ **代码一致性** - 所有 20+ 个 API 响应格式统一为 `{ok: true/false, ...}`
2. ✅ **安全性提升** - SQL 注入风险已修复
3. ✅ **可维护性** - 通用逻辑集中在 `util.php`，后续修改只需一处
4. ✅ **代码量减少** - 核心文件总计减少约 350+ 行重复代码
5. ✅ **可读性提升** - 所有文件统一缩进和格式化
6. ✅ **表名白名单校验** - 新增 `isValidTableName()` 和 `getSafeTableName()` 函数
7. ✅ **异常信息脱敏** - 生产环境 (`APP_ENV=production`) 自动隐藏详细错误
8. ✅ **常量配置** - 分片大小等魔法数字提取为 `CHUNK_SIZE` 常量
9. ✅ **PHP 8.4 兼容** - 修复已废弃的 `mysqli::ping()` 方法
10. ✅ **全局错误处理器** - 所有 PHP 错误输出为 JSON，禁止 HTML 错误页面
11. ✅ **表单 autocomplete** - 所有输入框添加 autocomplete 属性
12. ✅ **PHP Session 认证** - 完整的服务端会话管理机制

---

#### 3. 表名白名单校验 - 已解决 ✅

**问题**：`ensureUserTable()` 中表名直接拼接到 SQL 语句，虽已验证用户名格式但模式存在隐患

**解决方案**：新增白名单校验函数

```php
// api/util.php

/**
 * 验证表名格式是否安全（白名单校验）
 * 只允许 user_ + 纯数字 格式的表名
 */
function isValidTableName(string $table): bool {
  return (bool)preg_match('/^user_[0-9]+$/', $table);
}

/**
 * 获取安全的用户表名
 * @throws InvalidArgumentException 如果用户名格式不合法
 */
function getSafeTableName(string $username): string {
  if (!preg_match('/^[0-9]+$/', $username)) {
    throw new InvalidArgumentException('用户名必须为纯数字');
  }
  $table = 'user_' . $username;
  if (!isValidTableName($table)) {
    throw new InvalidArgumentException('生成的表名格式不合法');
  }
  return $table;
}
```

---

#### 4. 异常信息脱敏 - 已解决 ✅

**问题**：生产环境中 `$e->getMessage()` 直接返回给前端，可能泄露敏感信息

**解决方案**：根据环境变量自动决定是否显示详细错误

```php
// api/util.php

// 环境配置 - 通过环境变量 APP_ENV=production 设置
define('IS_PRODUCTION', getenv('APP_ENV') === 'production');

/**
 * 返回服务器内部错误
 * @param bool|null $includeDetail null 表示根据环境自动决定
 */
function jsonServerError(Throwable $e, ?bool $includeDetail = null): void {
    logException($e, 'API Error');  // 始终记录日志
    
    if ($includeDetail === null) {
        $includeDetail = !IS_PRODUCTION;  // 生产环境自动隐藏
    }
    
    $extra = $includeDetail ? ['detail' => $e->getMessage()] : [];
    jsonError('服务器内部错误', 500, $extra);
}
```

**使用方式**：
```bash
# 开发环境（显示详细错误）
php -S localhost:8000

# 生产环境（隐藏详细错误）
APP_ENV=production php -S 0.0.0.0:8000
```

---

#### 5. 魔法数字常量化 - 已解决 ✅

**问题**：分片大小 `2 * 1024 * 1024` 等魔法数字散落在代码中，难以统一维护

**解决方案**：提取为常量

```php
// api/util.php
define('CHUNK_SIZE', 2 * 1024 * 1024);     // 2MB
define('CHUNK_SIZE_MB', 2);                 // 可读格式
```

```javascript
// js/upload.js
const CHUNK_SIZE = 2 * 1024 * 1024;  // 2MB

// js/files-core.js
const FILE_CHUNK_SIZE = 2 * 1024 * 1024;  // 2MB
```

**修改后可统一调整分片大小**：只需修改常量定义即可影响所有分片上传功能

---

#### 6. 全局错误处理器 - 已解决 ✅

**问题**：PHP 错误/警告直接输出 HTML 导致前端 JSON 解析失败

**解决方案**：在 `util.php` 中注册全局错误处理器

```php
// api/util.php

// 禁止 PHP 直接输出错误到页面
ini_set('display_errors', '0');
ini_set('display_startup_errors', '0');
error_reporting(E_ALL);

// 注册全局错误处理器
set_error_handler(function($errno, $errstr, $errfile, $errline) {
    // 记录到日志，不输出到页面
    $logFile = __DIR__ . '/../logs/php_errors_' . date('Y-m-d') . '.log';
    @file_put_contents($logFile, sprintf("[%s] Error: %s in %s:%d\n", 
        date('Y-m-d H:i:s'), $errstr, $errfile, $errline), FILE_APPEND);
    return true;
});

// 注册全局异常处理器
set_exception_handler(function($e) {
    // 输出 JSON 错误响应
    header('Content-Type: application/json; charset=utf-8');
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => '服务器内部错误']);
    exit;
});

// 处理致命错误
register_shutdown_function(function() {
    $error = error_get_last();
    if ($error && in_array($error['type'], [E_ERROR, E_PARSE])) {
        if (ob_get_level()) ob_end_clean();
        header('Content-Type: application/json; charset=utf-8');
        http_response_code(500);
        echo json_encode(['ok' => false, 'error' => '服务器内部错误']);
    }
});
```

**关键特性**：
- ✅ **统一 JSON 响应** - 所有错误都返回 `{"ok": false, "error": "..."}`
- ✅ **日志记录** - 错误记录到 `logs/php_errors_YYYY-MM-DD.log`
- ✅ **安全脱敏** - 不向前端泄露服务器详细错误信息

---

#### 7. PHP 8.4 兼容性 - 已解决 ✅

**问题**：`mysqli::ping()` 在 PHP 8.4 中已废弃，会输出 Deprecation 警告

**解决方案**：用简单查询代替 `ping()` 方法

```php
// api/Database.php

// 改进前（PHP 8.4 废弃警告）
if ($conn->ping()) {
    return $conn;
}

// 改进后（PHP 8.4+ 兼容）
try {
    $conn->query('SELECT 1');
    return $conn;
} catch (Throwable $e) {
    @$conn->close();
    unset(self::$instances[$type]);
}
```

---

#### 8. 表单 autocomplete 属性 - 已解决 ✅

**问题**：输入框缺少 `autocomplete` 属性，浏览器控制台警告

**解决方案**：所有表单输入框添加适当的 `autocomplete` 属性

```html
<!-- index.html -->
<input id="login-username" name="login_username" autocomplete="username" />
<input id="login-password" name="login_password" autocomplete="current-password" />
<input id="register-password" autocomplete="new-password" />
```

**改进点**：
- ✅ 每个表单使用独立的 `name` 属性，避免浏览器自动填充混淆
- ✅ 符合 HTML5 无障碍和用户体验标准

---

#### 9. PHP Session 认证 - 已解决 ✅

**问题**：使用 localStorage 存储用户信息，无服务端 Session 验证，API 只验证用户名存在

**解决方案**：引入完整的 PHP Session 认证机制

**Session 配置** (`api/util.php`)：
```php
// Session 常量
define('SESSION_LIFETIME', 7200);      // 2 小时有效期
define('SESSION_NAME', 'FUSESSION');   // Session Cookie 名称

// 安全配置
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
ini_set('session.cookie_httponly', '1');
session_set_cookie_params([
    'lifetime' => SESSION_LIFETIME,
    'path' => '/',
    'httponly' => true,
    'samesite' => 'Lax'
]);
```

**核心函数**：
```php
// 创建 Session（登录时调用）
function sessionLogin(int $userId, string $username, string $role = 'user'): void

// 销毁 Session（登出时调用）
function sessionLogout(): void

// 检查是否已登录
function isLoggedIn(): bool

// 获取当前用户信息
function getCurrentUser(): ?array

// 要求必须登录（未登录返回 401）
function requireAuth(array $allowedRoles = []): array

// 渐进式认证：优先 Session，回退到请求参数（向后兼容）
function getAuthenticatedUser(?string $requestUsername = null): string
```

**新增 API 接口**：
- `POST /api/logout.php` - 登出并销毁 Session
- `GET /api/check_session.php` - 检查当前 Session 状态

**前端集成** (`js/utils.js`)：
```javascript
// API 请求工具（自动携带 Session Cookie）
function apiPost(url, data = {}) {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',  // 关键！携带 Cookie
    body: JSON.stringify(data)
  });
}

// 检查 Session 状态
async function checkSession() {
  const res = await apiGet('/api/check_session.php');
  return res.ok ? await res.json() : { loggedIn: false };
}

// 登出
async function logout() {
  await apiPost('/api/logout.php');
  localStorage.removeItem('currentUser');
}
```

**关键特性**：
- ✅ **服务端验证** - Session 存储在服务器，无法伪造
- ✅ **自动过期** - 2 小时不活动自动登出
- ✅ **安全 Cookie** - HttpOnly + SameSite 防止 XSS/CSRF
- ✅ **向后兼容** - 已登录用户优先 Session，否则回退到 localStorage
- ✅ **角色支持** - user/admin/graduation 三种角色
- ✅ **防固定攻击** - 登录时重生 Session ID

---

### 四、功能性改进

| 建议 | 说明 |
| :--- | :--- |
| **文件类型限制** | 当前允许上传任意文件，应限制危险类型（如 `.php`、`.exe`） |
| **文件大小限制** | 前端已有检测，后端应增加强制限制 |
| **操作日志** | ✅ 已实现审计日志系统 |
| **断点续传** | ✅ 已实现分片断点续传 |
| **文件去重** | 相同文件重复上传浪费空间（可用 hash 检测） |
| **批量下载进度** | 大文件夹打包下载无进度提示 |

### 五、用户体验改进

| 建议 | 说明 |
| :--- | :--- |
| **移动端适配** | ✅ 已实现响应式 CSS，支持平板和手机 |
| **拖拽上传** | 仅毕业提交支持拖拽，文件管理未支持 |
| **键盘导航** | 文件列表缺少键盘操作支持 |
| **撤销操作** | 删除等危险操作无法恢复 |
| **国际化** | 硬编码中文，难以扩展多语言 |

### 六、运维与部署

| 建议 | 说明 | 状态 |
| :--- | :--- | :--- |
| **配置分离** | 敏感配置（如数据库密码）建议使用环境变量 | 待处理 |
| **健康检查** | 缺少 `/health` 接口供监控 | 待处理 |
| **日志记录** | 无统一日志系统，排查问题困难 | ✅ 已解决 |
| **Rate Limiting** | 无请求频率限制，易受攻击 | 待处理 |

### 改进优先级

| 优先级 | 改进项 | 状态 |
| :--- | :--- | :--- |
| **P0** | 身份验证机制、密码重置安全 | Session 认证已完成 ✅，密码重置待处理 |
| **P1** | 文件类型限制、CORS 限制 | 待处理 |
| **P1** | SQL 表名白名单校验、异常信息脱敏、分片常量化 | 已完成 ✅ |
| **P2** | 代码重构（分片上传抽象、前端模块化） | 分片上传已完成 ✅ |
| **P2** | 代码质量（统一响应、SQL 注入修复） | 已完成 ✅ |
| **P2** | 数据库连接复用、统一错误处理、日志记录 | 已完成 ✅ |
| **P3** | 审计日志、断点续传、移动端适配 | 已完成 ✅ |
| **P3** | PHP 8.4 兼容、全局错误处理、表单 autocomplete | 已完成 ✅ |
