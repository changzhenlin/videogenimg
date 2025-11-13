import os
import random
import subprocess
import argparse
from contextlib import contextmanager
from moviepy import VideoFileClip
from PIL import Image
import tkinter as tk
from tkinter import filedialog
import cv2
import numpy as np


def check_ffmpeg():
    """检查系统是否安装了ffmpeg"""
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def is_ffmpeg_required():
    """确定是否强制要求ffmpeg（在Windows系统上，可以尝试使用更友好的提示）"""
    return True  # 默认仍然需要ffmpeg，但可以根据需要修改


@contextmanager
def get_video_clip(video_path):
    """上下文管理器，确保VideoFileClip正确关闭"""
    clip = None
    try:
        # 尝试创建VideoFileClip对象
        clip = VideoFileClip(video_path)
        yield clip
    except Exception as e:
        # 捕获所有可能的异常，特别是ffmpeg相关的错误
        error_msg = str(e).lower()
        if "ffmpeg" in error_msg or "not found" in error_msg:
            # 特别处理ffmpeg相关的错误
            raise RuntimeError(f"❌ ffmpeg错误: 无法处理视频文件。请确保ffmpeg已正确安装并添加到系统路径。\n详细错误: {e}")
        else:
            # 其他错误重新抛出
            raise
    finally:
        # 确保资源正确释放，即使在异常情况下
        if clip is not None:
            try:
                clip.close()
            except Exception as close_error:
                # 记录关闭时的错误，但不影响主流程
                print(f"⚠️ 关闭视频时发生错误: {close_error}")


def has_face(frame):
    """检测帧中是否包含人脸，使用多维度验证减少误判"""
    # 转换为灰度图
    gray = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2GRAY)
    
    # 加载人脸检测器
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    
    # 加载眼睛检测器（作为额外验证）
    eye_cascade = None
    try:
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    except Exception as e:
        print(f"⚠️ 无法加载眼睛检测器: {e}")
    
    # 优化检测参数
    frame_height, frame_width = gray.shape[:2]
    min_size = (max(40, frame_width // 10), max(40, frame_height // 10))  # 增大最小尺寸要求
    max_size = (frame_width // 2, frame_height // 2)
    
    faces = face_cascade.detectMultiScale(
        gray, 
        scaleFactor=1.3,     # 进一步增加到1.25
        minNeighbors=12,      # 进一步增加到10
        minSize=min_size,     
        maxSize=max_size      
    )
    
    # 调试信息和增强验证
    if len(faces) > 0:
        print(f"🔍 人脸检测信息: 发现{len(faces)}个候选人脸区域")
        
        # 对每个检测到的区域进行额外验证
        valid_faces = []
        for (x, y, w, h) in faces:
            # 1. 验证人脸宽高比（真实人脸通常接近1:1到1:1.5之间）
            aspect_ratio = w / h
            
            # 2. 验证人脸在画面中的位置（避免边缘误判）
            # 要求人脸中心位于画面的20%-80%区域内
            face_center_x = x + w // 2
            face_center_y = y + h // 2
            is_centered = 0.2 * frame_width < face_center_x < 0.8 * frame_width and \
                         0.1 * frame_height < face_center_y < 0.8 * frame_height
            
            # 3. 计算人脸相对于画面的比例
            face_ratio = (w * h) / (frame_width * frame_height)
            
            # 4. 可选的眼睛检测验证
            has_eyes = False
            if eye_cascade is not None:
                # 在人脸区域内检测眼睛
                roi_gray = gray[y:y+h, x:x+w]
                eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=5, minSize=(5, 5))
                has_eyes = len(eyes) >= 1  # 至少检测到一只眼睛
            
            # 输出详细信息
            print(f"  - 候选区域: x={x}, y={y}, 宽={w}, 高={h}")
            print(f"    宽高比: {aspect_ratio:.2f}, 画面占比: {face_ratio:.2%}, 位置合理: {is_centered}")
            if eye_cascade is not None:
                print(f"    眼睛检测: {has_eyes}")
            
            # 综合判断：宽高比合理 + 位置合理
            # 如果有眼睛检测器且开启了眼睛检测，则需要至少满足有眼睛
            is_valid = (0.7 < aspect_ratio < 1.3) and is_centered
            if eye_cascade is not None:
                is_valid = is_valid and has_eyes
            
            if is_valid:
                valid_faces.append((x, y, w, h))
                print(f"    ✅ 区域验证通过")
            else:
                print(f"    ❌ 区域验证失败")
        
        # 更新检测结果为通过严格验证的人脸数量
        if len(valid_faces) > 0:
            print(f"✅ 最终确认: {len(valid_faces)}个有效人脸")
        else:
            print("❌ 所有候选区域均未通过验证")
        
        return len(valid_faces) > 0
    
    return False


def generate_random_thumbnail(video_path, overwrite=True, quality=90, size=None):
    """为视频生成随机封面图"""
    if not os.path.isfile(video_path):
        print(f"❌ 文件不存在: {video_path}")
        return False

    ext = os.path.splitext(video_path)[1].lower()
    if ext not in [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"]:
        print(f"⚠️ 跳过非视频文件: {video_path}")
        return False

    try:
        folder = os.path.dirname(video_path)
        name, _ = os.path.splitext(os.path.basename(video_path))
        output_path = os.path.join(folder, f"poster.jpg")

        # 默认覆盖已存在的文件
        if os.path.exists(output_path) and not overwrite:
            print(f"⚠️ 封面已存在，跳过: {output_path}")
            return False
        elif os.path.exists(output_path):
            print(f"🔄 覆盖已存在的封面: {output_path}")

        # 检查ffmpeg是否可用，提前给出友好提示
        if not check_ffmpeg():
            print(f"❌ ffmpeg不可用: 无法处理视频 {os.path.basename(video_path)}")
            print("   请安装ffmpeg并添加到系统PATH后重试")
            return False

        with get_video_clip(video_path) as clip:
            try:
                duration = clip.duration
                if duration < 0.1:
                    print(f"⚠️ 视频过短，跳过: {video_path}")
                    return False

                # 尝试多次寻找有人脸的帧
                frame = None
                found_face = False
                for _ in range(5):
                    try:
                        t = random.uniform(duration * 0.1, duration * 0.9)
                        temp_frame = clip.get_frame(t)
                        if has_face(temp_frame):
                            frame = temp_frame
                            found_face = True
                            print(f"🧑‍🎤 检测到人脸，截取时间点: {t:.2f}s")
                            break
                    except Exception as frame_error:
                        print(f"⚠️ 获取帧时出错: {frame_error}，尝试下一个时间点")
                        continue
                
                if frame is None:
                    # 未检测到人脸则使用随机帧
                    try:
                        t = random.uniform(duration * 0.1, duration * 0.9)
                        frame = clip.get_frame(t)
                        print(f"🎞️ 使用随机帧: {t:.2f}s")
                    except Exception as frame_error:
                        print(f"❌ 无法获取视频帧: {frame_error}")
                        return False

                img = Image.fromarray(frame)

                if size is not None:
                    try:
                        img = img.resize(size, Image.LANCZOS)
                    except Exception as resize_error:
                        print(f"⚠️ 调整图片尺寸失败: {resize_error}，使用原始尺寸")

                img.save(output_path, "JPEG", quality=quality)
                print(f"✅ 封面生成成功: {output_path}")
                return True
            except Exception as clip_error:
                print(f"❌ 处理视频时出错: {clip_error}")
                return False

    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断")
        raise
    except IOError as e:
        print(f"⚠️ IO错误: {video_path}\n原因: {e}")
    except ValueError as e:
        print(f"⚠️ 视频格式不支持: {video_path}\n原因: {e}")
    except RuntimeError as e:
        # 特别处理RuntimeError，通常是ffmpeg相关的错误
        print(f"❌ ffmpeg错误: {e}")
    except Exception as e:
        print(f"⚠️ 处理失败: {video_path}\n原因: {e}")
    return False


def process_single_video(path, overwrite=True, quality=90, size=None):
    """处理单个视频文件"""
    if os.path.isfile(path):
        return generate_random_thumbnail(path, overwrite, quality, size)
    else:
        print(f"❌ 无效的视频文件: {path}")
        return False


def select_video_file():
    """图形化选择单个视频文件"""
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="请选择视频文件",
        filetypes=[("视频文件", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm"), ("所有文件", "*.*")]
    )


def main():
    parser = argparse.ArgumentParser(description="🎬 视频随机封面生成工具")
    parser.add_argument("--path", help="视频文件路径")
    parser.add_argument("--quality", type=int, default=90,
                        help="JPEG图片质量 (1-100)，默认90")
    parser.add_argument("--size", type=str, help="输出图片尺寸，格式为 'widthxheight'，例如 '1920x1080'")
    args = parser.parse_args()

    # 文件选择窗口
    if not args.path:
        print("📁 未提供路径，将打开文件选择窗口...")
        args.path = select_video_file()
        if not args.path:
            print("❌ 未选择任何文件，程序退出。")
            return

    # 检查ffmpeg
    if not check_ffmpeg():
        print("⚠️ 警告: 未找到ffmpeg，这是视频处理的必要依赖。")
        print("📥 下载地址: https://ffmpeg.org/download.html")
        print("🔧 Windows安装指南:")
        print("   1. 下载Windows版本的ffmpeg")
        print("   2. 解压到一个文件夹，例如: C:\ffmpeg")
        print("   3. 将C:\ffmpeg\bin添加到系统环境变量PATH中")
        print("   4. 重启命令提示符或PowerShell")
        
        # 提供临时跳过选项（虽然功能受限）
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            if messagebox.askyesno("缺少ffmpeg", "未找到ffmpeg。是否继续？（功能将受限）"):
                print("⚠️ 注意: 程序将在功能受限模式下运行，可能无法正常处理视频。")
            else:
                print("❌ 程序已退出，请安装ffmpeg后重试。")
                return
        except ImportError:
            # 如果tkinter不可用，使用命令行确认
            confirm = input("⚠️ 是否继续在功能受限模式下运行？(y/n): ")
            if confirm.lower() != 'y':
                print("❌ 程序已退出，请安装ffmpeg后重试。")
                return

    # 解析尺寸参数
    size = None
    if args.size:
        try:
            width, height = map(int, args.size.split('x'))
            size = (width, height)
        except ValueError:
            print(f"❌ 无效的尺寸格式: {args.size}，请使用 'widthxheight'")
            return

    # 默认覆盖已存在的文件
    overwrite = True
    success = process_single_video(args.path, overwrite, args.quality, size)
    
    if success:
        print("🎉 视频封面生成完成！")
    else:
        print("❌ 封面生成失败，请检查错误信息。")


if __name__ == "__main__":
    main()
