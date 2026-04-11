// API服务层 - 连接后端API

// 使用Next.js代理，避免跨域问题
const API_BASE_URL = '/api/v1';

// Token管理
export const getToken = (): string | null => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('access_token');
  }
  return null;
};

export const setToken = (token: string): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', token);
  }
};

export const removeToken = (): void => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
  }
};

// 通用请求方法
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(error.detail || '请求失败');
  }
  
  return response.json();
}

// ============ 认证 API ============
export interface LoginRequest {
  username: string;  // email
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  phone?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
  phone?: string;
  avatar?: string;
  role: 'student' | 'teacher' | 'admin';
  status: string;
  online_status?: 'online' | 'away' | 'offline';
  last_active?: string;
  created_at: string;
  last_login?: string;
}

export const authApi = {
  // 登录
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const formData = new URLSearchParams();
    formData.append('username', data.username);
    formData.append('password', data.password);
    
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '登录失败' }));
      throw new Error(error.detail || '登录失败');
    }
    
    return response.json();
  },
  
  // 注册
  register: async (data: RegisterRequest): Promise<User> => {
    return request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  
  // 获取当前用户信息
  getCurrentUser: async (): Promise<User> => {
    return request<User>('/auth/me');
  },
  
  // 退出登录
  logout: async (): Promise<void> => {
    try {
      await request('/activity/logout', { method: 'POST' });
    } finally {
      removeToken();
    }
  },
  
  // 用户心跳 - 定期调用表示在线
  heartbeat: async (): Promise<void> => {
    return request('/activity/heartbeat', { method: 'POST' });
  },
  
  // 修改密码
  changePassword: async (oldPassword: string, newPassword: string): Promise<void> => {
    return request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
  },

  // 忘记密码 - 发送重置邮件
  forgotPassword: async (email: string): Promise<void> => {
    return request('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  // 重置密码
  resetPassword: async (token: string, newPassword: string): Promise<void> => {
    return request('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword }),
    });
  },

  // GitHub OAuth回调
  githubCallback: async (code: string): Promise<TokenResponse> => {
    return request<TokenResponse>('/auth/github/callback', {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
  },
};

// ============ 帖子 API ============
export interface Post {
  id: number;
  user_id: number;
  content: string;
  images?: string[];
  likes_count: number;
  comments_count: number;
  shares_count: number;
  status: string;
  is_anonymous: boolean;
  created_at: string;
  updated_at: string;
  author?: User;
  tags?: { id: number; tag_name: string }[];
}

export interface PostListResponse {
  items: Post[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreatePostRequest {
  content: string;
  images?: string;
  is_anonymous?: boolean;
  tag_ids?: number[];
}

// 审核员状态
export interface ReviewerStatus {
  is_reviewer: boolean;
  credit_score: number;
  required_score: number;
  is_admin: boolean;
}

// 审核统计
export interface ReviewStats {
  pending: number;
  approved: number;
  rejected: number;
}

// 评论（增强版）
export interface Comment {
  id: number;
  post_id: number;
  user_id: number;
  content: string;
  parent_id?: number;
  likes_count: number;
  dislikes_count: number;
  reviewer_delete_count: number;
  status: string;
  delete_reason?: string;
  created_at: string;
  user?: User;
  liked?: boolean;
  disliked?: boolean;
}

// 评论交互状态
export interface CommentInteractionStatus {
  liked: boolean;
  disliked: boolean;
}

// 通知
export interface Notification {
  id: number;
  user_id: number;
  type: string;
  title: string;
  content: string;
  related_id?: number;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}

// 消息
export interface Message {
  id: number;
  sender_id: number;
  receiver_id: number;
  content: string;
  message_type: string;
  is_read: boolean;
  created_at: string;
  sender?: User;
  receiver?: User;
}

export interface Conversation {
  user: User;
  last_message?: Message;
  unread_count: number;
}

export const postsApi = {
  // 获取热门帖子
  getHotPosts: async (limit = 5): Promise<PostListResponse> => {
    return request<PostListResponse>(`/posts/hot?limit=${limit}`);
  },

  // 获取帖子列表
  getPosts: async (page = 1, pageSize = 20, keyword?: string): Promise<PostListResponse> => {
    let url = `/posts?page=${page}&page_size=${pageSize}`;
    if (keyword) url += `&keyword=${encodeURIComponent(keyword)}`;
    return request<PostListResponse>(url);
  },
  
  // 获取我的帖子
  getMyPosts: async (page = 1, pageSize = 20): Promise<PostListResponse> => {
    return request<PostListResponse>(`/posts/my?page=${page}&page_size=${pageSize}`);
  },
  
  // 创建帖子
  createPost: async (data: CreatePostRequest): Promise<Post> => {
    return request<Post>('/posts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  
  // 点赞
  likePost: async (postId: number): Promise<void> => {
    await request(`/posts/${postId}/like`, { method: 'POST' });
  },
  
  // 取消点赞
  unlikePost: async (postId: number): Promise<void> => {
    await request(`/posts/${postId}/like`, { method: 'DELETE' });
  },
  
  // 发表评论
  createComment: async (postId: number, content: string): Promise<void> => {
    await request(`/posts/${postId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },
  
  // 获取评论列表
  getComments: async (postId: number, page = 1, pageSize = 50): Promise<Comment[]> => {
    return request<Comment[]>(`/posts/${postId}/comments?page=${page}&page_size=${pageSize}`);
  },
  
  // 删除评论
  deleteComment: async (postId: number, commentId: number, reason?: string): Promise<void> => {
    let url = `/posts/${postId}/comments/${commentId}`;
    if (reason) url += `?reason=${encodeURIComponent(reason)}`;
    await request(url, { method: 'DELETE' });
  },
  
  // 点赞评论
  likeComment: async (postId: number, commentId: number): Promise<void> => {
    await request(`/posts/${postId}/comments/${commentId}/like`, { method: 'POST' });
  },
  
  // 取消评论点赞
  unlikeComment: async (postId: number, commentId: number): Promise<void> => {
    await request(`/posts/${postId}/comments/${commentId}/like`, { method: 'DELETE' });
  },
  
  // 拉踩评论
  dislikeComment: async (postId: number, commentId: number): Promise<void> => {
    await request(`/posts/${postId}/comments/${commentId}/dislike`, { method: 'POST' });
  },
  
  // 取消拉踩
  undislikeComment: async (postId: number, commentId: number): Promise<void> => {
    await request(`/posts/${postId}/comments/${commentId}/dislike`, { method: 'DELETE' });
  },
  
  // 审核员投票删除评论
  reviewerDeleteComment: async (postId: number, commentId: number, reason: string): Promise<void> => {
    await request(`/posts/${postId}/comments/${commentId}/reviewer-delete?reason=${encodeURIComponent(reason)}`, { method: 'POST' });
  },
  
  // 获取评论互动状态
  getCommentInteractionStatus: async (postId: number, commentId: number): Promise<CommentInteractionStatus> => {
    return request<CommentInteractionStatus>(`/posts/${postId}/comments/${commentId}/interaction-status`);
  },
  
  // 获取帖子详情
  getPost: async (postId: number): Promise<Post> => {
    return request<Post>(`/posts/${postId}`);
  },
  
  // 检查点赞状态
  checkLikeStatus: async (postId: number): Promise<{ liked: boolean }> => {
    return request<{ liked: boolean }>(`/posts/${postId}/like-status`);
  },
  
  // ============ 审核相关 API ============
  
  // 检查审核员权限
  checkReviewerStatus: async (): Promise<ReviewerStatus> => {
    return request<ReviewerStatus>('/posts/review/check');
  },
  
  // 获取待审核帖子
  getPendingPosts: async (page = 1, pageSize = 20): Promise<PostListResponse> => {
    return request<PostListResponse>(`/posts/review/pending?page=${page}&page_size=${pageSize}`);
  },
  
  // 审核通过
  approvePost: async (postId: number): Promise<void> => {
    await request(`/posts/review/${postId}/approve`, { method: 'POST' });
  },
  
  // 审核拒绝
  rejectPost: async (postId: number, reason?: string): Promise<void> => {
    let url = `/posts/review/${postId}/reject`;
    if (reason) url += `?reason=${encodeURIComponent(reason)}`;
    await request(url, { method: 'POST' });
  },
  
  // 获取审核统计
  getReviewStats: async (): Promise<ReviewStats> => {
    return request<ReviewStats>('/posts/review/stats');
  },
};

// ============ 任务 API ============
export interface Task {
  id: number;
  publisher_id: number;
  assignee_id?: number;
  title: string;
  description: string;
  category: 'errand' | 'purchase' | 'study' | 'other';
  reward: number;
  location?: string;
  deadline?: string;
  status: 'open' | 'assigned' | 'in_progress' | 'completed' | 'cancelled' | 'expired';
  application_count: number;
  created_at: string;
  publisher?: User;
  assignee?: User;
  private_info?: string;  // 私密信息，仅接单者和发布者可见
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateTaskRequest {
  title: string;
  description: string;
  category: string;
  reward: number;
  location?: string;
  deadline?: string;
  private_info?: string;  // 私密信息（快递码、手机尾号等）
}

export const tasksApi = {
  // 获取任务列表
  getTasks: async (page = 1, pageSize = 20, category?: string, status?: string): Promise<TaskListResponse> => {
    let url = `/tasks?page=${page}&page_size=${pageSize}`;
    if (category) url += `&category=${category}`;
    if (status) url += `&status=${status}`;
    return request<TaskListResponse>(url);
  },
  
  // 获取我发布的任务
  getMyPublishedTasks: async (page = 1, pageSize = 20): Promise<TaskListResponse> => {
    return request<TaskListResponse>(`/tasks/my/published?page=${page}&page_size=${pageSize}`);
  },
  
  // 获取我接受的任务
  getMyAcceptedTasks: async (page = 1, pageSize = 20): Promise<TaskListResponse> => {
    return request<TaskListResponse>(`/tasks/my/accepted?page=${page}&page_size=${pageSize}`);
  },
  
  // 获取我申请过的任务ID列表
  getMyAppliedTaskIds: async (): Promise<{ task_ids: number[] }> => {
    return request<{ task_ids: number[] }>('/tasks/my/applied-ids');
  },
  
  // 创建任务
  createTask: async (data: CreateTaskRequest): Promise<Task> => {
    return request<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  
  // 申请任务
  applyTask: async (taskId: number, message?: string): Promise<void> => {
    await request(`/tasks/${taskId}/apply`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },
  
  // 删除/取消任务
  deleteTask: async (taskId: number): Promise<void> => {
    await request(`/tasks/${taskId}`, { method: 'DELETE' });
  },
  
  // 完成任务
  completeTask: async (taskId: number): Promise<void> => {
    await request(`/tasks/${taskId}/complete`, { method: 'POST' });
  },
  
  // 获取任务申请列表
  getApplications: async (taskId: number): Promise<TaskApplication[]> => {
    return request<TaskApplication[]>(`/tasks/${taskId}/applications`);
  },
  
  // 接受申请
  acceptApplication: async (taskId: number, applicationId: number): Promise<void> => {
    await request(`/tasks/${taskId}/applications/${applicationId}/accept`, { method: 'POST' });
  },
};

// 任务申请类型
export interface TaskApplication {
  id: number;
  task_id: number;
  applicant_id: number;
  status: string;
  message?: string;
  created_at: string;
  applicant?: User;
  priority_score?: number;  // 优先分 = (信誉分 + 好评率 * 100) // 2
}

// 用户信誉信息
export interface UserCreditInfo {
  user_id: number;
  name: string;
  credit_score: number;     // 信誉分，初始60
  like_count: number;       // 获赞数
  approval_rate: number;    // 好评率 0-1
  priority_score: number;   // 优先分
}

// 用户点赞 API
export const userLikeApi = {
  // 点赞用户
  likeUser: async (userId: number): Promise<void> => {
    await request(`/auth/users/${userId}/like`, { method: 'POST' });
  },
  
  // 取消点赞
  unlikeUser: async (userId: number): Promise<void> => {
    await request(`/auth/users/${userId}/like`, { method: 'DELETE' });
  },
  
  // 获取点赞状态
  getLikeStatus: async (userId: number): Promise<{ liked: boolean }> => {
    return request(`/auth/users/${userId}/like-status`);
  },
  
  // 获取用户信誉信息
  getUserCredit: async (userId: number): Promise<UserCreditInfo> => {
    return request(`/auth/users/${userId}/profile`);
  },
};

// ============ 钱包 API ============
export interface Wallet {
  id: number;
  user_id: number;
  balance: number;
  frozen_amount: number;
  total_income: number;
  total_expense: number;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: number;
  wallet_id: number;
  user_id: number;
  type: string;
  amount: number;
  balance_after: number;
  description?: string;
  status: string;
  created_at: string;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const walletApi = {
  // 获取钱包信息
  getWallet: async (): Promise<Wallet> => {
    return request<Wallet>('/wallet');
  },
  
  // 获取交易记录
  getTransactions: async (page = 1, pageSize = 20, type?: string): Promise<TransactionListResponse> => {
    let url = `/wallet/transactions?page=${page}&page_size=${pageSize}`;
    if (type) url += `&type=${type}`;
    return request<TransactionListResponse>(url);
  },
  
  // 充值
  recharge: async (amount: number, paymentMethod: string): Promise<{ order_no: string }> => {
    return request('/wallet/recharge', {
      method: 'POST',
      body: JSON.stringify({ amount, payment_method: paymentMethod }),
    });
  },
  
  // 确认充值
  confirmRecharge: async (orderNo: string): Promise<void> => {
    await request(`/wallet/recharge/${orderNo}/confirm`, { method: 'POST' });
  },
};

// ============ 公告 API ============
export interface Announcement {
  id: number;
  title: string;
  content: string;
  type: 'important' | 'notice' | 'activity' | 'academic';
  is_pinned: boolean;
  publisher_id: number;
  view_count: number;
  status: string;
  publish_date: string;
  is_read?: boolean;
}

export interface AnnouncementListResponse {
  items: Announcement[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const announcementsApi = {
  // 获取公开公告列表（无需登录）
  getPublicAnnouncements: async (page = 1, pageSize = 20, type?: string): Promise<AnnouncementListResponse> => {
    let url = `/announcements/public?page=${page}&page_size=${pageSize}`;
    if (type) url += `&type=${type}`;
    return request<AnnouncementListResponse>(url);
  },

  // 获取公告列表
  getAnnouncements: async (page = 1, pageSize = 20, type?: string): Promise<AnnouncementListResponse> => {
    let url = `/announcements?page=${page}&page_size=${pageSize}`;
    if (type) url += `&type=${type}`;
    return request<AnnouncementListResponse>(url);
  },
  
  // 获取公告详情
  getAnnouncement: async (id: number): Promise<Announcement> => {
    return request<Announcement>(`/announcements/${id}`);
  },
};

// ============ 好友 API ============
export interface Friend {
  id: number;
  user_id: number;
  friend_id: number;
  created_at: string;
  friend?: User;
}

export interface FriendListResponse {
  items: Friend[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FriendRequest {
  id: number;
  sender_id: number;
  receiver_id: number;
  message?: string;
  status: string;
  created_at: string;
  from_user?: User;
  to_user?: User;
}

export const friendsApi = {
  // 获取好友列表
  getFriends: async (page = 1, pageSize = 50): Promise<FriendListResponse> => {
    return request<FriendListResponse>(`/friends?page=${page}&page_size=${pageSize}`);
  },
  
  // 获取在线好友ID列表
  getOnlineFriends: async (): Promise<number[]> => {
    return request<number[]>('/friends/online');
  },
  
  // 获取收到的好友请求
  getReceivedRequests: async (): Promise<{ items: FriendRequest[]; total: number }> => {
    return request('/friends/requests/received');
  },
  
  // 发送好友请求
  sendFriendRequest: async (toUserId: number, message?: string): Promise<void> => {
    await request('/friends/requests', {
      method: 'POST',
      body: JSON.stringify({ to_user_id: toUserId, message }),
    });
  },
  
  // 接受好友请求
  acceptRequest: async (requestId: number): Promise<void> => {
    await request(`/friends/requests/${requestId}/accept`, { method: 'POST' });
  },
  
  // 拒绝好友请求
  rejectRequest: async (requestId: number): Promise<void> => {
    await request(`/friends/requests/${requestId}/reject`, { method: 'POST' });
  },
  
  // 删除好友
  removeFriend: async (friendId: number): Promise<void> => {
    await request(`/friends/${friendId}`, { method: 'DELETE' });
  },
};

// ============ 黑名单 API ============
export interface BlacklistItem {
  id: number;
  user_id: number;
  blocked_user_id: number;
  reason?: string;
  created_at: string;
  blocked_user?: User;
}

export interface BlacklistListResponse {
  items: BlacklistItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const blacklistApi = {
  // 获取黑名单
  getBlacklist: async (page = 1, pageSize = 50): Promise<BlacklistListResponse> => {
    return request<BlacklistListResponse>(`/friends/blacklist?page=${page}&page_size=${pageSize}`);
  },
  
  // 添加黑名单
  addToBlacklist: async (blockedUserId: number, reason?: string): Promise<void> => {
    await request('/friends/blacklist', {
      method: 'POST',
      body: JSON.stringify({ blocked_user_id: blockedUserId, reason }),
    });
  },
  
  // 移出黑名单
  removeFromBlacklist: async (blockedUserId: number): Promise<void> => {
    await request(`/friends/blacklist/${blockedUserId}`, { method: 'DELETE' });
  },
};

// ============ 消息 API ============
export const messagesApi = {
  // 获取会话列表
  getConversations: async (): Promise<{ items: Conversation[]; total: number }> => {
    return request('/messages/conversations');
  },
  
  // 获取与某用户的消息
  getMessagesWithUser: async (userId: number, page = 1, pageSize = 50): Promise<{ items: Message[]; total: number }> => {
    return request(`/messages/with/${userId}?page=${page}&page_size=${pageSize}`);
  },
  
  // 发送消息
  sendMessage: async (receiverId: number, content: string, type: 'text' | 'image' | 'file' = 'text'): Promise<Message> => {
    return request<Message>('/messages', {
      method: 'POST',
      body: JSON.stringify({ receiver_id: receiverId, content, type }),
    });
  },
  
  // 删除会话
  deleteConversation: async (userId: number): Promise<void> => {
    await request(`/messages/conversations/${userId}`, { method: 'DELETE' });
  },
  
  // 清除聊天记录
  clearChatHistory: async (userId: number): Promise<void> => {
    await request(`/messages/with/${userId}/clear`, { method: 'DELETE' });
  },
};

// ============ 通知 API ============
export const notificationsApi = {
  // 获取通知列表
  getNotifications: async (page = 1, pageSize = 20, type?: string): Promise<NotificationListResponse> => {
    let url = `/messages/notifications?page=${page}&page_size=${pageSize}`;
    if (type) url += `&type=${type}`;
    return request<NotificationListResponse>(url);
  },
  
  // 标记所有通知已读
  markAllRead: async (): Promise<void> => {
    await request('/messages/notifications/read-all', { method: 'POST' });
  },
};

// ============ 学校信息 API ============
export interface SchoolInfo {
  id: number;
  name: string;
  founded_year?: number;
  type?: string;
  motto?: string;
  location?: string;
  website?: string;
  phone?: string;
  email?: string;
  description?: string;
  logo?: string;
}

export interface Department {
  id: number;
  name: string;
  description?: string;
  student_count: number;
  ranking?: string;
}

export interface Facility {
  id: number;
  name: string;
  type?: string;
  description?: string;
  location?: string;
  open_time?: string;
  image?: string;
}

export const schoolApi = {
  // 获取学校信息
  getSchoolInfo: async (): Promise<SchoolInfo> => {
    return request<SchoolInfo>('/school/info');
  },
  
  // 获取院系列表
  getDepartments: async (): Promise<Department[]> => {
    return request<Department[]>('/school/departments');
  },
  
  // 获取设施列表
  getFacilities: async (type?: string): Promise<Facility[]> => {
    let url = '/school/facilities';
    if (type) url += `?type=${type}`;
    return request<Facility[]>(url);
  },
};

// ============ 用户档案类型 ============
export interface UserProfileUpdate {
  student_id?: string;
  department?: string;
  major?: string;
  grade?: string;
  gender?: 'male' | 'female' | 'other';
  birthday?: string;
  bio?: string;
  dormitory?: string;
}

export interface UserProfile {
  id: number;
  user_id: number;
  student_id?: string;
  department?: string;
  major?: string;
  grade?: string;
  gender?: 'male' | 'female' | 'other';
  birthday?: string;
  bio?: string;
  dormitory?: string;
  credit_score: number;
  like_count: number;
  total_reviews: number;
  positive_reviews: number;
}

// ============ 用户 API ============
export const usersApi = {
  // 获取用户详细信息
  getMyProfile: async (): Promise<User> => {
    return request<User>('/users/me');
  },
  
  // 更新用户信息
  updateMyProfile: async (data: { name?: string; phone?: string; avatar?: string }): Promise<User> => {
    return request<User>('/users/me', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },
  
  // 更新用户详细档案
  updateMyDetailProfile: async (data: UserProfileUpdate): Promise<User> => {
    return request<User>('/users/me/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },
  
  // 搜索用户
  searchUsers: async (keyword: string, page = 1, pageSize = 20): Promise<User[]> => {
    return request<User[]>(`/users?keyword=${encodeURIComponent(keyword)}&page=${page}&page_size=${pageSize}`);
  },
  
  // 获取指定用户详细信息（包含档案）
  getUserDetail: async (userId: number): Promise<User & { profile?: UserProfile }> => {
    return request<User & { profile?: UserProfile }>(`/users/${userId}/detail`);
  },
};

// ============ 管理员 API ============
export const adminApi = {
  // 获取公开平台统计（无需登录）
  getPublicStats: async (): Promise<{
    user_count: number;
    post_count: number;
    task_count: number;
    open_task_count: number;
  }> => {
    return request('/admin/public-stats');
  },

  // 获取平台统计
  getStats: async (): Promise<{
    user_count: number;
    active_user_count: number;
    post_count: number;
    task_count: number;
    open_task_count: number;
    pending_report_count: number;
  }> => {
    return request('/admin/stats');
  },
  
  // 获取举报列表
  getReports: async (status = 'pending', page = 1, pageSize = 20): Promise<any[]> => {
    return request(`/admin/reports?status=${status}&page=${page}&page_size=${pageSize}`);
  },
  
  // 处理举报
  resolveReport: async (reportId: number, action: 'approve' | 'reject'): Promise<void> => {
    await request(`/admin/reports/${reportId}/resolve?action=${action}`, { method: 'POST' });
  },
};

// ============ 文件上传 API ============
export interface UploadedFile {
  file_id: number;
  file_hash: string;
  file_size: number;
  mime_type: string;
  reference_count: number;
}

export const filesApi = {
  // 上传文件
  uploadFile: async (file: File): Promise<UploadedFile> => {
    const token = getToken();
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/files/upload`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '上传失败' }));
      throw new Error(error.detail || '上传失败');
    }
    
    return response.json();
  },
  
  // 获取文件URL
  getFileUrl: (fileId: number): string => {
    return `${API_BASE_URL}/files/${fileId}`;
  },
};
