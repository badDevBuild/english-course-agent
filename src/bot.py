import logging
import os
import uuid
import asyncio

from dotenv import load_dotenv

# 必须在导入任何我们自己的模块（如 src.graph）之前首先加载环境变量
load_dotenv()

# --- LangSmith 配置 ---
# 为了实现可观察性，我们在此处配置 LangSmith
# 确保在 .env 文件中或下方直接设置了 LANGCHAIN_API_KEY
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
# 请注意：为了安全，建议将 API Key 存储在 .env 文件中，而不是硬编码在代码里
# 如果 .env 文件中没有设置，请在此处填入您的真实 Key
if not os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = "YOUR_LANGCHAIN_API_KEY_HERE" # <-- 请替换为您的真实 API Key
os.environ["LANGCHAIN_PROJECT"] = "English Course Designer" # 项目名称，可自定义


from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from src.graph import app
from src.storage import (initialize_user_sessions_db, get_thread_id,
                         save_thread_id, delete_thread_id)

# --- 初始化和配置 ---

# 加载 .env 文件中的环境变量
# load_dotenv() # <- 从这里移动到文件顶部

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)

# 检查必要的环境变量是否存在
if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("请确保 .env 文件中已配置 TELEGRAM_BOT_TOKEN 和 GOOGLE_API_KEY")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN").strip()

# ------------------------------------------------------------------
# 移除内存中的 user_threads 字典
# user_threads = {}
# ------------------------------------------------------------------


# --- Telegram Bot 处理器 ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /start 命令，启动一个新的课程设计流程。"""
    chat_id = update.effective_chat.id
    theme = " ".join(context.args)

    if not theme:
        await update.message.reply_text("欢迎使用！请使用 `/start <课程主题>` 的格式来开始一个新的课程设计。")
        return

    logger.info(f"收到来自 chat_id: {chat_id} 的新任务，主题: '{theme}'")
    await update.message.reply_text(f"好的，收到您的请求！正在围绕主题“{theme}”设计新的课程，请稍候...")

    # 为每个新流程创建一个唯一的 thread_id
    thread_id = str(uuid.uuid4())
    logger.info(f"为 chat_id: {chat_id} 创建了新的 thread_id: {thread_id}")
    # 将新的 thread_id 持久化存储
    save_thread_id(chat_id, thread_id)

    # 配置 LangGraph 实例以使用此 thread_id
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # 首次调用，传入主题来启动图
        logger.info("\n" + "#" * 80)
        logger.info(f"[BOT] 首次调用 graph.invoke")
        logger.info(f"[BOT] thread_id: {thread_id}")
        logger.info(f"[BOT] chat_id: {chat_id}")
        logger.info(f"[BOT] 输入: {{'theme': '{theme}'}}")
        logger.info(f"[BOT] config: {config}")
        logger.info("#" * 80)
        
        final_state = await asyncio.to_thread(app.invoke, {"theme": theme}, config=config)
        
        logger.info("\n" + "#" * 80)
        logger.info(f"[BOT] graph.invoke 调用返回")
        logger.info(f"[BOT] thread_id: {thread_id}")
        logger.info(f"[BOT] 返回状态键: {list(final_state.keys()) if final_state else 'None'}")
        logger.info(f"[BOT] lesson_draft 是否存在: {bool(final_state.get('lesson_draft'))}")
        logger.info(f"[BOT] theme: {final_state.get('theme', 'N/A')}")
        logger.info(f"[BOT] user_feedback: '{final_state.get('user_feedback', 'N/A')}'")
        logger.info("#" * 80)

        # 图执行直到第一个中断点（生成初稿后），然后返回状态
        draft = final_state.get("lesson_draft")
        if draft:
            response_message = (
                "课程初稿已生成！请您审核：\n\n"
                "```markdown\n"
                f"{draft}\n"
                "```\n\n"
                "如果您满意，请输入 **同意**。\n"
                "如果您有任何修改意见，请直接回复。"
            )
            await update.message.reply_text(response_message, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"[{thread_id}] 已向用户发送初稿以供审核。")
        else:
            logger.warning(f"[{thread_id}] 流程中断，但未在状态中找到 'lesson_draft'。")
            await update.message.reply_text("抱歉，生成课程初稿时遇到问题，请稍后重试。")

    except Exception as e:
        logger.error(f"处理 /start 命令时出错: {e}", exc_info=True)
        await update.message.reply_text("抱歉，处理您的请求时发生了内部错误。")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户的文本消息，作为对课程草稿的反馈。"""
    chat_id = update.effective_chat.id
    user_feedback = update.message.text
    logger.info(f"收到来自 chat_id: {chat_id} 的消息: '{user_feedback}'")

    # 检查用户是否已经有一个正在进行的流程
    thread_id = get_thread_id(chat_id)
    if not thread_id:
        logger.warning(f"chat_id: {chat_id} 发送了消息，但没有找到活跃的 thread_id。")
        await update.message.reply_text("请先使用 `/start <课程主题>` 开始一个新的课程设计。")
        return

    config = {"configurable": {"thread_id": thread_id}}

    await update.message.reply_text("正在处理您的反馈，请稍候...")

    try:
        # 正确的做法：先更新状态，再用 None 恢复执行
        logger.info("\n" + "#" * 80)
        logger.info(f"[BOT] 处理用户反馈")
        logger.info(f"[BOT] thread_id: {thread_id}")
        logger.info(f"[BOT] chat_id: {chat_id}")
        logger.info(f"[BOT] user_feedback: '{user_feedback}'")
        logger.info(f"[BOT] config: {config}")
        logger.info("#" * 80)
        
        # 步骤 1: 先更新状态中的 user_feedback
        logger.info(f"[BOT] 步骤 1: 更新状态中的 user_feedback")
        await asyncio.to_thread(
            app.update_state, config, {"user_feedback": user_feedback}
        )
        logger.info(f"[BOT] 状态更新完成")
        
        # 步骤 2: 用 None 作为输入来恢复图的执行（从中断点继续）
        logger.info(f"[BOT] 步骤 2: 用 None 恢复图的执行（从中断点继续）")
        final_state = await asyncio.to_thread(
            app.invoke, None, config=config
        )
        
        logger.info("\n" + "#" * 80)
        logger.info(f"[BOT] graph.invoke 调用返回 (处理用户反馈后)")
        logger.info(f"[BOT] thread_id: {thread_id}")
        logger.info(f"[BOT] 返回状态键: {list(final_state.keys()) if final_state else 'None'}")
        logger.info(f"[BOT] lesson_draft 是否存在: {bool(final_state.get('lesson_draft'))}")
        logger.info(f"[BOT] final_lesson_content 是否存在: {bool(final_state.get('final_lesson_content'))}")
        logger.info(f"[BOT] webpage_html 是否存在: {bool(final_state.get('webpage_html'))}")
        logger.info(f"[BOT] deployment_url 是否存在: {bool(final_state.get('deployment_url'))}")
        logger.info(f"[BOT] theme: {final_state.get('theme', 'N/A')}")
        logger.info(f"[BOT] user_feedback: '{final_state.get('user_feedback', 'N/A')}'")
        logger.info(f"[BOT] __end__ 是否存在: {'__end__' in final_state}")
        logger.info("#" * 80)
        
        # 检查是否完成网页部署
        if deployment_url := final_state.get("deployment_url"):
            # 检查流程是否真正到达 END（用户已批准网页）
            # 注意：不能只检查 user_feedback，因为 user_feedback 可能包含对课程内容的"同意"
            # 必须检查 __end__ 标志，这才表示流程真正结束
            if "__end__" in final_state:
                logger.info(f"流程 {thread_id} 已成功结束（到达 END 节点）。")
                response_message = (
                    "🎉 太棒了！整个流程已完成！\n\n"
                    f"您的英语课程网页已部署，可以通过以下链接访问：\n\n"
                    f"{deployment_url}\n\n"
                    "祝学习愉快！ 🌟"
                )
                await update.message.reply_text(response_message)
                logger.info(f"[{thread_id}] 流程结束，清理数据库会话。")
                delete_thread_id(chat_id)
                return
            
            # 否则，流程在 deploy_webpage_node 的中断点，需要用户审核网页
            else:
                logger.info(f"流程 {thread_id} 已完成网页部署，在中断点等待用户审核。")
                response_message = (
                    "✅ 网页已成功生成并部署！\n\n"
                    f"📱 访问链接：{deployment_url}\n\n"
                    "请点击链接查看网页效果。如果满意，请输入 **同意**；"
                    "如果需要调整（如字体大小、颜色等），请告诉我您的要求。"
                )
                await update.message.reply_text(response_message)
                logger.info(f"[{thread_id}] 已向用户发送部署链接以供审核。")
                return

        # 如果流程在修改草稿后再次中断
        if draft := final_state.get("lesson_draft"):
            response_message = (
                "📝 草稿已根据您的意见更新！请审核新版本：\n\n"
                "```markdown\n"
                f"{draft}\n"
                "```\n\n"
                "如果满意，请输入 **同意**，或继续提出修改意见。"
            )
            await update.message.reply_text(response_message, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"[{thread_id}] 已向用户发送修订后的草稿以供审核。")
        else:
            # 捕获其他可能的中间状态或意外情况
            logger.warning(f"[{thread_id}] 流程中断，但未在状态中找到预期的字段。")
            await update.message.reply_text("已收到您的反馈。流程正在继续...")


    except Exception as e:
        logger.error(f"处理用户消息时出错: {e}", exc_info=True)
        await update.message.reply_text("抱歉，处理您的反馈时发生了内部错误。")


def main() -> None:
    """启动 Telegram Bot。"""
    
    # 在启动 Bot 之前，先初始化数据库表
    initialize_user_sessions_db()
    
    logger.info("Bot 启动中...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 添加命令和消息处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 启动 Bot
    application.run_polling()
    logger.info("Bot 已停止。")


if __name__ == "__main__":
    main()
