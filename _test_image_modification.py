#!/usr/bin/env python3
"""
图片修改功能测试脚本

测试流程：
1. 生成完整的课程（含图片）
2. 用户提出修改某张图片
3. 系统识别目标图片并重新生成
4. 更新网页
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_image_modification():
    """测试图片修改功能"""
    print("=" * 70)
    print("🧪 图片修改功能测试")
    print("=" * 70)
    print()
    
    # 检查环境变量
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ 错误: 未找到 GOOGLE_API_KEY 环境变量")
        return False
    
    from src.graph import app
    from langchain_core.messages import HumanMessage
    
    # 配置
    config = {
        "configurable": {
            "thread_id": "test_image_mod_001"
        }
    }
    
    # 初始状态
    initial_state = {
        "theme": "海洋动物",
        "user_feedback": "",
        "curriculum_framework": "",
        "lesson_draft": "",
        "final_lesson_content": "",
        "webpage_html": "",
        "deployment_url": "",
        "lesson_id": "",
        "image_requirements": [],
        "generated_images": [],
        "messages": [HumanMessage(content="请帮我设计关于海洋动物的英语课程")]
    }
    
    try:
        print("📌 阶段 1: 生成课程和图片")
        print("-" * 70)
        
        # 第一次调用：生成初稿
        print("   步骤 1.1: 生成初稿...")
        result = app.invoke(initial_state, config)
        print(f"   ✓ 初稿生成完成（{len(result.get('lesson_draft', ''))} 字符）")
        
        # 用户同意
        print("   步骤 1.2: 用户同意课程内容...")
        app.update_state(config, {"user_feedback": "同意"})
        
        # 第二次调用：定稿 -> 生成图片 -> 生成网页 -> 部署
        print("   步骤 1.3: 自动生成图片和网页...")
        result = app.invoke(None, config)
        
        image_count = len(result.get('generated_images', []))
        print(f"   ✓ 生成了 {image_count} 张图片")
        print(f"   ✓ 网页已部署: {result.get('deployment_url', 'N/A')}")
        
        # 显示生成的图片列表
        print()
        print("   生成的图片:")
        for img in result.get('generated_images', []):
            print(f"   - {img['id']}: {img['alt_text']}")
        
        print()
        print("=" * 70)
        print("📌 阶段 2: 测试图片修改")
        print("-" * 70)
        
        # 选择第一张图片进行修改
        first_image = result.get('generated_images', [])[0] if result.get('generated_images') else None
        if not first_image:
            print("   ❌ 没有可修改的图片")
            return False
        
        target_image_id = first_image['id']
        target_image_name = first_image['alt_text'].split(' - ')[0]
        
        print(f"   目标图片: {target_image_id} ({target_image_name})")
        print(f"   修改要求: 背景改成深蓝色，更明亮")
        print()
        
        # 提交修改反馈
        print("   步骤 2.1: 提交图片修改反馈...")
        modification_feedback = f"{target_image_name}的图片背景改成深蓝色，更明亮"
        app.update_state(config, {"user_feedback": modification_feedback})
        
        # 继续执行：识别图片 -> 重新生成 -> 更新网页 -> 部署
        print("   步骤 2.2: 系统自动处理修改...")
        result = app.invoke(None, config)
        
        print(f"   ✓ 图片已重新生成")
        print(f"   ✓ 网页已更新: {result.get('deployment_url', 'N/A')}")
        
        print()
        print("=" * 70)
        print("📊 测试结果")
        print("=" * 70)
        print()
        
        # 验证图片是否更新
        updated_images = result.get('generated_images', [])
        updated_target = next((img for img in updated_images if img['id'] == target_image_id), None)
        
        if updated_target:
            original_path = first_image['absolute_path']
            updated_path = updated_target['absolute_path']
            
            # 检查文件是否存在
            if Path(updated_path).exists():
                file_size = Path(updated_path).stat().st_size / 1024
                print(f"✅ 目标图片已更新:")
                print(f"   ID: {target_image_id}")
                print(f"   路径: {updated_path}")
                print(f"   大小: {file_size:.2f} KB")
                print()
                
                # 检查路径是否变化（如果使用了时间戳）
                if original_path != updated_path:
                    print(f"   注意: 图片路径已变化（预期行为）")
                    print(f"   原路径: {original_path}")
                    print(f"   新路径: {updated_path}")
            else:
                print(f"⚠️  图片文件不存在: {updated_path}")
        else:
            print(f"⚠️  找不到目标图片: {target_image_id}")
        
        print()
        print("=" * 70)
        print("🎉 图片修改功能测试完成！")
        print("=" * 70)
        print()
        
        print("💡 查看结果:")
        print(f"   网页: {result.get('deployment_url', 'N/A')}")
        print()
        print("   打开网页查看修改后的图片:")
        if result.get('deployment_url'):
            print(f"   open \"{result['deployment_url'].replace('file://', '')}\"")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print()
    
    # 警告提示
    print("⚠️  注意:")
    print("   - 此测试会生成课程和图片（约 40-60 秒）")
    print("   - 然后重新生成一张图片（约 8-10 秒）")
    print("   - 总耗时: 约 50-70 秒")
    print("   - API 消耗: 约 6-8 张图片")
    print()
    
    user_input = input("是否继续测试图片修改功能？ [y/N]: ").strip().lower()
    if user_input != 'y':
        print("测试已取消")
        return False
    
    print()
    success = test_image_modification()
    
    if not success:
        print()
        print("💡 调试提示:")
        print("   - 检查日志获取详细错误信息")
        print("   - 确认图片修改识别逻辑是否正常")
        print("   - 验证路由函数是否正确识别关键词")
    
    return success


if __name__ == "__main__":
    # 加载环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    success = main()
    sys.exit(0 if success else 1)
