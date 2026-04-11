'use client'

import React, { useState, useEffect } from 'react'
import { 
  Users,
  Search,
  UserPlus,
  MessageCircle,
  MoreHorizontal,
  UserMinus,
  Shield,
  Check,
  X,
  Clock,
  Loader2,
  ArrowLeft,
  FileText
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'
import { friendsApi, usersApi, Friend as ApiFriend, FriendRequest as ApiFriendRequest, User, getToken } from '@/lib/api'

interface Friend {
  id: number
  name: string
  avatar?: string
  department: string
  status: 'online' | 'offline'
  lastActive?: string
  email?: string
  studentId?: string
  bio?: string
  major?: string
  gender?: string
  birthday?: string
  dormitory?: string
  enrollYear?: number
}

interface FriendRequest {
  id: number
  name: string
  avatar?: string
  department: string
  message: string
  time: string
}

// 格式化时间
function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 7) return `${diffDays}天前`
  return date.toLocaleDateString('zh-CN')
}

interface FriendsProps {
  onNavigateToMessages?: (friendId: number, friendName: string) => void
}

export function Friends({ onNavigateToMessages }: FriendsProps = {}) {
  const [friends, setFriends] = useState<Friend[]>([])
  const [requests, setRequests] = useState<FriendRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<'friends' | 'requests' | 'search'>('friends')
  const [searchResults, setSearchResults] = useState<Friend[]>([])
  const [searchKeyword, setSearchKeyword] = useState('')
  const [searching, setSearching] = useState(false)
  const [selectedFriend, setSelectedFriend] = useState<Friend | null>(null)
  const [showDetail, setShowDetail] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // 加载好友列表
  const loadFriends = async () => {
    try {
      setLoading(true)
      const response = await friendsApi.getFriends()
      
      // 获取在线好友列表
      let onlineFriendIds: number[] = []
      try {
        onlineFriendIds = await friendsApi.getOnlineFriends()
      } catch (err) {
        console.error('获取在线状态失败:', err)
      }
      
      const friendList: Friend[] = response.items.map(item => ({
        id: item.friend_id,
        name: item.friend?.name || '未知用户',
        avatar: item.friend?.avatar,
        department: '校园用户', // API暂无院系字段
        status: onlineFriendIds.includes(item.friend_id) ? 'online' as const : 'offline' as const,
        lastActive: formatTime(item.created_at)
      }))
      setFriends(friendList)
    } catch (err) {
      console.error('加载好友失败:', err)
    } finally {
      setLoading(false)
    }
  }

  // 加载好友请求
  const loadRequests = async () => {
    try {
      const response = await friendsApi.getReceivedRequests()
      const requestList: FriendRequest[] = response.items.map(item => ({
        id: item.id,
        name: item.from_user?.name || '未知用户',
        avatar: item.from_user?.avatar,
        department: '校园用户',
        message: item.message || '请求添加您为好友',
        time: formatTime(item.created_at)
      }))
      setRequests(requestList)
    } catch (err) {
      console.error('加载好友请求失败:', err)
    }
  }

  useEffect(() => {
    if (getToken()) {
      loadFriends()
      loadRequests()
    } else {
      setLoading(false)
    }
  }, [activeTab])

  const filteredFriends = friends.filter(friend =>
    friend.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    friend.department.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const onlineFriends = filteredFriends.filter(f => f.status === 'online')
  const offlineFriends = filteredFriends.filter(f => f.status === 'offline')

  // 接受好友请求
  const handleAcceptRequest = async (id: number) => {
    try {
      await friendsApi.acceptRequest(id)
      setRequests(requests.filter(r => r.id !== id))
      loadFriends() // 刷新好友列表
    } catch (err: any) {
      setError(err.message || '接受请求失败')
    }
  }

  // 拒绝好友请求
  const handleRejectRequest = async (id: number) => {
    try {
      await friendsApi.rejectRequest(id)
      setRequests(requests.filter(r => r.id !== id))
    } catch (err: any) {
      setError(err.message || '拒绝请求失败')
    }
  }

  // 删除好友
  const handleRemoveFriend = async (id: number) => {
    try {
      await friendsApi.removeFriend(id)
      setFriends(friends.filter(f => f.id !== id))
    } catch (err: any) {
      setError(err.message || '删除好友失败')
    }
  }

  // 搜索用户
  const handleSearch = async () => {
    if (!searchKeyword.trim()) return
    
    try {
      setSearching(true)
      const users = await usersApi.searchUsers(searchKeyword)
      setSearchResults(users.map(user => ({
        id: user.id,
        name: user.name,
        avatar: user.avatar,
        department: '校园用户',
        status: 'offline' as const
      })))
    } catch (err: any) {
      setError(err.message || '搜索失败')
    } finally {
      setSearching(false)
    }
  }

  // 发送好友请求
  const handleSendRequest = async (userId: number) => {
    try {
      await friendsApi.sendFriendRequest(userId)
      setSearchResults(searchResults.filter(u => u.id !== userId))
      setError('') // 清除错误
      // 可以显示成功提示
    } catch (err: any) {
      setError(err.message || '发送请求失败')
    }
  }

  // 点击好友进入详情页
  const handleViewFriend = async (friend: Friend) => {
    setSelectedFriend(friend)
    setShowDetail(true)
    setLoadingDetail(true)
    
    try {
      // 获取用户详细信息
      const userDetail = await usersApi.getUserDetail(friend.id) as any
      const profile = userDetail.profile || {}
      
      setSelectedFriend({
        ...friend,
        // 保留列表中已获取的在线状态，不覆盖
        email: userDetail.email,
        department: profile.department || friend.department,
        studentId: profile.student_id,
        bio: profile.bio,
        major: profile.major,
        gender: profile.gender,
        birthday: profile.birthday ? String(profile.birthday).split('T')[0] : undefined,
        dormitory: profile.dormitory,
        enrollYear: profile.enroll_year,
      })
    } catch (err) {
      console.error('获取用户详情失败:', err)
    } finally {
      setLoadingDetail(false)
    }
  }

  // 返回列表
  const handleBack = () => {
    setShowDetail(false)
    setSelectedFriend(null)
  }

  // 发送消息
  const handleSendMessage = (friend: Friend) => {
    if (onNavigateToMessages) {
      onNavigateToMessages(friend.id, friend.name)
    }
  }

  // 好友详情页
  if (showDetail && selectedFriend) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/50 pt-20 pb-8 px-4">
        <div className="max-w-4xl mx-auto">
          {/* 返回按钮 */}
          <Button 
            variant="outline" 
            onClick={handleBack}
            className="mb-6 bg-white/80 hover:bg-white"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回好友列表
          </Button>

          {/* 好友资料卡片 */}
          <Card className="mb-6 border-primary/20 bg-white/80 backdrop-blur-sm">
            <CardContent className="p-8">
              <div className="flex flex-col md:flex-row gap-6 items-center md:items-start">
                {/* 头像 */}
                <div className="relative">
                  <Avatar className="w-32 h-32 border-4 border-white shadow-lg">
                    <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground text-4xl">
                      {selectedFriend.name.slice(0, 1)}
                    </AvatarFallback>
                  </Avatar>
                  {selectedFriend.status === 'online' && (
                    <span className="absolute bottom-2 right-2 w-6 h-6 bg-success rounded-full border-4 border-white animate-pulse" />
                  )}
                </div>

                {/* 基本信息 */}
                <div className="flex-1 text-center md:text-left">
                  <h1 className="text-3xl font-bold text-foreground mb-2">{selectedFriend.name}</h1>
                  <div className="flex items-center justify-center md:justify-start gap-2 mb-4">
                    <Badge variant={selectedFriend.status === 'online' ? 'default' : 'secondary'}>
                      {selectedFriend.status === 'online' ? '在线' : '离线'}
                    </Badge>
                    <span className="text-muted-foreground">{selectedFriend.department}</span>
                  </div>
                  {selectedFriend.lastActive && (
                    <p className="text-sm text-muted-foreground mb-4">
                      最后活跃: {selectedFriend.lastActive}
                    </p>
                  )}
                  
                  {/* 操作按钮 */}
                  <div className="flex gap-3 justify-center md:justify-start">
                    <Button variant="gradient" className="gap-2" onClick={() => handleSendMessage(selectedFriend)}>
                      <MessageCircle className="w-4 h-4" />
                      发送消息
                    </Button>
                    <Button variant="outline" className="gap-2 text-destructive hover:bg-destructive/10" onClick={() => {
                      handleRemoveFriend(selectedFriend.id)
                      handleBack()
                    }}>
                      <UserMinus className="w-4 h-4" />
                      删除好友
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 详细信息 */}
          <div className="grid md:grid-cols-2 gap-6">
            <Card className="border-0 shadow-md bg-white/80 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Users className="w-5 h-5 text-primary" />
                  个人信息
                  {loadingDetail && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                  <Shield className="w-5 h-5 text-primary" />
                  <div>
                    <p className="text-sm text-muted-foreground">院系</p>
                    <p className="font-medium">{selectedFriend.department}</p>
                  </div>
                </div>
                {selectedFriend.major && (
                  <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                    <Shield className="w-5 h-5 text-primary" />
                    <div>
                      <p className="text-sm text-muted-foreground">专业</p>
                      <p className="font-medium">{selectedFriend.major}</p>
                    </div>
                  </div>
                )}
                {selectedFriend.enrollYear && (
                  <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                    <Clock className="w-5 h-5 text-primary" />
                    <div>
                      <p className="text-sm text-muted-foreground">年级</p>
                      <p className="font-medium">{selectedFriend.enrollYear}级</p>
                    </div>
                  </div>
                )}
                {selectedFriend.studentId && (
                  <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                    <Users className="w-5 h-5 text-primary" />
                    <div>
                      <p className="text-sm text-muted-foreground">学号</p>
                      <p className="font-medium">{selectedFriend.studentId}</p>
                    </div>
                  </div>
                )}
                {selectedFriend.gender && (
                  <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                    <Users className="w-5 h-5 text-primary" />
                    <div>
                      <p className="text-sm text-muted-foreground">性别</p>
                      <p className="font-medium">{selectedFriend.gender === 'male' ? '男' : selectedFriend.gender === 'female' ? '女' : '其他'}</p>
                    </div>
                  </div>
                )}
                {selectedFriend.birthday && (
                  <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                    <Clock className="w-5 h-5 text-primary" />
                    <div>
                      <p className="text-sm text-muted-foreground">生日</p>
                      <p className="font-medium">{selectedFriend.birthday}</p>
                    </div>
                  </div>
                )}
                {selectedFriend.dormitory && (
                  <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                    <Shield className="w-5 h-5 text-primary" />
                    <div>
                      <p className="text-sm text-muted-foreground">宿舍</p>
                      <p className="font-medium">{selectedFriend.dormitory}</p>
                    </div>
                  </div>
                )}
                {selectedFriend.email && (
                  <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                    <MessageCircle className="w-5 h-5 text-primary" />
                    <div>
                      <p className="text-sm text-muted-foreground">邮箱</p>
                      <p className="font-medium">{selectedFriend.email}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-0 shadow-md bg-white/80 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <MessageCircle className="w-5 h-5 text-primary" />
                  互动记录
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 rounded-lg bg-gradient-to-r from-primary/10 to-transparent">
                  <p className="text-sm text-muted-foreground mb-1">成为好友</p>
                  <p className="font-medium">{selectedFriend.lastActive || '未知'}</p>
                </div>
                <div className="p-4 rounded-lg bg-gradient-to-r from-secondary/10 to-transparent">
                  <p className="text-sm text-muted-foreground mb-1">最近消息</p>
                  <p className="font-medium">暂无消息记录</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 个人简介 */}
          {selectedFriend.bio && (
            <Card className="mt-6 border-0 shadow-md bg-white/80 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary" />
                  个人简介
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground leading-relaxed">{selectedFriend.bio}</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* 头部 */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2 text-foreground">
              <Users className="w-6 h-6 text-primary" />
              好友
            </h1>
            <p className="text-muted-foreground mt-1">
              {friends.length} 位好友 · {onlineFriends.length} 人在线
            </p>
          </div>
          {requests.length > 0 && (
            <Badge variant="destructive" className="gap-1">
              {requests.length} 个好友请求
            </Badge>
          )}
        </div>

        {/* 标签导航 */}
        <div className="flex gap-2 mb-6">
          <Button
            variant={activeTab === 'friends' ? 'default' : 'outline'}
            onClick={() => setActiveTab('friends')}
          >
            我的好友
          </Button>
          <Button
            variant={activeTab === 'requests' ? 'default' : 'outline'}
            onClick={() => setActiveTab('requests')}
            className="relative"
          >
            好友请求
            {requests.length > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-destructive text-destructive-foreground text-xs rounded-full flex items-center justify-center">
                {requests.length}
              </span>
            )}
          </Button>
          <Button
            variant={activeTab === 'search' ? 'default' : 'outline'}
            onClick={() => setActiveTab('search')}
          >
            <UserPlus className="w-4 h-4 mr-1" />
            添加好友
          </Button>
        </div>

        {/* 好友列表 */}
        {activeTab === 'friends' && (
          <div className="space-y-6 animate-fade-in">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="搜索好友..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {loading ? (
              <div className="text-center py-12">
                <Loader2 className="w-8 h-8 mx-auto text-primary animate-spin mb-4" />
                <p className="text-muted-foreground">加载中...</p>
              </div>
            ) : (
              <>
                {/* 在线好友 */}
                {onlineFriends.length > 0 && (
              <div>
                <h2 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                  在线 - {onlineFriends.length}
                </h2>
                <div className="grid gap-3">
                  {onlineFriends.map((friend) => (
                    <Card 
                      key={friend.id} 
                      className="border-0 shadow-md cursor-pointer hover:shadow-lg hover:scale-[1.02] transition-all"
                      onClick={() => handleViewFriend(friend)}
                    >
                      <CardContent className="p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="relative">
                            <Avatar className="w-12 h-12">
                              <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                                {friend.name.slice(0, 1)}
                              </AvatarFallback>
                            </Avatar>
                            <span className="absolute bottom-0 right-0 w-3 h-3 bg-success rounded-full border-2 border-card" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">{friend.name}</p>
                            <p className="text-sm text-muted-foreground">{friend.department}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                          <Button variant="ghost" size="icon" onClick={() => handleSendMessage(friend)}>
                            <MessageCircle className="w-5 h-5" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleRemoveFriend(friend.id)}>
                            <UserMinus className="w-5 h-5 text-destructive" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* 离线好友 */}
            {offlineFriends.length > 0 && (
              <div>
                <h2 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-muted-foreground" />
                  离线 - {offlineFriends.length}
                </h2>
                <div className="grid gap-3">
                  {offlineFriends.map((friend) => (
                    <Card 
                      key={friend.id} 
                      className="border-0 shadow-md opacity-75 cursor-pointer hover:shadow-lg hover:opacity-100 hover:scale-[1.02] transition-all"
                      onClick={() => handleViewFriend(friend)}
                    >
                      <CardContent className="p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Avatar className="w-12 h-12">
                            <AvatarFallback className="bg-muted text-muted-foreground">
                              {friend.name.slice(0, 1)}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium text-foreground">{friend.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {friend.department} · {friend.lastActive}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                          <Button variant="ghost" size="icon" onClick={() => handleSendMessage(friend)}>
                            <MessageCircle className="w-5 h-5" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleRemoveFriend(friend.id)}>
                            <UserMinus className="w-5 h-5 text-destructive" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {filteredFriends.length === 0 && (
              <div className="text-center py-12">
                <Users className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">暂无好友</p>
              </div>
            )}
              </>
            )}
          </div>
        )}

        {/* 好友请求 */}
        {activeTab === 'requests' && (
          <div className="space-y-4 animate-fade-in">
            {requests.length > 0 ? (
              requests.map((request) => (
                <Card key={request.id} className="border-0 shadow-md">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <Avatar className="w-12 h-12">
                        <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                          {request.name.slice(0, 1)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <p className="font-medium text-foreground">{request.name}</p>
                          <span className="text-xs text-muted-foreground">{request.time}</span>
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">{request.department}</p>
                        <p className="text-sm text-foreground bg-muted rounded-lg p-2 mb-3">
                          {request.message}
                        </p>
                        <div className="flex gap-2">
                          <Button size="sm" variant="gradient" onClick={() => handleAcceptRequest(request.id)}>
                            <Check className="w-4 h-4 mr-1" />
                            接受
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => handleRejectRequest(request.id)}>
                            <X className="w-4 h-4 mr-1" />
                            拒绝
                          </Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <div className="text-center py-12">
                <UserPlus className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">暂无好友请求</p>
              </div>
            )}
          </div>
        )}

        {/* 添加好友 */}
        {activeTab === 'search' && (
          <div className="space-y-6 animate-fade-in">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="搜索用户名或学号..."
                  className="pl-10"
                  value={searchKeyword}
                  onChange={(e) => setSearchKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
              </div>
              <Button variant="gradient" onClick={handleSearch} disabled={searching}>
                {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : '搜索'}
              </Button>
            </div>

            {searchResults.length > 0 && (
              <div className="grid gap-3">
                {searchResults.map((user) => (
                  <Card key={user.id} className="border-0 shadow-md">
                    <CardContent className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Avatar className="w-12 h-12">
                          <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                            {user.name.slice(0, 1)}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium text-foreground">{user.name}</p>
                          <p className="text-sm text-muted-foreground">{user.department}</p>
                        </div>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => handleSendRequest(user.id)}>
                        <UserPlus className="w-4 h-4 mr-1" />
                        添加
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-destructive text-destructive-foreground px-4 py-2 rounded-lg shadow-lg z-50">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
