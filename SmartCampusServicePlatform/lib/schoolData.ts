// 浙江工商职业技术学院 - 院系与专业完整数据

export interface Major {
  name: string
  code?: string
  duration: string
  degree: string
  description: string
  courses: string[]
  careers: string[]
  features?: string[]
}

export interface DepartmentDetail {
  id: number
  name: string
  englishName: string
  description: string
  ranking: string
  studentCount: number
  teacherCount: number
  establishedYear: number
  dean?: string
  phone?: string
  email?: string
  website?: string
  majors: Major[]
  achievements: string[]
  facilities: string[]
  colorScheme: string
}

export const departmentsData: DepartmentDetail[] = [
  {
    id: 1,
    name: '经济管理学院',
    englishName: 'School of Economics and Management',
    description: '经济管理学院是学校办学历史最悠久的学院之一，秉承"厚德载物、经世济民"的院训，致力于培养具有现代经济管理理念和实践能力的高素质技术技能人才。学院拥有省级重点专业群，与多家知名企业建立了深度产教融合关系。',
    ranking: '省级重点',
    studentCount: 2200,
    teacherCount: 85,
    establishedYear: 1999,
    phone: '0574-87422001',
    email: 'jjgl@zjbti.net.cn',
    colorScheme: 'from-blue-500 to-blue-600',
    majors: [
      {
        name: '大数据与会计',
        code: '530302',
        duration: '3年',
        degree: '专科',
        description: '培养掌握大数据技术与会计核心技能，能够运用现代信息技术进行财务数据分析、会计核算和财务管理的复合型人才。',
        courses: ['基础会计', '财务会计', '成本会计', '管理会计', '财务管理', '审计学', 'Python数据分析', '大数据财务分析', '智能财税实务', 'ERP系统应用'],
        careers: ['会计', '出纳', '财务分析师', '税务专员', '审计助理', '财务数据分析师'],
        features: ['省级特色专业', '1+X证书试点']
      },
      {
        name: '财富管理',
        code: '530205',
        duration: '3年',
        degree: '专科',
        description: '培养具备金融理财规划、投资分析、风险管理能力的专业人才，服务于银行、证券、保险等金融机构。',
        courses: ['金融学基础', '证券投资', '保险理论与实务', '个人理财规划', '基金投资', '风险管理', '金融营销', '财富管理综合实训'],
        careers: ['理财顾问', '投资顾问', '银行客户经理', '保险规划师', '基金销售'],
        features: ['校企合作订单班']
      },
      {
        name: '金融服务与管理',
        code: '530201',
        duration: '3年',
        degree: '专科',
        description: '面向银行、证券、保险等金融机构，培养具备金融服务技能和管理能力的应用型人才。',
        courses: ['货币银行学', '商业银行业务', '证券交易', '保险实务', '金融法规', '客户关系管理', '金融科技应用'],
        careers: ['银行柜员', '信贷专员', '证券经纪人', '保险代理人', '金融产品销售'],
        features: ['现代学徒制试点']
      },
      {
        name: '社会工作',
        code: '590101',
        duration: '3年',
        degree: '专科',
        description: '培养具有社会工作专业价值观、知识和技能，能在民政、社区、公益组织等领域从事社会服务的专业人才。',
        courses: ['社会工作概论', '社会学基础', '心理学基础', '个案工作', '小组工作', '社区工作', '社会调查方法', '社会保障'],
        careers: ['社工', '社区工作者', '公益项目专员', '养老服务管理', '青少年事务社工'],
        features: ['服务宁波地方经济']
      }
    ],
    achievements: [
      '浙江省高职院校技能大赛会计赛项一等奖',
      '全国金融职业技能大赛二等奖',
      '省级精品在线开放课程3门',
      '校企合作省级示范基地'
    ],
    facilities: ['会计信息化实训室', '金融模拟交易中心', 'ERP综合实训室', '财税一体化实训室']
  },
  {
    id: 2,
    name: '数字商务学院',
    englishName: 'School of Digital Commerce',
    description: '数字商务学院紧跟数字经济发展趋势，以电子商务和跨境电商为核心，培养适应新商业模式的创新创业型人才。学院建有省级电商产教融合基地，与阿里巴巴、京东等头部企业深度合作。',
    ranking: '省级特色',
    studentCount: 2500,
    teacherCount: 92,
    establishedYear: 2005,
    phone: '0574-87422002',
    email: 'szsw@zjbti.net.cn',
    colorScheme: 'from-emerald-500 to-emerald-600',
    majors: [
      {
        name: '电子商务',
        code: '530701',
        duration: '3年',
        degree: '专科',
        description: '培养掌握电子商务运营、网络营销、数据分析等核心技能，能够从事电商平台运营和数字化营销的高素质人才。',
        courses: ['电子商务概论', '网络营销', '网店运营', '电商数据分析', '视觉设计', '直播电商', '客户服务管理', '电商创业实践'],
        careers: ['电商运营专员', '网络营销师', '直播运营', '数据分析师', '电商创业者'],
        features: ['国家骨干专业', '省级优势专业']
      },
      {
        name: '跨境电子商务',
        code: '530702',
        duration: '3年',
        degree: '专科',
        description: '面向全球市场，培养具备跨境电商平台操作、国际贸易实务、跨文化沟通能力的复合型外贸电商人才。',
        courses: ['跨境电商概论', '国际贸易实务', '跨境平台操作', '外贸英语', '跨境物流', '海外营销', '跨境支付与结算', 'B2B/B2C实训'],
        careers: ['跨境电商运营', '外贸业务员', '海外市场专员', '跨境物流专员', '平台店铺管理'],
        features: ['省级特色专业', '阿里巴巴产教融合基地']
      },
      {
        name: '市场营销',
        code: '530605',
        duration: '3年',
        degree: '专科',
        description: '培养具备市场调研、营销策划、销售管理能力的应用型营销人才，适应数字化营销新时代需求。',
        courses: ['市场营销学', '消费者行为学', '市场调查', '广告策划', '销售管理', '品牌管理', '新媒体营销', '营销策划实训'],
        careers: ['营销专员', '市场调研员', '品牌策划', '销售代表', '新媒体运营'],
        features: ['实战导向教学']
      },
      {
        name: '国际经济与贸易',
        code: '530501',
        duration: '3年',
        degree: '专科',
        description: '培养熟悉国际贸易规则，掌握进出口业务操作流程的外贸专业人才，服务宁波外向型经济发展。',
        courses: ['国际贸易理论', '国际贸易实务', '外贸单证', '报关报检', '国际结算', '外贸函电', '国际商法', '跨境电商'],
        careers: ['外贸业务员', '单证员', '报关员', '跟单员', '国际采购'],
        features: ['宁波商帮传承专业']
      },
      {
        name: '商务数据分析与应用',
        code: '530706',
        duration: '3年',
        degree: '专科',
        description: '培养能够运用数据分析工具和方法，为企业商务决策提供数据支持的专业分析人才。',
        courses: ['统计学基础', 'Python编程', '数据可视化', '商务数据分析', '数据库应用', '机器学习基础', '商业智能', '数据分析项目实战'],
        careers: ['数据分析师', '商业分析师', 'BI工程师', '运营数据分析', '市场数据分析'],
        features: ['新兴热门专业']
      }
    ],
    achievements: [
      '全国职业院校技能大赛电子商务赛项一等奖',
      '浙江省"互联网+"大学生创新创业大赛金奖',
      '阿里巴巴全球速卖通人才培养基地',
      '省级创新创业教育示范基地'
    ],
    facilities: ['电商直播基地', '跨境电商实训中心', '大数据分析实验室', '创业孵化园', '新媒体工作室']
  },
  {
    id: 3,
    name: '机电工程学院',
    englishName: 'School of Mechanical and Electrical Engineering',
    description: '机电工程学院是学校工科类主体学院，面向智能制造产业，培养掌握先进制造技术的高素质技术技能人才。学院拥有国家级实训基地，与吉利、方太等知名企业建立了产教融合联盟。',
    ranking: '省级重点',
    studentCount: 1800,
    teacherCount: 78,
    establishedYear: 1998,
    phone: '0574-87422003',
    email: 'jdgc@zjbti.net.cn',
    colorScheme: 'from-orange-500 to-orange-600',
    majors: [
      {
        name: '机电一体化技术',
        code: '460301',
        duration: '3年',
        degree: '专科',
        description: '培养掌握机械、电气、控制等综合技术，能从事自动化设备安装调试、运行维护的复合型技术人才。',
        courses: ['机械制图', '电工电子技术', '机械设计基础', 'PLC编程', '液压与气动', '传感器技术', '自动化生产线', '工业机器人基础'],
        careers: ['设备维护工程师', '自动化技术员', '电气工程师', '生产技术员', '售后服务工程师'],
        features: ['国家骨干专业', '现代学徒制']
      },
      {
        name: '数控技术',
        code: '460103',
        duration: '3年',
        degree: '专科',
        description: '培养精通数控机床操作、编程和维护的高技能人才，服务于精密制造和智能加工领域。',
        courses: ['机械制图与CAD', '数控加工工艺', '数控编程', 'UG/Mastercam', '数控机床结构', '精密测量技术', '多轴加工技术'],
        careers: ['数控操作员', '数控编程员', '工艺工程师', '品质检验员', 'CAM工程师'],
        features: ['省级示范专业']
      },
      {
        name: '工业设计',
        code: '460105',
        duration: '3年',
        degree: '专科',
        description: '培养具备产品设计创意和工程实现能力的设计人才，融合艺术审美与工程技术。',
        courses: ['设计素描', '产品设计原理', '三维建模', '人机工程学', '材料与工艺', '产品渲染', '模型制作', '设计项目实践'],
        careers: ['产品设计师', '结构设计师', '3D建模师', '设计助理', '创意设计师'],
        features: ['艺工结合特色']
      },
      {
        name: '模具设计与制造',
        code: '460113',
        duration: '3年',
        degree: '专科',
        description: '培养掌握模具设计、制造和管理的专业人才，服务于汽车、家电等制造业核心领域。',
        courses: ['模具制图', '塑料模具设计', '冲压模具设计', '模具CAD/CAM', '模具制造工艺', '模具材料', '注塑成型技术'],
        careers: ['模具设计师', '模具工程师', 'CAD/CAM工程师', '模具项目管理', '技术支持'],
        features: ['宁波模具之都支撑专业']
      },
      {
        name: '工业机器人技术',
        code: '460305',
        duration: '3年',
        degree: '专科',
        description: '面向智能制造，培养能够从事工业机器人编程、调试和系统集成的高端技术人才。',
        courses: ['机器人技术基础', '机器人编程', '机器人视觉', 'PLC控制技术', '机器人系统集成', '智能产线技术', '机器人维护保养'],
        careers: ['机器人编程工程师', '系统集成工程师', '自动化工程师', '技术支持工程师', '项目工程师'],
        features: ['新兴战略专业', '校企共建专业']
      }
    ],
    achievements: [
      '全国职业院校技能大赛机器人赛项一等奖',
      '浙江省机械设计创新大赛特等奖',
      '国家级生产性实训基地',
      '吉利汽车产业学院共建单位'
    ],
    facilities: ['智能制造实训中心', '数控加工中心', '工业机器人实训室', '3D打印创新中心', 'CAD/CAM实验室']
  },
  {
    id: 4,
    name: '电子信息学院',
    englishName: 'School of Electronic Information',
    description: '电子信息学院聚焦信息技术产业，以计算机、软件、人工智能为核心，培养适应数字经济发展需求的IT技术人才。学院与华为、科大讯飞等企业深度合作，共建产业学院。',
    ranking: '省级特色',
    studentCount: 2100,
    teacherCount: 88,
    establishedYear: 2002,
    phone: '0574-87422004',
    email: 'dzxx@zjbti.net.cn',
    colorScheme: 'from-purple-500 to-purple-600',
    majors: [
      {
        name: '计算机应用技术',
        code: '510201',
        duration: '3年',
        degree: '专科',
        description: '培养具备计算机软硬件应用开发能力的技术人才，能够从事程序开发、系统维护等工作。',
        courses: ['C语言程序设计', 'Java程序设计', '数据库技术', '计算机网络', 'Web前端开发', 'Linux系统', '软件工程', '项目实战开发'],
        careers: ['软件开发工程师', '前端开发工程师', '系统运维工程师', '技术支持', '测试工程师'],
        features: ['省级优势专业']
      },
      {
        name: '软件技术',
        code: '510203',
        duration: '3年',
        degree: '专科',
        description: '专注于软件开发全流程，培养能够进行软件设计、编码、测试的专业开发人才。',
        courses: ['Java开发', 'Python编程', '数据结构', '数据库开发', 'Spring框架', '微服务架构', '移动应用开发', '软件测试'],
        careers: ['Java开发工程师', 'Python开发工程师', '全栈开发工程师', '软件测试工程师', '技术经理'],
        features: ['华为ICT学院']
      },
      {
        name: '人工智能技术应用',
        code: '510209',
        duration: '3年',
        degree: '专科',
        description: '面向AI产业，培养掌握机器学习、深度学习等技术，能够从事智能系统开发的新型人才。',
        courses: ['Python编程', '机器学习', '深度学习', '计算机视觉', '自然语言处理', '数据挖掘', 'TensorFlow/PyTorch', 'AI项目实战'],
        careers: ['AI算法工程师', '数据工程师', '机器学习工程师', 'AI应用开发', '智能产品经理'],
        features: ['新兴前沿专业', '科大讯飞共建']
      },
      {
        name: '计算机网络技术',
        code: '510202',
        duration: '3年',
        degree: '专科',
        description: '培养掌握网络规划、建设和安全管理的专业人才，服务于企业网络基础设施建设。',
        courses: ['计算机网络基础', '路由交换技术', '网络安全', 'Linux服务器', '云计算技术', '网络运维', '信息安全', '网络工程实训'],
        careers: ['网络工程师', '网络运维工程师', '安全工程师', '云计算工程师', '系统管理员'],
        features: ['华为认证培训点']
      },
      {
        name: '数字媒体技术',
        code: '510204',
        duration: '3年',
        degree: '专科',
        description: '融合艺术与技术，培养能够从事数字内容制作、交互设计的创意技术人才。',
        courses: ['数字图像处理', '视频编辑', '三维动画', 'UI/UX设计', '交互设计', '虚拟现实技术', '游戏开发基础', '数字媒体项目'],
        careers: ['UI设计师', '视频剪辑师', '动画设计师', '交互设计师', '新媒体制作'],
        features: ['创意设计特色']
      }
    ],
    achievements: [
      '全国职业院校技能大赛软件赛项一等奖',
      '蓝桥杯全国软件大赛一等奖',
      '华为ICT技能大赛全国总决赛二等奖',
      '省级精品资源共享课程5门'
    ],
    facilities: ['华为ICT实训中心', '人工智能创新实验室', '软件开发实训室', '网络安全攻防实验室', 'VR/AR体验中心']
  },
  {
    id: 5,
    name: '建筑与艺术学院',
    englishName: 'School of Architecture and Art',
    description: '建筑与艺术学院融合工程技术与艺术设计，培养具有创新精神和实践能力的建筑与设计人才。学院拥有省级艺术设计实训基地，与多家设计院和建筑企业建立了稳定的校企合作关系。',
    ranking: '校级重点',
    studentCount: 1600,
    teacherCount: 65,
    establishedYear: 2006,
    phone: '0574-87422005',
    email: 'jzys@zjbti.net.cn',
    colorScheme: 'from-pink-500 to-pink-600',
    majors: [
      {
        name: '建筑工程技术',
        code: '440301',
        duration: '3年',
        degree: '专科',
        description: '培养掌握建筑施工技术和工程管理能力的专业人才，服务于建筑行业转型升级。',
        courses: ['建筑制图', '建筑材料', '建筑力学', '建筑构造', '施工技术', 'BIM技术', '工程测量', '施工组织管理'],
        careers: ['施工员', '质检员', '安全员', 'BIM工程师', '项目管理员'],
        features: ['BIM技术特色']
      },
      {
        name: '工程造价',
        code: '440501',
        duration: '3年',
        degree: '专科',
        description: '培养精通工程计量计价、成本控制的专业人才，是建筑行业核心岗位之一。',
        courses: ['建筑制图', '建筑材料', '建筑构造', '工程计量', '工程计价', '招投标管理', '造价软件应用', '工程结算'],
        careers: ['造价员', '预算员', '投标专员', '成本工程师', '审计专员'],
        features: ['省级特色专业', '就业率高']
      },
      {
        name: '环境艺术设计',
        code: '550106',
        duration: '3年',
        degree: '专科',
        description: '培养具备室内外环境设计能力的创意设计人才，融合空间美学与实用功能。',
        courses: ['设计素描与色彩', '室内设计原理', '景观设计', 'CAD制图', '3Dmax效果图', '材料与施工工艺', '软装设计', '设计项目实践'],
        careers: ['室内设计师', '软装设计师', '景观设计师', '效果图设计师', '设计助理'],
        features: ['艺术与工程结合']
      },
      {
        name: '广告艺术设计',
        code: '550113',
        duration: '3年',
        degree: '专科',
        description: '培养掌握视觉传达设计、品牌策划能力的创意设计人才，服务于广告和品牌传播行业。',
        courses: ['设计基础', '字体设计', '版式设计', 'VI设计', '广告策划', '包装设计', 'PS/AI软件', '品牌设计项目'],
        careers: ['平面设计师', '品牌设计师', '广告设计师', '包装设计师', '视觉设计师'],
        features: ['创意产业对接']
      },
      {
        name: '影视动画',
        code: '560206',
        duration: '3年',
        degree: '专科',
        description: '培养具备动画创作、影视后期制作能力的创意人才，对接数字娱乐产业发展需求。',
        courses: ['动画原理', '角色设计', '场景设计', '二维动画', '三维动画', '影视后期', '特效制作', '动画项目创作'],
        careers: ['动画设计师', '原画师', '后期制作师', '特效师', '游戏美术'],
        features: ['产教融合特色']
      }
    ],
    achievements: [
      '全国高职院校建筑技能大赛二等奖',
      '浙江省大学生艺术设计大赛金奖',
      '省级艺术设计实训基地',
      'BIM技术应用创新中心'
    ],
    facilities: ['建筑BIM实训室', '装饰材料展示中心', '环艺设计工作室', '动画制作实训室', '摄影棚']
  },
  {
    id: 6,
    name: '国际交流学院',
    englishName: 'School of International Exchange',
    description: '国际交流学院致力于培养具有国际视野和跨文化交流能力的外语和旅游人才。学院与多所海外院校建立了合作关系，为学生提供海外交流和专升本通道。',
    ranking: '校级特色',
    studentCount: 1200,
    teacherCount: 52,
    establishedYear: 2008,
    phone: '0574-87422006',
    email: 'gjjl@zjbti.net.cn',
    colorScheme: 'from-cyan-500 to-cyan-600',
    majors: [
      {
        name: '应用英语',
        code: '570202',
        duration: '3年',
        degree: '专科',
        description: '培养具有扎实英语语言能力和商务沟通技能的应用型外语人才，服务于外向型经济发展。',
        courses: ['综合英语', '英语听说', '商务英语', '英语写作', '翻译理论与实践', '跨文化交际', '外贸英语函电', '商务谈判'],
        careers: ['外贸业务员', '商务翻译', '英语教师', '涉外文秘', '跨境电商'],
        features: ['小班化教学', '外教授课']
      },
      {
        name: '旅游管理',
        code: '540101',
        duration: '3年',
        degree: '专科',
        description: '培养具备旅游服务与管理能力的专业人才，适应现代旅游业智慧化发展需求。',
        courses: ['旅游学概论', '导游业务', '旅行社经营管理', '酒店管理', '旅游市场营销', '智慧旅游', '旅游英语', '旅游线路设计'],
        careers: ['导游', '旅行社计调', '酒店管理', '景区管理', '旅游电商运营'],
        features: ['省级示范专业']
      },
      {
        name: '休闲服务与管理',
        code: '540113',
        duration: '3年',
        degree: '专科',
        description: '面向休闲产业，培养能够从事健康休闲、运动康养服务与管理的专业人才。',
        courses: ['休闲学概论', '康养服务', '运动健康管理', '休闲活动策划', '客户服务', '休闲产业经营', '高尔夫服务'],
        careers: ['休闲会所管理', '康养服务专员', '运动指导员', '俱乐部运营', '活动策划'],
        features: ['健康产业新专业']
      },
      {
        name: '研学旅行管理与服务',
        code: '540104',
        duration: '3年',
        degree: '专科',
        description: '培养能够从事研学旅行课程设计、带队服务的专业人才，服务教育旅游新业态。',
        courses: ['研学旅行概论', '课程设计', '安全管理', '带队技巧', '教育学基础', '心理学基础', '户外拓展', '研学项目开发'],
        careers: ['研学导师', '课程设计师', '研学基地运营', '教育旅游策划', '户外教育指导'],
        features: ['新兴特色专业']
      }
    ],
    achievements: [
      '全国高职院校英语口语大赛一等奖',
      '浙江省导游技能大赛金奖',
      '海外合作院校10余所',
      '国际化办学示范学院'
    ],
    facilities: ['语言实训中心', '同声传译实训室', '模拟导游实训室', '酒店实训中心', '茶艺咖啡实训室']
  }
]

// 校区地理位置信息
export const campusLocations = [
  {
    name: '校本部',
    address: '浙江省宁波市海曙区机场路1988号',
    tag: '主校区',
    coordinates: { lat: 29.8683, lng: 121.5440 },
    description: '学校主校区，设有主要教学楼、图书馆、行政楼等',
    baiduMapUrl: 'https://map.baidu.com/search/浙江工商职业技术学院/@13514661.91,3519271.76,17z',
    amapUrl: 'https://www.amap.com/search?query=浙江工商职业技术学院&city=330200'
  },
  {
    name: '宁海校区',
    address: '浙江省宁波市宁海县',
    tag: '分校区',
    coordinates: { lat: 29.2878, lng: 121.4294 },
    description: '产教融合基地，与宁海模具产业深度合作',
    baiduMapUrl: 'https://map.baidu.com/search/浙江工商职业技术学院宁海校区/@13502689.91,3451371.76,17z',
    amapUrl: 'https://www.amap.com/search?query=浙江工商职业技术学院宁海校区&city=330200'
  },
  {
    name: '慈溪校区',
    address: '浙江省宁波市慈溪市',
    tag: '分校区',
    coordinates: { lat: 30.1699, lng: 121.2664 },
    description: '服务慈溪地方经济，开展特色专业培养',
    baiduMapUrl: 'https://map.baidu.com/search/浙江工商职业技术学院慈溪校区/@13495689.91,3551371.76,17z',
    amapUrl: 'https://www.amap.com/search?query=浙江工商职业技术学院慈溪校区&city=330200'
  }
]
