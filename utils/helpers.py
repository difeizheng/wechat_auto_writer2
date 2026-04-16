"""
辅助函数
提供常用的辅助功能
"""


def format_datetime(dt) -> str:
    """格式化日期时间"""
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def truncate_text(text: str, max_length: int = 100) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def count_words(text: str) -> int:
    """统计字数（中英文混合）"""
    import re
    # 中文字符
    chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 英文单词
    english = len(re.findall(r'[a-zA-Z]+', text))
    return chinese + english