import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import CourseGenerationState
from .nodes import (
    load_framework,
    generate_initial_draft,
    revise_draft,
    finalize_content,
    analyze_image_needs,        # v2.0 新增
    generate_images,             # v2.0 新增
    regenerate_single_image,     # v2.0 新增
    generate_webpage,
    deploy_webpage_node,
)

# --- 日志配置 ---
import logging
logger = logging.getLogger(__name__)

# 创建一个到 SQLite 文件的持久连接
conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)

# 使用连接直接初始化 SqliteSaver
checkpointer = SqliteSaver(conn=conn)

def route_content_feedback(state: CourseGenerationState) -> str:
    """
    根据用户的反馈决定下一步的路由。

    如果用户反馈包含 "同意" 或 "approve"，则进入定稿流程。
    否则，回到修改草稿的步骤。

    Args:
        state (CourseGenerationState): 当前的图状态。

    Returns:
        str: 下一个节点的名称。
    """
    logger.info("=" * 80)
    logger.info("--- 正在进行路由决策: 内容审核 ---")
    
    # 记录完整的状态信息用于调试
    logger.info(f"[路由决策] 当前状态键: {list(state.keys())}")
    logger.info(f"[路由决策] theme: {state.get('theme', 'N/A')}")
    logger.info(f"[路由决策] user_feedback 原始值: '{state.get('user_feedback', '')}'")
    logger.info(f"[路由决策] lesson_draft 是否存在: {bool(state.get('lesson_draft'))}")
    logger.info(f"[路由决策] lesson_draft 长度: {len(state.get('lesson_draft', ''))}")
    logger.info(f"[路由决策] final_lesson_content 是否存在: {bool(state.get('final_lesson_content'))}")
    
    user_feedback = state.get("user_feedback", "").strip().lower()
    logger.info(f"[路由决策] user_feedback 处理后值: '{user_feedback}'")

    # 检查用户是否明确表示同意
    if "同意" in user_feedback or "approve" in user_feedback:
        logger.info("✓ 路由决策结果: 用户已同意，内容进入定稿 -> 'finalize_content'")
        logger.info("=" * 80)
        return "finalize_content"
    
    # 任何其他非空反馈都视为修改意见
    if user_feedback:
        logger.info("✓ 路由决策结果: 用户提出修改意见，返回修改流程 -> 'revise_draft'")
        logger.info("=" * 80)
        return "revise_draft"
        
    # 如果反馈为空：这通常发生在首次生成初稿后、用户尚未提供反馈时。
    # 由于我们设置了 interrupt_after=["generate_initial_draft"]，
    # 路由决策会在中断前被评估并保存。这里我们返回 'revise_draft'，
    # 这样当用户提供反馈并恢复执行时，图会正确地进入 revise_draft 节点。
    logger.info("ℹ 路由决策结果: user_feedback 为空（首次生成或中断恢复），默认 -> 'revise_draft'")
    logger.info("  （这是正常的行为，用户反馈后会从中断点继续执行）")
    logger.info("=" * 80)
    return "revise_draft"

def route_webpage_feedback(state: CourseGenerationState) -> str:
    """
    根据用户对网页的反馈决定下一步的路由（v2.0 增强版）。

    支持三种路由：
    1. 批准关键词 -> END（流程结束）
    2. 包含图片修改关键词 -> regenerate_single_image（重新生成单张图片）
    3. 其他修改意见 -> generate_webpage（重新生成网页）

    Args:
        state (CourseGenerationState): 当前的图状态。

    Returns:
        str: 下一个节点的名称或 END。
    """
    logger.info("=" * 80)
    logger.info("--- 正在进行路由决策: 网页审核（v2.0 增强版）---")
    
    # 记录完整的状态信息用于调试
    logger.info(f"[路由决策] 当前状态键: {list(state.keys())}")
    logger.info(f"[路由决策] user_feedback 原始值: '{state.get('user_feedback', '')}'")
    logger.info(f"[路由决策] webpage_html 是否存在: {bool(state.get('webpage_html'))}")
    logger.info(f"[路由决策] deployment_url: {state.get('deployment_url', 'N/A')}")
    logger.info(f"[路由决策] generated_images 数量: {len(state.get('generated_images', []))}")
    
    user_feedback = state.get("user_feedback", "").strip().lower()
    logger.info(f"[路由决策] user_feedback 处理后值: '{user_feedback}'")

    # 1. 先检测图片修改请求（优先级提升，避免被"满意"等词误判）
    image_keywords = ["图片", "图", "picture", "image", "照片", "配图"]
    if any(keyword in user_feedback for keyword in image_keywords):
        logger.info("✓ 路由决策结果: 检测到图片修改请求 -> 'regenerate_single_image'")
        logger.info("=" * 80)
        return "regenerate_single_image"
    
    # 2. 检查用户是否明确表示同意
    # 特殊处理：先检查完整的同意短语（避免"没问题"被"没"误判）
    approve_phrases = ["没问题", "没意见", "没啥问题", "没什么问题"]
    if any(phrase in user_feedback for phrase in approve_phrases):
        logger.info("✓ 路由决策结果: 用户已同意网页（匹配到同意短语），流程结束 -> END")
        logger.info("=" * 80)
        return END
    
    # 再检查否定词（注意：已排除"没"，因为上面已经处理了"没问题"）
    negative_keywords = ["不", "别", "无", "非"]
    has_negative = any(neg in user_feedback for neg in negative_keywords)
    
    # 检查其他同意关键词
    approve_keywords = ["同意", "approve", "确认", "可以", "满意", "很好", "ok", "好的"]
    has_approve = any(keyword in user_feedback for keyword in approve_keywords)
    
    if has_approve and not has_negative:
        logger.info("✓ 路由决策结果: 用户已同意网页，流程结束 -> END")
        logger.info("=" * 80)
        return END
    
    if has_approve and has_negative:
        logger.info("⚠ 检测到同意关键词，但同时存在否定词，判定为修改意见")
        # 继续往下，走到"其他修改意见"的逻辑
    
    # 3. 任何其他非空反馈都视为网页修改意见
    if user_feedback:
        logger.info("✓ 路由决策结果: 用户提出网页修改意见 -> 'generate_webpage'")
        logger.info("=" * 80)
        return "generate_webpage"
        
    # 4. 如果反馈为空：这通常发生在首次部署后、用户尚未提供反馈时。
    logger.info("ℹ 路由决策结果: user_feedback 为空（首次部署或中断恢复），默认 -> 'generate_webpage'")
    logger.info("  （这是正常的行为，用户反馈后会从中断点继续执行）")
    logger.info("=" * 80)
    return "generate_webpage"

# 初始化图
workflow = StateGraph(CourseGenerationState)

# 添加节点
workflow.add_node("load_framework", load_framework)
workflow.add_node("generate_initial_draft", generate_initial_draft)
workflow.add_node("revise_draft", revise_draft)
workflow.add_node("finalize_content", finalize_content)
# v2.0 新增：图片生成节点
workflow.add_node("analyze_image_needs", analyze_image_needs)
workflow.add_node("generate_images", generate_images)
workflow.add_node("regenerate_single_image", regenerate_single_image)
workflow.add_node("generate_webpage", generate_webpage)
workflow.add_node("deploy_webpage_node", deploy_webpage_node)

# 设置图的入口点
workflow.set_entry_point("load_framework")

# 定义边的连接
workflow.add_edge("load_framework", "generate_initial_draft")

# 定义课程内容审核的条件边
workflow.add_conditional_edges(
    "generate_initial_draft",
    route_content_feedback,
    {
        "finalize_content": "finalize_content",
        "revise_draft": "revise_draft"
    }
)
workflow.add_conditional_edges(
    "revise_draft",
    route_content_feedback,
    {
        "finalize_content": "finalize_content",
        "revise_draft": "revise_draft"
    }
)

# v2.0 更新：课程内容确认后，先进行图片生成
workflow.add_edge("finalize_content", "analyze_image_needs")
workflow.add_edge("analyze_image_needs", "generate_images")
workflow.add_edge("generate_images", "generate_webpage")

# 网页生成后，自动部署
workflow.add_edge("generate_webpage", "deploy_webpage_node")

# v2.0 更新：定义网页审核的条件边（支持图片修改）
workflow.add_conditional_edges(
    "deploy_webpage_node",
    route_webpage_feedback,
    {
        "generate_webpage": "generate_webpage",
        "regenerate_single_image": "regenerate_single_image",
        END: END
    }
)

# v2.0 新增：图片重新生成后 -> 重新生成网页 -> 重新部署
workflow.add_edge("regenerate_single_image", "generate_webpage")

# 编译图
# 我们告诉图，在执行完这些节点后，应该暂停并等待外部输入。
# 中断点包括：课程初稿生成后、课程修改后、网页部署后
logger.info("\n" + "=" * 80)
logger.info("正在编译 LangGraph 工作流...")
logger.info(f"配置的中断点 (interrupt_after): ['generate_initial_draft', 'revise_draft', 'deploy_webpage_node']")
logger.info(f"入口点 (entry_point): 'load_framework'")
logger.info("=" * 80)

app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_after=["generate_initial_draft", "revise_draft", "deploy_webpage_node"]
)

logger.info("LangGraph 工作流编译成功！")
logger.info("=" * 80)
