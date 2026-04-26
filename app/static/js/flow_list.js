/**
 * flow_list.js - Shared flow list rendering with drag sort, pin, and color mark
 * Used by both product_detail.html and flows.html
 */

const MARK_COLORS = [
    { id: 'red', hex: '#ef4444' },
    { id: 'orange', hex: '#f97316' },
    { id: 'yellow', hex: '#eab308' },
    { id: 'green', hex: '#22c55e' },
    { id: 'blue', hex: '#3b82f6' },
    { id: 'purple', hex: '#a855f7' },
];

let _flowSortable = null;
let _currentFlows = [];
let _onFlowsChanged = null;  // callback after data changes

function initFlowList(containerId, onChanged) {
    _onFlowsChanged = onChanged;
    const container = document.getElementById(containerId);
    if (!container) return;

    _flowSortable = new Sortable(container, {
        handle: '.flow-drag-handle',
        animation: 150,
        ghostClass: 'flow-card-ghost',
        onEnd: onFlowSortEnd,
    });

    // Close mark picker on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.mark-picker-popup') && !e.target.closest('.flow-mark-dot')) {
            document.querySelectorAll('.mark-picker-popup').forEach(p => p.remove());
        }
    });
}

function renderFlowCards(flows, containerId) {
    _currentFlows = flows;
    const container = document.getElementById(containerId);
    if (!container) return;

    if (flows.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = flows.map(f => {
        const pinClass = f.is_pinned ? ' pinned' : '';
        const pinIcon = f.is_pinned ? '📌' : '<span class="pin-inactive">📌</span>';
        const markDot = f.mark_color
            ? `<span class="flow-mark-dot" style="background:${getMarkHex(f.mark_color)};" data-flow-id="${f.id}" onclick="showMarkPicker(${f.id}, this)"></span>`
            : `<span class="flow-mark-dot flow-mark-empty" data-flow-id="${f.id}" onclick="showMarkPicker(${f.id}, this)"></span>`;
        const statusBadge = f.status === 'recording'
            ? '<span class="badge badge-recording">录制中</span>'
            : '<span class="badge badge-completed">已完成</span>';
        const scoreHtml = f.average_score
            ? `${renderStars(Math.round(f.average_score))} ${f.average_score}`
            : '<span class="text-muted">-</span>';
        const productLabel = f.product_name
            ? `<span class="flow-card-product">${escapeHtmlSafe(f.product_name)}</span>`
            : '';

        const actionBtns = [];
        if (f.status === 'recording') {
            actionBtns.push(`<a href="/flow/${f.id}/record" class="btn btn-sm btn-primary">继续录制</a>`);
        } else {
            actionBtns.push(`<a href="/flow/${f.id}/view" class="btn btn-sm btn-secondary">查看</a>`);
            actionBtns.push(`<a href="/flow/${f.id}/record" class="btn btn-sm btn-secondary">编辑</a>`);
        }
        if (f.has_summary) {
            actionBtns.push(`<a href="/flow/${f.id}/summary" class="btn btn-sm btn-secondary">AI总结</a>`);
        }
        actionBtns.push(`<button class="btn btn-sm btn-secondary" onclick="exportFlow(${f.id})">导出</button>`);
        actionBtns.push(`<button class="btn btn-sm btn-danger" onclick="deleteFlow(${f.id}, '${escapeHtmlSafe(f.name)}')">删除</button>`);

        return `
        <div class="flow-card${pinClass}" data-flow-id="${f.id}">
            <div class="flow-drag-handle" title="拖拽排序">⋮⋮</div>
            <div class="flow-card-pin" onclick="togglePin(${f.id})" title="${f.is_pinned ? '取消置顶' : '置顶'}">${pinIcon}</div>
            ${markDot}
            <div class="flow-card-body">
                <div class="flow-card-title">
                    ${productLabel}
                    <strong>${escapeHtmlSafe(f.name)}</strong>
                </div>
                <div class="flow-card-meta">
                    <span>${f.step_count} 步</span>
                    <span>${scoreHtml}</span>
                    ${statusBadge}
                    <span class="text-muted text-small">${formatDate(f.updated_at)}</span>
                </div>
            </div>
            <div class="flow-card-actions">${actionBtns.join('')}</div>
        </div>`;
    }).join('');
}

function getMarkHex(colorId) {
    const c = MARK_COLORS.find(m => m.id === colorId);
    return c ? c.hex : '#64748b';
}

async function onFlowSortEnd(evt) {
    const container = evt.from;
    const ids = Array.from(container.children).map(el => parseInt(el.dataset.flowId));
    try {
        await apiCall('/api/flows/reorder', {
            method: 'POST',
            body: { flow_ids: ids },
        });
    } catch (error) {
        showToast('排序保存失败: ' + error.message, 'error');
        if (_onFlowsChanged) _onFlowsChanged();
    }
}

async function togglePin(flowId) {
    const flow = _currentFlows.find(f => f.id === flowId);
    if (!flow) return;
    try {
        await apiCall(`/api/flows/${flowId}`, {
            method: 'PUT',
            body: { is_pinned: !flow.is_pinned },
        });
        if (_onFlowsChanged) _onFlowsChanged();
    } catch (error) {
        showToast('操作失败: ' + error.message, 'error');
    }
}

function showMarkPicker(flowId, anchor) {
    // Remove existing pickers
    document.querySelectorAll('.mark-picker-popup').forEach(p => p.remove());

    const picker = document.createElement('div');
    picker.className = 'mark-picker-popup';

    let html = '';
    MARK_COLORS.forEach(c => {
        html += `<span class="mark-picker-dot" style="background:${c.hex};" data-color="${c.id}" title="${c.id}"></span>`;
    });
    html += `<span class="mark-picker-dot mark-picker-clear" data-color="" title="清除">×</span>`;
    picker.innerHTML = html;

    anchor.parentElement.appendChild(picker);

    picker.addEventListener('click', async (e) => {
        const dot = e.target.closest('[data-color]');
        if (!dot) return;
        const color = dot.dataset.color || null;
        picker.remove();
        try {
            await apiCall(`/api/flows/${flowId}`, {
                method: 'PUT',
                body: { mark_color: color },
            });
            if (_onFlowsChanged) _onFlowsChanged();
        } catch (error) {
            showToast('标记失败: ' + error.message, 'error');
        }
    });
}
