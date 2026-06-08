-- ============================================
-- 宁波旅游宣传网站 — 数据库初始化脚本
-- 数据库名: ningbo_tourism
-- 字符集: utf8mb4
-- ============================================

-- 创建数据库（如不存在）
CREATE DATABASE IF NOT EXISTS `ningbo_tourism`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `ningbo_tourism`;

-- ============================================
-- 景点表
-- ============================================
DROP TABLE IF EXISTS `spots`;
CREATE TABLE `spots` (
    `id`          INT AUTO_INCREMENT PRIMARY KEY COMMENT '景点ID',
    `name`        VARCHAR(100) NOT NULL COMMENT '景点名称',
    `category`    VARCHAR(50)  NOT NULL COMMENT '分类：自然风光/人文古迹/红色研学',
    `description` TEXT         COMMENT '景点描述',
    `image`       VARCHAR(255) DEFAULT '' COMMENT '图片路径',
    `sort_order`  INT          DEFAULT 0 COMMENT '排序（数字越小越靠前）',
    `created_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='景点信息表';

-- ============================================
-- 留言表
-- ============================================
DROP TABLE IF EXISTS `messages`;
CREATE TABLE `messages` (
    `id`         INT AUTO_INCREMENT PRIMARY KEY COMMENT '留言ID',
    `name`       VARCHAR(50) NOT NULL COMMENT '用户昵称',
    `content`    TEXT        NOT NULL COMMENT '留言内容',
    `created_at` DATETIME    DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='游客留言表';

-- ============================================
-- 插入示例景点数据
-- ============================================
INSERT INTO `spots` (`name`, `category`, `description`, `image`, `sort_order`) VALUES
('天一阁博物院', '人文古迹', '中国现存最早的私家藏书楼，建于明嘉靖四十年(1561年)。馆藏古籍30余万卷，是中华文化的瑰宝。', 'images/scenic/tianyi.png', 1),
('东钱湖', '自然风光', '浙江省最大的天然淡水湖，湖面面积约20平方公里。湖畔青山环抱，古迹星罗棋布，是休闲度假的绝佳去处。', 'images/scenic/dongqian.png', 2),
('溪口雪窦山', '自然风光', '国家级重点风景名胜区，海拔800米。千丈岩瀑布落差186米，气势磅礴。妙高台是弥勒佛道场所在。', 'images/scenic/xikou.png', 3),
('四明山森林公园', '自然风光', '地处四明山腹地，平均海拔700米，森林覆盖率高达96%。春赏杜鹃、夏避暑、秋观红叶、冬赏雾凇。', 'images/scenic/dongqian.png', 4),
('保国寺', '人文古迹', '全国重点文物保护单位，始建于东汉。大殿建于北宋，是江南现存最古老的木构建筑之一，被誉为建筑奇迹。', 'images/scenic/tianyi.png', 5),
('老外滩', '人文古迹', '中国最早的外滩，比上海外滩早20年开埠。保留了大量欧式老建筑，如今是集餐饮、酒吧、文化于一体的休闲街区。', 'images/food/oldtown.png', 6),
('河姆渡遗址', '人文古迹', '距今约7000年的新石器时代遗址，是中国最重要的考古发现之一。出土了大量稻作遗存，证明中国是最早种植水稻的国家。', 'images/scenic/tianyi.png', 7),
('渔山列岛', '自然风光', '被誉为"亚洲第一钓场"，海水清澈见底，礁石奇特多姿。是潜水、垂钓和看日出的绝佳海岛。', 'images/scenic/xikou.png', 8),
('浙东抗日根据地旧址', '红色研学', '全国重点文物保护单位，包括中共浙东区委旧址、浙东行政公署旧址等，是浙东革命斗争的历史见证。', 'images/scenic/red-tourism.png', 9),
('四明山革命烈士纪念碑', '红色研学', '矗立于四明山主峰之上，碑高18.5米，纪念在浙东革命斗争中英勇牺牲的革命先烈。周边环境庄严肃穆。', 'images/scenic/red-tourism.png', 10);

-- ============================================
-- 插入示例留言数据
-- ============================================
INSERT INTO `messages` (`name`, `content`, `created_at`) VALUES
('小明', '宁波太美了！东钱湖骑行一圈，风景超赞，下次还来！', '2025-01-15 14:30:00'),
('旅行达人Amy', '天一阁的文化底蕴真的很深厚，推荐大家去看看。南塘老街的汤圆也是一绝，缸鸭狗排队也值得！', '2025-02-01 09:15:00'),
('吃货老王', '红膏炝蟹太好吃了！第一次吃到这么鲜的蟹，宁波海鲜名不虚传。还有年糕也很好吃，买了好几盒带回去。', '2025-02-10 18:45:00');

-- ============================================
-- 完成提示
-- ============================================
-- 数据库初始化完成！
-- 管理员默认账号: admin
-- 管理员默认密码: 123456
-- 后台入口: /api/admin/login.php
