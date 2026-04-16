"""
数据库模块
提供数据模型和数据库管理功能
"""

from database.models import (
    Article,
    Template,
    ConfigItem,
    ArticleStatus,
    TemplateCategory
)

from database.db_manager import (
    DatabaseManager,
    DatabaseError,
    get_db_manager,
    reset_db_manager
)

# 导出的类和函数
__all__ = [
    # 数据模型
    "Article",
    "Template",
    "ConfigItem",
    "ArticleStatus",
    "TemplateCategory",
    
    # 数据库管理
    "DatabaseManager",
    "DatabaseError",
    "get_db_manager",
    "reset_db_manager"
]