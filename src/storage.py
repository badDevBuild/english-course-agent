import sqlite3
import logging

DB_PATH = "checkpoints.sqlite"

def initialize_user_sessions_db():
    """
    确保用于存储 chat_id 和 thread_id 映射的表存在。
    """
    try:
        # 使用 check_same_thread=False 是因为 bot 的不同处理器可能在不同线程中访问数据库
        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    chat_id INTEGER PRIMARY KEY,
                    thread_id TEXT NOT NULL
                )
            """)
            conn.commit()
            logging.info("成功初始化/验证 user_sessions 数据表。")
    except sqlite3.Error as e:
        logging.error(f"数据库初始化失败: {e}")
        raise

def get_thread_id(chat_id: int) -> str | None:
    """
    根据 chat_id 从数据库中检索 thread_id。

    Args:
        chat_id: 用户的 Telegram chat_id。

    Returns:
        如果找到，则返回 thread_id；否则返回 None。
    """
    try:
        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT thread_id FROM user_sessions WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"从数据库检索 thread_id 时出错: {e}")
        return None

def save_thread_id(chat_id: int, thread_id: str):
    """
    将 chat_id 和 thread_id 的映射关系保存或更新到数据库。

    Args:
        chat_id: 用户的 Telegram chat_id。
        thread_id: 与用户会话关联的 LangGraph thread_id。
    """
    try:
        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
            cursor = conn.cursor()
            # 使用 INSERT OR REPLACE 来处理插入新记录或更新现有记录的情况
            cursor.execute("""
                INSERT OR REPLACE INTO user_sessions (chat_id, thread_id)
                VALUES (?, ?)
            """, (chat_id, thread_id))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"向数据库保存 thread_id 时出错: {e}")

def delete_thread_id(chat_id: int):
    """
    当会话结束后，从数据库中删除 chat_id 的记录。

    Args:
        chat_id: 用户的 Telegram chat_id。
    """
    try:
        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_sessions WHERE chat_id = ?", (chat_id,))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"从数据库删除 thread_id 时出错: {e}")


