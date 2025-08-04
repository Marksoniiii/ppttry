import os
import sys
import shutil
import subprocess
import time
import uuid
import json
import torch
import difflib # 确保difflib被导入
from openai import OpenAI
from faster_whisper import WhisperModel

# 全局配置区 
FFMPEG_PATH = "ffmpeg"
EVP_PATH = "evp"
API_KEY = os.getenv("SILICON_CLOUD_API_KEY")
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL_NAME = "Qwen/Qwen3-30B-A3B-Thinking-2507"
FASTER_WHISPER_MODEL_PATH = r"C:\Users\ZzZz\.cache\modelscope\hub\models\angelala00\faster-whisper-small" # 请确保路径正确

# --- [修正] 将环境检查和变量定义移到模块顶层 ---
print("--- 正在初始化模块并检查运行环境 ---")
if torch.cuda.is_available():
    DEVICE = "cuda"
    COMPUTE_TYPE = "float16"
    print("CUDA (GPU) 可用！将使用GPU进行加速。")
else:
    DEVICE = "cpu"
    COMPUTE_TYPE = "int8"
    print("CUDA (GPU) 不可用。将使用CPU运行，速度会较慢。")
print("---------------------------------------\n")


# Prompt ---
GLOBAL_OPTIMIZE_PROMPT = """
你是一个顶级的文本修复师。你的任务是将一份完整的、由语音识别生成的课堂教学原始文稿，转化为一篇流畅的文章。请严格遵循以下规则：

1.  **通读全文，理解上下文**：在修正任何句子之前，先理解整个段落乃至全文的主旨和逻辑。
2.  **清除所有口语化痕迹**：彻底删除所有无意义的语气词（如“嗯”、“啊”、“那个”）、不必要的重复和犹豫。
3.  **保持原意与术语**：这是最重要的规则。你只能做“修正”，绝对不能添加自己的观点、进行内容总结或删除任何关键信息和专业术语。
4.  **输出纯净的文本**：只输出修复后的完整文章，不要添加任何前言、标题、摘要或评论。

原始文稿如下：
---
{full_raw_speech}
"""



def run_command(command, description):

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

# --- 文本优化函数
def optimize_full_text(client, full_text):
    if not full_text: return ""
    print("\n--- 正在对全文进行上下文感知优化 (这可能需要较长时间) ---")
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": GLOBAL_OPTIMIZE_PROMPT.format(full_raw_speech=full_text)}],
            temperature=0.2,
            stream=False
        )
        print("--- 全文优化完成 ---")
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"\n!!! 全文优化API调用失败: {e}")
        return None

# --- 时间戳对齐函数 ---
def align_timestamps(raw_words_with_ts, optimized_text):
    print("--- 正在将时间戳映射到优化后的文本 ---")
    raw_text = "".join(w['word'] for w in raw_words_with_ts)
    
    optimized_words_with_ts = []
    
    # 创建一个从原始文本字符索引到单词信息（包含时间戳）的映射
    # 这比之前的char_to_word_map更直接高效
    char_to_word_map = {}
    char_cursor = 0
    for word_info in raw_words_with_ts:
        for _ in word_info['word']:
            char_to_word_map[char_cursor] = word_info
            char_cursor += 1

    matcher = difflib.SequenceMatcher(None, raw_text, optimized_text, autojunk=False)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # 文字相同，直接继承时间戳
            for raw_char_index in range(i1, i2):
                if raw_char_index in char_to_word_map:
                    source_word = char_to_word_map[raw_char_index]
                    # 从优化文本中取出对应的字符
                    optimized_char = optimized_text[j1 + (raw_char_index - i1)]
                    optimized_words_with_ts.append({
                        'word': optimized_char, 
                        'start': source_word['start'], 
                        'end': source_word['end']
                    })
        
        elif tag == 'replace' or tag == 'insert':
            # --- [核心修复逻辑] ---
            # 这是被模型修改或新增的文本，需要智能地寻找时间戳锚点

            # 1. 优先寻找“后锚点”：它后面紧跟着的原始文本的位置(i2)
            # 这对于修复句首缺失至关重要
            anchor_char_index = i2
            
            # 2. 如果找不到“后锚点”（即修改发生在最末尾），则使用“前锚点”(i1 - 1)
            if anchor_char_index >= len(raw_text):
                anchor_char_index = i1 - 1

            # 确保锚点索引有效
            if 0 <= anchor_char_index < len(raw_text):
                anchor_word = char_to_word_map[anchor_char_index]
                # 将这段新文本中的每个字，都赋予锚点的时间戳
                for char in optimized_text[j1:j2]:
                    optimized_words_with_ts.append({
                        'word': char, 
                        'start': anchor_word['start'], 
                        'end': anchor_word['end']
                    })
            else:
                # 极端情况：如果整个文本都被替换了，就用第一个词的时间戳
                anchor_word = raw_words_with_ts[0] if raw_words_with_ts else {'start': 0, 'end': 0}
                for char in optimized_text[j1:j2]:
                    optimized_words_with_ts.append({
                        'word': char, 
                        'start': anchor_word['start'], 
                        'end': anchor_word['end']
                    })

    print("--- 时间戳映射完成 ---")
    return optimized_words_with_ts

def process_and_generate_final_note(image_dir, transcript_data, video_title):
    print("\n--- 核心处理: 正在整合图文并生成笔记 ---")
    actual_image_dir = os.path.join(image_dir, "frames")
    if not os.path.exists(actual_image_dir):
        print(f"!!! 关键错误: 预期的图片目录 '{actual_image_dir}' 不存在。")
        return

    output_dir, final_md_path = "output", os.path.join("output", f"{video_title}_笔记.md")
    image_files = [f for f in os.listdir(actual_image_dir) if f.lower().endswith('.jpg')]
    if not image_files:
        print("!!! 关键错误: 'frames' 子目录中未找到任何PPT图片。")
        return
        
    def filename_to_seconds(filename):
        parts = os.path.splitext(filename)[0].rstrip('-').split('.')
        return float(int(parts[0])*3600 + int(parts[1])*60 + int(parts[2]))
    ppt_timestamps = sorted([(filename_to_seconds(f), f) for f in image_files])
    
    raw_words_with_ts = [word for segment in transcript_data.get('segments', []) for word in segment.get('words', [])]
    full_raw_speech = "".join(w['word'] for w in raw_words_with_ts)

    if API_KEY and full_raw_speech:
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        optimized_full_text = optimize_full_text(client, full_raw_speech)
        if optimized_full_text is None:
            print("警告: 全文优化失败，将使用原始文本。")
            optimized_full_text = full_raw_speech
    else:
        print("未配置API Key或无语音内容，跳过文本优化。")
        optimized_full_text = full_raw_speech

    optimized_words_with_ts = align_timestamps(raw_words_with_ts, optimized_full_text)

    video_duration = transcript_data['segments'][-1]['end'] if transcript_data.get('segments') else 0
    notes = []
    for i, (ppt_start_time, ppt_filename) in enumerate(ppt_timestamps):
        ppt_end_time = ppt_timestamps[i+1][0] if i + 1 < len(ppt_timestamps) else video_duration
        speech_text = "".join(word['word'] for word in optimized_words_with_ts if ppt_start_time <= word['start'] < ppt_end_time)
        notes.append({
            "ppt_path": os.path.join(actual_image_dir, ppt_filename), 
            "timestamp_str": os.path.splitext(ppt_filename)[0].rstrip('-').replace('.', ':'), 
            "speech": speech_text.strip()
        })
    
    os.makedirs(output_dir, exist_ok=True)
    with open(final_md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {video_title} - 教学笔记 (精炼版)\n\n---\n\n")
        safe_title_for_dir = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        final_img_base_dir = os.path.join(output_dir, "images", safe_title_for_dir)
        os.makedirs(final_img_base_dir, exist_ok=True)
        for i, note in enumerate(notes):
            img_name = os.path.basename(note['ppt_path'])
            shutil.copy(note['ppt_path'], os.path.join(final_img_base_dir, img_name))
            image_md_path = f"./images/{safe_title_for_dir}/{img_name}"
            f.write(f"## Slide {i+1} (时间点: {note['timestamp_str']})\n\n![Slide {i+1}]({image_md_path})\n\n")

            # --- [最终修正] 增加后处理步骤 ---
            speech_content = note['speech'] or '(此时间段内无教师讲稿)'
            # 将所有换行符替换为能让Markdown引用块正确换行的格式
            formatted_speech = speech_content.replace('\n', '\n> ')
            
            f.write(f"> {formatted_speech}\n\n---\n\n")

    print(f"🎉 最终任务完成！精炼版笔记已成功生成于: {final_md_path}")

def transcribe_audio_with_faster_whisper(audio_path, device, compute_type):

    print("\n--- 正在使用 faster-whisper 进行音频转文字 ---")
    if not os.path.exists(FASTER_WHISPER_MODEL_PATH):
        print(f"!!! 错误: faster-whisper模型路径不存在: {FASTER_WHISPER_MODEL_PATH}")
        return None
    print(f"正在加载本地模型到 {device} (计算类型: {compute_type})...")
    try:
        model = WhisperModel(FASTER_WHISPER_MODEL_PATH, device=device, compute_type=compute_type)
    except Exception as e:
        print(f"!!! 加载模型失败: {e}")
        return None
    print("开始转录...")
    segments_generator, info = model.transcribe(audio_path, language="zh", word_timestamps=True)
    whisper_data, total_segments = {"segments": [], "language": info.language}, 0
    for segment in segments_generator:
        total_segments += 1
        print(f"\r正在处理第 {total_segments} 段语音...", end="")
        words_list = segment.words or []
        whisper_data["segments"].append({"start": segment.start, "end": segment.end, "words": [{"word": w.word, "start": w.start, "end": w.end} for w in words_list]})
    print(f"\n--- 音频转文字完成，共处理 {total_segments} 段。---")
    return whisper_data


def main_pipeline(video_url, device, compute_type):
    # ... (代码不变) ...
    temp_workspace = os.path.abspath(os.path.join("temp", str(uuid.uuid4())))
    os.makedirs(temp_workspace, exist_ok=True)
    print(f"创建临时工作区: {temp_workspace}")

    try:
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

        video_path = os.path.join(temp_workspace, "video.mp4")
        if not run_command(['yt-dlp', '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', '-o', video_path, video_url], "下载完整视频"): return

        ppt_output_dir = os.path.join(temp_workspace, 'ppt_images')
        if not run_command([EVP_PATH, '--raw_frames', '--diff_threshold', '4', ppt_output_dir, video_path], "提取PPT图片"): return

        audio_path = os.path.join(temp_workspace, 'audio.mp3')
        if not run_command([FFMPEG_PATH, '-i', video_path, '-q:a', '0', '-map', 'a', audio_path], "提取音频"): return

        transcript_data = transcribe_audio_with_faster_whisper(audio_path, device, compute_type)
        if not transcript_data: return

        process_and_generate_final_note(ppt_output_dir, transcript_data, safe_title)

    finally:
        print(f"\n--- 正在清理临时工作区: {temp_workspace} ---")
        if os.path.exists(temp_workspace):
            shutil.rmtree(temp_workspace)
        print("--- 清理完成 ---")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else input("请输入B站教学视频链接: ")
    if url.strip():
        main_pipeline(url, device=DEVICE, compute_type=COMPUTE_TYPE)
    else:
        print("错误：未输入链接。")