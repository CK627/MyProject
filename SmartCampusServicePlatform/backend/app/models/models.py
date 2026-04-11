from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey, DECIMAL, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
import enum

# 枚举类型定义
class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"

class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    banned = "banned"

class PostStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    deleted = "deleted"

class TaskCategory(str, enum.Enum):
    errand = "errand"
    purchase = "purchase"
    study = "study"
    other = "other"

class TaskStatus(str, enum.Enum):
    open = "open"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    expired = "expired"

class AnnouncementType(str, enum.Enum):
    important = "important"
    notice = "notice"
    activity = "activity"
    academic = "academic"

class TransactionType(str, enum.Enum):
    recharge = "recharge"
    withdraw = "withdraw"
    transfer_in = "transfer_in"
    transfer_out = "transfer_out"
    task_reward = "task_reward"
    task_payment = "task_payment"
    refund = "refund"
    other = "other"

# 用户模型
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, comment="用户ID")
    email = Column(String(255), unique=True, index=True, nullable=False, comment="邮箱，唯一标识")
    password_hash = Column(String(255), nullable=True, comment="密码哈希值，OAuth用户可为空")
    name = Column(String(100), nullable=False, comment="用户姓名")
    phone = Column(String(20), comment="手机号码")
    avatar = Column(String(500), comment="头像URL")
    role = Column(Enum(UserRole), default=UserRole.student, comment="用户角色：student/teacher/admin")
    status = Column(Enum(UserStatus), default=UserStatus.active, comment="账户状态：active/inactive/banned")
    online_status = Column(String(20), default='offline', comment="在线状态: online/away/offline")
    last_active = Column(DateTime, comment="最后活跃时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    last_login = Column(DateTime, comment="最后登录时间")
    github_id = Column(String(100), nullable=True, unique=True, index=True, comment="GitHub OAuth用户ID")
    password_reset_token = Column(String(255), nullable=True, comment="密码重置token")
    password_reset_expires = Column(DateTime, nullable=True, comment="密码重置token过期时间")
    
    # 关系
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    posts = relationship("Post", back_populates="author")
    wallet = relationship("Wallet", back_populates="user", uselist=False)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True, comment="用户资料ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, comment="关联用户ID")
    student_id = Column(String(50), comment="学号")
    department = Column(String(100), comment="院系")
    major = Column(String(100), comment="专业")
    enroll_year = Column(Integer, comment="入学年份")
    bio = Column(Text, comment="个人简介")
    gender = Column(String(10), comment="性别")
    birthday = Column(DateTime, comment="生日")
    dormitory = Column(String(100), comment="宿舍")
    rating = Column(DECIMAL(3, 2), default=5.00, comment="用户评分")
    total_tasks_completed = Column(Integer, default=0, comment="完成任务总数")
    total_tasks_published = Column(Integer, default=0, comment="发布任务总数")
    # 信誉系统字段
    credit_score = Column(Integer, default=60, comment="信誉分，初始60分（及格）")
    like_count = Column(Integer, default=0, comment="获赞数")
    total_reviews = Column(Integer, default=0, comment="被评价总数，用于计算好评率")
    positive_reviews = Column(Integer, default=0, comment="好评数")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    user = relationship("User", back_populates="profile")
    
    @property
    def approval_rate(self):
        """好评率"""
        if self.total_reviews == 0:
            return 1.0  # 无评价时默认100%好评率
        return self.positive_reviews / self.total_reviews
    
    @property
    def priority_score(self):
        """优先分 = (信誉分 + 好评率 * 100) // 2"""
        return (self.credit_score + int(self.approval_rate * 100)) // 2


# 用户点赞模型（用户间互相点赞）
class UserLike(Base):
    __tablename__ = "user_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="点赞者ID")
    to_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="被点赞者ID")
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    from_user = relationship("User", foreign_keys=[from_user_id])
    to_user = relationship("User", foreign_keys=[to_user_id])

# 校园墙帖子模型
class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True, comment="帖子ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="发帖用户ID")
    content = Column(Text, nullable=False, comment="帖子内容")
    images = Column(JSON, comment="图片列表JSON")
    likes_count = Column(Integer, default=0, comment="点赞数")
    comments_count = Column(Integer, default=0, comment="评论数")
    shares_count = Column(Integer, default=0, comment="分享数")
    status = Column(Enum(PostStatus), default=PostStatus.approved, comment="审核状态：pending/approved/rejected/deleted")
    is_anonymous = Column(Boolean, default=False, comment="是否匿名发布")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    author = relationship("User", back_populates="posts")
    tags = relationship("PostTag", back_populates="post")
    comments = relationship("PostComment", back_populates="post")
    likes = relationship("PostLike", back_populates="post")

class PostTag(Base):
    __tablename__ = "post_tags"
    
    id = Column(Integer, primary_key=True, index=True, comment="标签ID")
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), comment="关联帖子ID")
    tag_name = Column(String(50), nullable=False, comment="标签名称")
    
    post = relationship("Post", back_populates="tags")

class PostLike(Base):
    __tablename__ = "post_likes"
    
    id = Column(Integer, primary_key=True, index=True, comment="点赞记录ID")
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), comment="关联帖子ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="点赞用户ID")
    created_at = Column(DateTime, server_default=func.now(), comment="点赞时间")
    
    post = relationship("Post", back_populates="likes")

class PostComment(Base):
    """帖子评论模型"""
    __tablename__ = "post_comments"
    
    id = Column(Integer, primary_key=True, index=True, comment="评论ID")
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), comment="关联帖子ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="评论用户ID")
    parent_id = Column(Integer, ForeignKey("post_comments.id", ondelete="SET NULL"), comment="父评论ID，用于回复")
    content = Column(Text, nullable=False, comment="评论内容")
    likes_count = Column(Integer, default=0, comment="点赞数")
    dislikes_count = Column(Integer, default=0, comment="拉踩数")
    reviewer_delete_count = Column(Integer, default=0, comment="审核员删除投票数")
    status = Column(String(20), default="active", comment="状态：active/deleted")
    delete_reason = Column(String(255), comment="删除原因")
    created_at = Column(DateTime, server_default=func.now(), comment="评论时间")
    
    post = relationship("Post", back_populates="comments")
    user = relationship("User")
    likes = relationship("CommentLike", back_populates="comment", cascade="all, delete-orphan")
    dislikes = relationship("CommentDislike", back_populates="comment", cascade="all, delete-orphan")
    reviewer_deletes = relationship("CommentReviewerDelete", back_populates="comment", cascade="all, delete-orphan")


class CommentLike(Base):
    """评论点赞模型"""
    __tablename__ = "comment_likes"
    
    id = Column(Integer, primary_key=True, index=True, comment="点赞记录ID")
    comment_id = Column(Integer, ForeignKey("post_comments.id", ondelete="CASCADE"), comment="关联评论ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="点赞用户ID")
    created_at = Column(DateTime, server_default=func.now(), comment="点赞时间")
    
    comment = relationship("PostComment", back_populates="likes")
    user = relationship("User")


class CommentDislike(Base):
    """评论拉踩模型（普通用户踩评论，达到条件自动删除）"""
    __tablename__ = "comment_dislikes"
    
    id = Column(Integer, primary_key=True, index=True, comment="拉踩记录ID")
    comment_id = Column(Integer, ForeignKey("post_comments.id", ondelete="CASCADE"), comment="关联评论ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="拉踩用户ID")
    created_at = Column(DateTime, server_default=func.now(), comment="拉踩时间")
    
    comment = relationship("PostComment", back_populates="dislikes")
    user = relationship("User")


class CommentReviewerDelete(Base):
    """审核员删除评论投票模型（3个审核员投票删除）"""
    __tablename__ = "comment_reviewer_deletes"
    
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("post_comments.id", ondelete="CASCADE"))
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    reason = Column(String(255), comment="删除原因")
    created_at = Column(DateTime, server_default=func.now())
    
    comment = relationship("PostComment", back_populates="reviewer_deletes")
    reviewer = relationship("User")

# 互助任务模型
class HelpTask(Base):
    __tablename__ = "help_tasks"
    
    id = Column(Integer, primary_key=True, index=True, comment="任务ID")
    publisher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="发布者ID")
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), comment="接单者ID")
    title = Column(String(200), nullable=False, comment="任务标题")
    description = Column(Text, nullable=False, comment="任务描述")
    category = Column(Enum(TaskCategory), default=TaskCategory.other, comment="任务分类：errand/purchase/study/other")
    reward = Column(DECIMAL(10, 2), default=0, comment="任务奖励金额")
    location = Column(String(255), comment="任务地点")
    deadline = Column(DateTime, comment="任务截止时间")
    status = Column(Enum(TaskStatus), default=TaskStatus.open, comment="任务状态：open/assigned/in_progress/completed/cancelled/expired")
    applicants_count = Column(Integer, default=0, comment="申请人数")
    private_info = Column(Text, comment="私密信息（快递码、手机尾号等），仅接单者可见")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    completed_at = Column(DateTime, comment="完成时间")
    
    publisher = relationship("User", foreign_keys=[publisher_id], backref="published_tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], backref="assigned_tasks")
    applications = relationship("TaskApplication", back_populates="task")

class TaskApplication(Base):
    __tablename__ = "task_applications"
    
    id = Column(Integer, primary_key=True, index=True, comment="申请记录ID")
    task_id = Column(Integer, ForeignKey("help_tasks.id", ondelete="CASCADE"), comment="关联任务ID")
    applicant_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="申请人ID")
    message = Column(Text, comment="申请留言")
    status = Column(String(20), default="pending", comment="申请状态：pending/accepted/rejected")
    created_at = Column(DateTime, server_default=func.now(), comment="申请时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    task = relationship("HelpTask", back_populates="applications")
    applicant = relationship("User", foreign_keys=[applicant_id])

class TaskReview(Base):
    __tablename__ = "task_reviews"
    
    id = Column(Integer, primary_key=True, index=True, comment="评价记录ID")
    task_id = Column(Integer, ForeignKey("help_tasks.id", ondelete="CASCADE"), comment="关联任务ID")
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="评价人ID")
    reviewed_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="被评价人ID")
    rating = Column(Integer, nullable=False, comment="评分（1-5星）")
    comment = Column(Text, comment="评价内容")
    created_at = Column(DateTime, server_default=func.now(), comment="评价时间")

# 好友和黑名单模型
class Friendship(Base):
    __tablename__ = "friendships"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="用户ID")
    friend_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="好友ID")
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    friend = relationship("User", foreign_keys=[friend_id])

class FriendRequest(Base):
    __tablename__ = "friend_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="发送者ID")
    to_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="接收者ID")
    message = Column(Text, comment="请求消息")
    status = Column(String(20), default="pending", comment="状态：pending/accepted/rejected")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    from_user = relationship("User", foreign_keys=[from_user_id], backref="sent_friend_requests")
    to_user = relationship("User", foreign_keys=[to_user_id], backref="received_friend_requests")

class Blacklist(Base):
    __tablename__ = "blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="用户ID")
    blocked_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="被拉黑用户ID")
    reason = Column(String(255), comment="拉黑原因")
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    blocked_user = relationship("User", foreign_keys=[blocked_user_id])

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True, comment="消息ID")
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="发送者ID")
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="接收者ID")
    content = Column(Text, nullable=False, comment="消息内容")
    message_type = Column(String(20), default="text", comment="消息类型：text/image/file")
    is_read = Column(Boolean, default=False, comment="是否已读")
    created_at = Column(DateTime, server_default=func.now(), comment="发送时间")
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

# 钱包模型
class Wallet(Base):
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True, comment="钱包ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, comment="关联用户ID")
    balance = Column(DECIMAL(12, 2), default=0, comment="可用余额")
    frozen_amount = Column(DECIMAL(12, 2), default=0, comment="冻结金额")
    total_income = Column(DECIMAL(12, 2), default=0, comment="总收入")
    total_expense = Column(DECIMAL(12, 2), default=0, comment="总支出")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    user = relationship("User", back_populates="wallet")
    transactions = relationship("Transaction", back_populates="wallet")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True, comment="交易记录ID")
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="CASCADE"), comment="关联钱包ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="用户ID")
    type = Column(Enum(TransactionType), nullable=False, comment="交易类型：recharge/withdraw/transfer_in/transfer_out/task_reward/task_payment/refund/other")
    amount = Column(DECIMAL(12, 2), nullable=False, comment="交易金额")
    balance_after = Column(DECIMAL(12, 2), nullable=False, comment="交易后余额")
    related_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), comment="关联用户ID（转账对象）")
    related_task_id = Column(Integer, ForeignKey("help_tasks.id", ondelete="SET NULL"), comment="关联任务ID")
    description = Column(String(255), comment="交易描述")
    status = Column(String(20), default="completed", comment="交易状态")
    created_at = Column(DateTime, server_default=func.now(), comment="交易时间")
    
    wallet = relationship("Wallet", back_populates="transactions")

class RechargeRecord(Base):
    __tablename__ = "recharge_records"
    
    id = Column(Integer, primary_key=True, index=True, comment="充值记录ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="用户ID")
    amount = Column(DECIMAL(12, 2), nullable=False, comment="充值金额")
    payment_method = Column(String(20), nullable=False, comment="支付方式")
    transaction_id = Column(String(100), comment="第三方交易号")
    status = Column(String(20), default="pending", comment="充值状态：pending/completed/failed")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    completed_at = Column(DateTime, comment="完成时间")

# 公告模型
class Announcement(Base):
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True, index=True, comment="公告ID")
    title = Column(String(255), nullable=False, comment="公告标题")
    content = Column(Text, nullable=False, comment="公告内容")
    type = Column(Enum(AnnouncementType), default=AnnouncementType.notice, comment="公告类型：important/notice/activity/academic")
    is_pinned = Column(Boolean, default=False, comment="是否置顶")
    publisher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="发布者ID")
    view_count = Column(Integer, default=0, comment="浏览次数")
    status = Column(String(20), default="published", comment="发布状态")
    publish_date = Column(DateTime, server_default=func.now(), comment="发布时间")
    expire_date = Column(DateTime, comment="过期时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

class AnnouncementRead(Base):
    __tablename__ = "announcement_reads"
    
    id = Column(Integer, primary_key=True, index=True, comment="阅读记录ID")
    announcement_id = Column(Integer, ForeignKey("announcements.id", ondelete="CASCADE"), comment="关联公告ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="阅读用户ID")
    read_at = Column(DateTime, server_default=func.now(), comment="阅读时间")

# 学校信息模型
class SchoolInfo(Base):
    __tablename__ = "school_info"
    
    id = Column(Integer, primary_key=True, index=True, comment="学校信息ID")
    name = Column(String(100), nullable=False, comment="学校名称")
    founded_year = Column(Integer, comment="建校年份")
    type = Column(String(100), comment="学校类型")
    motto = Column(String(255), comment="校训")
    location = Column(String(255), comment="学校地址")
    website = Column(String(255), comment="官方网站")
    phone = Column(String(50), comment="联系电话")
    email = Column(String(100), comment="联系邮箱")
    description = Column(Text, comment="学校简介")
    logo = Column(String(500), comment="学校logo URL")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

class Department(Base):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True, comment="院系ID")
    name = Column(String(100), nullable=False, comment="院系名称")
    description = Column(Text, comment="院系简介")
    student_count = Column(Integer, default=0, comment="学生人数")
    ranking = Column(String(50), comment="学科排名")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

class Facility(Base):
    __tablename__ = "facilities"
    
    id = Column(Integer, primary_key=True, index=True, comment="设施ID")
    name = Column(String(100), nullable=False, comment="设施名称")
    type = Column(String(50), comment="设施类型")
    description = Column(Text, comment="设施描述")
    location = Column(String(255), comment="设施位置")
    open_time = Column(String(100), comment="开放时间")
    image = Column(String(500), comment="设施图片URL")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True, comment="通知ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="接收用户ID")
    type = Column(String(20), nullable=False, comment="通知类型")
    title = Column(String(255), nullable=False, comment="通知标题")
    content = Column(Text, comment="通知内容")
    related_id = Column(Integer, comment="关联对象ID")
    is_read = Column(Boolean, default=False, comment="是否已读")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True, comment="举报记录ID")
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="举报人ID")
    target_type = Column(String(20), nullable=False, comment="举报对象类型：post/comment/user等")
    target_id = Column(Integer, nullable=False, comment="举报对象ID")
    reason = Column(String(255), nullable=False, comment="举报原因")
    description = Column(Text, comment="详细描述")
    status = Column(String(20), default="pending", comment="处理状态：pending/processing/resolved/rejected")
    handled_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), comment="处理人ID")
    handled_at = Column(DateTime, comment="处理时间")
    result = Column(Text, comment="处理结果")
    created_at = Column(DateTime, server_default=func.now(), comment="举报时间")
