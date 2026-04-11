const app = createPageApp({
  data() {
    return {
      activeTab: 'all',
      festivals: SITE_DATA.culture.festivals,
      crafts: SITE_DATA.culture.crafts
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

function applyHashCulture() {
  const hash = window.location.hash;
  if (hash === '#festivals') vm.activeTab = 'festivals';
  else if (hash === '#crafts') vm.activeTab = 'crafts';
}
applyHashCulture();
window.addEventListener('hashchange', applyHashCulture);
