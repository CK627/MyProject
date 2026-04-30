'use client'

import React, { useState, useRef } from 'react'
import { X, Upload, Loader2, ImageIcon } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { usersApi } from '@/lib/api'

interface AvatarUploadDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (avatarUrl: string) => void
  currentAvatar?: string
}

export function AvatarUploadDialog({ isOpen, onClose, onSuccess, currentAvatar }: AvatarUploadDialogProps) {
  const [preview, setPreview] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // 验证文件类型
    if (!file.type.startsWith('image/')) {
      setError('请选择图片文件')
      return
    }

    // 验证文件大小 (10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('图片大小不能超过10MB')
      return
    }

    setError('')
    setSelectedFile(file)

    // 预览并压缩图片 (最大 300x300)
    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        const MAX_SIZE = 300
        let width = img.width
        let height = img.height

        if (width > height) {
          if (width > MAX_SIZE) {
            height *= MAX_SIZE / width
            width = MAX_SIZE
          }
        } else {
          if (height > MAX_SIZE) {
            width *= MAX_SIZE / height
            height = MAX_SIZE
          }
        }

        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        ctx?.drawImage(img, 0, 0, width, height)
        
        // 压缩质量为 0.8 的 JPEG
        const compressedBase64 = canvas.toDataURL('image/jpeg', 0.8)
        setPreview(compressedBase64)
      }
      img.src = e.target?.result as string
    }
    reader.readAsDataURL(file)
  }

  const handleUpload = async () => {
    if (!selectedFile || !preview) return

    try {
      setUploading(true)
      setError('')

      // Update user avatar directly with base64 data
      await usersApi.updateMyProfile({ avatar: preview })
      
      onSuccess(preview)
      handleClose()
    } catch (err: any) {
      setError(err.message || '上传失败')
    } finally {
      setUploading(false)
    }
  }

  const handleClose = () => {
    setPreview(null)
    setSelectedFile(null)
    setError('')
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={handleClose} />
      <Card className="relative z-10 w-full max-w-md mx-4 border-0 shadow-2xl">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-lg">更换头像</CardTitle>
          <button
            onClick={handleClose}
            className="p-1 rounded-full hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 预览区域 */}
          <div className="flex justify-center">
            <div className="relative w-40 h-40 rounded-full overflow-hidden bg-muted border-4 border-dashed border-border">
              {preview ? (
                <img
                  src={preview}
                  alt="预览"
                  className="w-full h-full object-cover"
                />
              ) : currentAvatar ? (
                <img
                  src={currentAvatar}
                  alt="当前头像"
                  className="w-full h-full object-cover opacity-50"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <ImageIcon className="w-16 h-16 text-muted-foreground" />
                </div>
              )}
            </div>
          </div>

          {/* 文件选择 */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={handleFileSelect}
            className="hidden"
          />
          
          <Button
            variant="outline"
            className="w-full"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="w-4 h-4 mr-2" />
            选择图片
          </Button>

          {selectedFile && (
            <p className="text-sm text-muted-foreground text-center">
              已选择: {selectedFile.name}
            </p>
          )}

          {/* 错误提示 */}
          {error && (
            <p className="text-sm text-destructive text-center">{error}</p>
          )}

          {/* 操作按钮 */}
          <div className="flex gap-3">
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
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  上传中...
                </>
              ) : (
                '确认上传'
              )}
            </Button>
          </div>

          <p className="text-xs text-muted-foreground text-center">
            支持 JPG、PNG、WebP、GIF 格式，最大 10MB
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
