'use client'

import React, { useState, useEffect } from 'react'
import { 
  User,
  Mail,
  Phone,
  School,
  Calendar,
  Edit,
  Camera,
  Save,
  Shield,
  Settings,
  Bell,
  Lock,
  LogOut,
  Loader2,
  FileText,
  Award
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'
import { usersApi, postsApi, friendsApi, tasksApi, userLikeApi, getToken, removeToken, UserCreditInfo } from '@/lib/api'
import { AvatarUploadDialog } from './AvatarUploadDialog'
import { ProfileEditDialog } from './ProfileEditDialog'
import { ChangePasswordDialog } from './ChangePasswordDialog'
import { ReputationBadge } from './ReputationBadge'

interface ProfileProps {
  user: {
    id?: number
    name: string
    role: string
    avatar?: string
  }
  onNavigate: (page: string) => void
  onLogout: () => void
  onAvatarUpdate?: (newAvatar: string) => void
}

export function Profile({ user, onNavigate, onLogout, onAvatarUpdate }: ProfileProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [currentAvatar, setCurrentAvatar] = useState(user.avatar)
  const [userId, setUserId] = useState<number | undefined>(user.id)
  
  // 对话框状态
  const [showAvatarUpload, setShowAvatarUpload] = useState(false)
  const [showProfileEdit, setShowProfileEdit] = useState(false)
  const [showChangePassword, setShowChangePassword] = useState(false)
  
  const [profile, setProfile] = useState({
    name: user.name,
    email: '',
    phone: '',
    department: '校园用户',
    studentId: '',
    enrollYear: '',
    bio: '',
    // 详细档案
    student_id: '',
    major: '',
    grade: '',
    gender: undefined as 'male' | 'female' | 'other' | undefined,
    birthday: '',
    dormitory: '',
  })

  const [stats, setStats] = useState([
    { label: '发布动态', value: 0 },
    { label: '互助任务', value: 0 },
    { label: '好友数量', value: 0 },
    { label: '获得点赞', value: 0 },
  ])

  // 信誉信息
  const [creditInfo, setCreditInfo] = useState<UserCreditInfo | null>(null)

  // 加载用户信息
  const loadProfile = async () => {
    try {
      setLoading(true)
      const userData = await usersApi.getMyProfile() as any
      setUserId(userData.id)
      setCurrentAvatar(userData.avatar)
      
      // 从用户档案中获取详细信息
      const userProfile = userData.profile || {}
      const enrollYear = userProfile.enroll_year 
        ? `${userProfile.enroll_year}级` 
        : new Date(userData.created_at).getFullYear().toString() + '级'
      
      setProfile({
        name: userData.name,
        email: userData.email,
        phone: userData.phone || '',
        department: userProfile.department || '校园用户',
        studentId: userProfile.student_id || userData.id.toString(),
        enrollYear: enrollYear,
        bio: userProfile.bio || '',
        student_id: userProfile.student_id || '',
        major: userProfile.major || '',
        grade: userProfile.enroll_year ? `${userProfile.enroll_year}级` : '',
        gender: userProfile.gender || undefined,
        birthday: userProfile.birthday ? userProfile.birthday.split('T')[0] : '',
        dormitory: userProfile.dormitory || '',
      })

      // 并行加载统计数据和信誉信息
      try {
        const [postsRes, friendsRes, publishedTasks, acceptedTasks, credit] = await Promise.all([
          postsApi.getMyPosts(1, 1).catch(() => ({ total: 0, items: [] })),
          friendsApi.getFriends(1, 1).catch(() => ({ total: 0, items: [] })),
          tasksApi.getMyPublishedTasks(1, 1).catch(() => ({ total: 0 })),
          tasksApi.getMyAcceptedTasks(1, 1).catch(() => ({ total: 0 })),
          userLikeApi.getUserCredit(userData.id).catch(() => null),
        ])
        
        const taskCount = publishedTasks.total + acceptedTasks.total
        const likeCount = credit?.like_count || 0
        
        setStats([
          { label: '发布动态', value: postsRes.total },
          { label: '互助任务', value: taskCount },
          { label: '好友数量', value: friendsRes.total },
          { label: '获得点赞', value: likeCount },
        ])
        
        if (credit) {
          setCreditInfo(credit)
        }
      } catch (e) {
        // 统计加载失败不影响主要功能
      }
    } catch (err) {
      console.error('加载用户信息失败:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (getToken()) {
      loadProfile()
    } else {
      setLoading(false)
    }
  }, [])

  // 保存用户信息
  const handleSave = async () => {
    try {
      setSaving(true)
      await usersApi.updateMyProfile({
        name: profile.name,
        phone: profile.phone || undefined
      })
      setIsEditing(false)
    } catch (err: any) {
      setError(err.message || '保存失败')
      setTimeout(() => setError(''), 3000)
    } finally {
      setSaving(false)
    }
  }

  // 头像上传成功
  const handleAvatarSuccess = (newAvatarUrl: string) => {
    setCurrentAvatar(newAvatarUrl)
    if (onAvatarUpdate) {
      onAvatarUpdate(newAvatarUrl)
    }
    // 更新localStorage中的用户信息
    try {
      const savedUser = localStorage.getItem('user')
      if (savedUser) {
        const userData = JSON.parse(savedUser)
        userData.avatar = newAvatarUrl
        localStorage.setItem('user', JSON.stringify(userData))
      }
    } catch (e) {}
  }

  // 档案编辑成功
  const handleProfileEditSuccess = () => {
    loadProfile() // 重新加载数据
  }

  // 密码修改成功
  const handlePasswordChangeSuccess = () => {
    // 可以添加成功提示
  }

  // 退出登录
  const handleLogout = () => {
    removeToken()
    onLogout()
  }

  const menuItems = [
    { icon: Bell, label: '消息通知', desc: '管理通知设置', onClick: () => onNavigate('notification-settings') },
    { icon: Shield, label: '黑名单', desc: '管理屏蔽用户', onClick: () => onNavigate('blacklist') },
    { icon: Lock, label: '账号安全', desc: '修改密码、绑定', onClick: () => setShowChangePassword(true) },
    { icon: Settings, label: '系统设置', desc: '个性化设置', onClick: () => onNavigate('system-settings') },
  ]

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-2xl mx-auto px-4">
        {/* 个人信息卡片 */}
        <Card className="border-0 shadow-xl mb-6 overflow-hidden">
          <div className="h-32 bg-gradient-to-r from-primary to-secondary" />
          <CardContent className="relative pt-0 pb-6 px-6">
            <div className="flex flex-col sm:flex-row items-center sm:items-end gap-4 -mt-16">
              <div className="relative">
                <Avatar className="w-32 h-32 border-4 border-card shadow-xl">
                  {currentAvatar ? (
                    <AvatarImage src={currentAvatar} />
                  ) : (
                    <AvatarFallback className="text-4xl bg-gradient-to-br from-primary to-secondary text-primary-foreground">
                      {user.name.slice(0, 1)}
                    </AvatarFallback>
                  )}
                </Avatar>
                <button 
                  className="absolute bottom-2 right-2 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center shadow-lg hover:bg-primary/90 transition-colors"
                  onClick={() => setShowAvatarUpload(true)}
                >
                  <Camera className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 text-center sm:text-left">
                <div className="flex items-center justify-center sm:justify-start gap-2 mb-1">
                  <h1 className="text-2xl font-bold text-foreground">{profile.name}</h1>
                  <Badge variant={user.role === 'admin' ? 'destructive' : 'secondary'}>
                    {user.role === 'admin' ? '管理员' : '学生'}
                  </Badge>
                </div>
                <p className="text-muted-foreground">{profile.department} · {profile.studentId}</p>
                {profile.bio && (
                  <p className="text-sm text-muted-foreground mt-1">{profile.bio}</p>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowProfileEdit(true)}
                >
                  <FileText className="w-4 h-4 mr-1" />
                  详细档案
                </Button>
                <Button
                  variant={isEditing ? 'gradient' : 'outline'}
                  size="sm"
                  onClick={() => {
                    if (isEditing) {
                      handleSave()
                    } else {
                      setIsEditing(true)
                    }
                  }}
                  disabled={saving}
                >
                  {saving ? (
                    <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                  ) : isEditing ? (
                    <>
                      <Save className="w-4 h-4 mr-1" />
                      保存
                    </>
                  ) : (
                    <>
                      <Edit className="w-4 h-4 mr-1" />
                      编辑
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* 统计 */}
            <div className="grid grid-cols-4 gap-4 mt-6 pt-6 border-t border-border">
              {stats.map((stat, index) => (
                <div key={index} className="text-center">
                  <p className="text-2xl font-bold text-foreground">{stat.value}</p>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 信誉信息 */}
        {creditInfo && (
          <Card className="border-0 shadow-lg mb-6">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Award className="w-5 h-5" />
                我的信誉
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ReputationBadge
                creditScore={creditInfo.credit_score}
                likeCount={creditInfo.like_count}
                approvalRate={creditInfo.approval_rate}
              />
            </CardContent>
          </Card>
        )}

        {/* 详细信息 */}
        <Card className="border-0 shadow-lg mb-6">
          <CardHeader>
            <CardTitle className="text-lg">个人信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                  <User className="w-4 h-4" />
                  姓名
                </label>
                {isEditing ? (
                  <Input
                    value={profile.name}
                    onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                  />
                ) : (
                  <p className="font-medium text-foreground">{profile.name}</p>
                )}
              </div>
              <div>
                <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                  <Mail className="w-4 h-4" />
                  邮箱
                </label>
                <p className="font-medium text-foreground">{profile.email}</p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                  <Phone className="w-4 h-4" />
                  手机
                </label>
                {isEditing ? (
                  <Input
                    value={profile.phone}
                    onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                    placeholder="请输入手机号"
                  />
                ) : (
                  <p className="font-medium text-foreground">{profile.phone || '未设置'}</p>
                )}
              </div>
              <div>
                <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                  <School className="w-4 h-4" />
                  学院
                </label>
                <p className="font-medium text-foreground">{profile.department}</p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                  <Calendar className="w-4 h-4" />
                  入学年份
                </label>
                <p className="font-medium text-foreground">{profile.enrollYear}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 功能菜单 */}
        <Card className="border-0 shadow-lg">
          <CardContent className="p-2">
            {menuItems.map((item, index) => {
              const Icon = item.icon
              return (
                <button
                  key={index}
                  className="w-full flex items-center gap-4 p-4 rounded-lg hover:bg-muted transition-colors"
                  onClick={item.onClick}
                >
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-primary" />
                  </div>
                  <div className="flex-1 text-left">
                    <p className="font-medium text-foreground">{item.label}</p>
                    <p className="text-sm text-muted-foreground">{item.desc}</p>
                  </div>
                </button>
              )
            })}
            <button
              className="w-full flex items-center gap-4 p-4 rounded-lg hover:bg-destructive/10 transition-colors text-destructive"
              onClick={handleLogout}
            >
              <div className="w-10 h-10 rounded-lg bg-destructive/10 flex items-center justify-center">
                <LogOut className="w-5 h-5" />
              </div>
              <div className="flex-1 text-left">
                <p className="font-medium">退出登录</p>
                <p className="text-sm opacity-70">退出当前账号</p>
              </div>
            </button>
          </CardContent>
        </Card>

        {error && (
          <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-destructive text-destructive-foreground px-4 py-2 rounded-lg shadow-lg z-50">
            {error}
          </div>
        )}
      </div>

      {/* 对话框 */}
      <AvatarUploadDialog
        isOpen={showAvatarUpload}
        onClose={() => setShowAvatarUpload(false)}
        onSuccess={handleAvatarSuccess}
        currentAvatar={currentAvatar}
      />

      <ProfileEditDialog
        isOpen={showProfileEdit}
        onClose={() => setShowProfileEdit(false)}
        onSuccess={handleProfileEditSuccess}
        initialData={{
          student_id: profile.student_id,
          department: profile.department !== '校园用户' ? profile.department : '',
          major: profile.major,
          grade: profile.grade,
          gender: profile.gender,
          birthday: profile.birthday,
          bio: profile.bio,
          dormitory: profile.dormitory,
        }}
      />

      <ChangePasswordDialog
        isOpen={showChangePassword}
        onClose={() => setShowChangePassword(false)}
        onSuccess={handlePasswordChangeSuccess}
      />
    </div>
  )
}
