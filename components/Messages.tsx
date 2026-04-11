'use client'

import React, { useState, useEffect } from 'react'
import { 
  MessageCircle,
  Search,
  Pin,
  BellOff,
  MoreVertical,
  Loader2,
  Trash2
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'
import { messagesApi, Conversation, getToken } from '@/lib/api'
import { wsManager, WebSocketMessage } from '@/lib/websocket'
import { ChatWindow } from './ChatWindow'
import { config } from '@/config'

interface MessagesProps {
  initialFriendId?: number
  initialFriendName?: string
}

export function Messages({ initialFriendId, initialFriendName }: MessagesProps = {}) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)

  useEffect(() => {
    loadConversations()
    
    // 连接WebSocket
    wsManager.connect()
    
    // 监听新消息
    const handleMessage = (message: WebSocketMessage) => {
      if (message.type === 'new_message') {
        // 收到新消息,智能更新会话列表而非完全重载
        if (message.data) {
          const newMsg = message.data
          
          // 从 token 或 localStorage 获取当前用户ID
          let currentUserId: number | null = null
          try {
            const token = getToken()
            if (token) {
              const payload = JSON.parse(atob(token.split('.')[1]))
              currentUserId = parseInt(payload.sub)
            }
          } catch {
            // token解析失败，尝试从localStorage获取
            const userData = localStorage.getItem(config.frontend.userStorageKey)
            if (userData) {
              currentUserId = JSON.parse(userData).id
            }
          }
          
          // 校验当前用户ID是否有效
          if (!currentUserId) {
            console.warn('无法获取当前用户ID，跳过会话更新')
            return
          }
          
          setConversations(prev => {
            const partnerId = newMsg.sender_id === currentUserId 
              ? newMsg.receiver_id 
              : newMsg.sender_id
            
            // 防止创建与自己的会话
            if (partnerId === currentUserId) {
              console.warn('跳过：不能创建与自己的会话')
              return prev
            }
            
            // 查找是否已存在该会话
            const existingIndex = prev.findIndex(conv => conv.user.id === partnerId)
            
            if (existingIndex >= 0) {
              // 更新现有会话
              const updated = [...prev]
              const existingConv = updated[existingIndex]
              
              updated[existingIndex] = {
                ...existingConv,
                last_message: newMsg,
                unread_count: newMsg.receiver_id === currentUserId
                  ? existingConv.unread_count + 1
                  : existingConv.unread_count
              }
              
              // 只有当该会话不在第一位时才移动（置顶）
              if (existingIndex > 0) {
                const [movedConv] = updated.splice(existingIndex, 1)
                return [movedConv, ...updated]
              }
              
              return updated
            } else {
              // 新会话：从消息中提取对话方用户信息，直接创建会话对象
              const partnerInfo = newMsg.sender_id === currentUserId 
                ? newMsg.receiver 
                : newMsg.sender
              
              // 校验对话方信息有效且不是自己
              if (partnerInfo && partnerInfo.id && partnerInfo.id !== currentUserId) {
                const newConversation: Conversation = {
                  user: {
                    id: partnerInfo.id,
                    name: partnerInfo.name || '未知用户',
                    avatar: partnerInfo.avatar,
                    email: '',
                    role: 'student',
                    status: 'active',
                    created_at: new Date().toISOString()
                  } as any,
                  last_message: newMsg,
                  unread_count: newMsg.receiver_id === currentUserId ? 1 : 0
                }
                return [newConversation, ...prev]
              }
              
              // 如果没有有效的对话方信息，则从服务器重新加载
              loadConversations()
              return prev
            }
          })
        }
      }
    }
    
    wsManager.addMessageHandler(handleMessage)
    
    return () => {
      wsManager.removeMessageHandler(handleMessage)
    }
  }, [])

  useEffect(() => {
    // 如果传入了好友ID,自动选择该会话
    if (initialFriendId) {
      if (initialFriendName) {
        // 创建临时会话对象
        setSelectedConversation({
          user: { 
            id: initialFriendId, 
            name: initialFriendName,
            email: '',
            role: 'student',
            status: 'active',
            created_at: new Date().toISOString()
          } as any,
          last_message: undefined,
          unread_count: 0
        })
      } else if (conversations.length > 0) {
        const conv = conversations.find(c => c.user.id === initialFriendId)
        if (conv) {
          setSelectedConversation(conv)
        }
      }
    }
  }, [initialFriendId, initialFriendName, conversations])

  const loadConversations = async () => {
    try {
      setLoading(true)
      
      // 直接从服务器加载
      if (getToken()) {
        const response = await messagesApi.getConversations()
        console.log('会话列表响应:', response)
        setConversations(response.items || [])
      } else {
        console.log('未登录，跳过加载会话')
      }
    } catch (err) {
      console.error('加载会话失败:', err)
    } finally {
      setLoading(false)
    }
  }

  // 删除会话
  const handleDeleteConversation = async (userId: number) => {
    if (!confirm('确定要删除这个会话吗？所有聊天记录将被删除。')) {
      return
    }
    
    try {
      await messagesApi.deleteConversation(userId)
      // 从列表中移除
      setConversations(prev => prev.filter(c => c.user.id !== userId))
      // 如果删除的是当前选中的会话，清空选中
      if (selectedConversation?.user.id === userId) {
        setSelectedConversation(null)
      }
    } catch (err) {
      console.error('删除会话失败:', err)
      alert('删除会话失败')
    }
  }

  const filteredConversations = conversations.filter(conv =>
    conv.user.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const formatTime = (dateStr?: string) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)
    
    if (diffMins < 1) return '刚刚'
    if (diffMins < 60) return `${diffMins}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays === 0) return '今天'
    if (diffDays === 1) return '昨天'
    if (diffDays < 7) return `${diffDays}天前`
    return date.toLocaleDateString('zh-CN')
  }

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2 text-foreground">
              <MessageCircle className="w-6 h-6 text-primary" />
              消息
            </h1>
            <p className="text-muted-foreground mt-1">
              {conversations.length} 个会话
            </p>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* 会话列表 */}
          <div className="md:col-span-1">
            <Card className="border-0 shadow-md">
              <CardContent className="p-4">
                {/* 搜索框 */}
                <div className="relative mb-4">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="搜索会话..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>

                {/* 会话列表 */}
                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                  {loading ? (
                    <div className="text-center py-12">
                      <Loader2 className="w-8 h-8 mx-auto text-primary animate-spin mb-4" />
                      <p className="text-muted-foreground">加载中...</p>
                    </div>
                  ) : filteredConversations.length === 0 ? (
                    <div className="text-center py-12">
                      <MessageCircle className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                      <p className="text-muted-foreground">暂无会话</p>
                    </div>
                  ) : (
                    filteredConversations.map((conv) => (
                      <div
                        key={conv.user.id}
                        className={`group flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-all hover:bg-accent ${
                          selectedConversation?.user.id === conv.user.id ? 'bg-accent' : ''
                        }`}
                        onClick={() => setSelectedConversation(conv)}
                      >
                        <div className="relative">
                          <Avatar className="w-12 h-12 flex-shrink-0">
                            <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                              {conv.user.name.slice(0, 1)}
                            </AvatarFallback>
                          </Avatar>
                          {/* 在线状态指示器 */}
                          {conv.user.online_status === 'online' && (
                            <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-background rounded-full"></span>
                          )}
                          {conv.user.online_status === 'away' && (
                            <span className="absolute bottom-0 right-0 w-3 h-3 bg-yellow-500 border-2 border-background rounded-full"></span>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-foreground truncate">
                                {conv.user.name}
                              </span>
                              {conv.user.online_status === 'online' && (
                                <span className="text-xs text-green-600 dark:text-green-400">在线</span>
                              )}
                              {conv.user.online_status === 'away' && (
                                <span className="text-xs text-yellow-600 dark:text-yellow-400">离开</span>
                              )}
                            </div>
                            <span className="text-xs text-muted-foreground flex-shrink-0">
                              {formatTime(conv.last_message?.created_at)}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <p className="text-sm text-muted-foreground truncate">
                              {conv.last_message?.content || '暂无消息'}
                            </p>
                            <div className="flex items-center gap-1 flex-shrink-0">
                              {conv.unread_count > 0 && (
                                <Badge className="bg-destructive text-destructive-foreground">
                                  {conv.unread_count}
                                </Badge>
                              )}
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6 opacity-0 group-hover:opacity-100 hover:bg-destructive/10"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleDeleteConversation(conv.user.id)
                                }}
                              >
                                <Trash2 className="w-3 h-3 text-destructive" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 聊天窗口 */}
          <div className="md:col-span-2">
            {selectedConversation ? (
              <ChatWindow 
                user={selectedConversation.user} 
                onBack={() => setSelectedConversation(null)}
              />
            ) : (
              <Card className="border-0 shadow-md h-[660px] flex items-center justify-center">
                <div className="text-center">
                  <MessageCircle className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                  <p className="text-lg font-medium text-foreground">选择一个会话开始聊天</p>
                  <p className="text-sm text-muted-foreground mt-2">从左侧列表选择好友</p>
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
