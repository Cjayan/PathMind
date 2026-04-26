// image_upload.js - Handles drag-and-drop, paste, and file picker image upload

class ImageUploader {
    constructor(uploadAreaId, fileInputId, onImageReady) {
        this.uploadArea = document.getElementById(uploadAreaId);
        this.fileInput = document.getElementById(fileInputId);
        this.onImageReady = onImageReady;
        this.currentFile = null;

        this._bindEvents();
    }

    _bindEvents() {
        // Click to select file
        this.uploadArea.addEventListener('click', () => this.fileInput.click());

        // File input change
        this.fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                this._processFile(e.target.files[0]);
            }
        });

        // Drag and drop
        this.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.uploadArea.classList.add('dragover');
        });

        this.uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.uploadArea.classList.remove('dragover');
        });

        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.uploadArea.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files && files[0] && files[0].type.startsWith('image/')) {
                this._processFile(files[0]);
            } else {
                showToast('请上传图片文件', 'error');
            }
        });

        // Global paste (Ctrl+V)
        document.addEventListener('paste', (e) => {
            // Only capture paste when editor form is visible
            const editorForm = document.getElementById('editor-form');
            if (!editorForm || editorForm.style.display === 'none') return;

            // Don't capture paste in input fields
            const activeEl = document.activeElement;
            if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')) {
                // Allow paste in text fields unless it's an image paste
                const items = e.clipboardData?.items;
                if (!items) return;
                let hasImage = false;
                for (const item of items) {
                    if (item.type.startsWith('image/')) {
                        hasImage = true;
                        break;
                    }
                }
                if (!hasImage) return; // Let text paste through
            }

            const items = e.clipboardData?.items;
            if (!items) return;

            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    e.preventDefault();
                    const blob = item.getAsFile();
                    if (blob) {
                        this._processFile(blob);
                    }
                    break;
                }
            }
        });
    }

    _processFile(file) {
        this.currentFile = file;

        // Create preview URL
        const url = URL.createObjectURL(file);
        this.onImageReady(file, url);
    }

    getFile() {
        return this.currentFile;
    }

    clear() {
        this.currentFile = null;
        this.fileInput.value = '';
    }
}
