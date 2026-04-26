/**
 * data_sync.js - Data export/import/backup frontend logic
 */

document.addEventListener('DOMContentLoaded', () => {
    loadBackups();
});

// =====================
// Export
// =====================
async function exportFull() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '导出中...';
    try {
        const resp = await fetch('/api/data/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'full' }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.error || '导出失败');
        }
        const blob = await resp.blob();
        downloadBlob(blob, resp.headers.get('content-disposition'));
        showToast('全量导出完成', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '全量导出';
    }
}

async function exportIncremental() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '导出中...';
    try {
        const resp = await fetch('/api/data/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'incremental' }),
        });
        if (resp.headers.get('content-type')?.includes('application/json')) {
            const data = await resp.json();
            if (data.message) {
                showToast(data.message, 'info');
                return;
            }
        }
        if (!resp.ok) {
            throw new Error('导出失败');
        }
        const blob = await resp.blob();
        downloadBlob(blob, resp.headers.get('content-disposition'));
        showToast('增量导出完成', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '增量导出';
    }
}

function downloadBlob(blob, disposition) {
    let filename = 'export.zip';
    if (disposition) {
        const match = disposition.match(/filename=(.+)/);
        if (match) filename = match[1].replace(/"/g, '');
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// =====================
// Import
// =====================
function triggerImportUpload() {
    document.getElementById('import-file-input').click();
}

async function onImportFileSelected(input) {
    if (!input.files.length) return;
    const file = input.files[0];
    if (!file.name.endsWith('.zip')) {
        showToast('请选择 ZIP 文件', 'error');
        return;
    }

    const preview = document.getElementById('import-preview');
    preview.innerHTML = '<p class="text-muted">正在解析...</p>';
    preview.style.display = 'block';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const resp = await fetch('/api/data/import-preview', {
            method: 'POST',
            body: formData,
        });
        const data = await resp.json();
        if (!resp.ok) {
            throw new Error(data.error || '解析失败');
        }
        renderImportPreview(data);
    } catch (error) {
        preview.innerHTML = `<p style="color:var(--color-danger);">${error.message}</p>`;
    }
    input.value = '';
}

function renderImportPreview(data) {
    const preview = document.getElementById('import-preview');
    const c = data.changes;
    const src = data.source;

    let html = `
        <div class="import-source">
            <strong>来源:</strong> ${src.instance_name || '未知'} | 
            <strong>类型:</strong> ${src.type === 'full' ? '全量' : '增量'} | 
            <strong>导出时间:</strong> ${src.exported_at ? new Date(src.exported_at).toLocaleString('zh-CN') : '-'}
        </div>
        <table class="import-table">
            <thead><tr><th></th><th>新增</th><th>更新</th><th>无变化</th></tr></thead>
            <tbody>
                <tr><td>产品</td><td class="add-count">${c.products.add.length}</td><td class="update-count">${c.products.update.length}</td><td>${c.products.unchanged}</td></tr>
                <tr><td>流程</td><td class="add-count">${c.flows.add.length}</td><td class="update-count">${c.flows.update.length}</td><td>${c.flows.unchanged}</td></tr>
                <tr><td>步骤</td><td class="add-count">${c.steps.add}</td><td class="update-count">${c.steps.update}</td><td>${c.steps.unchanged}</td></tr>
                <tr><td>图片</td><td class="add-count">${c.images.new}</td><td class="update-count">${c.images.replace}</td><td>-</td></tr>
            </tbody>
        </table>`;

    if (c.products.add.length > 0) {
        html += `<div class="import-detail"><strong>新增产品:</strong> ${c.products.add.map(p => p.name).join(', ')}</div>`;
    }
    if (c.flows.add.length > 0) {
        html += `<div class="import-detail"><strong>新增流程:</strong> ${c.flows.add.map(f => `${f.name} (${f.product_name})`).join(', ')}</div>`;
    }

    html += `
        <div class="import-actions">
            <button class="btn btn-secondary" onclick="cancelImport()">取消</button>
            <button class="btn btn-primary" onclick="confirmImport('${data.preview_id}')">确认导入</button>
        </div>`;

    preview.innerHTML = html;
}

function cancelImport() {
    document.getElementById('import-preview').style.display = 'none';
}

async function confirmImport(previewId) {
    const preview = document.getElementById('import-preview');
    preview.innerHTML = '<p class="text-muted">正在导入（已自动创建备份）...</p>';

    try {
        const result = await apiCall('/api/data/import', {
            method: 'POST',
            body: { preview_id: previewId },
        });
        const a = result.added;
        const u = result.updated;
        showToast(
            `导入完成: 新增 ${a.products}产品/${a.flows}流程/${a.steps}步骤, 更新 ${u.products}产品/${u.flows}流程/${u.steps}步骤`,
            'success'
        );
        preview.style.display = 'none';
        loadBackups();
    } catch (error) {
        preview.innerHTML = `<p style="color:var(--color-danger);">导入失败: ${error.message}</p>`;
    }
}

// =====================
// Backups
// =====================
async function loadBackups() {
    try {
        const backups = await apiCall('/api/data/backups');
        renderBackups(backups);
    } catch (error) {
        console.error('Failed to load backups:', error);
    }
}

function renderBackups(backups) {
    const container = document.getElementById('backup-list');
    if (!container) return;

    if (backups.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无备份</p>';
        return;
    }

    const REASON_LABELS = {
        manual: '手动',
        pre_import: '导入前自动',
        pre_restore: '恢复前自动',
    };

    container.innerHTML = backups.map(b => {
        const label = REASON_LABELS[b.reason] || b.reason;
        const time = b.created_at ? new Date(b.created_at).toLocaleString('zh-CN') : '-';
        const size = b.db_size ? `${(b.db_size / 1024).toFixed(1)} KB` : '-';
        return `
        <div class="backup-item">
            <div class="backup-info">
                <strong>${label}</strong>
                <span class="text-muted text-small">${time}</span>
                <span class="text-muted text-small">DB: ${size}</span>
            </div>
            <div class="backup-actions">
                <button class="btn btn-sm btn-secondary" onclick="restoreBackup('${b.backup_id}')">恢复</button>
                <button class="btn btn-sm btn-danger" onclick="deleteBackup('${b.backup_id}')">删除</button>
            </div>
        </div>`;
    }).join('');
}

async function createManualBackup() {
    try {
        await apiCall('/api/data/backups', { method: 'POST' });
        showToast('备份已创建', 'success');
        loadBackups();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function restoreBackup(backupId) {
    const confirmed = await showConfirm('恢复备份', '确定要恢复到此备份吗？当前数据将被替换（会自动创建安全备份）。');
    if (!confirmed) return;
    try {
        await apiCall('/api/data/restore', {
            method: 'POST',
            body: { backup_id: backupId },
        });
        showToast('已恢复，正在刷新...', 'success');
        setTimeout(() => window.location.reload(), 1000);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteBackup(backupId) {
    const confirmed = await showConfirm('删除备份', '确定要删除此备份吗？');
    if (!confirmed) return;
    try {
        await apiCall(`/api/data/backups/${backupId}`, { method: 'DELETE' });
        showToast('备份已删除', 'success');
        loadBackups();
    } catch (error) {
        showToast(error.message, 'error');
    }
}
