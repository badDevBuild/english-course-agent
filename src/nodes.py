import os
import logging
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from .state import CourseGenerationState, ImageRequirement, GeneratedImage
from .tools import load_curriculum_framework, generate_image_with_gemini
from datetime import datetime
from typing import Dict, List
import json
import re

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
    logger.info(f"[generate_webpage] generated_images 数量: {len(state.get('generated_images', []))}")
    
    final_content = state["final_lesson_content"]
    user_feedback = state.get("user_feedback", "").strip()
    current_html = state.get("webpage_html", "").strip()
    generated_images = state.get("generated_images", [])
    
    # 构建图片信息字符串
    images_info = ""
    if generated_images:
        images_info = "\n\n【可用图片资源 - 必须严格使用以下路径】：\n"
        for img in generated_images:
            images_info += f"\n图片 {img['id']}:\n"
            images_info += f"  - 文件路径: {img['file_path']}\n"
            images_info += f"  - 描述文本: {img['alt_text']}\n"
            images_info += f"  - HTML代码: <img src=\"{img['file_path']}\" alt=\"{img['alt_text']}\" style=\"border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);\">\n"
        images_info += "\n**重要**：以上路径是本地相对路径，请原样使用，不要替换为在线链接。\n"
        logger.info(f"[generate_webpage] 将使用 {len(generated_images)} 张图片")
    
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

**图片集成（v2.0 新增）**：
- 如果提供了图片资源，必须在 HTML 中使用 <img> 标签引用
- **关键要求**：必须严格使用我提供的本地图片路径（相对路径），绝对不允许使用互联网上的在线链接或自己生成的路径
- 图片路径格式示例：./images/lesson_xxx/word_dolphin.png
- 必须为每个图片添加 alt 属性（使用提供的描述）
- 单词图片：显示在单词卡片中，左侧图片（150-200px），右侧文字和发音按钮
- 句子图片：显示在句子上方或左侧（400-600px宽），作为场景配图
- 图片样式：圆角（border-radius: 12px）、阴影（box-shadow）、适当的 margin
- **再次强调**：所有 <img src="..."> 中的路径必须完全一致地使用我提供的路径，不要修改或替换

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
        
        # 检查是否是图片修改（图片路径可能已更新）
        is_image_modification = any(keyword in user_feedback.lower() for keyword in ["图片", "图", "picture", "image"])
        
        if is_image_modification and generated_images:
            # 图片修改场景：强调图片路径已更新
            user_prompt = f"""请根据以下要求修改网页：

用户的修改要求：
{user_feedback}

**重要提示**：以下是最新的图片资源和路径，这些图片已经重新生成。
请在修改 HTML 时，将对应图片的 src 属性更新为下面列表中的路径。
{images_info}

当前的网页 HTML 代码：
---
{current_html}
---

原始课程内容（供参考）：
---
{final_content}
---

**关键要求**：
1. 找到 HTML 中需要更新的图片（根据用户反馈和图片 ID）
2. 将这些图片的 src 属性更新为上面"可用图片资源"列表中提供的路径
3. 必须使用完整的相对路径，不要使用在线链接
4. 保持 HTML 的其他部分不变（除非用户明确要求修改）

请生成完整的修改后的 HTML 代码。"""
        else:
            # 普通修改场景
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
{images_info}

请基于当前的 HTML，根据用户的要求进行精确修改，并生成完整的修改后的 HTML 代码。"""
    else:
        # 首次生成网页
        logger.info(f"[generate_webpage] 这是首次生成网页")
        user_prompt = f"""请将以下英语课程内容转换为一个精美的 HTML 网页：

课程内容：
---
{final_content}
---
{images_info}

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
        
        # 验证图片路径（v2.0 新增）
        if generated_images:
            import re
            # 检查是否包含在线链接
            online_image_pattern = r'<img[^>]+src=["\'](https?://[^"\']+)["\']'
            online_images = re.findall(online_image_pattern, html_content)
            
            if online_images:
                logger.warning(f"[generate_webpage] ⚠️ 警告：检测到 {len(online_images)} 个在线图片链接，这可能不是预期的！")
                logger.warning(f"[generate_webpage] 在线链接列表: {online_images[:3]}")  # 只显示前3个
                logger.warning(f"[generate_webpage] 应该使用的本地路径: {[img['file_path'] for img in generated_images]}")
            
            # 检查是否使用了提供的本地路径
            local_paths_used = []
            for img in generated_images:
                if img['file_path'] in html_content:
                    local_paths_used.append(img['id'])
            
            logger.info(f"[generate_webpage] ✓ 已使用的本地图片: {local_paths_used} ({len(local_paths_used)}/{len(generated_images)})")
            
            if len(local_paths_used) < len(generated_images):
                missing = [img['id'] for img in generated_images if img['id'] not in local_paths_used]
                logger.warning(f"[generate_webpage] ⚠️ 警告：以下图片路径未在 HTML 中找到: {missing}")
        
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


# ============================================================================
# 图片生成相关节点 (v2.0 新增)
# ============================================================================

def analyze_image_needs(state: CourseGenerationState) -> Dict:
    """
    分析课程内容，确定需要哪些图片。
    
    提取：
    1. 所有学习单词
    2. 所有学习句子
    并为每个生成图片描述和英文 prompt。
    
    Args:
        state (CourseGenerationState): 当前状态
        
    Returns:
        Dict: 包含 image_requirements 和 lesson_id 的字典
    """
    logger.info("[analyze_image_needs] 开始分析图片需求...")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        request_timeout=120,
        google_api_key=google_api_key
    )
    
    prompt = f"""
你是一个儿童英语教学专家。请分析以下课程内容，提取需要配图的元素。

课程内容：
{state["final_lesson_content"]}

请按以下 JSON 格式返回（只返回 JSON，不要其他文字）：
{{
  "words": [
    {{
      "word": "dolphin",
      "chinese": "海豚",
      "image_prompt": "A friendly cartoon dolphin swimming in clear blue ocean water, bright colors, educational illustration for children"
    }}
  ],
  "sentences": [
    {{
      "sentence": "The dolphin swims in the ocean",
      "chinese": "海豚在海洋中游泳",
      "image_prompt": "A cheerful dolphin swimming gracefully in the ocean, with sunlight streaming through the water, colorful fish around, cartoon style for kids"
    }}
  ]
}}

注意：
1. 提取课程中明确标注为"学习单词"或"词汇"或"重点单词"的所有单词
2. 提取课程中的例句或对话中的关键句子（2-3个即可，选择最有代表性的）
3. 每个 image_prompt 都应该是详细的英文描述，适合生成儿童友好的插画
4. 确保 prompt 包含 "cartoon style", "bright colors", "educational", "for children" 等关键词
5. prompt 要具体描述场景、颜色、氛围，避免抽象描述
"""
    
    try:
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        
        # 解析 LLM 返回的 JSON
        content = response.content
        logger.debug(f"[analyze_image_needs] LLM 响应: {content[:200]}...")
        
        # 提取 JSON 内容
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            parsed = json.loads(content)
        
        # 构建 ImageRequirement 列表
        requirements = []
        
        for word_item in parsed.get("words", []):
            requirements.append(ImageRequirement(
                id=f"word_{word_item['word'].lower().replace(' ', '_')}",
                type="word",
                content=word_item["word"],
                description=word_item["chinese"],
                prompt_en=word_item["image_prompt"]
            ))
        
        for idx, sent_item in enumerate(parsed.get("sentences", []), 1):
            requirements.append(ImageRequirement(
                id=f"sentence_{idx}",
                type="sentence",
                content=sent_item["sentence"],
                description=sent_item["chinese"],
                prompt_en=sent_item["image_prompt"]
            ))
        
        lesson_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info(f"[analyze_image_needs] 分析完成，需要生成 {len(requirements)} 张图片")
        for req in requirements:
            logger.info(f"  - {req['id']}: {req['content']} ({req['description']})")
        
        return {
            "image_requirements": requirements,
            "lesson_id": lesson_id
        }
        
    except Exception as e:
        logger.error(f"[analyze_image_needs] 分析失败: {str(e)}")
        # 返回空列表，避免阻断流程
        return {
            "image_requirements": [],
            "lesson_id": datetime.now().strftime("%Y%m%d_%H%M%S")
        }


def generate_images(state: CourseGenerationState) -> Dict:
    """
    根据 image_requirements 批量生成图片。
    
    Args:
        state (CourseGenerationState): 当前状态
        
    Returns:
        Dict: 包含 generated_images 的字典
    """
    logger.info("[generate_images] 开始生成图片...")
    
    generated = []
    requirements = state.get("image_requirements", [])
    lesson_id = state.get("lesson_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
    
    if not requirements:
        logger.warning("[generate_images] 没有图片需求，跳过生成")
        return {"generated_images": []}
    
    total = len(requirements)
    logger.info(f"[generate_images] 共需生成 {total} 张图片")
    
    for idx, req in enumerate(requirements, 1):
        logger.info(f"[generate_images] 正在生成第 {idx}/{total} 张: {req['id']} - {req['content']}")
        
        try:
            # 根据类型选择合适的比例
            aspect_ratio = "3:2" if req["type"] == "sentence" else "1:1"
            
            result = generate_image_with_gemini(
                prompt=req["prompt_en"],
                image_id=req["id"],
                lesson_id=lesson_id,
                aspect_ratio=aspect_ratio
            )
            
            if result["success"]:
                generated.append(GeneratedImage(
                    id=req["id"],
                    file_path=result["file_path"],
                    absolute_path=result["absolute_path"],
                    alt_text=f"{req['content']} - {req['description']}"
                ))
                logger.info(f"  ✓ 成功生成: {req['id']}")
            else:
                logger.error(f"  ✗ 生成失败: {req['id']} - {result.get('error', '未知错误')}")
                
        except Exception as e:
            logger.error(f"  ✗ 生成异常: {req['id']} - {str(e)}")
            continue
    
    success_count = len(generated)
    logger.info(f"[generate_images] 图片生成完成: 成功 {success_count}/{total} 张")
    
    if success_count == 0:
        logger.warning("[generate_images] 所有图片生成失败，将继续使用无图片的网页")
    
    return {"generated_images": generated}


def regenerate_single_image(state: CourseGenerationState) -> Dict:
    """
    根据用户反馈，重新生成一张或多张图片。
    
    这个节点由条件路由调用，当用户反馈明确提到要修改某张图片时触发。
    支持批量修改多张图片。
    
    Args:
        state (CourseGenerationState): 当前状态
        
    Returns:
        Dict: 包含更新后的 generated_images 的字典
    """
    logger.info("[regenerate_single_image] 开始重新生成图片...")
    
    user_feedback = state.get("user_feedback", "")
    generated_images = state.get("generated_images", [])
    image_requirements = state.get("image_requirements", [])
    lesson_id = state.get("lesson_id", "")
    
    if not user_feedback:
        logger.warning("[regenerate_single_image] 没有用户反馈，跳过")
        return {}
    
    if not generated_images:
        logger.warning("[regenerate_single_image] 没有已生成的图片，跳过")
        return {}
    
    # 使用 LLM 理解用户要修改哪张图片，以及如何修改
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        temperature=0.3,
        request_timeout=120,
        google_api_key=google_api_key
    )
    
    # 构建图片列表信息
    images_info = "\n".join([
        f"- ID: {img['id']}, 描述: {img['alt_text']}"
        for img in generated_images
    ])
    
    # 构建原始需求信息
    requirements_info = "\n".join([
        f"- ID: {req['id']}, 内容: {req['content']} ({req['description']}), 原始Prompt: {req['prompt_en']}"
        for req in image_requirements
    ])
    
    analysis_prompt = f"""
你是一个智能助手，需要分析用户对图片的修改要求。

用户反馈：
{user_feedback}

当前图片列表：
{images_info}

原始图片生成需求：
{requirements_info}

请分析：
1. 用户想要修改哪些图片？（返回对应的 id 数组，支持多张图片）
2. 对每张图片，用户希望如何修改？
3. 为每张图片生成新的英文 image prompt（在原 prompt 基础上融入用户的修改意见）

只返回 JSON 格式：
{{
  "modifications": [
    {{
      "target_image_id": "word_dolphin",
      "modification_summary": "改成红色背景",
      "new_prompt": "A friendly cartoon dolphin swimming in bright ocean water with red background, cheerful atmosphere, educational illustration for children"
    }},
    {{
      "target_image_id": "word_shark",
      "modification_summary": "改成红色背景",
      "new_prompt": "A friendly cartoon shark swimming in bright ocean water with red background, cheerful atmosphere, educational illustration for children"
    }}
  ]
}}

注意：
1. 用户可能要修改一张或多张图片，请根据反馈内容识别
2. 如果用户说"都"、"全部"、"所有"，可能指多张图片
3. 每个 new_prompt 必须是完整的英文描述，包含原有的风格要求
4. 如果无法识别任何目标图片，返回空数组
"""
    
    try:
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=analysis_prompt)])
        
        # 解析 LLM 返回的 JSON
        content = response.content
        logger.debug(f"[regenerate_single_image] LLM 响应: {content[:200]}...")
        
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            parsed = json.loads(content)
        
        modifications = parsed.get("modifications", [])
        
        if not modifications:
            logger.warning("[regenerate_single_image] 无法识别任何目标图片，跳过修改")
            return {}
        
        logger.info(f"[regenerate_single_image] 识别到 {len(modifications)} 张图片需要修改")
        
        # 批量处理每张图片
        updated_images = list(generated_images)  # 复制原列表
        success_count = 0
        
        for idx, mod in enumerate(modifications, 1):
            target_id = mod.get("target_image_id", "")
            new_prompt = mod.get("new_prompt", "")
            modification_summary = mod.get("modification_summary", "")
            
            if not target_id or not new_prompt:
                logger.warning(f"[regenerate_single_image] 第 {idx} 张图片信息不完整，跳过")
                continue
            
            # 标准化 ID 格式（小写，去除空格，下划线分隔）
            target_id = target_id.lower().strip().replace(" ", "_")
            
            logger.info(f"[regenerate_single_image] [{idx}/{len(modifications)}] 目标图片: {target_id}")
            logger.info(f"[regenerate_single_image] [{idx}/{len(modifications)}] 修改要求: {modification_summary}")
            logger.info(f"[regenerate_single_image] [{idx}/{len(modifications)}] 新 prompt: {new_prompt[:100]}...")
            
            # 找到原图的类型（word 或 sentence）
            target_req = next((r for r in image_requirements if r["id"] == target_id), None)
            if not target_req:
                logger.error(f"[regenerate_single_image] 找不到目标图片的原始需求: {target_id}")
                logger.error(f"[regenerate_single_image] 可用的 image_requirements: {[r['id'] for r in image_requirements]}")
                continue
            
            aspect_ratio = "3:2" if target_req["type"] == "sentence" else "1:1"
            
            # 生成新图片
            logger.info(f"[regenerate_single_image] [{idx}/{len(modifications)}] 开始调用 Gemini Image API...")
            logger.info(f"[regenerate_single_image] [{idx}/{len(modifications)}] 参数: image_id={target_id}, aspect_ratio={aspect_ratio}")
            
            result = generate_image_with_gemini(
                prompt=new_prompt,
                image_id=target_id,
                lesson_id=lesson_id,
                aspect_ratio=aspect_ratio
            )
            
            logger.info(f"[regenerate_single_image] [{idx}/{len(modifications)}] API 调用完成，结果: success={result.get('success', False)}")
            
            if result["success"]:
                # 更新 generated_images 列表中的对应图片
                for i, img in enumerate(updated_images):
                    if img["id"] == target_id:
                        # 替换为新生成的图片
                        updated_images[i] = GeneratedImage(
                            id=target_id,
                            file_path=result["file_path"],
                            absolute_path=result["absolute_path"],
                            alt_text=img["alt_text"]  # 保持原有的 alt 文本
                        )
                        logger.info(f"[regenerate_single_image] [{idx}/{len(modifications)}] ✓ 图片重新生成成功: {target_id}")
                        success_count += 1
                        break
            else:
                logger.error(f"[regenerate_single_image] [{idx}/{len(modifications)}] ✗ 图片重新生成失败: {result.get('error', '未知错误')}")
        
        if success_count > 0:
            logger.info(f"[regenerate_single_image] 总计成功重新生成 {success_count}/{len(modifications)} 张图片")
            return {"generated_images": updated_images}
        else:
            logger.error(f"[regenerate_single_image] 所有图片重新生成均失败")
            return {}
        
    except Exception as e:
        logger.error(f"[regenerate_single_image] 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}
