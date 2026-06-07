/**
 * 教师管理页面 - 核心模块
 * 包含：初始化、导航、统计图表
 * 
 * 依赖: js/index.js (公共库), js/vue.global.js
 * 被依赖: teacher-class.js, teacher-filestat.js, teacher-filemanage.js
 */

const { createApp, ref, nextTick, reactive } = Vue;

let vueFetchData = null;
let globalProjects = [];

const statsApp = createApp({
  setup() {
    const cards = ref([
      { key: 'total', icon: '👥', title: '总人数', desc: '毕业库中的用户表数量', value: 0 }
    ]);

    const charts = ref([]);

    const initDynamicProjects = () => {
      // Rebuild cards
      const newCards = [
        { key: 'total', icon: '👥', title: '总人数', desc: '毕业库中的用户表数量', value: 0 }
      ];
      const newCharts = [];
      const icons = ['📦','📄','📝','🏠','👨‍👩‍👧‍👦','🤝','📋','📊','📜','💳','🛡️','📝','📊'];
      
      globalProjects.forEach((p, index) => {
        newCards.push({
          key: p.type_key,
          icon: icons[index % icons.length],
          title: p.name + '提交',
          desc: p.name + '提交人数',
          value: '0'
        });
        newCharts.push({
          id: 'chart-' + p.type_key,
          title: p.name + '提交饼图（已提交/未提交）',
          key: p.type_key + '_users'
        });
      });
      
      cards.value = newCards;
      charts.value = newCharts;
    };

    const fetchData = async () => {
      try {
        const res = await fetch('/api/teacher_stats.php', { method: 'GET', credentials: 'include' });
        const data = res.ok ? await res.json() : null;
        if (!res.ok || !data || !data.ok) return;
        
        const sum = data.summary || {};
        const total = Number(sum.total_users || 0);

        // Update cards
        cards.value[0].value = total;
        
        for (let i = 1; i < cards.value.length; i++) {
          const card = cards.value[i];
          const count = sum[card.key + '_users'] || 0;
          card.value = `${count}/${total}`;
        }

        // Draw charts
        await nextTick();
        charts.value.forEach(chart => {
          const submitted = Number(sum[chart.key] || 0);
          const pending = Math.max(0, total - submitted);
          const canvas = document.getElementById(chart.id);
          if (canvas) {
            drawPieChart(canvas, { '已提交': submitted, '未提交': pending });
          }
        });
      } catch (e) {
        console.error(e);
      }
    };

    return { cards, charts, fetchData, initDynamicProjects };
  }
});

function setChip(adm) {
  const chip = document.getElementById('admin-chip');
  if (!chip) return;
  chip.textContent = adm ? `教师：${String(adm.username||'')}` : '未登录';
}

function initSidebar(adm) {
  const btns = Array.from(document.querySelectorAll('.nav-item'));
  const panels = Array.from(document.querySelectorAll('.panel'));
  const setActive = (target) => {
    btns.forEach(b => b.classList.toggle('active', b.dataset.target === target));
    panels.forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(`${target}-section`);
    if (panel) panel.classList.add('active');
    
    // Toggle sub-navs
    document.querySelectorAll('.sub-nav').forEach(sn => sn.classList.remove('open'));
    if (target === 'filestat') {
      const subFilestat = document.getElementById('filestat-subnav');
      if (subFilestat) subFilestat.classList.add('open');
    }
    if (target === 'settings') {
      const subSettings = document.getElementById('settings-subnav');
      if (subSettings) subSettings.classList.add('open');
    }
    
    if (target === 'stats') { loadStats(adm); }
    if (target === 'class') { initClassManage(adm); }
    if (target === 'filestat') { initFileStat(adm); }
    if (target === 'filemanage') { initFileManage(adm); }
    if (target === 'settings') { initSettings(adm); }
  };
  btns.forEach(b => b.addEventListener('click', () => setActive(b.dataset.target)));
}

function loadStats(adm) {
  if (vueFetchData) vueFetchData();
}

function initLogout() {
  const btn = document.getElementById('btn-admin-logout');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    await logout();
    location.href = 'index.html';
  });
}

async function fetchProjects() {
  try {
    const res = await fetch('/api/config_projects.php', { method: 'GET', credentials: 'include' });
    const data = res.ok ? await res.json() : null;
    if (data && data.ok) {
      globalProjects = data.items || [];
      // Update FILE_TYPE_NAMES globally so other scripts can use it
      window.FILE_TYPE_NAMES = {};
      globalProjects.forEach(p => {
        window.FILE_TYPE_NAMES[p.type_key] = p.name;
      });
      // Update sidebar
      const subnav = document.getElementById('filestat-subnav');
      if (subnav) {
        subnav.innerHTML = '';
        globalProjects.forEach((p, i) => {
          const btn = document.createElement('button');
          btn.className = 'sub-nav-item' + (i === 0 ? ' active' : '');
          btn.setAttribute('data-sub', p.type_key);
          btn.type = 'button';
          btn.textContent = p.name;
          subnav.appendChild(btn);
        });
      }
    }
  } catch (e) {
    console.error('Failed to fetch projects', e);
  }
}

async function init() {
  // 优先检查 Session 认证
  let adm = null;
  try {
    const session = await checkSession();
    if (session.loggedIn && session.user && session.user.role === 'admin') {
      adm = {
        username: session.user.username,
        userId: session.user.userId,
        role: session.user.role,
        class: session.user.class || ''  // 获取班级信息
      };
      try { localStorage.setItem('currentAdmin', JSON.stringify(adm)); } catch (e) {}
    }
  } catch (e) { console.warn('[Session Check Failed]', e); }
  
  // 回退到 localStorage
  if (!adm) { adm = getAdmin(); }
  
  if (!adm) { location.href = 'index.html'; return; }
  
  await fetchProjects();
  
  setChip(adm);
  initSidebar(adm);
  
  // Mount Vue App
  const instance = statsApp.mount('#stats-app');
  vueFetchData = instance.fetchData;
  if (instance.initDynamicProjects) instance.initDynamicProjects();
  
  // Initial load
  loadStats(adm);
  
  initEditModal();
  initAddModal();
  initLogout();
  initChangePassword();
  
  // 启动 Session 监控 (每30秒检查一次)
  startSessionMonitor(30000);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else { init(); }

// ===== 图表相关 =====

function drawLineChart() {}

function drawPieChart(canvas, types) {
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0,0,W,H);
  const keys = Object.keys(types || {});
  const total = keys.reduce((s,k)=> s + (types[k]||0), 0);
  if (total === 0) return;
  const cx = W/2, cy = H/2, r = Math.min(W,H)/2 - 20;
  const palette = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#22d3ee','#64748b'];
  let start = -Math.PI/2;
  const segments = [];
  keys.forEach((k, i) => {
    const val = types[k] || 0;
    const ang = (val / total) * Math.PI * 2;
    const a0 = start;
    const a1 = start + ang;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    const col = k === '已提交' ? '#10b981' : (k === '未提交' ? '#ef4444' : palette[i % palette.length]);
    ctx.fillStyle = col;
    ctx.arc(cx, cy, r, a0, a1);
    ctx.closePath();
    ctx.fill();
    segments.push({ label:k, value:val, a0, a1, color: ctx.fillStyle });
    start = a1;
  });
  enablePieTooltip(canvas, segments, cx, cy, r, total);
}

function getTipEl() {
  let tip = document.getElementById('chart-tooltip');
  if (!tip) { tip = document.createElement('div'); tip.id = 'chart-tooltip'; tip.className = 'chart-tooltip'; document.body.appendChild(tip); }
  return tip;
}

function enablePieTooltip(canvas, segments, cx, cy, r, total) {
  const tip = getTipEl();
  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const dx = x - cx;
    const dy = y - cy;
    const dist = Math.sqrt(dx*dx + dy*dy);
    if (dist > r) { tip.style.display = 'none'; return; }
    let ang = Math.atan2(dy, dx);
    if (ang < -Math.PI/2) ang += Math.PI*2;
    let hit = null;
    for (const seg of segments) { if (ang >= seg.a0 && ang <= seg.a1) { hit = seg; break; } }
    if (!hit) { tip.style.display = 'none'; return; }
    const pct = total > 0 ? Math.round((hit.value / total) * 1000) / 10 : 0;
    tip.textContent = `${hit.label}: ${hit.value} (${pct}%)`;
    tip.style.left = `${e.clientX + 12}px`;
    tip.style.top = `${e.clientY + 12}px`;
    tip.style.display = 'block';
  };
  canvas.onmouseleave = () => { tip.style.display = 'none'; };
}

function initChangePassword() {
  const btn = document.getElementById('btn-admin-pwd');
  const modal = document.getElementById('pwd-modal');
  const btnSave = document.getElementById('pm-save');
  const btnCancel = document.getElementById('pm-cancel');
  
  if (!btn || !modal) return;
  
  const close = () => {
    modal.classList.remove('active');
    document.getElementById('pm-old').value = '';
    document.getElementById('pm-new').value = '';
    document.getElementById('pm-confirm').value = '';
  };
  
  btn.addEventListener('click', () => {
    modal.classList.add('active');
  });
  
  btnCancel.addEventListener('click', close);
  
  btnSave.addEventListener('click', async () => {
    const oldPass = document.getElementById('pm-old').value.trim();
    const newPass = document.getElementById('pm-new').value.trim();
    const confirmPass = document.getElementById('pm-confirm').value.trim();
    
    if (!oldPass || !newPass) {
      alert('请输入密码');
      return;
    }
    if (newPass.length < 6) {
      alert('新密码长度至少 6 位');
      return;
    }
    if (newPass !== confirmPass) {
      alert('两次输入的新密码不一致');
      return;
    }
    
    const adm = getAdmin(); // From index.js or localStorage
    if (!adm || !adm.username) {
      alert('未登录');
      return;
    }
    
    try {
      const res = await fetch('/api/admin_change_password.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: adm.username,
          oldPassword: oldPass,
          newPassword: newPass
        })
      });
      const data = await res.json();
      if (data.ok) {
        alert('修改成功，请重新登录');
        close();
        await logout();
        location.href = 'index.html';
      } else {
        alert(data.error || '修改失败');
      }
    } catch (e) {
      console.error(e);
      alert('网络错误');
    }
  });
}
