const app = createPageApp({
  data() {
    return {
      activeTab: 'all',
      nature: SITE_DATA.scenic.nature,
      culture: SITE_DATA.scenic.culture
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

// 监听 hash 变化（同页面导航）
function applyHashScenic() {
  const hash = window.location.hash;
  if (hash === '#nature') vm.activeTab = 'nature';
  else if (hash === '#culture') vm.activeTab = 'culture';
}
// 挂载到 vm 实例方法
vm._applyHash = applyHashScenic;
// 首次执行
applyHashScenic();
// 监听后续 hash 变化
window.addEventListener('hashchange', applyHashScenic);
