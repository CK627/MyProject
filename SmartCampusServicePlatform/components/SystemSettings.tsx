'use client'

import React, { useState, useEffect } from 'react'
import { 
  ArrowLeft, 
  Sun, 
  Moon, 
  Monitor, 
  Type, 
  Trash2,
  Check,
  Palette
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface SystemSettingsProps {
  onNavigate: (page: string) => void
}

type ThemeMode = 'light' | 'dark' | 'system'
type FontSize = 'small' | 'medium' | 'large'

export function SystemSettings({ onNavigate }: SystemSettingsProps) {
  const [theme, setTheme] = useState<ThemeMode>('system')
  const [fontSize, setFontSize] = useState<FontSize>('medium')
  const [cacheCleared, setCacheCleared] = useState(false)

  // 加载设置
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as ThemeMode
    const savedFontSize = localStorage.getItem('fontSize') as FontSize
    
    if (savedTheme) setTheme(savedTheme)
    if (savedFontSize) setFontSize(savedFontSize)
  }, [])

  // 应用主题
  useEffect(() => {
    const root = document.documentElement
    
    if (theme === 'dark') {
      root.classList.add('dark')
    } else if (theme === 'light') {
      root.classList.remove('dark')
    } else {
      // 跟随系统
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        root.classList.add('dark')
      } else {
        root.classList.remove('dark')
      }
    }
    
    localStorage.setItem('theme', theme)
  }, [theme])

  // 应用字体大小
  useEffect(() => {
    const root = document.documentElement
    
    root.classList.remove('text-sm', 'text-base', 'text-lg')
    
    if (fontSize === 'small') {
      root.style.fontSize = '14px'
    } else if (fontSize === 'large') {
      root.style.fontSize = '18px'
    } else {
      root.style.fontSize = '16px'
    }
    
    localStorage.setItem('fontSize', fontSize)
  }, [fontSize])

  // 清理缓存
  const handleClearCache = () => {
    // 保留登录信息
    const token = localStorage.getItem('access_token')
    const user = localStorage.getItem('user')
    const theme = localStorage.getItem('theme')
    const fontSize = localStorage.getItem('fontSize')
    
    localStorage.clear()
    
    // 恢复必要信息
    if (token) localStorage.setItem('access_token', token)
    if (user) localStorage.setItem('user', user)
    if (theme) localStorage.setItem('theme', theme)
    if (fontSize) localStorage.setItem('fontSize', fontSize)
    
    setCacheCleared(true)
    setTimeout(() => setCacheCleared(false), 2000)
  }

  const themeOptions: { value: ThemeMode; label: string; icon: React.ReactNode }[] = [
    { value: 'light', label: '浅色', icon: <Sun className="w-5 h-5" /> },
    { value: 'dark', label: '深色', icon: <Moon className="w-5 h-5" /> },
    { value: 'system', label: '跟随系统', icon: <Monitor className="w-5 h-5" /> },
  ]

  const fontSizeOptions: { value: FontSize; label: string; size: string }[] = [
    { value: 'small', label: '小', size: 'text-sm' },
    { value: 'medium', label: '中', size: 'text-base' },
    { value: 'large', label: '大', size: 'text-lg' },
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

        <h1 className="text-2xl font-bold text-foreground mb-6">系统设置</h1>

        {/* 主题设置 */}
        <Card className="border-0 shadow-lg mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Palette className="w-5 h-5" />
              主题模式
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              {themeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setTheme(option.value)}
                  className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                    theme === option.value
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  <div className={theme === option.value ? 'text-primary' : 'text-muted-foreground'}>
                    {option.icon}
                  </div>
                  <span className={`text-sm ${theme === option.value ? 'text-primary font-medium' : 'text-muted-foreground'}`}>
                    {option.label}
                  </span>
                  {theme === option.value && (
                    <Check className="w-4 h-4 text-primary" />
                  )}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 字体大小 */}
        <Card className="border-0 shadow-lg mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Type className="w-5 h-5" />
              字体大小
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              {fontSizeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setFontSize(option.value)}
                  className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                    fontSize === option.value
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  <span className={`${option.size} ${fontSize === option.value ? 'text-primary font-medium' : 'text-muted-foreground'}`}>
                    Aa
                  </span>
                  <span className={`text-sm ${fontSize === option.value ? 'text-primary font-medium' : 'text-muted-foreground'}`}>
                    {option.label}
                  </span>
                  {fontSize === option.value && (
                    <Check className="w-4 h-4 text-primary" />
                  )}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 数据管理 */}
        <Card className="border-0 shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Trash2 className="w-5 h-5" />
              数据管理
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-foreground">清理本地缓存</p>
                <p className="text-sm text-muted-foreground">清除本地存储的临时数据（不影响登录状态）</p>
              </div>
              <Button
                variant="outline"
                onClick={handleClearCache}
                disabled={cacheCleared}
              >
                {cacheCleared ? (
                  <>
                    <Check className="w-4 h-4 mr-2" />
                    已清理
                  </>
                ) : (
                  '清理'
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
