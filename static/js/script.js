class MaterialDesignNoteGenerator {
    constructor() {
        this.apiUrl = '/api';
        this.currentStep = 0;
        this.steps = ['download', 'extract', 'transcribe', 'optimize', 'complete'];
        this.stepNames = {
            'download': '下载视频',
            'extract': '提取PPT图片',
            'transcribe': '转录语音',
            'optimize': 'AI文本优化',
            'complete': '生成完成'
        };
        this.currentTaskId = null;
        this.progressInterval = null;
        this.initElements();
        this.bindEvents();
    }

    initElements() {
        this.videoUrlInput = document.getElementById('video-url');
        this.generateBtn = document.getElementById('generate-btn');
        this.notesOutput = document.getElementById('notes-output');
        this.stepperSection = document.getElementById('stepper-section');
        this.outputSection = document.getElementById('output-section');
        this.stepperSteps = document.querySelectorAll('.stepper-step');
        this.snackbar = document.getElementById('snackbar');
    }

    bindEvents() {
        this.generateBtn.addEventListener('click', () => this.generateNotes());
        this.videoUrlInput.addEventListener('keypress', (e) => this.handleInputKeypress(e));
        
        // 添加按钮涟漪效果
        this.generateBtn.addEventListener('mousedown', (e) => this.createRipple(e));
    }

    handleInputKeypress(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            this.generateNotes();
        }
    }

    createRipple(event) {
        const button = event.currentTarget;
        const ripple = button.querySelector('.button-ripple');
        
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.style.width = size + 'px';
        ripple.style.height = size + 'px';
    }

    async generateNotes() {
        const videoUrl = this.videoUrlInput.value.trim();
        
        if (!videoUrl) {
            this.showSnackbar('请输入视频链接', 'error');
            return;
        }

        // 禁用按钮
        this.generateBtn.disabled = true;
        this.generateBtn.innerHTML = '生成中...';

        // 显示步骤器
        this.showStepper();

        try {
            // 进度同步
            await this.startRealProgress(videoUrl);
            
        } catch (error) {
            console.error('生成笔记时出错:', error);
            this.showSnackbar('生成笔记时出错: ' + error.message, 'error');
        } finally {
            // 恢复按钮状态
            this.generateBtn.disabled = false;
            this.generateBtn.innerHTML = '<span class="button-text">生成笔记</span>';
        }
    }

    async startRealProgress(videoUrl) {
        try {
            // 发送请求到后端开始处理
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ video_url: videoUrl })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success) {
                this.currentTaskId = data.task_id;
                // 开始轮询进度
                this.startProgressPolling();
            } else {
                throw new Error(data.error || '生成失败');
            }
        } catch (error) {
            throw error;
        }
    }

    startProgressPolling() {
        // 清除之前的轮询
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        // 开始轮询进度
        this.progressInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/progress/${this.currentTaskId}`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        this.updateProgress(data.data);
                        
                        // 如果处理完成或出错，停止轮询
                        if (data.data.current_step === 'complete' || data.data.current_step === 'error') {
                            clearInterval(this.progressInterval);
                            this.progressInterval = null;
                            
                            if (data.data.current_step === 'complete') {
                                this.hideStepper();
                                this.showOutput();
                                this.displayNotes('视频处理完成！请查看output目录中的生成文件。\n\n## 生成的文件\n\n- 📄 final_note.md - 完整笔记\n- 📊 final_note.pdf - PDF格式\n- 🖼️ images/ - 提取的图片\n\n### 处理步骤\n\n1. ✅ 下载视频\n2. ✅ 提取PPT图片\n3. ✅ 转录语音\n4. ✅ AI文本优化\n5. ✅ 生成完成');
                                this.showSnackbar('笔记生成成功！', 'success');
                            } else {
                                this.showSnackbar('处理失败: ' + data.data.status, 'error');
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('获取进度失败:', error);
            }
        }, 1000); // 每秒轮询一次
    }

    updateProgress(progressData) {
        const { current_step, status, completed_steps } = progressData;
        
        // 更新所有步骤状态
        this.steps.forEach(stepName => {
            const step = document.querySelector(`[data-step="${stepName}"]`);
            const statusElement = document.getElementById(`${stepName}-status`);
            
            if (step && statusElement) {
                // 重置步骤状态
                step.classList.remove('active', 'completed');
                const icon = step.querySelector('.material-icons');
                
                if (completed_steps && completed_steps.includes(stepName)) {
                    // 已完成
                    step.classList.add('completed');
                    statusElement.textContent = '已完成';
                    if (icon) icon.textContent = 'check';
                } else if (stepName === current_step) {
                    // 当前激活
                    step.classList.add('active');
                    statusElement.textContent = status;
                } else {
                    // 等待中
                    statusElement.textContent = '等待中';
                    // 恢复原始图标
                    const originalIcons = {
                        'download': 'cloud_download',
                        'extract': 'image',
                        'transcribe': 'record_voice_over',
                        'optimize': 'auto_awesome',
                        'complete': 'check_circle'
                    };
                    if (icon) icon.textContent = originalIcons[stepName] || 'circle';
                }
            }
        });
    }

    showStepper() {
        this.stepperSection.style.display = 'block';
        this.outputSection.style.display = 'none';
        
        // 重置所有步骤状态
        this.stepperSteps.forEach(step => {
            step.classList.remove('active', 'completed');
            const icon = step.querySelector('.material-icons');
            if (icon) {
                // 恢复原始图标
                const stepName = step.dataset.step;
                const originalIcons = {
                    'download': 'cloud_download',
                    'extract': 'image',
                    'transcribe': 'record_voice_over',
                    'optimize': 'auto_awesome',
                    'complete': 'check_circle'
                };
                icon.textContent = originalIcons[stepName] || 'circle';
            }
        });
        
        // 重置状态文本
        const statusElements = ['download-status', 'extract-status', 'transcribe-status', 'optimize-status', 'complete-status'];
        statusElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = '等待中';
            }
        });
    }

    hideStepper() {
        this.stepperSection.style.display = 'none';
    }

    showOutput() {
        this.outputSection.style.display = 'block';
        
        // 添加淡入动画
        this.outputSection.style.opacity = '0';
        this.outputSection.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            this.outputSection.style.transition = 'all 0.6s ease-out';
            this.outputSection.style.opacity = '1';
            this.outputSection.style.transform = 'translateY(0)';
        }, 100);
    }

    displayNotes(notes) {
        if (!notes) {
            this.notesOutput.innerHTML = `
                <div class="placeholder-content">
                    <div class="placeholder-icon">
                        <span class="material-icons">description</span>
                    </div>
                    <p>暂无笔记内容</p>
                </div>
            `;
            return;
        }

        const formattedNotes = this.formatNotes(notes);
        
        this.notesOutput.innerHTML = `
            <div class="note-content">
                ${formattedNotes}
            </div>
        `;
    }

    formatNotes(notes) {
        if (typeof notes === 'string') {
            return this.escapeHtml(notes).replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
        }
        
        return this.escapeHtml(String(notes));
    }

    showSnackbar(message, type = 'info') {
        const snackbar = this.snackbar;
        const content = snackbar.querySelector('.snackbar-content');
        const icon = content.querySelector('.snackbar-icon');
        const messageEl = content.querySelector('.snackbar-message');
        
        // 设置图标和消息
        const icons = {
            'success': 'check_circle',
            'error': 'error',
            'info': 'info'
        };
        
        icon.textContent = icons[type] || 'info';
        messageEl.textContent = message;
        
        // 显示snackbar
        snackbar.classList.add('show');
        
        // 自动隐藏
        setTimeout(() => {
            snackbar.classList.remove('show');
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new MaterialDesignNoteGenerator();
});

