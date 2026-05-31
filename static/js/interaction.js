/**
 * 交互模块 - 处理点赞、收藏、评论等功能
 */

const SboxInteraction = {
    /**
     * 点赞作品
     * @param {string} workId - 作品ID
     * @param {HTMLElement} button - 点赞按钮元素
     * @param {HTMLElement} countEl - 显示点赞数的元素
     */
    async likeWork(workId, button, countEl) {
        if (!workId) return;
        
        // 检查是否已登录
        const isLoggedIn = document.body.dataset.loggedIn === 'true';
        if (!isLoggedIn) {
            SboxAjax.showMessage('请先登录', 'warning');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1000);
            return;
        }

        // 显示加载状态
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<span class="loading-spinner"></span>';

        try {
            const result = await SboxAjax.get(`/scratchlike=${workId}`);
            
            if (result.like !== undefined) {
                // 更新点赞数
                if (countEl) {
                    countEl.textContent = result.like;
                }
                
                // 切换点赞状态样式
                button.classList.toggle('liked');
                if (button.classList.contains('liked')) {
                    button.innerHTML = '❤️ ' + result.like;
                    SboxAjax.showMessage('点赞成功！', 'success');
                } else {
                    button.innerHTML = '🤍 ' + result.like;
                    SboxAjax.showMessage('取消点赞', 'info');
                }
            }
        } catch (error) {
            SboxAjax.showMessage(error.message || '点赞失败', 'error');
            button.innerHTML = originalText;
        } finally {
            button.disabled = false;
        }
    },

    /**
     * 收藏作品
     * @param {string} workId - 作品ID
     * @param {HTMLElement} button - 收藏按钮元素
     * @param {HTMLElement} countEl - 显示收藏数的元素
     */
    async starWork(workId, button, countEl) {
        if (!workId) return;
        
        // 检查是否已登录
        const isLoggedIn = document.body.dataset.loggedIn === 'true';
        if (!isLoggedIn) {
            SboxAjax.showMessage('请先登录', 'warning');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1000);
            return;
        }

        // 显示加载状态
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<span class="loading-spinner"></span>';

        try {
            const result = await SboxAjax.get(`/scratchstar=${workId}`);
            
            if (result.star !== undefined) {
                // 更新收藏数
                if (countEl) {
                    countEl.textContent = result.star;
                }
                
                // 切换收藏状态样式
                button.classList.toggle('starred');
                if (button.classList.contains('starred')) {
                    button.innerHTML = '⭐ ' + result.star;
                    SboxAjax.showMessage('收藏成功！', 'success');
                } else {
                    button.innerHTML = '☆ ' + result.star;
                    SboxAjax.showMessage('取消收藏', 'info');
                }
            }
        } catch (error) {
            SboxAjax.showMessage(error.message || '收藏失败', 'error');
            button.innerHTML = originalText;
        } finally {
            button.disabled = false;
        }
    },

    /**
     * 提交Issues/评论
     * @param {string} workId - 作品ID
     * @param {string} content - 评论内容
     * @param {string} type - 评论类型
     * @param {Object} options - 配置选项
     */
    async submitIssue(workId, content, type = 'general', options = {}) {
        if (!content || !content.trim()) {
            SboxAjax.showMessage('请输入评论内容', 'warning');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('issue_content', content);
            formData.append('issue_type', type);

            const response = await fetch(`/scratch/${workId}?page=Issues`, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });

            if (response.ok) {
                SboxAjax.showMessage('评论提交成功！', 'success');
                if (options.onSuccess) {
                    options.onSuccess();
                } else {
                    // 刷新页面或重新加载评论
                    setTimeout(() => {
                        window.location.reload();
                    }, 500);
                }
            } else {
                throw new Error('提交失败');
            }
        } catch (error) {
            SboxAjax.showMessage(error.message || '评论提交失败', 'error');
            if (options.onError) {
                options.onError(error);
            }
        }
    },

    /**
     * 加载Issues列表（AJAX分页）
     * @param {string} workId - 作品ID
     * @param {number} page - 页码
     * @param {HTMLElement} container - 容器元素
     */
    async loadIssues(workId, page = 1, container) {
        if (!container) return;

        container.innerHTML = '<div class="loading">加载中...</div>';

        try {
            const result = await SboxAjax.get(`/scratch/${workId}`, { 
                page: 'Issues_api', 
                p: page 
            });

            if (result.error) {
                throw new Error(result.error);
            }

            // 渲染Issues列表
            this.renderIssues(result, container, workId);
        } catch (error) {
            container.innerHTML = `<div class="error">加载失败：${error.message}</div>`;
        }
    },

    /**
     * 渲染Issues列表
     * @param {Object} data - Issues数据
     * @param {HTMLElement} container - 容器元素
     * @param {string} workId - 作品ID
     */
    renderIssues(data, container, workId) {
        const { issues, current_page, total_pages, total_issues } = data;

        let html = '<div class="issues-list">';
        
        if (issues && issues.length > 0) {
            issues.forEach((issue, index) => {
                html += `
                    <div class="issue-item">
                        <div class="issue-content">${this.escapeHtml(issue)}</div>
                    </div>
                `;
            });
        } else {
            html += '<p class="no-issues">暂无评论</p>';
        }
        
        html += '</div>';

        // 分页控件
        if (total_pages > 1) {
            html += '<div class="pagination">';
            
            if (current_page > 1) {
                html += `<button class="page-btn" data-page="${current_page - 1}">上一页</button>`;
            }
            
            html += `<span class="page-info">第 ${current_page} / ${total_pages} 页</span>`;
            
            if (current_page < total_pages) {
                html += `<button class="page-btn" data-page="${current_page + 1}">下一页</button>`;
            }
            
            html += '</div>';
        }

        container.innerHTML = html;

        // 绑定分页事件
        container.querySelectorAll('.page-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = parseInt(btn.dataset.page);
                this.loadIssues(workId, page, container);
            });
        });
    },

    /**
     * HTML转义
     * @param {string} text - 原始文本
     * @returns {string}
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * 初始化作品详情页交互
     */
    initWorkInteraction() {
        // 点赞按钮
        const likeBtn = document.getElementById('like-btn');
        if (likeBtn) {
            const workId = likeBtn.dataset.workId;
            const countEl = document.getElementById('like-count');
            
            likeBtn.addEventListener('click', () => {
                this.likeWork(workId, likeBtn, countEl);
            });
        }

        // 收藏按钮
        const starBtn = document.getElementById('star-btn');
        if (starBtn) {
            const workId = starBtn.dataset.workId;
            const countEl = document.getElementById('star-count');
            
            starBtn.addEventListener('click', () => {
                this.starWork(workId, starBtn, countEl);
            });
        }

        // Issues表单
        const issueForm = document.getElementById('issue-form');
        if (issueForm) {
            const workId = issueForm.dataset.workId;
            const contentEl = issueForm.querySelector('textarea[name="issue_content"]');
            const typeEl = issueForm.querySelector('select[name="issue_type"]');
            
            issueForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const content = contentEl?.value;
                const type = typeEl?.value || 'general';
                this.submitIssue(workId, content, type, {
                    onSuccess: () => {
                        contentEl.value = '';
                        // 重新加载Issues列表
                        const issuesContainer = document.getElementById('issues-container');
                        if (issuesContainer) {
                            this.loadIssues(workId, 1, issuesContainer);
                        }
                    }
                });
            });
        }

        // Issues列表容器
        const issuesContainer = document.getElementById('issues-container');
        if (issuesContainer) {
            const workId = issuesContainer.dataset.workId;
            this.loadIssues(workId, 1, issuesContainer);
        }
    }
};

// 添加交互相关的CSS样式
const interactionStyles = document.createElement('style');
interactionStyles.textContent = `
    .liked {
        color: #e74c3c !important;
    }
    
    .starred {
        color: #f39c12 !important;
    }
    
    .issues-list {
        margin: 20px 0;
    }
    
    .issue-item {
        padding: 15px;
        border-bottom: 1px solid #eee;
        background: #fff;
    }
    
    .issue-item:hover {
        background: #f9f9f9;
    }
    
    .issue-content {
        line-height: 1.6;
    }
    
    .pagination {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 15px;
        margin: 20px 0;
    }
    
    .page-btn {
        padding: 8px 16px;
        background: #667eea;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        transition: background 0.3s;
    }
    
    .page-btn:hover {
        background: #764ba2;
    }
    
    .page-info {
        color: #666;
    }
    
    .loading, .error {
        text-align: center;
        padding: 20px;
        color: #666;
    }
    
    .error {
        color: #e74c3c;
    }
    
    .no-issues {
        text-align: center;
        color: #999;
        padding: 40px;
    }
`;
document.head.appendChild(interactionStyles);

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    // 检查用户登录状态
    const isLoggedIn = document.body.dataset.loggedIn || 
                       (document.querySelector('.navbar-dropdown') !== null);
    document.body.dataset.loggedIn = isLoggedIn;

    // 初始化作品交互
    if (document.getElementById('like-btn') || 
        document.getElementById('star-btn') ||
        document.getElementById('issues-container')) {
        SboxInteraction.initWorkInteraction();
    }
});

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SboxInteraction;
}