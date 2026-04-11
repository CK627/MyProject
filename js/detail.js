/* ============================================
   详情页脚本
   ============================================ */

// 获取 URL 参数
function getUrlParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    type: params.get('type'),  // scenic, food, route, culture
    id: parseInt(params.get('id'), 10)
  };
}

// 根据类型获取数据源
function getDataSource(type) {
  const sources = {
    scenic: [...SITE_DATA.scenic.nature, ...SITE_DATA.scenic.culture],
    food: [...SITE_DATA.food.snacks, ...SITE_DATA.food.dishes],
    route: [...SITE_DATA.routes.oneDay, ...SITE_DATA.routes.deep],
    culture: [...SITE_DATA.culture.festivals, ...SITE_DATA.culture.crafts]
  };
  return sources[type] || [];
}

// 获取返回链接
function getBackUrl(type) {
  const urls = {
    scenic: 'scenic.html',
    food: 'food.html',
    route: 'route.html',
    culture: 'culture.html'
  };
  return urls[type] || 'index.html';
}

// 获取类型中文名
function getTypeName(type) {
  const names = {
    scenic: '景点',
    food: '美食',
    route: '线路',
    culture: '民俗'
  };
  return names[type] || '详情';
}

const app = createPageApp({
  data() {
    return {
      item: null,
      error: null,
      type: null,
      currentImageIndex: 0,
      relatedItems: []
    };
  },
  computed: {
    currentImage() {
      if (!this.item) return '';
      if (this.item.gallery && this.item.gallery.length) {
        return this.item.gallery[this.currentImageIndex];
      }
      return this.item.img;
    },
    backUrl() {
      return getBackUrl(this.type);
    }
  },
  methods: {
    formatContent(text) {
      if (!text) return '';
      // 将换行符转为段落
      return text.split('\n').filter(p => p.trim()).map(p => `<p>${p}</p>`).join('');
    },
    goDetail(item) {
      window.location.href = `detail.html?type=${this.type}&id=${item.id}`;
    },
    loadData() {
      const { type, id } = getUrlParams();
      this.type = type;

      if (!type || !id) {
        this.error = '缺少必要参数';
        return;
      }

      const dataSource = getDataSource(type);
      const item = dataSource.find(d => d.id === id);

      if (!item) {
        this.error = '未找到该内容';
        return;
      }

      this.item = item;
      
      // 更新页面标题
      document.title = `${item.name} - ${getTypeName(type)} - 衢江文化旅游信息平台`;

      // 获取相关推荐（同类型其他内容，最多4个）
      this.relatedItems = dataSource
        .filter(d => d.id !== id)
        .slice(0, 4);
    }
  },
  mounted() {
    this.loadData();
    this.$nextTick(() => {
      commonInit();
    });
  }
});

app.mount('#app');
