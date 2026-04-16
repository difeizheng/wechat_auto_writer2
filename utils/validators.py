"""
验证器
提供数据验证功能
"""
import re
from typing import Optional


def validate_url(url: str) -> bool:
    """验证URL格式"""
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(pattern.match(email))


def validate_not_empty(value: str, field_name: str = "字段") -> Optional[str]:
    """验证非空"""
    if not value or not value.strip():
        return f"{field_name}不能为空"
    return None


def validate_length(value: str, min_len: int, max_len: int, field_name: str = "字段") -> Optional[str]:
    """验证长度"""
    length = len(value)
    if length < min_len:
        return f"{field_name}长度不能少于{min_len}个字符"
    if length > max_len:
        return f"{field_name}长度不能超过{max_len}个字符"
    return None