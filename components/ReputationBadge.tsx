'use client'

import React from 'react'
import { Award, Heart, ThumbsUp, Star } from 'lucide-react'

interface ReputationBadgeProps {
  creditScore: number
  likeCount: number
  approvalRate: number
  compact?: boolean
}

export function ReputationBadge({ creditScore, likeCount, approvalRate, compact = false }: ReputationBadgeProps) {
  // 根据信誉分获取颜色和等级
  const getCreditLevel = (score: number): { color: string; bgColor: string; label: string } => {
    if (score >= 80) return { color: 'text-green-500', bgColor: 'bg-green-500/10', label: '优秀' }
    if (score >= 60) return { color: 'text-yellow-500', bgColor: 'bg-yellow-500/10', label: '良好' }
    if (score >= 40) return { color: 'text-orange-500', bgColor: 'bg-orange-500/10', label: '一般' }
    return { color: 'text-red-500', bgColor: 'bg-red-500/10', label: '待提升' }
  }

  const creditLevel = getCreditLevel(creditScore)
  const approvalPercent = Math.round(approvalRate * 100)

  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-1 px-2 py-1 rounded-full ${creditLevel.bgColor}`}>
          <Award className={`w-4 h-4 ${creditLevel.color}`} />
          <span className={`text-sm font-medium ${creditLevel.color}`}>{creditScore}</span>
        </div>
        <div className="flex items-center gap-1 text-muted-foreground">
          <Heart className="w-4 h-4" />
          <span className="text-sm">{likeCount}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-4">
      {/* 信誉分 */}
      <div className={`flex flex-col items-center p-4 rounded-lg ${creditLevel.bgColor}`}>
        <Award className={`w-8 h-8 mb-2 ${creditLevel.color}`} />
        <span className={`text-2xl font-bold ${creditLevel.color}`}>{creditScore}</span>
        <span className="text-xs text-muted-foreground">信誉分</span>
        <span className={`text-xs mt-1 ${creditLevel.color}`}>{creditLevel.label}</span>
      </div>

      {/* 获赞数 */}
      <div className="flex flex-col items-center p-4 rounded-lg bg-pink-500/10">
        <Heart className="w-8 h-8 mb-2 text-pink-500" />
        <span className="text-2xl font-bold text-pink-500">{likeCount}</span>
        <span className="text-xs text-muted-foreground">获赞数</span>
      </div>

      {/* 好评率 */}
      <div className="flex flex-col items-center p-4 rounded-lg bg-blue-500/10">
        <ThumbsUp className="w-8 h-8 mb-2 text-blue-500" />
        <span className="text-2xl font-bold text-blue-500">{approvalPercent}%</span>
        <span className="text-xs text-muted-foreground">好评率</span>
      </div>
    </div>
  )
}

// 信誉分说明组件
export function ReputationExplain() {
  return (
    <div className="text-sm text-muted-foreground space-y-2">
      <p className="font-medium text-foreground">信誉分说明</p>
      <ul className="space-y-1 text-xs">
        <li className="flex items-center gap-2">
          <Star className="w-3 h-3 text-green-500" />
          <span>80+ 分: 优秀信誉，任务优先匹配</span>
        </li>
        <li className="flex items-center gap-2">
          <Star className="w-3 h-3 text-yellow-500" />
          <span>60-79 分: 良好信誉，正常使用</span>
        </li>
        <li className="flex items-center gap-2">
          <Star className="w-3 h-3 text-orange-500" />
          <span>40-59 分: 一般信誉，部分功能受限</span>
        </li>
        <li className="flex items-center gap-2">
          <Star className="w-3 h-3 text-red-500" />
          <span>&lt;40 分: 待提升，需改善行为</span>
        </li>
      </ul>
      <p className="text-xs pt-2">
        提升方式: 完成任务、获得好评、遵守社区规范
      </p>
    </div>
  )
}
