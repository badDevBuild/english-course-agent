#!/usr/bin/env python3
"""Gemini Image API 测试脚本"""

import os
import sys
from pathlib import Path
from datetime import datetime

def test_image_api():
    print("=" * 60)
    print("🧪 Gemini Image API 测试脚本")
    print("=" * 60)
    print()
    
    # 检查 API Key
    print("📌 步骤 1: 检查环境变量...")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ 错误: 未找到 GOOGLE_API_KEY 环境变量")
        return False
    print(f"✅ API Key 已设置 (长度: {len(api_key)})")
    print()
    
    # 导入依赖
    print("📌 步骤 2: 导入依赖库...")
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        from io import BytesIO
        print("✅ 所有依赖已成功导入")
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print()
        print("💡 解决方案:")
        print("   请运行: pip install google-genai Pillow")
        return False
    print()
    
    # 初始化客户端
    print("📌 步骤 3: 初始化 Gemini 客户端...")
    try:
        client = genai.Client(api_key=api_key)
        print("✅ 客户端初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False
    print()
    
    # 生成测试图片
    print("📌 步骤 4: 调用 Image API 生成测试图片...")
    print("   Prompt: A friendly cartoon dolphin swimming in blue ocean")
    print("   模型: gemini-2.5-flash-image")
    print("   比例: 1:1 (1024x1024)")
    print()
    
    prompt = (
        "A friendly cartoon dolphin swimming in clear blue ocean water, "
        "bright colors, educational illustration for children, simple background"
    )
    
    try:
        start_time = datetime.now()
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
            config=types.GenerateContentConfig(
                image_config=types.ImageConfig(aspect_ratio="1:1")
            )
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        print(f"✅ API 调用成功 (耗时: {duration:.2f}秒)")
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        print()
        print("💡 可能的原因:")
        print("   1. API Key 无效或已过期")
        print("   2. 未启用 Imagen API")
        print("   3. 网络连接问题")
        print("   4. API 配额已用完")
        return False
    print()
    
    # 保存图片
    print("📌 步骤 5: 提取图片数据并保存到文件...")
    
    test_dir = Path("test_images")
    test_dir.mkdir(exist_ok=True)
    
    image_saved = False
    for part in response.candidates[0].content.parts:
        if part.text is not None:
            print(f"   响应文本: {part.text}")
        elif part.inline_data is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = test_dir / f"test_dolphin_{timestamp}.png"
            
            try:
                image = Image.open(BytesIO(part.inline_data.data))
                image.save(filepath)
                
                width, height = image.size
                file_size = filepath.stat().st_size / 1024
                
                print(f"✅ 图片已保存到: {filepath}")
                print(f"   尺寸: {width}x{height}px")
                print(f"   大小: {file_size:.2f} KB")
                
                image_saved = True
            except Exception as e:
                print(f"❌ 保存图片失败: {e}")
                return False
    
    if not image_saved:
        print("❌ 响应中没有找到图片数据")
        return False
    print()
    
    # 总结
    print("=" * 60)
    print("🎉 测试完成！所有步骤均通过")
    print("=" * 60)
    print()
    print("📊 测试摘要:")
    print(f"   ✅ API 连接: 正常")
    print(f"   ✅ 图片生成: 成功")
    print(f"   ✅ 文件保存: 成功")
    print(f"   ⏱️  生成耗时: {duration:.2f}秒")
    print()
    print("💡 下一步:")
    print("   1. 查看生成的图片: open test_images/")
    print("   2. 如果图片质量满意，可以开始集成到项目中")
    print()
    
    return True


if __name__ == "__main__":
    # 加载环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # 运行测试
    success = test_image_api()
    sys.exit(0 if success else 1)
