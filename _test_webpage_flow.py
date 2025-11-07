#!/usr/bin/env python3
"""
测试网页生成流程的脚本

此脚本模拟完整的工作流：
1. 生成课程初稿
2. 用户批准内容
3. 生成网页
4. 部署网页
5. 用户批准网页
"""

import os
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 设置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.graph import app

def test_webpage_flow():
    """测试完整的网页生成流程"""
    
    print("\n" + "=" * 80)
    print("开始测试网页生成流程")
    print("=" * 80)
    
    # 创建一个测试用的 thread_id
    thread_id = "test_webpage_flow_001"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 步骤 1: 启动流程，生成课程初稿
    print("\n[步骤 1] 启动流程，生成课程初稿...")
    initial_input = {"theme": "恐龙世界"}
    
    try:
        state = app.invoke(initial_input, config=config)
        print(f"✓ 初稿生成完成")
        print(f"  - lesson_draft 长度: {len(state.get('lesson_draft', ''))}")
        
        # 步骤 2: 用户批准课程内容
        print("\n[步骤 2] 用户批准课程内容...")
        app.update_state(config, {"user_feedback": "同意"})
        state = app.invoke(None, config=config)
        print(f"✓ 课程内容已确认")
        print(f"  - final_lesson_content 长度: {len(state.get('final_lesson_content', ''))}")
        print(f"  - webpage_html 长度: {len(state.get('webpage_html', ''))}")
        print(f"  - deployment_url: {state.get('deployment_url', 'N/A')}")
        
        # 检查是否在 deploy_webpage_node 后中断
        if state.get('deployment_url'):
            print(f"\n✓ 网页已成功部署！")
            print(f"  访问链接: {state['deployment_url']}")
            
            # 步骤 3: 用户批准网页（结束流程）
            print("\n[步骤 3] 用户批准网页...")
            app.update_state(config, {"user_feedback": "满意"})
            state = app.invoke(None, config=config)
            
            if "__end__" in state:
                print(f"\n✓✓✓ 流程成功完成！✓✓✓")
                print(f"  最终部署链接: {state['deployment_url']}")
            else:
                print(f"\n⚠ 流程未正常结束")
                print(f"  当前状态键: {list(state.keys())}")
        else:
            print(f"\n✗ 网页部署失败")
            print(f"  当前状态键: {list(state.keys())}")
            
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试结束")
    print("=" * 80)

def test_webpage_revision():
    """测试网页修改流程"""
    
    print("\n" + "=" * 80)
    print("开始测试网页修改流程")
    print("=" * 80)
    
    # 创建一个测试用的 thread_id
    thread_id = "test_webpage_revision_001"
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # 步骤 1: 启动流程并批准初稿
        print("\n[步骤 1] 启动流程...")
        state = app.invoke({"theme": "太空探险"}, config=config)
        print(f"✓ 初稿生成完成")
        
        # 步骤 2: 批准课程内容
        print("\n[步骤 2] 批准课程内容...")
        app.update_state(config, {"user_feedback": "同意"})
        state = app.invoke(None, config=config)
        print(f"✓ 网页已部署")
        print(f"  deployment_url: {state.get('deployment_url')}")
        
        # 步骤 3: 用户要求修改网页
        print("\n[步骤 3] 用户要求修改网页...")
        app.update_state(config, {"user_feedback": "请把字体调大一点，颜色改成蓝色"})
        state = app.invoke(None, config=config)
        
        if state.get('deployment_url'):
            print(f"✓ 网页已重新生成并部署")
            print(f"  新的 deployment_url: {state['deployment_url']}")
            
            # 步骤 4: 用户批准修改后的网页
            print("\n[步骤 4] 用户批准修改后的网页...")
            app.update_state(config, {"user_feedback": "可以"})
            state = app.invoke(None, config=config)
            
            if "__end__" in state:
                print(f"\n✓✓✓ 修改流程成功完成！✓✓✓")
            else:
                print(f"\n⚠ 流程未正常结束")
        else:
            print(f"\n✗ 网页修改失败")
            
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试结束")
    print("=" * 80)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试网页生成流程")
    parser.add_argument(
        "--test",
        choices=["flow", "revision", "all"],
        default="flow",
        help="选择要运行的测试：flow（基本流程）、revision（修改流程）、all（全部）"
    )
    
    args = parser.parse_args()
    
    if args.test in ["flow", "all"]:
        test_webpage_flow()
    
    if args.test in ["revision", "all"]:
        print("\n\n")
        test_webpage_revision()
