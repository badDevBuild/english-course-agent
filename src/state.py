from typing import List, TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

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
    
    # 专门用于和LLM交互的消息历史
    messages: Annotated[List[BaseMessage], add_messages]
