// ai_assistant.js - AI analysis integration

class AIAssistant {
    constructor() {
        this.lastSuggestion = null;
    }

    async analyzeScreenshot(imageBase64, context) {
        const btnEl = document.getElementById('btn-ai-analyze');
        const oldText = btnEl.textContent;
        btnEl.textContent = '分析中...';
        btnEl.disabled = true;

        try {
            const result = await apiCall('/api/ai/analyze-screenshot', {
                method: 'POST',
                body: { image_base64: imageBase64, context }
            });

            this.lastSuggestion = result;
            this._showSuggestion(result);
            return result;
        } catch (error) {
            showToast(error.message, 'error');
            return null;
        } finally {
            btnEl.textContent = oldText;
            btnEl.disabled = false;
        }
    }

    _showSuggestion(result) {
        const box = document.getElementById('ai-suggestion-box');
        const content = document.getElementById('ai-suggestion-content');

        let html = '';
        if (result.suggested_title) {
            html += `<p><strong>建议描述:</strong> ${escapeHtml(result.suggested_title)}</p>`;
        }
        if (result.description) {
            html += `<p><strong>页面分析:</strong> ${escapeHtml(result.description)}</p>`;
        }
        if (result.ui_elements && result.ui_elements.length > 0) {
            html += `<p><strong>关键元素:</strong> ${result.ui_elements.map(e => escapeHtml(e)).join(', ')}</p>`;
        }
        // If result is just raw text
        if (!result.suggested_title && !result.ui_elements && typeof result.description === 'string') {
            html = `<p>${escapeHtml(result.description)}</p>`;
        }

        content.innerHTML = html;
        box.classList.add('visible');
    }

    getSuggestion() {
        return this.lastSuggestion;
    }

    clearSuggestion() {
        this.lastSuggestion = null;
        document.getElementById('ai-suggestion-box').classList.remove('visible');
    }

    async generateSummary(flowId) {
        try {
            const result = await apiCall(`/api/ai/generate-summary/${flowId}`, {
                method: 'POST'
            });
            return result.summary;
        } catch (error) {
            showToast(error.message, 'error');
            return null;
        }
    }
}

function escapeHtmlAi(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
