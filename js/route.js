const app = createPageApp({
  data() {
    return {
      activeTab: 'all',
      oneDay: SITE_DATA.routes.oneDay,
      deep: SITE_DATA.routes.deep
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

function applyHashRoute() {
  const hash = window.location.hash;
  if (hash === '#oneday') vm.activeTab = 'oneday';
  else if (hash === '#deep') vm.activeTab = 'deep';
}
applyHashRoute();
window.addEventListener('hashchange', applyHashRoute);
