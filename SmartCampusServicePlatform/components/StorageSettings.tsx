'use client'

import React, { useState, useEffect } from 'react'
import { 
  HardDrive,
  Trash2,
  Database,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Loader2,
  Info
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { messageStorage } from '@/lib/messageStorage'

interface CacheStats {
  totalSize: number
  fileCount: number
}

export function StorageSettings() {
  const [loading, setLoading] = useState(true)
  const [cacheStats, setCacheStats] = useState<CacheStats>({ totalSize: 0, fileCount: 0 })
  const [clearing, setClearing] = useState(false)
  const [cleaning, setCleaning] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      setLoading(true)
      const stats = await messageStorage.getCacheStats()
      setCacheStats(stats)
    } catch (err) {
      console.error('加载统计失败:', err)
      setErrorMessage('加载统计失败')
    } finally {
      setLoading(false)
    }
  }

  const handleClearAll = async () => {
    if (!confirm('确定要清空所有缓存吗?这将删除所有本地消息和文件,但不影响服务器数据。')) {
      return
    }

    try {
      setClearing(true)
      await messageStorage.clearAllCache()
      await loadStats()
      setSuccessMessage('缓存已清空')
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (err) {
      console.error('清空缓存失败:', err)
      setErrorMessage('清空缓存失败')
      setTimeout(() => setErrorMessage(''), 3000)
    } finally {
      setClearing(false)
    }
  }

  const handleCleanExpired = async () => {
    try {
      setCleaning(true)
      const count = await messageStorage.cleanExpiredFiles(30)
      await loadStats()
      setSuccessMessage(`已清理 ${count} 个过期文件`)
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (err) {
      console.error('清理过期文件失败:', err)
      setErrorMessage('清理过期文件失败')
      setTimeout(() => setErrorMessage(''), 3000)
    } finally {
      setCleaning(false)
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="min-h-screen bg-background pt-20 pb-8">
      <div className="max-w-4xl mx-auto px-4">
        <h1 className="text-2xl font-bold flex items-center gap-2 text-foreground mb-6">
          <Database className="w-6 h-6 text-primary" />
          存储管理
        </h1>

        {/* 提示消息 */}
        {successMessage && (
          <div className="mb-4 p-3 rounded-lg bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 text-sm flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            {successMessage}
          </div>
        )}
        {errorMessage && (
          <div className="mb-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {errorMessage}
          </div>
        )}

        {/* 缓存统计 */}
        <Card className="mb-6 border-0 shadow-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="w-5 h-5 text-primary" />
              本地缓存统计
            </CardTitle>
            <CardDescription>
              IndexedDB 存储的消息和文件数据
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">
                <Loader2 className="w-8 h-8 mx-auto text-primary animate-spin mb-4" />
                <p className="text-muted-foreground">加载中...</p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 gap-6">
                <div className="p-6 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">总占用空间</span>
                    <HardDrive className="w-5 h-5 text-primary" />
                  </div>
                  <p className="text-3xl font-bold text-foreground">{formatBytes(cacheStats.totalSize)}</p>
                </div>
                
                <div className="p-6 rounded-lg bg-gradient-to-br from-secondary/10 to-secondary/5">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">文件数量</span>
                    <Database className="w-5 h-5 text-secondary" />
                  </div>
                  <p className="text-3xl font-bold text-foreground">{cacheStats.fileCount}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 缓存管理操作 */}
        <Card className="mb-6 border-0 shadow-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-primary" />
              缓存管理
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 清理过期文件 */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
              <div className="flex-1">
                <h3 className="font-medium text-foreground mb-1">清理过期文件</h3>
                <p className="text-sm text-muted-foreground">
                  删除30天未访问的缓存文件,释放存储空间
                </p>
              </div>
              <Button
                variant="outline"
                onClick={handleCleanExpired}
                disabled={cleaning}
                className="ml-4"
              >
                {cleaning ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4 mr-2" />
                )}
                清理
              </Button>
            </div>

            {/* 刷新统计 */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
              <div className="flex-1">
                <h3 className="font-medium text-foreground mb-1">刷新统计</h3>
                <p className="text-sm text-muted-foreground">
                  重新计算缓存占用空间和文件数量
                </p>
              </div>
              <Button
                variant="outline"
                onClick={loadStats}
                disabled={loading}
                className="ml-4"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4 mr-2" />
                )}
                刷新
              </Button>
            </div>

            {/* 清空所有缓存 */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-destructive/10">
              <div className="flex-1">
                <h3 className="font-medium text-destructive mb-1">清空所有缓存</h3>
                <p className="text-sm text-muted-foreground">
                  删除所有本地消息和文件,不可恢复(服务器数据不受影响)
                </p>
              </div>
              <Button
                variant="destructive"
                onClick={handleClearAll}
                disabled={clearing}
                className="ml-4"
              >
                {clearing ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4 mr-2" />
                )}
                清空
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 存储说明 */}
        <Card className="border-0 shadow-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="w-5 h-5 text-primary" />
              存储说明
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <div className="flex gap-2">
              <Badge variant="outline" className="flex-shrink-0">本地优先</Badge>
              <p>消息和文件优先存储在本地IndexedDB,离线可访问</p>
            </div>
            <div className="flex gap-2">
              <Badge variant="outline" className="flex-shrink-0">智能缓存</Badge>
              <p>自动管理缓存过期,30天未访问的文件将被清理</p>
            </div>
            <div className="flex gap-2">
              <Badge variant="outline" className="flex-shrink-0">软删除</Badge>
              <p>删除的消息会延迟物理删除,提供撤销恢复时间</p>
            </div>
            <div className="flex gap-2">
              <Badge variant="outline" className="flex-shrink-0">去重存储</Badge>
              <p>相同文件只存储一次,通过引用计数节省空间</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
