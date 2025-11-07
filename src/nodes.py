import os
import logging
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from .state import CourseGenerationState
from .tools import load_curriculum_framework

# --- 日志配置 ---
logger = logging.getLogger(__name__)

# --- 模型和 Prompt 配置 ---

# 初始化 LLM
# 我们需要从环境变量中显式加载 API Key 并传递给模型
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("未找到 GOOGLE_API_KEY。请确保您的 .env 文件中已正确设置。")

logger.info("--- 正在初始化 Google Generative AI 模型 ---")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.7,
    # 对密钥进行 strip 操作，去除可能存在的首尾空格或换行符
    google_api_key=google_api_key.strip(),
    # 设置请求超时，防止因网络问题导致程序无限期等待
    client_options={"api_endpoint": "generativelanguage.googleapis.com"},
    transport="rest",
    request_timeout=120,
)
logger.info("--- Google Generative AI 模型初始化成功 (已设置 120 秒超时) ---")

class LessonDraft(BaseModel):
    """用于结构化输出的模型，确保课程草稿是格式良好的 Markdown。"""
    draft_content: str = Field(description="完整的课程草稿内容，必须是 Markdown 格式。")

# 将 LLM 绑定到结构化输出工具
structured_llm = llm.with_structured_output(LessonDraft)

# 生成初稿的 Prompt 模板
GENERATE_DRAFT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一位顶级的儿童英语课程设计师。
你的任务是根据用户提供的主题和固定的课程框架，设计一堂生动有趣、内容翔实的英语课。
你需要严格遵循框架的结构，并确保内容适合儿童学习。
最终的输出必须是结构清晰、内容完整的 Markdown 文档。"""),
    ("human", """这是课程设计框架:
---
{curriculum_framework}
---

请围绕 `{theme}` 这个主题，为我生成一份详细的课程草稿。""")
])

# 修改草稿的 Prompt 模板
REVISE_DRAFT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一位善于听取反馈的课程设计师。
你的任务是根据用户提出的修改意见，对现有的课程草稿进行调整。
你需要仔细阅读用户的反馈，并对草稿的相应部分做出精确、合理的修改。
最终的输出仍然必须是结构清晰、内容完整的 Markdown 文档。"""),
    ("human", """这是当前的课程草稿:
---
{lesson_draft}
---

这是我的修改意见:
---
{user_feedback}
---

请根据我的意见修改课程草稿，并返回完整的、修改后的版本。""")
])

# 将 Prompt 模板与 LLM 链式组合
generate_draft_chain = GENERATE_DRAFT_PROMPT | structured_llm
revise_draft_chain = REVISE_DRAFT_PROMPT | structured_llm


# --- 节点函数 ---

def load_framework(state: CourseGenerationState) -> dict:
    """
    加载课程框架。

    Args:
        state (CourseGenerationState): 当前的图状态。

    Returns:
        dict: 包含课程框架的状态字典。
    """
    logger.info("\n" + "=" * 80)
    logger.info(">>> 进入节点: load_framework (加载课程框架)")
    logger.info("=" * 80)
    logger.info(f"[load_framework] 输入状态键: {list(state.keys())}")
    logger.info(f"[load_framework] theme: {state.get('theme', 'N/A')}")
    logger.info(f"[load_framework] user_feedback: '{state.get('user_feedback', 'N/A')}'")
    
    framework_content = load_curriculum_framework()
    logger.info(f"[load_framework] 成功加载了 {len(framework_content)} 个字符的课程框架。")
    result = {"curriculum_framework": framework_content}
    
    logger.info(f"[load_framework] 返回结果键: {list(result.keys())}")
    logger.info("<<< 退出节点: load_framework")
    logger.info("=" * 80)
    return result

def generate_initial_draft(state: CourseGenerationState) -> dict:
    """
    调用 LLM 生成第一版课程草稿。

    Args:
        state (CourseGenerationState): 当前的图状态。

    Returns:
        dict: 包含新生成的课程草稿的状态字典。
    """
    logger.info("\n" + "=" * 80)
    logger.info(">>> 进入节点: generate_initial_draft (生成课程初稿)")
    logger.info("=" * 80)
    logger.info(f"[generate_initial_draft] 输入状态键: {list(state.keys())}")
    logger.info(f"[generate_initial_draft] theme: {state.get('theme', 'N/A')}")
    logger.info(f"[generate_initial_draft] user_feedback: '{state.get('user_feedback', 'N/A')}'")
    logger.info(f"[generate_initial_draft] curriculum_framework 是否存在: {bool(state.get('curriculum_framework'))}")
    logger.info(f"[generate_initial_draft] lesson_draft 是否已存在: {bool(state.get('lesson_draft'))}")
    logger.info(f"[generate_initial_draft] 正在使用主题 '{state['theme']}' 调用 LLM 生成初稿...")
    # logger.debug(f"完整 Prompt:\n{GENERATE_DRAFT_PROMPT.format(curriculum_framework=state['curriculum_framework'], theme=state['theme'])}")

    try:
        response = generate_draft_chain.invoke({
            "curriculum_framework": state["curriculum_framework"],
            "theme": state["theme"]
        })
    except Exception as e:
        logger.error(f"调用 LLM (generate_initial_draft) 时发生严重错误: {e}", exc_info=True)
        # 返回一个包含错误信息的内容，以防止图流程中断
        return {"lesson_draft": "错误：调用 LLM 生成课程时失败。请查看日志了解详情。"}

    logger.info(f"[generate_initial_draft] LLM 调用成功，返回了 {len(response.draft_content)} 个字符的草稿。")
    result = {"lesson_draft": response.draft_content}
    
    logger.info(f"[generate_initial_draft] 返回结果键: {list(result.keys())}")
    logger.info("<<< 退出节点: generate_initial_draft")
    logger.info("=" * 80)
    return result

def revise_draft(state: CourseGenerationState) -> dict:
    """
    根据用户反馈调用 LLM 修改课程草稿。

    Args:
        state (CourseGenerationState): 当前的图状态。

    Returns:
        dict: 包含修改后课程草稿的状态字典。
    """
    logger.info("\n" + "=" * 80)
    logger.info(">>> 进入节点: revise_draft (根据反馈修改草稿)")
    logger.info("=" * 80)
    logger.info(f"[revise_draft] 输入状态键: {list(state.keys())}")
    logger.info(f"[revise_draft] theme: {state.get('theme', 'N/A')}")
    logger.info(f"[revise_draft] user_feedback: '{state.get('user_feedback', 'N/A')}'")
    logger.info(f"[revise_draft] lesson_draft 是否存在: {bool(state.get('lesson_draft'))}")
    logger.info(f"[revise_draft] lesson_draft 长度: {len(state.get('lesson_draft', ''))}")
    logger.info(f"[revise_draft] 收到用户反馈: '{state['user_feedback']}'")
    logger.info(f"[revise_draft] 正在调用 LLM 修改草稿...")
    # logger.debug(f"完整 Prompt:\n{REVISE_DRAFT_PROMPT.format(lesson_draft=state['lesson_draft'], user_feedback=state['user_feedback'])}")
    
    try:
        response = revise_draft_chain.invoke({
            "lesson_draft": state["lesson_draft"],
            "user_feedback": state["user_feedback"]
        })
    except Exception as e:
        logger.error(f"调用 LLM (revise_draft) 时发生严重错误: {e}", exc_info=True)
        return {"lesson_draft": "错误：调用 LLM 修改课程时失败。请查看日志了解详情。"}
        
    logger.info(f"[revise_draft] LLM 调用成功，返回了 {len(response.draft_content)} 个字符的新草稿。")
    result = {"lesson_draft": response.draft_content}
    
    logger.info(f"[revise_draft] 返回结果键: {list(result.keys())}")
    logger.info("<<< 退出节点: revise_draft")
    logger.info("=" * 80)
    return result

def finalize_content(state: CourseGenerationState) -> dict:
    """
    最终确定课程内容。

    Args:
        state (CourseGenerationState): 当前的图状态。

    Returns:
        dict: 包含最终课程内容的状态字典。
    """
    logger.info("\n" + "=" * 80)
    logger.info(">>> 进入节点: finalize_content (最终确定课程内容)")
    logger.info("=" * 80)
    logger.info(f"[finalize_content] 输入状态键: {list(state.keys())}")
    logger.info(f"[finalize_content] theme: {state.get('theme', 'N/A')}")
    logger.info(f"[finalize_content] user_feedback: '{state.get('user_feedback', 'N/A')}'")
    logger.info(f"[finalize_content] lesson_draft 长度: {len(state.get('lesson_draft', ''))}")
    
    final_content = state["lesson_draft"]
    logger.info(f"[finalize_content] 已将 {len(final_content)} 个字符的草稿内容最终确定。")
    result = {"final_lesson_content": final_content}
    
    logger.info(f"[finalize_content] 返回结果键: {list(result.keys())}")
    logger.info("<<< 退出节点: finalize_content")
    logger.info("=" * 80)
    return result

def generate_webpage(state: CourseGenerationState) -> dict:
    """
    根据最终确认的课程内容生成 HTML 网页。
    
    如果用户提供了修改反馈，则在生成时考虑这些反馈。
    同时将原始课程内容一并发送给 LLM，以便其理解内容结构并做出合适的调整。

    Args:
        state (CourseGenerationState): 当前的图状态。

    Returns:
        dict: 包含生成的 HTML 网页代码的状态字典。
    """
    logger.info("\n" + "=" * 80)
    logger.info(">>> 进入节点: generate_webpage (生成网页)")
    logger.info("=" * 80)
    logger.info(f"[generate_webpage] 输入状态键: {list(state.keys())}")
    logger.info(f"[generate_webpage] final_lesson_content 长度: {len(state.get('final_lesson_content', ''))}")
    logger.info(f"[generate_webpage] user_feedback: '{state.get('user_feedback', 'N/A')}'")
    logger.info(f"[generate_webpage] webpage_html 是否已存在: {bool(state.get('webpage_html'))}")
    logger.info(f"[generate_webpage] webpage_html 长度: {len(state.get('webpage_html', ''))}")
    
    final_content = state["final_lesson_content"]
    user_feedback = state.get("user_feedback", "").strip()
    current_html = state.get("webpage_html", "").strip()
    
    # 构建系统提示
    system_prompt = """你是一个专业的前端开发专家和儿童教育专家。

你的任务是将英语课程内容转换为一个精美的、适合儿童学习的 HTML 网页。

**技术要求**：
1. 生成一个完整的、可独立运行的 HTML5 文件
2. 使用内嵌 CSS，采用温暖、柔和的配色方案（如浅蓝#E3F2FD、淡黄#FFF9C4、柔和的绿色#C8E6C9）
3. 字体大小适合儿童阅读（正文至少 18px，标题更大）
4. 响应式设计，同时适配手机和电脑（使用 media query）
5. 为英文单词添加点击发音功能（使用 Web Speech API）
6. 使用语义化 HTML5 标签（header, main, section, article 等）
7. 添加适当的 padding 和 margin，避免内容拥挤
8. 字体使用系统默认的易读字体（如 -apple-system, sans-serif）

**发音功能实现**：
- 为所有英文单词或短语添加 <span class="pronounce" data-text="单词">单词</span> 标签
- 在 JavaScript 中实现点击发音功能
- 给可发音的单词添加视觉提示（如下划线、鼠标悬停效果）

**样式指南**：
- 使用圆角、阴影等现代设计元素
- 适当的行高（line-height: 1.6-1.8）
- 清晰的标题层级
- 使用卡片式布局展示不同的课程模块

**重要**：只输出完整的 HTML 代码，不要有任何额外的解释或说明。"""

    # 构建用户提示
    if user_feedback and current_html:
        # 如果有反馈且已有网页，说明这是修改网页
        logger.info(f"[generate_webpage] 检测到这是修改网页的请求，将提供当前 HTML（长度: {len(current_html)}）")
        user_prompt = f"""请根据以下要求修改网页：

用户的修改要求：
{user_feedback}

当前的网页 HTML 代码：
---
{current_html}
---

原始课程内容（供参考）：
---
{final_content}
---

请基于当前的 HTML，根据用户的要求进行精确修改，并生成完整的修改后的 HTML 代码。"""
    else:
        # 首次生成网页
        logger.info(f"[generate_webpage] 这是首次生成网页")
        user_prompt = f"""请将以下英语课程内容转换为一个精美的 HTML 网页：

课程内容：
---
{final_content}
---

请生成完整的 HTML 代码。"""

    logger.info(f"[generate_webpage] 正在调用 LLM 生成网页...")
    
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        html_content = _extract_html_from_response(response.content)
        
        logger.info(f"[generate_webpage] LLM 调用成功，生成了 {len(html_content)} 个字符的 HTML 代码。")
        
        result = {"webpage_html": html_content}
        
    except Exception as e:
        logger.error(f"调用 LLM (generate_webpage) 时发生严重错误: {e}", exc_info=True)
        result = {"webpage_html": "<html><body><h1>错误：生成网页失败</h1><p>请查看日志了解详情。</p></body></html>"}
    
    logger.info(f"[generate_webpage] 返回结果键: {list(result.keys())}")
    logger.info("<<< 退出节点: generate_webpage")
    logger.info("=" * 80)
    return result

def deploy_webpage_node(state: CourseGenerationState) -> dict:
    """
    将生成的网页部署到服务器（或本地文件系统）。

    Args:
        state (CourseGenerationState): 当前的图状态。

    Returns:
        dict: 包含部署后访问链接的状态字典。
    """
    logger.info("\n" + "=" * 80)
    logger.info(">>> 进入节点: deploy_webpage_node (部署网页)")
    logger.info("=" * 80)
    logger.info(f"[deploy_webpage_node] 输入状态键: {list(state.keys())}")
    logger.info(f"[deploy_webpage_node] webpage_html 长度: {len(state.get('webpage_html', ''))}")
    
    html_content = state["webpage_html"]
    
    try:
        from .tools import deploy_webpage
        
        logger.info(f"[deploy_webpage_node] 正在调用部署工具...")
        deployment_url = deploy_webpage(html_content)
        logger.info(f"[deploy_webpage_node] 部署成功！访问链接: {deployment_url}")
        
        result = {"deployment_url": deployment_url}
        
    except Exception as e:
        logger.error(f"部署网页时发生错误: {e}", exc_info=True)
        result = {"deployment_url": f"错误：部署失败 - {str(e)}"}
    
    logger.info(f"[deploy_webpage_node] 返回结果键: {list(result.keys())}")
    logger.info("<<< 退出节点: deploy_webpage_node")
    logger.info("=" * 80)
    return result

# --- 辅助函数 ---

def _extract_html_from_response(response_text: str) -> str:
    """
    从 LLM 响应中提取 HTML 代码。
    
    LLM 可能会在代码块中返回 HTML，需要提取出纯代码。

    Args:
        response_text (str): LLM 的原始响应文本。

    Returns:
        str: 提取出的 HTML 代码。
    """
    import re
    
    # 尝试提取 ```html ... ``` 或 ``` ... ``` 代码块
    pattern = r'```(?:html)?\s*\n(.*?)\n```'
    matches = re.findall(pattern, response_text, re.DOTALL)
    
    if matches:
        logger.info("[_extract_html_from_response] 从代码块中提取了 HTML。")
        return matches[0].strip()
    
    # 如果没有代码块，检查是否有 HTML 标签
    if '<!DOCTYPE html>' in response_text or '<html' in response_text:
        logger.info("[_extract_html_from_response] 直接返回响应文本（包含 HTML 标签）。")
        return response_text.strip()
    
    # 否则返回原文
    logger.warning("[_extract_html_from_response] 未能识别出标准的 HTML 格式，返回原始响应。")
    return response_text.strip()
