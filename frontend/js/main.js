/**
 * 简化的前端页面JavaScript
 * 只保留基本的页面展示功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 页面加载完成
    initializePage();
});

/**
 * 页面初始化
 */
function initializePage() {
    bindEvents();
    loadParticipantCount();
    showStaticData();
    initializeMusic();
    // 页面初始化完成
}

/**
 * 绑定基本事件
 */
function bindEvents() {
    // 导航菜单切换
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }
    
    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // 返回顶部按钮
    const backToTop = document.querySelector('.back-to-top');
    if (backToTop) {
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                backToTop.style.display = 'block';
            } else {
                backToTop.style.display = 'none';
            }
        });
        
        backToTop.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
}

/**
 * 加载报名人数统计
 */
function loadParticipantCount() {
    const participantCountEl = document.getElementById('participant-count');
    if (!participantCountEl) return;
    
    // 显示加载状态
    participantCountEl.textContent = '0';
    
    // 调用简化的API获取统计数据
    fetch('api/index.php')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(text => {
            // 检查是否是PHP源码（静态服务器环境）
            if (text.includes('<?php')) {
                // 检测到静态服务器环境，使用模拟数据
                animateNumber(participantCountEl, 0, 88, 1000);
                return;
            }
            
            // 尝试解析JSON
            const data = JSON.parse(text);
            if (data.success && data.data) {
                // 显示总报名人数
                const totalRegistrations = data.data.total_registrations || 0;
                
                // 添加数字动画效果
                animateNumber(participantCountEl, 0, totalRegistrations, 1000);
            } else {
                console.error('API返回错误:', data.error || '未知错误');
                participantCountEl.textContent = '0';
            }
        })
        .catch(error => {
            console.error('获取报名人数失败:', error);
            
            // 如果是在静态服务器环境下，显示模拟数据
            if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                // 检测到静态服务器环境，使用模拟数据
                animateNumber(participantCountEl, 0, 88, 1000);
            } else {
                participantCountEl.textContent = '0';
            }
        });
}

/**
 * 数字动画效果
 */
function animateNumber(element, start, end, duration = 1000) {
    if (start === end) return;
    
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current);
    }, 16);
}

/**
 * 显示静态数据
 */
function showStaticData() {
    // 报名人数通过loadParticipantCount()函数加载，不在这里设置
    
    // 显示静态公告
    displayStaticAnnouncements();
}

/**
 * 显示静态公告
 */
function displayStaticAnnouncements() {
    const container = document.querySelector('.announcements-list');
    if (!container) return;
    
    const announcements = [
        {
            title: '会议注册开放',
            content: '2025年学术会议注册现已开放，欢迎各位学者踊跃参与...',
            date: '2025-01-15'
        },
        {
            title: '议程安排更新',
            content: '最新的活动议程已发布，请查看详细安排...',
            date: '2025-01-10'
        }
    ];
    
    container.innerHTML = announcements.map(announcement => `
        <div class="announcement-item">
            <h3>${announcement.title}</h3>
            <p>${announcement.content}</p>
            <span class="date">${announcement.date}</span>
        </div>
    `).join('');
}

/**
 * 基础音乐播放功能
 */
function initializeMusic() {
    const musicToggle = document.getElementById('musicToggle');
    const audio = document.getElementById('schoolSong');
    
    if (!musicToggle || !audio) {
        return;
    }
    
    let isPlaying = false;
    
    musicToggle.addEventListener('click', function() {
        if (isPlaying) {
            audio.pause();
            musicToggle.classList.remove('playing');
            isPlaying = false;
        } else {
            audio.play().then(() => {
                musicToggle.classList.add('playing');
                isPlaying = true;
            }).catch(error => {
                console.error('音乐播放失败:', error);
            });
        }
    });
    
    audio.addEventListener('ended', () => {
        musicToggle.classList.remove('playing');
        isPlaying = false;
    });
}

/**
 * 显示消息提示
 */
function showMessage(message, type = 'info') {
    // 移除现有的消息提示
    const existingToast = document.querySelector('.message-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // 创建新的消息提示
    const toast = document.createElement('div');
    toast.className = `message-toast ${type}`;
    toast.textContent = message;
    
    // 添加样式
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 4px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
    `;
    
    // 根据类型设置背景色
    switch (type) {
        case 'success':
            toast.style.backgroundColor = '#28a745';
            break;
        case 'error':
            toast.style.backgroundColor = '#dc3545';
            break;
        case 'warning':
            toast.style.backgroundColor = '#ffc107';
            toast.style.color = '#212529';
            break;
        default:
            toast.style.backgroundColor = '#17a2b8';
    }
    
    document.body.appendChild(toast);
    
    // 显示动画
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    }, 100);
    
    // 自动隐藏
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}