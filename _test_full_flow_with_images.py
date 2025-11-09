#!/usr/bin/env python3
"""
完整流程测试：包含图片生成的端到端测试

测试流程：
1. 加载框架
2. 生成初稿
3. 用户同意
4. 分析图片需求
5. 生成图片
6. 生成包含图片的网页
7. 部署
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_full_flow():
    """测试完整流程"""
    print("=" * 70)
    print("🚀 完整流程测试：课程生成 + 图片生成 + 网页部署")
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
            "thread_id": "test_with_images_001"
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
    
    print("📌 步骤 1: 启动流程 - 生成初稿")
    print()
    
    try:
        # 第一次调用：生成初稿（会在 generate_initial_draft 后中断）
        result = app.invoke(initial_state, config)
        
        print(f"✅ 初稿生成完成")
        print(f"   草稿长度: {len(result.get('lesson_draft', ''))} 字符")
        print()
        
        # 模拟用户同意
        print("📌 步骤 2: 用户同意课程内容")
        print()
        
        # 步骤 2.1: 更新状态中的 user_feedback
        print("   更新用户反馈...")
        app.update_state(config, {"user_feedback": "同意"})
        
        # 步骤 2.2: 用 None 继续执行（从中断点恢复）
        # 第二次调用：定稿 -> 分析图片 -> 生成图片 -> 生成网页 -> 部署（会在 deploy_webpage_node 后中断）
        print("📌 步骤 3-7: 自动执行图片生成和网页部署...")
        print()
        
        result = app.invoke(None, config)
        
        # 检查结果
        print()
        print("=" * 70)
        print("📊 流程执行结果")
        print("=" * 70)
        print()
        
        print(f"✅ 最终课程内容: {len(result.get('final_lesson_content', ''))} 字符")
        print(f"✅ 课程ID: {result.get('lesson_id', 'N/A')}")
        print(f"✅ 图片需求数量: {len(result.get('image_requirements', []))}")
        
        # 显示图片需求
        for req in result.get('image_requirements', []):
            print(f"   - {req['id']}: {req['content']}")
        
        print(f"✅ 生成的图片数量: {len(result.get('generated_images', []))}")
        
        # 显示生成的图片
        for img in result.get('generated_images', []):
            img_path = Path(img['absolute_path'])
            if img_path.exists():
                file_size = img_path.stat().st_size / 1024
                print(f"   ✓ {img['id']}: {file_size:.2f} KB")
            else:
                print(f"   ✗ {img['id']}: 文件不存在")
        
        print(f"✅ 网页HTML长度: {len(result.get('webpage_html', ''))} 字符")
        
        # 检查HTML是否包含图片标签
        html = result.get('webpage_html', '')
        img_count = html.count('<img')
        print(f"✅ HTML中的<img>标签数量: {img_count}")
        
        print(f"✅ 部署URL: {result.get('deployment_url', 'N/A')}")
        
        print()
        print("=" * 70)
        print("🎉 完整流程测试成功！")
        print("=" * 70)
        print()
        
        # 提示查看结果
        if result.get('deployment_url'):
            print("💡 查看生成的网页:")
            print(f"   {result['deployment_url']}")
            print()
            print("   或在浏览器中打开:")
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
    print("   - 此测试会调用 Gemini API 生成图片")
    print("   - 预计耗时: 40-60 秒")
    print("   - 预计消耗: 约 5-7 张图片的 API 配额")
    print()
    
    user_input = input("是否继续测试完整流程？ [y/N]: ").strip().lower()
    if user_input != 'y':
        print("测试已取消")
        return False
    
    print()
    success = test_full_flow()
    
    if not success:
        print()
        print("💡 调试提示:")
        print("   - 检查 API Key 是否有效")
        print("   - 查看日志获取详细错误信息")
        print("   - 确保网络连接正常")
    
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
