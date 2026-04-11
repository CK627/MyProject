'use client'

import React from 'react'
import { 
  Shield, 
  Star, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  ThumbsDown,
  Users,
  Award,
  TrendingDown,
  Ban,
  MessageSquare,
  FileText,
  ArrowLeft,
  Info,
  TrendingUp,
  Heart,
  Trophy,
  Calendar,
  RefreshCw,
  Gift
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface ReputationRulesProps {
  onBack?: () => void
}

export function ReputationRules({ onBack }: ReputationRulesProps) {
  // 信誉分加分规则
  const rewardRules = [
    {
      icon: Heart,
      title: '完成互助任务',
      points: '+0.2',
      description: '成功完成一个互助任务',
      category: 'task'
    },
    {
      icon: Star,
      title: '获得点赞',
      points: '+0.3',
      description: '帖子或评论获得点赞',
      category: 'social'
    },
    {
      icon: CheckCircle,
      title: '发布任务并完成',
      points: '+0.1',
      description: '发布的任务被他人成功完成',
      category: 'task'
    },
    {
      icon: Trophy,
      title: '月度热度榜第一',
      points: '+3',
      description: '校园墙月度热度榜冠军',
      category: 'ranking'
    },
    {
      icon: Award,
      title: '月度热度榜第二',
      points: '+2',
      description: '校园墙月度热度榜亚军',
      category: 'ranking'
    },
    {
      icon: Star,
      title: '月度热度榜第三',
      points: '+1',
      description: '校园墙月度热度榜季军',
      category: 'ranking'
    },
    {
      icon: Trophy,
      title: '周度热度榜第一',
      points: '+1',
      description: '校园墙周度热度榜冠军',
      category: 'ranking'
    },
    {
      icon: Award,
      title: '周度热度榜第二',
      points: '+0.5',
      description: '校园墙周度热度榜亚军',
      category: 'ranking'
    },
    {
      icon: Star,
      title: '周度热度榜第三',
      points: '+0.3',
      description: '校园墙周度热度榜季军',
      category: 'ranking'
    },
    {
      icon: TrendingUp,
      title: '日度趋势榜第一',
      points: '+0.3',
      description: '校园墙日度趋势榜冠军',
      category: 'trending'
    },
    {
      icon: TrendingUp,
      title: '日度趋势榜第二',
      points: '+0.2',
      description: '校园墙日度趋势榜亚军',
      category: 'trending'
    },
    {
      icon: TrendingUp,
      title: '日度趋势榜第三',
      points: '+0.1',
      description: '校园墙日度趋势榜季军',
      category: 'trending'
    },
    {
      icon: TrendingUp,
      title: '周度趋势榜第一',
      points: '+0.5',
      description: '校园墙周度趋势榜冠军',
      category: 'trending'
    },
    {
      icon: TrendingUp,
      title: '周度趋势榜第二',
      points: '+0.3',
      description: '校园墙周度趋势榜亚军',
      category: 'trending'
    },
    {
      icon: TrendingUp,
      title: '周度趋势榜第三',
      points: '+0.2',
      description: '校园墙周度趋势榜季军',
      category: 'trending'
    }
  ]

  // 信誉分扣除规则
  const deductionRules = [
    {
      icon: XCircle,
      title: '评论被管理员删除',
      points: -10,
      description: '管理员判定评论违规后直接删除',
      severity: 'high'
    },
    {
      icon: Users,
      title: '评论被审核员投票删除',
      points: -5,
      description: '3名以上审核员投票判定违规后删除',
      severity: 'medium'
    },
    {
      icon: ThumbsDown,
      title: '评论因拉踩过多删除',
      points: -2,
      description: '当拉踩数 > 点赞数×2+5 时自动删除',
      severity: 'low'
    },
    {
      icon: FileText,
      title: '帖子被管理员删除',
      points: -15,
      description: '发布严重违规内容被管理员删除',
      severity: 'high'
    },
    {
      icon: AlertTriangle,
      title: '帖子审核未通过',
      points: -3,
      description: '发布的帖子因内容问题被驳回',
      severity: 'low'
    },
    {
      icon: XCircle,
      title: '任务未完成',
      points: -5,
      description: '接受的任务未按时完成',
      severity: 'medium'
    },
    {
      icon: Ban,
      title: '发布违规内容',
      points: -10,
      description: '发布暴力、血腥、色情等违规内容',
      severity: 'high'
    },
    {
      icon: MessageSquare,
      title: '恶意评论',
      points: -2,
      description: '发表恶意、攻击性评论',
      severity: 'low'
    }
  ]

  // 信誉等级
  const reputationLevels = [
    {
      range: '≥98',
      level: '审核员',
      color: 'from-amber-400 to-yellow-500',
      textColor: 'text-amber-600',
      bgColor: 'bg-amber-50',
      borderColor: 'border-amber-200',
      icon: Award,
      privileges: ['可发布帖子（无限制）', '可评论（无限制）', '可发布互助任务', '可接单互助任务', '可参与内容审核投票', '可投票删除违规评论', '享有专属身份标识']
    },
    {
      range: '≥60',
      level: '正常用户',
      color: 'from-emerald-400 to-green-500',
      textColor: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
      borderColor: 'border-emerald-200',
      icon: CheckCircle,
      privileges: ['可发布帖子（无限制）', '可评论（无限制）', '可发布互助任务', '可接单互助任务']
    },
    {
      range: '<60',
      level: '禁言用户',
      color: 'from-gray-500 to-slate-600',
      textColor: 'text-gray-600',
      bgColor: 'bg-gray-100',
      borderColor: 'border-gray-300',
      icon: Ban,
      privileges: ['禁止发布帖子', '禁止评论', '可发布互助任务', '可接单互助任务', '需努力提升信誉分']
    }
  ]

  // 审核员权限
  const reviewerPrivileges = [
    '参与内容审核投票',
    '查看待审核帖子',
    '投票删除违规评论',
    '获得审核员专属标识',
    '信誉分优先恢复权'
  ]

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'bg-red-500'
      case 'medium': return 'bg-orange-500'
      case 'low': return 'bg-yellow-500'
      default: return 'bg-gray-500'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* 返回按钮 */}
        {onBack && (
          <Button 
            variant="ghost" 
            onClick={onBack}
            className="mb-6 hover:bg-white/80"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回
          </Button>
        )}

        {/* 标题区域 */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-primary to-primary/70 mb-4 shadow-lg shadow-primary/25">
            <Shield className="w-10 h-10 text-primary-foreground" />
          </div>
          <h1 className="text-3xl font-bold text-foreground mb-3">信誉系统规则</h1>
          <p className="text-muted-foreground max-w-xl mx-auto">
            信誉分是衡量用户在平台行为规范程度的重要指标，初始60分，良好的信誉分可以享受更多权益
          </p>
        </div>

        {/* 基础说明 */}
        <Card className="mb-8 border-primary/20 bg-gradient-to-r from-primary/5 to-transparent">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Info className="w-5 h-5 text-primary" />
              基础规则
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-3 gap-4">
              <div className="flex items-center gap-3 p-4 bg-white/60 rounded-xl">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <Star className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-primary">60</div>
                  <div className="text-sm text-muted-foreground">初始信誉分</div>
                </div>
              </div>
              <div className="flex items-center gap-3 p-4 bg-white/60 rounded-xl">
                <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center">
                  <Award className="w-6 h-6 text-amber-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-amber-600">98+</div>
                  <div className="text-sm text-muted-foreground">审核员门槛</div>
                </div>
              </div>
              <div className="flex items-center gap-3 p-4 bg-white/60 rounded-xl">
                <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                  <Ban className="w-6 h-6 text-red-500" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-500">&lt;60</div>
                  <div className="text-sm text-muted-foreground">禁言阈值</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 加分规则 */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-500" />
              信誉分获取规则
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* 任务相关 */}
            <div className="mb-6">
              <h4 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                <Heart className="w-4 h-4 text-pink-500" />
                互助任务
              </h4>
              <div className="grid md:grid-cols-2 gap-3">
                {rewardRules.filter(r => r.category === 'task').map((rule, index) => (
                  <div 
                    key={index}
                    className="flex items-center gap-3 p-3 rounded-xl bg-gradient-to-r from-emerald-50 to-transparent hover:from-emerald-100 transition-colors"
                  >
                    <div className="w-10 h-10 rounded-full flex items-center justify-center bg-emerald-100">
                      <rule.icon className="w-5 h-5 text-emerald-600" />
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-foreground">{rule.title}</div>
                      <div className="text-xs text-muted-foreground">{rule.description}</div>
                    </div>
                    <span className="px-3 py-1 rounded-full text-sm font-bold bg-emerald-100 text-emerald-700">
                      {rule.points}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* 社交互动 */}
            <div className="mb-6">
              <h4 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                <Star className="w-4 h-4 text-amber-500" />
                社交互动
              </h4>
              <div className="grid md:grid-cols-2 gap-3">
                {rewardRules.filter(r => r.category === 'social').map((rule, index) => (
                  <div 
                    key={index}
                    className="flex items-center gap-3 p-3 rounded-xl bg-gradient-to-r from-amber-50 to-transparent hover:from-amber-100 transition-colors"
                  >
                    <div className="w-10 h-10 rounded-full flex items-center justify-center bg-amber-100">
                      <rule.icon className="w-5 h-5 text-amber-600" />
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-foreground">{rule.title}</div>
                      <div className="text-xs text-muted-foreground">{rule.description}</div>
                    </div>
                    <span className="px-3 py-1 rounded-full text-sm font-bold bg-amber-100 text-amber-700">
                      {rule.points}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* 热度榜单 */}
            <div className="mb-6">
              <h4 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                <Trophy className="w-4 h-4 text-purple-500" />
                热度榜单
              </h4>
              <div className="grid md:grid-cols-3 gap-3">
                {rewardRules.filter(r => r.category === 'ranking').map((rule, index) => (
                  <div 
                    key={index}
                    className="flex flex-col gap-2 p-3 rounded-xl bg-gradient-to-br from-purple-50 to-pink-50 hover:shadow-md transition-all"
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center bg-purple-100">
                        <rule.icon className="w-4 h-4 text-purple-600" />
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-700">
                        {rule.points}
                      </span>
                    </div>
                    <div className="font-medium text-sm text-foreground">{rule.title}</div>
                    <div className="text-xs text-muted-foreground">{rule.description}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* 趋势榜单 */}
            <div>
              <h4 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-500" />
                趋势榜单
              </h4>
              <div className="grid md:grid-cols-3 gap-3">
                {rewardRules.filter(r => r.category === 'trending').map((rule, index) => (
                  <div 
                    key={index}
                    className="flex flex-col gap-2 p-3 rounded-xl bg-gradient-to-br from-blue-50 to-cyan-50 hover:shadow-md transition-all"
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center bg-blue-100">
                        <rule.icon className="w-4 h-4 text-blue-600" />
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-700">
                        {rule.points}
                      </span>
                    </div>
                    <div className="font-medium text-sm text-foreground">{rule.title}</div>
                    <div className="text-xs text-muted-foreground">{rule.description}</div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 扣分规则 */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-red-500" />
              信誉分扣除规则
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {deductionRules.map((rule, index) => (
              <div 
                key={index}
                className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-r from-gray-50 to-transparent hover:from-gray-100 transition-colors"
              >
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  rule.severity === 'high' ? 'bg-red-100' : 
                  rule.severity === 'medium' ? 'bg-orange-100' : 'bg-yellow-100'
                }`}>
                  <rule.icon className={`w-5 h-5 ${
                    rule.severity === 'high' ? 'text-red-500' : 
                    rule.severity === 'medium' ? 'text-orange-500' : 'text-yellow-600'
                  }`} />
                </div>
                <div className="flex-1">
                  <div className="font-medium text-foreground">{rule.title}</div>
                  <div className="text-sm text-muted-foreground">{rule.description}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                    rule.severity === 'high' ? 'bg-red-100 text-red-600' : 
                    rule.severity === 'medium' ? 'bg-orange-100 text-orange-600' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {rule.points} 分
                  </span>
                  <div className={`w-2 h-2 rounded-full ${getSeverityColor(rule.severity)}`} />
                </div>
              </div>
            ))}
            <div className="flex items-center gap-4 mt-4 pt-4 border-t text-sm text-muted-foreground">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> 严重</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500" /> 中等</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" /> 轻微</span>
            </div>
          </CardContent>
        </Card>

        {/* 信誉等级 */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Star className="w-5 h-5 text-amber-500" />
              信誉等级与权限
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4">
              {reputationLevels.map((level, index) => (
                <div 
                  key={index}
                  className={`p-4 rounded-xl border ${level.borderColor} ${level.bgColor} transition-all hover:shadow-md`}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${level.color} flex items-center justify-center shadow-lg`}>
                      <level.icon className="w-7 h-7 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span className={`font-bold text-lg ${level.textColor}`}>{level.level}</span>
                        <span className="px-2 py-0.5 rounded-full bg-white/80 text-sm font-medium text-gray-600">
                          {level.range} 分
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {level.privileges.map((privilege, pIndex) => (
                          <span 
                            key={pIndex}
                            className="text-xs px-2 py-1 rounded-full bg-white/60 text-gray-600"
                          >
                            {privilege}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 审核员说明 */}
        <Card className="mb-8 border-amber-200 bg-gradient-to-r from-amber-50 to-yellow-50/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-700">
              <Award className="w-5 h-5" />
              成为审核员
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 mb-4">
              信誉分达到 <span className="font-bold text-amber-600">98分及以上</span> 的用户将自动成为审核员，
              参与平台内容审核工作，维护社区环境。
            </p>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">
              {reviewerPrivileges.map((privilege, index) => (
                <div 
                  key={index}
                  className="flex items-center gap-2 p-3 bg-white/70 rounded-lg"
                >
                  <CheckCircle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                  <span className="text-sm text-gray-700">{privilege}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 评论删除机制 */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-indigo-500" />
              月度刷新规则
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-100">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                  <RefreshCw className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-indigo-700 mb-2">每月信誉分刷新</h4>
                  <p className="text-sm text-gray-600 mb-3">
                    每个月会进行信誉分刷新，保证系统活力与公平性
                  </p>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-green-500" />
                      <span className="text-sm"><span className="font-semibold text-green-600">&gt;70分</span>：下月继承时扣除5分</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <span className="text-sm"><span className="font-semibold text-blue-600">60-70分</span>：下月继承时不扣分</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-orange-500" />
                      <span className="text-sm"><span className="font-semibold text-orange-600">&lt;60分</span>：下月自动增加3分（帮助恢复）</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-gradient-to-r from-amber-50 to-yellow-50 border border-amber-100">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
                  <Gift className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-amber-700 mb-2">管理员嘉奖</h4>
                  <p className="text-sm text-gray-600">
                    管理员可以对表现优秀的用户进行信誉分嘉奖，鼓励积极行为
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 评论删除机制 */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-blue-500" />
              评论删除机制
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100">
                <h4 className="font-semibold text-blue-700 mb-2">自己的评论</h4>
                <p className="text-sm text-gray-600">可以随时删除自己发布的评论，无任何惩罚</p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-red-50 to-rose-50 border border-red-100">
                <h4 className="font-semibold text-red-600 mb-2">管理员删除</h4>
                <p className="text-sm text-gray-600">管理员可直接删除违规评论，评论者 <span className="font-bold">-10 信誉分</span></p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-orange-50 to-amber-50 border border-orange-100">
                <h4 className="font-semibold text-orange-600 mb-2">审核员投票删除</h4>
                <p className="text-sm text-gray-600">3名及以上审核员投票后删除，评论者 <span className="font-bold">-5 信誉分</span></p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-yellow-50 to-lime-50 border border-yellow-100">
                <h4 className="font-semibold text-yellow-700 mb-2">社区投票删除</h4>
                <p className="text-sm text-gray-600">拉踩数 &gt; 点赞数×2+5 时自动删除，评论者 <span className="font-bold">-2 信誉分</span></p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 温馨提示 */}
        <div className="p-6 rounded-2xl bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border border-primary/20">
          <div className="flex gap-4">
            <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
              <Shield className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground mb-2">温馨提示</h3>
              <ul className="space-y-1 text-sm text-muted-foreground">
                <li>• 遵守社区规范，发布积极正向的内容</li>
                <li>• 尊重他人，文明交流，共建和谐校园</li>
                <li>• 积极参与互助任务，帮助他人获得信誉加分</li>
                <li>• 创作优质内容冲击热度榜和趋势榜</li>
                <li>• 如对处罚有异议，可联系管理员申诉</li>
                <li>• 每月信誉分会自动刷新，低于60分会自动恢复3分</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
