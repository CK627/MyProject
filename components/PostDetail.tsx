'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { 
  Heart, 
  MessageCircle, 
  Share2, 
  ArrowLeft,
  Send,
  ThumbsDown,
  Trash2,
  Loader2,
  Shield,
  MoreVertical,
  AlertTriangle,
  X,
  Users,
  Search,
  CheckCircle,
  Bell
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
  Comment,
  friendsApi,
  messagesApi,
  Friend,
  authApi,
  User as ApiUser
} from '@/lib/api'

interface PostDetailProps {
  postId: number
  onBack: () => void
}

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

export function PostDetail({ postId, onBack }: PostDetailProps) {
  const [post, setPost] = useState<ApiPost | null>(null)
  const [comments, setComments] = useState<Comment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  
  // 当前用户状态
  const [currentUserId, setCurrentUserId] = useState<number | null>(null)
  const [currentUser, setCurrentUser] = useState<ApiUser | null>(null)
  const [isReviewer, setIsReviewer] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  
  // 帖子互动状态
  const [liked, setLiked] = useState(false)
  const [likesCount, setLikesCount] = useState(0)
  
  // 评论状态
  const [newComment, setNewComment] = useState('')
  const [submittingComment, setSubmittingComment] = useState(false)
  const [commentInteractions, setCommentInteractions] = useState<Record<number, { liked: boolean; disliked: boolean }>>({})
  const [processingCommentId, setProcessingCommentId] = useState<number | null>(null)
  
  // 删除弹窗
  const [deleteModalComment, setDeleteModalComment] = useState<Comment | null>(null)
  const [deleteReason, setDeleteReason] = useState('')
  const [deleting, setDeleting] = useState(false)
  
  // 审核员删除弹窗
  const [reviewerDeleteComment, setReviewerDeleteComment] = useState<Comment | null>(null)
  const [reviewerDeleteReason, setReviewerDeleteReason] = useState('')
  
  // 分享弹窗
  const [showShareModal, setShowShareModal] = useState(false)
  const [friends, setFriends] = useState<Friend[]>([])
  const [friendsLoading, setFriendsLoading] = useState(false)
  const [friendSearch, setFriendSearch] = useState('')
  const [sharingTo, setSharingTo] = useState<number | null>(null)

  // 图片放大预览
  const [previewImage, setPreviewImage] = useState<string | null>(null)

  // 加载帖子数据
  useEffect(() => {
    loadPost()
    loadComments()
    checkUserStatus()
  }, [postId])

  const checkUserStatus = async () => {
    if (!getToken()) return
    try {
      const [user, reviewerStatus] = await Promise.all([
        authApi.getCurrentUser(),
        postsApi.checkReviewerStatus()
      ])
      setCurrentUser(user)
      setCurrentUserId(user.id)
      setIsReviewer(reviewerStatus.is_reviewer)
      setIsAdmin(reviewerStatus.is_admin)
    } catch (err) {
      console.error('Failed to check user status:', err)
    }
  }

  const loadPost = async () => {
    setLoading(true)
    try {
      const postData = await postsApi.getPost(postId)
      
      // Parse images from string to array if needed
      let parsedImages: string[] = []
      try {
        if (postData.images) {
          parsedImages = JSON.parse(postData.images as unknown as string)
        }
      } catch (e) {
        console.error('Failed to parse post images', e)
      }
      
      const enrichedPostData = {
        ...postData,
        images: parsedImages as any // Temporarily cast to any to satisfy the interface if it expects string
      }
      
      setPost(enrichedPostData)
      setLikesCount(postData.likes_count)
      
      // 检查点赞状态
      if (getToken()) {
        try {
          const { liked } = await postsApi.checkLikeStatus(postId)
          setLiked(liked)
        } catch {}
      }
    } catch (err: any) {
      setError('加载帖子失败')
    } finally {
      setLoading(false)
    }
  }

  const loadComments = async () => {
    try {
      const commentList = await postsApi.getComments(postId)
      // 只显示active状态的评论
      const activeComments = commentList.filter(c => c.status === 'active')
      setComments(activeComments)
      
      // 加载评论互动状态
      if (getToken()) {
        const interactions: Record<number, { liked: boolean; disliked: boolean }> = {}
        await Promise.all(activeComments.map(async (comment) => {
          try {
            const status = await postsApi.getCommentInteractionStatus(postId, comment.id)
            interactions[comment.id] = status
          } catch {
            interactions[comment.id] = { liked: false, disliked: false }
          }
        }))
        setCommentInteractions(interactions)
      }
    } catch (err) {
      console.error('Failed to load comments:', err)
    }
  }

  // 点赞帖子
  const handleLikePost = async () => {
    if (!getToken()) {
      setError('请先登录')
      return
    }
    
    // 乐观更新
    setLiked(!liked)
    setLikesCount(liked ? likesCount - 1 : likesCount + 1)
    
    try {
      if (liked) {
        await postsApi.unlikePost(postId)
      } else {
        await postsApi.likePost(postId)
      }
    } catch (err: any) {
      // 回滚
      setLiked(liked)
      setLikesCount(likesCount)
      setError(err.message || '操作失败')
    }
  }

  // 发表评论
  const handleSubmitComment = async () => {
    if (!newComment.trim()) return
    if (!getToken()) {
      setError('请先登录')
      return
    }
    
    setSubmittingComment(true)
    try {
      await postsApi.createComment(postId, newComment)
      setNewComment('')
      await loadComments()
      setSuccessMessage('评论发表成功')
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (err: any) {
      setError(err.message || '发表评论失败')
    } finally {
      setSubmittingComment(false)
    }
  }

  // 点赞评论
  const handleLikeComment = async (commentId: number) => {
    if (!getToken()) {
      setError('请先登录')
      return
    }
    
    const current = commentInteractions[commentId] || { liked: false, disliked: false }
    setProcessingCommentId(commentId)
    
    try {
      if (current.liked) {
        await postsApi.unlikeComment(postId, commentId)
      } else {
        await postsApi.likeComment(postId, commentId)
      }
      
      // 更新状态
      setCommentInteractions(prev => ({
        ...prev,
        [commentId]: { liked: !current.liked, disliked: false }
      }))
      
      // 更新评论点赞数
      setComments(comments.map(c => {
        if (c.id === commentId) {
          let newLikes = c.likes_count + (current.liked ? -1 : 1)
          let newDislikes = c.dislikes_count + (current.disliked ? -1 : 0)
          return { ...c, likes_count: Math.max(0, newLikes), dislikes_count: Math.max(0, newDislikes) }
        }
        return c
      }))
    } catch (err: any) {
      setError(err.message || '操作失败')
    } finally {
      setProcessingCommentId(null)
    }
  }

  // 拉踩评论
  const handleDislikeComment = async (commentId: number) => {
    if (!getToken()) {
      setError('请先登录')
      return
    }
    
    const comment = comments.find(c => c.id === commentId)
    if (comment && comment.user_id === currentUserId) {
      setError('不能拉踩自己的评论')
      return
    }
    
    const current = commentInteractions[commentId] || { liked: false, disliked: false }
    setProcessingCommentId(commentId)
    
    try {
      if (current.disliked) {
        await postsApi.undislikeComment(postId, commentId)
      } else {
        await postsApi.dislikeComment(postId, commentId)
      }
      
      // 更新状态
      setCommentInteractions(prev => ({
        ...prev,
        [commentId]: { liked: false, disliked: !current.disliked }
      }))
      
      // 更新评论拉踩数
      setComments(comments.map(c => {
        if (c.id === commentId) {
          let newLikes = c.likes_count + (current.liked ? -1 : 0)
          let newDislikes = c.dislikes_count + (current.disliked ? -1 : 1)
          return { ...c, likes_count: Math.max(0, newLikes), dislikes_count: Math.max(0, newDislikes) }
        }
        return c
      }))
      
      // 重新加载评论（可能被删除了）
      setTimeout(() => loadComments(), 500)
    } catch (err: any) {
      setError(err.message || '操作失败')
    } finally {
      setProcessingCommentId(null)
    }
  }

  // 删除评论
  const handleDeleteComment = async () => {
    if (!deleteModalComment) return
    
    setDeleting(true)
    try {
      await postsApi.deleteComment(postId, deleteModalComment.id, deleteReason || undefined)
      await loadComments()
      setDeleteModalComment(null)
      setDeleteReason('')
      setSuccessMessage('评论删除成功')
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (err: any) {
      setError(err.message || '删除失败')
    } finally {
      setDeleting(false)
    }
  }

  // 审核员投票删除
  const handleReviewerDelete = async () => {
    if (!reviewerDeleteComment || !reviewerDeleteReason.trim()) {
      setError('请输入删除原因')
      return
    }
    
    setDeleting(true)
    try {
      await postsApi.reviewerDeleteComment(postId, reviewerDeleteComment.id, reviewerDeleteReason)
      await loadComments()
      setReviewerDeleteComment(null)
      setReviewerDeleteReason('')
      setSuccessMessage('投票成功')
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (err: any) {
      setError(err.message || '投票失败')
    } finally {
      setDeleting(false)
    }
  }

  // 分享
  const openShareModal = async () => {
    if (!getToken()) {
      setError('请先登录')
      return
    }
    setShowShareModal(true)
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

  const handleShareToFriend = async (friendUserId: number) => {
    if (!post) return
    
    setSharingTo(friendUserId)
    try {
      const shareContent = `[分享帖子] ${post.author?.name || '匿名用户'}的动态:\n"${post.content.slice(0, 100)}${post.content.length > 100 ? '...' : ''}"`
      await messagesApi.sendMessage(friendUserId, shareContent, 'text')
      
      setSuccessMessage('分享成功！')
      setTimeout(() => setSuccessMessage(''), 3000)
      setShowShareModal(false)
    } catch (err: any) {
      setError(err.message || '分享失败')
    } finally {
      setSharingTo(null)
    }
  }

  const filteredFriends = friends.filter(f => 
    f.friend?.name?.toLowerCase().includes(friendSearch.toLowerCase())
  )

  if (loading) {
    return (
      <div className="min-h-screen bg-background pt-20 pb-8 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!post) {
    return (
      <div className="min-h-screen bg-background pt-20 pb-8">
        <div className="max-w-2xl mx-auto px-4">
          <Button variant="ghost" onClick={onBack} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回
          </Button>
          <Card className="p-8 text-center text-muted-foreground">
            帖子不存在或已被删除
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-2xl mx-auto px-4">
        {/* 返回按钮 */}
        <Button variant="ghost" onClick={onBack} className="mb-4 gap-2">
          <ArrowLeft className="w-4 h-4" />
          返回校园墙
        </Button>

        {/* 错误/成功提示 */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm flex items-center justify-between">
            <span>{error}</span>
            <Button variant="ghost" size="sm" onClick={() => setError('')}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        )}
        {successMessage && (
          <div className="mb-4 p-3 rounded-lg bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 text-sm flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            {successMessage}
          </div>
        )}

        {/* 帖子详情 */}
        <Card className="mb-6 border-0 shadow-lg">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <Avatar className="w-12 h-12">
                <AvatarImage src={post.author?.avatar} />
                <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground text-lg">
                  {post.author?.name?.slice(0, 1) || '?'}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1">
                <p className="font-semibold text-foreground text-lg">{post.author?.name || '匿名用户'}</p>
                <p className="text-sm text-muted-foreground">{formatTime(post.created_at)}</p>
              </div>
            </div>
          </CardHeader>
          
          <CardContent>
            <p className="text-foreground text-lg leading-relaxed mb-6">{post.content}</p>
            
            {/* 图片展示 */}
            {post.images && (post.images as unknown as string[]).length > 0 && (
              <div className="grid grid-cols-2 gap-2 mb-6">
                {(post.images as unknown as string[]).map((img, idx) => (
                  <img 
                    key={idx} 
                    src={img} 
                    alt="" 
                    className="rounded-lg w-full h-48 object-cover cursor-pointer transition-transform hover:scale-105" 
                    onDoubleClick={(e) => {
                      e.stopPropagation()
                      setPreviewImage(img)
                    }}
                  />
                ))}
              </div>
            )}
            
            {/* 标签 */}
            {post.tags && post.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {post.tags.map((tag) => (
                  <Badge key={tag.id} variant="secondary" className="text-xs">
                    #{tag.tag_name}
                  </Badge>
                ))}
              </div>
            )}

            {/* 互动按钮 */}
            <div className="flex items-center justify-between pt-4 border-t border-border">
              <Button
                variant="ghost"
                size="lg"
                className={`transition-all ${liked ? 'text-pink-500 hover:text-pink-600' : 'text-muted-foreground hover:text-pink-500'}`}
                onClick={handleLikePost}
              >
                <Heart className={`w-5 h-5 mr-2 transition-all ${liked ? 'fill-current scale-110' : ''}`} />
                {likesCount}
              </Button>
              <Button variant="ghost" size="lg" className="text-muted-foreground">
                <MessageCircle className="w-5 h-5 mr-2" />
                {comments.length}
              </Button>
              <Button 
                variant="ghost" 
                size="lg" 
                className="text-muted-foreground hover:text-primary"
                onClick={openShareModal}
              >
                <Share2 className="w-5 h-5 mr-2" />
                分享
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 评论区 */}
        <Card className="border-0 shadow-lg">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <MessageCircle className="w-5 h-5 text-primary" />
              <span className="font-semibold">评论 ({comments.length})</span>
            </div>
          </CardHeader>
          
          <CardContent className="space-y-4">
            {/* 发表评论 */}
            <div className="flex gap-3">
              <Avatar className="w-10 h-10">
                {currentUser?.avatar && <AvatarImage src={currentUser.avatar} alt="我" />}
                <AvatarFallback className="bg-primary/10">我</AvatarFallback>
              </Avatar>
              <div className="flex-1 space-y-2">
                <Textarea
                  placeholder="写下你的评论..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  className="min-h-[80px] resize-none"
                />
                <div className="flex justify-end">
                  <Button
                    variant="gradient"
                    disabled={!newComment.trim() || submittingComment}
                    onClick={handleSubmitComment}
                  >
                    {submittingComment ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4 mr-2" />
                    )}
                    发表评论
                  </Button>
                </div>
              </div>
            </div>

            {/* 评论列表 */}
            <div className="space-y-4 pt-4 border-t border-border">
              {comments.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  暂无评论，快来抢沙发吧~
                </div>
              ) : (
                comments.map((comment) => {
                  const interaction = commentInteractions[comment.id] || { liked: false, disliked: false }
                  const isOwner = currentUserId === comment.user_id
                  const canDelete = isOwner || isAdmin
                  const threshold = comment.likes_count * 2 + 5
                  
                  return (
                    <div key={comment.id} className="flex gap-3 group">
                      <Avatar className="w-10 h-10">
                        <AvatarImage src={comment.user?.avatar} />
                        <AvatarFallback className="bg-muted">
                          {comment.user?.name?.slice(0, 1) || '?'}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <div className="bg-muted/50 rounded-lg px-4 py-3">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{comment.user?.name || '匿名'}</span>
                              <span className="text-xs text-muted-foreground">{formatTime(comment.created_at)}</span>
                              {isOwner && (
                                <Badge variant="outline" className="text-xs">我的</Badge>
                              )}
                            </div>
                            
                            {/* 操作菜单 */}
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              {canDelete && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                                  onClick={() => setDeleteModalComment(comment)}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              )}
                              {isReviewer && !isOwner && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0 text-muted-foreground hover:text-amber-500"
                                  onClick={() => setReviewerDeleteComment(comment)}
                                  title="审核员投票删除"
                                >
                                  <Shield className="w-4 h-4" />
                                </Button>
                              )}
                            </div>
                          </div>
                          <p className="text-foreground">{comment.content}</p>
                        </div>
                        
                        {/* 评论互动 */}
                        <div className="flex items-center gap-4 mt-2 px-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            className={`h-8 gap-1 transition-all ${interaction.liked ? 'text-pink-500' : 'text-muted-foreground'}`}
                            onClick={() => handleLikeComment(comment.id)}
                            disabled={processingCommentId === comment.id}
                          >
                            {processingCommentId === comment.id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Heart className={`w-4 h-4 ${interaction.liked ? 'fill-current' : ''}`} />
                            )}
                            <span>{comment.likes_count || 0}</span>
                          </Button>
                          
                          {!isOwner && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className={`h-8 gap-1 transition-all ${interaction.disliked ? 'text-amber-500' : 'text-muted-foreground'}`}
                              onClick={() => handleDislikeComment(comment.id)}
                              disabled={processingCommentId === comment.id}
                              title={`拉踩 (${comment.dislikes_count || 0}/${threshold}删除)`}
                            >
                              <ThumbsDown className={`w-4 h-4 ${interaction.disliked ? 'fill-current' : ''}`} />
                              <span>{comment.dislikes_count || 0}</span>
                            </Button>
                          )}
                          
                          {/* 删除进度提示 */}
                          {(comment.dislikes_count || 0) > 0 && (
                            <span className="text-xs text-muted-foreground">
                              {comment.dislikes_count}/{threshold}删除
                            </span>
                          )}
                          {(comment.reviewer_delete_count || 0) > 0 && (
                            <span className="text-xs text-amber-500">
                              审核员投票: {comment.reviewer_delete_count}/3
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 删除确认弹窗 */}
      {deleteModalComment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <Card className="w-full max-w-md mx-4 shadow-2xl border-0">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="w-5 h-5" />
                <span className="font-semibold">删除评论</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-muted-foreground">确定要删除这条评论吗？</p>
              <div className="p-3 bg-muted/50 rounded-lg text-sm">
                {deleteModalComment.content}
              </div>
              
              {isAdmin && deleteModalComment.user_id !== currentUserId && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">删除原因（将通知用户）</label>
                  <Input
                    placeholder="请输入删除原因..."
                    value={deleteReason}
                    onChange={(e) => setDeleteReason(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    管理员删除将扣除用户10信誉分
                  </p>
                </div>
              )}
              
              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setDeleteModalComment(null)
                    setDeleteReason('')
                  }}
                >
                  取消
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={handleDeleteComment}
                  disabled={deleting}
                >
                  {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : '确认删除'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 审核员删除弹窗 */}
      {reviewerDeleteComment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <Card className="w-full max-w-md mx-4 shadow-2xl border-0">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2 text-amber-500">
                <Shield className="w-5 h-5" />
                <span className="font-semibold">审核员投票删除</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-muted-foreground">
                需要3位审核员投票才能删除此评论。当前已有 {reviewerDeleteComment.reviewer_delete_count || 0}/3 票。
              </p>
              <div className="p-3 bg-muted/50 rounded-lg text-sm">
                {reviewerDeleteComment.content}
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">删除原因 *</label>
                <Input
                  placeholder="请输入删除原因..."
                  value={reviewerDeleteReason}
                  onChange={(e) => setReviewerDeleteReason(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  审核员删除将扣除用户5信誉分
                </p>
              </div>
              
              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setReviewerDeleteComment(null)
                    setReviewerDeleteReason('')
                  }}
                >
                  取消
                </Button>
                <Button
                  variant="default"
                  className="flex-1 bg-amber-500 hover:bg-amber-600"
                  onClick={handleReviewerDelete}
                  disabled={deleting || !reviewerDeleteReason.trim()}
                >
                  {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : '投票删除'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 图片预览弹窗 */}
      {previewImage && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setPreviewImage(null)}
        >
          <div className="relative w-full max-w-4xl max-h-screen p-4 flex items-center justify-center">
            <Button 
              variant="ghost" 
              size="icon" 
              className="absolute top-4 right-4 text-white hover:bg-white/20 z-10"
              onClick={(e) => {
                e.stopPropagation()
                setPreviewImage(null)
              }}
            >
              <X className="w-6 h-6" />
            </Button>
            <img 
              src={previewImage} 
              alt="Preview" 
              className="max-w-full max-h-[90vh] object-contain rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}

      {/* 分享弹窗 */}
      {showShareModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <Card className="w-full max-w-md mx-4 shadow-2xl border-0">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-primary" />
                  <span className="font-semibold">分享给好友</span>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setShowShareModal(false)}>
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* 帖子预览 */}
              <div className="p-3 bg-muted/50 rounded-lg">
                <p className="text-sm text-muted-foreground mb-1">分享内容:</p>
                <p className="text-sm line-clamp-2">{post.content}</p>
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
