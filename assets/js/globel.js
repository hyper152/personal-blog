/**
 * 全局通用脚本
 * 功能：导航激活、页面加载动画、通用工具方法
 */
document.addEventListener('DOMContentLoaded', () => {
    // 严格模式，避免隐式错误
    'use strict';

    // 1. 导航栏激活状态（优化匹配逻辑，支持多级路径）
    const setNavActive = () => {
        const currentPath = window.location.pathname.replace(/\/$/, ''); // 移除末尾斜杠
        const navLinks = document.querySelectorAll('.nav-links a');
        
        navLinks.forEach(link => {
            const linkHref = link.getAttribute('href').replace(/\/$/, '');
            
            // 匹配规则：精确匹配 或 当前路径以链接路径为前缀（支持子页面）
            if (currentPath === linkHref || currentPath.startsWith(`${linkHref}/`)) {
                link.style.color = '#ff6b6b';
                link.style.fontWeight = '700';
                link.setAttribute('aria-current', 'page'); // 无障碍优化
            } else {
                link.style.color = '';
                link.style.fontWeight = '';
                link.removeAttribute('aria-current');
            }
        });
    };

    // 2. 页面加载动画（优化过渡效果，避免闪烁）
    const pageLoadAnimation = () => {
        document.body.style.opacity = '0';
        document.body.style.transition = 'opacity 0.5s ease-out';
        
        // 确保DOM完全渲染后再显示
        requestAnimationFrame(() => {
            setTimeout(() => {
                document.body.style.opacity = '1';
            }, 100);
        });
    };

    // 3. 通用工具：防抖函数（后续扩展可用）
    window.debounce = (func, delay = 300) => {
        let timer = null;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => func.apply(this, args), delay);
        };
    };

    // 初始化
    setNavActive();
    pageLoadAnimation();

    // 监听路由变化（单页应用场景）
    window.addEventListener('popstate', setNavActive);
});