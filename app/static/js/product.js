// product.js - Product list page logic

document.addEventListener('DOMContentLoaded', loadProducts);

async function loadProducts() {
    try {
        const products = await apiCall('/api/products/');
        renderProducts(products);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function renderProducts(products) {
    const list = document.getElementById('product-list');
    const empty = document.getElementById('empty-state');

    if (products.length === 0) {
        list.style.display = 'none';
        empty.style.display = 'block';
        return;
    }

    empty.style.display = 'none';
    list.style.display = 'grid';
    list.innerHTML = products.map(p => `
        <div class="card" style="cursor: pointer;" onclick="window.location.href='/product/${p.id}'">
            <div class="flex justify-between items-center mb-8">
                <h3>${escapeHtml(p.name)}</h3>
                <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); deleteProduct(${p.id}, '${escapeHtml(p.name)}')" title="删除">删除</button>
            </div>
            <p class="text-secondary text-small">${escapeHtml(p.description || '暂无描述')}</p>
            <div class="flex justify-between items-center mt-16">
                <span class="text-muted text-small">${p.flow_count} 个流程</span>
                <span class="text-muted text-small">${formatDate(p.updated_at)}</span>
            </div>
        </div>
    `).join('');
}

function showCreateModal() {
    document.getElementById('create-modal').classList.add('active');
    document.getElementById('product-name').focus();
}

function hideCreateModal() {
    document.getElementById('create-modal').classList.remove('active');
    document.getElementById('product-name').value = '';
    document.getElementById('product-desc').value = '';
}

async function createProduct() {
    const name = document.getElementById('product-name').value.trim();
    const description = document.getElementById('product-desc').value.trim();

    if (!name) {
        showToast('请输入产品名称', 'error');
        return;
    }

    try {
        await apiCall('/api/products/', {
            method: 'POST',
            body: { name, description },
        });
        hideCreateModal();
        showToast('产品创建成功', 'success');
        loadProducts();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteProduct(id, name) {
    const confirmed = await showConfirm('删除产品', `确定要删除产品"${name}"吗？其下所有流程和步骤数据都将被删除。`);
    if (!confirmed) return;

    try {
        await apiCall(`/api/products/${id}`, { method: 'DELETE' });
        showToast('产品已删除', 'success');
        loadProducts();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Handle Enter key in modal
document.getElementById('product-name')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') createProduct();
});

// Close modal on overlay click
document.getElementById('create-modal')?.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) hideCreateModal();
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
