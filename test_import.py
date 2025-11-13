import sys
import numpy as np
from PIL import Image

# 全面测试所有必要模块的导入
def test_imports():
    print("="*50)
    print("🔍 模块导入测试")
    print("="*50)
    
    # 测试moviepy
    try:
        from moviepy import VideoFileClip
        print("✅ moviepy导入成功！")
        print(f"✅ 成功导入VideoFileClip类")
        print(f"✅ moviepy版本: {__import__('moviepy').__version__}")
    except ImportError as e:
        print(f"❌ moviepy导入失败: {e}")
        return False
    
    # 测试PIL/Pillow
    try:
        from PIL import Image
        print("✅ Pillow导入成功！")
        print(f"✅ 成功导入Image类")
    except ImportError as e:
        print(f"❌ Pillow导入失败: {e}")
        return False
    
    # 测试OpenCV
    try:
        import cv2
        print("✅ OpenCV导入成功！")
        print(f"✅ OpenCV版本: {cv2.__version__}")
    except ImportError as e:
        print(f"❌ OpenCV导入失败: {e}")
        return False
    
    # 测试NumPy
    try:
        import numpy as np
        print("✅ NumPy导入成功！")
        print(f"✅ NumPy版本: {np.__version__}")
    except ImportError as e:
        print(f"❌ NumPy导入失败: {e}")
        return False
    
    # 测试tkinter（通常是Python标准库的一部分）
    try:
        import tkinter as tk
        print("✅ tkinter导入成功！")
    except ImportError as e:
        print(f"❌ tkinter导入失败: {e}")
        print("   注意：tkinter通常是Python标准库的一部分")
        # tkinter失败不影响主要功能测试，仅警告
    
    print("\n✅ 所有必要模块导入成功！")
    return True

# 测试人脸检测功能
def test_face_detection():
    print("\n" + "="*50)
    print("👤 人脸检测功能测试")
    print("="*50)
    
    # 尝试导入cv2和has_face函数
    try:
        import cv2
        
        # 动态导入has_face函数
        import importlib.util
        spec = importlib.util.spec_from_file_location("auto_thumbnail", "auto_thumbnail.py")
        auto_thumbnail = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auto_thumbnail)
        
        print("🎨 创建测试图像进行人脸检测验证...")
        
        # 测试用例1: 空白图像（不应该检测到人脸）
        print("\n🔹 测试用例1: 空白图像")
        blank_image = np.zeros((400, 600, 3), dtype=np.uint8)
        pil_blank_image = Image.fromarray(blank_image)
        result1 = auto_thumbnail.has_face(pil_blank_image)
        print(f"  结果: {'检测到人脸 ❌ (误判)' if result1 else '未检测到人脸 ✅'}")
        print(f"  期望: 未检测到人脸")
        test1_passed = not result1
        
        # 测试用例2: 简单形状图像（不应该检测到人脸）
        print("\n🔹 测试用例2: 简单形状图像")
        shape_image = np.ones((400, 600, 3), dtype=np.uint8) * 255  # 白色背景
        # 添加一个圆形
        cv2.circle(shape_image, (300, 200), 50, (0, 0, 255), -1)
        pil_shape_image = Image.fromarray(shape_image)
        result2 = auto_thumbnail.has_face(pil_shape_image)
        print(f"  结果: {'检测到人脸 ❌ (误判)' if result2 else '未检测到人脸 ✅'}")
        print(f"  期望: 未检测到人脸")
        test2_passed = not result2
        
        # 测试用例3: 边缘区域图像（不应该检测到人脸）
        print("\n🔹 测试用例3: 边缘区域图像")
        edge_image = np.ones((400, 600, 3), dtype=np.uint8) * 255
        # 在角落添加一个矩形
        cv2.rectangle(edge_image, (10, 10), (100, 100), (0, 0, 0), -1)
        pil_edge_image = Image.fromarray(edge_image)
        result3 = auto_thumbnail.has_face(pil_edge_image)
        print(f"  结果: {'检测到人脸 ❌ (误判)' if result3 else '未检测到人脸 ✅'}")
        print(f"  期望: 未检测到人脸")
        test3_passed = not result3
        
        # 总结测试结果
        print("\n" + "="*50)
        print("📊 人脸检测测试结果:")
        print(f"✅ 测试用例1通过: {test1_passed}")
        print(f"✅ 测试用例2通过: {test2_passed}")
        print(f"✅ 测试用例3通过: {test3_passed}")
        
        all_passed = test1_passed and test2_passed and test3_passed
        if all_passed:
            print("🎉 所有测试用例通过！人脸检测不再误判")
        else:
            print("❌ 部分测试用例失败，请检查has_face函数")
        print("="*50)
        
        return all_passed
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

if __name__ == "__main__":
    print("🎬 运行视频封面生成工具测试")
    print()
    
    # 运行模块导入测试
    imports_success = test_imports()
    
    # 运行人脸检测测试
    face_detection_success = test_face_detection()
    
    print("\n📋 总体测试结果:")
    print(f"模块导入测试: {'✅ 通过' if imports_success else '❌ 失败'}")
    print(f"人脸检测测试: {'✅ 通过' if face_detection_success else '❌ 失败'}")
    
    # 如果所有测试都通过，则退出码为0，否则为1
    sys.exit(0 if imports_success and face_detection_success else 1)
