"""
UI页面模块
导出所有页面组件函数
"""

# 导入所有页面模块
from ui.pages.article_gen import show_article_generation
from ui.pages.templates import show_template_management
from ui.pages.history import show_history
from ui.pages.settings import show_settings

# 导出所有页面函数
__all__ = [
    "show_article_generation",
    "show_template_management",
    "show_history",
    "show_settings",
]