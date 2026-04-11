"""批量为数据库表添加中文注释"""
from app.database import engine
from sqlalchemy import text

def add_comments():
    with engine.connect() as conn:
        # Posts 表
        print('📝 添加 posts 表注释...')
        conn.execute(text('ALTER TABLE posts MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "帖子ID"'))
        conn.execute(text('ALTER TABLE posts MODIFY COLUMN user_id INT COMMENT "发帖用户ID"'))
        conn.execute(text('ALTER TABLE posts MODIFY COLUMN content TEXT NOT NULL COMMENT "帖子内容"'))
        conn.execute(text('ALTER TABLE posts MODIFY COLUMN images JSON COMMENT "图片列表JSON"'))
        conn.execute(text('ALTER TABLE posts MODIFY COLUMN likes_count INT DEFAULT 0 COMMENT "点赞数"'))
        conn.execute(text('ALTER TABLE posts MODIFY COLUMN comments_count INT DEFAULT 0 COMMENT "评论数"'))
        conn.execute(text('ALTER TABLE posts MODIFY COLUMN shares_count INT DEFAULT 0 COMMENT "分享数"'))
        conn.execute(text('ALTER TABLE posts MODIFY COLUMN is_anonymous TINYINT(1) DEFAULT 0 COMMENT "是否匿名发布"'))
        conn.execute(text('ALTER TABLE posts MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间"'))
        conn.execute(text('ALTER TABLE posts MODIFY COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "更新时间"'))
        conn.commit()
        
        # Messages 表
        print('📝 添加 messages 表注释...')
        conn.execute(text('ALTER TABLE messages MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "消息ID"'))
        conn.execute(text('ALTER TABLE messages MODIFY COLUMN sender_id INT COMMENT "发送者ID"'))
        conn.execute(text('ALTER TABLE messages MODIFY COLUMN receiver_id INT COMMENT "接收者ID"'))
        conn.execute(text('ALTER TABLE messages MODIFY COLUMN content TEXT NOT NULL COMMENT "消息内容"'))
        conn.execute(text('ALTER TABLE messages MODIFY COLUMN message_type VARCHAR(20) DEFAULT "text" COMMENT "消息类型：text/image/file"'))
        conn.execute(text('ALTER TABLE messages MODIFY COLUMN is_read TINYINT(1) DEFAULT 0 COMMENT "是否已读"'))
        conn.execute(text('ALTER TABLE messages MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "发送时间"'))
        conn.commit()
        
        # Help_tasks 表
        print('📝 添加 help_tasks 表注释...')
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "任务ID"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN publisher_id INT COMMENT "发布者ID"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN assignee_id INT COMMENT "接单者ID"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN title VARCHAR(200) NOT NULL COMMENT "任务标题"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN description TEXT NOT NULL COMMENT "任务描述"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN reward DECIMAL(10,2) DEFAULT 0 COMMENT "任务奖励金额"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN location VARCHAR(255) COMMENT "任务地点"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN deadline DATETIME COMMENT "任务截止时间"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN applicants_count INT DEFAULT 0 COMMENT "申请人数"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN private_info TEXT COMMENT "私密信息（快递码、手机尾号等），仅接单者可见"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "更新时间"'))
        conn.execute(text('ALTER TABLE help_tasks MODIFY COLUMN completed_at DATETIME COMMENT "完成时间"'))
        conn.commit()
        
        # Wallets 表
        print('📝 添加 wallets 表注释...')
        conn.execute(text('ALTER TABLE wallets MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "钱包ID"'))
        conn.execute(text('ALTER TABLE wallets MODIFY COLUMN user_id INT COMMENT "关联用户ID"'))
        conn.execute(text('ALTER TABLE wallets MODIFY COLUMN balance DECIMAL(12,2) DEFAULT 0 COMMENT "可用余额"'))
        conn.execute(text('ALTER TABLE wallets MODIFY COLUMN frozen_amount DECIMAL(12,2) DEFAULT 0 COMMENT "冻结金额"'))
        conn.execute(text('ALTER TABLE wallets MODIFY COLUMN total_income DECIMAL(12,2) DEFAULT 0 COMMENT "总收入"'))
        conn.execute(text('ALTER TABLE wallets MODIFY COLUMN total_expense DECIMAL(12,2) DEFAULT 0 COMMENT "总支出"'))
        conn.execute(text('ALTER TABLE wallets MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间"'))
        conn.execute(text('ALTER TABLE wallets MODIFY COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "更新时间"'))
        conn.commit()
        
        # Transactions 表
        print('📝 添加 transactions 表注释...')
        conn.execute(text('ALTER TABLE transactions MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "交易记录ID"'))
        conn.execute(text('ALTER TABLE transactions MODIFY COLUMN wallet_id INT COMMENT "关联钱包ID"'))
        conn.execute(text('ALTER TABLE transactions MODIFY COLUMN user_id INT COMMENT "用户ID"'))
        conn.execute(text('ALTER TABLE transactions MODIFY COLUMN amount DECIMAL(12,2) NOT NULL COMMENT "交易金额"'))
        conn.execute(text('ALTER TABLE transactions MODIFY COLUMN balance_after DECIMAL(12,2) NOT NULL COMMENT "交易后余额"'))
        conn.execute(text('ALTER TABLE transactions MODIFY COLUMN related_user_id INT COMMENT "关联用户ID（转账对象）"'))
        conn.execute(text('ALTER TABLE transactions MODIFY COLUMN related_task_id INT COMMENT "关联任务ID"'))
        conn.execute(text('ALTER TABLE transactions MODIFY COLUMN description VARCHAR(255) COMMENT "交易描述"'))
        conn.execute(text('ALTER TABLE transactions MODIFY COLUMN status VARCHAR(20) DEFAULT "completed" COMMENT "交易状态"'))
        conn.execute(text('ALTER TABLE transactions MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "交易时间"'))
        conn.commit()
        
        # Friendships 表
        print('📝 添加 friendships 表注释...')
        conn.execute(text('ALTER TABLE friendships MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "好友关系ID"'))
        conn.execute(text('ALTER TABLE friendships MODIFY COLUMN user_id INT COMMENT "用户ID"'))
        conn.execute(text('ALTER TABLE friendships MODIFY COLUMN friend_id INT COMMENT "好友ID"'))
        conn.execute(text('ALTER TABLE friendships MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "添加时间"'))
        conn.commit()
        
        # Friend_requests 表
        print('📝 添加 friend_requests 表注释...')
        conn.execute(text('ALTER TABLE friend_requests MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "好友请求ID"'))
        conn.execute(text('ALTER TABLE friend_requests MODIFY COLUMN from_user_id INT COMMENT "发送者ID"'))
        conn.execute(text('ALTER TABLE friend_requests MODIFY COLUMN to_user_id INT COMMENT "接收者ID"'))
        conn.execute(text('ALTER TABLE friend_requests MODIFY COLUMN message TEXT COMMENT "请求消息"'))
        conn.execute(text('ALTER TABLE friend_requests MODIFY COLUMN status VARCHAR(20) DEFAULT "pending" COMMENT "状态：pending/accepted/rejected"'))
        conn.execute(text('ALTER TABLE friend_requests MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间"'))
        conn.execute(text('ALTER TABLE friend_requests MODIFY COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "更新时间"'))
        conn.commit()
        
        # Blacklist 表
        print('📝 添加 blacklist 表注释...')
        conn.execute(text('ALTER TABLE blacklist MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "黑名单记录ID"'))
        conn.execute(text('ALTER TABLE blacklist MODIFY COLUMN user_id INT COMMENT "用户ID"'))
        conn.execute(text('ALTER TABLE blacklist MODIFY COLUMN blocked_user_id INT COMMENT "被拉黑用户ID"'))
        conn.execute(text('ALTER TABLE blacklist MODIFY COLUMN reason VARCHAR(255) COMMENT "拉黑原因"'))
        conn.execute(text('ALTER TABLE blacklist MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "拉黑时间"'))
        conn.commit()
        
        # Announcements 表
        print('📝 添加 announcements 表注释...')
        conn.execute(text('ALTER TABLE announcements MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "公告ID"'))
        conn.execute(text('ALTER TABLE announcements MODIFY COLUMN title VARCHAR(255) NOT NULL COMMENT "公告标题"'))
        conn.execute(text('ALTER TABLE announcements MODIFY COLUMN content TEXT NOT NULL COMMENT "公告内容"'))
        conn.execute(text('ALTER TABLE announcements MODIFY COLUMN is_pinned TINYINT(1) DEFAULT 0 COMMENT "是否置顶"'))
        conn.execute(text('ALTER TABLE announcements MODIFY COLUMN publisher_id INT COMMENT "发布者ID"'))
        conn.execute(text('ALTER TABLE announcements MODIFY COLUMN view_count INT DEFAULT 0 COMMENT "浏览次数"'))
        conn.execute(text('ALTER TABLE announcements MODIFY COLUMN status VARCHAR(20) DEFAULT "published" COMMENT "发布状态"'))
        conn.execute(text('ALTER TABLE announcements MODIFY COLUMN publish_date DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "发布时间"'))
        conn.execute(text('ALTER TABLE announcements MODIFY COLUMN expire_date DATETIME COMMENT "过期时间"'))
        conn.execute(text('ALTER TABLE announcements MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间"'))
        conn.execute(text('ALTER TABLE announcements MODIFY COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "更新时间"'))
        conn.commit()
        
        # Notifications 表
        print('📝 添加 notifications 表注释...')
        conn.execute(text('ALTER TABLE notifications MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "通知ID"'))
        conn.execute(text('ALTER TABLE notifications MODIFY COLUMN user_id INT COMMENT "接收用户ID"'))
        conn.execute(text('ALTER TABLE notifications MODIFY COLUMN type VARCHAR(20) NOT NULL COMMENT "通知类型"'))
        conn.execute(text('ALTER TABLE notifications MODIFY COLUMN title VARCHAR(255) NOT NULL COMMENT "通知标题"'))
        conn.execute(text('ALTER TABLE notifications MODIFY COLUMN content TEXT COMMENT "通知内容"'))
        conn.execute(text('ALTER TABLE notifications MODIFY COLUMN related_id INT COMMENT "关联对象ID"'))
        conn.execute(text('ALTER TABLE notifications MODIFY COLUMN is_read TINYINT(1) DEFAULT 0 COMMENT "是否已读"'))
        conn.execute(text('ALTER TABLE notifications MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "创建时间"'))
        conn.commit()
        
        # Post_comments 表
        print('📝 添加 post_comments 表注释...')
        conn.execute(text('ALTER TABLE post_comments MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "评论ID"'))
        conn.execute(text('ALTER TABLE post_comments MODIFY COLUMN post_id INT COMMENT "关联帖子ID"'))
        conn.execute(text('ALTER TABLE post_comments MODIFY COLUMN user_id INT COMMENT "评论用户ID"'))
        conn.execute(text('ALTER TABLE post_comments MODIFY COLUMN parent_id INT COMMENT "父评论ID，用于回复"'))
        conn.execute(text('ALTER TABLE post_comments MODIFY COLUMN content TEXT NOT NULL COMMENT "评论内容"'))
        conn.execute(text('ALTER TABLE post_comments MODIFY COLUMN likes_count INT DEFAULT 0 COMMENT "点赞数"'))
        conn.execute(text('ALTER TABLE post_comments MODIFY COLUMN dislikes_count INT DEFAULT 0 COMMENT "拉踩数"'))
        conn.execute(text('ALTER TABLE post_comments MODIFY COLUMN reviewer_delete_count INT DEFAULT 0 COMMENT "审核员删除投票数"'))
        conn.execute(text('ALTER TABLE post_comments MODIFY COLUMN status VARCHAR(20) DEFAULT "active" COMMENT "状态：active/deleted"'))
        conn.execute(text('ALTER TABLE post_comments MODIFY COLUMN delete_reason VARCHAR(255) COMMENT "删除原因"'))
        conn.execute(text('ALTER TABLE post_comments MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "评论时间"'))
        conn.commit()
        
        # 其他关联表
        print('📝 添加其他表注释...')
        conn.execute(text('ALTER TABLE user_likes MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "点赞记录ID"'))
        conn.execute(text('ALTER TABLE user_likes MODIFY COLUMN from_user_id INT COMMENT "点赞者ID"'))
        conn.execute(text('ALTER TABLE user_likes MODIFY COLUMN to_user_id INT COMMENT "被点赞者ID"'))
        conn.execute(text('ALTER TABLE user_likes MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "点赞时间"'))
        
        conn.execute(text('ALTER TABLE post_tags MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "标签ID"'))
        conn.execute(text('ALTER TABLE post_tags MODIFY COLUMN post_id INT COMMENT "关联帖子ID"'))
        conn.execute(text('ALTER TABLE post_tags MODIFY COLUMN tag_name VARCHAR(50) NOT NULL COMMENT "标签名称"'))
        
        conn.execute(text('ALTER TABLE post_likes MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "点赞记录ID"'))
        conn.execute(text('ALTER TABLE post_likes MODIFY COLUMN post_id INT COMMENT "关联帖子ID"'))
        conn.execute(text('ALTER TABLE post_likes MODIFY COLUMN user_id INT COMMENT "点赞用户ID"'))
        conn.execute(text('ALTER TABLE post_likes MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "点赞时间"'))
        
        conn.execute(text('ALTER TABLE comment_likes MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "点赞记录ID"'))
        conn.execute(text('ALTER TABLE comment_likes MODIFY COLUMN comment_id INT COMMENT "关联评论ID"'))
        conn.execute(text('ALTER TABLE comment_likes MODIFY COLUMN user_id INT COMMENT "点赞用户ID"'))
        conn.execute(text('ALTER TABLE comment_likes MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "点赞时间"'))
        
        conn.execute(text('ALTER TABLE comment_dislikes MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "拉踩记录ID"'))
        conn.execute(text('ALTER TABLE comment_dislikes MODIFY COLUMN comment_id INT COMMENT "关联评论ID"'))
        conn.execute(text('ALTER TABLE comment_dislikes MODIFY COLUMN user_id INT COMMENT "拉踩用户ID"'))
        conn.execute(text('ALTER TABLE comment_dislikes MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "拉踩时间"'))
        
        conn.execute(text('ALTER TABLE task_applications MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "申请记录ID"'))
        conn.execute(text('ALTER TABLE task_applications MODIFY COLUMN task_id INT COMMENT "关联任务ID"'))
        conn.execute(text('ALTER TABLE task_applications MODIFY COLUMN applicant_id INT COMMENT "申请人ID"'))
        conn.execute(text('ALTER TABLE task_applications MODIFY COLUMN message TEXT COMMENT "申请留言"'))
        conn.execute(text('ALTER TABLE task_applications MODIFY COLUMN status VARCHAR(20) DEFAULT "pending" COMMENT "申请状态：pending/accepted/rejected"'))
        
        conn.execute(text('ALTER TABLE task_reviews MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "评价记录ID"'))
        conn.execute(text('ALTER TABLE task_reviews MODIFY COLUMN task_id INT COMMENT "关联任务ID"'))
        conn.execute(text('ALTER TABLE task_reviews MODIFY COLUMN reviewer_id INT COMMENT "评价人ID"'))
        conn.execute(text('ALTER TABLE task_reviews MODIFY COLUMN reviewed_user_id INT COMMENT "被评价人ID"'))
        conn.execute(text('ALTER TABLE task_reviews MODIFY COLUMN rating INT NOT NULL COMMENT "评分（1-5星）"'))
        conn.execute(text('ALTER TABLE task_reviews MODIFY COLUMN comment TEXT COMMENT "评价内容"'))
        
        conn.execute(text('ALTER TABLE reports MODIFY COLUMN id INT AUTO_INCREMENT COMMENT "举报记录ID"'))
        conn.execute(text('ALTER TABLE reports MODIFY COLUMN reporter_id INT COMMENT "举报人ID"'))
        conn.execute(text('ALTER TABLE reports MODIFY COLUMN target_type VARCHAR(20) NOT NULL COMMENT "举报对象类型"'))
        conn.execute(text('ALTER TABLE reports MODIFY COLUMN target_id INT NOT NULL COMMENT "举报对象ID"'))
        conn.execute(text('ALTER TABLE reports MODIFY COLUMN reason VARCHAR(255) NOT NULL COMMENT "举报原因"'))
        conn.execute(text('ALTER TABLE reports MODIFY COLUMN description TEXT COMMENT "详细描述"'))
        conn.execute(text('ALTER TABLE reports MODIFY COLUMN status VARCHAR(20) DEFAULT "pending" COMMENT "处理状态"'))
        
        conn.commit()
        print('✅ 所有表注释添加完成！')

if __name__ == '__main__':
    add_comments()
