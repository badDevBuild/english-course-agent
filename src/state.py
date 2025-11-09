from typing import List, TypedDict, Annotated, Dict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ImageRequirement(TypedDict):
    """
    单个图片需求的定义。
    
    Attributes:
        id (str): 唯一标识，如 "word_dolphin", "sentence_1"
        type (str): "word" 或 "sentence"
        content (str): 单词或句子的英文原文
        description (str): 中文描述
        prompt_en (str): 英文图片生成 prompt
    """
    id: str
    type: str
    content: str
    description: str
    prompt_en: str


class GeneratedImage(TypedDict):
    """
    已生成的图片信息。
    
    Attributes:
        id (str): 对应 ImageRequirement 的 id
        file_path (str): HTML 中使用的相对路径
        absolute_path (str): 文件系统绝对路径
        alt_text (str): HTML alt 属性值
    """
    id: str
    file_path: str
    absolute_path: str
    alt_text: str


class CourseGenerationState(TypedDict):
    """
    定义了整个课程生成流程的状态。

    Attributes:
        theme (str): 今天的课程主题.
        user_feedback (str): 用户的反馈.
        curriculum_framework (str): 固定的课程框架内容.
        lesson_draft (str): 当前的课程草稿.
        final_lesson_content (str): 最终确认的课程内容.
        webpage_html (str): 生成的网页HTML代码.
        deployment_url (str): 部署后的访问链接.
        messages (Annotated[List[BaseMessage], add_messages]): 用于和LLM交互的消息历史.
        lesson_id (str): 课程唯一标识（时间戳）.
        image_requirements (List[ImageRequirement]): 图片需求列表.
        generated_images (List[GeneratedImage]): 已生成的图片列表.
    """
    # 输入信息
    theme: str
    user_feedback: str
    
    # 核心内容
    curriculum_framework: str
    lesson_draft: str
    final_lesson_content: str
    
    # 网页和部署
    webpage_html: str
    deployment_url: str
    
    # 图片相关（v2.0 新增）
    lesson_id: str
    image_requirements: List[ImageRequirement]
    generated_images: List[GeneratedImage]
    
    # 专门用于和LLM交互的消息历史
    messages: Annotated[List[BaseMessage], add_messages]
