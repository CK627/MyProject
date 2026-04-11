/* ============================================
   首页脚本
   ============================================ */

const app = createPageApp({
  data() {
    return {
      currentSlide: 0,
      slides: SITE_DATA.carousel,
      slideTimer: null,
      features: [
        { icon: '🏔️', title: '山水风光', desc: '青山绿水间，感受自然的宁静与壮美' },
        { icon: '🏛️', title: '人文古迹', desc: '千年历史沉淀，品读古村古镇的悠远故事' },
        { icon: '🍜', title: '地道美食', desc: '三头一掌、烤饼飘香，味蕾的浙西之旅' },
        { icon: '🎭', title: '民俗文化', desc: '非遗传承，体验原汁原味的衢江民间智慧' }
      ],
      featuredScenic: [
        ...SITE_DATA.scenic.nature.slice(0, 2),
        ...SITE_DATA.scenic.culture.slice(0, 2)
      ],
      featuredFood: [
        ...SITE_DATA.food.snacks.slice(0, 2),
        ...SITE_DATA.food.dishes.slice(0, 2)
      ],
      featuredCulture: [
        ...SITE_DATA.culture.festivals.slice(0, 2),
        ...SITE_DATA.culture.crafts.slice(0, 1)
      ]
    };
  },
  mounted() {
    commonInit();
    this.startAutoPlay();
  },
  beforeUnmount() {
    this.stopAutoPlay();
  },
  methods: {
    goSlide(i) {
      this.currentSlide = i;
      this.resetAutoPlay();
    },
    nextSlide() {
      this.currentSlide = (this.currentSlide + 1) % this.slides.length;
      this.resetAutoPlay();
    },
    prevSlide() {
      this.currentSlide = (this.currentSlide - 1 + this.slides.length) % this.slides.length;
      this.resetAutoPlay();
    },
    startAutoPlay() {
      this.slideTimer = setInterval(() => {
        this.currentSlide = (this.currentSlide + 1) % this.slides.length;
      }, 5000);
    },
    stopAutoPlay() {
      clearInterval(this.slideTimer);
    },
    resetAutoPlay() {
      this.stopAutoPlay();
      this.startAutoPlay();
    }
  }
});

app.mount('#app');
