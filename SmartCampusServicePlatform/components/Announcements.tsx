'use client'

import React, { useState, useEffect } from 'react'
import { 
  Bell,
  Clock,
  Filter,
  Search,
  ChevronRight,
  AlertCircle,
  Info,
  CheckCircle,
  Star,
  Loader2
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { announcementsApi, Announcement as ApiAnnouncement } from '@/lib/api'

interface Announcement {
  id: number
  title: string
  content: string
  date: string
  type: '重要' | '通知' | '活动' | '学术'
  read: boolean
  pinned: boolean
}

// 公告类型映射
const typeMap: Record<string, '重要' | '通知' | '活动' | '学术'> = {
  'important': '重要',
  'notice': '通知',
  'activity': '活动',
  'academic': '学术'
}

// 格式化日期
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

// 转换API公告数据
function convertAnnouncement(apiAnn: ApiAnnouncement): Announcement {
  return {
    id: apiAnn.id,
    title: apiAnn.title,
    content: apiAnn.content,
    date: formatDate(apiAnn.publish_date),
    type: typeMap[apiAnn.type] || '通知',
    read: apiAnn.is_read || false,
    pinned: apiAnn.is_pinned
  }
}

const typeFilters = ['全部', '重要', '通知', '活动', '学术']
const typeFilterMap: Record<string, string> = {
  '重要': 'important',
  '通知': 'notice',
  '活动': 'activity',
  '学术': 'academic'
}

export function Announcements() {
  const [announcements, setAnnouncements] = useState<Announcement[]>([])
  const [loading, setLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState('全部')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedAnnouncement, setSelectedAnnouncement] = useState<Announcement | null>(null)
  const [showDetail, setShowDetail] = useState(false)

  // 加载公告
  const loadAnnouncements = async (type?: string) => {
    try {
      setLoading(true)
      const apiType = type && type !== '全部' ? typeFilterMap[type] : undefined
      const response = await announcementsApi.getAnnouncements(1, 50, apiType)
      setAnnouncements(response.items.map(convertAnnouncement))
    } catch (err) {
      console.error('加载公告失败:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAnnouncements()
  }, [])

  // 切换筛选时重新加载
  const handleFilterChange = (filter: string) => {
    setActiveFilter(filter)
    loadAnnouncements(filter)
  }

  const filteredAnnouncements = announcements.filter(ann => {
    const matchSearch = ann.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                       ann.content.toLowerCase().includes(searchQuery.toLowerCase())
    return matchSearch
  })

  const pinnedAnnouncements = filteredAnnouncements.filter(a => a.pinned)
  const normalAnnouncements = filteredAnnouncements.filter(a => !a.pinned)

  const getTypeIcon = (type: Announcement['type']) => {
    switch (type) {
      case '重要':
        return <AlertCircle className="w-4 h-4" />
      case '通知':
        return <Info className="w-4 h-4" />
      case '活动':
        return <Star className="w-4 h-4" />
      case '学术':
        return <CheckCircle className="w-4 h-4" />
    }
  }

  const getTypeBadgeVariant = (type: Announcement['type']) => {
    switch (type) {
      case '重要':
        return 'destructive'
      case '通知':
        return 'default'
      case '活动':
        return 'warning'
      case '学术':
        return 'secondary'
      default:
        return 'default'
    }
  }

  const handleRead = (id: number) => {
    setAnnouncements(announcements.map(ann => 
      ann.id === id ? { ...ann, read: true } : ann
    ))
    const ann = announcements.find(a => a.id === id)
    if (ann) {
      setSelectedAnnouncement(ann)
      setShowDetail(true)
    }
  }

  const handleBack = () => {
    setShowDetail(false)
  }

  // 如果显示详情页，渲染详情视图
  if (showDetail && selectedAnnouncement) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/50 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          {/* 返回按钮 */}
          <Button 
            variant="ghost" 
            onClick={handleBack}
            className="mb-6 hover:bg-white/80"
          >
            <ChevronRight className="w-4 h-4 mr-2 rotate-180" />
            返回公告列表
          </Button>

          {/* 公告详情卡片 */}
          <Card className="border-0 shadow-lg">
            <CardHeader className="space-y-4 pb-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <Badge variant={getTypeBadgeVariant(selectedAnnouncement.type) as "default" | "destructive" | "secondary" | "outline" | "success" | "warning"} className="gap-1 mb-3">
                    {getTypeIcon(selectedAnnouncement.type)}
                    {selectedAnnouncement.type}
                  </Badge>
                  <h1 className="text-3xl font-bold text-foreground mb-3">
                    {selectedAnnouncement.title}
                  </h1>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Clock className="w-4 h-4" />
                    发布时间：{selectedAnnouncement.date}
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* 分隔线 */}
              <div className="border-t border-border" />
              
              {/* 公告内容 */}
              <div className="prose prose-slate max-w-none">
                <div className="text-foreground leading-relaxed whitespace-pre-wrap text-base">
                  {selectedAnnouncement.content}
                </div>
              </div>

              {/* 底部信息 */}
              <div className="pt-6 border-t border-border">
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Info className="w-4 h-4" />
                    <span>如有疑问，请联系相关部门</span>
                  </div>
                  {selectedAnnouncement.pinned && (
                    <div className="flex items-center gap-1 text-amber-600">
                      <Star className="w-4 h-4 fill-amber-600" />
                      <span>置顶公告</span>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* 头部 */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold flex items-center gap-2 text-foreground">
            <Bell className="w-6 h-6 text-primary" />
            校园公告
          </h1>
          <p className="text-muted-foreground mt-1">及时获取学校最新通知和活动信息</p>
        </div>

        {/* 搜索和筛选 */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="搜索公告..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            {typeFilters.map((type) => (
              <Button
                key={type}
                variant={activeFilter === type ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleFilterChange(type)}
              >
                {type}
              </Button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <Loader2 className="w-8 h-8 mx-auto text-primary animate-spin mb-4" />
            <p className="text-muted-foreground">加载中...</p>
          </div>
        ) : (
        <div className="space-y-4">
          {/* 公告列表 */}
          <div className="space-y-4">
            {/* 置顶公告 */}
            {pinnedAnnouncements.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Star className="w-4 h-4" />
                  置顶公告
                </h2>
                {pinnedAnnouncements.map((ann) => (
                  <Card
                    key={ann.id}
                    className={`border-0 shadow-md cursor-pointer transition-all hover:shadow-lg ${
                      !ann.read ? 'bg-primary/5 border-l-4 border-l-primary' : ''
                    }`}
                    onClick={() => handleRead(ann.id)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant={getTypeBadgeVariant(ann.type) as "default" | "destructive" | "secondary" | "outline" | "success" | "warning"} className="gap-1">
                              {getTypeIcon(ann.type)}
                              {ann.type}
                            </Badge>
                            {!ann.read && (
                              <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                            )}
                          </div>
                          <h3 className="font-medium text-foreground mb-1">{ann.title}</h3>
                          <p className="text-sm text-muted-foreground line-clamp-2">{ann.content}</p>
                          <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                            <Clock className="w-3 h-3" />
                            {ann.date}
                          </div>
                        </div>
                        <ChevronRight className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* 普通公告 */}
            <div className="space-y-3">
              {pinnedAnnouncements.length > 0 && normalAnnouncements.length > 0 && (
                <h2 className="text-sm font-medium text-muted-foreground">全部公告</h2>
              )}
              {normalAnnouncements.map((ann) => (
                <Card
                  key={ann.id}
                  className={`border-0 shadow-md cursor-pointer transition-all hover:shadow-lg ${
                    !ann.read ? 'bg-primary/5 border-l-4 border-l-primary' : ''
                  }`}
                  onClick={() => handleRead(ann.id)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant={getTypeBadgeVariant(ann.type) as "default" | "destructive" | "secondary" | "outline" | "success" | "warning"} className="gap-1">
                            {getTypeIcon(ann.type)}
                            {ann.type}
                          </Badge>
                          {!ann.read && (
                            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                          )}
                        </div>
                        <h3 className="font-medium text-foreground mb-1">{ann.title}</h3>
                        <p className="text-sm text-muted-foreground line-clamp-2">{ann.content}</p>
                        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          {ann.date}
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {filteredAnnouncements.length === 0 && (
              <div className="text-center py-12">
                <Bell className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">暂无相关公告</p>
              </div>
            )}
          </div>
        </div>
        )}
      </div>
    </div>
  )
}
