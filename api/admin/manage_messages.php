<?php
/**
 * 留言管理页面（后台）
 * 查看所有留言、删除不当留言
 */

require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

checkAuth();

$db = getDB();
$message = '';
$messageType = '';

// 删除留言
if (isset($_GET['action']) && $_GET['action'] === 'delete' && isset($_GET['id'])) {
    $id = intval($_GET['id']);
    if ($id > 0) {
        $stmt = $db->prepare("DELETE FROM messages WHERE id = :id");
        $stmt->execute([':id' => $id]);
        $message = '留言已删除';
        $messageType = 'success';
    }
}

// 获取留言列表（分页+搜索）
list($page, $pageSize, $offset) = getPagination();
$pageSize = 20;
$offset = ($page - 1) * $pageSize;
$searchKeyword = isset($_GET['keyword']) ? sanitizeInput($_GET['keyword']) : '';

$where = '';
$params = [];
if (!empty($searchKeyword)) {
    $where = "WHERE name LIKE :kw1 OR content LIKE :kw2";
    $params[':kw1'] = '%' . $searchKeyword . '%';
    $params[':kw2'] = '%' . $searchKeyword . '%';
}

$countSql = "SELECT COUNT(*) FROM messages $where";
$countStmt = $db->prepare($countSql);
$countStmt->execute($params);
$total = $countStmt->fetchColumn();
$totalPages = ceil($total / $pageSize);

$sql = "SELECT * FROM messages $where ORDER BY created_at DESC LIMIT :limit OFFSET :offset";
$stmt = $db->prepare($sql);
foreach ($params as $k => $v) {
    $stmt->bindValue($k, $v);
}
$stmt->bindValue(':limit', $pageSize, PDO::PARAM_INT);
$stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
$stmt->execute();
$messages = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>留言管理 — 宁波旅游后台</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #F5EDE2; color: #2C1810; line-height: 1.6; }
        .admin-header { background: #2C1810; color: #fff; padding: 0 24px; height: 60px; display: flex; align-items: center; justify-content: space-between; }
        .admin-header__brand { font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
        .admin-header__icon { width: 32px; height: 32px; background: #B8763E; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
        .admin-header__nav { display: flex; align-items: center; gap: 16px; }
        .admin-header__nav a { color: rgba(255,255,255,0.7); text-decoration: none; font-size: 14px; padding: 6px 14px; border-radius: 6px; transition: all 0.2s; }
        .admin-header__nav a:hover, .admin-header__nav a.active { color: #fff; background: rgba(255,255,255,0.1); }
        .admin-header__user { font-size: 14px; color: rgba(255,255,255,0.6); }
        .admin-header__user a { color: #D4975F; text-decoration: none; margin-left: 12px; }
        .container { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
        .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
        .page-title { font-size: 24px; font-weight: 700; }
        .total-badge { font-size: 14px; color: #9E8C7E; background: #fff; padding: 4px 14px; border-radius: 20px; border: 1px solid #E8DDD1; }
        .alert { padding: 12px 16px; border-radius: 8px; font-size: 14px; margin-bottom: 20px; }
        .alert--success { background: #F0FDF4; color: #166534; border: 1px solid #BBF7D0; }
        .table-wrapper { background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(44,24,16,0.06); border: 1px solid #E8DDD1; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { background: #FDFAF6; font-weight: 600; text-align: left; padding: 12px 16px; border-bottom: 1px solid #E8DDD1; color: #6B5344; font-size: 13px; }
        td { padding: 12px 16px; border-bottom: 1px solid #F0E8DE; vertical-align: top; }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: rgba(184,118,62,0.03); }
        .msg-name { font-weight: 600; white-space: nowrap; }
        .msg-content { max-width: 500px; color: #6B5344; line-height: 1.5; }
        .msg-time { font-size: 13px; color: #9E8C7E; white-space: nowrap; }
        .btn--danger { display: inline-flex; align-items: center; gap: 4px; padding: 5px 12px; font-size: 13px; font-weight: 600; border-radius: 6px; background: #C4584A; color: #fff; text-decoration: none; border: none; cursor: pointer; transition: all 0.2s; }
        .btn--danger:hover { background: #A33D30; }
        .empty { text-align: center; padding: 48px; color: #9E8C7E; }
        .search-bar { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .search-input { max-width: 320px; width: 100%; padding: 8px 14px; border: 2px solid #E8DDD1; border-radius: 8px; font-size: 14px; outline: none; transition: border-color 0.2s; font-family: inherit; }
        .search-input:focus { border-color: #B8763E; }
        .btn--search { background: #B8763E; color: #fff; padding: 8px 18px; font-size: 14px; font-weight: 600; border-radius: 8px; border: none; cursor: pointer; transition: all 0.2s; }
        .btn--search:hover { background: #8E5A2A; }
        .btn--reset { background: #fff; color: #6B5344; padding: 8px 18px; font-size: 14px; border-radius: 8px; border: 1px solid #E8DDD1; text-decoration: none; transition: all 0.2s; display: inline-flex; align-items: center; }
        .btn--reset:hover { border-color: #B8763E; color: #B8763E; }
        .result-info { font-size: 13px; color: #9E8C7E; margin-bottom: 12px; }
        .pagination { display: flex; justify-content: center; gap: 8px; margin-top: 24px; }
        .pagination a, .pagination span {
            display: inline-flex; align-items: center; justify-content: center;
            min-width: 36px; height: 36px; padding: 0 10px;
            border-radius: 8px; font-size: 14px; text-decoration: none;
            border: 1px solid #E8DDD1; color: #6B5344; background: #fff;
            transition: all 0.2s;
        }
        .pagination a:hover { border-color: #B8763E; color: #B8763E; }
        .pagination .current { background: #B8763E; color: #fff; border-color: #B8763E; }
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
            <a href="manage_strategies.php">攻略管理</a>
            <a href="manage_messages.php" class="active">留言板</a>
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

        <div class="page-header">
            <h1 class="page-title">留言管理</h1>
            <span class="total-badge">共 <?php echo $total; ?> 条留言</span>
        </div>

        <form method="GET" class="search-bar">
            <input type="text" class="search-input" name="keyword" placeholder="搜索昵称或留言内容..." value="<?php echo htmlspecialchars($searchKeyword); ?>">
            <button type="submit" class="btn--search">搜索</button>
            <?php if (!empty($searchKeyword)): ?>
                <a href="manage_messages.php" class="btn--reset">清除搜索</a>
            <?php endif; ?>
        </form>

        <?php if (!empty($searchKeyword)): ?>
            <div class="result-info">找到 <?php echo $total; ?> 条结果（关键词: <?php echo htmlspecialchars($searchKeyword); ?>）</div>
        <?php endif; ?>

        <div class="table-wrapper">
            <?php if (empty($messages)): ?>
                <div class="empty">暂无留言</div>
            <?php else: ?>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>昵称</th>
                        <th>留言内容</th>
                        <th>时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($messages as $msg): ?>
                    <tr>
                        <td><?php echo $msg['id']; ?></td>
                        <td class="msg-name"><?php echo htmlspecialchars($msg['name']); ?></td>
                        <td class="msg-content"><?php echo htmlspecialchars($msg['content']); ?></td>
                        <td class="msg-time"><?php echo $msg['created_at']; ?></td>
                        <td>
                            <a href="?action=delete&id=<?php echo $msg['id']; ?>" class="btn--danger"
                               onclick="return confirm('确定要删除此留言吗？');">删除</a>
                        </td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
            <?php endif; ?>
        </div>

        <?php if ($totalPages > 1): ?>
        <?php $queryExtra = !empty($searchKeyword) ? '&keyword=' . urlencode($searchKeyword) : ''; ?>
        <div class="pagination">
            <?php if ($page > 1): ?>
                <a href="?page=<?php echo $page - 1; ?><?php echo $queryExtra; ?>">上一页</a>
            <?php endif; ?>
            <?php for ($i = 1; $i <= $totalPages; $i++): ?>
                <?php if ($i === $page): ?>
                    <span class="current"><?php echo $i; ?></span>
                <?php else: ?>
                    <a href="?page=<?php echo $i; ?><?php echo $queryExtra; ?>"><?php echo $i; ?></a>
                <?php endif; ?>
            <?php endfor; ?>
            <?php if ($page < $totalPages): ?>
                <a href="?page=<?php echo $page + 1; ?><?php echo $queryExtra; ?>">下一页</a>
            <?php endif; ?>
        </div>
        <?php endif; ?>
    </div>
</body>
</html>
