import os
import random
import subprocess
import argparse
from contextlib import contextmanager
from moviepy import VideoFileClip
from PIL import Image


def check_ffmpeg():
    """检查系统是否安装了ffmpeg，这是moviepy的依赖项"""
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
            clip.close()


def generate_random_thumbnail(video_path, overwrite=False, quality=90, size=None):
    """
    为视频生成随机封面图
    
    参数:
    video_path: 视频文件路径
    overwrite: 是否覆盖已存在的封面图
    quality: JPEG质量 (0-100)
    size: 输出图片尺寸 (width, height)，None表示使用原视频尺寸
    """
    if not os.path.isfile(video_path):
        print(f"❌ 文件不存在: {video_path}")
        return False

    # 检查文件扩展名是否为视频文件
    ext = os.path.splitext(video_path)[1].lower()
    if ext not in [".mp4", ".mov", ".avi", ".mkv"]:
        print(f"⚠️ 跳过非视频文件: {video_path}")
        return False

    try:
        # 获取输出路径
        folder = os.path.dirname(video_path)
        name, _ = os.path.splitext(os.path.basename(video_path))
        output_path = os.path.join(folder, f"{name}.jpg")

        # 检查文件是否存在
        if os.path.exists(output_path) and not overwrite:
            print(f"⚠️ 封面已存在，跳过: {output_path}")
            return False

        # 使用上下文管理器确保资源释放
        with get_video_clip(video_path) as clip:
            duration = clip.duration
            # 避免处理非常短的视频
            if duration < 0.1:
                print(f"⚠️ 视频过短，跳过: {video_path}")
                return False

            # 随机选取中间80%区间的时间点
            t = random.uniform(max(0.1, duration * 0.1), duration * 0.9)

            # 获取帧
            frame = clip.get_frame(t)
            img = Image.fromarray(frame)

            # 调整大小（如果指定）
            if size is not None:
                img = img.resize(size, Image.LANCZOS)

            # 保存图片
            img.save(output_path, "JPEG", quality=quality)
            print(f"✅ 封面生成成功: {output_path}")
            return True

    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断")
        raise
    except IOError as e:
        print(f"⚠️ IO错误: {video_path}\n原因: {e}")
    except ValueError as e:
        print(f"⚠️ 视频格式不支持: {video_path}\n原因: {e}")
    except Exception as e:
        print(f"⚠️ 处理失败: {video_path}\n原因: {e}")
    return False


def process_folder(path, overwrite=False, quality=90, size=None):
    """处理单个文件或文件夹中的所有视频"""
    success_count = 0
    fail_count = 0
    total_count = 0

    if os.path.isfile(path):
        total_count = 1
        if generate_random_thumbnail(path, overwrite, quality, size):
            success_count += 1
        else:
            fail_count += 1
    elif os.path.isdir(path):
        # 获取所有视频文件
        video_files = []
        for file in os.listdir(path):
            if file.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
                video_files.append(os.path.join(path, file))
        
        total_count = len(video_files)
        print(f"📂 找到 {total_count} 个视频文件")
        
        # 处理每个视频文件
        for i, video_path in enumerate(video_files, 1):
            print(f"[{i}/{total_count}] 处理: {os.path.basename(video_path)}")
            if generate_random_thumbnail(video_path, overwrite, quality, size):
                success_count += 1
            else:
                fail_count += 1
    else:
        print(f"❌ 路径无效: {path}")
        return

    # 输出统计信息
    print(f"\n📊 处理完成:")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {fail_count}")
    print(f"📋 总计: {total_count}")


def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description="视频随机封面生成工具")
    parser.add_argument("path", help="视频文件路径或包含视频的文件夹路径")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的封面图")
    parser.add_argument("--quality", type=int, default=90, choices=range(1, 101), 
                        help="JPEG图片质量 (1-100)，默认90")
    parser.add_argument("--size", type=str, help="输出图片尺寸，格式为 'widthxheight'，例如 '1920x1080'")
    
    args = parser.parse_args()
    
    # 检查ffmpeg
    if not check_ffmpeg():
        print("⚠️ 警告: 未找到ffmpeg。请安装ffmpeg，这是moviepy的必要依赖。")
        print("   Windows用户可以从 https://ffmpeg.org/download.html 下载，并将ffmpeg.exe添加到环境变量PATH中。")
        print("   Linux用户可以使用包管理器安装，如 'sudo apt-get install ffmpeg'。")
    
    # 解析尺寸参数
    size = None
    if args.size:
        try:
            width, height = map(int, args.size.split('x'))
            size = (width, height)
        except ValueError:
            print(f"❌ 无效的尺寸格式: {args.size}。请使用 'widthxheight' 格式。")
            return
    
    # 处理路径
    process_folder(args.path, args.overwrite, args.quality, size)


if __name__ == "__main__":
    main()
