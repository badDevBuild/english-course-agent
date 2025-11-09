#!/usr/bin/env python3
"""
图片生成节点测试脚本

测试 analyze_image_needs 和 generate_images 节点的功能。
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_analyze_image_needs():
    """测试图片需求分析节点"""
    print("=" * 60)
    print("🧪 测试 1: analyze_image_needs 节点")
    print("=" * 60)
    print()
    
    from src.nodes import analyze_image_needs
    from src.state import CourseGenerationState
    
    # 模拟状态
    mock_state = {
        "final_lesson_content": """
# 今日课程：海洋动物

## 重点单词
1. **dolphin** (海豚) - A smart sea animal
2. **ocean** (海洋) - A large body of water
3. **swim** (游泳) - Move through water

## 学习句子
1. The dolphin swims in the ocean.（海豚在海洋中游泳）
2. I love the blue ocean.（我喜欢蓝色的海洋）
"""
    }
    
    try:
        print("📌 调用 analyze_image_needs...")
        result = analyze_image_needs(mock_state)
        
        print(f"✅ 调用成功")
        print(f"\n📊 分析结果:")
        print(f"   lesson_id: {result.get('lesson_id')}")
        print(f"   图片需求数量: {len(result.get('image_requirements', []))}")
        print()
        
        for req in result.get('image_requirements', []):
            print(f"   🖼️  {req['id']}")
            print(f"      类型: {req['type']}")
            print(f"      内容: {req['content']} ({req['description']})")
            print(f"      Prompt: {req['prompt_en'][:80]}...")
            print()
        
        return True, result
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None


def test_generate_images(image_requirements, lesson_id):
    """测试图片生成节点"""
    print("=" * 60)
    print("🧪 测试 2: generate_images 节点")
    print("=" * 60)
    print()
    
    from src.nodes import generate_images
    
    # 只生成第一张图片以节省时间
    limited_requirements = image_requirements[:1]
    
    mock_state = {
        "image_requirements": limited_requirements,
        "lesson_id": lesson_id
    }
    
    try:
        print(f"📌 生成图片（仅测试第 1/{len(image_requirements)} 张以节省时间）...")
        print()
        
        result = generate_images(mock_state)
        
        generated = result.get('generated_images', [])
        print(f"\n✅ 生成完成")
        print(f"📊 生成结果: {len(generated)}/{len(limited_requirements)} 张成功")
        print()
        
        for img in generated:
            print(f"   🖼️  {img['id']}")
            print(f"      相对路径: {img['file_path']}")
            print(f"      绝对路径: {img['absolute_path']}")
            print(f"      Alt 文本: {img['alt_text']}")
            
            # 验证文件是否存在
            if Path(img['absolute_path']).exists():
                file_size = Path(img['absolute_path']).stat().st_size / 1024
                print(f"      ✓ 文件存在，大小: {file_size:.2f} KB")
            else:
                print(f"      ✗ 文件不存在")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试流程"""
    print()
    print("🚀 图片生成节点单元测试")
    print("=" * 60)
    print()
    
    # 检查环境变量
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ 错误: 未找到 GOOGLE_API_KEY 环境变量")
        print("   请确保 .env 文件已正确配置")
        return False
    
    # 测试 1: 分析图片需求
    success1, result = test_analyze_image_needs()
    if not success1:
        return False
    
    # 询问是否继续测试图片生成
    print()
    user_input = input("⚠️  继续测试图片生成吗？(会消耗 API 配额，约 8 秒) [y/N]: ").strip().lower()
    if user_input != 'y':
        print("跳过图片生成测试")
        print()
        print("=" * 60)
        print("✅ 部分测试完成（仅测试了分析功能）")
        print("=" * 60)
        return True
    
    # 测试 2: 生成图片
    image_requirements = result.get('image_requirements', [])
    lesson_id = result.get('lesson_id')
    
    if not image_requirements:
        print("⚠️  没有图片需求，跳过生成测试")
        return True
    
    success2 = test_generate_images(image_requirements, lesson_id)
    
    # 总结
    print()
    print("=" * 60)
    if success1 and success2:
        print("🎉 所有测试通过！")
    elif success1:
        print("⚠️  部分测试通过（图片生成失败）")
    else:
        print("❌ 测试失败")
    print("=" * 60)
    print()
    
    return success1 and success2


if __name__ == "__main__":
    # 加载环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    success = main()
    sys.exit(0 if success else 1)
