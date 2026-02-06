/**
 * 旅游图片预览脚本
 * 功能：图片点击放大、键盘关闭、自适应缩放、防重复创建
 */
document.addEventListener('DOMContentLoaded', () => {
    'use strict';

    const images = document.querySelectorAll('.travel-image');
    let previewInstance = null; // 单例模式，避免重复创建预览层

    // 图片预览核心逻辑
    const createImagePreview = (img) => {
        // 如果已有预览层，先销毁
        if (previewInstance) {
            destroyPreview();
        }

        // 创建预览容器
        const preview = document.createElement('div');
        preview.className = 'image-preview-overlay';
        preview.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: rgba(0,0,0,0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            cursor: pointer;
            padding: 20px;
            box-sizing: border-box;
        `;

        // 创建预览图片
        const previewImg = document.createElement('img');
        previewImg.src = img.src;
        previewImg.alt = img.alt || '预览图片';
        previewImg.style.cssText = `
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
            transition: transform 0.2s ease;
        `;

        // 加载失败降级处理
        previewImg.onerror = () => {
            previewImg.src = '../home/img/error-img.jpg'; // 备用图
            previewImg.alt = '图片加载失败';
        };

        preview.appendChild(previewImg);
        document.body.appendChild(preview);
        previewInstance = preview;

        // 点击关闭
        preview.addEventListener('click', destroyPreview);

        // 键盘ESC关闭
        document.addEventListener('keydown', escCloseHandler);
    };

    // 销毁预览层
    const destroyPreview = () => {
        if (previewInstance) {
            document.body.removeChild(previewInstance);
            previewInstance = null;
            document.removeEventListener('keydown', escCloseHandler);
        }
    };

    // ESC键关闭处理器
    const escCloseHandler = (e) => {
        if (e.key === 'Escape') {
            destroyPreview();
        }
    };

    // 绑定图片点击事件（防抖处理）
    images.forEach(img => {
        img.style.cursor = 'zoom-in'; // 视觉提示
        img.addEventListener('click', () => createImagePreview(img));
    });

    // 窗口大小变化时重新调整预览图
    window.addEventListener('resize', window.debounce(() => {
        if (previewInstance) {
            const img = previewInstance.querySelector('img');
            img.style.maxWidth = '95%';
            img.style.maxHeight = '95%';
        }
    }));
});