'use client'

import React, { useState, useEffect } from 'react'
import { 
  ArrowLeft, 
  Bell, 
  MessageSquare, 
  Heart, 
  UserPlus,
  ClipboardList,
  Megaphone,
  Check
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface NotificationSettingsProps {
  onNavigate: (page: string) => void
}

interface NotificationPreferences {
  comments: boolean
  likes: boolean
  friendRequests: boolean
  taskUpdates: boolean
  systemAnnouncements: boolean
}

const STORAGE_KEY = 'notification_preferences'

export function NotificationSettings({ onNavigate }: NotificationSettingsProps) {
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    comments: true,
    likes: true,
    friendRequests: true,
    taskUpdates: true,
    systemAnnouncements: true,
  })
  const [saved, setSaved] = useState(false)

  // 加载设置
  useEffect(() => {
    const savedPrefs = localStorage.getItem(STORAGE_KEY)
    if (savedPrefs) {
      try {
        setPreferences(JSON.parse(savedPrefs))
      } catch (e) {
        console.error('Failed to parse notification preferences')
      }
    }
  }, [])

  // 保存设置
  const savePreferences = (newPrefs: NotificationPreferences) => {
    setPreferences(newPrefs)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newPrefs))
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  const togglePreference = (key: keyof NotificationPreferences) => {
    const newPrefs = { ...preferences, [key]: !preferences[key] }
    savePreferences(newPrefs)
  }

  const enableAll = () => {
    const newPrefs: NotificationPreferences = {
      comments: true,
      likes: true,
      friendRequests: true,
      taskUpdates: true,
      systemAnnouncements: true,
    }
    savePreferences(newPrefs)
  }

  const disableAll = () => {
    const newPrefs: NotificationPreferences = {
      comments: false,
      likes: false,
      friendRequests: false,
      taskUpdates: false,
      systemAnnouncements: false,
    }
    savePreferences(newPrefs)
  }

  const notificationItems: { key: keyof NotificationPreferences; icon: React.ReactNode; label: string; desc: string }[] = [
    { key: 'comments', icon: <MessageSquare className="w-5 h-5" />, label: '评论通知', desc: '有人评论你的帖子或任务' },
    { key: 'likes', icon: <Heart className="w-5 h-5" />, label: '点赞通知', desc: '有人点赞你的帖子或评论' },
    { key: 'friendRequests', icon: <UserPlus className="w-5 h-5" />, label: '好友申请', desc: '有人申请添加你为好友' },
    { key: 'taskUpdates', icon: <ClipboardList className="w-5 h-5" />, label: '任务动态', desc: '任务状态变更通知' },
    { key: 'systemAnnouncements', icon: <Megaphone className="w-5 h-5" />, label: '系统公告', desc: '重要的系统公告和通知' },
  ]

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-2xl mx-auto px-4">
        {/* 返回按钮 */}
        <button
          onClick={() => onNavigate('profile')}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground mb-4 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          返回个人中心
        </button>

        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Bell className="w-6 h-6" />
            通知设置
          </h1>
          {saved && (
            <span className="text-sm text-green-500 flex items-center gap-1">
              <Check className="w-4 h-4" /> 已保存
            </span>
          )}
        </div>

        {/* 快捷操作 */}
        <div className="flex gap-3 mb-4">
          <Button variant="outline" size="sm" onClick={enableAll}>
            全部开启
          </Button>
          <Button variant="outline" size="sm" onClick={disableAll}>
            全部关闭
          </Button>
        </div>

        {/* 通知设置列表 */}
        <Card className="border-0 shadow-lg">
          <CardContent className="p-0 divide-y divide-border">
            {notificationItems.map((item) => (
              <div
                key={item.key}
                className="flex items-center justify-between p-4"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                    {item.icon}
                  </div>
                  <div>
                    <p className="font-medium text-foreground">{item.label}</p>
                    <p className="text-sm text-muted-foreground">{item.desc}</p>
                  </div>
                </div>
                {/* Toggle Switch */}
                <button
                  onClick={() => togglePreference(item.key)}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    preferences[item.key] ? 'bg-primary' : 'bg-muted'
                  }`}
                >
                  <span
                    className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                      preferences[item.key] ? 'translate-x-7' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            ))}
          </CardContent>
        </Card>

        <p className="text-sm text-muted-foreground text-center mt-4">
          通知设置仅存储在本地设备
        </p>
      </div>
    </div>
  )
}
