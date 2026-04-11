'use client'

import React, { useState, useEffect } from 'react'
import { 
  Settings,
  Users,
  MessageSquare,
  Bell,
  Shield,
  BarChart3,
  FileText,
  Search,
  MoreHorizontal,
  Check,
  X,
  Eye,
  Trash2,
  UserCog,
  TrendingUp,
  Loader2
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'
import { adminApi, getToken } from '@/lib/api'

interface Stats {
  userCount: string
  postCount: string
  pendingCount: string
  reportCount: string
  userChange: string
  postChange: string
}

export function AdminPanel() {
  const [activeTab, setActiveTab] = useState('overview')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [statsData, setStatsData] = useState<Stats>({
    userCount: '0',
    postCount: '0',
    pendingCount: '0',
    reportCount: '0',
    userChange: '+0',
    postChange: '+0'
  })

  // 加载统计数据
  const loadStats = async () => {
    try {
      setLoading(true)
      const data = await adminApi.getStats()
      setStatsData({
        userCount: data.user_count?.toLocaleString() || '0',
        postCount: data.post_count?.toLocaleString() || '0',
        pendingCount: '0', // 暂无待审核统计
        reportCount: data.pending_report_count?.toString() || '0',
        userChange: `+${data.active_user_count || 0}`,
        postChange: `+${data.open_task_count || 0}`
      })
    } catch (err) {
      console.error('加载统计失败:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (getToken()) {
      loadStats()
    } else {
      setLoading(false)
    }
  }, [])

  const stats = [
    { label: '总用户', value: statsData.userCount, change: statsData.userChange, icon: Users, color: 'from-blue-500 to-cyan-500' },
    { label: '帖子总数', value: statsData.postCount, change: statsData.postChange, icon: MessageSquare, color: 'from-purple-500 to-violet-500' },
    { label: '待审核', value: statsData.pendingCount, change: '-0', icon: FileText, color: 'from-orange-500 to-amber-500' },
    { label: '待处理举报', value: statsData.reportCount, change: '+0', icon: Shield, color: 'from-red-500 to-pink-500' },
  ]

  const pendingPosts = [
    { id: 1, author: '张同学', content: '分享一下期末复习资料...', time: '10分钟前', type: '校园墙' },
    { id: 2, author: '李同学', content: '求帮取快递，赏金10元...', time: '30分钟前', type: '互助' },
    { id: 3, author: '王同学', content: '有人一起拼车吗...', time: '1小时前', type: '校园墙' },
  ]

  const reports = [
    { id: 1, reporter: '陈同学', target: '某用户', reason: '发布不当言论', time: '2小时前', status: 'pending' },
    { id: 2, reporter: '刘同学', target: '某帖子', reason: '涉嫌广告', time: '3小时前', status: 'pending' },
  ]

  const recentUsers = [
    { id: 1, name: '新用户A', department: '计算机学院', joinTime: '今天 14:30', status: 'active' },
    { id: 2, name: '新用户B', department: '商学院', joinTime: '今天 12:00', status: 'active' },
    { id: 3, name: '新用户C', department: '文学院', joinTime: '昨天 18:20', status: 'inactive' },
  ]

  const tabs = [
    { id: 'overview', label: '概览', icon: BarChart3 },
    { id: 'users', label: '用户管理', icon: Users },
    { id: 'content', label: '内容审核', icon: FileText },
    { id: 'reports', label: '举报处理', icon: Shield },
    { id: 'announcements', label: '公告管理', icon: Bell },
    { id: 'settings', label: '系统设置', icon: Settings },
  ]

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-7xl mx-auto px-4">
        {/* 头部 */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold flex items-center gap-2 text-foreground">
            <Settings className="w-6 h-6 text-primary" />
            后台管理
          </h1>
          <p className="text-muted-foreground mt-1">管理平台用户、内容和系统设置</p>
        </div>

        <div className="grid lg:grid-cols-5 gap-6">
          {/* 侧边栏 */}
          <Card className="lg:col-span-1 border-0 shadow-lg h-fit">
            <CardContent className="p-2">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      activeTab === tab.id
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-muted text-foreground'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    {tab.label}
                  </button>
                )
              })}
            </CardContent>
          </Card>

          {/* 主内容 */}
          <div className="lg:col-span-4 space-y-6">
            {activeTab === 'overview' && (
              <>
                {/* 统计卡片 */}
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {stats.map((stat, index) => {
                    const Icon = stat.icon
                    return (
                      <Card key={index} className="border-0 shadow-md">
                        <CardContent className="p-6">
                          <div className="flex items-center justify-between mb-4">
                            <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center`}>
                              <Icon className="w-6 h-6 text-primary-foreground" />
                            </div>
                            <Badge variant={stat.change.startsWith('+') ? 'success' : 'secondary'} className="gap-1">
                              <TrendingUp className="w-3 h-3" />
                              {stat.change}
                            </Badge>
                          </div>
                          <p className="text-2xl font-bold text-foreground">{stat.value}</p>
                          <p className="text-sm text-muted-foreground">{stat.label}</p>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>

                {/* 待审核内容 */}
                <Card className="border-0 shadow-lg">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <FileText className="w-5 h-5 text-primary" />
                        待审核内容
                      </span>
                      <Badge>{pendingPosts.length}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {pendingPosts.map((post) => (
                      <div key={post.id} className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                        <div className="flex items-center gap-3">
                          <Avatar className="w-10 h-10">
                            <AvatarFallback>{post.author.slice(0, 1)}</AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium text-foreground">{post.author}</p>
                            <p className="text-sm text-muted-foreground truncate max-w-xs">{post.content}</p>
                            <p className="text-xs text-muted-foreground">{post.time} · {post.type}</p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button size="icon" variant="ghost" className="text-success hover:text-success hover:bg-success/10">
                            <Check className="w-4 h-4" />
                          </Button>
                          <Button size="icon" variant="ghost" className="text-destructive hover:text-destructive hover:bg-destructive/10">
                            <X className="w-4 h-4" />
                          </Button>
                          <Button size="icon" variant="ghost">
                            <Eye className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                {/* 最新举报 */}
                <Card className="border-0 shadow-lg">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Shield className="w-5 h-5 text-destructive" />
                      最新举报
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {reports.map((report) => (
                      <div key={report.id} className="flex items-center justify-between p-4 rounded-lg bg-destructive/5">
                        <div>
                          <p className="font-medium text-foreground">
                            {report.reporter} 举报 {report.target}
                          </p>
                          <p className="text-sm text-muted-foreground">原因: {report.reason}</p>
                          <p className="text-xs text-muted-foreground">{report.time}</p>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline">查看详情</Button>
                          <Button size="sm" variant="destructive">处理</Button>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </>
            )}

            {activeTab === 'users' && (
              <Card className="border-0 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>用户管理</span>
                    <div className="relative w-64">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input placeholder="搜索用户..." className="pl-10" />
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {recentUsers.map((user) => (
                      <div key={user.id} className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                        <div className="flex items-center gap-3">
                          <Avatar className="w-10 h-10">
                            <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                              {user.name.slice(0, 1)}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium text-foreground">{user.name}</p>
                            <p className="text-sm text-muted-foreground">{user.department}</p>
                            <p className="text-xs text-muted-foreground">注册时间: {user.joinTime}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge variant={user.status === 'active' ? 'success' : 'secondary'}>
                            {user.status === 'active' ? '活跃' : '不活跃'}
                          </Badge>
                          <Button size="icon" variant="ghost">
                            <UserCog className="w-4 h-4" />
                          </Button>
                          <Button size="icon" variant="ghost" className="text-destructive">
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {(activeTab === 'content' || activeTab === 'reports' || activeTab === 'announcements' || activeTab === 'settings') && (
              <Card className="border-0 shadow-lg">
                <CardContent className="p-12 text-center">
                  <Settings className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">该功能模块正在开发中...</p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
