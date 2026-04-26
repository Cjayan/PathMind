// step_manager.js - Manages step list, ordering, selection

class StepManager {
    constructor(listElementId, onStepSelect) {
        this.listEl = document.getElementById(listElementId);
        this.onStepSelect = onStepSelect;
        this.steps = [];
        this.activeStepId = null;
        this.sortable = null;

        this._initSortable();
    }

    _initSortable() {
        this.sortable = new Sortable(this.listEl, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            dragClass: 'sortable-drag',
            handle: '.step-item',
            onEnd: (evt) => {
                this._onSortEnd(evt);
            }
        });
    }

    async _onSortEnd(evt) {
        // Reorder steps based on new DOM order
        const items = this.listEl.querySelectorAll('.step-item');
        const stepIds = Array.from(items).map(el => parseInt(el.dataset.stepId));

        try {
            await apiCall('/api/steps/reorder', {
                method: 'POST',
                body: { step_ids: stepIds }
            });
            // Update local order
            stepIds.forEach((id, index) => {
                const step = this.steps.find(s => s.id === id);
                if (step) step.order = index + 1;
            });
            this.steps.sort((a, b) => a.order - b.order);
            this.render();
        } catch (error) {
            showToast('排序更新失败: ' + error.message, 'error');
            this.render(); // Re-render to reset order
        }
    }

    setSteps(steps) {
        this.steps = steps;
        this.render();
        this._updateStatusBar();
    }

    addStep(step) {
        this.steps.push(step);
        this.render();
        this._updateStatusBar();
    }

    updateStep(updatedStep) {
        const idx = this.steps.findIndex(s => s.id === updatedStep.id);
        if (idx !== -1) {
            this.steps[idx] = updatedStep;
        }
        this.render();
        this._updateStatusBar();
    }

    removeStep(stepId) {
        this.steps = this.steps.filter(s => s.id !== stepId);
        // Re-number
        this.steps.forEach((s, i) => s.order = i + 1);
        if (this.activeStepId === stepId) {
            this.activeStepId = null;
        }
        this.render();
        this._updateStatusBar();
    }

    setActive(stepId) {
        this.activeStepId = stepId;
        this.render();
    }

    getStep(stepId) {
        return this.steps.find(s => s.id === stepId);
    }

    getSteps() {
        return this.steps;
    }

    render() {
        if (this.steps.length === 0) {
            this.listEl.innerHTML = '<div class="empty-state" style="padding: 20px;"><p class="text-muted text-small">暂无步骤</p></div>';
            return;
        }

        this.listEl.innerHTML = this.steps.map(step => {
            const isActive = step.id === this.activeStepId;
            const thumbHtml = step.image_path
                ? `<img class="step-thumb" src="/api/steps/image/${step.image_path}" alt="step ${step.order}">`
                : `<div class="step-thumb-placeholder">📷</div>`;
            const scoreHtml = step.score ? `<span class="score-badge score-color-${getScoreLevel(step.score)}">${step.score}/10</span>` : '';

            return `
                <div class="step-item ${isActive ? 'active' : ''}" data-step-id="${step.id}" onclick="selectStep(${step.id})">
                    <span class="step-order">${step.order}</span>
                    ${thumbHtml}
                    <div class="step-info">
                        <div class="step-title">${escapeHtml(step.description || '(未填写描述)')}</div>
                        <div class="step-meta">
                            <span style="color: var(--color-star);">${scoreHtml}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Update step count
        document.getElementById('step-count').textContent = `${this.steps.length} 步`;
    }

    _updateStatusBar() {
        const countEl = document.getElementById('status-steps');
        const avgEl = document.getElementById('status-avg-score');

        countEl.textContent = `共 ${this.steps.length} 步`;

        const scores = this.steps.filter(s => s.score).map(s => s.score);
        if (scores.length > 0) {
            const avg = (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1);
            avgEl.textContent = `平均评分: ${avg}/10`;
        } else {
            avgEl.textContent = '平均评分: -';
        }
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getScoreLevel(score) {
    if (score <= 3) return 'low';
    if (score <= 5) return 'mid';
    if (score <= 7) return 'ok';
    if (score <= 9) return 'good';
    return 'great';
}
