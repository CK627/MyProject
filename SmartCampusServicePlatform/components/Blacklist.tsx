'use client'

import React, { useState, useEffect } from 'react'
import { 
  Shield,
  Search,
  UserMinus,
  AlertTriangle,
  Clock,
  X,
  Loader2
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'
import { blacklistApi, BlacklistItem as ApiBlacklistItem, getToken } from '@/lib/api'

interface BlockedUser {
  id: number
  userId: number
  name: string
  department: string
  blockedAt: string
  reason: string
}

// 格式化日期
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

export function Blacklist() {
  const [blockedUsers, setBlockedUsers] = useState<BlockedUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  // 加载黑名单
  const loadBlacklist = async () => {
    try {
      setLoading(true)
      const response = await blacklistApi.getBlacklist()
      const users: BlockedUser[] = response.items.map(item => ({
        id: item.id,
        userId: item.blocked_user_id,
        name: item.blocked_user?.name || '未知用户',
        department: '校园用户',
        blockedAt: formatDate(item.created_at),
        reason: item.reason || '无'
      }))
      setBlockedUsers(users)
    } catch (err) {
      console.error('加载黑名单失败:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (getToken()) {
      loadBlacklist()
    } else {
      setLoading(false)
    }
  }, [])

  const filteredUsers = blockedUsers.filter(user =>
    user.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // 移除黑名单
  const handleUnblock = async (userId: number) => {
    try {
      await blacklistApi.removeFromBlacklist(userId)
      setBlockedUsers(blockedUsers.filter(u => u.userId !== userId))
    } catch (err: any) {
      setError(err.message || '移除失败')
    }
  }

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-2xl mx-auto px-4">
        {/* 头部 */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold flex items-center gap-2 text-foreground">
            <Shield className="w-6 h-6 text-primary" />
            黑名单管理
          </h1>
          <p className="text-muted-foreground mt-1">
            被拉黑的用户将无法查看你的动态、向你发送消息
          </p>
        </div>

        {/* 搜索 */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="搜索黑名单用户..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* 提示 */}
        <Card className="border-0 shadow-md bg-warning/10 mb-6">
          <CardContent className="p-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-foreground">黑名单说明</p>
              <p className="text-sm text-muted-foreground">
                将用户加入黑名单后，对方将无法：查看你的校园墙动态、向你发送私信、
                接受你发布的互助任务。解除拉黑后，以上限制将被取消。
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 黑名单列表 */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="text-lg flex items-center justify-between">
              <span>已拉黑用户</span>
              <span className="text-sm font-normal text-muted-foreground">
                共 {blockedUsers.length} 人
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-12">
                <Loader2 className="w-8 h-8 mx-auto text-primary animate-spin mb-4" />
                <p className="text-muted-foreground">加载中...</p>
              </div>
            ) : filteredUsers.length > 0 ? (
              <div className="space-y-3">
                {filteredUsers.map((user) => (
                  <div
                    key={user.id}
                    className="flex items-center justify-between p-4 rounded-lg bg-muted/50"
                  >
                    <div className="flex items-center gap-3">
                      <Avatar className="w-12 h-12">
                        <AvatarFallback className="bg-muted-foreground/20 text-muted-foreground">
                          {user.name.slice(0, 1)}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="font-medium text-foreground">{user.name}</p>
                        <p className="text-sm text-muted-foreground">{user.department}</p>
                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          {user.blockedAt} 拉黑
                          <span className="text-muted-foreground/50">|</span>
                          {user.reason}
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleUnblock(user.userId)}
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                    >
                      <UserMinus className="w-4 h-4 mr-1" />
                      移除
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <Shield className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">
                  {searchQuery ? '没有找到匹配的用户' : '黑名单为空'}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {error && (
          <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-destructive text-destructive-foreground px-4 py-2 rounded-lg shadow-lg z-50">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
