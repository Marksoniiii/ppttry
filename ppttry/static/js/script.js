class NoteGenerator {
    constructor() {
        this.apiUrl = '/api';
        this.initElements();
        this.bindEvents();
        this.loadHistory();
    }

    initElements() {
        this.contentTextarea = document.getElementById('content');
        this.generateBtn = document.getElementById('generate-btn');
        this.notesOutput = document.getElementById('notes-output');
        this.historyList = document.getElementById('history-list');
    }

    bindEvents() {
        this.generateBtn.addEventListener('click', () => this.generateNotes());
        this.historyList.addEventListener('click', (e) => this.handleHistoryClick(e));
    }

    async generateNotes() {
        const content = this.contentTextarea.value.trim();

        if (!content) {
            alert('请输入内容');
            return;
        }

        // 显示加载状态
        this.notesOutput.innerHTML = '<div class="loading">正在生成笔记...</div>';
        this.generateBtn.disabled = true;
        this.generateBtn.textContent = '生成中...';

        try {
            const response = await fetch(`${this.apiUrl}/generate_notes`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content })
            });

            const result = await response.json();

            if (result.success) {
                this.displayNotes(result.notes);
                this.loadHistory(); // 刷新历史记录
            } else {
                throw new Error(result.error || '生成失败');
            }
        } catch (error) {
            this.notesOutput.innerHTML = `<p class="error">错误: ${error.message}</p>`;
        } finally {
            this.generateBtn.disabled = false;
            this.generateBtn.textContent = '生成笔记';
        }
    }

    displayNotes(notes) {
        this.notesOutput.innerHTML = `
            <div class="note-card">
                <img src="https://placehold.co/200x150" alt="PPT缩略图">
                <div class="note-content">${this.escapeHtml(notes)}</div>
            </div>
        `;
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    async loadHistory() {
        try {
            const response = await fetch(`${this.apiUrl}/notes`);
            const result = await response.json();

            if (result.success) {
                this.renderHistory(result.data);
            }
        } catch (error) {
            console.error('加载历史记录失败:', error);
        }
    }

    renderHistory(notes) {
        if (!notes || notes.length === 0) {
            this.historyList.innerHTML = '<p class="placeholder">暂无历史记录</p>';
            return;
        }

        // 按时间倒序排列
        const sortedNotes = [...notes].sort((a, b) => b.id - a.id);
        
        this.historyList.innerHTML = sortedNotes.map(note => `
            <div class="history-item" data-id="${note.id}">
                <h3>笔记 #${note.id}</h3>
                <p>${note.content.substring(0, 100)}${note.content.length > 100 ? '...' : ''}</p>
            </div>
        `).join('');
    }

    async handleHistoryClick(event) {
        const historyItem = event.target.closest('.history-item');
        if (!historyItem) return;

        const noteId = historyItem.dataset.id;
        this.loadNoteDetail(noteId);
    }

    async loadNoteDetail(noteId) {
        try {
            const response = await fetch(`${this.apiUrl}/notes/${noteId}`);
            const result = await response.json();

            if (result.success) {
                this.displayNotes(result.data.notes);
                // 填充表单内容
                this.contentTextarea.value = result.data.content;
            }
        } catch (error) {
            console.error('加载笔记详情失败:', error);
        }
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new NoteGenerator();
});