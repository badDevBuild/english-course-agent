import uuid
from dotenv import load_dotenv

# 必须在导入任何自定义模块之前首先加载环境变量
load_dotenv()

from src.graph import app

def run_test():
    """
    一个简单的脚本，用于在本地终端测试核心的 LangGraph 工作流。
    模拟了用户与 Bot 之间的完整交互。
    """
    # 为本次测试运行创建一个唯一的会话 ID
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    print("--- 测试开始 ---")
    
    # 1. 模拟用户输入 /start <主题>
    print("\n[用户]: /start 探索宇宙")
    theme_input = {"theme": "探索宇宙"}
    
    # 调用图，它会运行直到第一个中断点（generate_initial_draft 之后）
    current_state = app.invoke(theme_input, config=config)
    draft = current_state.get("lesson_draft")
    
    print("\n[Agent]: 课程初稿已生成！")
    print("-------------------------")
    print(draft)
    print("-------------------------")
    
    # 2. 模拟用户提出修改意见
    print("\n[用户]: 第二部分太难了，请简化一下，多用一些比喻。")
    feedback_input = {"user_feedback": "第二部分太难了，请简化一下，多用一些比喻。"}
    
    # 再次调用图，它会从上次中断的地方继续，运行到下一个中断点（revise_draft 之后）
    current_state = app.invoke(feedback_input, config=config)
    revised_draft = current_state.get("lesson_draft")
    
    print("\n[Agent]: 草稿已根据您的意见更新！")
    print("-------------------------")
    print(revised_draft)
    print("-------------------------")
    
    # 3. 模拟用户同意
    print("\n[用户]: 同意")
    approval_input = {"user_feedback": "同意"}
    
    # 最后一次调用图，这次应该会运行到 END 节点并结束
    final_state = app.invoke(approval_input, config=config)
    
    print("\n[Agent]: 课程已定稿！")
    print("-------------------------")
    # LangGraph 流程结束时，invoke 返回的是最终的完整状态对象。
    # 我们直接通过键来访问最终内容。
    final_content = final_state["final_lesson_content"]
    print(final_content)
    print("-------------------------")
    
    print("\n--- 测试结束 ---")


if __name__ == "__main__":
    run_test()
