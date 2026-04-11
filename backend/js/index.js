// 全局变量
let sessionId = localStorage.getItem('session_id');
let currentUser = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    if (!sessionId) {
        redirectToLogin();
        return;
    }
    
    verifySession();
    initializeSidebar();
});

// 初始化侧边栏
function initializeSidebar() {
    // 检查是否是移动设备
    if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.add('collapsed');
    }
    
    // 监听窗口大小变化
    window.addEventListener('resize', function() {
        if (window.innerWidth <= 768) {
            document.getElementById('sidebar').classList.remove('mobile-open');
        }
    });
}

// 切换侧边栏
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleIcon = document.getElementById('toggleIcon');
    
    if (window.innerWidth <= 768) {
        // 移动端：显示/隐藏侧边栏
        sidebar.classList.toggle('mobile-open');
    } else {
        // 桌面端：折叠/展开侧边栏
        sidebar.classList.toggle('collapsed');
        toggleIcon.textContent = sidebar.classList.contains('collapsed') ? '›' : '‹';
    }
}

// 设置活动导航项
function setActiveNavItem(clickedItem) {
    // 移除所有活动状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 设置当前项为活动状态
    clickedItem.classList.add('active');
    
    // 在移动端点击后关闭侧边栏
    if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('mobile-open');
    }
}

// 显示仪表板
function showDashboard() {
    const clickedItem = event.target.closest('.nav-item');
    setActiveNavItem(clickedItem);
    
    document.getElementById('pageTitle').textContent = '仪表板';
    hideOtherContent();
    document.getElementById('dashboardContent').style.display = 'block';
    
    // 加载仪表盘数据
    loadDashboardData();
}

// 显示登录日志
function viewLogs() {
    const clickedItem = event.target.closest('.nav-item');
    setActiveNavItem(clickedItem);
    document.getElementById('pageTitle').textContent = '登录日志';
    hideOtherContent();
    document.getElementById('logsContent').style.display = 'block';
}

// 显示系统设置
function viewSettings() {
    const clickedItem = event.target.closest('.nav-item');
    setActiveNavItem(clickedItem);
    document.getElementById('pageTitle').textContent = '系统设置';
    hideOtherContent();
    document.getElementById('settingsContent').style.display = 'block';
    
    // 初始化系统设置
    if (window.SystemSettings && typeof window.SystemSettings.initialize === 'function') {
        window.SystemSettings.initialize();
    }
}

// 显示数据统计
function viewStats() {
    const clickedItem = event.target.closest('.nav-item');
    setActiveNavItem(clickedItem);
    document.getElementById('pageTitle').textContent = '数据统计';
    hideOtherContent();
    document.getElementById('statsContent').style.display = 'block';
}

// 显示数据导入
function importData() {
    const clickedItem = event.target.closest('.nav-item');
    setActiveNavItem(clickedItem);
    document.getElementById('pageTitle').textContent = '数据导入';
    hideOtherContent();
    document.getElementById('importContent').style.display = 'block';
}

// 显示数据导出
function exportData() {
    const clickedItem = event.target.closest('.nav-item');
    setActiveNavItem(clickedItem);
    document.getElementById('pageTitle').textContent = '数据导出';
    hideOtherContent();
    document.getElementById('exportContent').style.display = 'block';
}

// 显示数据备份
function backupData() {
    const clickedItem = event.target.closest('.nav-item');
    setActiveNavItem(clickedItem);
    document.getElementById('pageTitle').textContent = '数据备份';
    hideOtherContent();
    document.getElementById('backupContent').style.display = 'block';
}

// 隐藏其他内容区域
function hideOtherContent() {
    const contentSections = [
        'dashboardContent',
        'registrationsContent', 
        'seatingsContent',
        'logsContent',
        'settingsContent',
        'statsContent',
        'importContent',
        'exportContent',
        'pagesContent',
        'backupContent'
    ];
    
    contentSections.forEach(sectionId => {
        const element = document.getElementById(sectionId);
        if (element) {
            element.style.display = 'none';
        }
    });
}

// 隐藏所有内容区域（别名函数，供其他模块使用）
function hideAllSections() {
    hideOtherContent();
}

// 验证会话
async function verifySession() {
    showLoading(true);
    
    try {
        const response = await fetch(API_CONFIG.ENDPOINTS.VERIFY_SESSION, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId
            })
        });

        const result = await response.json();
        
        if (result.success) {
            currentUser = result.data;
            updateUserInfo();
            
            // 默认显示仪表盘页面
            initializeDashboard();
        } else {
            showError('会话已过期，请重新登录');
            setTimeout(redirectToLogin, 2000);
        }
    } catch (error) {
        console.error('验证会话失败:', error);
        showError('网络连接失败，请检查网络后重试');
    } finally {
        showLoading(false);
    }
}

// 更新用户信息显示
function updateUserInfo() {
    if (!currentUser) return;
    
    document.getElementById('username').textContent = currentUser.username;
    document.getElementById('userAvatar').textContent = currentUser.username.charAt(0).toUpperCase();
    
    if (currentUser.last_login) {
        document.getElementById('lastLogin').textContent = `最后登录: ${currentUser.last_login}`;
    } else {
        document.getElementById('lastLogin').textContent = '首次登录';
    }
}

// 初始化仪表盘（默认页面）
function initializeDashboard() {
    // 设置页面标题
    document.getElementById('pageTitle').textContent = '仪表板';
    
    // 隐藏所有内容区域
    hideOtherContent();
    
    // 显示仪表盘内容
    document.getElementById('dashboardContent').style.display = 'block';
    
    // 设置仪表盘导航项为活动状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 找到仪表盘导航项并设置为活动状态
    const dashboardNavItem = document.querySelector('.nav-item[onclick="showDashboard()"]');
    if (dashboardNavItem) {
        dashboardNavItem.classList.add('active');
    }
    
    // 加载仪表盘数据
    loadDashboardData();
}

// 加载仪表板数据
async function loadDashboardData() {
    try {
        // 显示加载状态
        setDashboardLoading(true);
        
        const response = await fetch(API_CONFIG.ENDPOINTS.DASHBOARD, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            updateDashboardStats(result.data);
            // 加载图表数据
            await loadChartsData();
        } else {
            throw new Error(result.message || '获取数据失败');
        }
        
    } catch (error) {
        console.error('加载仪表盘数据失败:', error);
        showError('加载数据失败: ' + error.message);
        // 显示默认数据
        updateDashboardStats({
            total_registrations: 0,
            total_payments: 0,
            total_sponsorship: 0,
            total_programs: 0
        });
    } finally {
        setDashboardLoading(false);
    }
}

// 加载图表数据
async function loadChartsData() {
    try {
        const response = await fetch(API_CONFIG.ENDPOINTS.CHARTS, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            renderCharts(result.data);
        } else {
            console.error('获取图表数据失败:', result.message);
            renderDefaultCharts();
        }
        
    } catch (error) {
        console.error('加载图表数据失败:', error);
        renderDefaultCharts();
    }
}

// 渲染图表
function renderCharts(data) {
    // 渲染报名人数趋势图
    renderRegistrationTrendChart(data.registration_trend || []);
    
    // 渲染提交金额分布图
    renderPaymentDistributionChart(data.payment_distribution || []);
    
    // 渲染才艺表演统计图
    renderTalentShowStatsChart(data.talent_show_stats || []);
}

// 渲染默认图表（无数据时）
function renderDefaultCharts() {
    renderRegistrationTrendChart([]);
    renderPaymentDistributionChart([]);
    renderTalentShowStatsChart([]);
}

// 报名人数趋势图
function renderRegistrationTrendChart(data) {
    const ctx = document.getElementById('registrationTrendChart');
    if (!ctx) return;

    // 销毁之前的图表实例
    const existingChart = Chart.getChart(ctx);
    if (existingChart) {
        existingChart.destroy();
    }

    // 检查是否有数据
    const hasData = data && data.length > 0;
    const chartData = hasData ? data : [{ date: '暂无数据', count: 0 }];

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.map(item => item.date),
            datasets: [{
                label: '报名人数',
                data: chartData.map(item => item.count),
                borderColor: hasData ? '#3498db' : '#bdc3c7',
                backgroundColor: hasData ? 'rgba(52, 152, 219, 0.1)' : 'rgba(189, 195, 199, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: hasData,
                    callbacks: {
                        title: function(context) {
                            return hasData ? context[0].label : '';
                        },
                        label: function(context) {
                            return hasData ? `报名人数: ${context.parsed.y}人` : '暂无数据';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    },
                    ticks: {
                        display: hasData
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    },
                    ticks: {
                        display: hasData
                    }
                }
            },
            // 添加无数据时的文本显示
            onComplete: function(chart) {
                if (!hasData) {
                    const ctx = chart.ctx;
                    const width = chart.width;
                    const height = chart.height;
                    
                    ctx.save();
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.font = '16px Arial';
                    ctx.fillStyle = '#95a5a6';
                    ctx.fillText('暂无报名数据', width / 2, height / 2);
                    ctx.restore();
                }
            }
        }
    });
}

// 提交金额分布图
function renderPaymentDistributionChart(data) {
    const ctx = document.getElementById('paymentDistributionChart');
    if (!ctx) return;

    // 销毁之前的图表实例
    const existingChart = Chart.getChart(ctx);
    if (existingChart) {
        existingChart.destroy();
    }

    // 过滤掉count为0的数据
    const validData = data && data.length > 0 ? data.filter(item => parseInt(item.count) > 0) : [];
    
    // 检查是否有有效数据
    const hasData = validData.length > 0;
    const chartData = hasData ? validData : [{ category: '暂无数据', amount: 0, count: 0 }];

    // 准备图表数据
    const labels = chartData.map(item => item.category || '未知类型');
    const counts = chartData.map(item => parseInt(item.count) || 0);
    const colors = hasData ? ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6'] : ['#bdc3c7'];

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        generateLabels: function(chart) {
                            const data = chart.data;
                            if (data.labels.length && data.datasets.length && hasData) {
                                return data.labels.map((label, index) => {
                                    const count = counts[index] || 0;
                                    return {
                                        text: `${label} (${count}人)`,
                                        fillStyle: colors[index % colors.length],
                                        strokeStyle: colors[index % colors.length],
                                        lineWidth: 2,
                                        hidden: false,
                                        index: index
                                    };
                                });
                            }
                            return [];
                        }
                    }
                },
                tooltip: {
                    enabled: hasData,
                    callbacks: {
                        label: function(context) {
                            if (!hasData) {
                                return '暂无数据';
                            }
                            
                            const dataIndex = context.dataIndex;
                            const item = chartData[dataIndex];
                            
                            if (!item) {
                                return '暂无数据';
                            }
                            
                            const label = item.category || '未知类型';
                            const amount = parseFloat(item.amount) || 0;
                            const count = parseInt(item.count) || 0;
                            
                            // 计算总人数用于百分比计算
                            const totalCount = counts.reduce((sum, c) => sum + c, 0);
                            const percentage = totalCount > 0 ? ((count / totalCount) * 100).toFixed(1) : '0.0';
                            
                            return [
                                `类型: ${label}`,
                                `金额: ¥${amount.toLocaleString()}`,
                                `人数: ${count}人`,
                                `占比: ${percentage}%`
                            ];
                        }
                    }
                }
            },
            // 添加无数据时的文本显示
            onComplete: function(chart) {
                if (!hasData) {
                    const ctx = chart.ctx;
                    const width = chart.width;
                    const height = chart.height;
                    
                    ctx.save();
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.font = '16px Arial';
                    ctx.fillStyle = '#95a5a6';
                    ctx.fillText('暂无提交金额数据', width / 2, height / 2);
                    ctx.restore();
                }
            }
        }
    });
}

// 才艺表演统计图
function renderTalentShowStatsChart(data) {
    const ctx = document.getElementById('talentShowStatsChart');
    if (!ctx) return;

    // 销毁之前的图表实例
    const existingChart = Chart.getChart(ctx);
    if (existingChart) {
        existingChart.destroy();
    }

    // 检查是否有数据
    const hasData = data && data.length > 0;
    const chartData = hasData ? data : [{ category: '暂无数据', count: 0 }];

    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: chartData.map(item => item.category),
            datasets: [{
                label: '人数',
                data: chartData.map(item => item.count),
                backgroundColor: hasData ? [
                    '#3498db',
                    '#e74c3c',
                    '#f39c12',
                    '#27ae60',
                    '#9b59b6'
                ] : ['#bdc3c7'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: hasData,
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    enabled: hasData,
                    callbacks: {
                        label: function(context) {
                            if (!hasData) {
                                return '暂无数据';
                            }
                            
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return `${label}: ${value}人 (${percentage}%)`;
                        }
                    }
                }
            },
            // 添加无数据时的文本显示
            onComplete: function(chart) {
                if (!hasData) {
                    const ctx = chart.ctx;
                    const width = chart.width;
                    const height = chart.height;
                    
                    ctx.save();
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.font = '16px Arial';
                    ctx.fillStyle = '#95a5a6';
                    ctx.fillText('暂无才艺表演数据', width / 2, height / 2);
                    ctx.restore();
                }
            }
        }
    });
}

// 更新仪表盘统计数据
function updateDashboardStats(data) {
    // 更新总报名人数
    const totalRegistrationsEl = document.getElementById('totalRegistrations');
    if (totalRegistrationsEl) {
        animateNumber(totalRegistrationsEl, data.total_registrations || 0);
    }
    
    // 已移除缴费金额统计功能
    
    // 更新总节目数量
    const totalProgramsEl = document.getElementById('totalPrograms');
    if (totalProgramsEl) {
        animateNumber(totalProgramsEl, data.total_programs || 0);
    }
    
    // 更新签到统计数据
    const checkedInCountEl = document.getElementById('checkedInCount');
    if (checkedInCountEl) {
        animateNumber(checkedInCountEl, data.checked_in_count || 0);
    }
    
    const notCheckedInCountEl = document.getElementById('notCheckedInCount');
    if (notCheckedInCountEl) {
        animateNumber(notCheckedInCountEl, data.not_checked_in_count || 0);
    }
    
    const checkinRateEl = document.getElementById('checkinRate');
    if (checkinRateEl) {
        animatePercentage(checkinRateEl, data.checkin_rate || 0);
    }
    
    const todayCheckinCountEl = document.getElementById('todayCheckinCount');
    if (todayCheckinCountEl) {
        animateNumber(todayCheckinCountEl, data.today_checkin_count || 0);
    }
}

// 设置仪表盘加载状态
function setDashboardLoading(loading) {
    const elements = [
        'totalRegistrations',
        'totalPrograms',
        'checkedInCount',
        'notCheckedInCount',
        'checkinRate',
        'todayCheckinCount'
    ];
    
    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            if (loading) {
                // 加载时显示加载状态
                if (id === 'checkinRate') {
                    element.textContent = '...';
                } else {
                    element.textContent = '...';
                }
                element.style.opacity = '0.6';
            } else {
                // 加载完成时不重置内容，让updateDashboardStats函数处理
                element.style.opacity = '1';
            }
        }
    });
}

// 刷新仪表盘数据
async function refreshDashboard() {
    const refreshBtn = document.querySelector('.refresh-btn');
    const refreshIcon = document.getElementById('refreshIcon');
    
    // 添加加载状态
    refreshBtn.classList.add('loading');
    refreshBtn.disabled = true;
    
    try {
        await loadDashboardData();
        showSuccess('数据刷新成功');
    } catch (error) {
        showError('刷新失败: ' + error.message);
    } finally {
        // 移除加载状态
        refreshBtn.classList.remove('loading');
        refreshBtn.disabled = false;
    }
}

// 数字动画效果
function animateNumber(element, targetValue, isCurrency = false) {
    const startValue = 0;
    const duration = 1000; // 1秒
    const startTime = performance.now();
    
    function updateNumber(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // 使用缓动函数
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const currentValue = Math.floor(startValue + (targetValue - startValue) * easeOutQuart);
        
        if (isCurrency) {
            element.textContent = currentValue.toLocaleString('zh-CN', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        } else {
            element.textContent = currentValue.toLocaleString('zh-CN');
        }
        
        if (progress < 1) {
            requestAnimationFrame(updateNumber);
        }
    }
    
    requestAnimationFrame(updateNumber);
}

// 百分比动画效果
function animatePercentage(element, targetValue) {
    const startValue = 0;
    const duration = 1000; // 1秒
    const startTime = performance.now();
    
    function updatePercentage(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // 使用缓动函数
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const currentValue = startValue + (targetValue - startValue) * easeOutQuart;
        
        // 保留一位小数
        element.textContent = currentValue.toFixed(1) + '%';
        
        if (progress < 1) {
            requestAnimationFrame(updatePercentage);
        }
    }
    
    requestAnimationFrame(updatePercentage);
}

// 登出功能
async function logout() {
    if (!confirm('确定要退出登录吗？')) {
        return;
    }

    try {
        const response = await fetch(API_CONFIG.ENDPOINTS.LOGOUT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId
            })
        });

        const result = await response.json();
        
        if (result.success) {
            showSuccess('退出登录成功');
            localStorage.removeItem('session_id');
            setTimeout(redirectToLogin, 1000);
        } else {
            showError('退出登录失败: ' + result.message);
        }
    } catch (error) {
        console.error('退出登录失败:', error);
        // 即使API调用失败，也清除本地会话
        localStorage.removeItem('session_id');
        redirectToLogin();
    }
}

// 重定向到登录页面
function redirectToLogin() {
    window.location.href = 'login.html';
}

// 显示/隐藏加载状态
function showLoading(show) {
    // 不显示加载状态
    if (show) {
        document.getElementById('dashboardContent').style.display = 'none';
    }
}

// 显示弹窗提示
function showToast(message, type = 'success', duration = 3000) {
    const container = document.getElementById('toastContainer');
    
    // 创建弹窗元素
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // 设置图标
    const icon = type === 'success' ? '✅' : '❌';
    
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-content">${message}</div>
        <button class="toast-close" onclick="removeToast(this.parentElement)">×</button>
    `;
    
    // 添加到容器
    container.appendChild(toast);
    
    // 触发显示动画
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // 自动移除
    setTimeout(() => {
        removeToast(toast);
    }, duration);
}

// 移除弹窗
function removeToast(toast) {
    if (toast && toast.parentElement) {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentElement) {
                toast.parentElement.removeChild(toast);
            }
        }, 300);
    }
}

// 显示错误消息
function showError(message) {
    showToast(message, 'error', 5000);
}

// 显示成功消息
function showSuccess(message) {
    showToast(message, 'success', 3000);
}

// 快捷操作功能
function quickAction(action) {
    switch(action) {
        case 'export':
            exportData();
            break;
        case 'backup':
            backupData();
            break;
        case 'settings':
            viewSettings();
            break;
        case 'logs':
            viewLogs();
            break;
        default:
            showError('未知操作');
    }
}

// 其他功能函数
function showStats() {
    viewStats();
}

function manageUsers() {
    showSuccess('用户管理功能开发中...');
}

function manageEvents() {
    showSuccess('会议管理功能开发中...');
}

function viewReports() {
    showSuccess('报告生成功能开发中...');
}

// 新增卡片功能函数
function viewPayments() {
    showSuccess('正在查看提交金额详情...');
    // TODO: 实现查看提交金额详情功能
}

// 已移除缴费金额详情查看功能

function viewPrograms() {
    showSuccess('正在查看节目详情...');
    // TODO: 实现查看节目详情功能
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);