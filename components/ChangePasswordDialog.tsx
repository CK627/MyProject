'use client'

import React, { useState } from 'react'
import { X, Loader2, Eye, EyeOff, Lock, Check } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { authApi } from '@/lib/api'

interface ChangePasswordDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function ChangePasswordDialog({ isOpen, onClose, onSuccess }: ChangePasswordDialogProps) {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showOldPassword, setShowOldPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  // 密码强度检测
  const getPasswordStrength = (password: string): { level: number; label: string; color: string } => {
    if (!password) return { level: 0, label: '', color: '' }
    
    let score = 0
    if (password.length >= 6) score++
    if (password.length >= 8) score++
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++
    if (/\d/.test(password)) score++
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++
    
    if (score <= 2) return { level: 1, label: '弱', color: 'bg-red-500' }
    if (score <= 3) return { level: 2, label: '中', color: 'bg-yellow-500' }
    return { level: 3, label: '强', color: 'bg-green-500' }
  }

  const passwordStrength = getPasswordStrength(newPassword)

  const handleSubmit = async () => {
    // 验证
    if (!oldPassword) {
      setError('请输入当前密码')
      return
    }
    if (newPassword.length < 6) {
      setError('新密码至少需要6个字符')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    try {
      setSaving(true)
      setError('')
      
      await authApi.changePassword(oldPassword, newPassword)
      
      setSuccessMsg('密码修改成功')
      setTimeout(() => {
        onSuccess()
        handleClose()
      }, 1500)
    } catch (err: any) {
      setError(err.message || '密码修改失败')
    } finally {
      setSaving(false)
    }
  }

  const handleClose = () => {
    setOldPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setError('')
    setSuccessMsg('')
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={handleClose} />
      <Card className="relative z-10 w-full max-w-md mx-4 border-0 shadow-2xl">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Lock className="w-5 h-5" />
            修改密码
          </CardTitle>
          <button
            onClick={handleClose}
            className="p-1 rounded-full hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 当前密码 */}
          <div>
            <label className="text-sm text-muted-foreground mb-1 block">
              当前密码
            </label>
            <div className="relative">
              <Input
                type={showOldPassword ? 'text' : 'password'}
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                placeholder="请输入当前密码"
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowOldPassword(!showOldPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showOldPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* 新密码 */}
          <div>
            <label className="text-sm text-muted-foreground mb-1 block">
              新密码
            </label>
            <div className="relative">
              <Input
                type={showNewPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="请输入新密码 (至少6位)"
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowNewPassword(!showNewPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {/* 密码强度指示器 */}
            {newPassword && (
              <div className="mt-2">
                <div className="flex gap-1 mb-1">
                  <div className={`h-1 flex-1 rounded ${passwordStrength.level >= 1 ? passwordStrength.color : 'bg-muted'}`} />
                  <div className={`h-1 flex-1 rounded ${passwordStrength.level >= 2 ? passwordStrength.color : 'bg-muted'}`} />
                  <div className={`h-1 flex-1 rounded ${passwordStrength.level >= 3 ? passwordStrength.color : 'bg-muted'}`} />
                </div>
                <p className="text-xs text-muted-foreground">
                  密码强度: <span className={passwordStrength.level >= 3 ? 'text-green-500' : passwordStrength.level >= 2 ? 'text-yellow-500' : 'text-red-500'}>{passwordStrength.label}</span>
                </p>
              </div>
            )}
          </div>

          {/* 确认密码 */}
          <div>
            <label className="text-sm text-muted-foreground mb-1 block">
              确认新密码
            </label>
            <div className="relative">
              <Input
                type={showConfirmPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="请再次输入新密码"
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {confirmPassword && newPassword && (
              <p className={`text-xs mt-1 ${confirmPassword === newPassword ? 'text-green-500' : 'text-red-500'}`}>
                {confirmPassword === newPassword ? (
                  <span className="flex items-center gap-1">
                    <Check className="w-3 h-3" /> 密码一致
                  </span>
                ) : (
                  '密码不一致'
                )}
              </p>
            )}
          </div>

          {/* 错误/成功提示 */}
          {error && (
            <p className="text-sm text-destructive text-center">{error}</p>
          )}
          {successMsg && (
            <p className="text-sm text-green-500 text-center flex items-center justify-center gap-1">
              <Check className="w-4 h-4" /> {successMsg}
            </p>
          )}

          {/* 操作按钮 */}
          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={handleClose}
            >
              取消
            </Button>
            <Button
              variant="gradient"
              className="flex-1"
              onClick={handleSubmit}
              disabled={saving || !!successMsg}
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  修改中...
                </>
              ) : (
                '确认修改'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
