<?php
/**
 * 详情页留言管理（后台）
 * 左侧分类导航，右侧管理对应页面的留言
 */

require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

checkAuth();

$db = getDB();
$message = '';
$messageType = '';

// ========== 内容类型配置 ==========
$typeMap = [
    'spot'          => ['label' => '景点留言', 'icon' => '🏞️', 'table' => 'spots',          'nameCol' => 'name'],
    'food'          => ['label' => '美食留言', 'icon' => '🍜', 'table' => 'foods',          'nameCol' => 'name'],
    'accommodation' => ['label' => '住宿留言', 'icon' => '🏨', 'table' => 'accommodations', 'nameCol' => 'name'],
    'transport'     => ['label' => '交通留言', 'icon' => '🚄', 'table' => 'transports',     'nameCol' => 'name'],
    'strategy'      => ['label' => '攻略留言', 'icon' => '📋', 'table' => 'strategies',     'nameCol' => 'name'],
];

// ========== 获取当前选中的类型 ==========
$activeType = isset($_GET['type']) && array_key_exists($_GET['type'], $typeMap) ? $_GET['type'] : 'spot';
$activeItemId = isset($_GET['item_id']) ? intval($_GET['item_id']) : 0;

// ========== 删除留言 ==========
if (isset($_GET['action']) && $_GET['action'] === 'delete' && isset($_GET['id'])) {
    $delId = intval($_GET['id']);
    if ($delId > 0) {
        $stmt = $db->prepare("DELETE FROM comments WHERE id = :id");
        $stmt->execute([':id' => $delId]);
        $message = '留言已删除';
        $messageType = 'success';
    }
}

// ========== 左侧导航：统计每个类型的留言数 ==========
$typeCounts = [];
foreach ($typeMap as $typeKey => $typeInfo) {
    $cStmt = $db->prepare("SELECT COUNT(*) FROM comments WHERE content_type = :t");
    $cStmt->execute([':t' => $typeKey]);
    $typeCounts[$typeKey] = $cStmt->fetchColumn();
}

// ========== 左侧导航：获取当前类型下有留言的内容条目 ==========
$contentItems = [];
$cfg = $typeMap[$activeType];
$itemSql = "SELECT c.content_id, t.{$cfg['nameCol']} as item_name, COUNT(c.id) as comment_count
            FROM comments c
            LEFT JOIN {$cfg['table']} t ON c.content_id = t.id
            WHERE c.content_type = :t
            GROUP BY c.content_id
            ORDER BY comment_count DESC";
$itemStmt = $db->prepare($itemSql);
$itemStmt->execute([':t' => $activeType]);
$contentItems = $itemStmt->fetchAll();

// ========== 右侧：获取评论列表 ==========
$pageSize = 20;
$page = isset($_GET['page']) ? max(1, intval($_GET['page'])) : 1;
$offset = ($page - 1) * $pageSize;
$searchKeyword = isset($_GET['keyword']) ? sanitizeInput($_GET['keyword']) : '';

$where = "WHERE c.content_type = :t";
$params = [':t' => $activeType];

if ($activeItemId > 0) {
    $where .= " AND c.content_id = :item_id";
    $params[':item_id'] = $activeItemId;
}
if (!empty($searchKeyword)) {
    $where .= " AND (c.name LIKE :kw1 OR c.content LIKE :kw2)";
    $params[':kw1'] = '%' . $searchKeyword . '%';
    $params[':kw2'] = '%' . $searchKeyword . '%';
}

$countSql = "SELECT COUNT(*) FROM comments c $where";
$countStmt = $db->prepare($countSql);
$countStmt->execute($params);
$total = $countStmt->fetchColumn();
$totalPages = ceil($total / $pageSize);

$sql = "SELECT c.*, t.{$cfg['nameCol']} as item_name
        FROM comments c
        LEFT JOIN {$cfg['table']} t ON c.content_id = t.id
        $where
        ORDER BY c.created_at DESC
        LIMIT :limit OFFSET :offset";
$stmt = $db->prepare($sql);
foreach ($params as $k => $v) {
    $stmt->bindValue($k, $v);
}
$stmt->bindValue(':limit', $pageSize, PDO::PARAM_INT);
$stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
$stmt->execute();
$comments = $stmt->fetchAll();

// ========== 构建 URL 辅助函数 ==========
function buildUrl($extraParams = []) {
    global $activeType, $activeItemId, $searchKeyword;
    $base = [
        'type' => $activeType
    ];
    if ($activeItemId > 0) $base['item_id'] = $activeItemId;
    if (!empty($searchKeyword)) $base['keyword'] = $searchKeyword;
    return 'manage_comments.php?' . http_build_query(array_merge($base, $extraParams));
}
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>评论管理 — 宁波旅游后台</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #F5EDE2; color: #2C1810; line-height: 1.6; }

        /* ===== Admin Header ===== */
        .admin-header { background: #2C1810; color: #fff; padding: 0 24px; height: 60px; display: flex; align-items: center; justify-content: space-between; }
        .admin-header__brand { font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
        .admin-header__icon { width: 32px; height: 32px; background: #B8763E; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
        .admin-header__nav { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
        .admin-header__nav a { color: rgba(255,255,255,0.7); text-decoration: none; font-size: 14px; padding: 6px 14px; border-radius: 6px; transition: all 0.2s; }
        .admin-header__nav a:hover, .admin-header__nav a.active { color: #fff; background: rgba(255,255,255,0.1); }
        .admin-header__user { font-size: 14px; color: rgba(255,255,255,0.6); }
        .admin-header__user a { color: #D4975F; text-decoration: none; margin-left: 12px; }

        /* ===== Layout: Container + Sidebar + Main ===== */
        .container { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
        .layout { display: flex; gap: 24px; min-height: 500px; }

        /* ===== Sidebar ===== */
        .sidebar { width: 240px; background: #fff; border: 1px solid #E8DDD1; border-radius: 12px; padding: 20px 0; flex-shrink: 0; overflow-y: auto; align-self: flex-start; box-shadow: 0 1px 3px rgba(44,24,16,0.06); }
        .sidebar__title { font-size: 13px; font-weight: 700; color: #9E8C7E; text-transform: uppercase; letter-spacing: 1px; padding: 0 20px; margin-bottom: 12px; }
        .sidebar__section { margin-bottom: 8px; }
        .sidebar__type-btn {
            display: flex; align-items: center; gap: 10px; width: 100%;
            padding: 10px 20px; font-size: 14px; border: none; background: none;
            cursor: pointer; text-align: left; transition: all 0.15s;
            color: #6B5344; font-family: inherit; text-decoration: none;
        }
        .sidebar__type-btn:hover { background: #FDFAF6; color: #2C1810; }
        .sidebar__type-btn.active { background: #F5EDE2; color: #B8763E; font-weight: 600; border-right: 3px solid #B8763E; }
        .sidebar__type-icon { font-size: 18px; width: 24px; text-align: center; }
        .sidebar__type-label { flex: 1; }
        .sidebar__type-count {
            font-size: 12px; font-weight: 600; padding: 2px 8px;
            border-radius: 10px; background: #F0E8DE; color: #9E8C7E;
        }
        .sidebar__type-btn.active .sidebar__type-count { background: rgba(184,118,62,0.15); color: #B8763E; }

        /* Sidebar sub-items */
        .sidebar__items { display: none; padding: 4px 0 8px 0; }
        .sidebar__items.open { display: block; }
        .sidebar__item-link {
            display: flex; align-items: center; justify-content: space-between;
            padding: 7px 20px 7px 54px; font-size: 13px; color: #9E8C7E;
            text-decoration: none; transition: all 0.15s;
        }
        .sidebar__item-link:hover { color: #6B5344; background: #FDFAF6; }
        .sidebar__item-link.active { color: #B8763E; font-weight: 600; background: rgba(184,118,62,0.05); }
        .sidebar__item-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .sidebar__item-count { font-size: 12px; color: #B8763E; background: rgba(184,118,62,0.1); padding: 1px 7px; border-radius: 8px; margin-left: 8px; flex-shrink: 0; }
        .sidebar__all-link {
            display: block; padding: 6px 20px 6px 54px; font-size: 13px;
            color: #B8763E; text-decoration: none; font-weight: 600;
            transition: all 0.15s;
        }
        .sidebar__all-link:hover { background: rgba(184,118,62,0.05); }

        /* ===== Main Content ===== */
        .main { flex: 1; overflow-x: auto; min-width: 0; }
        .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
        .page-title { font-size: 22px; font-weight: 700; }
        .page-title__icon { margin-right: 8px; }
        .page-subtitle { font-size: 13px; color: #9E8C7E; font-weight: 400; margin-left: 8px; }
        .total-badge { font-size: 14px; color: #9E8C7E; background: #fff; padding: 4px 14px; border-radius: 20px; border: 1px solid #E8DDD1; }

        .alert { padding: 12px 16px; border-radius: 8px; font-size: 14px; margin-bottom: 16px; }
        .alert--success { background: #F0FDF4; color: #166534; border: 1px solid #BBF7D0; }

        /* Filter bar */
        .filter-bar { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
        .filter-bar__item-name { font-size: 14px; color: #6B5344; background: #fff; border: 1px solid #E8DDD1; border-radius: 8px; padding: 6px 14px; display: flex; align-items: center; gap: 6px; }
        .filter-bar__item-name a { color: #C4584A; text-decoration: none; font-size: 16px; margin-left: 4px; line-height: 1; }
        .search-input { max-width: 280px; width: 100%; padding: 8px 14px; border: 2px solid #E8DDD1; border-radius: 8px; font-size: 14px; outline: none; transition: border-color 0.2s; font-family: inherit; }
        .search-input:focus { border-color: #B8763E; }
        .btn--search { background: #B8763E; color: #fff; padding: 8px 18px; font-size: 14px; font-weight: 600; border-radius: 8px; border: none; cursor: pointer; transition: all 0.2s; }
        .btn--search:hover { background: #8E5A2A; }
        .btn--reset { background: #fff; color: #6B5344; padding: 8px 14px; font-size: 13px; border-radius: 8px; border: 1px solid #E8DDD1; text-decoration: none; transition: all 0.2s; }
        .btn--reset:hover { border-color: #B8763E; color: #B8763E; }

        /* Comment Cards */
        .comment-cards { display: flex; flex-direction: column; gap: 12px; padding: 16px; }
        .comment-card-admin { background: #FDFAF6; border: 1px solid #F0E8DE; border-radius: 10px; padding: 16px; transition: box-shadow 0.2s; }
        .comment-card-admin:hover { box-shadow: 0 2px 8px rgba(44,24,16,0.06); }
        .comment-card-admin__header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
        .comment-card-admin__avatar { width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #B8763E, #D4975F); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; flex-shrink: 0; }
        .comment-card-admin__meta { display: flex; flex-direction: column; flex: 1; min-width: 0; }
        .comment-card-admin__name { font-weight: 600; font-size: 14px; color: #2C1810; }
        .comment-card-admin__time { font-size: 12px; color: #9E8C7E; }
        .comment-card-admin__target { font-size: 12px; color: #B8763E; background: rgba(184,118,62,0.08); padding: 3px 10px; border-radius: 12px; text-decoration: none; white-space: nowrap; flex-shrink: 0; }
        .comment-card-admin__target:hover { background: rgba(184,118,62,0.15); }
        .comment-card-admin__body { font-size: 14px; color: #6B5344; line-height: 1.6; word-break: break-all; margin-bottom: 10px; }
        .comment-card-admin__footer { display: flex; justify-content: flex-end; }
        .btn--danger-sm { display: inline-flex; align-items: center; gap: 4px; padding: 4px 12px; font-size: 12px; font-weight: 500; border-radius: 6px; background: none; color: #C4584A; text-decoration: none; border: 1px solid transparent; cursor: pointer; transition: all 0.2s; }
        .btn--danger-sm:hover { background: #FEF2F2; border-color: #FECACA; color: #A33D30; }
        .empty { text-align: center; padding: 48px; color: #9E8C7E; }
        .empty__icon { font-size: 40px; margin-bottom: 12px; }

        /* Pagination */
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

        /* Responsive */
        @media (max-width: 900px) {
            .layout { flex-direction: column; }
            .sidebar { width: 100%; }
            .sidebar__items.open { display: flex; flex-wrap: wrap; gap: 4px; padding: 4px 20px 8px; }
            .sidebar__item-link { padding: 4px 10px; }
        }
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
            <a href="manage_messages.php">留言板</a>
            <a href="manage_comments.php" class="active">评论管理</a>
        </nav>
        <div class="admin-header__user">
            <?php echo htmlspecialchars($_SESSION['admin_username']); ?>
            <a href="logout.php">退出</a>
        </div>
    </header>

    <div class="container">
    <div class="layout">
        <!-- ===== 左侧分类导航 ===== -->
        <aside class="sidebar">
            <div class="sidebar__title">留言分类</div>

            <?php foreach ($typeMap as $typeKey => $typeInfo): ?>
            <div class="sidebar__section">
                <a href="manage_comments.php?type=<?php echo $typeKey; ?>"
                   class="sidebar__type-btn <?php echo $activeType === $typeKey ? 'active' : ''; ?>">
                    <span class="sidebar__type-icon"><?php echo $typeInfo['icon']; ?></span>
                    <span class="sidebar__type-label"><?php echo $typeInfo['label']; ?></span>
                    <span class="sidebar__type-count"><?php echo $typeCounts[$typeKey]; ?></span>
                </a>

                <?php if ($activeType === $typeKey && !empty($contentItems)): ?>
                <div class="sidebar__items open">
                    <a href="manage_comments.php?type=<?php echo $typeKey; ?>"
                       class="sidebar__all-link <?php echo $activeItemId === 0 ? '' : ''; ?>">
                        查看全部
                    </a>
                    <?php foreach ($contentItems as $ci): ?>
                    <a href="manage_comments.php?type=<?php echo $typeKey; ?>&item_id=<?php echo $ci['content_id']; ?>"
                       class="sidebar__item-link <?php echo $activeItemId === (int)$ci['content_id'] ? 'active' : ''; ?>">
                        <span class="sidebar__item-name"><?php echo htmlspecialchars($ci['item_name'] ?: '(ID:' . $ci['content_id'] . ')'); ?></span>
                        <span class="sidebar__item-count"><?php echo $ci['comment_count']; ?></span>
                    </a>
                    <?php endforeach; ?>
                </div>
                <?php endif; ?>
            </div>
            <?php endforeach; ?>
        </aside>

        <!-- ===== 右侧主内容 ===== -->
        <div class="main">
            <?php if ($message): ?>
                <div class="alert alert--<?php echo $messageType; ?>"><?php echo htmlspecialchars($message); ?></div>
            <?php endif; ?>

            <div class="page-header">
                <h1 class="page-title">
                    <span class="page-title__icon"><?php echo $typeMap[$activeType]['icon']; ?></span>
                    <?php echo $typeMap[$activeType]['label']; ?>
                    <?php if ($activeItemId > 0):
                        $currentItemName = '';
                        foreach ($contentItems as $ci) {
                            if ((int)$ci['content_id'] === $activeItemId) {
                                $currentItemName = $ci['item_name'];
                                break;
                            }
                        }
                    ?>
                        <span class="page-subtitle">— <?php echo htmlspecialchars($currentItemName ?: 'ID:' . $activeItemId); ?></span>
                    <?php endif; ?>
                </h1>
                <span class="total-badge">共 <?php echo $total; ?> 条留言</span>
            </div>

            <!-- 筛选与搜索 -->
            <form method="GET" class="filter-bar">
                <input type="hidden" name="type" value="<?php echo htmlspecialchars($activeType); ?>">
                <?php if ($activeItemId > 0): ?>
                    <input type="hidden" name="item_id" value="<?php echo $activeItemId; ?>">
                    <div class="filter-bar__item-name">
                        📌 <?php echo htmlspecialchars($currentItemName ?: 'ID:' . $activeItemId); ?>
                        <a href="manage_comments.php?type=<?php echo $activeType; ?>" title="取消筛选">×</a>
                    </div>
                <?php endif; ?>
                <input type="text" class="search-input" name="keyword" placeholder="搜索昵称或留言内容..."
                       value="<?php echo htmlspecialchars($searchKeyword); ?>">
                <button type="submit" class="btn--search">搜索</button>
                <?php if (!empty($searchKeyword)): ?>
                    <a href="<?php echo buildUrl(['keyword' => '']); ?>" class="btn--reset">清除</a>
                <?php endif; ?>
            </form>

            <!-- 评论表格 -->
            <div class="table-wrapper">
                <?php if (empty($comments)): ?>
                    <div class="empty">
                        <div class="empty__icon">💬</div>
                        暂无留言
                    </div>
                <?php else: ?>
                <div class="comment-cards">
                    <?php foreach ($comments as $c): ?>
                    <div class="comment-card-admin">
                        <div class="comment-card-admin__header">
                            <div class="comment-card-admin__avatar"><?php echo mb_substr(htmlspecialchars($c['name']), 0, 1); ?></div>
                            <div class="comment-card-admin__meta">
                                <span class="comment-card-admin__name"><?php echo htmlspecialchars($c['name']); ?></span>
                                <span class="comment-card-admin__time"><?php echo $c['created_at']; ?></span>
                            </div>
                            <a href="manage_comments.php?type=<?php echo $activeType; ?>&item_id=<?php echo $c['content_id']; ?>" class="comment-card-admin__target">
                                <?php echo htmlspecialchars($c['item_name'] ?: 'ID:' . $c['content_id']); ?>
                            </a>
                        </div>
                        <div class="comment-card-admin__body"><?php echo htmlspecialchars($c['content']); ?></div>
                        <div class="comment-card-admin__footer">
                            <a href="<?php echo buildUrl(['action' => 'delete', 'id' => $c['id'], 'page' => isset($_GET['page']) ? $_GET['page'] : 1]); ?>"
                               class="btn--danger-sm"
                               onclick="return confirm('确定要删除此留言吗？');">🗑 删除</a>
                        </div>
                    </div>
                    <?php endforeach; ?>
                </div>
                <?php endif; ?>
            </div>

            <!-- 分页 -->
            <?php if ($totalPages > 1): ?>
            <div class="pagination">
                <?php if ($page > 1): ?>
                    <a href="<?php echo buildUrl(['page' => $page - 1]); ?>">上一页</a>
                <?php endif; ?>
                <?php
                $startPage = max(1, $page - 3);
                $endPage = min($totalPages, $page + 3);
                if ($startPage > 1): ?>
                    <a href="<?php echo buildUrl(['page' => 1]); ?>">1</a>
                    <?php if ($startPage > 2): ?><span style="border:none;background:none;color:#9E8C7E;">…</span><?php endif; ?>
                <?php endif; ?>
                <?php for ($i = $startPage; $i <= $endPage; $i++): ?>
                    <?php if ($i === $page): ?>
                        <span class="current"><?php echo $i; ?></span>
                    <?php else: ?>
                        <a href="<?php echo buildUrl(['page' => $i]); ?>"><?php echo $i; ?></a>
                    <?php endif; ?>
                <?php endfor; ?>
                <?php if ($endPage < $totalPages): ?>
                    <?php if ($endPage < $totalPages - 1): ?><span style="border:none;background:none;color:#9E8C7E;">…</span><?php endif; ?>
                    <a href="<?php echo buildUrl(['page' => $totalPages]); ?>"><?php echo $totalPages; ?></a>
                <?php endif; ?>
                <?php if ($page < $totalPages): ?>
                    <a href="<?php echo buildUrl(['page' => $page + 1]); ?>">下一页</a>
                <?php endif; ?>
            </div>
            <?php endif; ?>
        </div>
    </div>
    </div>
</body>
</html>
