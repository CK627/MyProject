'use client'

import React, { useState, useEffect } from 'react'
import { Navbar } from '@/components/Navbar'
import { LoginPage } from '@/components/LoginPage'
import { HomePage } from '@/components/HomePage'
import { SchoolIntro } from '@/components/SchoolIntro'
import { CampusWall } from '@/components/CampusWall'
import { MutualHelp } from '@/components/MutualHelp'
import { Announcements } from '@/components/Announcements'
import { Messages } from '@/components/Messages'
import { Friends } from '@/components/Friends'
import { WalletPage } from '@/components/WalletPage'
import { Profile } from '@/components/Profile'
import { Blacklist } from '@/components/Blacklist'
import { AdminPanel } from '@/components/AdminPanel'
import { PostDetail } from '@/components/PostDetail'
import { ReputationRules } from '@/components/ReputationRules'
import { StorageSettings } from '@/components/StorageSettings'
import { SystemSettings } from '@/components/SystemSettings'
import { NotificationSettings } from '@/components/NotificationSettings'
import { getToken, removeToken, authApi } from '@/lib/api'
import { useUserActivity } from '@/lib/useUserActivity'

interface User {
  name: string
  role: string
  avatar?: string
}

import config from '@/config'

// 用户信息存储key
const USER_STORAGE_KEY = config.frontend.userStorageKey
const USER_EXPIRE_KEY = config.frontend.userExpireKey
const PAGE_STORAGE_KEY = config.frontend.pageStorageKey
const ONE_DAY_MS = config.frontend.sessionExpireTime

// 保存当前页面到localStorage
const savePageToStorage = (page: string) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(PAGE_STORAGE_KEY, page)
  }
}

// 从localStorage获取页面
const getPageFromStorage = (): string => {
  if (typeof window === 'undefined') return 'home'
  return localStorage.getItem(PAGE_STORAGE_KEY) || 'home'
}

// 保存用户信息到localStorage（有效期1天）
const saveUserToStorage = (userData: User) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(userData))
    localStorage.setItem(USER_EXPIRE_KEY, String(Date.now() + ONE_DAY_MS))
  }
}

// 从localStorage获取用户信息
const getUserFromStorage = (): User | null => {
  if (typeof window === 'undefined') return null
  
  try {
    const expireTime = localStorage.getItem(USER_EXPIRE_KEY)
    const userData = localStorage.getItem(USER_STORAGE_KEY)
    
    // 检查是否过期
    if (expireTime && Date.now() > Number(expireTime)) {
      clearUserStorage()
      return null
    }
    
    if (userData) {
      return JSON.parse(userData)
    }
  } catch (e) {
    console.error('读取用户信息失败:', e)
  }
  return null
}

// 清除用户信息
const clearUserStorage = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(USER_STORAGE_KEY)
    localStorage.removeItem(USER_EXPIRE_KEY)
  }
}

export default function App() {
  const [currentPage, setCurrentPage] = useState('home')
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedPostId, setSelectedPostId] = useState<number | null>(null)
  const [chatFriendId, setChatFriendId] = useState<number | undefined>(undefined)
  const [chatFriendName, setChatFriendName] = useState<string | undefined>(undefined)

  // 用户活跃状态管理 - 定期发送心跳
  useUserActivity()

  // 页面加载时恢复登录状态和页面状态
  useEffect(() => {
    const protectedPages = ['wall', 'help', 'friends', 'wallet', 'profile', 'blacklist', 'admin', 'storage', 'system-settings', 'notification-settings']
    
    const restoreSession = async () => {
      const token = getToken()
      const savedUser = getUserFromStorage()
      const savedPage = getPageFromStorage()
      
      let hasValidUser = false
      
      if (token && savedUser) {
        // 有token和缓存的用户信息，先快速恢复
        setUser(savedUser)
        hasValidUser = true
        
        // 后台验证token是否仍然有效
        try {
          const freshUser = await authApi.getCurrentUser()
          const userData = {
            name: freshUser.name,
            role: freshUser.role,
            avatar: freshUser.avatar
          }
          setUser(userData)
          saveUserToStorage(userData) // 刷新过期时间
        } catch (e) {
          // token无效，清除登录状态
          console.log('Token已过期，需要重新登录')
          removeToken()
          clearUserStorage()
          setUser(null)
          hasValidUser = false
        }
      } else if (token && !savedUser) {
        // 有token但没有缓存用户信息，尝试获取
        try {
          const freshUser = await authApi.getCurrentUser()
          const userData = {
            name: freshUser.name,
            role: freshUser.role,
            avatar: freshUser.avatar
          }
          setUser(userData)
          saveUserToStorage(userData)
          hasValidUser = true
        } catch (e) {
          removeToken()
          clearUserStorage()
        }
      }
      
      // 恢复页面状态，但需要检查权限
      if (savedPage) {
        if (protectedPages.includes(savedPage) && !hasValidUser) {
          // 保护页面但用户未登录，跳转到首页
          setCurrentPage('home')
          savePageToStorage('home')
        } else {
          setCurrentPage(savedPage)
        }
      }
      
      setIsLoading(false)
    }
    
    restoreSession()
  }, [])

  const handleLogin = (userData: User) => {
    setUser(userData)
    saveUserToStorage(userData)
    setCurrentPage('home')
    savePageToStorage('home')
  }

  const handleLogout = async () => {
    try {
      await authApi.logout() // 调用后端API更新在线状态
    } catch (error) {
      console.error('退出登录失败:', error)
    } finally {
      setUser(null)
      removeToken()
      clearUserStorage()
      setCurrentPage('home')
      savePageToStorage('home')
    }
  }

  const handleNavigate = (page: string, data?: any) => {
    // 需要登录才能访问的页面
    const protectedPages = ['wall', 'help', 'friends', 'messages', 'wallet', 'profile', 'blacklist', 'admin', 'storage', 'system-settings', 'notification-settings']
    
    if (protectedPages.includes(page) && !user) {
      setCurrentPage('login')
      savePageToStorage('login')
      return
    }
    
    // 只有管理员才能访问后台
    if (page === 'admin' && user?.role !== 'admin') {
      return
    }
    
    // 处理帖子详情页
    if (page === 'post-detail' && data?.postId) {
      setSelectedPostId(data.postId)
      setCurrentPage('post-detail')
      savePageToStorage('wall') // 保存为wall,刷新后返回校园墙
      return
    }
    
    // 处理从好友页跳转到消息页
    if (page === 'messages' && data?.friendId && data?.friendName) {
      setChatFriendId(data.friendId)
      setChatFriendName(data.friendName)
      setCurrentPage('messages')
      savePageToStorage('messages')
      return
    }
    
    // 从帖子详情返回时清除postId
    if (page !== 'post-detail') {
      setSelectedPostId(null)
    }
    
    // 切换到其他页面时清除聊天参数
    if (page !== 'messages') {
      setChatFriendId(undefined)
      setChatFriendName(undefined)
    }
    
    setCurrentPage(page)
    savePageToStorage(page)
  }

  const renderPage = () => {
    switch (currentPage) {
      case 'login':
        return <LoginPage onLogin={handleLogin} onNavigate={handleNavigate} />
      case 'home':
        return <HomePage onNavigate={handleNavigate} user={user} />
      case 'school':
        return <SchoolIntro />
      case 'wall':
        return <CampusWall onNavigate={handleNavigate} />
      case 'post-detail':
        return selectedPostId ? (
          <PostDetail 
            postId={selectedPostId} 
            onBack={() => handleNavigate('wall')}
          />
        ) : <CampusWall onNavigate={handleNavigate} />
      case 'help':
        return <MutualHelp />
      case 'announcements':
        return <Announcements />
      case 'messages':
        return <Messages initialFriendId={chatFriendId} initialFriendName={chatFriendName} />
      case 'friends':
        return <Friends onNavigateToMessages={(friendId, friendName) => handleNavigate('messages', { friendId, friendName })} />
      case 'wallet':
        return <WalletPage />
      case 'profile':
        return user ? (
          <Profile 
            user={user} 
            onNavigate={handleNavigate} 
            onLogout={handleLogout}
            onAvatarUpdate={(newAvatar) => {
              const updatedUser = { ...user, avatar: newAvatar }
              setUser(updatedUser)
              saveUserToStorage(updatedUser)
            }}
          />
        ) : null
      case 'system-settings':
        return <SystemSettings onNavigate={handleNavigate} />
      case 'notification-settings':
        return <NotificationSettings onNavigate={handleNavigate} />
      case 'storage':
        return <StorageSettings />
      case 'blacklist':
        return <Blacklist />
      case 'admin':
        return user?.role === 'admin' ? <AdminPanel /> : null
      case 'reputation-rules':
        return <ReputationRules onBack={() => handleNavigate('home')} />
      default:
        return <HomePage onNavigate={handleNavigate} user={user} />
    }
  }

  // 加载中状态
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
          <p className="text-muted-foreground">加载中...</p>
        </div>
      </div>
    )
  }

  // 登录页面不显示导航栏
  if (currentPage === 'login') {
    return renderPage()
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar
        currentPage={currentPage}
        onNavigate={handleNavigate}
        user={user}
        onLogout={handleLogout}
      />
      {renderPage()}
    </div>
  )
}
