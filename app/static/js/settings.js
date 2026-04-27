// settings.js - Settings page logic

document.addEventListener('DOMContentLoaded', loadSettings);

async function loadSettings() {
    try {
        const config = await apiCall('/api/config/');
        fillForm(config);
    } catch (error) {
        showToast('加载设置失败: ' + error.message, 'error');
    }
}

function fillForm(config) {
    const obs = config.obsidian || {};
    const ai = config.ai || {};
    const rec = config.recording || {};
    document.getElementById('vault-path').value = obs.vault_path || '';
    document.getElementById('products-folder').value = obs.products_folder || 'Products';
    document.getElementById('ai-base-url').value = ai.base_url || '';
    document.getElementById('ai-api-key').value = ai.api_key || '';
    document.getElementById('ai-model').value = ai.model || '';
    document.getElementById('ai-max-tokens').value = ai.max_tokens || 4096;
    document.getElementById('recording-hotkey-start').value = rec.hotkey_start || '';
    document.getElementById('recording-hotkey-stop').value = rec.hotkey_stop || '';
    const snipasteEl = document.getElementById('recording-snipaste-path');
    if (snipasteEl) {
        snipasteEl.value = rec.snipaste_path || '';
    }
}

async function saveSettings() {
    const data = {
        obsidian: {
            vault_path: document.getElementById('vault-path').value.trim(),
            products_folder: document.getElementById('products-folder').value.trim() || 'Products',
        },
        ai: {
            base_url: document.getElementById('ai-base-url').value.trim(),
            api_key: document.getElementById('ai-api-key').value.trim(),
            model: document.getElementById('ai-model').value.trim(),
            max_tokens: parseInt(document.getElementById('ai-max-tokens').value) || 4096,
        },
        recording: {
            hotkey_start: document.getElementById('recording-hotkey-start').value.trim().toLowerCase(),
            hotkey_stop: document.getElementById('recording-hotkey-stop').value.trim().toLowerCase(),
            snipaste_path: (document.getElementById('recording-snipaste-path') || {}).value?.trim() || '',
        }
    };

    try {
        await apiCall('/api/config/', {
            method: 'PUT',
            body: data,
        });
        showToast('设置已保存', 'success');
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

async function validateVault() {
    const path = document.getElementById('vault-path').value.trim();
    const statusEl = document.getElementById('vault-status');

    if (!path) {
        statusEl.textContent = '请输入路径';
        statusEl.style.color = 'var(--color-danger)';
        return;
    }

    try {
        const result = await apiCall('/api/config/validate-vault', {
            method: 'POST',
            body: { vault_path: path },
        });
        statusEl.textContent = result.message;
        statusEl.style.color = result.valid ? 'var(--color-success)' : 'var(--color-danger)';
    } catch (error) {
        statusEl.textContent = error.message;
        statusEl.style.color = 'var(--color-danger)';
    }
}

function toggleApiKeyVisibility() {
    const input = document.getElementById('ai-api-key');
    const btn = document.getElementById('btn-toggle-key');
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '隐藏';
    } else {
        input.type = 'password';
        btn.textContent = '显示';
    }
}

async function testAiConnection() {
    const resultEl = document.getElementById('ai-test-result');
    resultEl.textContent = '测试中...';
    resultEl.style.color = 'var(--color-text-secondary)';

    // Save settings first
    await saveSettings();

    try {
        const result = await apiCall('/api/ai/test-connection', { method: 'POST' });
        resultEl.textContent = `连接成功 - 模型: ${result.model}`;
        resultEl.style.color = 'var(--color-success)';
    } catch (error) {
        resultEl.textContent = `连接失败: ${error.message}`;
        resultEl.style.color = 'var(--color-danger)';
    }
}

async function validateSnipaste() {
    const path = document.getElementById('recording-snipaste-path').value.trim();
    const statusEl = document.getElementById('snipaste-status');

    if (!path) {
        statusEl.textContent = '请输入路径';
        statusEl.style.color = 'var(--color-danger)';
        return;
    }

    try {
        const result = await apiCall('/api/config/validate-snipaste', {
            method: 'POST',
            body: { snipaste_path: path },
        });
        statusEl.textContent = result.message;
        statusEl.style.color = result.valid ? 'var(--color-success)' : 'var(--color-danger)';
    } catch (error) {
        statusEl.textContent = error.message;
        statusEl.style.color = 'var(--color-danger)';
    }
}
