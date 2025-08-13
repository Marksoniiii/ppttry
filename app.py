from flask import Flask, request, jsonify, render_template
import os
import json
import threading
import time
import subprocess
import sys
import uuid
import shutil
from auto_note_generator import DEVICE, COMPUTE_TYPE, transcribe_audio_with_faster_whisper, process_and_generate_final_note

app = Flask(__name__, template_folder='templates', static_folder='static')

# 模拟存储笔记数据
notes_storage = {}

# 进度状态存储
progress_status = {}

def run_command(command, description):
    """运行命令并更新进度"""
    print(f"--- 正在执行: {description} ---")
    print(f"CMD: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, capture_output=True)
        print(f"--- {description}... 成功 ---")
        return True
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode(sys.getdefaultencoding(), errors='ignore')
        print(f"!!! 错误: {description} 失败。\n{error_message}")
        return False
    except FileNotFoundError:
        print(f"!!! 错误: 命令 '{command[0]}' 未找到。")
        return False

def process_video_background(video_url, task_id):
    """后台处理视频的函数，实时更新进度"""
    temp_workspace = os.path.abspath(os.path.join("temp", str(uuid.uuid4())))
    os.makedirs(temp_workspace, exist_ok=True)
    
    try:
        # 步骤1: 获取视频信息
        progress_status[task_id].update({
            'current_step': 'download',
            'status': '正在获取视频信息...',
            'overall_progress': 5
        })
        
        print(f"创建临时工作区: {temp_workspace}")
        print("\n--- 正在获取视频信息 ---")
        
        title_cmd = ['yt-dlp', '--get-title', '--no-warnings', '--skip-download', video_url]
        video_title = "Untitled_Video"
        try:
            title_result = subprocess.run(title_cmd, check=True, capture_output=True, timeout=20)
            for encoding in ['utf-8', sys.getdefaultencoding(), 'gbk']:
                try:
                    video_title = title_result.stdout.decode(encoding).strip()
                    break
                except UnicodeDecodeError: continue
        except Exception as e:
            print(f"警告：获取视频标题失败 ({e})，将使用默认标题。")
        
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        if not safe_title: safe_title = "video_note_" + str(uuid.uuid4())[:8]
        print(f"视频标题已识别为: {safe_title}")
        
        # 步骤2: 下载视频
        progress_status[task_id].update({
            'current_step': 'download',
            'status': '正在下载视频...',
            'overall_progress': 15
        })
        
        video_path = os.path.join(temp_workspace, "video.mp4")
        if not run_command(['yt-dlp', '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', '-o', video_path, video_url], "下载完整视频"):
            progress_status[task_id].update({
                'current_step': 'error',
                'status': '下载视频失败',
                'overall_progress': 0
            })
            return
        
        # 步骤3: 提取PPT图片
        progress_status[task_id].update({
            'current_step': 'extract',
            'status': '正在提取PPT图片...',
            'completed_steps': ['download'],
            'overall_progress': 35
        })
        
        ppt_output_dir = os.path.join(temp_workspace, 'ppt_images')
        if not run_command(['evp', '--raw_frames', '--diff_threshold', '3', '--motion_threshold', '0.8', ppt_output_dir, video_path], "提取PPT图片"):  # 修复：降低运动阈值到0.8
            progress_status[task_id].update({
                'current_step': 'error',
                'status': '提取PPT图片失败',
                'overall_progress': 0
            })
            return
        
        # 步骤4: 提取音频
        progress_status[task_id].update({
            'current_step': 'transcribe',
            'status': '正在提取音频...',
            'completed_steps': ['download', 'extract'],
            'overall_progress': 50
        })
        
        audio_path = os.path.join(temp_workspace, 'audio.mp3')
        if not run_command(['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', audio_path], "提取音频"):
            progress_status[task_id].update({
                'current_step': 'error',
                'status': '提取音频失败',
                'overall_progress': 0
            })
            return
        
        # 步骤5: 转录语音
        progress_status[task_id].update({
            'current_step': 'transcribe',
            'status': '正在转录语音...',
            'completed_steps': ['download', 'extract'],
            'overall_progress': 65
        })
        
        transcript_data = transcribe_audio_with_faster_whisper(audio_path, DEVICE, COMPUTE_TYPE)
        if not transcript_data:
            progress_status[task_id].update({
                'current_step': 'error',
                'status': '转录语音失败',
                'overall_progress': 0
            })
            return
        
        # 步骤6: AI文本优化和生成笔记
        progress_status[task_id].update({
            'current_step': 'optimize',
            'status': '正在生成笔记...',
            'completed_steps': ['download', 'extract', 'transcribe'],
            'overall_progress': 85
        })
        
        process_and_generate_final_note(ppt_output_dir, transcript_data, safe_title)
        
        # 步骤7: 完成
        progress_status[task_id].update({
            'current_step': 'complete',
            'status': '生成完成',
            'completed_steps': ['download', 'extract', 'transcribe', 'optimize'],
            'overall_progress': 100
        })
        
        # 保存生成的笔记
        note_id = len(notes_storage) + 1
        notes_storage[note_id] = {
            'id': note_id,
            'video_url': video_url,
            'notes': '视频处理完成，请查看output目录中的生成文件'
        }
        
    except Exception as e:
        progress_status[task_id].update({
            'current_step': 'error',
            'status': f'处理失败: {str(e)}',
            'overall_progress': 0
        })
    finally:
        print(f"\n--- 正在清理临时工作区: {temp_workspace} ---")
        if os.path.exists(temp_workspace):
            shutil.rmtree(temp_workspace)
        print("--- 清理完成 ---")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api', methods=['POST'])
def api_generate_notes():
    try:
        data = request.json
        video_url = data.get('video_url', '')
        
        if not video_url:
            return jsonify({
                'success': False,
                'error': '请提供视频链接'
            }), 400
        
        # 生成任务ID
        task_id = str(int(time.time() * 1000))
        progress_status[task_id] = {
            'current_step': 'download',
            'status': '正在初始化...',
            'completed_steps': [],
            'overall_progress': 0
        }
        
        # 在后台线程中执行视频处理
        thread = threading.Thread(target=process_video_background, args=(video_url, task_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '开始处理视频'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """获取任务进度"""
    if task_id not in progress_status:
        return jsonify({
            'success': False,
            'error': '任务不存在'
        }), 404
    
    return jsonify({
        'success': True,
        'data': progress_status[task_id]
    })

@app.route('/api/generate_notes', methods=['POST'])
def api_generate_notes_legacy():
    # 保持向后兼容的端点
    try:
        data = request.json
        video_url = data.get('content', '')  # 兼容旧的content字段
        
        if not video_url:
            return jsonify({
                'success': False,
                'error': '请提供视频链接'
            }), 400
        
        # 生成任务ID
        task_id = str(int(time.time() * 1000))
        progress_status[task_id] = {
            'current_step': 'download',
            'status': '正在初始化...',
            'completed_steps': [],
            'overall_progress': 0
        }
        
        # 在后台线程中执行视频处理
        thread = threading.Thread(target=process_video_background, args=(video_url, task_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '开始处理视频'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    if note_id in notes_storage:
        return jsonify({
            'success': True,
            'data': notes_storage[note_id]
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Note not found'
        }), 404

@app.route('/api/notes', methods=['GET'])
def list_notes():
    return jsonify({
        'success': True,
        'data': list(notes_storage.values())
    })

if __name__ == '__main__':
    # 确保模板和静态文件目录存在
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
