'use client'

import React, { useState, useEffect } from 'react'
import { Eye, EyeOff, Mail, Lock, User, Phone, ArrowRight, School, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { authApi, setToken } from '@/lib/api'

interface LoginPageProps {
  onLogin: (user: { name: string; role: string; avatar?: string }) => void
  onNavigate: (page: string) => void
}

export function LoginPage({ onLogin, onNavigate }: LoginPageProps) {
  const [isLogin, setIsLogin] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    phone: '',
    confirmPassword: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 忘记密码状态
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotLoading, setForgotLoading] = useState(false)
  const [forgotMessage, setForgotMessage] = useState('')
  const [forgotError, setForgotError] = useState('')

  // 监听 GitHub OAuth 弹窗消息
  useEffect(() => {
    const handleMessage = async (event: MessageEvent) => {
      // 验证消息来源
      if (event.origin !== window.location.origin) return
      if (event.data?.type !== 'github-oauth-success') return

      const { token, user } = event.data
      if (token && user) {
        setToken(token)
        onLogin({
          name: user.name,
          role: user.role,
          avatar: user.avatar
        })
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [onLogin])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    
    try {
      if (isLogin) {
        // 登录
        const tokenResponse = await authApi.login({
          username: formData.email,
          password: formData.password
        })
        
        // 保存token
        setToken(tokenResponse.access_token)
        
        // 获取用户信息
        const user = await authApi.getCurrentUser()
        
        onLogin({
          name: user.name,
          role: user.role,
          avatar: user.avatar
        })
      } else {
        // 注册
        if (formData.password !== formData.confirmPassword) {
          setError('两次密码输入不一致')
          setLoading(false)
          return
        }
        
        await authApi.register({
          email: formData.email,
          password: formData.password,
          name: formData.name,
          phone: formData.phone
        })
        
        // 注册成功后自动登录
        const tokenResponse = await authApi.login({
          username: formData.email,
          password: formData.password
        })
        
        setToken(tokenResponse.access_token)
        
        const user = await authApi.getCurrentUser()
        
        onLogin({
          name: user.name,
          role: user.role,
          avatar: user.avatar
        })
      }
    } catch (err: any) {
      setError(err.message || '操作失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!forgotEmail) return
    setForgotLoading(true)
    setForgotError('')
    setForgotMessage('')
    try {
      await authApi.forgotPassword(forgotEmail)
      setForgotMessage('如果该邮箱已注册，重置链接已发送到您的邮箱')
    } catch (err: any) {
      setForgotError(err.message || '发送失败，请稍后重试')
    } finally {
      setForgotLoading(false)
    }
  }

  const handleGitHubLogin = () => {
    const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID
    if (!clientId) {
      setError('GitHub登录未配置，请在 .env.local 中设置 NEXT_PUBLIC_GITHUB_CLIENT_ID')
      return
    }
    const redirectUri = encodeURIComponent(window.location.origin + '/auth/github/callback')
    const authUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=user:email`

    // 计算弹窗位置（居中）
    const width = 600
    const height = 700
    const left = window.screenX + (window.outerWidth - width) / 2
    const top = window.screenY + (window.outerHeight - height) / 2

    // 打开弹窗
    window.open(
      authUrl,
      'github-oauth',
      `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes`
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-primary/5 via-background to-secondary/5">
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary/10 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-secondary/10 rounded-full blur-3xl animate-pulse-slow animation-delay-200" />
      </div>

      <Card className="w-full max-w-md relative z-10 shadow-xl border-0">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center mb-4 shadow-lg">
            <School className="w-8 h-8 text-primary-foreground" />
          </div>
          <CardTitle className="text-2xl font-bold">
            {isLogin ? '欢迎回来' : '注册账号'}
          </CardTitle>
          <CardDescription>
            {isLogin ? '登录您的智慧校园账号' : '创建您的智慧校园账号'}
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
                {error}
              </div>
            )}
            
            {!isLogin && (
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input
                  placeholder="姓名"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="pl-10"
                  required
                />
              </div>
            )}
            
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input
                type="email"
                placeholder="邮箱地址"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="pl-10"
                required
              />
            </div>

            {!isLogin && (
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input
                  type="tel"
                  placeholder="手机号码"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="pl-10"
                  required
                />
              </div>
            )}
            
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input
                type={showPassword ? 'text' : 'password'}
                placeholder="密码"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="pl-10 pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>

            {!isLogin && (
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="确认密码"
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                  className="pl-10"
                  required
                />
              </div>
            )}

            {isLogin && (
              <div className="flex items-center justify-between text-sm">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" className="rounded border-border" />
                  <span className="text-muted-foreground">记住我</span>
                </label>
                <button type="button" className="text-primary hover:underline" onClick={() => {
                  setShowForgotPassword(true)
                  setForgotEmail('')
                  setForgotMessage('')
                  setForgotError('')
                }}>
                  忘记密码？
                </button>
              </div>
            )}

            <Button type="submit" variant="gradient" className="w-full" size="lg" disabled={loading}>
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                  处理中...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  {isLogin ? '登录' : '注册'}
                  <ArrowRight className="w-4 h-4" />
                </span>
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <span className="text-muted-foreground text-sm">
              {isLogin ? '还没有账号？' : '已有账号？'}
            </span>
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-primary font-medium ml-1 hover:underline text-sm"
            >
              {isLogin ? '立即注册' : '去登录'}
            </button>
          </div>

          <div className="mt-6 relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">或</span>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-3">
            <Button variant="outline" className="w-full" onClick={handleGitHubLogin}>
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path fill="currentColor" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.164 6.839 9.489.5.092.682-.217.682-.482 0-.237-.009-.866-.013-1.7-2.782.603-3.369-1.342-3.369-1.342-.454-1.155-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.161 22 16.418 22 12c0-5.523-4.477-10-10-10z"/>
              </svg>
              使用 GitHub 登录
            </Button>
          </div>

          {/* 忘记密码面板 */}
          {showForgotPassword && (
            <div className="mt-6 p-4 rounded-lg border border-border bg-muted/30">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium">重置密码</h3>
                <button
                  type="button"
                  onClick={() => setShowForgotPassword(false)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <ArrowLeft className="w-4 h-4" />
                </button>
              </div>
              <form onSubmit={handleForgotPassword} className="space-y-3">
                {forgotError && (
                  <div className="p-2 rounded-lg bg-destructive/10 text-destructive text-sm">
                    {forgotError}
                  </div>
                )}
                {forgotMessage && (
                  <div className="p-2 rounded-lg bg-green-500/10 text-green-600 text-sm">
                    {forgotMessage}
                  </div>
                )}
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    type="email"
                    placeholder="请输入注册邮箱"
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    className="pl-9 h-9 text-sm"
                    required
                  />
                </div>
                <Button type="submit" variant="gradient" className="w-full" size="sm" disabled={forgotLoading}>
                  {forgotLoading ? '发送中...' : '发送重置链接'}
                </Button>
              </form>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
