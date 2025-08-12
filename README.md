# 教学笔记生成器

能够自动从教学视频中提取PPT图片、转录语音内容并整合生成markdown文件。

## 功能

### 核心功能
- **视频下载**: 支持从各种平台下载教学视频
- **PPT提取**: 智能识别并提取视频中的PPT图片，借用https://github.com/wudududu/extract-video-ppt  的项目并加以改进
- **语音转录**: 使用先进的语音识别技术转录教师讲解
- **文本优化**: AI辅助优化转录文本，去除口语化痕迹
- **笔记生成**: 自动生成包含PPT图片和对应文本的结构化笔记

### 技术特色
- **PPT检测**: 使用多种算法（aHash、pHash、边缘检测）确保准确提取PPT变化
- **时间戳对齐**: 精确的时间戳映射，确保图片与文本对应

## 📋 系统要求

### 必需软件
- Python 3.8+
- FFmpeg
- yt-dlp

### Python依赖
```bash
pip install flask torch openai faster-whisper opencv-python numpy
```

### 可选配置
- CUDA支持的GPU（用于加速语音转录）
- Silicon Cloud API Key（用于文本优化）

## 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd ppttry
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
*本项目（企图方便）用的模型供应商是硅基流动，可以在其官网选择你喜欢的模型并复制粘贴其名字到project_script.py的模型选择中测试不同模型文本优化的效果* 
```bash
export SILICON_CLOUD_API_KEY="your-api-key"
```

### 4. 启动Web服务
```bash
python app.py
```

### 5. 访问
打开浏览器访问 `http://localhost:5000`

## 使用方法

### Web界面使用
1. 在输入框中粘贴教学视频链接
2. 点击"生成笔记"按钮
3. 等待处理完成（会显示实时进度）
4. 查看生成的笔记结果

### 命令行使用
```bash
python auto_note_generator.py <视频链接>
```

## 🏗️ 项目结构

```
ppttry/
├── app.py                          # Flask Web应用主文件
├── auto_note_generator.py          # 核心处理逻辑
├── extract-video-ppt/             # PPT提取模块
│   ├── video2ppt/
│   │   ├── video2ppt.py          # 视频处理主逻辑
│   │   ├── compare.py            # 图像相似度比较
│   │   └── images2pdf.py         # 图片转PDF
├── templates/                      # HTML模板
│   └── index.html                # 主页面
├── static/                        # 静态资源
│   ├── css/
│   │   └── style.css             # Material Design样式
│   └── js/
│       └── script.js             # 前端交互逻辑
├── output/                        # 生成结果目录
│   ├── images/                   # 提取的PPT图片
│   └── *.md                      # 生成的笔记文件
└── temp/                         # 临时工作目录
```

## main模块

### 1. PPT提取模块 (`extract-video-ppt/`)
- **功能**: 从视频中智能提取PPT图片
- **算法**: 结合aHash、pHash、边缘检测等多种算法
- **特点**: 高精度检测PPT变化，避免重复提取

### 2. 语音转录模块 (`auto_note_generator.py`)
- **技术**: 使用faster-whisper进行语音识别
- **支持**: CPU/GPU加速，多语言支持
- **优化**: AI辅助文本优化，去除口语化痕迹

## something about 参数

### PPT提取参数
```python
# 相似度阈值（越小越敏感）
diff_threshold = 4

# 采样频率（每秒帧数）
sampling_rate = 2  # 每秒2帧

# 时间间隔检查（秒）
min_interval = 2.0
```

### 语音转录参数
```python
# 设备选择
DEVICE = "cuda"  # 或 "cpu"

# 计算类型
COMPUTE_TYPE = "float16"  # 或 "int8"

# 模型路径
FASTER_WHISPER_MODEL_PATH = "path/to/model"
```

## about输出

生成的笔记采用Markdown格式，包含：

```markdown
# 视频标题 - 教学笔记

## Slide 1 (时间点: 00:00:01)

![Slide 1](./images/slide1.jpg)

> 对应的转录文本内容...

---

## Slide 2 (时间点: 00:00:35)

![Slide 2](./images/slide2.jpg)

> 对应的转录文本内容...
```

## 故障

### 常见问题

1. **视频下载失败**
   - 检查网络连接
   - 确认视频链接有效
   - 更新yt-dlp: `pip install --upgrade yt-dlp`

2. **PPT提取不准确**
   - 调整相似度阈值
   - 检查视频质量
   - 确认视频包含PPT内容

3. **语音转录失败**
   - 检查音频文件是否生成
   - 确认模型路径正确
   - 尝试使用CPU模式

4. **Web界面无法访问**
   - 检查端口是否被占用
   - 确认Flask依赖已安装
   - 查看控制台错误信息

### 性能优化

1. **GPU加速**: 确保CUDA环境正确配置
2. **内存优化**: 处理大视频时增加系统内存
3. **存储优化**: 定期清理temp目录，因为在一些运行失败的调试中工作区的清理的相关代码不会正常执行


### 开发环境设置
```bash
git clone <repository-url>
cd ppttry
pip install -r requirements.txt
python app.py
```


## 参考与借鉴

- [extract-video-ppt](https://github.com/wudududu/extract-video-ppt) - PPT提取核心算法
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - 语音转录引擎
- [Material Design](https://material.io/) - UI设计规范
- [Flask](https://flask.palletsprojects.com/) - Web框架

