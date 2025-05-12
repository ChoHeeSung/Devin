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
                showError('Only PDF files are supported');
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
            showError('Please select a PDF file first');
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
                    throw new Error(data.detail || 'Failed to convert PDF');
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
            showError(error.message || 'An unknown error occurred');
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
