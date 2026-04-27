/* Global JS utilities */

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

async function apiCall(url, options = {}) {
    const defaults = {
        headers: {},
    };

    if (options.body && !(options.body instanceof FormData)) {
        defaults.headers['Content-Type'] = 'application/json';
        if (typeof options.body === 'object') {
            options.body = JSON.stringify(options.body);
        }
    }

    const config = { ...defaults, ...options };
    config.headers = { ...defaults.headers, ...options.headers };

    try {
        const response = await fetch(url, config);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `请求失败 (${response.status})`);
        }
        return data;
    } catch (error) {
        if (error instanceof TypeError && error.message.includes('fetch')) {
            throw new Error('网络连接失败，请检查服务是否正常运行');
        }
        throw error;
    }
}

function showConfirm(title, message) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'confirm-overlay active';
        overlay.innerHTML = `
            <div class="confirm-box">
                <h3>${title}</h3>
                <p>${message}</p>
                <div class="flex gap-8" style="justify-content: center;">
                    <button class="btn btn-secondary" id="confirm-cancel">取消</button>
                    <button class="btn btn-danger" id="confirm-ok">确定</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        overlay.querySelector('#confirm-cancel').onclick = () => {
            overlay.remove();
            resolve(false);
        };
        overlay.querySelector('#confirm-ok').onclick = () => {
            overlay.remove();
            resolve(true);
        };
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                overlay.remove();
                resolve(false);
            }
        };
    });
}

/**
 * Show a dialog with multiple custom buttons.
 * @param {string} title
 * @param {string} message
 * @param {Array<{id: string, text: string, class: string}>} buttons
 * @returns {Promise<string|null>} resolves with button id or null if dismissed
 */
function showCustomDialog(title, message, buttons) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'confirm-overlay active';
        const btnsHtml = buttons.map(b =>
            `<button class="btn ${b.class || 'btn-secondary'}" data-btn-id="${b.id}">${b.text}</button>`
        ).join('');
        overlay.innerHTML = `
            <div class="confirm-box">
                <h3>${title}</h3>
                <p>${message}</p>
                <div class="flex gap-8" style="justify-content: center; flex-wrap: wrap;">
                    ${btnsHtml}
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        overlay.querySelectorAll('[data-btn-id]').forEach(btn => {
            btn.onclick = () => {
                overlay.remove();
                resolve(btn.dataset.btnId);
            };
        });
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                overlay.remove();
                resolve(null);
            }
        };
    });
}

function formatDate(isoString) {
    if (!isoString) return '-';
    const d = new Date(isoString);
    return d.toLocaleDateString('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit'
    });
}

function renderStars(score) {
    if (!score) return '<span class="text-muted">未评分</span>';
    const level = score <= 3 ? 'low' : score <= 5 ? 'mid' : score <= 7 ? 'ok' : score <= 9 ? 'good' : 'great';
    return `<span class="score-badge score-color-${level}">${score}/10</span>`;
}

/* ---- Global Search ---- */

function debounce(fn, delay) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

function initGlobalSearch() {
    const input = document.getElementById('global-search');
    const fieldSelect = document.getElementById('search-field');
    const dropdown = document.getElementById('search-dropdown');
    if (!input || !dropdown) return;

    const FIELD_LABELS = {
        description: '描述',
        notes: '备注',
        solution: '解决方案',
    };

    const doSearch = debounce(async () => {
        const q = input.value.trim();
        if (!q) {
            dropdown.classList.remove('active');
            return;
        }
        const field = fieldSelect.value;
        dropdown.innerHTML = '<div class="search-loading"><span class="spinner"></span> 搜索中...</div>';
        dropdown.classList.add('active');

        try {
            const data = await apiCall(`/api/search/?q=${encodeURIComponent(q)}&field=${field}`);
            if (data.total === 0) {
                dropdown.innerHTML = '<div class="search-empty">未找到匹配结果</div>';
                return;
            }
            // Group by product > flow
            const groups = {};
            for (const r of data.results) {
                const key = `${r.product_name}>${r.flow_name}`;
                if (!groups[key]) {
                    groups[key] = { product: r.product_name, flow: r.flow_name, flow_id: r.flow_id, items: [] };
                }
                groups[key].items.push(r);
            }
            let html = '';
            for (const g of Object.values(groups)) {
                html += `<div class="search-result-group">${escapeHtmlSafe(g.product)} &gt; ${escapeHtmlSafe(g.flow)}</div>`;
                for (const item of g.items) {
                    const fieldLabel = FIELD_LABELS[item.matched_field] || item.matched_field;
                    html += `<div class="search-result-item" data-href="/flow/${item.flow_id}/view#step-${item.step_id}">
                        <div class="search-result-title">步骤 ${item.step_order}: ${escapeHtmlSafe(item.description || '(无描述)')}</div>
                        <div class="search-result-snippet"><span class="search-field-tag">${fieldLabel}</span> ${item.matched_text}</div>
                    </div>`;
                }
            }
            dropdown.innerHTML = html;
        } catch (err) {
            dropdown.innerHTML = `<div class="search-empty">搜索失败: ${escapeHtmlSafe(err.message)}</div>`;
        }
    }, 300);

    input.addEventListener('input', doSearch);
    fieldSelect.addEventListener('change', () => { if (input.value.trim()) doSearch(); });

    // Click result to navigate
    dropdown.addEventListener('click', (e) => {
        const item = e.target.closest('.search-result-item');
        if (item && item.dataset.href) {
            window.location.href = item.dataset.href;
            dropdown.classList.remove('active');
        }
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-wrapper')) {
            dropdown.classList.remove('active');
        }
    });

    // Close on ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') dropdown.classList.remove('active');
    });
}

function escapeHtmlSafe(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    initGlobalSearch();
    initLanguage();

    // Show beginner's guide on first visit of this session
    try {
        if (!localStorage.getItem('pathmind_guide_dismissed')
            && !sessionStorage.getItem('pathmind_guide_shown')) {
            sessionStorage.setItem('pathmind_guide_shown', 'true');
            showBeginnersGuide();
        }
    } catch (e) { /* storage unavailable */ }
});

/* ---- Beginner's Guide ---- */

function showBeginnersGuide() {
    const overlay = document.createElement('div');
    overlay.className = 'confirm-overlay active';
    overlay.innerHTML = `
        <div class="confirm-box guide-box">
            <h3 style="margin-bottom: 16px; font-size: 18px;" data-i18n-guide="guide_title">Welcome to PathMind / 欢迎使用路径智慧库</h3>
            <div class="guide-step">
                <h4 data-i18n-guide="guide_s1_title">1. 使用流程</h4>
                <p data-i18n-guide="guide_s1_body">创建产品 → 新建流程 → 录制步骤（截图+描述+评分） → AI 自动分析 → 导出到 Obsidian 知识库</p>
            </div>
            <div class="guide-step">
                <h4 data-i18n-guide="guide_s2_title">2. 悬浮窗录制</h4>
                <p data-i18n-guide="guide_s2_body">通过 <strong>系统托盘图标</strong> 打开桌面悬浮窗。在悬浮窗中选择产品和流程后，可使用 Ctrl+V 粘贴截图快速录制，也可以使用自动录制模式。</p>
            </div>
            <div class="guide-step">
                <h4 data-i18n-guide="guide_s3_title">3. 自动录制截图</h4>
                <p data-i18n-guide="guide_s3_body">在 <a href="/settings" style="color: var(--color-primary);">设置</a> 中配置 <strong>开始/停止录制热键</strong>，然后通过悬浮窗 REC 按钮或快捷键开始自动录制。录制期间 <strong>每次鼠标左键点击</strong> 都会触发截图（点击空白处也会截图）。每次截图后需要 <strong>输入步骤标题或跳过</strong> 才能继续下一次截图。如果截图不理想，可以稍后在 Web 页面中删除。</p>
            </div>
            <div class="guide-step">
                <h4 data-i18n-guide="guide_s4_title">4. AI 智能分析</h4>
                <p data-i18n-guide="guide_s4_body">在 <a href="/settings" style="color: var(--color-primary);">设置</a> 页面配置 <strong>AI API</strong>（支持 OpenAI 兼容接口），保存步骤后自动生成交互分析、体验评价和改进建议。</p>
            </div>
            <div class="guide-footer">
                <label class="guide-checkbox">
                    <input type="checkbox" id="guide-dismiss-check"> <span data-i18n-guide="guide_dismiss">不再自动显示</span>
                </label>
                <button class="btn btn-primary" id="guide-close-btn" data-i18n-guide="guide_close">我知道了</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    // Apply translations if in English mode
    if (currentLang === 'en' && _i18nDict) {
        overlay.querySelectorAll('[data-i18n-guide]').forEach(el => {
            const key = el.getAttribute('data-i18n-guide');
            if (_i18nDict[key]) el.innerHTML = _i18nDict[key];
        });
    }

    overlay.querySelector('#guide-close-btn').onclick = () => {
        try {
            if (overlay.querySelector('#guide-dismiss-check').checked) {
                localStorage.setItem('pathmind_guide_dismissed', 'true');
            }
        } catch (e) { /* localStorage unavailable */ }
        overlay.remove();
    };
    overlay.onclick = (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    };
}

/* ---- Language Switching (i18n) ---- */

let currentLang = 'zh';
let _i18nDict = null;       // loaded from static JSON
let _i18nPlaceholders = null;

async function _loadI18nDict() {
    if (_i18nDict) return;
    try {
        const resp = await fetch('/static/i18n/en.json');
        const data = await resp.json();
        _i18nPlaceholders = data._placeholders || {};
        delete data._placeholders;
        _i18nDict = data;
    } catch (e) {
        _i18nDict = {};
        _i18nPlaceholders = {};
    }
}

async function initLanguage() {
    try {
        currentLang = localStorage.getItem('pathmind_lang') || 'zh';
    } catch (e) {}

    const btn = document.getElementById('lang-toggle');
    if (btn) btn.textContent = currentLang === 'zh' ? '中' : 'EN';

    if (currentLang === 'en') {
        await _loadI18nDict();
        applyTranslations();
    }
}

async function toggleLanguage() {
    currentLang = currentLang === 'zh' ? 'en' : 'zh';
    try {
        localStorage.setItem('pathmind_lang', currentLang);
    } catch (e) {}

    const btn = document.getElementById('lang-toggle');
    if (btn) btn.textContent = currentLang === 'zh' ? '中' : 'EN';

    if (currentLang === 'en') {
        await _loadI18nDict();
        applyTranslations();
    } else {
        restoreOriginalTexts();
    }
}

function applyTranslations() {
    if (!_i18nDict) return;
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (_i18nDict[key]) {
            el.textContent = _i18nDict[key];
        }
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (_i18nPlaceholders[key]) {
            el.placeholder = _i18nPlaceholders[key];
        }
    });
}

function restoreOriginalTexts() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        el.textContent = el.getAttribute('data-i18n');
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        el.placeholder = el.getAttribute('data-i18n-placeholder');
    });
}
