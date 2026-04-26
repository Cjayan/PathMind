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

document.addEventListener('DOMContentLoaded', initGlobalSearch);
