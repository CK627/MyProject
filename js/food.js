const app = createPageApp({
  data() {
    return {
      activeTab: 'all',
      snacks: SITE_DATA.food.snacks,
      dishes: SITE_DATA.food.dishes
    };
  },
  watch: {
    activeTab() {
      this.$nextTick(() => initLazyLoad());
    }
  },
  mounted() {
    commonInit();
  }
});

const vm = app.mount('#app');

function applyHashFood() {
  const hash = window.location.hash;
  if (hash === '#snacks') vm.activeTab = 'snacks';
  else if (hash === '#dishes') vm.activeTab = 'dishes';
}
applyHashFood();
window.addEventListener('hashchange', applyHashFood);
