// flow_record.js - Main recording page logic

const FLOW_ID = parseInt(window.location.pathname.split('/')[2]);
const DRAFT_KEY = `flow_draft_${FLOW_ID}`;
let stepManager;
let imageUploader;
let aiAssistant;

// Current editor state
let editingStepId = null; // null = new step, number = editing existing
let currentImageFile = null;
let currentImageUrl = null;
let currentScore = 0;
let hasUnsavedChanges = false;

document.addEventListener('DOMContentLoaded', async () => {
    stepManager = new StepManager('step-list', onStepSelected);
    aiAssistant = new AIAssistant();

    // Bridge for ai_comment.js compatibility
    window.getStepById = (id) => stepManager.getStep(id);

    imageUploader = new ImageUploader('upload-area', 'file-input', (file, url) => {
        currentImageFile = file;
        currentImageUrl = url;
        showImagePreview(url);
        markDirty();
        // Save image as base64 to draft
        fileToBase64(file).then(b64 => {
            saveDraft({ imageBase64: b64 });
        });
    });

    // Init score rating
    initScoreRating();

    // Bind auto-save on input changes
    bindAutoSave();

    // Load existing steps
    await loadSteps();

    // Restore draft if available
    restoreDraft();

    // Warn before closing with unsaved changes
    window.addEventListener('beforeunload', (e) => {
        if (hasUnsavedChanges) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
});

// =====================
// Auto-save / Draft
// =====================
function bindAutoSave() {
    const desc = document.getElementById('step-description');
    const notes = document.getElementById('step-notes');

    desc.addEventListener('input', () => { markDirty(); saveDraftFromForm(); });
    notes.addEventListener('input', () => { markDirty(); saveDraftFromForm(); });
}

function markDirty() {
    hasUnsavedChanges = true;
}

function markClean() {
    hasUnsavedChanges = false;
    clearDraft();
}

function saveDraftFromForm() {
    saveDraft({});
}

function saveDraft(extra) {
    const existing = getDraftData();
    const data = {
        ...existing,
        editingStepId: editingStepId,
        description: document.getElementById('step-description').value,
        notes: document.getElementById('step-notes').value,
        score: currentScore,
        imageUrl: currentImageUrl,
        timestamp: Date.now(),
        ...extra,
    };
    try {
        localStorage.setItem(DRAFT_KEY, JSON.stringify(data));
    } catch (e) {
        // localStorage full or unavailable, ignore
    }
}

function getDraftData() {
    try {
        const raw = localStorage.getItem(DRAFT_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch {
        return {};
    }
}

function clearDraft() {
    localStorage.removeItem(DRAFT_KEY);
}

function restoreDraft() {
    const draft = getDraftData();
    if (!draft.timestamp) return;

    // Only restore if draft is less than 24 hours old
    if (Date.now() - draft.timestamp > 24 * 60 * 60 * 1000) {
        clearDraft();
        return;
    }

    const hasContent = draft.description || draft.notes || draft.score || draft.imageBase64;
    if (!hasContent) return;

    // Show restore prompt
    const overlay = document.createElement('div');
    overlay.className = 'confirm-overlay active';

    const age = getTimeAgo(draft.timestamp);
    let preview = '';
    if (draft.description) preview += `描述: ${draft.description.substring(0, 50)}...\n`;
    if (draft.score) preview += `评分: ${draft.score}/10`;

    overlay.innerHTML = `
        <div class="confirm-box">
            <h3>发现未保存的草稿</h3>
            <p>${age}有一条未保存的步骤记录，是否恢复？</p>
            ${preview ? `<div style="text-align:left;background:var(--color-bg-input);padding:8px 12px;border-radius:6px;font-size:13px;color:var(--color-text-secondary);margin-bottom:16px;white-space:pre-line;">${escapeHtmlLocal(preview)}</div>` : ''}
            <div class="flex gap-8" style="justify-content: center;">
                <button class="btn btn-secondary" id="draft-discard">丢弃</button>
                <button class="btn btn-primary" id="draft-restore">恢复草稿</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    overlay.querySelector('#draft-discard').onclick = () => {
        clearDraft();
        overlay.remove();
    };
    overlay.querySelector('#draft-restore').onclick = () => {
        overlay.remove();
        applyDraft(draft);
    };
}

function applyDraft(draft) {
    // Open editor
    if (draft.editingStepId) {
        // Try to select the existing step
        const step = stepManager.getStep(draft.editingStepId);
        if (step) {
            selectStep(draft.editingStepId);
        } else {
            addNewStep();
        }
    } else {
        addNewStep();
    }

    // Fill form
    if (draft.description) {
        document.getElementById('step-description').value = draft.description;
    }
    if (draft.notes) {
        document.getElementById('step-notes').value = draft.notes;
    }
    if (draft.score) {
        setScore(draft.score);
    }

    // Restore image from base64
    if (draft.imageBase64) {
        const b64 = draft.imageBase64;
        // Convert base64 back to File for upload
        fetch(b64).then(res => res.blob()).then(blob => {
            const file = new File([blob], 'draft_image.png', { type: 'image/png' });
            currentImageFile = file;
            currentImageUrl = URL.createObjectURL(blob);
            showImagePreview(currentImageUrl);
        });
    }

    hasUnsavedChanges = true;
    showToast('草稿已恢复', 'info');
}

function getTimeAgo(timestamp) {
    const diff = Date.now() - timestamp;
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}小时前`;
    return '超过一天前';
}

function escapeHtmlLocal(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =====================
// Core Logic
// =====================
async function loadSteps() {
    try {
        const steps = await apiCall(`/api/steps/?flow_id=${FLOW_ID}`);
        stepManager.setSteps(steps);
    } catch (error) {
        showToast('加载步骤失败: ' + error.message, 'error');
    }
}

function initScoreRating() {
    const container = document.getElementById('score-rating');
    const btns = container.querySelectorAll('.score-btn');

    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            const score = parseInt(btn.dataset.score);
            setScore(score);
            markDirty();
            saveDraftFromForm();
        });

        btn.addEventListener('mouseenter', () => {
            const score = parseInt(btn.dataset.score);
            highlightScore(score);
        });
    });

    container.addEventListener('mouseleave', () => {
        highlightScore(currentScore);
    });
}

function setScore(score) {
    currentScore = score;
    highlightScore(score);
    const label = document.getElementById('score-label');
    const labels = ['', '极差', '很差', '差', '较差', '一般', '尚可', '较好', '好', '很好', '优秀'];
    if (score > 0) {
        label.textContent = `${score}/10 - ${labels[score]}`;
    } else {
        label.textContent = '未评分';
    }
}

function highlightScore(score) {
    const btns = document.querySelectorAll('#score-rating .score-btn');
    btns.forEach(btn => {
        const s = parseInt(btn.dataset.score);
        btn.classList.toggle('active', s <= score);
        // Color coding
        btn.classList.remove('score-low', 'score-mid', 'score-ok', 'score-good', 'score-great');
        if (s <= score && score > 0) {
            if (score <= 3) btn.classList.add('score-low');
            else if (score <= 5) btn.classList.add('score-mid');
            else if (score <= 7) btn.classList.add('score-ok');
            else if (score <= 9) btn.classList.add('score-good');
            else btn.classList.add('score-great');
        }
    });
}

// --- Step Selection ---
function selectStep(stepId) {
    const step = stepManager.getStep(stepId);
    if (!step) return;

    editingStepId = stepId;
    stepManager.setActive(stepId);
    showEditorForm();

    // Fill form with step data
    document.getElementById('step-description').value = step.description || '';
    document.getElementById('step-notes').value = step.notes || '';
    setScore(step.score || 0);

    // Show image
    if (step.image_path) {
        currentImageUrl = `/api/steps/image/${step.image_path}`;
        currentImageFile = null; // Not a new file
        showImagePreview(currentImageUrl);
    } else {
        hideImagePreview();
        currentImageFile = null;
        currentImageUrl = null;
    }

    // Update title
    document.getElementById('editor-step-title').textContent = `步骤 ${step.order}`;
    document.getElementById('btn-delete-step').style.display = 'inline-flex';

    // Clear AI suggestion
    aiAssistant.clearSuggestion();

    // Load AI comment panel for this step
    refreshAiCommentPanel(stepId);

    // Loaded from server = clean state
    hasUnsavedChanges = false;
}

function addNewStep() {
    editingStepId = null;
    stepManager.setActive(null);
    showEditorForm();
    clearEditorForm();

    const nextOrder = stepManager.getSteps().length + 1;
    document.getElementById('editor-step-title').textContent = `新步骤 #${nextOrder}`;
    document.getElementById('btn-delete-step').style.display = 'none';

    // Hide AI comment panel for new steps
    const panel = document.getElementById('ai-comment-panel');
    if (panel) {
        panel.style.display = 'none';
        document.getElementById('ai-comment-content').innerHTML =
            '<p class="text-muted text-small">保存步骤后可生成 AI 评论</p>';
    }
}

function onStepSelected(stepId) {
    selectStep(stepId);
}

// --- Editor Form ---
function showEditorForm() {
    document.getElementById('editor-empty').style.display = 'none';
    document.getElementById('editor-form').style.display = 'block';
}

function hideEditorForm() {
    document.getElementById('editor-empty').style.display = 'flex';
    document.getElementById('editor-form').style.display = 'none';
}

function clearEditorForm() {
    document.getElementById('step-description').value = '';
    document.getElementById('step-notes').value = '';
    setScore(0);
    document.getElementById('score-label').textContent = '未评分';
    hideImagePreview();
    currentImageFile = null;
    currentImageUrl = null;
    imageUploader.clear();
    aiAssistant.clearSuggestion();
}

function showImagePreview(url) {
    document.getElementById('upload-area-container').querySelector('.upload-area').style.display = 'none';
    const container = document.getElementById('image-preview-container');
    container.style.display = 'block';
    document.getElementById('image-preview').src = url;
}

function hideImagePreview() {
    document.getElementById('upload-area-container').querySelector('.upload-area').style.display = 'flex';
    document.getElementById('image-preview-container').style.display = 'none';
    document.getElementById('image-preview').src = '';
}

function replaceImage() {
    document.getElementById('file-input').click();
}

function removeImage() {
    currentImageFile = null;
    currentImageUrl = null;
    imageUploader.clear();
    hideImagePreview();
    markDirty();
    saveDraft({ imageBase64: null, imageUrl: null });
}

function cancelEdit() {
    editingStepId = null;
    stepManager.setActive(null);
    hideEditorForm();
    clearEditorForm();
    markClean();
}

// --- Save Step ---
async function saveStep() {
    const description = document.getElementById('step-description').value.trim();
    const notes = document.getElementById('step-notes').value.trim();
    const score = currentScore;

    const formData = new FormData();
    formData.append('description', description);
    formData.append('notes', notes);
    if (score > 0) formData.append('score', score);

    if (currentImageFile) {
        formData.append('image', currentImageFile);
    }

    const btn = document.getElementById('btn-save-step');
    btn.disabled = true;
    btn.textContent = '保存中...';

    try {
        if (editingStepId) {
            // Update existing step
            const updated = await apiCall(`/api/steps/${editingStepId}`, {
                method: 'PUT',
                body: formData,
            });
            stepManager.updateStep(updated);
            showToast('步骤已更新', 'success');
        } else {
            // Create new step
            formData.append('flow_id', FLOW_ID);
            const created = await apiCall('/api/steps/', {
                method: 'POST',
                body: formData,
            });
            stepManager.addStep(created);
            editingStepId = created.id;
            stepManager.setActive(created.id);
            document.getElementById('btn-delete-step').style.display = 'inline-flex';
            document.getElementById('editor-step-title').textContent = `步骤 ${created.order}`;
            showToast('步骤已保存', 'success');
        }
        // Saved to server, clear dirty state and draft
        markClean();
        // Show AI comment panel now that step is saved
        refreshAiCommentPanel(editingStepId);
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '保存步骤';
    }
}

// --- Delete Step ---
async function deleteCurrentStep() {
    if (!editingStepId) return;

    const confirmed = await showConfirm('删除步骤', '确定要删除这个步骤吗？截图也会被删除。');
    if (!confirmed) return;

    try {
        await apiCall(`/api/steps/${editingStepId}`, { method: 'DELETE' });
        stepManager.removeStep(editingStepId);
        editingStepId = null;
        hideEditorForm();
        clearEditorForm();
        markClean();
        showToast('步骤已删除', 'success');
        // Reload to get correct ordering
        await loadSteps();
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

// --- AI Analysis ---
async function requestAiAnalysis() {
    // Need an image to analyze
    if (!currentImageUrl && !currentImageFile) {
        showToast('请先上传截图再使用AI分析', 'error');
        return;
    }

    let imageBase64;
    if (currentImageFile) {
        // Read file as base64
        imageBase64 = await fileToBase64(currentImageFile);
    } else if (currentImageUrl && currentImageUrl.startsWith('/api/')) {
        // Fetch from server and convert
        try {
            const response = await fetch(currentImageUrl);
            const blob = await response.blob();
            imageBase64 = await blobToBase64(blob);
        } catch {
            showToast('无法读取图片', 'error');
            return;
        }
    }

    if (!imageBase64) {
        showToast('无法处理图片', 'error');
        return;
    }

    // Remove data URL prefix if present
    if (imageBase64.includes(',')) {
        imageBase64 = imageBase64.split(',')[1];
    }

    // Build context
    const steps = stepManager.getSteps();
    const currentOrder = editingStepId
        ? stepManager.getStep(editingStepId)?.order || steps.length + 1
        : steps.length + 1;

    const previousSteps = steps
        .filter(s => s.order < currentOrder)
        .map(s => `步骤${s.order}: ${s.description || '(无描述)'}`)
        .join('\n');

    // Get product and flow name from breadcrumb
    const crumbs = document.querySelectorAll('.nav-crumb');
    const productName = crumbs[0]?.textContent || '';
    const flowName = crumbs[1]?.textContent || '';

    const context = {
        product_name: productName,
        flow_name: flowName,
        step_order: currentOrder,
        previous_steps: previousSteps,
    };

    await aiAssistant.analyzeScreenshot(imageBase64, context);
}

function adoptAiSuggestion() {
    const suggestion = aiAssistant.getSuggestion();
    if (!suggestion) return;

    if (suggestion.suggested_title) {
        document.getElementById('step-description').value = suggestion.suggested_title;
        markDirty();
        saveDraftFromForm();
    }
    aiAssistant.clearSuggestion();
    showToast('已采纳AI建议', 'success');
}

function dismissAiSuggestion() {
    aiAssistant.clearSuggestion();
}

// --- Complete Recording ---
async function completeRecording() {
    const steps = stepManager.getSteps();
    if (steps.length === 0) {
        showToast('至少需要一个步骤才能完成录制', 'error');
        return;
    }

    const confirmed = await showConfirm('完成录制', '确定要完成录制吗？完成后可以生成AI总结并导出到Obsidian。');
    if (!confirmed) return;

    try {
        markClean(); // Clear draft before navigating away
        await apiCall(`/api/flows/${FLOW_ID}/complete`, { method: 'POST' });
        showToast('录制已完成，正在生成AI总结...', 'info');

        // Try to generate AI summary
        const summary = await aiAssistant.generateSummary(FLOW_ID);
        if (summary) {
            showToast('AI总结已生成', 'success');
            window.location.href = `/flow/${FLOW_ID}/summary`;
        } else {
            showToast('录制已完成（AI总结生成失败，可稍后重试）', 'info');
            window.location.href = `/flow/${FLOW_ID}/view`;
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// --- Finish Editing (for completed flows) ---
async function finishEditing() {
    const steps = stepManager.getSteps();
    if (steps.length === 0) {
        showToast('至少需要一个步骤', 'error');
        return;
    }

    const result = await showCustomDialog(
        '保存修改',
        '流程已修改，是否重新生成AI总结？',
        [
            { id: 'cancel', text: '取消', class: 'btn-secondary' },
            { id: 'save', text: '仅保存', class: 'btn-secondary' },
            { id: 'regenerate', text: '重新生成总结', class: 'btn-primary' },
        ]
    );

    if (!result || result === 'cancel') return;

    markClean();

    if (result === 'regenerate') {
        try {
            showToast('正在重新生成AI总结...', 'info');
            const summary = await aiAssistant.generateSummary(FLOW_ID);
            if (summary) {
                showToast('AI总结已更新', 'success');
                window.location.href = `/flow/${FLOW_ID}/summary`;
            } else {
                showToast('AI总结生成失败，已保存修改', 'info');
                window.location.href = `/flow/${FLOW_ID}/view`;
            }
        } catch (error) {
            showToast('AI总结生成失败: ' + error.message, 'error');
            window.location.href = `/flow/${FLOW_ID}/view`;
        }
    } else {
        // save only
        window.location.href = `/flow/${FLOW_ID}/view`;
    }
}

// --- Utilities ---
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

// =====================
// AI Comment Panel (flow_record integration)
// =====================

/**
 * Refresh the AI comment panel for the given step.
 */
function refreshAiCommentPanel(stepId) {
    const panel = document.getElementById('ai-comment-panel');
    const content = document.getElementById('ai-comment-content');
    if (!panel || !content) return;

    if (!stepId) {
        panel.style.display = 'none';
        return;
    }

    const step = stepManager.getStep(stepId);
    if (!step) {
        panel.style.display = 'none';
        return;
    }

    panel.style.display = 'block';

    const hasComment = step.ai_interaction || step.ai_description || step.ai_experience || step.ai_improvement;
    const hasImage = !!step.image_path;
    const genBtn = document.getElementById('btn-gen-ai-comment');

    if (hasComment) {
        // Render AI comment fields
        let html = '';
        for (const [field, cfg] of Object.entries(AI_FIELD_CONFIG)) {
            let value = step[field] || '';
            let label = cfg.label;

            // Backward compatibility
            if (field === 'ai_interaction' && !value && step.ai_description) {
                value = step.ai_description;
                label = '界面描述 (旧版)';
            }

            const charCount = value.length;
            html += `
                <div class="ai-field-group" data-step-id="${step.id}" data-field="${field}">
                    <div class="ai-field-header">
                        <span class="ai-field-label">${label}</span>
                        <span class="ai-field-count ${charCount > cfg.maxLen ? 'over' : ''}">${charCount}/${cfg.maxLen}</span>
                    </div>
                    <div class="ai-field-value">${formatBulletHtml(value)}</div>
                </div>`;
        }
        if (step.score) {
            html += `<div class="ai-field-group"><div class="ai-field-header"><span class="ai-field-label">AI 评分</span></div><div class="ai-field-value">${step.score}/10</div></div>`;
        }
        content.innerHTML = html;
        if (genBtn) {
            genBtn.textContent = '重新生成';
            genBtn.className = 'btn btn-sm btn-secondary';
        }
    } else if (hasImage) {
        content.innerHTML = '<p class="text-muted text-small">尚未生成 AI 评论，点击右上方按钮生成</p>';
        if (genBtn) {
            genBtn.textContent = '生成 AI 评论';
            genBtn.className = 'btn btn-sm btn-primary';
        }
    } else {
        content.innerHTML = '<p class="text-muted text-small">需要先上传截图才能生成 AI 评论</p>';
        if (genBtn) {
            genBtn.textContent = '生成 AI 评论';
            genBtn.className = 'btn btn-sm btn-primary';
            genBtn.disabled = true;
        }
    }
}

/**
 * Generate AI comment from the recording/editing page.
 */
async function generateAiCommentFromRecord() {
    if (!editingStepId) {
        showToast('请先保存步骤再生成 AI 评论', 'error');
        return;
    }

    const step = stepManager.getStep(editingStepId);
    if (!step || !step.image_path) {
        showToast('该步骤没有截图，无法生成 AI 评论', 'error');
        return;
    }

    const btn = document.getElementById('btn-gen-ai-comment');
    const oldText = btn ? btn.textContent : '';
    if (btn) {
        btn.innerHTML = '<span class="spinner-sm"></span> 生成中...';
        btn.disabled = true;
    }

    try {
        const result = await apiCall('/api/ai/generate-step-comment', {
            method: 'POST',
            body: { step_id: editingStepId }
        });

        // Update step data in stepManager
        const s = stepManager.getStep(editingStepId);
        if (s) {
            s.ai_interaction = result.ai_interaction || '';
            s.ai_experience = result.ai_experience || '';
            s.ai_improvement = result.ai_improvement || '';
            if (result.score) {
                s.score = result.score;
                setScore(result.score);
            }
        }

        refreshAiCommentPanel(editingStepId);
        showToast('AI 评论已生成', 'success');
    } catch (error) {
        showToast('AI 评论生成失败: ' + error.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = oldText;
        }
    }
}

/**
 * Show floating window usage tip with dependency check.
 */
function showFloatingWindowTip() {
    const overlay = document.createElement('div');
    overlay.className = 'confirm-overlay active';
    overlay.innerHTML = `
        <div class="confirm-box" style="max-width: 420px;">
            <h3>悬浮窗录制模式</h3>
            <p style="line-height:1.6; white-space:pre-line;">可通过系统托盘打开悬浮窗，进行自动截图录制。

自动录制模式下，每次点击操作会自动截图，并可选择是否触发 AI 评论生成。

使用方法：
1. 点击系统托盘图标打开悬浮窗
2. 在悬浮窗中选择当前流程
3. 点击 REC 按钮或按快捷键开始自动录制</p>
            <div id="floating-dep-result" style="margin-top:12px;"></div>
            <div class="flex gap-8" style="justify-content: center; margin-top: 16px;">
                <button class="btn btn-secondary" id="floating-check-btn" onclick="checkFloatingDeps()">检查依赖</button>
                <button class="btn btn-primary" id="floating-close-btn">关闭</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    overlay.querySelector('#floating-close-btn').onclick = () => overlay.remove();
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
}

/**
 * Check floating window dependencies via API.
 */
async function checkFloatingDeps() {
    const btn = document.getElementById('floating-check-btn');
    const result = document.getElementById('floating-dep-result');
    if (!btn || !result) return;

    btn.disabled = true;
    btn.textContent = '检查中...';
    result.innerHTML = '';

    try {
        const data = await apiCall('/api/config/check-floating-deps');
        let html = '<div style="text-align:left; font-size:13px;">';
        for (const dep of data.deps) {
            if (dep.installed) {
                html += `<div style="margin-bottom:4px;">✅ <b>${dep.name}</b> <span style="color:var(--color-text-muted);">(${dep.version})</span></div>`;
            } else {
                html += `<div style="margin-bottom:4px;">❌ <b>${dep.name}</b> <span style="color:var(--color-danger);">未安装</span>
                    <code style="font-size:11px; background:var(--color-bg-input); padding:2px 6px; border-radius:3px; margin-left:4px;">${dep.pip}</code></div>`;
            }
        }
        if (data.ready) {
            html += '<div style="margin-top:8px; color:var(--color-success); font-weight:600;">所有依赖已就绪，可以使用悬浮窗</div>';
        } else {
            html += '<div style="margin-top:8px; color:var(--color-danger);">请安装缺失的依赖后重启应用</div>';
        }
        html += '</div>';
        result.innerHTML = html;
    } catch (err) {
        result.innerHTML = '<span style="color:var(--color-danger);">检查失败: ' + (err.message || err) + '</span>';
    } finally {
        btn.textContent = '重新检查';
        btn.disabled = false;
    }
}
