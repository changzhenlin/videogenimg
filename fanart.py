# Updated code: generate fanart.jpg if poster.jpg exists and fanart.jpg is missing
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

# Existing functions unchanged up to generate_random_thumbnail
# ... (keep previous functions same: check_ffmpeg, get_video_clip, has_face, generate_random_thumbnail)
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

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def generate_random_thumbnail(video_path, output_path, overwrite=True, quality=100, size=None):
    try:
        if not os.path.exists(video_path):
            return False, f"视频文件不存在: {video_path}"
        try:
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
        except Exception:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False, "无法打开视频"
            fps = cap.get(cv2.CAP_PROP_FPS)
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            duration = frames / fps if fps and fps > 0 and frames and frames > 0 else None
            frame_rgb = None
            found_face = False
            face_time = None
            t_used = 0
            for _ in range(5):
                if duration:
                    t = random.uniform(duration * 0.1, duration * 0.9)
                    idx = int(t * fps)
                else:
                    if frames and frames > 0:
                        idx = int(random.uniform(0.1, 0.9) * frames)
                        t = idx / fps if fps and fps > 0 else 0
                    else:
                        idx = 0
                        t = 0
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, bgr = cap.read()
                if not ret:
                    continue
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                if has_face(rgb):
                    frame_rgb = rgb
                    found_face = True
                    face_time = t
                    t_used = t
                    break
                else:
                    frame_rgb = rgb
                    t_used = t
            if frame_rgb is None:
                cap.release()
                return False, "无法读取视频帧"
            cap.release()
            img = Image.fromarray(frame_rgb)
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
                "timestamp": face_time if found_face else t_used
            }
            return True, result
    except Exception as e:
        return False, f"处理视频失败: {str(e)}"

# New function to generate fanart.jpg if poster.jpg exists and fanart.jpg is missing
def process_fanart(video_path, temp_output, quality=100, size=None):
    directory = os.path.dirname(video_path)
    poster_path = os.path.join(directory, "poster.jpg")
    fanart_path = os.path.join(directory, "fanart.jpg")

    # Only proceed if poster.jpg exists and fanart.jpg does not exist
    if os.path.exists(poster_path) and not os.path.exists(fanart_path):
        success, result = generate_random_thumbnail(video_path, temp_output, quality=quality, size=size)
        if success:
            try:
                shutil.copy2(temp_output, fanart_path)
                result["saved_path"] = fanart_path
            except Exception as e:
                result["warning"] = f"封面生成成功但无法保存fanart.jpg: {str(e)}"
            return True, result
        else:
            return False, result
    else:
        return None, "poster.jpg不存在或fanart.jpg已存在，跳过"

# Modify main to use process_fanart logic
def choose_folder():
    root = Tk()
    root.withdraw()
    path = filedialog.askdirectory(title="选择包含视频的文件夹")
    root.update()
    root.destroy()
    return path

def main():
    print("🎬 视频封面生成工具（根据poster.jpg生成fanart.jpg）")
    if not check_ffmpeg():
        print("❌ 警告: 未找到ffmpeg，这是视频处理的必要依赖。")
    folder_path = choose_folder()
    if not folder_path:
        print("⚠️ 未选择文件夹")
        return
    quality = 100
    size = (1920, 1080)  # 横屏尺寸
    temp_dir = os.path.join(tempfile.gettempdir(), "thumbnails")
    os.makedirs(temp_dir, exist_ok=True)
    temp_output = os.path.join(temp_dir, "temp_thumbnail.jpg")

    def collect_videos(root_dir, max_depth=2):
        result = []
        def walk(dir_path, depth):
            try:
                for name in os.listdir(dir_path):
                    p = os.path.join(dir_path, name)
                    if os.path.isfile(p) and any(name.lower().endswith(ext) for ext in SUPPORTED_EXTS):
                        result.append(p)
                    elif os.path.isdir(p) and depth < max_depth:
                        walk(p, depth + 1)
            except Exception:
                pass
        walk(root_dir, 0)
        return result

    videos = collect_videos(folder_path, max_depth=2)
    if not videos:
        print("⚠️ 选中文件夹下未发现支持的视频文件")
        return

    print(f"⏳ 共找到 {len(videos)} 个视频，开始检查poster.jpg并生成fanart.jpg...")
    for video_path in videos:
        print(f"🎞️ 检查: {os.path.basename(video_path)}")
        success, result = process_fanart(video_path, temp_output, quality=quality, size=size)
        if success:
            msg = "✅ fanart.jpg生成成功！"
            msg += " 检测到人脸" if result.get("has_face") else " 使用随机帧"
            ts = result.get("timestamp")
            if isinstance(ts, (int, float)):
                msg += f" 时间点: {ts:.2f}s"
            if result.get("saved_path"):
                msg += f"\n📁 已保存到: {result.get('saved_path')}"
            if result.get("warning"):
                msg += f"\n⚠️ {result.get('warning')}"
            print(msg)
        elif success is None:
            print(f"⏭️ 跳过: {result}")
        else:
            print(f"❌ {os.path.basename(video_path)} fanart生成失败: {result}")

if __name__ == "__main__":
    main()
