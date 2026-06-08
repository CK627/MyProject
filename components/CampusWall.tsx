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
  authApi,
  Post as ApiPost, 
  getToken, 
  ReviewerStatus, 
  ReviewStats,
  friendsApi,
  messagesApi,
  Friend,
  User
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
  let imagesList: string[] = []
  try {
    if (apiPost.images) {
      imagesList = JSON.parse(apiPost.images as unknown as string)
    }
  } catch (e) {
    console.error('解析帖子图片出错', e)
  }

  return {
    id: apiPost.id,
    author: {
      id: apiPost.user_id,
      name: apiPost.author?.name || '匿名用户',
      avatar: apiPost.author?.avatar,
      department: '校园用户'
    },
    content: apiPost.content,
    images: imagesList,
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

  // 新增图片状态
  const [selectedImages, setSelectedImages] = useState<string[]>([])
  const [uploadingImages, setUploadingImages] = useState(false)
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  
  // 图片放大预览
  const [previewImage, setPreviewImage] = useState<string | null>(null)
  
  // 帖子操作菜单
  const [activeMenuId, setActiveMenuId] = useState<number | null>(null)

  // 监听点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      // 检查点击是否在菜单或按钮内
      const target = e.target as Element;
      if (!target.closest('.post-menu-container')) {
        setActiveMenuId(null);
      }
    };
    
    // 使用 capture 阶段来捕获点击事件，防止被其他 stopPropagation 阻止
    document.addEventListener('click', handleClickOutside, true);
    return () => document.removeEventListener('click', handleClickOutside, true);
  }, []);

  const handleDeletePost = async (postId: number) => {
    if (!confirm('确定要删除这条动态吗？')) return
    
    try {
      await postsApi.deletePost(postId)
      setPosts(posts.filter(p => p.id !== postId))
      setSuccessMessage('删除成功')
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (err: any) {
      setError(err.message || '删除失败')
    }
  }
  
  // 审核相关状态
  const [isReviewer, setIsReviewer] = useState(false)
  const [reviewerStatus, setReviewerStatus] = useState<ReviewerStatus | null>(null)
  const [showReviewPanel, setShowReviewPanel] = useState(false)
  const [reviewStats, setReviewStats] = useState<ReviewStats | null>(null)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [processingId, setProcessingId] = useState<number | null>(null)
  
  // 举报相关状态
  const [reportModalPost, setReportModalPost] = useState<Post | null>(null)
  const [reportReason, setReportReason] = useState('')
  const [reporting, setReporting] = useState(false)
  
  // 审核员举报管理状态
  const [reviewTab, setReviewTab] = useState<'posts' | 'reports'>('posts')
  const [pendingReports, setPendingReports] = useState<any[]>([])
  const [reportsLoading, setReportsLoading] = useState(false)

  useEffect(() => {
    loadPosts()
  }, [activeFilter])

  useEffect(() => {
    const fetchUser = async () => {
      try {
        if (getToken()) {
          const user = await authApi.getCurrentUser()
          setCurrentUser(user)
        }
      } catch (err) {
        console.error('获取用户信息失败', err)
      }
    }
    fetchUser()
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

  const loadPendingReports = async () => {
    setReportsLoading(true)
    try {
      const reports = await postsApi.getReviewReports('pending', 1, 50)
      setPendingReports(reports)
      loadReviewStats()
    } catch (err: any) {
      setError('加载举报列表失败')
      console.error('Failed to load pending reports:', err)
    } finally {
      setReportsLoading(false)
    }
  }

  // 提交举报
  const handleReportPost = async () => {
    if (!reportModalPost || !reportReason.trim()) {
      setError('请填写举报理由')
      return
    }
    
    setReporting(true)
    try {
      await postsApi.reportPost(reportModalPost.id, reportReason)
      setSuccessMessage('举报提交成功，等待审核员处理')
      setTimeout(() => setSuccessMessage(''), 3000)
      setReportModalPost(null)
      setReportReason('')
    } catch (err: any) {
      setError(err.message || '举报提交失败')
    } finally {
      setReporting(false)
    }
  }

  // 处理举报
  const handleResolveReport = async (reportId: number, action: 'approve' | 'reject') => {
    setProcessingId(reportId)
    try {
      await postsApi.resolveReviewReport(reportId, action)
      setPendingReports(pendingReports.filter(r => r.id !== reportId))
      loadReviewStats()
      setSuccessMessage(action === 'approve' ? '举报已通过，帖子已隐藏' : '举报已拒绝')
      setTimeout(() => setSuccessMessage(''), 3000)
      
      // 如果举报通过，需要从前台的帖子列表中移除该帖子
      if (action === 'approve') {
        const report = pendingReports.find(r => r.id === reportId)
        if (report) {
          setPosts(posts.filter(p => p.id !== report.target_id))
        }
      }
    } catch (err: any) {
      setError(err.message || '操作失败')
    } finally {
      setProcessingId(null)
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

  // 处理图片上传
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length === 0) return

    // 限制最多9张图
    if (selectedImages.length + files.length > 9) {
      setError('最多只能上传9张图片')
      return
    }

    setUploadingImages(true)
    setError('')

    try {
      // 循环压缩图片转 base64
      const base64Images = await Promise.all(files.map(file => {
        return new Promise<string>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = (e) => {
            const img = new Image()
            img.onload = () => {
              const canvas = document.createElement('canvas')
              // 适当降低尺寸以符合大文本存储需求，同时保持清晰度
              const MAX_SIZE = 800
              let width = img.width
              let height = img.height

              if (width > height) {
                if (width > MAX_SIZE) {
                  height *= MAX_SIZE / width
                  width = MAX_SIZE
                }
              } else {
                if (height > MAX_SIZE) {
                  width *= MAX_SIZE / height
                  height = MAX_SIZE
                }
              }

              canvas.width = width
              canvas.height = height
              const ctx = canvas.getContext('2d')
              ctx?.drawImage(img, 0, 0, width, height)
              
              // 压缩为 JPEG, 质量0.7
              resolve(canvas.toDataURL('image/jpeg', 0.7))
            }
            img.onerror = reject
            img.src = e.target?.result as string
          }
          reader.onerror = reject
          reader.readAsDataURL(file)
        })
      }))

      setSelectedImages(prev => [...prev, ...base64Images])
    } catch (err: any) {
      setError('图片处理失败')
      console.error(err)
    } finally {
      setUploadingImages(false)
      // 清空 input 使得同一张图可以再次选择
      e.target.value = ''
    }
  }

  // 移除图片
  const removeImage = (index: number) => {
    setSelectedImages(prev => prev.filter((_, i) => i !== index))
  }

  const handlePost = async () => {
    if (!newPost.trim() && selectedImages.length === 0) return
    if (!getToken()) {
      setError('请先登录')
      return
    }
    
    setPosting(true)
    setError('')
    try {
      await postsApi.createPost({
        content: newPost,
        is_anonymous: false,
        images: selectedImages.length > 0 ? JSON.stringify(selectedImages) : undefined
      })
      
      setNewPost('')
      setSelectedImages([])
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
      loadPendingReports()
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
                    <span className="text-amber-600">待处理举报: {reviewStats?.pending_reports || 0}</span>
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

            {/* 标签切换 */}
            <div className="flex border-b border-border mb-4">
              <button
                className={`py-2 px-4 text-sm font-medium transition-colors border-b-2 ${
                  reviewTab === 'posts'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
                }`}
                onClick={() => setReviewTab('posts')}
              >
                待审核动态
                {reviewStats && reviewStats.pending > 0 && (
                  <span className="ml-2 bg-amber-100 text-amber-700 text-xs px-2 py-0.5 rounded-full">{reviewStats.pending}</span>
                )}
              </button>
              <button
                className={`py-2 px-4 text-sm font-medium transition-colors border-b-2 ${
                  reviewTab === 'reports'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
                }`}
                onClick={() => setReviewTab('reports')}
              >
                待处理举报
                {reviewStats && reviewStats.pending_reports && reviewStats.pending_reports > 0 ? (
                  <span className="ml-2 bg-amber-100 text-amber-700 text-xs px-2 py-0.5 rounded-full">{reviewStats.pending_reports}</span>
                ) : null}
              </button>
            </div>

            {/* 待审核列表 */}
            {reviewTab === 'posts' && (
              reviewLoading ? (
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
                              {post.author.avatar && <AvatarImage src={post.author.avatar} alt={post.author.name} />}
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
                        
                        {/* 图片展示区 */}
                        {post.images && post.images.length > 0 && (
                          <div className="mt-3 mb-4 flex flex-wrap gap-2">
                            {post.images.map((img, idx) => (
                              <div key={idx} className="w-24 h-24 sm:w-32 sm:h-32 rounded-md overflow-hidden border border-border cursor-pointer">
                                <img 
                                  src={img} 
                                  alt={`post-image-${idx}`} 
                                  className="w-full h-full object-cover transition-transform hover:scale-105" 
                                  onDoubleClick={(e) => {
                                    e.stopPropagation()
                                    setPreviewImage(img)
                                  }}
                                />
                              </div>
                            ))}
                          </div>
                        )}

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
              )
            )}

            {/* 待处理举报列表 */}
            {reviewTab === 'reports' && (
              reportsLoading ? (
                <div className="flex justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-primary" />
                </div>
              ) : pendingReports.length === 0 ? (
                <Card className="border-0 shadow-md p-8 text-center text-muted-foreground">
                  <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-500" />
                  <p>暂无待处理举报</p>
                </Card>
              ) : (
                <div className="space-y-4">
                  {pendingReports.map((report) => (
                    <Card key={report.id} className="border-0 shadow-md border-l-4 border-l-red-500">
                      <CardHeader className="pb-2 bg-red-50/50 dark:bg-red-950/20">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-red-600 dark:text-red-400 font-medium">
                            <AlertCircle className="w-4 h-4" />
                            举报理由: {report.reason}
                          </div>
                          <span className="text-xs text-muted-foreground">
                            举报人: {report.reporter?.name || '未知'} · {new Date(report.created_at).toLocaleDateString('zh-CN')}
                          </span>
                        </div>
                      </CardHeader>
                      <CardContent className="pt-4">
                        <div className="bg-muted p-3 rounded-md mb-4 border border-border">
                          <p className="text-sm font-medium text-muted-foreground mb-2">被举报内容 (帖子ID: {report.target_id})</p>
                          <div className="text-sm">
                            <Button 
                              variant="link" 
                              className="px-0 h-auto text-primary"
                              onClick={() => onNavigate?.('post-detail', { postId: report.target_id })}
                            >
                              查看原帖详情 &rarr;
                            </Button>
                          </div>
                        </div>

                        <div className="flex gap-2">
                          <Button
                            variant="destructive"
                            size="sm"
                            className="flex-1"
                            onClick={() => handleResolveReport(report.id, 'approve')}
                            disabled={processingId === report.id}
                          >
                            {processingId === report.id ? (
                              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                            ) : (
                              <CheckCircle className="w-4 h-4 mr-1" />
                            )}
                            核实通过 (隐藏原帖)
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="flex-1"
                            onClick={() => handleResolveReport(report.id, 'reject')}
                            disabled={processingId === report.id}
                          >
                            {processingId === report.id ? (
                              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                            ) : (
                              <XCircle className="w-4 h-4 mr-1" />
                            )}
                            驳回举报 (无需处理)
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )
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
                    {currentUser?.avatar && <AvatarImage src={currentUser.avatar} alt="我" />}
                    <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">我</AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <Textarea
                      placeholder="分享你的校园生活..."
                      value={newPost}
                      onChange={(e) => setNewPost(e.target.value)}
                      className="min-h-[80px] resize-none border-0 bg-muted/50 focus-visible:ring-0"
                    />

                    {/* 图片预览区域 */}
                    {selectedImages.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {selectedImages.map((img, index) => (
                          <div key={index} className="relative group w-20 h-20 rounded-md overflow-hidden border border-border">
                            <img src={img} alt="preview" className="w-full h-full object-cover" />
                            <button
                              onClick={() => removeImage(index)}
                              className="absolute top-1 right-1 bg-black/60 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        ))}
                        {uploadingImages && (
                          <div className="w-20 h-20 flex items-center justify-center bg-muted rounded-md">
                            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                          </div>
                        )}
                      </div>
                    )}

                    <div className="flex items-center justify-between mt-3">
                      <div className="flex gap-2">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="text-muted-foreground relative overflow-hidden"
                        >
                          <input
                            type="file"
                            accept="image/*"
                            multiple
                            className="absolute inset-0 opacity-0 cursor-pointer"
                            onChange={handleImageUpload}
                          />
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
                    <Card 
                      key={post.id} 
                      className="border-0 shadow-md hover:shadow-lg transition-shadow relative"
                      style={{ zIndex: activeMenuId === post.id ? 50 : 1 }}
                    >
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <div 
                            className="flex items-center gap-3 cursor-pointer flex-1"
                            onClick={() => onNavigate?.('post-detail', { postId: post.id })}
                          >
                            <Avatar className="w-10 h-10">
                              {post.author.avatar && <AvatarImage src={post.author.avatar} alt={post.author.name} />}
                              <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                                {post.author.name.slice(0, 1)}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <p className="font-medium text-foreground">{post.author.name}</p>
                              <p className="text-xs text-muted-foreground">{post.author.department} · {post.time}</p>
                            </div>
                          </div>
                          <div className="relative post-menu-container">
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="text-muted-foreground relative z-20"
                              onClick={(e) => {
                                e.preventDefault()
                                e.stopPropagation()
                                console.log("Dropdown toggle clicked! post.id:", post.id, "current activeMenuId:", activeMenuId)
                                setActiveMenuId(activeMenuId === post.id ? null : post.id)
                              }}
                            >
                              <MoreHorizontal className="w-5 h-5 pointer-events-none" />
                            </Button>
                            
                            {activeMenuId === post.id && (
                                <div 
                                  className="absolute right-0 mt-2 w-32 bg-popover border border-border rounded-md shadow-lg overflow-hidden z-[100] animate-in fade-in zoom-in-95"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    e.stopPropagation()
                                  }}
                                >
                                {(currentUser?.id === post.author.id || currentUser?.role === 'admin') ? (
                                  <div
                                    className="w-full text-left px-4 py-2 text-sm text-destructive hover:bg-muted transition-colors cursor-pointer"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      e.stopPropagation()
                                      setActiveMenuId(null)
                                      handleDeletePost(post.id)
                                    }}
                                  >
                                    删除动态
                                  </div>
                                ) : (
                                <div
                                  className="w-full text-left px-4 py-2 text-sm text-muted-foreground hover:bg-muted transition-colors cursor-pointer"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    e.stopPropagation()
                                    setActiveMenuId(null)
                                    setReportModalPost(post)
                                  }}
                                >
                                  举报
                                </div>
                              )}
                                </div>
                            )}
                          </div>
                        </div>
                      </CardHeader>
                      
                      <CardContent className="pt-0">
                        <div 
                          className="cursor-pointer mb-3"
                          onClick={() => onNavigate?.('post-detail', { postId: post.id })}
                        >
                          <p className="text-foreground leading-relaxed hover:text-primary/80 transition-colors">{post.content}</p>
                        </div>
                        
                        {/* 图片展示区 */}
                        {post.images && post.images.length > 0 && (
                          <div className="mt-3 mb-4 flex flex-wrap gap-2">
                            {post.images.map((img, idx) => (
                              <div key={idx} className="w-24 h-24 sm:w-32 sm:h-32 rounded-md overflow-hidden border border-border cursor-pointer">
                                <img 
                                  src={img} 
                                  alt={`post-image-${idx}`} 
                                  className="w-full h-full object-cover transition-transform hover:scale-105"
                                  onDoubleClick={(e) => {
                                    e.stopPropagation()
                                    setPreviewImage(img)
                                  }}
                                />
                              </div>
                            ))}
                          </div>
                        )}

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

      {/* 图片预览弹窗 */}
      {previewImage && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setPreviewImage(null)}
        >
          <div className="relative w-full h-full flex items-center justify-center p-4">
            <Button 
              variant="ghost" 
              size="icon" 
              className="absolute top-4 right-4 text-white hover:bg-white/20"
              onClick={() => setPreviewImage(null)}
            >
              <X className="w-6 h-6" />
            </Button>
            <img 
              src={previewImage} 
              alt="preview" 
              className="max-w-full max-h-full object-contain cursor-zoom-out"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}

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
      {/* 举报弹窗 */}
      {reportModalPost && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <Card className="w-full max-w-md mx-4 shadow-2xl border-0">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-destructive" />
                  <span className="font-semibold text-destructive">举报动态</span>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setReportModalPost(null)}>
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 bg-muted/50 rounded-lg">
                <p className="text-sm text-muted-foreground mb-1">举报对象:</p>
                <div className="flex items-center gap-2 mb-2">
                  <Avatar className="w-6 h-6">
                    <AvatarImage src={reportModalPost.author.avatar} />
                    <AvatarFallback>{reportModalPost.author.name.slice(0, 1)}</AvatarFallback>
                  </Avatar>
                  <span className="text-sm font-medium">{reportModalPost.author.name}</span>
                </div>
                <p className="text-sm line-clamp-2">{reportModalPost.content}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium block mb-2">请填写举报理由</label>
                <Textarea
                  placeholder="例如：广告营销、不实信息、人身攻击等..."
                  value={reportReason}
                  onChange={(e) => setReportReason(e.target.value)}
                  className="min-h-[100px] resize-none"
                />
              </div>
              
              <div className="flex gap-2 pt-2">
                <Button variant="outline" className="flex-1" onClick={() => setReportModalPost(null)}>
                  取消
                </Button>
                <Button 
                  variant="destructive" 
                  className="flex-1" 
                  disabled={!reportReason.trim() || reporting}
                  onClick={handleReportPost}
                >
                  {reporting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                  提交举报
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
