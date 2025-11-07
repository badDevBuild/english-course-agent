import requests

FRAMEWORK_PATH = "curriculum/framework.md"

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
