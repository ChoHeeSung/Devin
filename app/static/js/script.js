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
    const progressBar = document.getElementById('progress-bar');
    const progressPercentage = document.getElementById('progress-percentage');
    const progressStatus = document.getElementById('progress-status');
    const conversionLog = document.getElementById('conversion-log');
    const logContent = document.getElementById('log-content');
    
    let currentFile = null;
    let markdownContent = '';
    let eventSource = null;
    
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
        
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        
        const formData = new FormData();
        formData.append('file', currentFile);
        
        convertBtn.classList.add('hidden');
        loading.classList.remove('hidden');
        conversionLog.classList.remove('hidden');
        markdownOutput.value = '';
        downloadBtn.disabled = true;
        progressBar.style.width = '0%';
        progressPercentage.textContent = '0';
        progressStatus.textContent = '변환 준비 중...';
        logContent.innerHTML = '';
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
            const taskId = data.task_id;
            connectToEventStream(taskId);
        })
        .catch(error => {
            showError(error.message || '알 수 없는 오류가 발생했습니다');
            loading.classList.add('hidden');
            convertBtn.classList.remove('hidden');
        });
    });
    
    function connectToEventStream(taskId) {
        eventSource = new EventSource(`/stream-conversion-progress/${taskId}`);
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            updateProgress(data.progress, data.status);
            
            updateLogs(data.logs);
            
            if (data.result) {
                markdownContent = data.result;
                markdownOutput.value = markdownContent;
                downloadBtn.disabled = false;
                
                eventSource.close();
                eventSource = null;
                
                setTimeout(() => {
                    loading.classList.add('hidden');
                    convertBtn.classList.remove('hidden');
                }, 500);
            }
            
            if (data.error) {
                showError(data.error);
                
                eventSource.close();
                eventSource = null;
                
                loading.classList.add('hidden');
                convertBtn.classList.remove('hidden');
            }
        };
        
        eventSource.onerror = function() {
            showError('서버 연결이 끊어졌습니다');
            
            eventSource.close();
            eventSource = null;
            
            loading.classList.add('hidden');
            convertBtn.classList.remove('hidden');
        };
    }
    
    function updateProgress(progress, status) {
        progressBar.style.width = `${progress}%`;
        progressPercentage.textContent = progress;
        
        if (status) {
            progressStatus.textContent = status;
        }
    }
    
    function updateLogs(logs) {
        if (!logs || !logs.length) return;
        
        logContent.innerHTML = '';
        logs.forEach(log => {
            const logLine = document.createElement('p');
            logLine.className = 'text-xs mb-1';
            logLine.textContent = log;
            logContent.appendChild(logLine);
        });
        
        logContent.scrollTop = logContent.scrollHeight;
    }
    
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
