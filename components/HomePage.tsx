'use client'

import React, { useState, useEffect } from 'react'
import { 
  School, 
  Heart, 
  MessageSquare, 
  Bell, 
  Users, 
  Wallet,
  ArrowRight,
  TrendingUp,
  Clock,
  Star,
  Loader2,
  Shield
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { announcementsApi, tasksApi, adminApi, postsApi, Announcement, Task, Post, getToken } from '@/lib/api'

interface HomePageProps {
  onNavigate: (page: string) => void
  user: { name: string; role: string } | null
}

const quickActions = [
  { id: 'school', label: '学校介绍', icon: School, color: 'from-blue-500 to-blue-600', desc: '了解校园文化' },
  { id: 'help', label: '互帮互助', icon: Heart, color: 'from-pink-500 to-rose-500', desc: '发布/接受任务' },
  { id: 'wall', label: '校园墙', icon: MessageSquare, color: 'from-purple-500 to-violet-500', desc: '分享校园生活' },
  { id: 'friends', label: '好友', icon: Users, color: 'from-green-500 to-emerald-500', desc: '管理好友关系' },
  { id: 'wallet', label: '钱包', icon: Wallet, color: 'from-amber-500 to-orange-500', desc: '余额与交易' },
  { id: 'announcements', label: '公告', icon: Bell, color: 'from-cyan-500 to-teal-500', desc: '查看最新通知' },
]

// 热门话题类型
interface HotTopic {
  id: number
  title: string
  replies: number
  views: number
}

export function HomePage({ onNavigate, user }: HomePageProps) {
  const [announcements, setAnnouncements] = useState<Announcement[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [hotTopics, setHotTopics] = useState<HotTopic[]>([])
  const [stats, setStats] = useState({
    user_count: 0,
    post_count: 0,
    task_count: 0,
    open_task_count: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      // 并行加载所有数据
      const [announcementRes, taskRes, statsRes, hotPostsRes] = await Promise.all([
        announcementsApi.getPublicAnnouncements(1, 3),
        tasksApi.getTasks(1, 3, undefined, 'open'),
        adminApi.getPublicStats(),
        postsApi.getHotPosts(3)
      ])

      setAnnouncements(announcementRes.items)
      setTasks(taskRes.items)
      setStats(statsRes)

      // 将热门帖子转换为热门话题格式
      const topics: HotTopic[] = hotPostsRes.items.map((post: Post) => ({
        id: post.id,
        title: post.content.slice(0, 30) + (post.content.length > 30 ? '...' : ''),
        replies: post.comments_count,
        views: post.likes_count * 10 + post.comments_count * 5 // 估算浏览量
      }))
      setHotTopics(topics)
    } catch (err) {
      console.error('Failed to load home data:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN')
  }

  const getAnnouncementType = (type: string) => {
    const types: Record<string, string> = {
      important: '重要',
      notice: '通知',
      activity: '活动',
      academic: '学术'
    }
    return types[type] || type
  }
  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-primary/10 via-background to-secondary/10 pt-24 pb-16">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-20 right-10 w-72 h-72 bg-primary/20 rounded-full blur-3xl animate-pulse-slow" />
          <div className="absolute bottom-10 left-10 w-72 h-72 bg-secondary/20 rounded-full blur-3xl animate-pulse-slow animation-delay-200" />
        </div>
        
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-4xl md:text-5xl font-bold mb-6">
              欢迎来到<span className="text-gradient">智慧校园</span>
            </h1>
            <p className="text-lg text-muted-foreground mb-8">
              一站式校园服务平台，连接师生，共建美好校园生活
            </p>
            {!user && (
              <div className="flex gap-4 justify-center">
                <Button variant="gradient" size="lg" onClick={() => onNavigate('login')}>
                  立即加入
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
                <Button variant="outline" size="lg" onClick={() => onNavigate('school')}>
                  了解更多
                </Button>
              </div>
            )}
          </div>

          {/* 统计数据 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-12">
            {[
              { label: '注册用户', value: stats.user_count, icon: Users },
              { label: '校园动态', value: stats.post_count, icon: MessageSquare },
              { label: '互助任务', value: stats.task_count, icon: Heart },
              { label: '进行中任务', value: stats.open_task_count, icon: Wallet },
            ].map((stat, index) => (
              <Card key={index} className="card-hover border-0 bg-card/80 backdrop-blur">
                <CardContent className="p-4 text-center">
                  <stat.icon className="w-8 h-8 mx-auto mb-2 text-primary" />
                  <div className="text-2xl font-bold text-foreground">{stat.value}</div>
                  <div className="text-sm text-muted-foreground">{stat.label}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 快捷入口 */}
      <section className="py-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
          <Star className="w-6 h-6 text-primary" />
          快捷服务
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Card
                key={action.id}
                className="card-hover cursor-pointer group border-0 overflow-hidden"
                onClick={() => onNavigate(action.id)}
              >
                <CardContent className="p-6 text-center">
                  <div className={`w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br ${action.color} flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                    <Icon className="w-7 h-7 text-primary-foreground" />
                  </div>
                  <h3 className="font-semibold text-foreground">{action.label}</h3>
                  <p className="text-xs text-muted-foreground mt-1">{action.desc}</p>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* 信誉系统入口 */}
        <Card 
          className="mt-6 border-0 shadow-lg bg-gradient-to-r from-primary/5 via-transparent to-amber-50/50 cursor-pointer hover:shadow-xl transition-all group"
          onClick={() => onNavigate('reputation-rules')}
        >
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                  <Shield className="w-7 h-7 text-primary-foreground" />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-foreground">信誉系统规则</h3>
                  <p className="text-sm text-muted-foreground">了解信誉分规则，成为优秀用户</p>
                </div>
              </div>
              <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
            </div>
          </CardContent>
        </Card>
      </section>

      {/* 内容区域 */}
      <section className="py-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* 最新公告 */}
          <Card className="lg:col-span-2 border-0 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5 text-primary" />
                最新公告
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => onNavigate('announcements')}>
                查看全部 <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {loading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </div>
              ) : announcements.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">暂无公告</div>
              ) : (
                announcements.map((item) => (
                <div
                  key={item.id}
                  className="p-4 rounded-xl bg-muted/50 hover:bg-muted transition-colors cursor-pointer"
                  onClick={() => onNavigate('announcements')}
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-medium text-foreground">{item.title}</h3>
                    <Badge variant={item.type === 'important' ? 'destructive' : 'secondary'}>
                      {getAnnouncementType(item.type)}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2">{item.content}</p>
                  <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    {formatDate(item.publish_date)}
                  </div>
                </div>
              ))
              )}
            </CardContent>
          </Card>

          {/* 侧边栏 */}
          <div className="space-y-6">
            {/* 热门话题 */}
            <Card className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <TrendingUp className="w-5 h-5 text-primary" />
                  热门话题
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {loading ? (
                  <div className="flex justify-center py-4">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  </div>
                ) : hotTopics.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground">暂无热门话题</div>
                ) : (
                  hotTopics.map((topic, index) => (
                    <div
                      key={topic.id}
                      className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted transition-colors cursor-pointer"
                      onClick={() => onNavigate('wall')}
                    >
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        index === 0 ? 'bg-red-500 text-primary-foreground' :
                        index === 1 ? 'bg-orange-500 text-primary-foreground' :
                        'bg-yellow-500 text-primary-foreground'
                      }`}>
                        {index + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate text-foreground">{topic.title}</p>
                        <p className="text-xs text-muted-foreground">{topic.replies}回复 · {topic.views}热度</p>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            {/* 最新互助 */}
            <Card className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Heart className="w-5 h-5 text-pink-500" />
                  最新互助
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {loading ? (
                  <div className="flex justify-center py-4">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  </div>
                ) : tasks.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground">暂无任务</div>
                ) : (
                  tasks.map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted transition-colors cursor-pointer"
                    onClick={() => onNavigate('help')}
                  >
                    <Avatar className="w-10 h-10">
                      {task.publisher?.avatar && <AvatarImage src={task.publisher.avatar} alt={task.publisher.name} />}
                      <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                        {task.publisher?.name?.slice(0, 1) || '匿'}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate text-foreground">{task.title}</p>
                      <p className="text-xs text-muted-foreground">赏金 ¥{task.reward}</p>
                    </div>
                    <Badge variant={task.status === 'open' ? 'default' : 'success'}>
                      {task.status === 'open' ? '进行中' : '已完成'}
                    </Badge>
                  </div>
                ))
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-muted/50 py-8 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                <School className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="font-bold text-foreground">智慧校园服务平台</span>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2024 智慧校园. 为校园生活提供便捷服务
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
