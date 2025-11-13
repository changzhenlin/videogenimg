try:
    # 从moviepy直接导入VideoFileClip，不再通过editor模块
    from moviepy import VideoFileClip
    print("✅ moviepy导入成功！")
    print(f"✅ 成功导入VideoFileClip类")
    print(f"✅ moviepy版本: {__import__('moviepy').__version__}")
    import moviepy
    print(f"✅ moviepy包路径: {moviepy.__file__}")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    import sys
    print(f"Python路径: {sys.path}")
