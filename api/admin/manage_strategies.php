<?php
/**
 * 攻略管理页面（后台）
 * 支持攻略的增删改查操作
 */

require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

checkAuth();

$db = getDB();
$action = isset($_GET['action']) ? $_GET['action'] : 'list';
$message = '';
$messageType = '';

// ========== 处理表单提交 ==========

if ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'add') {
    $name = sanitizeInput($_POST['name'] ?? '');
    $category = sanitizeInput($_POST['category'] ?? '');
    $description = sanitizeInput($_POST['description'] ?? '');
    $detail_content = $_POST['detail_content'] ?? '';
    $sort_order = intval($_POST['sort_order'] ?? 0);

    if (empty($name) || empty($category)) {
        $message = '名称和分类不能为空';
        $messageType = 'error';
    } else {
        $imagePath = '';
        if (isset($_FILES['image']) && $_FILES['image']['error'] === UPLOAD_ERR_OK) {
            $uploaded = handleImageUpload($_FILES['image'], '../../images/strategy/');
            if ($uploaded) {
                $imagePath = str_replace('../../', '', $uploaded);
            } else {
                $message = '图片上传失败';
                $messageType = 'error';
            }
        }
        if ($messageType !== 'error') {
            $stmt = $db->prepare("INSERT INTO strategies (name, category, description, image, detail_content, sort_order) VALUES (:name, :category, :description, :image, :detail_content, :sort_order)");
            $stmt->execute([':name' => $name, ':category' => $category, ':description' => $description, ':image' => $imagePath, ':detail_content' => $detail_content, ':sort_order' => $sort_order]);
            $message = '攻略添加成功';
            $messageType = 'success';
            $action = 'list';
        }
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'edit') {
    $id = intval($_POST['id'] ?? 0);
    $name = sanitizeInput($_POST['name'] ?? '');
    $category = sanitizeInput($_POST['category'] ?? '');
    $description = sanitizeInput($_POST['description'] ?? '');
    $detail_content = $_POST['detail_content'] ?? '';
    $sort_order = intval($_POST['sort_order'] ?? 0);

    if ($id <= 0 || empty($name) || empty($category)) {
        $message = '参数错误';
        $messageType = 'error';
    } else {
        $imageClause = '';
        $params = [':name' => $name, ':category' => $category, ':description' => $description, ':detail_content' => $detail_content, ':sort_order' => $sort_order, ':id' => $id];
        if (isset($_FILES['image']) && $_FILES['image']['error'] === UPLOAD_ERR_OK) {
            $uploaded = handleImageUpload($_FILES['image'], '../../images/strategy/');
            if ($uploaded) {
                $imageClause = ', image = :image';
                $params[':image'] = str_replace('../../', '', $uploaded);
            }
        }
        $sql = "UPDATE strategies SET name = :name, category = :category, description = :description, detail_content = :detail_content, sort_order = :sort_order $imageClause WHERE id = :id";
        $stmt = $db->prepare($sql);
        $stmt->execute($params);
        $message = '攻略更新成功';
        $messageType = 'success';
        $action = 'list';
    }
}

if ($action === 'delete' && isset($_GET['id'])) {
    $id = intval($_GET['id']);
    if ($id > 0) {
        $stmt = $db->prepare("DELETE FROM strategies WHERE id = :id");
        $stmt->execute([':id' => $id]);
        $message = '已删除';
        $messageType = 'success';
    }
    $action = 'list';
}

// ========== 获取数据 ==========
$editItem = null;
if ($action === 'edit' && isset($_GET['id'])) {
    $stmt = $db->prepare("SELECT * FROM strategies WHERE id = :id");
    $stmt->execute([':id' => intval($_GET['id'])]);
    $editItem = $stmt->fetch();
    if (!$editItem) { $message = '不存在'; $messageType = 'error'; $action = 'list'; }
}

$items = [];
$searchKeyword = isset($_GET['keyword']) ? sanitizeInput($_GET['keyword']) : '';
$searchCategory = isset($_GET['cat']) ? sanitizeInput($_GET['cat']) : '';

if ($action === 'list') {
    $where = []; $params = [];
    if (!empty($searchKeyword)) {
        $where[] = '(name LIKE :kw1 OR description LIKE :kw2)';
        $params[':kw1'] = '%' . $searchKeyword . '%';
        $params[':kw2'] = '%' . $searchKeyword . '%';
    }
    if (!empty($searchCategory)) { $where[] = 'category = :cat'; $params[':cat'] = $searchCategory; }
    $whereClause = !empty($where) ? 'WHERE ' . implode(' AND ', $where) : '';
    $stmt = $db->prepare("SELECT * FROM strategies $whereClause ORDER BY sort_order ASC, id DESC");
    $stmt->execute($params);
    $items = $stmt->fetchAll();
}

$categories = ['行程规划', '攻略指南', '实用贴士'];
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>攻略管理 — 宁波旅游后台</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #F5EDE2; color: #2C1810; line-height: 1.6; }
        .admin-header { background: #2C1810; color: #fff; padding: 0 24px; height: 60px; display: flex; align-items: center; justify-content: space-between; }
        .admin-header__brand { font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
        .admin-header__icon { width: 32px; height: 32px; background: #B8763E; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
        .admin-header__nav { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
        .admin-header__nav a { color: rgba(255,255,255,0.7); text-decoration: none; font-size: 14px; padding: 6px 14px; border-radius: 6px; transition: all 0.2s; }
        .admin-header__nav a:hover, .admin-header__nav a.active { color: #fff; background: rgba(255,255,255,0.1); }
        .admin-header__user { font-size: 14px; color: rgba(255,255,255,0.6); }
        .admin-header__user a { color: #D4975F; text-decoration: none; margin-left: 12px; }
        .container { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
        .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
        .page-title { font-size: 24px; font-weight: 700; }
        .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 20px; font-size: 14px; font-weight: 600; border-radius: 8px; text-decoration: none; border: none; cursor: pointer; transition: all 0.2s; font-family: inherit; }
        .btn--primary { background: #B8763E; color: #fff; } .btn--primary:hover { background: #8E5A2A; }
        .btn--danger { background: #C4584A; color: #fff; } .btn--danger:hover { background: #A33D30; }
        .btn--outline { border: 1px solid #E8DDD1; background: #fff; color: #6B5344; } .btn--outline:hover { border-color: #B8763E; color: #B8763E; }
        .btn--sm { padding: 5px 12px; font-size: 13px; }
        .alert { padding: 12px 16px; border-radius: 8px; font-size: 14px; margin-bottom: 20px; }
        .alert--success { background: #F0FDF4; color: #166534; border: 1px solid #BBF7D0; }
        .alert--error { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
        .table-wrapper { background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(44,24,16,0.06); border: 1px solid #E8DDD1; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { background: #FDFAF6; font-weight: 600; text-align: left; padding: 12px 16px; border-bottom: 1px solid #E8DDD1; color: #6B5344; font-size: 13px; }
        td { padding: 12px 16px; border-bottom: 1px solid #F0E8DE; vertical-align: middle; }
        tr:last-child td { border-bottom: none; } tr:hover td { background: rgba(184,118,62,0.03); }
        .thumb { width: 60px; height: 40px; object-fit: cover; border-radius: 6px; background: #F5EDE2; }
        .tag { display: inline-block; padding: 2px 10px; font-size: 12px; border-radius: 20px; font-weight: 500; background: rgba(61,122,95,0.1); color: #3D7A5F; }
        .actions { display: flex; gap: 8px; }
        .form-card { background: #fff; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(44,24,16,0.06); border: 1px solid #E8DDD1; max-width: 800px; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 6px; }
        .form-input, .form-select, .form-textarea { width: 100%; padding: 9px 14px; border: 2px solid #E8DDD1; border-radius: 8px; font-size: 14px; outline: none; transition: border-color 0.2s; font-family: inherit; }
        .form-input:focus, .form-select:focus, .form-textarea:focus { border-color: #B8763E; }
        .form-textarea { min-height: 100px; resize: vertical; }
        .empty { text-align: center; padding: 48px; color: #9E8C7E; font-size: 14px; }
        .search-bar { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .search-bar .form-input { max-width: 280px; padding: 8px 14px; }
        .search-bar .form-select { max-width: 160px; padding: 8px 14px; }
        .btn--search { background: #B8763E; color: #fff; padding: 8px 18px; font-size: 14px; font-weight: 600; border-radius: 8px; border: none; cursor: pointer; }
        .btn--reset { background: #fff; color: #6B5344; padding: 8px 18px; font-size: 14px; border-radius: 8px; border: 1px solid #E8DDD1; text-decoration: none; display: inline-flex; align-items: center; }
        .result-info { font-size: 13px; color: #9E8C7E; margin-bottom: 12px; }
    </style>
</head>
<body>
    <header class="admin-header">
        <div class="admin-header__brand"><img src="../../images/favicon.ico" alt="宁波旅游" style="width:32px;height:32px;border-radius:8px;object-fit:contain;"> 后台管理</div>
        <nav class="admin-header__nav">
            <a href="dashboard.php">首页</a>
            <a href="manage_spots.php">景点管理</a>
            <a href="manage_foods.php">美食管理</a>
            <a href="manage_accommodations.php">住宿管理</a>
            <a href="manage_transports.php">交通管理</a>
            <a href="manage_strategies.php" class="active">攻略管理</a>
            <a href="manage_messages.php">留言板</a>
            <a href="manage_comments.php">评论管理</a>
        </nav>
        <div class="admin-header__user">
            <?php echo htmlspecialchars($_SESSION['admin_username']); ?>
            <a href="logout.php">退出</a>
        </div>
    </header>

    <div class="container">
        <?php if ($message): ?>
            <div class="alert alert--<?php echo $messageType; ?>"><?php echo htmlspecialchars($message); ?></div>
        <?php endif; ?>

        <?php if ($action === 'list'): ?>
        <div class="page-header">
            <h1 class="page-title">攻略管理</h1>
            <a href="?action=add" class="btn btn--primary">+ 添加攻略</a>
        </div>
        <form method="GET" class="search-bar">
            <input type="text" class="form-input" name="keyword" placeholder="搜索名称/描述..." value="<?php echo htmlspecialchars($searchKeyword); ?>">
            <select class="form-select" name="cat">
                <option value="">全部分类</option>
                <?php foreach ($categories as $cat): ?>
                <option value="<?php echo $cat; ?>" <?php echo $searchCategory === $cat ? 'selected' : ''; ?>><?php echo $cat; ?></option>
                <?php endforeach; ?>
            </select>
            <button type="submit" class="btn--search">搜索</button>
            <?php if (!empty($searchKeyword) || !empty($searchCategory)): ?>
                <a href="manage_strategies.php" class="btn--reset">清除筛选</a>
            <?php endif; ?>
        </form>
        <?php if (!empty($searchKeyword) || !empty($searchCategory)): ?>
            <div class="result-info">找到 <?php echo count($items); ?> 条结果</div>
        <?php endif; ?>
        <div class="table-wrapper">
            <?php if (empty($items)): ?>
                <div class="empty">暂无数据</div>
            <?php else: ?>
            <table>
                <thead><tr><th>ID</th><th>图片</th><th>名称</th><th>分类</th><th>排序</th><th>操作</th></tr></thead>
                <tbody>
                    <?php foreach ($items as $item): ?>
                    <tr>
                        <td><?php echo $item['id']; ?></td>
                        <td><?php if ($item['image']): ?><img src="../../<?php echo htmlspecialchars($item['image']); ?>" class="thumb" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';"><div class="thumb" style="display:none;align-items:center;justify-content:center;color:#9E8C7E;">无</div><?php else: ?><div class="thumb" style="display:flex;align-items:center;justify-content:center;color:#9E8C7E;">无</div><?php endif; ?></td>
                        <td><strong><?php echo htmlspecialchars($item['name']); ?></strong></td>
                        <td><span class="tag"><?php echo htmlspecialchars($item['category']); ?></span></td>
                        <td><?php echo $item['sort_order']; ?></td>
                        <td><div class="actions">
                            <a href="?action=edit&id=<?php echo $item['id']; ?>" class="btn btn--outline btn--sm">编辑</a>
                            <a href="?action=delete&id=<?php echo $item['id']; ?>" class="btn btn--danger btn--sm" onclick="return confirm('确定删除？');">删除</a>
                        </div></td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
            <?php endif; ?>
        </div>

        <?php elseif ($action === 'add'): ?>
        <div class="page-header"><h1 class="page-title">添加攻略</h1><a href="manage_strategies.php" class="btn btn--outline">← 返回列表</a></div>
        <div class="form-card">
            <form method="POST" action="?action=add" enctype="multipart/form-data">
                <div class="form-group"><label class="form-label">名称 *</label><input type="text" class="form-input" name="name" required placeholder="例如：宁波经典一日游"></div>
                <div class="form-group"><label class="form-label">分类 *</label><select class="form-select" name="category" required><option value="">请选择</option><?php foreach ($categories as $cat): ?><option value="<?php echo $cat; ?>"><?php echo $cat; ?></option><?php endforeach; ?></select></div>
                <div class="form-group"><label class="form-label">描述</label><textarea class="form-textarea" name="description" placeholder="简短描述..."></textarea></div>
                <div class="form-group"><label class="form-label">图片</label><input type="file" class="form-input" name="image" accept="image/*"><small style="color:#9E8C7E;font-size:12px;">支持 jpg/png/gif/webp，最大 5MB</small></div>
                <div class="form-group"><label class="form-label">详情内容（HTML）</label><textarea class="form-textarea" name="detail_content" style="min-height:200px;font-family:monospace;font-size:13px;" placeholder="支持HTML标签"></textarea><small style="color:#9E8C7E;font-size:12px;">此内容将显示在前台详情页</small></div>
                <div class="form-group"><label class="form-label">排序</label><input type="number" class="form-input" name="sort_order" value="0" min="0"></div>
                <button type="submit" class="btn btn--primary">提交添加</button>
            </form>
        </div>

        <?php elseif ($action === 'edit' && $editItem): ?>
        <div class="page-header"><h1 class="page-title">编辑攻略</h1><a href="manage_strategies.php" class="btn btn--outline">← 返回列表</a></div>
        <div class="form-card">
            <form method="POST" action="?action=edit" enctype="multipart/form-data">
                <input type="hidden" name="id" value="<?php echo $editItem['id']; ?>">
                <div class="form-group"><label class="form-label">名称 *</label><input type="text" class="form-input" name="name" required value="<?php echo htmlspecialchars($editItem['name']); ?>"></div>
                <div class="form-group"><label class="form-label">分类 *</label><select class="form-select" name="category" required><?php foreach ($categories as $cat): ?><option value="<?php echo $cat; ?>" <?php echo $editItem['category'] === $cat ? 'selected' : ''; ?>><?php echo $cat; ?></option><?php endforeach; ?></select></div>
                <div class="form-group"><label class="form-label">描述</label><textarea class="form-textarea" name="description"><?php echo htmlspecialchars($editItem['description']); ?></textarea></div>
                <div class="form-group"><label class="form-label">图片</label><?php if ($editItem['image']): ?><div style="margin-bottom:8px;"><img src="../../<?php echo htmlspecialchars($editItem['image']); ?>" style="max-width:200px;border-radius:8px;"></div><?php endif; ?><input type="file" class="form-input" name="image" accept="image/*"><small style="color:#9E8C7E;font-size:12px;">留空保持原图</small></div>
                <div class="form-group"><label class="form-label">详情内容（HTML）</label><textarea class="form-textarea" name="detail_content" style="min-height:200px;font-family:monospace;font-size:13px;"><?php echo htmlspecialchars($editItem['detail_content'] ?? ''); ?></textarea></div>
                <div class="form-group"><label class="form-label">排序</label><input type="number" class="form-input" name="sort_order" value="<?php echo $editItem['sort_order']; ?>" min="0"></div>
                <button type="submit" class="btn btn--primary">保存修改</button>
            </form>
        </div>
        <?php endif; ?>
    </div>
</body>
</html>
