import json
import os
import time
from openai import OpenAI # 引入官方推荐的OpenAI库

# --- 1. 配置区域 ---
IMAGE_DIR = r"D:\ppttry\output\ppt_images"
WHISPER_JSON_PATH = r"D:\ppttry\output\transcript\output_audio.json"
OUTPUT_MD_PATH = r"D:\ppttry\output\final_note_optimized.md"
IMAGE_PATH_PREFIX = "./ppt_images/"

# --- 大语言模型API配置 (根据官方文档更新) ---
# 从环境变量中读取API密钥
API_KEY = os.getenv("SILICON_CLOUD_API_KEY") 
# 使用官方文档指定的正确API地址
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL_NAME = "Qwen/Qwen3-30B-A3B-Thinking-2507" # 你指定的模型

PROMPT_TEMPLATE = """
你是一个专业的教学笔记整理助手。你的任务是处理一段教师课堂教学的原始口语录音稿，将其转化为书面化的、流畅且结构清晰的文字。请严格遵循以下规则：

1.  **删除所有无意义的语气词、口头禅和重复**：例如“嗯”、“啊”、“那个”、“就是说”、“对吧”、“是吧”等。
2.  **修正明显的口误和语法错误**：将颠倒的词序调整通顺，补全句子成分，使其符合书面语规范。
3.  **保持教师的原意和专业术语**：绝对不要进行内容上的总结、缩写或个人解读。核心目标是“润色”而非“创作”。
4.  **输出整理后的纯文本**：不需要添加任何额外的评论、标题、前言或结语，直接输出精炼后的段落。

下面是需要你处理的原始讲稿：
---
{raw_speech}
"""

# --- 2. 辅助函数 ---
def filename_to_seconds(filename):
    base_name = os.path.splitext(filename)[0]
    clean_name = base_name.rstrip('-')
    parts = clean_name.split('.')
    if len(parts) != 3:
        raise ValueError(f"Filename '{filename}' does not match expected HH.MM.SS format.")
    hours, minutes, seconds = map(int, parts)
    return float(hours * 3600 + minutes * 60 + seconds)

# --- 新增：使用OpenAI库调用Qwen模型的函数 (完全重写) ---
def optimize_text_with_qwen(client, text_to_optimize):
    if not text_to_optimize:
        return "" # 如果文本为空，直接返回空字符串
    
    final_prompt = PROMPT_TEMPLATE.format(raw_speech=text_to_optimize)
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.3,
            stream=False # 我们需要一次性获得完整结果，所以不使用stream
        )
        optimized_text = response.choices[0].message.content
        return optimized_text.strip()
    
    except Exception as e:
        print(f"\n调用API时发生错误: {e}")
        return f"【API调用失败，保留原始文本】: {text_to_optimize}"

# --- 3. 主逻辑 ---
def main():
    print("--- 步骤 1: 读取并排序PPT图片时间戳 ---")
    try:
        image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith('.jpg')]
        ppt_timestamps = sorted([(filename_to_seconds(f), f) for f in image_files])
    except (FileNotFoundError, ValueError) as e:
        print(f"处理图片目录时出错: {e}")
        return
    if not ppt_timestamps:
        print("错误：未找到有效图片文件。")
        return
    print(f"成功读取并排序了 {len(ppt_timestamps)} 张PPT图片。")

    print("\n--- 步骤 2: 读取Whisper生成的文稿 ---")
    try:
        with open(WHISPER_JSON_PATH, 'r', encoding='utf-8') as f:
            whisper_data = json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到Whisper的JSON文件。")
        return
    video_duration = whisper_data['segments'][-1]['end']

    print("\n--- 步骤 3: 匹配PPT与教师讲稿 ---")
    notes = []
    for i, (ppt_start_time, ppt_filename) in enumerate(ppt_timestamps):
        ppt_end_time = ppt_timestamps[i+1][0] if i + 1 < len(ppt_timestamps) else video_duration
        speech_text = "".join(word_info['word'] for segment in whisper_data['segments'] if 'words' in segment for word_info in segment['words'] if ppt_start_time <= word_info['start'] < ppt_end_time)
        timestamp_str = os.path.splitext(ppt_filename)[0].rstrip('-').replace('.', ':')
        notes.append({"ppt_path": ppt_filename, "timestamp_str": timestamp_str, "speech": speech_text.strip()})
        print(f"已匹配PPT {ppt_filename}...")
    
    print("\n--- 新增步骤: 调用大模型优化讲稿文本 ---")
    if not API_KEY:
        print("警告：未设置 SILICON_CLOUD_API_KEY 环境变量，将跳过文本优化步骤。")
    else:
        # 只需创建一次客户端
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        for i, note in enumerate(notes):
            print(f"正在优化第 {i+1}/{len(notes)} 段文本...")
            if note['speech']:
                optimized_speech = optimize_text_with_qwen(client, note['speech'])
                note['speech'] = optimized_speech
                time.sleep(1) # 保留1秒的请求间隔，保护API
            else:
                print("文本为空，跳过优化。")

    print("\n--- 步骤 4: 生成最终的精炼版Markdown笔记 ---")
    with open(OUTPUT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("# 教学视频学习笔记 (精炼版)\n\n---\n\n")
        for i, note in enumerate(notes):
            f.write(f"## Slide {i+1} (时间点: {note['timestamp_str']})\n\n")
            image_md_path = os.path.join(IMAGE_PATH_PREFIX, note['ppt_path']).replace("\\", "/")
            f.write(f"![Slide {i+1}]({image_md_path})\n\n")
            f.write(f"> {note['speech'] or '(此时间段内无教师讲稿)'}\n\n---\n\n")

    print(f"\n🎉 最终任务完成！精炼版笔记已成功生成于: {OUTPUT_MD_PATH}")

if __name__ == "__main__":
    main()