'use client'

import React, { useState, useEffect } from 'react'
import { X, Loader2, User, School, BookOpen, Calendar, MapPin } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { usersApi, UserProfileUpdate } from '@/lib/api'

interface ProfileEditDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  initialData: {
    student_id?: string
    department?: string
    major?: string
    grade?: string
    gender?: 'male' | 'female' | 'other'
    birthday?: string
    bio?: string
    dormitory?: string
  }
}

export function ProfileEditDialog({ isOpen, onClose, onSuccess, initialData }: ProfileEditDialogProps) {
  const [formData, setFormData] = useState<UserProfileUpdate>({
    student_id: initialData.student_id || '',
    department: initialData.department || '',
    major: initialData.major || '',
    grade: initialData.grade || '',
    gender: initialData.gender || undefined,
    birthday: initialData.birthday || '',
    bio: initialData.bio || '',
    dormitory: initialData.dormitory || '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // 当对话框打开或initialData变化时，更新表单数据
  useEffect(() => {
    if (isOpen) {
      setFormData({
        student_id: initialData.student_id || '',
        department: initialData.department || '',
        major: initialData.major || '',
        grade: initialData.grade || '',
        gender: initialData.gender || undefined,
        birthday: initialData.birthday || '',
        bio: initialData.bio || '',
        dormitory: initialData.dormitory || '',
      })
      setError('')
    }
  }, [isOpen, initialData])

  const handleSubmit = async () => {
    try {
      setSaving(true)
      setError('')
      
      // 过滤空值，只发送有值的字段
      const dataToSubmit: UserProfileUpdate = {}
      if (formData.student_id?.trim()) dataToSubmit.student_id = formData.student_id.trim()
      if (formData.department?.trim()) dataToSubmit.department = formData.department.trim()
      if (formData.major?.trim()) dataToSubmit.major = formData.major.trim()
      if (formData.grade?.trim()) dataToSubmit.grade = formData.grade.trim()
      if (formData.gender) dataToSubmit.gender = formData.gender
      if (formData.birthday?.trim()) dataToSubmit.birthday = formData.birthday.trim()
      if (formData.bio?.trim()) dataToSubmit.bio = formData.bio.trim()
      if (formData.dormitory?.trim()) dataToSubmit.dormitory = formData.dormitory.trim()
      
      // 检查是否有要更新的数据
      if (Object.keys(dataToSubmit).length === 0) {
        onSuccess()
        onClose()
        return
      }
      
      await usersApi.updateMyDetailProfile(dataToSubmit)
      onSuccess()
      onClose()
    } catch (err: any) {
      setError(err.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto py-8">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <Card className="relative z-10 w-full max-w-lg mx-4 border-0 shadow-2xl">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-lg">编辑详细档案</CardTitle>
          <button
            onClick={onClose}
            className="p-1 rounded-full hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* 学号 */}
            <div>
              <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                <User className="w-4 h-4" />
                学号
              </label>
              <Input
                value={formData.student_id}
                onChange={(e) => setFormData({ ...formData, student_id: e.target.value })}
                placeholder="请输入学号"
              />
            </div>

            {/* 院系 */}
            <div>
              <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                <School className="w-4 h-4" />
                院系
              </label>
              <Input
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                placeholder="请输入院系"
              />
            </div>

            {/* 专业 */}
            <div>
              <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                <BookOpen className="w-4 h-4" />
                专业
              </label>
              <Input
                value={formData.major}
                onChange={(e) => setFormData({ ...formData, major: e.target.value })}
                placeholder="请输入专业"
              />
            </div>

            {/* 年级 */}
            <div>
              <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                <Calendar className="w-4 h-4" />
                年级
              </label>
              <Input
                value={formData.grade}
                onChange={(e) => setFormData({ ...formData, grade: e.target.value })}
                placeholder="如: 2024级"
              />
            </div>

            {/* 性别 */}
            <div>
              <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                性别
              </label>
              <select
                value={formData.gender || ''}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value as any || undefined })}
                className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">请选择</option>
                <option value="male">男</option>
                <option value="female">女</option>
                <option value="other">其他</option>
              </select>
            </div>

            {/* 生日 */}
            <div>
              <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                <Calendar className="w-4 h-4" />
                生日
              </label>
              <Input
                type="date"
                value={formData.birthday}
                onChange={(e) => setFormData({ ...formData, birthday: e.target.value })}
              />
            </div>

            {/* 宿舍 */}
            <div className="sm:col-span-2">
              <label className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
                <MapPin className="w-4 h-4" />
                宿舍
              </label>
              <Input
                value={formData.dormitory}
                onChange={(e) => setFormData({ ...formData, dormitory: e.target.value })}
                placeholder="如: 学生公寓1栋101室"
              />
            </div>
          </div>

          {/* 个人简介 */}
          <div>
            <label className="text-sm text-muted-foreground mb-1 block">
              个人简介
            </label>
            <textarea
              value={formData.bio}
              onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
              placeholder="介绍一下自己吧..."
              maxLength={500}
              className="w-full h-24 px-3 py-2 rounded-md border border-input bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <p className="text-xs text-muted-foreground text-right">
              {formData.bio?.length || 0}/500
            </p>
          </div>

          {/* 错误提示 */}
          {error && (
            <p className="text-sm text-destructive text-center">{error}</p>
          )}

          {/* 操作按钮 */}
          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={onClose}
            >
              取消
            </Button>
            <Button
              variant="gradient"
              className="flex-1"
              onClick={handleSubmit}
              disabled={saving}
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  保存中...
                </>
              ) : (
                '保存'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
