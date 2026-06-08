<?php
/**
 * 后台管理首页（仪表盘）
 * 显示统计数据和快捷导航
 */

require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../config/db.php';
require_once __DIR__ . '/../includes/functions.php';

checkAuth();

// 获取统计数据
$db = getDB();
$spotCount = $db->query("SELECT COUNT(*) FROM spots")->fetchColumn();
$foodCount = $db->query("SELECT COUNT(*) FROM foods")->fetchColumn();
$accommodationCount = $db->query("SELECT COUNT(*) FROM accommodations")->fetchColumn();
$transportCount = $db->query("SELECT COUNT(*) FROM transports")->fetchColumn();
$strategyCount = $db->query("SELECT COUNT(*) FROM strategies")->fetchColumn();
$messageCount = $db->query("SELECT COUNT(*) FROM messages")->fetchColumn();
$commentCount = $db->query("SELECT COUNT(*) FROM comments")->fetchColumn();
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>后台管理 — 宁波旅游</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #F5EDE2;
            color: #2C1810;
            line-height: 1.6;
        }
        .admin-header {
            background: #2C1810;
            color: #fff;
            padding: 0 24px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .admin-header__brand {
            font-size: 18px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .admin-header__icon {
            width: 32px; height: 32px;
            border-radius: 8px;
            object-fit: contain;
        }
        .admin-header__nav {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .admin-header__nav a {
            color: rgba(255,255,255,0.7);
            text-decoration: none;
            font-size: 14px;
            padding: 6px 14px;
            border-radius: 6px;
            transition: all 0.2s;
        }
        .admin-header__nav a:hover, .admin-header__nav a.active {
            color: #fff;
            background: rgba(255,255,255,0.1);
        }
        .admin-header__user {
            font-size: 14px;
            color: rgba(255,255,255,0.6);
        }
        .admin-header__user a {
            color: #D4975F;
            text-decoration: none;
            margin-left: 12px;
        }
        .admin-header__user a:hover { color: #E8BE93; }
        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 32px 24px;
        }
        .page-title {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 24px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }
        .stat-card {
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(44,24,16,0.06);
            border: 1px solid #E8DDD1;
        }
        .stat-card__number {
            font-size: 36px;
            font-weight: 800;
            color: #B8763E;
            line-height: 1;
        }
        .stat-card__label {
            font-size: 14px;
            color: #9E8C7E;
            margin-top: 6px;
        }
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }
        .action-card {
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #E8DDD1;
            text-decoration: none;
            color: inherit;
            transition: all 0.2s;
            display: flex;
            gap: 16px;
            align-items: flex-start;
        }
        .action-card:hover {
            box-shadow: 0 4px 12px rgba(44,24,16,0.08);
            transform: translateY(-2px);
        }
        .action-card__icon {
            width: 48px; height: 48px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            flex-shrink: 0;
        }
        .action-card__icon--spot { background: rgba(61,122,95,0.1); }
        .action-card__icon--food { background: rgba(236,72,153,0.1); }
        .action-card__icon--hotel { background: rgba(168,85,247,0.1); }
        .action-card__icon--transport { background: rgba(59,130,246,0.1); }
        .action-card__icon--strategy { background: rgba(245,158,11,0.1); }
        .action-card__icon--msg { background: rgba(184,118,62,0.1); }
        .action-card__icon--site { background: rgba(196,88,74,0.1); }
        .action-card__title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
        .action-card__desc { font-size: 13px; color: #9E8C7E; }
    </style>
</head>
<body>
    <header class="admin-header">
        <div class="admin-header__brand">
            <img src="../../images/favicon.ico" alt="宁波旅游" class="admin-header__icon">
            后台管理
        </div>
        <nav class="admin-header__nav">
            <a href="dashboard.php" class="active">首页</a>
            <a href="manage_spots.php">景点管理</a>
            <a href="manage_foods.php">美食管理</a>
            <a href="manage_accommodations.php">住宿管理</a>
            <a href="manage_transports.php">交通管理</a>
            <a href="manage_strategies.php">攻略管理</a>
            <a href="manage_messages.php">留言板</a>
            <a href="manage_comments.php">评论管理</a>
        </nav>
        <div class="admin-header__user">
            欢迎，<?php echo htmlspecialchars($_SESSION['admin_username']); ?>
            <a href="logout.php">退出登录</a>
        </div>
    </header>

    <div class="container">
        <h1 class="page-title">管理概览</h1>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-card__number"><?php echo $spotCount; ?></div>
                <div class="stat-card__label">景点总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-card__number"><?php echo $foodCount; ?></div>
                <div class="stat-card__label">美食总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-card__number"><?php echo $accommodationCount; ?></div>
                <div class="stat-card__label">住宿总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-card__number"><?php echo $transportCount; ?></div>
                <div class="stat-card__label">交通信息</div>
            </div>
            <div class="stat-card">
                <div class="stat-card__number"><?php echo $strategyCount; ?></div>
                <div class="stat-card__label">攻略总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-card__number"><?php echo $messageCount; ?></div>
                <div class="stat-card__label">留言总数</div>
            </div>
        </div>

        <h2 class="page-title" style="font-size:18px;">快捷操作</h2>
        <div class="quick-actions">
            <a href="manage_spots.php" class="action-card">
                <div class="action-card__icon action-card__icon--spot">🏞️</div>
                <div>
                    <div class="action-card__title">景点管理</div>
                    <div class="action-card__desc">添加、编辑、删除景点信息，管理景点图片与分类</div>
                </div>
            </a>
            <a href="manage_foods.php" class="action-card">
                <div class="action-card__icon action-card__icon--food">🍜</div>
                <div>
                    <div class="action-card__title">美食管理</div>
                    <div class="action-card__desc">管理宁波特色美食，包括海鲜、小吃、糕点等</div>
                </div>
            </a>
            <a href="manage_accommodations.php" class="action-card">
                <div class="action-card__icon action-card__icon--hotel">🏨</div>
                <div>
                    <div class="action-card__title">住宿管理</div>
                    <div class="action-card__desc">管理酒店、民宿等住宿信息与详情内容</div>
                </div>
            </a>
            <a href="manage_transports.php" class="action-card">
                <div class="action-card__icon action-card__icon--transport">🚄</div>
                <div>
                    <div class="action-card__title">交通管理</div>
                    <div class="action-card__desc">管理交通出行信息，包括航空、铁路、公交等</div>
                </div>
            </a>
            <a href="manage_strategies.php" class="action-card">
                <div class="action-card__icon action-card__icon--strategy">📋</div>
                <div>
                    <div class="action-card__title">攻略管理</div>
                    <div class="action-card__desc">管理行程规划、攻略指南、实用贴士</div>
                </div>
            </a>
            <a href="manage_messages.php" class="action-card">
                <div class="action-card__icon action-card__icon--msg">💬</div>
                <div>
                    <div class="action-card__title">留言板管理</div>
                    <div class="action-card__desc">查看留言板游客留言，删除不当内容</div>
                </div>
            </a>
            <a href="manage_comments.php" class="action-card">
                <div class="action-card__icon action-card__icon--msg">📝</div>
                <div>
                    <div class="action-card__title">评论管理</div>
                    <div class="action-card__desc">按页面分类管理各详情页面的用户评论</div>
                </div>
            </a>
            <a href="../../index.html" class="action-card" target="_blank">
                <div class="action-card__icon action-card__icon--site">🌐</div>
                <div>
                    <div class="action-card__title">查看前台</div>
                    <div class="action-card__desc">在新窗口中预览网站前台页面</div>
                </div>
            </a>
        </div>
    </div>
</body>
</html>
