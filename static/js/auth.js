/**
 * 认证模块 - 处理登录、注册等功能的AJAX实现
 */

const SboxAuth = {
    /**
     * 初始化登录表单
     * @param {string} formId - 表单ID
     * @param {Object} options - 配置选项
     */
    initLoginForm(formId, options = {}) {
        const form = document.getElementById(formId);
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = form.querySelector('button[type="submit"]');
            const username = form.querySelector('#username')?.value;
            const password = form.querySelector('#password')?.value;
            const token = form.querySelector('#token')?.value || '';
            const captchaInput = form.querySelector('#captchaInput')?.value;
            const captchaId = form.querySelector('#captchaId')?.value;

            // 验证用户协议同意
            const agreeCheck = form.querySelector('#agreeCheck');
            if (agreeCheck && !agreeCheck.checked) {
                SboxAjax.showMessage('请阅读并同意用户协议', 'error');
                return;
            }

            // 显示加载状态
            SboxAjax.showLoading(submitBtn, true);

            try {
                const result = await this.login({
                    username,
                    password,
                    token,
                    captcha: captchaInput,
                    captcha_id: captchaId
                });

                if (result.success) {
                    SboxAjax.showMessage('登录成功！', 'success');
                    
                    if (options.onSuccess) {
                        options.onSuccess(result);
                    } else {
                        // 默认跳转到首页
                        setTimeout(() => {
                            window.location.href = result.redirect || '/';
                        }, 500);
                    }
                } else {
                    SboxAjax.showMessage(result.error || '登录失败', 'error');
                    if (options.onError) options.onError(result);
                    // 验证码错误时刷新验证码
                    if (result.error && result.error.includes('验证码')) {
                        if (typeof loadCaptcha === 'function') {
                            loadCaptcha();
                        }
                    }
                }
            } catch (error) {
                SboxAjax.showMessage(error.message || '网络错误，请重试', 'error');
                if (options.onError) options.onError({ error: error.message });
            } finally {
                SboxAjax.showLoading(submitBtn, false);
            }
        });
    },

    /**
     * 登录请求
     * @param {Object} credentials - 登录凭据
     * @returns {Promise}
     */
    async login(credentials) {
        return await SboxAjax.post('/api/login', credentials);
    },

    /**
     * 初始化注册表单
     * @param {string} formId - 表单ID
     * @param {Object} options - 配置选项
     */
    initRegisterForm(formId, options = {}) {
        const form = document.getElementById(formId);
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = form.querySelector('button[type="submit"]');
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            // 验证密码
            if (data.password !== data.confirm_password) {
                SboxAjax.showMessage('两次输入的密码不一致', 'error');
                return;
            }

            // 密码强度检查
            if (!this.checkPasswordStrength(data.password)) {
                SboxAjax.showMessage('密码强度不足：至少8位，包含数字、大小写字母和特殊字符', 'error');
                return;
            }

            // 显示加载状态
            SboxAjax.showLoading(submitBtn, true);

            try {
                const result = await this.register(data);

                if (result.success) {
                    SboxAjax.showMessage('注册成功！', 'success');
                    
                    if (options.onSuccess) {
                        options.onSuccess(result);
                    } else {
                        // 默认跳转到登录页
                        setTimeout(() => {
                            window.location.href = '/login';
                        }, 1000);
                    }
                } else {
                    SboxAjax.showMessage(result.error || '注册失败', 'error');
                    if (options.onError) options.onError(result);
                }
            } catch (error) {
                SboxAjax.showMessage(error.message || '网络错误，请重试', 'error');
                if (options.onError) options.onError({ error: error.message });
            } finally {
                SboxAjax.showLoading(submitBtn, false);
            }
        });
    },

    /**
     * 注册请求
     * @param {Object} userData - 用户数据
     * @returns {Promise}
     */
    async register(userData) {
        return await SboxAjax.post('/api/register', userData);
    },

    /**
     * 发送验证码
     * @param {string} email - 邮箱地址
     * @returns {Promise}
     */
    async sendVerificationCode(email) {
        return await SboxAjax.post('/api/send-verification', { email });
    },

    /**
     * 重置密码
     * @param {Object} data - 重置密码数据
     * @returns {Promise}
     */
    async resetPassword(data) {
        return await SboxAjax.post('/api/reset-password', data);
    },

    /**
     * 检查密码强度
     * @param {string} password - 密码
     * @returns {boolean}
     */
    checkPasswordStrength(password) {
        if (password.length < 8) return false;
        if (!/\d/.test(password)) return false;
        if (!/[a-z]/.test(password)) return false;
        if (!/[A-Z]/.test(password)) return false;
        if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) return false;
        return true;
    },

    /**
     * 实时验证用户名
     * @param {string} username - 用户名
     * @returns {Promise}
     */
    async checkUsername(username) {
        return await SboxAjax.get('/api/check-username', { username });
    },

    /**
     * 实时验证邮箱
     * @param {string} email - 邮箱
     * @returns {Promise}
     */
    async checkEmail(email) {
        return await SboxAjax.get('/api/check-email', { email });
    }
};

// 自动初始化（如果页面有登录/注册表单）
document.addEventListener('DOMContentLoaded', () => {
    // 初始化登录表单
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        SboxAuth.initLoginForm('loginForm');
    }

    // 初始化注册表单
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        SboxAuth.initRegisterForm('registerForm');
    }

    // 添加实时验证
    const usernameInput = document.getElementById('username');
    if (usernameInput) {
        let debounceTimer;
        usernameInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(async () => {
                const username = e.target.value.trim();
                if (username.length >= 3) {
                    try {
                        const result = await SboxAuth.checkUsername(username);
                        const hint = document.getElementById('username-hint');
                        if (hint) {
                            if (result.exists) {
                                hint.textContent = '用户名已存在';
                                hint.style.color = 'red';
                            } else {
                                hint.textContent = '用户名可用';
                                hint.style.color = 'green';
                            }
                        }
                    } catch (error) {
                        console.error('检查用户名失败:', error);
                    }
                }
            }, 500);
        });
    }

    const emailInput = document.getElementById('email');
    if (emailInput) {
        let debounceTimer;
        emailInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(async () => {
                const email = e.target.value.trim();
                if (email.includes('@')) {
                    try {
                        const result = await SboxAuth.checkEmail(email);
                        const hint = document.getElementById('email-hint');
                        if (hint) {
                            if (result.exists) {
                                hint.textContent = '邮箱已被注册';
                                hint.style.color = 'red';
                            } else {
                                hint.textContent = '邮箱可用';
                                hint.style.color = 'green';
                            }
                        }
                    } catch (error) {
                        console.error('检查邮箱失败:', error);
                    }
                }
            }, 500);
        });
    }
});

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SboxAuth;
}