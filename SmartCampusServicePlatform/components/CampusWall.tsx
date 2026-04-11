'use client'

import React, { useState, useEffect } from 'react'
import { 
  Heart, 
  MessageCircle, 
  Share2, 
  MoreHorizontal, 
  Image as ImageIcon,
  Send,
  TrendingUp,
  Clock,
  Flame,
  Loader2,
  Shield,
  CheckCircle,
  XCircle,
  AlertCircle,
  X,
  Users,
  Search
} from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { 
  postsApi, 
  Post as ApiPost, 
  getToken, 
  ReviewerStatus, 
  ReviewStats,
  friendsApi,
  messagesApi,
  Friend
} from '@/lib/api'

interface Post {
  id: number
  author: {
    id: number
    name: string
    avatar?: string
    department: string
  }
  content: string
  images?: string[]
  likes: number
  comments: number
  shares: number
  time: string
  tags: string[]
  liked: boolean
  status: string
}

const filters = [
  { id: 'hot', label: '热门', icon: Flame },
  { id: 'new', label: '最新', icon: Clock },
  { id: 'trending', label: '趋势', icon: TrendingUp },
]

// 格式化时间
function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  
  return date.toLocaleDateString('zh-CN')
}

// 转换API数据到本地格式
function convertPost(apiPost: ApiPost): Post {
  return {
    id: apiPost.id,
    author: {
      id: apiPost.user_id,
      name: apiPost.author?.name || '匿名用户',
      avatar: apiPost.author?.avatar,
      department: '校园用户'
    },
    content: apiPost.content,
    images: apiPost.images,
    likes: apiPost.likes_count,
    comments: apiPost.comments_count,
    shares: apiPost.shares_count,
    time: formatTime(apiPost.created_at),
    tags: apiPost.tags?.map(t => t.tag_name) || [],
    liked: false,
    status: apiPost.status
  }
}

// 状态徽章组件
function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'pending':
      return <Badge variant="warning" className="gap-1"><AlertCircle className="w-3 h-3" />待审核</Badge>
    case 'approved':
      return <Badge variant="success" className="gap-1"><CheckCircle className="w-3 h-3" />已通过</Badge>
    case 'rejected':
      return <Badge variant="destructive" className="gap-1"><XCircle className="w-3 h-3" />已拒绝</Badge>
    default:
      return null
  }
}

interface CampusWallProps {
  onNavigate?: (page: string, data?: any) => void
}

export function CampusWall({ onNavigate }: CampusWallProps) {
  const [posts, setPosts] = useState<Post[]>([])
  const [pendingPosts, setPendingPosts] = useState<Post[]>([])
  const [newPost, setNewPost] = useState('')
  const [activeFilter, setActiveFilter] = useState('hot')
  const [loading, setLoading] = useState(true)
  const [posting, setPosting] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  
  // 分享相关状态
  const [shareModalPost, setShareModalPost] = useState<Post | null>(null)
  const [friends, setFriends] = useState<Friend[]>([])
  const [friendsLoading, setFriendsLoading] = useState(false)
  const [friendSearch, setFriendSearch] = useState('')
  const [sharingTo, setSharingTo] = useState<number | null>(null)
  
  // 审核相关状态
  const [isReviewer, setIsReviewer] = useState(false)
  const [reviewerStatus, setReviewerStatus] = useState<ReviewerStatus | null>(null)
  const [showReviewPanel, setShowReviewPanel] = useState(false)
  const [reviewStats, setReviewStats] = useState<ReviewStats | null>(null)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [processingId, setProcessingId] = useState<number | null>(null)

  // 加载帖子和检查审核员权限
  useEffect(() => {
    loadPosts()
    checkReviewerStatus()
  }, [])

  const checkReviewerStatus = async () => {
    if (!getToken()) return
    try {
      const status = await postsApi.checkReviewerStatus()
      setReviewerStatus(status)
      setIsReviewer(status.is_reviewer)
      if (status.is_reviewer) {
        loadReviewStats()
      }
    } catch (err) {
      console.error('Failed to check reviewer status:', err)
    }
  }

  const loadReviewStats = async () => {
    try {
      const stats = await postsApi.getReviewStats()
      setReviewStats(stats)
    } catch (err) {
      console.error('Failed to load review stats:', err)
    }
  }

  const loadPosts = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await postsApi.getPosts(1, 20)
      const postsData = response.items.map(convertPost)
      
      // 检查每个帖子的点赞状态
      if (getToken()) {
        const likeStatusPromises = postsData.map(async (post) => {
          try {
            const { liked } = await postsApi.checkLikeStatus(post.id)
            return { ...post, liked }
          } catch {
            return post
          }
        })
        const postsWithLikes = await Promise.all(likeStatusPromises)
        setPosts(postsWithLikes)
      } else {
        setPosts(postsData)
      }
    } catch (err: any) {
      setError('加载失败，请重试')
      console.error('Failed to load posts:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadPendingPosts = async () => {
    setReviewLoading(true)
    try {
      const response = await postsApi.getPendingPosts(1, 50)
      setPendingPosts(response.items.map(convertPost))
      loadReviewStats()
    } catch (err: any) {
      setError('加载待审核帖子失败')
      console.error('Failed to load pending posts:', err)
    } finally {
      setReviewLoading(false)
    }
  }

  // 点赞功能
  const handleLike = async (postId: number) => {
    if (!getToken()) {
      setError('请先登录')
      return
    }
    
    const post = posts.find(p => p.id === postId)
    if (!post) return

    // 乐观更新
    setPosts(posts.map(p => {
      if (p.id === postId) {
        return {
          ...p,
          liked: !p.liked,
          likes: p.liked ? p.likes - 1 : p.likes + 1
        }
      }
      return p
    }))

    try {
      if (post.liked) {
        await postsApi.unlikePost(postId)
      } else {
        await postsApi.likePost(postId)
      }
    } catch (err: any) {
      // 回滚
      setPosts(posts.map(p => {
        if (p.id === postId) {
          return {
            ...p,
            liked: post.liked,
            likes: post.likes
          }
        }
        return p
      }))
      console.error('Like failed:', err)
    }
  }

  // 打开分享弹窗
  const openShareModal = async (post: Post) => {
    if (!getToken()) {
      setError('请先登录')
      return
    }
    setShareModalPost(post)
    setFriendsLoading(true)
    try {
      const response = await friendsApi.getFriends(1, 100)
      setFriends(response.items)
    } catch (err) {
      console.error('Failed to load friends:', err)
    } finally {
      setFriendsLoading(false)
    }
  }

  // 分享给好友
  const handleShareToFriend = async (friendUserId: number) => {
    if (!shareModalPost) return
    
    setSharingTo(friendUserId)
    try {
      const shareContent = `[分享帖子] ${shareModalPost.author.name}的动态:\n"${shareModalPost.content.slice(0, 100)}${shareModalPost.content.length > 100 ? '...' : ''}"`
      await messagesApi.sendMessage(friendUserId, shareContent, 'text')
      
      // 更新分享数
      setPosts(posts.map(p => 
        p.id === shareModalPost.id ? { ...p, shares: p.shares + 1 } : p
      ))
      
      setSuccessMessage('分享成功！')
      setTimeout(() => setSuccessMessage(''), 3000)
      setShareModalPost(null)
    } catch (err: any) {
      setError(err.message || '分享失败')
    } finally {
      setSharingTo(null)
    }
  }

  const handlePost = async () => {
    if (!newPost.trim()) return
    if (!getToken()) {
      setError('请先登录')
      return
    }
    
    setPosting(true)
    setError('')
    try {
      await postsApi.createPost({
        content: newPost,
        is_anonymous: false
      })
      
      setNewPost('')
      setSuccessMessage('发布成功！帖子正在等待审核，审核通过后将显示在校园墙上。')
      setTimeout(() => setSuccessMessage(''), 5000)
    } catch (err: any) {
      setError(err.message || '发布失败')
    } finally {
      setPosting(false)
    }
  }

  // 审核通过
  const handleApprove = async (postId: number) => {
    setProcessingId(postId)
    try {
      await postsApi.approvePost(postId)
      setPendingPosts(pendingPosts.filter(p => p.id !== postId))
      loadReviewStats()
      setSuccessMessage('已通过审核')
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (err: any) {
      setError(err.message || '操作失败')
    } finally {
      setProcessingId(null)
    }
  }

  // 审核拒绝
  const handleReject = async (postId: number) => {
    setProcessingId(postId)
    try {
      await postsApi.rejectPost(postId)
      setPendingPosts(pendingPosts.filter(p => p.id !== postId))
      loadReviewStats()
      setSuccessMessage('已拒绝')
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (err: any) {
      setError(err.message || '操作失败')
    } finally {
      setProcessingId(null)
    }
  }

  // 切换到审核面板
  const toggleReviewPanel = () => {
    if (!showReviewPanel) {
      loadPendingPosts()
    }
    setShowReviewPanel(!showReviewPanel)
  }

  // 过滤好友搜索
  const filteredFriends = friends.filter(f => 
    f.friend?.name?.toLowerCase().includes(friendSearch.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-2xl mx-auto px-4">
        {/* 审核员入口 */}
        {isReviewer && (
          <div className="mb-4">
            <Button
              variant={showReviewPanel ? 'default' : 'outline'}
              onClick={toggleReviewPanel}
              className="w-full gap-2"
            >
              <Shield className="w-4 h-4" />
              {showReviewPanel ? '返回校园墙' : '审核管理'}
              {reviewStats && reviewStats.pending > 0 && (
                <Badge variant="destructive" className="ml-2">{reviewStats.pending}</Badge>
              )}
            </Button>
          </div>
        )}

        {/* 审核面板 */}
        {showReviewPanel && isReviewer && (
          <div className="space-y-4 mb-6">
            {/* 审核统计 */}
            <Card className="border-0 shadow-lg bg-gradient-to-r from-primary/5 to-secondary/5">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-primary" />
                    <span className="font-medium">审核中心</span>
                  </div>
                  <div className="flex gap-4 text-sm">
                    <span className="text-amber-600">待审核: {reviewStats?.pending || 0}</span>
                    <span className="text-green-600">已通过: {reviewStats?.approved || 0}</span>
                    <span className="text-red-600">已拒绝: {reviewStats?.rejected || 0}</span>
                  </div>
                </div>
                {reviewerStatus && (
                  <p className="text-xs text-muted-foreground mt-2">
                    您的信誉分: {reviewerStatus.credit_score} (审核员要求: &gt;{reviewerStatus.required_score})
                  </p>
                )}
              </CardContent>
            </Card>

            {/* 待审核列表 */}
            {reviewLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
              </div>
            ) : pendingPosts.length === 0 ? (
              <Card className="border-0 shadow-md p-8 text-center text-muted-foreground">
                <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-500" />
                <p>暂无待审核内容</p>
              </Card>
            ) : (
              <div className="space-y-4">
                {pendingPosts.map((post) => (
                  <Card key={post.id} className="border-0 shadow-md border-l-4 border-l-amber-500">
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Avatar className="w-10 h-10">
                            <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                              {post.author.name.slice(0, 1)}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium text-foreground">{post.author.name}</p>
                            <p className="text-xs text-muted-foreground">{post.time}</p>
                          </div>
                        </div>
                        <StatusBadge status={post.status} />
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-foreground mb-4 leading-relaxed">{post.content}</p>
                      <div className="flex gap-2">
                        <Button
                          variant="default"
                          size="sm"
                          className="flex-1 bg-green-600 hover:bg-green-700"
                          onClick={() => handleApprove(post.id)}
                          disabled={processingId === post.id}
                        >
                          {processingId === post.id ? (
                            <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                          ) : (
                            <CheckCircle className="w-4 h-4 mr-1" />
                          )}
                          通过
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          className="flex-1"
                          onClick={() => handleReject(post.id)}
                          disabled={processingId === post.id}
                        >
                          {processingId === post.id ? (
                            <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                          ) : (
                            <XCircle className="w-4 h-4 mr-1" />
                          )}
                          拒绝
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 主内容区域 - 非审核模式 */}
        {!showReviewPanel && (
          <>
            {/* 发布区域 */}
            <Card className="mb-6 border-0 shadow-lg">
              <CardContent className="p-4">
                {error && (
                  <div className="mb-3 p-3 rounded-lg bg-destructive/10 text-destructive text-sm flex items-center justify-between">
                    <span>{error}</span>
                    <Button variant="ghost" size="sm" onClick={() => setError('')}>
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                )}
                {successMessage && (
                  <div className="mb-3 p-3 rounded-lg bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 text-sm flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    {successMessage}
                  </div>
                )}
                <div className="flex gap-3">
                  <Avatar className="w-10 h-10">
                    <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">我</AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <Textarea
                      placeholder="分享你的校园生活..."
                      value={newPost}
                      onChange={(e) => setNewPost(e.target.value)}
                      className="min-h-[80px] resize-none border-0 bg-muted/50 focus-visible:ring-0"
                    />
                    <div className="flex items-center justify-between mt-3">
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm" className="text-muted-foreground">
                          <ImageIcon className="w-4 h-4 mr-1" />
                          图片
                        </Button>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">发布后需审核</span>
                        <Button variant="gradient" size="sm" onClick={handlePost} disabled={!newPost.trim() || posting}>
                          {posting ? (
                            <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                          ) : (
                            <Send className="w-4 h-4 mr-1" />
                          )}
                          发布
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 筛选器 */}
            <div className="flex items-center gap-2 mb-6">
              {filters.map((filter) => {
                const Icon = filter.icon
                return (
                  <Button
                    key={filter.id}
                    variant={activeFilter === filter.id ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setActiveFilter(filter.id)}
                    className="gap-1"
                  >
                    <Icon className="w-4 h-4" />
                    {filter.label}
                  </Button>
                )
              })}
              <Button variant="ghost" size="sm" onClick={loadPosts} className="ml-auto">
                刷新
              </Button>
            </div>

            {/* 加载状态 */}
            {loading && (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
              </div>
            )}

            {/* 动态列表 */}
            {!loading && (
              <div className="space-y-4">
                {posts.length === 0 ? (
                  <Card className="border-0 shadow-md p-8 text-center text-muted-foreground">
                    暂无动态，快来发布第一条吧！
                  </Card>
                ) : (
                  posts.map((post) => (
                    <Card key={post.id} className="border-0 shadow-md hover:shadow-lg transition-shadow">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <div 
                            className="flex items-center gap-3 cursor-pointer flex-1"
                            onClick={() => onNavigate?.('post-detail', { postId: post.id })}
                          >
                            <Avatar className="w-10 h-10">
                              <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                                {post.author.name.slice(0, 1)}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <p className="font-medium text-foreground">{post.author.name}</p>
                              <p className="text-xs text-muted-foreground">{post.author.department} · {post.time}</p>
                            </div>
                          </div>
                          <Button variant="ghost" size="icon" className="text-muted-foreground">
                            <MoreHorizontal className="w-5 h-5" />
                          </Button>
                        </div>
                      </CardHeader>
                      
                      <CardContent className="pt-0">
                        <div 
                          className="cursor-pointer mb-3"
                          onClick={() => onNavigate?.('post-detail', { postId: post.id })}
                        >
                          <p className="text-foreground leading-relaxed hover:text-primary/80 transition-colors">{post.content}</p>
                        </div>
                        
                        {/* 标签 */}
                        {post.tags.length > 0 && (
                          <div className="flex flex-wrap gap-2 mb-4">
                            {post.tags.map((tag) => (
                              <Badge key={tag} variant="secondary" className="text-xs">
                                #{tag}
                              </Badge>
                            ))}
                          </div>
                        )}

                        {/* 互动按钮 */}
                        <div className="flex items-center justify-between pt-3 border-t border-border">
                          <Button
                            variant="ghost"
                            size="sm"
                            className={`transition-all ${post.liked ? 'text-pink-500 hover:text-pink-600' : 'text-muted-foreground hover:text-pink-500'}`}
                            onClick={() => handleLike(post.id)}
                          >
                            <Heart className={`w-4 h-4 mr-1 transition-all ${post.liked ? 'fill-current scale-110' : ''}`} />
                            {post.likes}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-muted-foreground hover:text-primary"
                            onClick={() => onNavigate?.('post-detail', { postId: post.id })}
                          >
                            <MessageCircle className="w-4 h-4 mr-1" />
                            {post.comments}
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="text-muted-foreground hover:text-primary"
                            onClick={() => openShareModal(post)}
                          >
                            <Share2 className="w-4 h-4 mr-1" />
                            {post.shares}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* 分享弹窗 */}
      {shareModalPost && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <Card className="w-full max-w-md mx-4 shadow-2xl border-0">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-primary" />
                  <span className="font-semibold">分享给好友</span>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setShareModalPost(null)}>
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* 帖子预览 */}
              <div className="p-3 bg-muted/50 rounded-lg">
                <p className="text-sm text-muted-foreground mb-1">分享内容:</p>
                <p className="text-sm line-clamp-2">{shareModalPost.content}</p>
              </div>
              
              {/* 搜索好友 */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="搜索好友..."
                  className="pl-9"
                  value={friendSearch}
                  onChange={(e) => setFriendSearch(e.target.value)}
                />
              </div>
              
              {/* 好友列表 */}
              <div className="max-h-64 overflow-y-auto space-y-2">
                {friendsLoading ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  </div>
                ) : filteredFriends.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    {friends.length === 0 ? '暂无好友，快去添加好友吧~' : '未找到匹配的好友'}
                  </div>
                ) : (
                  filteredFriends.map((friend) => (
                    <div 
                      key={friend.id}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <Avatar className="w-10 h-10">
                          <AvatarImage src={friend.friend?.avatar} />
                          <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                            {friend.friend?.name?.slice(0, 1) || '?'}
                          </AvatarFallback>
                        </Avatar>
                        <span className="font-medium">{friend.friend?.name}</span>
                      </div>
                      <Button
                        size="sm"
                        variant="gradient"
                        disabled={sharingTo === friend.friend_id}
                        onClick={() => handleShareToFriend(friend.friend_id)}
                      >
                        {sharingTo === friend.friend_id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            <Send className="w-4 h-4 mr-1" />
                            分享
                          </>
                        )}
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
