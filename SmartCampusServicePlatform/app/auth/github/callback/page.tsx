'use client'

import React, { useEffect, useState } from 'react'
import { School, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { authApi, setToken } from '@/lib/api'
import { useSearchParams, useRouter } from 'next/navigation'
import config from '@/config'

const USER_STORAGE_KEY = config.frontend.userStorageKey
const USER_EXPIRE_KEY = config.frontend.userExpireKey
const ONE_DAY_MS = config.frontend.sessionExpireTime

function GitHubCallbackContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const code = searchParams.get('code')

  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (!code) {
      setError('GitHub授权失败，未收到授权码')
      return
    }

    const handleCallback = async () => {
      try {
        // 用授权码换取JWT
        const tokenResponse = await authApi.githubCallback(code)
        setToken(tokenResponse.access_token)

        // 获取用户信息
        const user = await authApi.getCurrentUser()

        // 保存用户信息到localStorage（与主页面使用同一格式）
        const userData = {
          name: user.name,
          role: user.role,
          avatar: user.avatar,
        }
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(userData))
        localStorage.setItem(USER_EXPIRE_KEY, String(Date.now() + ONE_DAY_MS))

        setSuccess(true)

        // 检测是否在弹窗中（window.opener 存在说明是弹窗）
        if (window.opener && !window.opener.closed) {
          // 向父窗口发送消息
          window.opener.postMessage({
            type: 'github-oauth-success',
            token: tokenResponse.access_token,
            user: userData
          }, window.location.origin)
          // 关闭弹窗
          setTimeout(() => window.close(), 500)
        } else {
          // 不在弹窗中，跳转到首页
          setTimeout(() => {
            router.push('/')
          }, 1000)
        }
      } catch (err: any) {
        setError(err.message || 'GitHub登录失败，请稍后重试')
      }
    }

    handleCallback()
  }, [code, router])

  if (error) {
    const isPopup = typeof window !== 'undefined' && window.opener && !window.opener.closed
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-primary/5 via-background to-secondary/5">
        <Card className="w-full max-w-md shadow-xl border-0">
          <CardContent className="pt-8 pb-8 text-center">
            <XCircle className="w-16 h-16 text-destructive mx-auto mb-4" />
            <h2 className="text-xl font-bold mb-2">登录失败</h2>
            <p className="text-muted-foreground mb-6">{error}</p>
            {isPopup ? (
              <Button variant="gradient" onClick={() => window.close()}>关闭窗口</Button>
            ) : (
              <a href="/">
                <Button variant="gradient">返回登录</Button>
              </a>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-primary/5 via-background to-secondary/5">
        <Card className="w-full max-w-md shadow-xl border-0">
          <CardContent className="pt-8 pb-8 text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold mb-2">登录成功</h2>
            <p className="text-muted-foreground">正在跳转...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-primary/5 via-background to-secondary/5">
      <Card className="w-full max-w-md shadow-xl border-0">
        <CardContent className="pt-8 pb-8 text-center">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center mb-6 shadow-lg">
            <School className="w-8 h-8 text-primary-foreground" />
          </div>
          <div className="flex flex-col items-center gap-4">
            <div className="w-10 h-10 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
            <p className="text-muted-foreground">正在通过 GitHub 登录...</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default function GitHubCallbackPage() {
  return (
    <React.Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/5 via-background to-secondary/5">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
          <p className="text-muted-foreground">加载中...</p>
        </div>
      </div>
    }>
      <GitHubCallbackContent />
    </React.Suspense>
  )
}
