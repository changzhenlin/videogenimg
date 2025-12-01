import os
import sys
import tempfile
import shutil
from tkinter import Tk, filedialog

# 尝试导入PIL库，如果失败提供更详细的错误信息
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("❌ 错误: 无法导入PIL (Pillow)库。请确认是否正确安装。")
    print("  建议尝试以下命令重新安装:")
    print("  - pip install pillow")
    print(f"  当前Python环境: {sys.executable}")
    print(f"  Python版本: {sys.version}")
    sys.exit(1)

# 支持的视频格式
SUPPORTED_EXTS = [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"]

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
    error_dirs = []
    
    def walk(dir_path, depth):
        try:
            # 检查目录是否存在且可访问
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return
                
            for name in os.listdir(dir_path):
                p = os.path.join(dir_path, name)
                try:
                    if os.path.isfile(p) and any(name.lower().endswith(ext) for ext in SUPPORTED_EXTS):
                        result.append(p)
                    elif os.path.isdir(p) and depth < max_depth:
                        walk(p, depth + 1)
                except Exception as e:
                    # 记录访问失败的文件或目录
                    error_dirs.append((p, str(e)))
        except Exception as e:
            # 记录无法访问的目录
            error_dirs.append((dir_path, str(e)))
    
    walk(root_dir, 0)
    
    # 如果有无法访问的目录，打印警告信息
    if error_dirs and len(error_dirs) <= 5:  # 限制显示的错误数量
        print(f"\n⚠️ 警告: 无法访问以下 {len(error_dirs)} 个文件或目录:")
        for path, error in error_dirs[:3]:  # 只显示前3个错误
            print(f"  - {path}: {error}")
        if len(error_dirs) > 3:
            print(f"  - ... 等{len(error_dirs) - 3}个更多错误")
    elif error_dirs:
        print(f"\n⚠️ 警告: 无法访问 {len(error_dirs)} 个文件或目录")
    
    return result

def add_text_to_image(image_path, text, output_path=None, center=False):
    """在图片上添加文字
    
    参数:
    image_path: 原始图片路径
    text: 要添加的文字
    output_path: 输出图片路径，如果为None则覆盖原图
    center: 是否居中显示文字
    
    返回:
    bool: 是否成功
    str: 错误信息（如果失败）
    """
    """在图片上添加文字
    
    参数:
    image_path: 原始图片路径
    text: 要添加的文字
    output_path: 输出图片路径，如果为None则覆盖原图
    
    返回:
    bool: 是否成功
    str: 错误信息（如果失败）
    """
    try:
        # 如果未指定输出路径，覆盖原图
        if output_path is None:
            output_path = image_path
        
        # 打开图片
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # 获取图片尺寸
        width, height = img.size
        
        # 尝试使用系统字体，确保支持中文
        font_size = int(height * 0.13)  # 字体大小为图片高度的15%
        font = None
        
        # 尝试几种可能的中文字体，优先使用微软雅黑
        font_candidates = [
            "msyh.ttc",    # 微软雅黑（优先）
            "msyh.ttf",    # 微软雅黑的另一种格式
            "simhei.ttf",  # 黑体
            "simsun.ttc",  # 宋体
            "Arial.ttf"     # fallback英文字体
        ]
        
        # 尝试从系统字体目录加载字体
        for font_name in font_candidates:
            try:
                # 尝试直接加载字体
                font = ImageFont.truetype(font_name, font_size)
                break
            except IOError:
                # 尝试在系统字体目录中查找
                try:
                    # Windows系统字体目录
                    system_font_path = os.path.join("C:", "Windows", "Fonts", font_name)
                    if os.path.exists(system_font_path):
                        font = ImageFont.truetype(system_font_path, font_size)
                        break
                except:
                    continue
        
        # 如果无法加载字体，使用默认字体
        if font is None:
            font = ImageFont.load_default()
            print("⚠️ 无法加载中文字体，使用默认字体")
        
        # 计算文字位置（居中显示在图片底部）
        try:
            # 尝试获取文字尺寸
            text_width, text_height = draw.textsize(text, font=font)
        except:
            # 如果无法获取文字尺寸，使用估算值
            text_width = len(text) * font_size * 0.3
            text_height = font_size
        
        # 根据center参数决定文字位置
        if center:
            # 居中显示
            x = 0
            y = height - text_height - int(height * 0.03)
        else:
            # 默认在底部靠左
            x = 0
            y = height - text_height - int(height * 0.03)  # 底部留出5%的边距
        
        # 绘制白色文字（无背景）
        draw.text((x, y), text, font=font, fill=(255, 255, 255))
        
        # 保存图片
        img.save(output_path, "JPEG", quality=100)
        
        return True, ""
    except Exception as e:
        return False, str(e)

def main():
    """主函数 - 将视频文件名前五个字合成到同目录下的poster.jpg图片上"""
    print("🎬 视频标题合成工具")
    print("📝 功能: 将视频文件名前五个字合成到同目录下的poster.jpg图片上")
    print("🔍 支持的视频格式: " + ", ".join(SUPPORTED_EXTS))
    print("💡 使用提示: 按Ctrl+C可随时终止程序")
    
    try:
        # 选择文件夹
        folder_path = choose_folder()
        if not folder_path:
            print("⚠️ 未选择文件夹，退出程序")
            return
        
        print(f"\n📂 已选择文件夹: {folder_path}")
        print("🔍 正在扫描视频文件...")
        
        # 收集视频文件
        videos = collect_videos(folder_path, max_depth=2)
        if not videos:
            print("⚠️ 选中文件夹下未发现支持的视频文件")
            return
        
        print(f"⏳ 共找到 {len(videos)} 个视频，开始处理...")
        print("----------------------------------------")
        
        # 为每个视频文件处理poster.jpg
        processed_count = 0
        no_poster_count = 0
        error_count = 0
        
        for i, video_path in enumerate(videos, 1):
            try:
                video_name = os.path.basename(video_path)
                print(f"🎞️ 处理 ({i}/{len(videos)}): {video_name}")
                
                # 获取视频文件所在目录
                video_dir = os.path.dirname(video_path)
                
                # 处理poster.jpg（前5个字，底部靠左）
                poster_path = os.path.join(video_dir, "poster.jpg")
                if os.path.exists(poster_path):
                    # 提取视频文件名前五个字（不包括扩展名）
                    video_name_no_ext = os.path.splitext(video_name)[0]
                    title_text_poster = video_name_no_ext[:5]  # 获取前五个字符
                    
                    print(f"  📝 提取标题(poster): '{title_text_poster}'")
                    print(f"  🖼️ 找到poster.jpg")
                    
                    # 将文字合成到poster.jpg（不居中）
                    success, error_msg = add_text_to_image(poster_path, title_text_poster, center=False)
                    if success:
                        print(f"  ✅ 成功添加文字到poster.jpg")
                        processed_count += 1
                    else:
                        print(f"  ❌ 添加文字到poster.jpg失败: {error_msg}")
                        error_count += 1
                else:
                    print(f"  ❌ 未找到 poster.jpg")
                    no_poster_count += 1
                
                # 处理fanart.jpg（前10个字，居中显示）
                fanart_path = os.path.join(video_dir, "fanart.jpg")
                if os.path.exists(fanart_path):
                    # 提取视频文件名前十个字（不包括扩展名）
                    video_name_no_ext = os.path.splitext(video_name)[0]
                    title_text_fanart = video_name_no_ext[:10]  # 获取前十个字符
                    
                    print(f"  📝 提取标题(fanart): '{title_text_fanart}'")
                    print(f"  🖼️ 找到fanart.jpg")
                    
                    # 将文字合成到fanart.jpg（居中显示）
                    success, error_msg = add_text_to_image(fanart_path, title_text_fanart, center=True)
                    if success:
                        print(f"  ✅ 成功添加文字到fanart.jpg")
                        processed_count += 1
                    else:
                        print(f"  ❌ 添加文字到fanart.jpg失败: {error_msg}")
                        error_count += 1
                else:
                    print(f"  ❌ 未找到 fanart.jpg")
                    no_poster_count += 1
                    
            except Exception as e:
                print(f"  ⚠️ 处理视频时发生异常: {str(e)}")
                error_count += 1
        
        print("----------------------------------------")
        print(f"\n📊 处理完成！")
        print(f"✅ 成功处理: {processed_count} 个")
        print(f"❌ 缺少图片: {no_poster_count} 个")
        print(f"⚠️ 处理失败: {error_count} 个")
        print(f"📋 总计: {len(videos)} 个视频")
        print("\n💡 提示:")
        print("  - poster.jpg: 前5个字，底部靠左，使用微软雅黑字体")
        print("  - fanart.jpg: 前10个字，居中显示，使用微软雅黑字体")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作，程序已停止")
    except Exception as e:
        print(f"\n❌ 程序运行时发生错误: {str(e)}")
        print("  如果问题持续，请检查文件权限或重新安装依赖库")
    finally:
        print("\n👋 感谢使用视频标题合成工具！")

if __name__ == "__main__":
    main()