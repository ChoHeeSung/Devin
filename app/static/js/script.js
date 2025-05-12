document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('pdf-upload');
    const fileName = document.getElementById('file-name');
    const convertBtn = document.getElementById('convert-btn');
    const loading = document.getElementById('loading');
    const markdownOutput = document.getElementById('markdown-output');
    const downloadBtn = document.getElementById('download-btn');
    const errorAlert = document.getElementById('error-alert');
    const errorMessage = document.getElementById('error-message');
    
    let currentFile = null;
    let markdownContent = '';
    
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        
        if (file) {
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                showError('PDF 파일만 지원됩니다');
                fileInput.value = '';
                return;
            }
            
            currentFile = file;
            fileName.textContent = file.name;
            convertBtn.classList.remove('hidden');
            hideError();
        }
    });
    
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!currentFile) {
            showError('먼저 PDF 파일을 선택해주세요');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', currentFile);
        
        convertBtn.classList.add('hidden');
        loading.classList.remove('hidden');
        markdownOutput.value = '';
        downloadBtn.disabled = true;
        hideError();
        
        fetch('/convert-pdf', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.detail || 'PDF 변환에 실패했습니다');
                });
            }
            return response.json();
        })
        .then(data => {
            markdownContent = data.markdown_content;
            markdownOutput.value = markdownContent;
            downloadBtn.disabled = false;
        })
        .catch(error => {
            showError(error.message || '알 수 없는 오류가 발생했습니다');
        })
        .finally(() => {
            loading.classList.add('hidden');
            convertBtn.classList.remove('hidden');
        });
    });
    
    downloadBtn.addEventListener('click', function() {
        if (!markdownContent) return;
        
        const blob = new Blob([markdownContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = currentFile.name.replace('.pdf', '.md');
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
    
    function showError(message) {
        errorMessage.textContent = message;
        errorAlert.classList.remove('hidden');
    }
    
    function hideError() {
        errorAlert.classList.add('hidden');
    }
});
