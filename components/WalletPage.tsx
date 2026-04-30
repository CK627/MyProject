'use client'

import React, { useState, useEffect } from 'react'
import { 
  Wallet,
  ArrowUpRight,
  ArrowDownLeft,
  CreditCard,
  History,
  Plus,
  Send,
  QrCode,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Loader2,
  X
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { walletApi, usersApi, Wallet as ApiWallet, Transaction as ApiTransaction, getToken } from '@/lib/api'

interface Transaction {
  id: number
  type: 'income' | 'expense' | 'transfer'
  title: string
  amount: number
  date: string
  status: 'completed' | 'pending'
  icon: string
}

// 交易类型图标映射
const typeIconMap: Record<string, string> = {
  'recharge': '💳',
  'task_reward': '💰',
  'task_payment': '📋',
  'transfer_in': '📥',
  'transfer_out': '📤',
  'withdraw': '🏦'
}

// 格式化时间
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffDays === 0) {
    return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  }
  if (diffDays === 1) return '昨天'
  if (diffDays <= 7) return `${diffDays}天前`
  return date.toLocaleDateString('zh-CN')
}

// 转换API交易数据
function convertTransaction(apiTx: ApiTransaction): Transaction {
  const isIncome = apiTx.amount > 0
  return {
    id: apiTx.id,
    type: isIncome ? 'income' : 'expense',
    title: apiTx.description || (isIncome ? '收入' : '支出'),
    amount: apiTx.amount,
    date: formatDate(apiTx.created_at),
    status: apiTx.status === 'completed' ? 'completed' : 'pending',
    icon: typeIconMap[apiTx.type] || (isIncome ? '💰' : '💸')
  }
}

const quickActions = [
  { icon: Plus, label: '充值', color: 'from-green-500 to-emerald-500' },
  { icon: Send, label: '转账', color: 'from-blue-500 to-cyan-500' },
  { icon: QrCode, label: '收款', color: 'from-purple-500 to-violet-500' },
  { icon: History, label: '账单', color: 'from-orange-500 to-amber-500' },
]

export function WalletPage() {
  const [wallet, setWallet] = useState<ApiWallet | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showRecharge, setShowRecharge] = useState(false)
  const [showTransfer, setShowTransfer] = useState(false)
  const [showAllTransactions, setShowAllTransactions] = useState(false)
  const [allTransactions, setAllTransactions] = useState<Transaction[]>([])
  const [allTxLoading, setAllTxLoading] = useState(false)
  const [rechargeAmount, setRechargeAmount] = useState('')
  const [transferData, setTransferData] = useState({ to: '', amount: '' })
  const [submitting, setSubmitting] = useState(false)

  // 加载钱包信息
  const loadWallet = async () => {
    try {
      setLoading(true)
      const walletData = await walletApi.getWallet()
      setWallet(walletData)
      
      const txResponse = await walletApi.getTransactions(1, 20)
      setTransactions(txResponse.items.map(convertTransaction))
    } catch (err) {
      console.error('加载钱包失败:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (getToken()) {
      loadWallet()
    } else {
      setLoading(false)
    }
  }, [])

  // 充值
  const handleRecharge = async () => {
    if (!rechargeAmount || Number(rechargeAmount) <= 0) return
    
    try {
      setSubmitting(true)
      const result = await walletApi.recharge(Number(rechargeAmount), 'alipay')
      // 模拟确认充值
      await walletApi.confirmRecharge(result.order_no)
      setShowRecharge(false)
      setRechargeAmount('')
      loadWallet() // 刷新钱包
      
      setError('充值成功')
      setTimeout(() => setError(''), 2000)
    } catch (err: any) {
      setError(err.message || '充值失败')
      setTimeout(() => setError(''), 3000)
    } finally {
      setSubmitting(false)
    }
  }

  // 加载全部交易记录
  const loadAllTransactions = async () => {
    try {
      setAllTxLoading(true)
      const txResponse = await walletApi.getTransactions(1, 100) // 简单起见，这里拉取前100条作为"全部"
      setAllTransactions(txResponse.items.map(convertTransaction))
      setShowAllTransactions(true)
    } catch (err: any) {
      setError(err.message || '加载交易记录失败')
      setTimeout(() => setError(''), 3000)
    } finally {
      setAllTxLoading(false)
    }
  }

  // 转账
  const handleTransfer = async () => {
    if (!transferData.to || !transferData.amount || Number(transferData.amount) <= 0) return
    
    try {
      setSubmitting(true)
      setError('')
      
      // 先搜索用户，根据用户名或学号匹配转账对象
      const users = await usersApi.searchUsers(transferData.to)
      if (users.length === 0) {
        throw new Error('未找到该转账对象')
      }
      
      // 取第一个匹配的用户作为转账对象
      const toUserId = users[0].id
      
      // 执行转账
      await walletApi.transfer(toUserId, Number(transferData.amount))
      
      setShowTransfer(false)
      setTransferData({ to: '', amount: '' })
      loadWallet() // 刷新钱包
      
      // 成功提示 (使用 alert 或者通过 setError 设置临时成功的状态，这里简单处理一下错误提示作为通用弹窗)
      setError('转账成功')
      setTimeout(() => setError(''), 2000)
    } catch (err: any) {
      setError(err.message || '转账失败')
      setTimeout(() => setError(''), 3000)
    } finally {
      setSubmitting(false)
    }
  }

  const balance = wallet?.balance || 0
  const totalIncome = wallet?.total_income || 0
  const totalExpense = wallet?.total_expense || 0

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-2xl mx-auto px-4">
        {loading ? (
          <div className="text-center py-12">
            <Loader2 className="w-8 h-8 mx-auto text-primary animate-spin mb-4" />
            <p className="text-muted-foreground">加载中...</p>
          </div>
        ) : (
          <>
            {/* 余额卡片 */}
        <Card className="border-0 shadow-xl bg-gradient-to-br from-primary to-info text-primary-foreground mb-6 overflow-hidden relative">
          <div className="absolute top-0 right-0 w-40 h-40 bg-primary-foreground/10 rounded-full -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-32 h-32 bg-primary-foreground/10 rounded-full translate-y-1/2 -translate-x-1/2" />
          <CardContent className="p-6 relative z-10">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Wallet className="w-6 h-6" />
                <span className="font-medium">我的钱包</span>
              </div>
              <CreditCard className="w-6 h-6 opacity-70" />
            </div>
            <div className="mb-6">
              <p className="text-sm opacity-80 mb-1">账户余额</p>
              <p className="text-4xl font-bold">¥{balance.toFixed(2)}</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-primary-foreground/10 rounded-lg p-3">
                <div className="flex items-center gap-1 text-sm opacity-80 mb-1">
                  <TrendingUp className="w-4 h-4" />
                  本月收入
                </div>
                <p className="text-xl font-semibold">+¥{totalIncome.toFixed(2)}</p>
              </div>
              <div className="bg-primary-foreground/10 rounded-lg p-3">
                <div className="flex items-center gap-1 text-sm opacity-80 mb-1">
                  <TrendingDown className="w-4 h-4" />
                  本月支出
                </div>
                <p className="text-xl font-semibold">-¥{totalExpense.toFixed(2)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 快捷操作 */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          {quickActions.map((action, index) => {
            const Icon = action.icon
            return (
              <button
                key={index}
                className="flex flex-col items-center gap-2 p-4 rounded-xl bg-card shadow-md hover:shadow-lg transition-all card-hover"
                onClick={() => {
                  if (action.label === '充值') setShowRecharge(true)
                  if (action.label === '转账') setShowTransfer(true)
                  if (action.label === '账单') loadAllTransactions()
                }}
              >
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${action.color} flex items-center justify-center`}>
                  <Icon className="w-6 h-6 text-primary-foreground" />
                </div>
                <span className="text-sm font-medium text-foreground">{action.label}</span>
              </button>
            )
          })}
        </div>

        {/* 交易记录 */}
        <Card className="border-0 shadow-lg">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <History className="w-5 h-5 text-primary" />
              交易记录
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={loadAllTransactions} disabled={allTxLoading}>
              {allTxLoading ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : null}
              查看全部 <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {transactions.length > 0 ? transactions.map((transaction) => (
              <div
                key={transaction.id}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center text-xl">
                    {transaction.icon}
                  </div>
                  <div>
                    <p className="font-medium text-foreground">{transaction.title}</p>
                    <p className="text-xs text-muted-foreground">{transaction.date}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`font-semibold ${transaction.amount > 0 ? 'text-success' : 'text-foreground'}`}>
                    {transaction.amount > 0 ? '+' : ''}¥{Math.abs(transaction.amount).toFixed(2)}
                  </p>
                  <Badge variant={transaction.status === 'completed' ? 'secondary' : 'outline'} className="text-xs">
                    {transaction.status === 'completed' ? '已完成' : '处理中'}
                  </Badge>
                </div>
              </div>
            )) : (
              <div className="text-center py-8 text-muted-foreground">
                暂无交易记录
              </div>
            )}
          </CardContent>
        </Card>

        {/* 充值弹窗 */}
        {showRecharge && (
          <div className="fixed inset-0 bg-foreground/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-sm animate-scale-in">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>模拟充值</CardTitle>
                <Button variant="ghost" size="icon" onClick={() => setShowRecharge(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-foreground">自定义充值金额 (模拟)</label>
                  <Input
                    type="number"
                    placeholder="请输入任意金额..."
                    value={rechargeAmount}
                    onChange={(e) => setRechargeAmount(e.target.value)}
                    className="mt-1"
                    min="0.01"
                    step="0.01"
                  />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {[50, 100, 200].map((amount) => (
                    <Button
                      key={amount}
                      variant="outline"
                      onClick={() => setRechargeAmount(amount.toString())}
                    >
                      ¥{amount}
                    </Button>
                  ))}
                </div>
                <div className="flex gap-2 pt-2">
                  <Button variant="gradient" className="w-full" onClick={handleRecharge} disabled={submitting}>
                    {submitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                    {submitting ? '处理中...' : '确认充值 (模拟)'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* 转账弹窗 */}
        {showTransfer && (
          <div className="fixed inset-0 bg-foreground/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-sm animate-scale-in">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>转账</CardTitle>
                <Button variant="ghost" size="icon" onClick={() => setShowTransfer(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-foreground">转账对象</label>
                  <Input
                    placeholder="输入用户名或学号"
                    value={transferData.to}
                    onChange={(e) => setTransferData({ ...transferData, to: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground">转账金额</label>
                  <Input
                    type="number"
                    placeholder="请输入金额"
                    value={transferData.amount}
                    onChange={(e) => setTransferData({ ...transferData, amount: e.target.value })}
                    className="mt-1"
                    min="0.01"
                    step="0.01"
                  />
                </div>
                <div className="flex gap-2 pt-2">
                  <Button variant="gradient" className="w-full" onClick={handleTransfer} disabled={submitting}>
                    {submitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                    {submitting ? '处理中...' : '确认转账'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* 全部交易记录弹窗 */}
        {showAllTransactions && (
          <div className="fixed inset-0 bg-foreground/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-lg animate-scale-in max-h-[80vh] flex flex-col">
              <CardHeader className="flex flex-row items-center justify-between border-b border-border pb-4">
                <div className="flex items-center gap-3">
                  <CardTitle>全部交易记录</CardTitle>
                  <Badge variant="secondary" className="font-normal">{allTransactions.length}条记录</Badge>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setShowAllTransactions(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </CardHeader>
              <CardContent className="flex-1 overflow-y-auto p-4 space-y-3">
                {allTransactions.length > 0 ? allTransactions.map((transaction) => (
                  <div
                    key={transaction.id}
                    className="flex items-center justify-between p-4 rounded-xl bg-card border border-border shadow-sm hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center text-2xl">
                        {transaction.icon}
                      </div>
                      <div>
                        <p className="font-medium text-foreground text-base">{transaction.title}</p>
                        <p className="text-sm text-muted-foreground">{transaction.date}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`font-bold text-lg ${transaction.amount > 0 ? 'text-success' : 'text-foreground'}`}>
                        {transaction.amount > 0 ? '+' : ''}¥{Math.abs(transaction.amount).toFixed(2)}
                      </p>
                      <Badge variant={transaction.status === 'completed' ? 'secondary' : 'outline'} className="text-xs mt-1">
                        {transaction.status === 'completed' ? '已完成' : '处理中'}
                      </Badge>
                    </div>
                  </div>
                )) : (
                  <div className="text-center py-12 text-muted-foreground flex flex-col items-center">
                    <History className="w-12 h-12 mb-4 opacity-20" />
                    <p>暂无交易记录</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
          </>
        )}

        {error && (
          <div className={`fixed bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg shadow-lg z-50 ${
            error.includes('成功') ? 'bg-green-500 text-white' : 'bg-destructive text-destructive-foreground'
          }`}>
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
