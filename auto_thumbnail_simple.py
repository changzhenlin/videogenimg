import os
import random
import subprocess
import sys
import importlib.util
from PIL import Image
import numpy as np
import tempfile
import shutil
from tkinter import Tk, filedialog

# 尝试导入cv2，如果失败提供更详细的错误信息
try:
    import cv2
except ImportError:
    print("❌ 错误: 无法导入cv2模块。请确认opencv-python是否正确安装。")
    print("  建议尝试以下命令重新安装:")
    print("  - pip uninstall opencv-python")
    print("  - pip install opencv-python-headless  # 无头版本，更轻量且兼容性更好")
    print("  - 或尝试指定版本: pip install opencv-python==4.8.0.74")
    print(f"  当前Python环境: {sys.executable}")
    print(f"  Python版本: {sys.version}")
    print("\n正在尝试继续执行...")
    # 设置一个假的cv2对象，让程序能够继续执行到主函数进行检查
    class MockCV2:
        def __getattr__(self, name):
            raise ImportError(f"cv2模块未正确安装，无法使用{name}")
    cv2 = MockCV2()

# 支持的视频格式
SUPPORTED_EXTS = [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"]

def check_ffmpeg():
    """检查系统是否安装了ffmpeg"""
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def _ffprobe_duration(video_path):
    try:
        out = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        return float(out.stdout.strip())
    except Exception:
        return None

def generate_thumbnail(video_path, output_path, quality=100, size=None, vertical=False):
    try:
        if not os.path.exists(video_path):
            return False, f"视频文件不存在: {video_path}"

        if check_ffmpeg():
            duration = _ffprobe_duration(video_path)
            if duration and duration > 0.2:
                t = random.uniform(duration * 0.1, duration * 0.9)
            else:
                t = 10
            vf_parts = []
            if size and len(size) == 2:
                vf_parts.append(f"scale={size[0]}:{size[1]}")
            else:
                vf_parts.append("scale=min(1920\\,iw):-2")
            vf = ",".join(vf_parts)
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-hwaccel", "auto",
                "-ss", f"{t}", "-i", video_path,
                "-frames:v", "1", "-vf", vf,
                "-q:v", "2", "-y", output_path
            ]
            try:
                subprocess.run(cmd, check=True)
                # 如需竖截图或进一步尺寸调整，使用PIL进行后处理
                try:
                    post_img = Image.open(output_path)
                    if vertical:
                        w, h = post_img.size
                        target_ratio = 2 / 3
                        target_w = int(h * target_ratio)
                        if target_w > w:
                            target_w = w
                            target_h = int(w / target_ratio)
                            if target_h > h:
                                target_h = h
                            top = (h - target_h) // 2
                            bottom = top + target_h
                            left = 0
                            right = w
                        else:
                            left = (w - target_w) // 2
                            right = left + target_w
                            top = 0
                            bottom = h
                        post_img = post_img.crop((left, top, right, bottom))
                    elif size and len(size) == 2:
                        post_img = post_img.resize(size, Image.LANCZOS)
                    post_img.save(output_path, "JPEG", quality=quality)
                except Exception:
                    pass
                frame_idx = None
                try:
                    cap_meta = cv2.VideoCapture(video_path)
                    fps = cap_meta.get(cv2.CAP_PROP_FPS)
                    frame_idx = int(t * fps) if fps and fps > 0 else None
                    cap_meta.release()
                except Exception:
                    frame_idx = None
                return True, {"success": True, "message": "封面生成成功", "frame_index": frame_idx}
            except Exception:
                pass

        cap = cv2.VideoCapture(video_path)
        if not hasattr(cv2, 'VideoCapture') or not cap.isOpened():
            return False, "无法打开视频文件"
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return False, "无法获取视频帧数"
        start_frame = int(total_frames * 0.1)
        end_frame = int(total_frames * 0.9)
        if start_frame >= end_frame:
            start_frame = 0
            end_frame = total_frames - 1
        target_frame = random.randint(start_frame, end_frame)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return False, "无法读取视频帧"
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_frame)
        if vertical:
            width, height = img.size
            target_ratio = 2 / 3
            target_width = int(height * target_ratio)
            if target_width > width:
                target_width = width
                target_height = int(width / target_ratio)
                if target_height > height:
                    target_height = height
                top = (height - target_height) // 2
                bottom = top + target_height
                left = 0
                right = width
            else:
                left = (width - target_width) // 2
                right = left + target_width
                top = 0
                bottom = height
            img = img.crop((left, top, right, bottom))
        elif size:
            try:
                img = img.resize(size, Image.LANCZOS)
            except Exception as e:
                return False, f"调整图片尺寸失败: {str(e)}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, "JPEG", quality=quality)
        return True, {"success": True, "message": "封面生成成功", "frame_index": target_frame}
    except Exception as e:
        return False, f"处理视频失败: {str(e)}"

def choose_folder():
    """选择文件夹的简单实现"""
    root = Tk()
    root.withdraw()
    path = filedialog.askdirectory(title="选择包含视频的文件夹")
    root.update()
    root.destroy()
    return path

def collect_videos(root_dir, max_depth=2):
    """收集指定目录下的视频文件"""
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
            pass  # 忽略无法访问的目录
    
    walk(root_dir, 0)
    return result

def check_image_files_identical(file1_path, file2_path):
    """检查两个图片文件是否大小相同（简单判断是否可能为相同图片）"""
    try:
        if not os.path.exists(file1_path) or not os.path.exists(file2_path):
            return False
        
        # 比较文件大小
        size1 = os.path.getsize(file1_path)
        size2 = os.path.getsize(file2_path)
        
        return size1 == size2
    except Exception as e:
        print(f"⚠️ 检查图片文件时出错: {str(e)}")
        return False

def create_video_folders(videos):
    """为多个视频文件创建单独的文件夹并移动视频文件"""
    # 首先按目录分组视频文件
    videos_by_dir = {}
    for video_path in videos:
        dir_path = os.path.dirname(video_path)
        if dir_path not in videos_by_dir:
            videos_by_dir[dir_path] = []
        videos_by_dir[dir_path].append(video_path)
    
    # 处理每个目录中的视频
    new_video_paths = []
    moved_count = 0
    
    for dir_path, dir_videos in videos_by_dir.items():
        # 如果目录中只有一个视频，不需要创建子文件夹
        if len(dir_videos) <= 1:
            new_video_paths.extend(dir_videos)
            continue
        
        # 目录中有多个视频，为每个视频创建单独的文件夹
        for video_path in dir_videos:
            video_name = os.path.basename(video_path)
            # 移除扩展名作为文件夹名
            folder_name = os.path.splitext(video_name)[0]
            # 确保文件夹名有效（移除特殊字符）
            folder_name = ''.join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_'))
            # 如果文件夹名为空，使用默认名称
            if not folder_name:
                folder_name = f"video_{moved_count + 1}"
            
            # 创建新文件夹
            new_folder_path = os.path.join(dir_path, folder_name)
            try:
                # 如果文件夹已存在，添加数字后缀避免覆盖
                counter = 1
                base_folder_path = new_folder_path
                while os.path.exists(new_folder_path):
                    new_folder_path = f"{base_folder_path}_{counter}"
                    counter += 1
                
                os.makedirs(new_folder_path, exist_ok=True)
                
                # 移动视频文件到新文件夹
                new_video_path = os.path.join(new_folder_path, video_name)
                shutil.move(video_path, new_video_path)
                new_video_paths.append(new_video_path)
                moved_count += 1
                print(f"📁 已将 '{video_name}' 移动到新文件夹 '{folder_name}'")
            except Exception as e:
                print(f"⚠️ 移动文件 '{video_name}' 失败: {str(e)}")
                # 如果移动失败，使用原路径
                new_video_paths.append(video_path)
    
    if moved_count > 0:
        print(f"✅ 共移动 {moved_count} 个视频文件到单独的文件夹")
    
    return new_video_paths

def main():
    """主函数 - 简化版批量处理视频"""
    print("🎬 视频封面生成工具（简化版）")
    print("⚡ 模式: 随机截取视频帧，快速生成封面")
    print("📂 功能: 自动为多视频文件夹创建单独目录结构")
    
    # 检查cv2是否可用
    try:
        # 测试cv2是否真正可用
        test_cv2 = hasattr(cv2, 'VideoCapture')
        if not test_cv2:
            raise ImportError("cv2模块不完整")
    except (ImportError, AttributeError):
        print("\n❌ 严重错误: OpenCV (cv2) 模块未正确安装或不完整")
        print("  程序无法继续执行，因为OpenCV是视频处理的核心依赖")
        print("  请按照之前的建议重新安装OpenCV:")
        print("  1. pip uninstall opencv-python")
        print("  2. pip install opencv-python-headless")
        print("  或尝试:")
        print("  1. pip install opencv-python==4.8.0.74")
        print("\n如果使用conda环境:")
        print("  conda install -c conda-forge opencv")
        print("\n请确保使用的是与Python版本兼容的OpenCV版本")
        return
    
    # 检查ffmpeg
    if not check_ffmpeg():
        print("⚠️ 警告: 未找到ffmpeg，某些视频格式可能无法处理")
    
    # 选择文件夹
    folder_path = choose_folder()
    if not folder_path:
        print("⚠️ 未选择文件夹，退出程序")
        return
    
    # 设置参数
    quality = 100  # 最高质量 - 保持原图质量
    size = None  # 不调整尺寸，保持原始大小
    
    # 创建临时目录
    temp_dir = os.path.join(tempfile.gettempdir(), "thumbnails")
    os.makedirs(temp_dir, exist_ok=True)
    temp_output = os.path.join(temp_dir, "temp_thumbnail.jpg")
    
    # 收集视频文件
    videos = collect_videos(folder_path, max_depth=2)
    if not videos:
        print("⚠️ 选中文件夹下未发现支持的视频文件")
        return
    
    print(f"⏳ 共找到 {len(videos)} 个视频，开始处理...")
    
    # 为多个视频创建单独的文件夹
    videos_to_process = create_video_folders(videos)
    
    # 批量处理视频生成封面
    success_count = 0
    print(f"\n🎨 开始为 {len(videos_to_process)} 个视频生成封面...")

    for i, video_path in enumerate(videos_to_process, 1):
        video_name = os.path.basename(video_path)
        print(f"\n🎞️ 处理 ({i}/{len(videos_to_process)}): {video_name}")

        folder = os.path.dirname(video_path)
        poster_path = os.path.join(folder, "poster.jpg")
        fanart_path = os.path.join(folder, "fanart.jpg")

        if os.path.exists(poster_path):
            print("➡️ 跳过 poster.jpg（已存在）")
        else:
            print("🖼️ 正在生成2:3比例竖截图作为poster...")
            success_poster, result_poster = generate_thumbnail(video_path, temp_output, quality=quality, vertical=True)
            if success_poster:
                try:
                    shutil.copy2(temp_output, poster_path)
                    success_count += 1
                    frame_idx = result_poster.get("frame_index")
                    print(f"✅ poster.jpg 生成成功，帧索引: {frame_idx}")
                    print(f"📁 保存到: {poster_path}")
                except Exception as e:
                    print(f"⚠️ poster.jpg 生成成功但保存失败: {str(e)}")
            else:
                print(f"❌ poster.jpg 生成失败: {result_poster}")

        # 检查是否需要重新生成fanart（当poster和fanart存在且大小相同时）
        need_regenerate_fanart = False
        if os.path.exists(fanart_path):
            if os.path.exists(poster_path) and check_image_files_identical(poster_path, fanart_path):
                print("🔄 发现poster和fanart相同，准备重新生成fanart")
                try:
                    os.remove(fanart_path)
                    need_regenerate_fanart = True
                    print("🗑️ 已删除相同的fanart")
                except Exception as e:
                    print(f"⚠️ 删除fanart失败: {str(e)}")
            else:
                print("➡️ 跳过 fanart.jpg（已存在且与poster不同）")
        else:
            need_regenerate_fanart = True
        
        if need_regenerate_fanart:
            print("🎨 正在生成fanart...")
            # fanart保持原有逻辑，不使用竖截图
            success_fanart, result_fanart = generate_thumbnail(video_path, temp_output, quality=quality, size=size)
            if success_fanart:
                try:
                    shutil.copy2(temp_output, fanart_path)
                    success_count += 1
                    frame_idx = result_fanart.get("frame_index")
                    print(f"✅ fanart.jpg 生成成功，帧索引: {frame_idx}")
                    print(f"📁 保存到: {fanart_path}")
                except Exception as e:
                    print(f"⚠️ fanart.jpg 生成成功但保存失败: {str(e)}")
            else:
                print(f"❌ fanart.jpg 生成失败: {result_fanart}")
    
    # 总结
    print(f"\n📊 处理完成: 成功 {success_count} / {len(videos_to_process)}")
    print("✨ 现在每个视频文件都位于单独的文件夹中，并配有对应的封面图片")

if __name__ == "__main__":
    main()
