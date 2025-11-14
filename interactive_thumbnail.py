import os
import random
import subprocess
from contextlib import contextmanager
from moviepy import VideoFileClip
from PIL import Image
import cv2
import numpy as np
import tempfile
import shutil
from tkinter import Tk, filedialog

SUPPORTED_EXTS = [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"]

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

@contextmanager
def get_video_clip(video_path):
    clip = None
    try:
        clip = VideoFileClip(video_path)
        yield clip
    finally:
        if clip is not None:
            try:
                clip.close()
            except Exception as e:
                print(f"关闭视频时发生错误: {e}")

def has_face(frame):
    gray = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    frame_height, frame_width = gray.shape[:2]
    min_size = (max(40, frame_width // 10), max(40, frame_height // 10))
    max_size = (frame_width // 2, frame_height // 2)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=12, minSize=min_size, maxSize=max_size)
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
    try:
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
                except Exception:
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

def choose_video_file():
    root = Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title="选择视频文件", filetypes=[("视频文件", "*.mp4;*.mov;*.avi;*.mkv;*.wmv;*.flv;*.webm"), ("所有文件", "*.*")])
    root.update()
    root.destroy()
    return path

def main():
    print("🎬 视频封面生成工具（交互选择视频，其余默认）")
    if not check_ffmpeg():
        print("❌ 警告: 未找到ffmpeg，这是视频处理的必要依赖。")
    video_path = choose_video_file()
    if not video_path:
        print("⚠️ 未选择视频文件")
        return
    ext = os.path.splitext(video_path)[1].lower()
    if ext not in SUPPORTED_EXTS:
        print("❌ 不支持的文件类型")
        return
    quality = 100
    size = (1920, 1080)
    temp_dir = os.path.join(tempfile.gettempdir(), "thumbnails")
    os.makedirs(temp_dir, exist_ok=True)
    temp_output = os.path.join(temp_dir, "temp_thumbnail.jpg")
    video_dir = os.path.dirname(video_path)
    sidecar_output_path = os.path.join(video_dir, "poster.jpg")
    print("⏳ 正在生成封面...")
    success, result = generate_random_thumbnail(video_path, temp_output, quality=quality, size=size)
    if success:
        try:
            shutil.copy2(temp_output, sidecar_output_path)
            result["saved_path"] = sidecar_output_path
        except Exception as e:
            result["warning"] = f"封面生成成功但无法保存到同级目录: {str(e)}"
        msg = "✅ 封面生成成功！"
        msg += " 检测到人脸" if result.get("has_face") else " 使用随机帧"
        ts = result.get("timestamp")
        if isinstance(ts, (int, float)):
            msg += f" 时间点: {ts:.2f}s"
        if result.get("saved_path"):
            msg += f"\n📁 已保存到: {result.get('saved_path')}"
        if result.get("warning"):
            msg += f"\n⚠️ {result.get('warning')}"
        print(msg)
    else:
        print(f"❌ {result}")

if __name__ == "__main__":
    main()