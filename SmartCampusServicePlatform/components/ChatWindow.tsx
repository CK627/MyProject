'use client'

import React, { useState, useEffect, useRef } from 'react'
import { 
  Send,
  Paperclip,
  Image as ImageIcon,
  Smile,
  MoreVertical,
  ArrowLeft,
  Loader2,
  Trash2
} from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'
import { messagesApi, Message, User, getToken } from '@/lib/api'
import { wsManager, WebSocketMessage } from '@/lib/websocket'

interface ChatWindowProps {
  user: User
  onBack?: () => void
  onMessageSent?: () => void
}

export function ChatWindow({ user, onBack, onMessageSent }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [inputValue, setInputValue] = useState('')
  const [sending, setSending] = useState(false)
  const [uploadingFile, setUploadingFile] = useState(false)
  const [previewFile, setPreviewFile] = useState<{ url: string; name: string; type: string } | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadMessages()
    
    // 监听WebSocket消息
    const handleMessage = (wsMessage: WebSocketMessage) => {
      if (wsMessage.type === 'new_message' && wsMessage.data) {
        const newMsg = wsMessage.data
        
        // 如果消息是当前聊天对象发来的,添加到消息列表
        if (newMsg.sender_id === user.id || newMsg.receiver_id === user.id) {
          setMessages(prev => {
            // 检查消息是否已存在,避免重复
            if (prev.some(msg => msg.id === newMsg.id)) {
              return prev
            }
            return [...prev, newMsg]
          })
          scrollToBottom()
        }
      }
    }
    
    wsManager.addMessageHandler(handleMessage)
    
    return () => {
      wsManager.removeMessageHandler(handleMessage)
    }
  }, [user.id])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const loadMessages = async () => {
    try {
      setLoading(true)
      const response = await messagesApi.getMessagesWithUser(user.id)
      setMessages(response.items)
    } catch (err) {
      console.error('加载消息失败:', err)
    } finally {
      setLoading(false)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // 清除聊天记录
  const handleClearHistory = async () => {
    if (!confirm('确定要清除所有聊天记录吗？此操作不可恢复。')) {
      return
    }
    
    try {
      await messagesApi.clearChatHistory(user.id)
      setMessages([])
    } catch (err) {
      console.error('清除聊天记录失败:', err)
      alert('清除聊天记录失败')
    }
  }

  const handleSend = async () => {
    if (!inputValue.trim() || sending) return

    try {
      setSending(true)
      const message = await messagesApi.sendMessage(user.id, inputValue.trim())
      
      // 更新消息列表,检查是否已存在
      setMessages(prev => {
        if (prev.some(msg => msg.id === message.id)) {
          return prev
        }
        return [...prev, message]
      })
      
      setInputValue('')
      scrollToBottom()
    } catch (err) {
      console.error('发送消息失败:', err)
      alert('发送失败,请重试')
    } finally {
      setSending(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>, type: 'image' | 'file') => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setUploadingFile(true)
      
      // 上传文件到服务器
      const formData = new FormData()
      formData.append('file', file)
      formData.append('message_id', '0') // 临时ID，实际会在后端处理
      
      const response = await fetch('/api/v1/files/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getToken()}`
        },
        body: formData
      })
      
      if (!response.ok) throw new Error('文件上传失败')
      
      const fileData = await response.json()
      
      // 构造消息内容（存储文件ID和元数据）
      const fileInfo = {
        file_id: fileData.file_id,
        file_hash: fileData.file_hash,
        name: file.name,
        size: fileData.file_size,
        type: file.type
      }
      
      // 发送消息
      const message = await messagesApi.sendMessage(user.id, JSON.stringify(fileInfo), type)
      
      // 更新消息列表,检查是否已存在
      setMessages(prev => {
        if (prev.some(msg => msg.id === message.id)) {
          return prev
        }
        return [...prev, message]
      })
      
      scrollToBottom()
    } catch (err) {
      console.error('文件上传失败:', err)
      alert('文件上传失败,请重试')
    } finally {
      setUploadingFile(false)
      if (e.target) e.target.value = ''
    }
  }

  const handlePreviewFile = async (fileInfo: any) => {
    try {
      const info = typeof fileInfo === 'string' ? JSON.parse(fileInfo) : fileInfo
      
      // 从服务器获取文件URL
      const url = `/api/v1/files/${info.file_id}`
      
      setPreviewFile({
        url,
        name: info.name,
        type: info.type
      })
    } catch (err) {
      console.error('预览文件失败:', err)
    }
  }

  const renderMessageContent = (message: Message) => {
    if (message.message_type === 'image' || message.message_type === 'file') {
      try {
        const fileInfo = JSON.parse(message.content)
        const fileUrl = `/api/v1/files/${fileInfo.file_id}`
        
        if (message.message_type === 'image') {
          return (
            <div className="cursor-pointer" onClick={() => handlePreviewFile(fileInfo)}>
              <img 
                src={fileUrl} 
                alt={fileInfo.name}
                className="max-w-full max-h-48 rounded-lg"
                onError={(e) => {
                  e.currentTarget.style.display = 'none'
                  e.currentTarget.nextElementSibling?.classList.remove('hidden')
                }}
              />
              <div className="hidden text-sm">图片加载失败</div>
            </div>
          )
        } else {
          return (
            <div 
              className="flex items-center gap-2 cursor-pointer hover:opacity-80"
              onClick={() => handlePreviewFile(fileInfo)}
            >
              <Paperclip className="w-4 h-4" />
              <div>
                <p className="text-sm font-medium">{fileInfo.name}</p>
                <p className="text-xs opacity-70">{(fileInfo.size / 1024).toFixed(1)} KB</p>
              </div>
            </div>
          )
        }
      } catch {
        return <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
      }
    }
    
    return <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  const getCurrentUserId = () => {
    // 从token中获取当前用户ID
    const token = getToken()
    if (!token) return null
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      return parseInt(payload.sub)
    } catch {
      return null
    }
  }

  const currentUserId = getCurrentUserId()

  return (
    <Card className="border-0 shadow-md h-[660px] flex flex-col">
      {/* 聊天头部 */}
      <CardHeader className="border-b p-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {onBack && (
              <Button variant="ghost" size="icon" onClick={onBack}>
                <ArrowLeft className="w-5 h-5" />
              </Button>
            )}
            <Avatar className="w-10 h-10">
              <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                {user.name.slice(0, 1)}
              </AvatarFallback>
            </Avatar>
            <div>
              <p className="font-medium text-foreground">{user.name}</p>
              <p className="text-xs text-muted-foreground">在线</p>
            </div>
          </div>
          <Button 
            variant="ghost" 
            size="icon"
            onClick={handleClearHistory}
            title="清除聊天记录"
          >
            <Trash2 className="w-5 h-5 text-muted-foreground hover:text-destructive" />
          </Button>
        </div>
      </CardHeader>

      {/* 消息列表 */}
      <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
        {loading ? (
          <div className="text-center py-12">
            <Loader2 className="w-8 h-8 mx-auto text-primary animate-spin mb-4" />
            <p className="text-muted-foreground">加载中...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">暂无消息，发送第一条消息吧</p>
          </div>
        ) : (
          messages.map((message) => {
            const isMe = message.sender_id === currentUserId
            return (
              <div
                key={message.id}
                className={`flex gap-3 ${isMe ? 'flex-row-reverse' : ''}`}
              >
                <Avatar className="w-8 h-8 flex-shrink-0">
                  <AvatarFallback className={isMe ? 'bg-primary text-primary-foreground' : 'bg-muted'}>
                    {isMe ? '我' : user.name.slice(0, 1)}
                  </AvatarFallback>
                </Avatar>
                <div className={`flex flex-col ${isMe ? 'items-end' : 'items-start'} max-w-[70%]`}>
                  <div
                    className={`px-4 py-2 rounded-2xl ${
                      isMe
                        ? 'bg-primary text-primary-foreground rounded-tr-sm'
                        : 'bg-muted text-foreground rounded-tl-sm'
                    }`}
                  >
                    {renderMessageContent(message)}
                  </div>
                  <span className="text-xs text-muted-foreground mt-1">
                    {formatTime(message.created_at)}
                  </span>
                </div>
              </div>
            )
          })
        )}
        <div ref={messagesEndRef} />
      </CardContent>

      {/* 输入框 */}
      <div className="border-t p-4 flex-shrink-0">
        <input
          ref={imageInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFileSelect(e, 'image')}
        />
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={(e) => handleFileSelect(e, 'file')}
        />
        
        <div className="flex items-center gap-2 mb-3">
          <Button variant="ghost" size="icon" className="flex-shrink-0">
            <Smile className="w-5 h-5" />
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            className="flex-shrink-0"
            onClick={() => imageInputRef.current?.click()}
            disabled={uploadingFile}
          >
            {uploadingFile ? <Loader2 className="w-5 h-5 animate-spin" /> : <ImageIcon className="w-5 h-5" />}
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            className="flex-shrink-0"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingFile}
          >
            <Paperclip className="w-5 h-5" />
          </Button>
        </div>
        <div className="flex items-end gap-2">
          <Input
            placeholder="输入消息..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1 resize-none"
            disabled={sending}
          />
          <Button
            variant="gradient"
            onClick={handleSend}
            disabled={!inputValue.trim() || sending}
            className="flex-shrink-0"
          >
            {sending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Send className="w-4 h-4 mr-1" />
                发送
              </>
            )}
          </Button>
        </div>
      </div>

      {/* 文件预览弹窗 */}
      {previewFile && (
        <div 
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setPreviewFile(null)}
        >
          <div 
            className="bg-background rounded-lg p-6 max-w-4xl max-h-[90vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">{previewFile.name}</h3>
              <Button variant="ghost" size="icon" onClick={() => setPreviewFile(null)}>
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </div>
            
            {previewFile.type.startsWith('image/') ? (
              <img 
                src={previewFile.url} 
                alt={previewFile.name}
                className="max-w-full max-h-[70vh] mx-auto"
              />
            ) : (
              <div className="text-center py-12">
                <Paperclip className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">暂不支持预览此文件类型</p>
                <Button 
                  variant="gradient"
                  onClick={() => {
                    const a = document.createElement('a')
                    a.href = previewFile.url
                    a.download = previewFile.name
                    a.click()
                  }}
                >
                  下载文件
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  )
}
