'use client'

import React, { useState, useEffect } from 'react'
import { 
  Heart, 
  Clock, 
  MapPin, 
  DollarSign,
  Plus,
  Filter,
  Search,
  CheckCircle,
  AlertCircle,
  User,
  X,
  Loader2,
  Trash2,
  Eye,
  ThumbsUp,
  Star,
  TrendingUp,
  Lock
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { tasksApi, Task as ApiTask, TaskApplication, getToken, authApi, userLikeApi } from '@/lib/api'

interface Task {
  id: number
  title: string
  description: string
  reward: number
  location: string
  deadline: string
  category: string
  status: 'open' | 'assigned' | 'in_progress' | 'completed'
  author: {
    id: number
    name: string
    avatar?: string
    rating: number
  }
  assigneeId?: number  // 接单者ID
  applicants: number
  privateInfo?: string  // 私密信息，仅接单者和发布者可见
}

// 分类映射
const categoryMap: Record<string, string> = {
  'errand': '跑腿',
  'purchase': '代买',
  'study': '学业',
  'other': '其他'
}

const categoryMapReverse: Record<string, string> = {
  '跑腿': 'errand',
  '代买': 'purchase',
  '学业': 'study',
  '其他': 'other'
}

const categories = ['全部', '跑腿', '代买', '学业', '其他']

// 格式化截止时间
function formatDeadline(deadline?: string): string {
  if (!deadline) return '待定'
  const date = new Date(deadline)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffDays < 0) return '已过期'
  if (diffDays === 0) {
    const hours = date.getHours().toString().padStart(2, '0')
    const mins = date.getMinutes().toString().padStart(2, '0')
    return `今天 ${hours}:${mins}`
  }
  if (diffDays === 1) return '明天'
  if (diffDays <= 7) return `${diffDays}天后`
  return date.toLocaleDateString('zh-CN')
}

// 转换API任务数据到组件格式
function convertTask(apiTask: ApiTask): Task {
  return {
    id: apiTask.id,
    title: apiTask.title,
    description: apiTask.description,
    reward: apiTask.reward,
    location: apiTask.location || '待定',
    deadline: formatDeadline(apiTask.deadline),
    category: categoryMap[apiTask.category] || '其他',
    status: apiTask.status as Task['status'],
    author: {
      id: apiTask.publisher_id,
      name: apiTask.publisher?.name || '匿名',
      rating: 4.5 // API暂无评分字段
    },
    assigneeId: apiTask.assignee_id,
    applicants: apiTask.application_count || 0,
    privateInfo: apiTask.private_info  // 私密信息
  }
}

export function MutualHelp() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [activeCategory, setActiveCategory] = useState('全部')
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    reward: '',
    location: '',
    deadline: '',
    category: '跑腿',
    privateInfo: ''  // 私密信息
  })
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [applications, setApplications] = useState<TaskApplication[]>([])
  const [showApplicationsModal, setShowApplicationsModal] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [currentUserId, setCurrentUserId] = useState<number | null>(null)
  const [appliedTaskIds, setAppliedTaskIds] = useState<number[]>([])
  const [likedUsers, setLikedUsers] = useState<Set<number>>(new Set())  // 已点赞的用户
  const [likingUser, setLikingUser] = useState<number | null>(null)  // 正在点赞中的用户ID

  // 加载任务列表
  const loadTasks = async (category?: string) => {
    try {
      setLoading(true)
      setError('')
      const apiCategory = category && category !== '全部' ? categoryMapReverse[category] : undefined
      const response = await tasksApi.getTasks(1, 50, apiCategory)
      setTasks(response.items.map(convertTask))
    } catch (err) {
      console.error('加载任务失败:', err)
      setError('加载任务失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
    // 获取当前用户ID和已申请的任务
    const fetchCurrentUser = async () => {
      if (getToken()) {
        try {
          const user = await authApi.getCurrentUser()
          setCurrentUserId(user.id)
          // 获取已申请的任务ID列表
          const appliedIds = await tasksApi.getMyAppliedTaskIds()
          setAppliedTaskIds(appliedIds.task_ids)
        } catch (err) {
          console.error('获取用户信息失败:', err)
        }
      }
    }
    fetchCurrentUser()
  }, [])

  const filteredTasks = tasks.filter(task => {
    const matchCategory = activeCategory === '全部' || task.category === activeCategory
    const matchSearch = task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                       task.description.toLowerCase().includes(searchQuery.toLowerCase())
    return matchCategory && matchSearch
  })

  // 创建任务
  const handleCreateTask = async () => {
    if (!newTask.title || !newTask.description || !newTask.reward) return
    
    if (!getToken()) {
      setError('请先登录')
      return
    }

    try {
      setSubmitting(true)
      setError('')
      const createdTask = await tasksApi.createTask({
        title: newTask.title,
        description: newTask.description,
        category: categoryMapReverse[newTask.category] || 'other',
        reward: Number(newTask.reward),
        location: newTask.location || undefined,
        deadline: newTask.deadline || undefined,
        private_info: newTask.privateInfo || undefined  // 私密信息
      })
      
      setTasks([convertTask(createdTask), ...tasks])
      setShowCreateModal(false)
      setNewTask({ title: '', description: '', reward: '', location: '', deadline: '', category: '跑腿', privateInfo: '' })
    } catch (err: any) {
      setError(err.message || '创建任务失败')
    } finally {
      setSubmitting(false)
    }
  }

  // 接受任务
  const handleApplyTask = async (taskId: number) => {
    if (!getToken()) {
      setError('请先登录')
      return
    }

    try {
      await tasksApi.applyTask(taskId)
      // 更新已申请列表
      setAppliedTaskIds([...appliedTaskIds, taskId])
      // 刷新任务列表
      loadTasks()
    } catch (err: any) {
      setError(err.message || '申请任务失败')
    }
  }

  // 删除任务
  const handleDeleteTask = async (taskId: number) => {
    if (!getToken()) {
      setError('请先登录')
      return
    }

    try {
      await tasksApi.deleteTask(taskId)
      loadTasks()
    } catch (err: any) {
      setError(err.message || '删除任务失败')
    }
  }

  // 查看申请列表
  const handleViewApplications = async (task: Task) => {
    if (!getToken()) {
      setError('请先登录')
      return
    }

    try {
      setSelectedTask(task)
      const apps = await tasksApi.getApplications(task.id)
      setApplications(apps)
      setShowApplicationsModal(true)
    } catch (err: any) {
      setError(err.message || '获取申请列表失败')
    }
  }

  // 查看任务详情时检查点赞状态
  const handleViewDetail = async (task: Task) => {
    setSelectedTask(task)
    setShowDetailModal(true)
    // 先清空点赞状态，确保初始状态为未点赞
    setLikedUsers(new Set())
    
    // 如果任务已完成，检查对方的点赞状态
    if (task.status === 'completed' && getToken()) {
      const targetUserId = currentUserId === task.author.id ? task.assigneeId : task.author.id
      if (targetUserId) {
        try {
          const status = await userLikeApi.getLikeStatus(targetUserId)
          if (status.liked) {
            setLikedUsers(new Set([targetUserId]))
          }
        } catch (e) {
          // 忽略错误，保持未点赞状态
        }
      }
    }
  }

  // 点赞/取消点赞用户
  const handleLikeUser = async (userId: number) => {
    if (!getToken()) {
      setError('请先登录')
      return
    }

    try {
      setLikingUser(userId)
      const isLiked = likedUsers.has(userId)
      
      if (isLiked) {
        await userLikeApi.unlikeUser(userId)
        setLikedUsers(prev => {
          const newSet = new Set(prev)
          newSet.delete(userId)
          return newSet
        })
      } else {
        await userLikeApi.likeUser(userId)
        setLikedUsers(prev => new Set(prev).add(userId))
      }
    } catch (err: any) {
      setError(err.message || '操作失败')
    } finally {
      setLikingUser(null)
    }
  }

  // 接受申请
  const handleAcceptApplication = async (applicationId: number) => {
    if (!selectedTask) return

    try {
      setSubmitting(true)
      await tasksApi.acceptApplication(selectedTask.id, applicationId)
      setShowApplicationsModal(false)
      setSelectedTask(null)
      setApplications([])
      loadTasks()
    } catch (err: any) {
      setError(err.message || '接受申请失败')
    } finally {
      setSubmitting(false)
    }
  }

  // 完成任务
  const handleCompleteTask = async (taskId: number) => {
    if (!getToken()) {
      setError('请先登录')
      return
    }

    try {
      await tasksApi.completeTask(taskId)
      loadTasks()
    } catch (err: any) {
      setError(err.message || '完成任务失败')
    }
  }

  const getStatusBadge = (status: Task['status']) => {
    switch (status) {
      case 'open':
        return <Badge variant="success" className="gap-1"><AlertCircle className="w-3 h-3" />招募中</Badge>
      case 'assigned':
        return <Badge variant="default" className="gap-1"><User className="w-3 h-3" />已分配</Badge>
      case 'in_progress':
        return <Badge variant="warning" className="gap-1"><Clock className="w-3 h-3" />进行中</Badge>
      case 'completed':
        return <Badge variant="secondary" className="gap-1"><CheckCircle className="w-3 h-3" />已完成</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* 头部 */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2 text-foreground">
              <Heart className="w-6 h-6 text-pink-500" />
              互帮互助
            </h1>
            <p className="text-muted-foreground mt-1">发布任务，寻求帮助；接受任务，赚取赏金</p>
          </div>
          <Button variant="gradient" onClick={() => setShowCreateModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            发布任务
          </Button>
        </div>

        {/* 搜索和筛选 */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="搜索任务..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            {categories.map((cat) => (
              <Button
                key={cat}
                variant={activeCategory === cat ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveCategory(cat)}
              >
                {cat}
              </Button>
            ))}
          </div>
        </div>

        {/* 任务列表 */}
        <div className="grid gap-4">
          {loading ? (
            <div className="text-center py-12">
              <Loader2 className="w-8 h-8 mx-auto text-primary animate-spin mb-4" />
              <p className="text-muted-foreground">加载中...</p>
            </div>
          ) : filteredTasks.map((task) => (
            <Card key={task.id} className="border-0 shadow-md hover:shadow-lg transition-all card-hover cursor-pointer" onClick={() => handleViewDetail(task)}>
              <CardContent className="p-6">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-lg text-foreground">{task.title}</h3>
                      {getStatusBadge(task.status)}
                      <Badge variant="outline">{task.category}</Badge>
                    </div>
                    <p className="text-muted-foreground mb-4">{task.description}</p>
                    
                    <div className="flex flex-wrap gap-4 text-sm">
                      <span className="flex items-center gap-1 text-muted-foreground">
                        <MapPin className="w-4 h-4" />
                        {task.location}
                      </span>
                      <span className="flex items-center gap-1 text-muted-foreground">
                        <Clock className="w-4 h-4" />
                        {task.deadline}
                      </span>
                      <span className="flex items-center gap-1 text-muted-foreground">
                        <User className="w-4 h-4" />
                        {task.applicants}人申请
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex flex-col items-end gap-3">
                    <div className="text-right">
                      <div className="flex items-center gap-1 text-2xl font-bold text-primary">
                        <DollarSign className="w-5 h-5" />
                        {task.reward}
                      </div>
                      <span className="text-xs text-muted-foreground">赏金</span>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Avatar className="w-8 h-8">
                        {task.author.avatar && <AvatarImage src={task.author.avatar} alt={task.author.name} />}
                        <AvatarFallback className="text-xs">{task.author.name.slice(0, 1)}</AvatarFallback>
                      </Avatar>
                      <div className="text-sm">
                        <p className="font-medium text-foreground">{task.author.name}</p>
                        <p className="text-xs text-muted-foreground">信誉 {task.author.rating}</p>
                      </div>
                    </div>
                    
                    {/* 已申请状态 */}
                    {task.status === 'open' && currentUserId !== task.author.id && appliedTaskIds.includes(task.id) && (
                      <Badge variant="outline" className="px-3 py-1.5 bg-muted text-muted-foreground border-muted" onClick={(e) => e.stopPropagation()}>
                        已申请
                      </Badge>
                    )}
                    {/* 接受任务按钮 */}
                    {task.status === 'open' && currentUserId !== task.author.id && !appliedTaskIds.includes(task.id) && (
                      <Button variant="gradient" size="sm" onClick={(e) => { e.stopPropagation(); handleApplyTask(task.id); }}>
                        接受任务
                      </Button>
                    )}
                    {/* 查看申请按钮 */}
                    {task.status === 'open' && currentUserId === task.author.id && task.applicants > 0 && (
                      <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); handleViewApplications(task); }}>
                        查看申请 ({task.applicants})
                      </Button>
                    )}
                    {/* 删除任务按钮 - 发布者可删除无人申请的任务 */}
                    {task.status === 'open' && currentUserId === task.author.id && task.applicants === 0 && (
                      <Button variant="destructive" size="sm" onClick={(e) => { e.stopPropagation(); handleDeleteTask(task.id); }}>
                        <Trash2 className="w-4 h-4 mr-1" />
                        删除
                      </Button>
                    )}
                    {(task.status === 'assigned' || task.status === 'in_progress') && currentUserId === task.assigneeId && (
                      <Badge variant="outline" className="px-3 py-1.5 bg-muted text-muted-foreground border-muted" onClick={(e) => e.stopPropagation()}>
                        你已接单
                      </Badge>
                    )}
                    {(task.status === 'assigned' || task.status === 'in_progress') && currentUserId === task.author.id && (
                      <Button variant="gradient" size="sm" onClick={(e) => { e.stopPropagation(); handleCompleteTask(task.id); }}>
                        确认完成
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {filteredTasks.length === 0 && !loading && (
          <div className="text-center py-12">
            <Heart className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">暂无相关任务</p>
          </div>
        )}

        {error && (
          <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-destructive text-destructive-foreground px-4 py-2 rounded-lg shadow-lg z-50">
            {error}
          </div>
        )}

        {/* 创建任务弹窗 */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-foreground/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-md animate-scale-in">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>发布新任务</CardTitle>
                <Button variant="ghost" size="icon" onClick={() => setShowCreateModal(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-foreground">任务标题</label>
                  <Input
                    placeholder="简短描述你的任务"
                    value={newTask.title}
                    onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground">任务描述</label>
                  <Textarea
                    placeholder="详细说明任务内容..."
                    value={newTask.description}
                    onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-foreground">赏金 (元)</label>
                    <Input
                      type="number"
                      placeholder="0"
                      value={newTask.reward}
                      onChange={(e) => setNewTask({ ...newTask, reward: e.target.value })}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-foreground">分类</label>
                    <select
                      value={newTask.category}
                      onChange={(e) => setNewTask({ ...newTask, category: e.target.value })}
                      className="mt-1 w-full h-11 rounded-lg border border-input bg-background px-3 text-sm"
                    >
                      {categories.filter(c => c !== '全部').map(cat => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground">地点</label>
                  <Input
                    placeholder="任务地点"
                    value={newTask.location}
                    onChange={(e) => setNewTask({ ...newTask, location: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground">截止时间</label>
                  <Input
                    type="datetime-local"
                    value={newTask.deadline}
                    onChange={(e) => setNewTask({ ...newTask, deadline: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground flex items-center gap-1">
                    <Lock className="w-3 h-3" />
                    私密信息（可选）
                  </label>
                  <Textarea
                    placeholder="填写快递码、手机尾号、取件码等私密信息，仅接单者可见"
                    value={newTask.privateInfo}
                    onChange={(e) => setNewTask({ ...newTask, privateInfo: e.target.value })}
                    className="mt-1"
                    rows={2}
                  />
                  <p className="text-xs text-muted-foreground mt-1">此信息仅在接单后对接单者可见</p>
                </div>
                <Button variant="gradient" className="w-full" onClick={handleCreateTask} disabled={submitting}>
                  {submitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                  {submitting ? '发布中...' : '发布任务'}
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        {/* 申请列表弹窗 */}
        {showApplicationsModal && selectedTask && (
          <div className="fixed inset-0 bg-foreground/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-md animate-scale-in max-h-[80vh] overflow-hidden flex flex-col">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>申请列表 - {selectedTask.title}</CardTitle>
                  <p className="text-xs text-muted-foreground mt-1">按优先分排序（信誉分+好评率）</p>
                </div>
                <Button variant="ghost" size="icon" onClick={() => {
                  setShowApplicationsModal(false)
                  setSelectedTask(null)
                  setApplications([])
                }}>
                  <X className="w-4 h-4" />
                </Button>
              </CardHeader>
              <CardContent className="overflow-y-auto flex-1">
                {applications.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">暂无申请</p>
                ) : (
                  <div className="space-y-3">
                    {applications.map((app, index) => (
                      <div key={app.id} className="p-3 bg-muted rounded-lg">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                              <div className="relative">
                                <Avatar className="w-10 h-10">
                                  {app.applicant?.avatar && <AvatarImage src={app.applicant.avatar} alt={app.applicant.name} />}
                                  <AvatarFallback>{app.applicant?.name?.slice(0, 1) || '?'}</AvatarFallback>
                                </Avatar>
                              {index === 0 && (
                                <div className="absolute -top-1 -right-1 w-5 h-5 bg-yellow-500 rounded-full flex items-center justify-center">
                                  <Star className="w-3 h-3 text-white fill-white" />
                                </div>
                              )}
                            </div>
                            <div>
                              <p className="font-medium text-foreground">{app.applicant?.name || '匿名用户'}</p>
                              {app.message && (
                                <p className="text-sm text-muted-foreground">{app.message}</p>
                              )}
                              <div className="flex items-center gap-2 mt-1">
                                <Badge variant="outline" className="text-xs gap-1">
                                  <TrendingUp className="w-3 h-3" />
                                  优先分: {app.priority_score ?? 80}
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  {new Date(app.created_at).toLocaleString('zh-CN')}
                                </span>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {/* 接受按钮 */}
                            {app.status === 'pending' && (
                              <Button 
                                variant="gradient" 
                                size="sm" 
                                onClick={() => handleAcceptApplication(app.id)}
                                disabled={submitting}
                              >
                                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : '接受'}
                              </Button>
                            )}
                            {app.status === 'accepted' && (
                              <Badge variant="success">已接受</Badge>
                            )}
                            {app.status === 'rejected' && (
                              <Badge variant="secondary">已拒绝</Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* 任务详情弹窗 */}
        {showDetailModal && selectedTask && (
          <div className="fixed inset-0 bg-foreground/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-lg animate-scale-in">
              <CardHeader className="flex flex-row items-center justify-between">
                <div className="flex items-center gap-3">
                  <CardTitle>{selectedTask.title}</CardTitle>
                  {getStatusBadge(selectedTask.status)}
                </div>
                <Button variant="ghost" size="icon" onClick={() => {
                  setShowDetailModal(false)
                  setSelectedTask(null)
                }}>
                  <X className="w-4 h-4" />
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">任务描述</label>
                  <p className="mt-1 text-foreground">{selectedTask.description}</p>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">赏金</label>
                    <p className="mt-1 text-xl font-bold text-primary">¥{selectedTask.reward}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">分类</label>
                    <div className="mt-1">
                      <Badge variant="outline">{selectedTask.category}</Badge>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">地点</label>
                    <p className="mt-1 flex items-center gap-1 text-foreground">
                      <MapPin className="w-4 h-4" />
                      {selectedTask.location}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">截止时间</label>
                    <p className="mt-1 flex items-center gap-1 text-foreground">
                      <Clock className="w-4 h-4" />
                      {selectedTask.deadline}
                    </p>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-muted-foreground">发布者</label>
                  <div className="mt-1 flex items-center gap-2">
                    <Avatar className="w-8 h-8">
                      {/* @ts-ignore */}
                      {selectedTask.author.avatar && <AvatarImage src={selectedTask.author.avatar} alt={selectedTask.author.name} />}
                      <AvatarFallback className="text-xs">{selectedTask.author.name.slice(0, 1)}</AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium text-foreground">{selectedTask.author.name}</p>
                      <p className="text-xs text-muted-foreground">信誉 {selectedTask.author.rating}</p>
                    </div>
                  </div>
                </div>

                {/* 私密信息 - 仅接单者和发布者可见 */}
                {selectedTask.privateInfo && (currentUserId === selectedTask.author.id || currentUserId === selectedTask.assigneeId) && (
                  <div className="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
                    <label className="text-sm font-medium text-amber-800 dark:text-amber-200 flex items-center gap-1">
                      <Lock className="w-3 h-3" />
                      私密信息
                    </label>
                    <p className="mt-1 text-amber-900 dark:text-amber-100 whitespace-pre-wrap">{selectedTask.privateInfo}</p>
                  </div>
                )}

                <div className="text-sm text-muted-foreground">
                  <User className="w-4 h-4 inline mr-1" />
                  {selectedTask.applicants}人申请
                </div>

                <div className="flex gap-2 pt-2">
                  {/* 已申请状态 */}
                  {selectedTask.status === 'open' && currentUserId !== selectedTask.author.id && appliedTaskIds.includes(selectedTask.id) && (
                    <Badge variant="outline" className="px-4 py-2 bg-muted text-muted-foreground border-muted">
                      已申请，等待审核
                    </Badge>
                  )}
                  {/* 接受任务按钮 */}
                  {selectedTask.status === 'open' && currentUserId !== selectedTask.author.id && !appliedTaskIds.includes(selectedTask.id) && (
                    <Button variant="gradient" className="flex-1" onClick={() => { handleApplyTask(selectedTask.id); setShowDetailModal(false); }}>
                      接受任务
                    </Button>
                  )}
                  {/* 查看申请按钮 */}
                  {selectedTask.status === 'open' && currentUserId === selectedTask.author.id && selectedTask.applicants > 0 && (
                    <Button variant="outline" className="flex-1" onClick={() => { setShowDetailModal(false); handleViewApplications(selectedTask); }}>
                      查看申请 ({selectedTask.applicants})
                    </Button>
                  )}
                  {/* 删除任务按钮 */}
                  {selectedTask.status === 'open' && currentUserId === selectedTask.author.id && selectedTask.applicants === 0 && (
                    <Button variant="destructive" className="flex-1" onClick={() => { handleDeleteTask(selectedTask.id); setShowDetailModal(false); }}>
                      <Trash2 className="w-4 h-4 mr-1" />
                      删除任务
                    </Button>
                  )}
                  {(selectedTask.status === 'assigned' || selectedTask.status === 'in_progress') && currentUserId === selectedTask.assigneeId && (
                    <Badge variant="outline" className="px-4 py-2 bg-muted text-muted-foreground border-muted">
                      你已接单
                    </Badge>
                  )}
                  {(selectedTask.status === 'assigned' || selectedTask.status === 'in_progress') && currentUserId === selectedTask.author.id && (
                    <Button variant="gradient" className="flex-1" onClick={() => { handleCompleteTask(selectedTask.id); setShowDetailModal(false); }}>
                      确认完成
                    </Button>
                  )}
                  {/* 已完成任务 - 可以给对方点赞 */}
                  {selectedTask.status === 'completed' && (currentUserId === selectedTask.author.id || currentUserId === selectedTask.assigneeId) && (
                    <div className="w-full">
                      <div className="p-3 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg mb-3">
                        <p className="text-sm text-green-800 dark:text-green-200 flex items-center gap-1">
                          <CheckCircle className="w-4 h-4" />
                          任务已完成
                        </p>
                      </div>
                      {/* 点赞按钮 */}
                      {(() => {
                        const targetUserId = currentUserId === selectedTask.author.id ? selectedTask.assigneeId : selectedTask.author.id
                        const targetName = currentUserId === selectedTask.author.id ? '接单者' : '发布者'
                        if (!targetUserId) return null
                        const isLiked = likedUsers.has(targetUserId)
                        return (
                          <Button
                            variant={isLiked ? "secondary" : "outline"}
                            className={`w-full gap-2 ${isLiked ? 'text-pink-500 border-pink-200' : ''}`}
                            onClick={() => handleLikeUser(targetUserId)}
                            disabled={likingUser === targetUserId}
                          >
                            {likingUser === targetUserId ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <ThumbsUp className={`w-4 h-4 ${isLiked ? 'fill-current' : ''}`} />
                            )}
                            {isLiked ? `已点赞${targetName}` : `给${targetName}点赞`}
                          </Button>
                        )
                      })()}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
