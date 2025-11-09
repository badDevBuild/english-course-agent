import requests
import os
from datetime import datetime
from pathlib import Path
from typing import Dict
import logging

FRAMEWORK_PATH = "curriculum/framework.md"

logger = logging.getLogger(__name__)

def load_curriculum_framework() -> str:
    """
    从本地文件加载课程设计框架。

    Returns:
        str: 课程框架的文本内容。
    """
    try:
        with open(FRAMEWORK_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "错误：未找到课程框架文件。"
    except Exception as e:
        return f"错误：读取文件时发生未知错误: {e}"

def deploy_webpage(html_content: str) -> str:
    """
    将生成的 HTML 内容部署到本地文件系统。

    Args:
        html_content (str): 要部署的网页 HTML 内容。

    Returns:
        str: 部署后的可访问 URL（本地 file:// 路径），或错误信息。
    """
    import os
    from datetime import datetime
    
    # 创建部署目录（在项目根目录下）
    # 获取当前文件所在目录的父目录（即项目根目录）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    deploy_dir = os.path.join(project_root, "deployed_lessons")
    
    # 确保部署目录存在
    os.makedirs(deploy_dir, exist_ok=True)
    
    # 生成唯一的文件名（使用时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lesson_{timestamp}.html"
    filepath = os.path.join(deploy_dir, filename)
    
    # 写入 HTML 文件
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 返回本地访问路径
        abs_path = os.path.abspath(filepath)
        file_url = f"file://{abs_path}"
        
        print(f"✓ 网页已成功部署到: {abs_path}")
        print(f"✓ 访问链接: {file_url}")
        
        return file_url
        
    except Exception as e:
        error_msg = f"部署失败: {str(e)}"
        print(f"✗ {error_msg}")
        return error_msg


def generate_image_with_gemini(prompt: str, image_id: str, lesson_id: str, aspect_ratio: str = "1:1") -> Dict:
    """
    使用 Gemini 2.5 Flash Image API 生成图片。
    
    Args:
        prompt (str): 英文图片生成 prompt
        image_id (str): 图片唯一标识，如 "word_dolphin"
        lesson_id (str): 课程标识（用于目录组织）
        aspect_ratio (str): 图片比例，默认 "1:1"，可选 "3:2", "16:9" 等
        
    Returns:
        Dict: 包含以下键的字典
            - success (bool): 是否成功
            - file_path (str): 相对路径（用于 HTML）
            - absolute_path (str): 绝对路径
            - error (str): 错误信息（如果失败）
    """
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        from io import BytesIO
        
        # 初始化客户端
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "未找到 GOOGLE_API_KEY 环境变量"
            }
        
        client = genai.Client(api_key=api_key)
        
        # 为儿童学习优化 prompt
        enhanced_prompt = f"{prompt}. Child-friendly, bright colors, cartoon style, educational illustration."
        
        logger.info(f"正在生成图片: {image_id}")
        logger.debug(f"Prompt: {enhanced_prompt}")
        
        # 调用 API 生成图片
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[enhanced_prompt],
            config=types.GenerateContentConfig(
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio
                )
            )
        )
        
        # 创建目录结构
        # deployed_lessons/images/lesson_YYYYMMDD_HHMMSS/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        image_dir = Path(project_root) / "deployed_lessons" / "images" / f"lesson_{lesson_id}"
        image_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存图片
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                file_name = f"{image_id}.png"
                absolute_path = image_dir / file_name
                image.save(absolute_path)
                
                # 返回相对路径（相对于 HTML 文件）
                relative_path = f"./images/lesson_{lesson_id}/{file_name}"
                
                logger.info(f"✓ 图片生成成功: {image_id} -> {absolute_path}")
                
                return {
                    "success": True,
                    "file_path": relative_path,
                    "absolute_path": str(absolute_path)
                }
        
        return {
            "success": False,
            "error": "API 响应中没有图片数据"
        }
        
    except ImportError as e:
        return {
            "success": False,
            "error": f"缺少依赖库: {str(e)}。请运行 pip install google-genai Pillow"
        }
    except Exception as e:
        logger.error(f"✗ 图片生成失败: {image_id} - {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
