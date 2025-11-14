import os
import random
import subprocess
from contextlib import contextmanager
from moviepy import VideoFileClip
from PIL import Image
import cv2
import numpy as np
from flask import Flask, render_template_string, request, jsonify, send_file
import tempfile
import shutil

# Flask应用初始化
app = Flask(__name__)

# 配置目录
ROOT_DIR = "/videos"  # NAS挂载目录
TEMP_DIR = "/tmp/thumbnails"

SUPPORTED_EXTS = [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"]

# 确保临时目录存在
os.makedirs(TEMP_DIR, exist_ok=True)


def check_ffmpeg():
    """检查系统是否安装了ffmpeg"""
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


@contextmanager
def get_video_clip(video_path):
    """上下文管理器，确保VideoFileClip正确关闭"""
    clip = None
    try:
        clip = VideoFileClip(video_path)
        yield clip
    finally:
        if clip is not None:
            try:
                clip.close()
            except Exception as e:
                print(f"⚠️ 关闭视频时发生错误: {e}")


def has_face(frame):
    """检测帧中是否包含人脸，使用多维度验证减少误判"""
    gray = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2GRAY)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

    frame_height, frame_width = gray.shape[:2]
    min_size = (max(40, frame_width // 10), max(40, frame_height // 10))
    max_size = (frame_width // 2, frame_height // 2)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=12,
        minSize=min_size,
        maxSize=max_size
    )

    if len(faces) == 0:
        return False

    valid_faces = []

    for (x, y, w, h) in faces:
        aspect_ratio = w / h
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        is_centered = (
            0.2 * frame_width < face_center_x < 0.8 * frame_width and
            0.1 * frame_height < face_center_y < 0.8 * frame_height
        )

        face_ratio = (w * h) / (frame_width * frame_height)

        roi_gray = gray[y:y+h, x:x+w]
        eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=5)
        has_eyes = len(eyes) >= 1

        is_valid = (0.7 < aspect_ratio < 1.3) and is_centered and has_eyes
        if is_valid:
            valid_faces.append((x, y, w, h))

    return len(valid_faces) > 0


def generate_random_thumbnail(video_path, output_path, overwrite=True, quality=100, size=None):
    """为视频生成随机封面图"""
    # 不校验视频文件是否有效，直接尝试处理
    try:
        # 检查文件是否存在
        if not os.path.exists(video_path):
            return False, f"视频文件不存在: {video_path}"
        
        with get_video_clip(video_path) as clip:
            duration = clip.duration
            if duration < 0.1:
                return False, "视频过短"

            frame = None
            found_face = False
            face_time = None

            for _ in range(5):
                t = random.uniform(duration * 0.1, duration * 0.9)
                try:
                    temp_frame = clip.get_frame(t)
                    if has_face(temp_frame):
                        frame = temp_frame
                        found_face = True
                        face_time = t
                        break
                except Exception as e:
                    continue

            if frame is None:
                t = random.uniform(duration * 0.1, duration * 0.9)
                try:
                    frame = clip.get_frame(t)
                except Exception as e:
                    return False, f"获取视频帧失败: {str(e)}"

            img = Image.fromarray(frame)

            if size:
                try:
                    img = img.resize(size, Image.LANCZOS)
                except Exception as e:
                    return False, f"调整图片尺寸失败: {str(e)}"

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path, "JPEG", quality=quality)

            result = {
                "success": True,
                "message": "封面生成成功",
                "has_face": found_face,
                "timestamp": face_time if found_face else t
            }
            return True, result

    except Exception as e:
        return False, f"处理视频失败: {str(e)}"


# Web界面模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频封面生成工具</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }
        .container {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .file-browser {
            margin-bottom: 20px;
        }
        .dir-list, .file-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 10px 0;
        }
        .item {
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
            min-width: 150px;
            text-align: center;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .dir {
            background-color: #3498db;
            color: white;
        }
        .dir:hover {
            background-color: #2980b9;
        }
        .file {
            background-color: #ecf0f1;
            border: 1px solid #ddd;
        }
        .file:hover {
            background-color: #bdc3c7;
        }
        .back-btn {
            background-color: #95a5a6;
            color: white;
        }
        .back-btn:hover {
            background-color: #7f8c8d;
        }
        .current-path {
            font-weight: bold;
            margin-bottom: 10px;
            color: #2c3e50;
        }
        .preview-container {
            margin-top: 20px;
            text-align: center;
        }
        .preview-img {
            max-width: 100%;
            max-height: 500px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-top: 10px;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .controls {
            margin-top: 20px;
            text-align: center;
        }
        button {
            background-color: #27ae60;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #229954;
        }
        .quality-control {
            margin: 15px 0;
        }
        .message {
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎬 视频封面生成工具</h1>
        <p>为您的视频自动生成高质量封面图</p>
    </div>
    
    <div class="container">
        <div class="file-browser">
            <div class="current-path">当前路径: {{ current_path }}</div>
            
            <div class="dir-list">
                {% if current_path != ROOT_DIR %}
                <div class="item dir back-btn" onclick="navigateTo('..')">📁 .. (上级目录)</div>
                {% endif %}
                {% for dir in dirs %}
                <div class="item dir" onclick="navigateTo('{{ dir }}')">📁 {{ dir }}</div>
                {% endfor %}
            </div>
            
            <div class="file-list">
                {% for file in files %}
                <div class="item file" onclick="selectFile('{{ file }}')">🎥 {{ file }}</div>
                {% endfor %}
            </div>
        </div>
        
        <div class="controls">
            <div class="quality-control">
                <label for="quality">图片质量 (1-100): </label>
                <input type="range" id="quality" min="1" max="100" value="100">
                <span id="quality-value">100</span>
            </div>
            
            <button id="generate-btn" onclick="generateThumbnail()" disabled>生成封面</button>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>正在生成封面，请稍候...</p>
        </div>
        
        <div id="message" class="message" style="display: none;"></div>
        
        <div class="preview-container">
            <h3>封面预览</h3>
            <img id="preview-img" class="preview-img" src="" alt="预览图片" style="display: none;">
        </div>
    </div>
    
    <script>
        let selectedFile = null;
        const qualitySlider = document.getElementById('quality');
        const qualityValue = document.getElementById('quality-value');
        const generateBtn = document.getElementById('generate-btn');
        const loading = document.getElementById('loading');
        const message = document.getElementById('message');
        const previewImg = document.getElementById('preview-img');
        
        qualitySlider.addEventListener('input', function() {
            qualityValue.textContent = this.value;
        });
        
        function navigateTo(path) {
            window.location.href = `/?path=${encodeURIComponent(path)}`;
        }
        
        function selectFile(file) {
            // 移除其他文件的选中状态
            document.querySelectorAll('.file-list .file').forEach(el => {
                el.style.border = '1px solid #ddd';
                el.style.backgroundColor = '#ecf0f1';
            });
            
            // 设置当前选中文件
            selectedFile = file;
            const selectedEl = event.target;
            selectedEl.style.border = '2px solid #3498db';
            selectedEl.style.backgroundColor = '#d6eaf8';
            
            // 启用生成按钮
            generateBtn.disabled = false;
        }
        
        function showMessage(text, isSuccess = true) {
            message.textContent = text;
            message.className = `message ${isSuccess ? 'success' : 'error'}`;
            message.style.display = 'block';
        }
        
        function generateThumbnail() {
            if (!selectedFile) return;
            
            loading.style.display = 'block';
            message.style.display = 'none';
            previewImg.style.display = 'none';
            
            const quality = qualitySlider.value;
            const currentPath = new URLSearchParams(window.location.search).get('path') || '';
            const filePath = currentPath ? `${currentPath}/${selectedFile}` : selectedFile;
            
            fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_path: filePath,
                    quality: parseInt(quality)
                })
            })
            .then(response => response.json())
            .then(data => {
                loading.style.display = 'none';
                
                if (data.success) {
                    let message = `✅ 封面生成成功！${data.has_face ? '检测到人脸' : '使用随机帧'} 时间点: ${data.timestamp.toFixed(2)}s`;
                    if (data.saved_path) {
                        message += `<br>📁 已保存到视频同级目录`;
                    }
                    if (data.warning) {
                        message += `<br>⚠️ ${data.warning}`;
                    }
                    showMessage(message);
                    previewImg.src = `/preview?t=${Date.now()}`;
                    previewImg.style.display = 'block';
                } else {
                    showMessage(`❌ ${data.error}`, false);
                }
            })
            .catch(error => {
                loading.style.display = 'none';
                showMessage(`❌ 请求失败: ${error}`, false);
            });
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    """首页 - 文件浏览器"""
    # 不进行路径校验，默认使用当前目录
    path = request.args.get('path', '')
    full_path = os.path.join(ROOT_DIR, path).replace('\\', '/')
    
    # 确保路径在ROOT_DIR范围内，但不检查是否存在
    if not full_path.startswith(ROOT_DIR):
        full_path = ROOT_DIR
        path = ''
    
    dirs = []
    files = []
    
    # 尝试列出目录内容，不处理异常
    try:
        if os.path.exists(full_path) and os.path.isdir(full_path):
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                if os.path.isdir(item_path):
                    dirs.append(item)
                elif os.path.isfile(item_path) and any(item.lower().endswith(ext) for ext in SUPPORTED_EXTS):
                    files.append(item)
    except:
        pass  # 忽略错误，显示空列表
    
    return render_template_string(
        HTML_TEMPLATE,
        current_path=full_path,
        ROOT_DIR=ROOT_DIR,
        dirs=dirs,
        files=files
    )


@app.route('/generate', methods=['POST'])
def generate():
    """生成封面图API"""
    data = request.json
    file_path = data.get('file_path')
    quality = data.get('quality', 100)
    
    if not file_path:
        return jsonify({'success': False, 'error': '未指定文件路径'})
    
    # 构建完整路径，不校验路径有效性
    full_path = os.path.join(ROOT_DIR, file_path).replace('\\', '/')
    
    # 只做基本的安全检查，确保在ROOT_DIR范围内
    if not full_path.startswith(ROOT_DIR):
        return jsonify({'success': False, 'error': '路径不允许'})
    
    # 生成临时输出路径
    temp_output = os.path.join(TEMP_DIR, 'temp_thumbnail.jpg')
    
    # 生成同级目录输出路径 - 默认使用'poster.jpg'作为文件名
    video_dir = os.path.dirname(full_path)
    sidecar_output_path = os.path.join(video_dir, "poster.jpg")
    
    # 生成封面图（先生成到临时文件）
    success, result = generate_random_thumbnail(full_path, temp_output, quality=quality)
    
    # 如果成功，复制到视频同级目录
    if success:
        try:
            # 复制文件到视频同级目录
            shutil.copy2(temp_output, sidecar_output_path)
            print(f"✅ 封面已保存到: {sidecar_output_path}")
            result['saved_path'] = sidecar_output_path
        except Exception as e:
            print(f"⚠️ 保存到同级目录失败: {e}")
            # 仍然返回成功，但添加警告信息
            result['warning'] = f"封面生成成功但无法保存到同级目录: {str(e)}"
    
    if success:
        return jsonify({'success': True, **result})
    else:
        return jsonify({'success': False, 'error': result})


@app.route('/preview')
def preview():
    """预览生成的封面图"""
    temp_output = os.path.join(TEMP_DIR, 'temp_thumbnail.jpg')
    
    if os.path.exists(temp_output):
        return send_file(temp_output, mimetype='image/jpeg')
    else:
        return jsonify({'error': '预览图不存在'}), 404


def main():
    """启动Web服务"""
    # 检查ffmpeg
    if not check_ffmpeg():
        print("❌ 警告: 未找到ffmpeg，这是视频处理的必要依赖。")
    
    # 确保必要的目录存在
    os.makedirs(ROOT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # 启动Flask服务
    print("🚀 Web服务已启动")
    print(f"📂 视频目录: {ROOT_DIR}")
    print("🌐 访问 http://localhost:5000 使用Web界面")
    
    # 监听所有地址，以便在Docker容器中访问
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == "__main__":
    main()
