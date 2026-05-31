/**
 * AJAX工具库 - 提供统一的AJAX请求封装
 * 用于小盒子社区项目
 */

const SboxAjax = {
    // 配置
    config: {
        baseUrl: '',
        timeout: 30000,
        csrfToken: null
    },

    /**
     * 初始化配置
     */
    init() {
        // 从meta标签获取CSRF token（如果存在）
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            this.config.csrfToken = metaToken.getAttribute('content');
        }
    },

    /**
     * 发送GET请求
     * @param {string} url - 请求URL
     * @param {Object} params - 查询参数
     * @returns {Promise}
     */
    get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        
        return this.request(fullUrl, {
            method: 'GET'
        });
    },

    /**
     * 发送POST请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @param {boolean} isJson - 是否发送JSON数据
     * @returns {Promise}
     */
    post(url, data = {}, isJson = true) {
        const options = {
            method: 'POST'
        };

        if (isJson) {
            options.headers = {
                'Content-Type': 'application/json'
            };
            options.body = JSON.stringify(data);
        } else {
            // FormData格式
            const formData = new FormData();
            for (const key in data) {
                formData.append(key, data[key]);
            }
            options.body = formData;
        }

        return this.request(url, options);
    },

    /**
     * 发送请求的核心方法
     * @param {string} url - 请求URL
     * @param {Object} options - fetch选项
     * @returns {Promise}
     */
    async request(url, options = {}) {
        // 设置超时
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);
        
        // 合并默认选项
        const defaultOptions = {
            credentials: 'same-origin',
            signal: controller.signal
        };
        
        const finalOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, finalOptions);
            clearTimeout(timeoutId);

            // 检查响应状态
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            // 尝试解析JSON
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('请求超时，请重试');
            }
            
            console.error('AJAX请求失败:', error);
            throw error;
        }
    },

    /**
     * 显示提示消息
     * @param {string} message - 消息内容
     * @param {string} type - 消息类型 (success, error, info, warning)
     * @param {number} duration - 显示时长（毫秒）
     */
    showMessage(message, type = 'info', duration = 3000) {
        // 检查是否已存在消息容器
        let container = document.getElementById('sbox-message-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'sbox-message-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
            `;
            document.body.appendChild(container);
        }

        // 创建消息元素
        const messageEl = document.createElement('div');
        messageEl.className = `sbox-message sbox-message-${type}`;
        
        // 根据类型设置样式
        const styles = {
            success: 'background: #4CAF50; color: white;',
            error: 'background: #f44336; color: white;',
            info: 'background: #2196F3; color: white;',
            warning: 'background: #ff9800; color: white;'
        };
        
        messageEl.style.cssText = `
            padding: 12px 20px;
            border-radius: 4px;
            animation: slideIn 0.3s ease;
            ${styles[type] || styles.info}
        `;
        
        messageEl.textContent = message;
        container.appendChild(messageEl);

        // 自动移除
        setTimeout(() => {
            messageEl.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                messageEl.remove();
                // 如果容器为空，移除容器
                if (container.children.length === 0) {
                    container.remove();
                }
            }, 300);
        }, duration);
    },

    /**
     * 显示加载状态
     * @param {HTMLElement} element - 要显示加载状态的元素
     * @param {boolean} show - 是否显示
     */
    showLoading(element, show = true) {
        if (!element) return;

        if (show) {
            element.dataset.originalText = element.textContent;
            element.disabled = true;
            element.innerHTML = '<span class="loading-spinner"></span> 加载中...';
        } else {
            element.disabled = false;
            element.textContent = element.dataset.originalText || '提交';
        }
    }
};

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .loading-spinner {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid rgba(255,255,255,0.3);
        border-radius: 50%;
        border-top-color: #fff;
        animation: spin 0.8s linear infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    SboxAjax.init();
});

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SboxAjax;
}