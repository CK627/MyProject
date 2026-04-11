'use client'

import React, { useState, useEffect } from 'react'
import { 
  School,
  MapPin,
  Calendar,
  Users,
  Award,
  BookOpen,
  Building,
  GraduationCap,
  Globe,
  Phone,
  Mail,
  ExternalLink,
  Loader2,
  MapPinned,
  Briefcase,
  TrendingUp,
  Clock,
  Cpu,
  Palette,
  Languages,
  BadgeCheck,
  Dumbbell,
  Lightbulb,
  ChevronRight,
  Navigation,
  Target,
  Layers,
  Star,
  X
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogBody } from '@/components/ui/dialog'
import { schoolApi, SchoolInfo, Department, Facility } from '@/lib/api'
import { departmentsData, campusLocations, DepartmentDetail, Major } from '@/lib/schoolData'

// 院系图标映射
const departmentIcons: Record<string, React.ElementType> = {
  '经济管理学院': Briefcase,
  '数字商务学院': TrendingUp,
  '机电工程学院': Cpu,
  '电子信息学院': Cpu,
  '建筑与艺术学院': Palette,
  '国际交流学院': Languages,
}

// 设施图标映射
const facilityIcons: Record<string, React.ElementType> = {
  '图书馆': BookOpen,
  '实训中心': Briefcase,
  '体育馆': Dumbbell,
  '学生活动中心': Users,
  '创业孵化园': Lightbulb,
  '国际交流中心': Globe,
}

// 默认学校信息
const defaultSchoolInfo = {
  name: '浙江工商职业技术学院',
  founded: '1914年',
  type: '公办高职院校',
  motto: '厚德 进业 明智 笃行',
  location: '浙江省宁波市海曙区机场路1988号',
  website: 'https://zs.zbti.edu.cn/',
  phone: '0574-87422148',
  email: 'zsb@zjbti.net.cn',
  description: '浙江工商职业技术学院是浙江省人民政府首批批准成立的四所全日制公办普通高等职业院校之一，前身为创建于1914年的"宁波公立甲种商业学校"，被誉为"宁波商帮文化的摇篮"。',
  stats: [
    { label: '在校学生', value: '11,400+', icon: Users },
    { label: '占地面积', value: '894亩', icon: MapPinned },
    { label: '二级学院', value: '6个', icon: Building },
    { label: '就业率', value: '98.36%', icon: Award },
  ]
}

const defaultDepartments = departmentsData.map(d => ({
  name: d.name,
  description: d.majors.map(m => m.name).slice(0, 4).join('、'),
  students: d.studentCount,
  ranking: d.ranking
}))

const defaultFacilities = [
  { name: '图书馆', desc: '藏书丰富，设有电子阅览室、自习区', location: '校本部中心区', time: '7:00-22:00' },
  { name: '实训中心', desc: '商贸实训、电商直播、财会模拟', location: '校本部教学楼', time: '8:00-21:00' },
  { name: '体育馆', desc: '篮球场、羽毛球馆、健身房', location: '校本部南区', time: '6:00-22:00' },
  { name: '学生活动中心', desc: '社团活动、文艺演出、学生会议', location: '校本部西区', time: '8:00-22:00' },
  { name: '创业孵化园', desc: '大学生创业基地，电商实战平台', location: '校本部创业楼', time: '8:00-21:00' },
  { name: '国际交流中心', desc: '留学生服务、中外合作办学', location: '校本部行政楼', time: '8:30-17:00' },
]

const news = [
  { title: '我校学子在全国职业院校技能大赛中荣获一等奖', date: '2024-01-10', tag: '喜报' },
  { title: '校企合作签约仪式暨产教融合发展论坛成功举办', date: '2024-01-08', tag: '活动' },
  { title: '2024年春季学期开学典礼隆重举行', date: '2024-01-05', tag: '校园' },
  { title: '我校入选浙江省高水平职业院校建设单位', date: '2024-01-03', tag: '荣誉' },
]

const features = [
  { title: '百年商科', desc: '传承1914年商业教育精髓', icon: Award },
  { title: '产教融合', desc: '深度校企合作育人模式', icon: Briefcase },
  { title: '技能竞赛', desc: '全国大赛屡获佳绩', icon: TrendingUp },
  { title: '就业保障', desc: '98.36%毕业去向落实率', icon: BadgeCheck },
]

// 专业详情卡片组件
function MajorCard({ major, colorScheme }: { major: Major; colorScheme: string }) {
  const [expanded, setExpanded] = useState(false)
  
  return (
    <div className="border border-border/60 rounded-xl overflow-hidden hover:border-primary/30 transition-colors bg-card">
      <div 
        className="p-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <h4 className="font-semibold text-foreground">{major.name}</h4>
              {major.features?.map((f, i) => (
                <Badge key={i} variant="outline" className="text-xs bg-primary/5 text-primary border-primary/20">
                  {f}
                </Badge>
              ))}
            </div>
            <p className="text-sm text-muted-foreground line-clamp-2">{major.description}</p>
            <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {major.duration}
              </span>
              <span className="flex items-center gap-1">
                <GraduationCap className="w-3 h-3" />
                {major.degree}
              </span>
              {major.code && (
                <span className="flex items-center gap-1">
                  <Layers className="w-3 h-3" />
                  专业代码: {major.code}
                </span>
              )}
            </div>
          </div>
          <ChevronRight className={`w-5 h-5 text-muted-foreground transition-transform flex-shrink-0 ${expanded ? 'rotate-90' : ''}`} />
        </div>
      </div>
      
      {expanded && (
        <div className="px-4 pb-4 pt-0 space-y-4 border-t border-border/50 bg-secondary/20">
          <div className="pt-4">
            <h5 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-primary" />
              核心课程
            </h5>
            <div className="flex flex-wrap gap-1.5">
              {major.courses.map((course, i) => (
                <span key={i} className="px-2 py-1 text-xs bg-secondary rounded-md text-secondary-foreground">
                  {course}
                </span>
              ))}
            </div>
          </div>
          
          <div>
            <h5 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" />
              就业方向
            </h5>
            <div className="flex flex-wrap gap-1.5">
              {major.careers.map((career, i) => (
                <span key={i} className="px-2 py-1 text-xs bg-primary/10 rounded-md text-primary">
                  {career}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// 院系详情弹窗组件
function DepartmentDetailDialog({ 
  department, 
  open, 
  onClose 
}: { 
  department: DepartmentDetail | null
  open: boolean
  onClose: () => void 
}) {
  if (!department) return null

  const colorClasses: Record<string, string> = {
    'from-blue-500 to-blue-600': 'bg-gradient-to-r from-blue-500 to-blue-600',
    'from-emerald-500 to-emerald-600': 'bg-gradient-to-r from-emerald-500 to-emerald-600',
    'from-orange-500 to-orange-600': 'bg-gradient-to-r from-orange-500 to-orange-600',
    'from-purple-500 to-purple-600': 'bg-gradient-to-r from-purple-500 to-purple-600',
    'from-pink-500 to-pink-600': 'bg-gradient-to-r from-pink-500 to-pink-600',
    'from-cyan-500 to-cyan-600': 'bg-gradient-to-r from-cyan-500 to-cyan-600',
  }

  const Icon = departmentIcons[department.name] || Building

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent onClose={onClose} className="max-w-4xl">
        {/* Header with gradient */}
        <div className={`${colorClasses[department.colorScheme]} p-6 -m-0 rounded-t-2xl`}>
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center flex-shrink-0">
              <Icon className="w-9 h-9 text-white" />
            </div>
            <div className="flex-1 text-white">
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-2xl font-bold">{department.name}</h2>
                <Badge className="bg-white/20 text-white border-white/30 hover:bg-white/30">
                  {department.ranking}
                </Badge>
              </div>
              <p className="text-white/80 text-sm">{department.englishName}</p>
              <div className="flex items-center gap-6 mt-3 text-sm text-white/90">
                <span className="flex items-center gap-1.5">
                  <Users className="w-4 h-4" />
                  {department.studentCount.toLocaleString()} 名学生
                </span>
                <span className="flex items-center gap-1.5">
                  <GraduationCap className="w-4 h-4" />
                  {department.teacherCount} 名教师
                </span>
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-4 h-4" />
                  创建于 {department.establishedYear}
                </span>
              </div>
            </div>
          </div>
        </div>

        <DialogBody className="space-y-6">
          {/* 学院简介 */}
          <div>
            <h3 className="font-semibold text-lg text-foreground mb-3 flex items-center gap-2">
              <School className="w-5 h-5 text-primary" />
              学院简介
            </h3>
            <p className="text-muted-foreground leading-relaxed">{department.description}</p>
          </div>

          {/* 联系方式 */}
          {(department.phone || department.email) && (
            <div className="flex flex-wrap gap-4 p-4 bg-secondary/50 rounded-xl">
              {department.phone && (
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="w-4 h-4 text-primary" />
                  <span className="text-muted-foreground">电话：</span>
                  <span className="text-foreground">{department.phone}</span>
                </div>
              )}
              {department.email && (
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="w-4 h-4 text-primary" />
                  <span className="text-muted-foreground">邮箱：</span>
                  <span className="text-foreground">{department.email}</span>
                </div>
              )}
            </div>
          )}

          {/* 专业设置 */}
          <div>
            <h3 className="font-semibold text-lg text-foreground mb-4 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary" />
              专业设置
              <span className="text-sm font-normal text-muted-foreground">（共 {department.majors.length} 个专业）</span>
            </h3>
            <div className="space-y-3">
              {department.majors.map((major, index) => (
                <MajorCard key={index} major={major} colorScheme={department.colorScheme} />
              ))}
            </div>
          </div>

          {/* 办学成果 */}
          <div>
            <h3 className="font-semibold text-lg text-foreground mb-3 flex items-center gap-2">
              <Award className="w-5 h-5 text-primary" />
              办学成果
            </h3>
            <div className="grid md:grid-cols-2 gap-2">
              {department.achievements.map((achievement, i) => (
                <div key={i} className="flex items-start gap-2 p-3 rounded-lg bg-primary/5">
                  <Star className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-foreground">{achievement}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 实训设施 */}
          <div>
            <h3 className="font-semibold text-lg text-foreground mb-3 flex items-center gap-2">
              <Building className="w-5 h-5 text-primary" />
              实训设施
            </h3>
            <div className="flex flex-wrap gap-2">
              {department.facilities.map((facility, i) => (
                <Badge key={i} variant="outline" className="px-3 py-1.5 text-sm">
                  {facility}
                </Badge>
              ))}
            </div>
          </div>
        </DialogBody>
      </DialogContent>
    </Dialog>
  )
}

// 地图导航弹窗组件
function MapNavigationDialog({
  open,
  onClose,
  campus
}: {
  open: boolean
  onClose: () => void
  campus: typeof campusLocations[0] | null
}) {
  if (!campus) return null

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent onClose={onClose} className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Navigation className="w-5 h-5 text-primary" />
            选择导航方式
          </DialogTitle>
        </DialogHeader>
        <DialogBody className="space-y-4">
          <div className="p-4 bg-secondary/50 rounded-xl">
            <h4 className="font-semibold text-foreground mb-1">{campus.name}</h4>
            <p className="text-sm text-muted-foreground flex items-center gap-1.5">
              <MapPin className="w-4 h-4" />
              {campus.address}
            </p>
            {campus.description && (
              <p className="text-xs text-muted-foreground mt-2">{campus.description}</p>
            )}
          </div>
          
          <div className="space-y-3">
            <Button 
              className="w-full h-14 text-base justify-start gap-4 bg-blue-500 hover:bg-blue-600"
              onClick={() => window.open(campus.baiduMapUrl, '_blank')}
            >
              <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
                <MapPinned className="w-5 h-5" />
              </div>
              <div className="text-left">
                <div className="font-semibold">百度地图</div>
                <div className="text-xs text-white/70">使用百度地图导航</div>
              </div>
            </Button>
            
            <Button 
              className="w-full h-14 text-base justify-start gap-4 bg-emerald-500 hover:bg-emerald-600"
              onClick={() => window.open(campus.amapUrl, '_blank')}
            >
              <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
                <Navigation className="w-5 h-5" />
              </div>
              <div className="text-left">
                <div className="font-semibold">高德地图</div>
                <div className="text-xs text-white/70">使用高德地图导航</div>
              </div>
            </Button>
          </div>
        </DialogBody>
      </DialogContent>
    </Dialog>
  )
}

export function SchoolIntro() {
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [schoolInfo, setSchoolInfo] = useState(defaultSchoolInfo)
  const [departments, setDepartments] = useState(defaultDepartments)
  const [facilities, setFacilities] = useState(defaultFacilities)
  
  // 弹窗状态
  const [selectedDepartment, setSelectedDepartment] = useState<DepartmentDetail | null>(null)
  const [departmentDialogOpen, setDepartmentDialogOpen] = useState(false)
  const [selectedCampus, setSelectedCampus] = useState<typeof campusLocations[0] | null>(null)
  const [mapDialogOpen, setMapDialogOpen] = useState(false)

  // 加载学校信息
  const loadSchoolData = async () => {
    try {
      setLoading(true)
      
      try {
        const [infoData, deptData, facilityData] = await Promise.all([
          schoolApi.getSchoolInfo(),
          schoolApi.getDepartments(),
          schoolApi.getFacilities()
        ])
        
        if (infoData) {
          setSchoolInfo({
            ...defaultSchoolInfo,
            name: infoData.name || defaultSchoolInfo.name,
            founded: infoData.founded_year ? `${infoData.founded_year}年` : defaultSchoolInfo.founded,
            type: infoData.type || defaultSchoolInfo.type,
            motto: infoData.motto || defaultSchoolInfo.motto,
            location: infoData.location || defaultSchoolInfo.location,
            website: infoData.website || defaultSchoolInfo.website,
            phone: infoData.phone || defaultSchoolInfo.phone,
            email: infoData.email || defaultSchoolInfo.email,
            description: infoData.description || defaultSchoolInfo.description,
          })
        }
        
        if (deptData && deptData.length > 0) {
          setDepartments(deptData.map(d => ({
            name: d.name,
            description: d.description || '',
            students: d.student_count || 0,
            ranking: d.ranking || '优秀'
          })))
        }
        
        if (facilityData && facilityData.length > 0) {
          setFacilities(facilityData.map(f => ({
            name: f.name,
            desc: f.description || '',
            location: f.location || '',
            time: f.open_time || ''
          })))
        }
      } catch (e) {
        console.log('使用默认学校数据')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSchoolData()
  }, [])

  // 打开院系详情
  const openDepartmentDetail = (deptName: string) => {
    const detail = departmentsData.find(d => d.name === deptName)
    if (detail) {
      setSelectedDepartment(detail)
      setDepartmentDialogOpen(true)
    }
  }

  // 打开地图导航
  const openMapNavigation = (campusName?: string) => {
    const campus = campusName 
      ? campusLocations.find(c => c.name === campusName) 
      : campusLocations[0]
    if (campus) {
      setSelectedCampus(campus)
      setMapDialogOpen(true)
    }
  }

  const tabs = [
    { id: 'overview', label: '学校概况', icon: School },
    { id: 'departments', label: '院系设置', icon: Building },
    { id: 'facilities', label: '校园设施', icon: MapPinned },
    { id: 'news', label: '校园动态', icon: BookOpen },
    { id: 'contact', label: '联系我们', icon: Phone },
  ]

  const colors = [
    'from-blue-500 to-blue-600',
    'from-emerald-500 to-emerald-600',
    'from-orange-500 to-orange-600',
    'from-purple-500 to-purple-600',
    'from-pink-500 to-pink-600',
    'from-cyan-500 to-cyan-600',
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-background via-secondary/5 to-background pt-20 pb-12">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-gradient-to-bl from-primary/8 via-primary/4 to-transparent rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-gradient-to-tr from-secondary/10 to-transparent rounded-full blur-3xl" />
        </div>
        
        <div className="max-w-6xl mx-auto px-4 py-16 relative z-10">
          <div className="flex flex-col lg:flex-row items-center gap-10">
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-primary to-primary/60 rounded-3xl blur-xl opacity-40 group-hover:opacity-60 transition-opacity" />
              <div className="relative w-36 h-36 rounded-3xl bg-gradient-to-br from-primary via-primary to-primary/80 flex items-center justify-center shadow-2xl">
                <School className="w-20 h-20 text-primary-foreground" />
              </div>
            </div>
            
            <div className="text-center lg:text-left flex-1">
              <h1 className="text-4xl lg:text-5xl font-bold mb-3 text-foreground tracking-tight">
                {schoolInfo.name}
              </h1>
              <p className="text-xl lg:text-2xl text-primary/80 font-medium mb-6 tracking-widest">
                {schoolInfo.motto}
              </p>
              <div className="flex flex-wrap justify-center lg:justify-start gap-3">
                <Badge className="gap-1.5 px-4 py-2 text-sm bg-primary/10 text-primary border-primary/20 hover:bg-primary/15">
                  <Calendar className="w-4 h-4" />
                  创建于 {schoolInfo.founded}
                </Badge>
                <Badge className="gap-1.5 px-4 py-2 text-sm bg-secondary text-secondary-foreground">
                  <MapPin className="w-4 h-4" />
                  浙江宁波
                </Badge>
                <Badge className="gap-1.5 px-4 py-2 text-sm bg-secondary text-secondary-foreground">
                  <Building className="w-4 h-4" />
                  {schoolInfo.type}
                </Badge>
                <Badge className="gap-1.5 px-4 py-2 text-sm bg-green-500/10 text-green-600 border-green-500/20">
                  <BadgeCheck className="w-4 h-4" />
                  公办院校
                </Badge>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-14">
            {schoolInfo.stats.map((stat, index) => {
              const Icon = stat.icon
              return (
                <Card 
                  key={index} 
                  className="group border-0 bg-card/60 backdrop-blur-sm hover:bg-card/80 transition-all duration-300 hover:shadow-lg hover:-translate-y-1"
                >
                  <CardContent className="p-6 text-center">
                    <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center group-hover:from-primary/20 group-hover:to-primary/10 transition-colors">
                      <Icon className="w-7 h-7 text-primary" />
                    </div>
                    <div className="text-3xl font-bold text-foreground mb-1">{stat.value}</div>
                    <div className="text-sm text-muted-foreground">{stat.label}</div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
            {features.map((feature, index) => {
              const Icon = feature.icon
              return (
                <div 
                  key={index}
                  className="flex items-center gap-3 p-4 rounded-xl bg-gradient-to-r from-primary/5 to-transparent border border-primary/10 hover:border-primary/20 transition-colors"
                >
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <div className="font-semibold text-foreground text-sm">{feature.title}</div>
                    <div className="text-xs text-muted-foreground">{feature.desc}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* 导航标签 */}
      <div className="max-w-6xl mx-auto px-4 mt-4">
        <div className="flex gap-2 p-2 bg-secondary/50 rounded-2xl overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <Button
                key={tab.id}
                variant={activeTab === tab.id ? 'default' : 'ghost'}
                className={`flex-1 min-w-max gap-2 rounded-xl transition-all ${
                  activeTab === tab.id 
                    ? 'shadow-md' 
                    : 'hover:bg-secondary'
                }`}
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </Button>
            )
          })}
        </div>

        {/* 内容区域 */}
        <div className="mt-8">
          {/* 学校概况 */}
          {activeTab === 'overview' && (
            <div className="space-y-6 animate-fade-in">
              <Card className="border-0 shadow-lg overflow-hidden">
                <div className="h-2 bg-gradient-to-r from-primary via-primary/80 to-primary/60" />
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                      <School className="w-5 h-5 text-primary" />
                    </div>
                    学校简介
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5 text-foreground/90 leading-relaxed">
                  <p>{schoolInfo.description}</p>
                  <p>
                    学校秉承百年商科办学传统，坚持"质量立校、服务兴校、管理促校、特色强校"的办学方针，
                    积极探索和实践工学结合人才培养模式，形成了"传承宁波商帮精神，培育现代商贸人才"的办学特色。
                  </p>
                  <p>
                    学校现有校本部、宁海校区、慈溪校区三个校区，占地面积894亩，设有经济管理学院、
                    数字商务学院、机电工程学院、电子信息学院、建筑与艺术学院、国际交流学院等6个二级学院，
                    开设40余个专业，在校生11400余人。
                  </p>
                  
                  <div className="pt-4 border-t border-border">
                    <h4 className="font-semibold mb-4 text-foreground">办学荣誉</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {[
                        '浙江省高水平职业院校建设单位',
                        '国家骨干高职院校优秀单位',
                        '全国职业教育先进单位',
                        '教育部现代学徒制试点单位'
                      ].map((honor, i) => (
                        <div key={i} className="flex items-center gap-2 p-3 rounded-lg bg-primary/5">
                          <Award className="w-4 h-4 text-primary flex-shrink-0" />
                          <span className="text-sm">{honor}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* 院系设置 */}
          {activeTab === 'departments' && (
            <div className="space-y-6 animate-fade-in">
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
                {departments.map((dept, index) => {
                  const Icon = departmentIcons[dept.name] || Building
                  return (
                    <Card 
                      key={index} 
                      className="group border-0 shadow-md hover:shadow-xl transition-all duration-300 hover:-translate-y-1 overflow-hidden"
                    >
                      <div className={`h-1.5 bg-gradient-to-r ${colors[index % colors.length]}`} />
                      <CardContent className="p-6">
                        <div className="flex items-start justify-between mb-4">
                          <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${colors[index % colors.length]} flex items-center justify-center shadow-lg`}>
                            <Icon className="w-7 h-7 text-white" />
                          </div>
                          <Badge variant="outline" className="text-xs font-medium">
                            {dept.ranking}
                          </Badge>
                        </div>
                        <h3 className="font-bold text-lg text-foreground mb-2">{dept.name}</h3>
                        <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                          {dept.description}
                        </p>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Users className="w-4 h-4" />
                            {dept.students.toLocaleString()} 名学生
                          </div>
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="gap-1 text-primary hover:text-primary"
                            onClick={() => openDepartmentDetail(dept.name)}
                          >
                            详情 <ChevronRight className="w-4 h-4" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>
          )}

          {/* 校园设施 */}
          {activeTab === 'facilities' && (
            <div className="grid md:grid-cols-2 gap-5 animate-fade-in">
              {facilities.map((facility, index) => {
                const Icon = facilityIcons[facility.name] || Building
                return (
                  <Card 
                    key={index} 
                    className="group border-0 shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden"
                  >
                    <CardContent className="p-6">
                      <div className="flex gap-5">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center flex-shrink-0 group-hover:from-primary/30 group-hover:to-primary/20 transition-colors">
                          <Icon className="w-8 h-8 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-bold text-lg text-foreground mb-2">{facility.name}</h3>
                          <p className="text-sm text-muted-foreground mb-3">{facility.desc}</p>
                          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                            <div className="flex items-center gap-1.5">
                              <MapPin className="w-3.5 h-3.5" />
                              {facility.location}
                            </div>
                            <div className="flex items-center gap-1.5">
                              <Clock className="w-3.5 h-3.5" />
                              {facility.time}
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}

          {/* 校园动态 */}
          {activeTab === 'news' && (
            <div className="space-y-4 animate-fade-in">
              {news.map((item, index) => (
                <Card 
                  key={index} 
                  className="border-0 shadow-md hover:shadow-lg transition-all duration-300 cursor-pointer group"
                >
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${
                              item.tag === '喜报' ? 'bg-green-500/10 text-green-600 border-green-500/20' :
                              item.tag === '荣誉' ? 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20' :
                              item.tag === '活动' ? 'bg-blue-500/10 text-blue-600 border-blue-500/20' :
                              'bg-secondary text-secondary-foreground'
                            }`}
                          >
                            {item.tag}
                          </Badge>
                          <span className="text-sm text-muted-foreground">{item.date}</span>
                        </div>
                        <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                          {item.title}
                        </h3>
                      </div>
                      <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* 联系方式 */}
          {activeTab === 'contact' && (
            <div className="grid md:grid-cols-2 gap-6 animate-fade-in">
              <Card className="border-0 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                      <Phone className="w-5 h-5 text-primary" />
                    </div>
                    联系方式
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  {[
                    { icon: Globe, label: '官方网站', value: schoolInfo.website, isLink: true },
                    { icon: Phone, label: '招生热线', value: schoolInfo.phone },
                    { icon: Mail, label: '招生邮箱', value: schoolInfo.email },
                    { icon: MapPin, label: '学校地址', value: schoolInfo.location },
                  ].map((item, i) => {
                    const Icon = item.icon
                    return (
                      <div key={i} className="flex items-start gap-4 p-4 rounded-xl bg-secondary/50 hover:bg-secondary/70 transition-colors">
                        <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                          <Icon className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground mb-1">{item.label}</p>
                          {item.isLink ? (
                            <a 
                              href={item.value} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="font-medium text-primary hover:underline flex items-center gap-1"
                            >
                              {item.value}
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          ) : (
                            <p className="font-medium text-foreground">{item.value}</p>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </CardContent>
              </Card>

              <Card className="border-0 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                      <MapPinned className="w-5 h-5 text-primary" />
                    </div>
                    校区分布
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {campusLocations.map((campus, i) => (
                    <div 
                      key={i} 
                      className="p-4 rounded-xl border border-border hover:border-primary/30 hover:bg-primary/5 transition-colors cursor-pointer"
                      onClick={() => openMapNavigation(campus.name)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-foreground">{campus.name}</h4>
                        <Badge variant="outline" className="text-xs">{campus.tag}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5" />
                        {campus.address}
                      </p>
                      {campus.description && (
                        <p className="text-xs text-muted-foreground mt-1">{campus.description}</p>
                      )}
                    </div>
                  ))}
                  
                  <Button 
                    className="w-full mt-4 gap-2" 
                    variant="outline"
                    onClick={() => openMapNavigation()}
                  >
                    <Navigation className="w-4 h-4" />
                    查看地图导航
                  </Button>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>

      {/* 弹窗组件 */}
      <DepartmentDetailDialog 
        department={selectedDepartment}
        open={departmentDialogOpen}
        onClose={() => setDepartmentDialogOpen(false)}
      />
      
      <MapNavigationDialog
        campus={selectedCampus}
        open={mapDialogOpen}
        onClose={() => setMapDialogOpen(false)}
      />
    </div>
  )
}
