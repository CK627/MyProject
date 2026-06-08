'use client'

import React, { useState } from 'react'
import { 
  Home, 
  School, 
  Users, 
  MessageSquare, 
  Bell, 
  Heart, 
  Wallet, 
  Settings,
  Menu,
  X,
  LogOut,
  User,
  Shield,
  ChevronDown,
  MessageCircle,
  Database
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'

interface NavbarProps {
  currentPage: string
  onNavigate: (page: string) => void
  user: {
    name: string
    avatar?: string
    role: string
  } | null
  onLogout: () => void
}

const navItems = [
  { id: 'home', label: '首页', icon: Home },
  { id: 'school', label: '学校介绍', icon: School },
  { id: 'help', label: '互帮互助', icon: Heart },
  { id: 'wall', label: '校园墙', icon: MessageSquare },
  { id: 'announcements', label: '公告', icon: Bell },
  { id: 'messages', label: '消息', icon: MessageCircle },
  { id: 'friends', label: '好友', icon: Users },
  { id: 'wallet', label: '钱包', icon: Wallet },
]

export function Navbar({ currentPage, onNavigate, user, onLogout }: NavbarProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => onNavigate('home')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
              <School className="w-6 h-6 text-primary-foreground" />
            </div>
            <span className="font-bold text-xl text-gradient hidden sm:block">智慧校园</span>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                    currentPage === item.id
                      ? "bg-primary text-primary-foreground shadow-md"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              )
            })}
          </div>

          {/* User Menu */}
          <div className="flex items-center gap-4">
            {user ? (
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 p-2 rounded-lg hover:bg-muted transition-colors"
                >
                  <Avatar className="w-8 h-8">
                    {user.avatar ? (
                      <AvatarImage src={user.avatar} alt={user.name} />
                    ) : (
                      <AvatarFallback>{user.name.slice(0, 2)}</AvatarFallback>
                    )}
                  </Avatar>
                  <span className="hidden md:block text-sm font-medium">{user.name}</span>
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-card rounded-xl shadow-xl border py-2 animate-scale-in">
                    <button
                      onClick={() => { onNavigate('profile'); setUserMenuOpen(false) }}
                      className="w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-muted transition-colors"
                    >
                      <User className="w-4 h-4" />
                      个人中心
                    </button>
                    <button
                      onClick={() => { onNavigate('storage'); setUserMenuOpen(false) }}
                      className="w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-muted transition-colors"
                    >
                      <Database className="w-4 h-4" />
                      存储管理
                    </button>
                    <button
                      onClick={() => { onNavigate('blacklist'); setUserMenuOpen(false) }}
                      className="w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-muted transition-colors"
                    >
                      <Shield className="w-4 h-4" />
                      黑名单
                    </button>
                    {user.role === 'admin' && (
                      <button
                        onClick={() => { onNavigate('admin'); setUserMenuOpen(false) }}
                        className="w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-muted transition-colors"
                      >
                        <Settings className="w-4 h-4" />
                        后台管理
                      </button>
                    )}
                    <hr className="my-2 border-border" />
                    <button
                      onClick={onLogout}
                      className="w-full flex items-center gap-3 px-4 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      退出登录
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Button variant="gradient" onClick={() => onNavigate('login')}>
                登录
              </Button>
            )}

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg hover:bg-muted"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="lg:hidden py-4 border-t border-border animate-slide-up">
            <div className="grid grid-cols-2 gap-2">
              {navItems.map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.id}
                    onClick={() => { onNavigate(item.id); setMobileMenuOpen(false) }}
                    className={cn(
                      "flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-medium transition-all",
                      currentPage === item.id
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-muted"
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}
