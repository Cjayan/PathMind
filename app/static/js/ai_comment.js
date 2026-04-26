// ai_comment.js - AI structured comment generation & editing (shared by flow_view and flow_record)

const AI_FIELD_CONFIG = {
    ai_interaction: { label: '互动预测', maxLen: 300, placeholder: 'AI 将预测界面交互元素的功能...' },
    ai_experience:  { label: '体验感受', maxLen: 300, placeholder: 'AI 将评价操作体验...' },
    ai_improvement: { label: '改进建议', maxLen: 300, placeholder: 'AI 将提出改进建议...' },
};

/**
 * Format bullet-point text as HTML list.
 * Handles multiple formats: \n-separated, •-separated, and Chinese sentence splits.
 */
function formatBulletHtml(text) {
    if (!text) return '<span class="text-muted">(未生成)</span>';
    let lines = text.split('\n').filter(l => l.trim());

    // If single block but contains '•' markers, split by '•'
    if (lines.length <= 1 && text.includes('•')) {
        lines = text.split('•').map(s => s.trim()).filter(s => s);
    }

    // If still single block, try splitting by Chinese sentence ending '。'
    if (lines.length <= 1) {
        const sentences = (text.match(/[^。]+。?/g) || []).map(s => s.trim()).filter(s => s);
        if (sentences.length > 1) {
            lines = sentences;
        }
    }

    // Truly single-point text → plain
    if (lines.length <= 1) {
        return escapeHtml(text);
    }

    return '<ul class="ai-bullet-list">' +
        lines.map(l => {
            const clean = l.replace(/^[•\-\*\d+\.]\s*/, '').trim();
            return '<li>' + escapeHtml(clean) + '</li>';
        }).join('') + '</ul>';
}

/**
 * Generate AI comment for a step. Called when user clicks the generate button.
 */
async function generateAiComment(stepId) {
    const btn = document.getElementById(`ai-gen-btn-${stepId}`);
    if (!btn) return;

    const oldHtml = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-sm"></span> 生成中...';
    btn.disabled = true;

    try {
        const result = await apiCall('/api/ai/generate-step-comment', {
            method: 'POST',
            body: { step_id: stepId }
        });

        // Update local data
        const step = getStepById(stepId);
        if (step) {
            step.ai_interaction = result.ai_interaction || '';
            step.ai_experience = result.ai_experience || '';
            step.ai_improvement = result.ai_improvement || '';
            if (result.score) step.score = result.score;
        }

        // Re-render: flow_view uses renderStepsView, flow_record uses refreshAiCommentPanel
        if (typeof renderStepsView === 'function' && typeof stepsData !== 'undefined') {
            renderStepsView(stepsData);
        } else if (typeof refreshAiCommentPanel === 'function') {
            refreshAiCommentPanel(stepId);
        }
        showToast('AI 评论已生成', 'success');
    } catch (error) {
        showToast(error.message, 'error');
        btn.innerHTML = oldHtml;
        btn.disabled = false;
    }
}

/**
 * Regenerate AI comment with confirmation.
 */
async function regenerateAiComment(stepId) {
    const confirmed = await showConfirm('重新生成', '重新生成将覆盖当前的 AI 评论和评分，是否继续？');
    if (!confirmed) return;
    await generateAiComment(stepId);
}

/**
 * Render the AI comment section HTML for a step.
 */
function renderAiCommentSection(step) {
    const hasComment = step.ai_interaction || step.ai_description || step.ai_experience || step.ai_improvement;
    const hasImage = !!step.image_path;

    let html = '<div class="ai-comment-area" id="ai-comment-section-' + step.id + '">';
    html += '<label class="step-text-label">AI 评论</label>';

    if (hasComment) {
        // Show structured fields from AI_FIELD_CONFIG
        for (const [field, cfg] of Object.entries(AI_FIELD_CONFIG)) {
            let value = step[field] || '';
            let label = cfg.label;

            // Backward compatibility: show old ai_description if ai_interaction is empty
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
                    <div class="ai-field-value editable-ai" data-step-id="${step.id}" data-field="${field}">${formatBulletHtml(value)}</div>
                </div>`;
        }

        // Action buttons
        html += `<div class="ai-comment-actions">`;
        if (hasImage) {
            html += `<button class="btn btn-secondary btn-sm" onclick="regenerateAiComment(${step.id})" id="ai-gen-btn-${step.id}">&#x21bb; 重新生成</button>`;
        }
        html += `</div>`;
    } else {
        // No comments yet - show generate button
        if (hasImage) {
            html += `<button class="btn btn-primary btn-sm ai-gen-btn" onclick="generateAiComment(${step.id})" id="ai-gen-btn-${step.id}">&#x2728; 生成 AI 评论</button>`;
        } else {
            html += `<p class="text-muted text-small">需要先上传截图才能生成 AI 评论</p>`;
        }
    }

    html += '</div>';
    return html;
}

/**
 * Enable inline editing for an AI comment field.
 */
function enableAiFieldEdit(el) {
    const field = el.dataset.field;
    const stepId = parseInt(el.dataset.stepId);
    const step = getStepById(stepId);
    const cfg = AI_FIELD_CONFIG[field];
    if (!step || !cfg) return;

    // For backward compat: if editing ai_interaction but it's empty and ai_description has data
    let originalValue = step[field] || '';
    if (field === 'ai_interaction' && !originalValue && step.ai_description) {
        originalValue = step.ai_description;
    }

    el.classList.add('editing');

    const wrapper = document.createElement('div');
    wrapper.className = 'inline-edit-wrapper';

    const textarea = document.createElement('textarea');
    textarea.className = 'form-textarea ai-edit-textarea';
    textarea.value = originalValue;
    textarea.rows = 4;
    textarea.maxLength = cfg.maxLen;
    textarea.placeholder = cfg.placeholder;

    const footer = document.createElement('div');
    footer.className = 'ai-edit-footer';

    const counter = document.createElement('span');
    counter.className = 'ai-field-count';
    counter.textContent = `${originalValue.length}/${cfg.maxLen}`;

    const actions = document.createElement('div');
    actions.className = 'inline-edit-actions';
    actions.innerHTML = `
        <button class="btn btn-primary btn-sm ai-save-btn">保存</button>
        <button class="btn btn-secondary btn-sm ai-cancel-btn">取消</button>
    `;

    footer.appendChild(counter);
    footer.appendChild(actions);
    wrapper.appendChild(textarea);
    wrapper.appendChild(footer);

    el.style.display = 'none';
    el.parentNode.insertBefore(wrapper, el.nextSibling);
    textarea.focus();

    // Live character count
    textarea.addEventListener('input', () => {
        const len = textarea.value.length;
        counter.textContent = `${len}/${cfg.maxLen}`;
        counter.classList.toggle('over', len > cfg.maxLen);
    });

    // Save
    actions.querySelector('.ai-save-btn').onclick = async () => {
        const newValue = textarea.value.trim().slice(0, cfg.maxLen);
        try {
            await apiCall(`/api/steps/${stepId}`, {
                method: 'PUT',
                body: { [field]: newValue }
            });
            if (step) step[field] = newValue;
            wrapper.remove();
            el.classList.remove('editing');
            el.style.display = '';
            // Re-render appropriate view
            if (typeof renderStepsView === 'function' && typeof stepsData !== 'undefined') {
                renderStepsView(stepsData);
            } else if (typeof refreshAiCommentPanel === 'function') {
                refreshAiCommentPanel(stepId);
            }
            showToast('已保存', 'success');
        } catch (err) {
            showToast(err.message, 'error');
        }
    };

    // Cancel
    actions.querySelector('.ai-cancel-btn').onclick = () => {
        wrapper.remove();
        el.classList.remove('editing');
        el.style.display = '';
    };

    // ESC to cancel
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            wrapper.remove();
            el.classList.remove('editing');
            el.style.display = '';
        }
    });
}
