"""
核心功能模块

包含AI生成引擎、微信API接口、模板管理等核心功能
"""

from .ai_writer import (
    AIWriter,
    AIProvider,
    OpenAIProvider,
    ClaudeProvider,
    OllamaProvider,
    create_ai_writer,
    get_default_prompt,
    AIWriterError,
    ModelNotAvailableError,
    APICallError,
    ResponseParseError
)

from .wechat_api import (
    WeChatAPI,
    WeChatAPIError,
    WeChatNetworkError,
    WeChatTokenExpiredError,
    TokenCache,
    create_wechat_api,
    ArticleData,
    DraftItem,
    APIResponse
)

__all__ = [
    # AI Writer 主类
    "AIWriter",
    
    # AI Provider类
    "AIProvider",
    "OpenAIProvider",
    "ClaudeProvider",
    "OllamaProvider",
    
    # AI Writer 工厂函数
    "create_ai_writer",
    "get_default_prompt",
    
    # AI Writer 异常类
    "AIWriterError",
    "ModelNotAvailableError",
    "APICallError",
    "ResponseParseError",
    
    # WeChat API 主类
    "WeChatAPI",
    
    # WeChat API 异常类
    "WeChatAPIError",
    "WeChatNetworkError",
    "WeChatTokenExpiredError",
    
    # WeChat API 缓存类
    "TokenCache",
    
    # WeChat API 工厂函数
    "create_wechat_api",
    
    # WeChat API 类型别名
    "ArticleData",
    "DraftItem",
    "APIResponse",
]