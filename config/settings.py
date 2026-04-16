"""
配置管理模块
从 .env 文件或 Streamlit secrets 加载配置，提供统一的配置访问接口
"""
import os
import logging
from typing import Optional, List
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_streamlit_secret(key: str, default: str = "") -> str:
    """从 Streamlit secrets 获取配置值
    
    Args:
        key: 配置键名
        default: 默认值
        
    Returns:
        str: 配置值
    """
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default


class Settings:
    """应用配置管理
    
    负责从环境变量加载配置，提供统一的配置访问接口。
    支持多环境配置和必需配置验证。
    """
    
    # ==================== 配置属性 ====================
    
    # AI模型配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"  # OpenAI模型名称
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-3-haiku-20240307"  # Claude模型名称
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"  # Ollama模型名称
    
    # SiliconFlow配置（国内AI模型平台）
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"  # SiliconFlow模型名称
    
    DEFAULT_AI_MODEL: str = "openai"  # openai/claude/ollama/siliconflow
    
    # 微信公众号配置
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""
    
    # DingTalk 通知配置
    DINGTALK_WEBHOOK: str = ""
    DINGTALK_SECRET: str = ""  # 钉钉机器人签名密钥（加签方式）
    
    # 应用配置
    DATABASE_PATH: str = "data/wechat_writer.db"
    DEBUG_MODE: bool = False
    
    def __init__(self, env_file: Optional[str] = None):
        """初始化配置
        
        Args:
            env_file: 指定 .env 文件路径，默认自动查找
        """
        # 加载 .env 文件
        self._load_env_file(env_file)
        
        # 从环境变量加载配置
        self._load_from_env()
        
        # 验证必需配置
        self._validate_required()
    
    def _load_env_file(self, env_file: Optional[str] = None):
        """加载 .env 文件
        
        Args:
            env_file: 指定文件路径
        """
        if env_file:
            env_path = Path(env_file)
        else:
            # 查找 .env 文件的优先级：
            # 1. 当前工作目录
            # 2. config 目录
            # 3. 项目根目录
            possible_paths = [
                Path(".") / ".env",
                Path(__file__).parent / ".env",
                Path(__file__).parent.parent / ".env",
            ]
            
            env_path = None
            for path in possible_paths:
                if path.exists():
                    env_path = path
                    break
        
        if env_path and env_path.exists():
            load_dotenv(env_path, override=True)
    
    def _load_from_env(self):
        """从环境变量或 Streamlit secrets 加载配置
        
        优先级：Streamlit secrets > 环境变量 > 默认值
        """
        # AI模型配置
        self.OPENAI_API_KEY = _get_streamlit_secret("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_BASE_URL = _get_streamlit_secret("OPENAI_BASE_URL") or os.getenv(
            "OPENAI_BASE_URL", 
            "https://api.openai.com/v1"
        )
        self.OPENAI_MODEL = _get_streamlit_secret("OPENAI_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        self.CLAUDE_API_KEY = _get_streamlit_secret("CLAUDE_API_KEY") or os.getenv("CLAUDE_API_KEY", "")
        self.CLAUDE_MODEL = _get_streamlit_secret("CLAUDE_MODEL") or os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")
        
        self.OLLAMA_BASE_URL = _get_streamlit_secret("OLLAMA_BASE_URL") or os.getenv(
            "OLLAMA_BASE_URL", 
            "http://localhost:11434"
        )
        self.OLLAMA_MODEL = _get_streamlit_secret("OLLAMA_MODEL") or os.getenv("OLLAMA_MODEL", "llama3")
        
        # SiliconFlow配置
        self.SILICONFLOW_API_KEY = _get_streamlit_secret("SILICONFLOW_API_KEY") or os.getenv("SILICONFLOW_API_KEY", "")
        self.SILICONFLOW_BASE_URL = _get_streamlit_secret("SILICONFLOW_BASE_URL") or os.getenv(
            "SILICONFLOW_BASE_URL",
            "https://api.siliconflow.cn/v1"
        )
        self.SILICONFLOW_MODEL = _get_streamlit_secret("SILICONFLOW_MODEL") or os.getenv(
            "SILICONFLOW_MODEL",
            "Qwen/Qwen2.5-7B-Instruct"
        )
        
        self.DEFAULT_AI_MODEL = (_get_streamlit_secret("DEFAULT_AI_MODEL") or os.getenv("DEFAULT_AI_MODEL", "openai")).lower()
        
        # 微信公众号配置
        self.WECHAT_APP_ID = _get_streamlit_secret("WECHAT_APP_ID") or os.getenv("WECHAT_APP_ID", "")
        self.WECHAT_APP_SECRET = _get_streamlit_secret("WECHAT_APP_SECRET") or os.getenv("WECHAT_APP_SECRET", "")
        
        # DingTalk 通知配置
        self.DINGTALK_WEBHOOK = _get_streamlit_secret("DINGTALK_WEBHOOK") or os.getenv("DINGTALK_WEBHOOK", "")
        self.DINGTALK_SECRET = _get_streamlit_secret("DINGTALK_SECRET") or os.getenv("DINGTALK_SECRET", "")
        
        # 应用配置
        self.DATABASE_PATH = os.getenv(
            "DATABASE_PATH", 
            "data/wechat_writer.db"
        )
        self.DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    def _validate_required(self):
        """验证必需配置项
        
        注意：不再强制抛出异常，而是允许空配置
        用户可以在设置页面进行配置
        
        Raises:
            ValueError: 配置格式错误时抛出
        """
        # 验证默认AI模型名称是否有效
        valid_models = ["openai", "claude", "ollama", "siliconflow"]
        if self.DEFAULT_AI_MODEL not in valid_models:
            # 如果无效，设置默认值
            logger.warning(f"无效的 DEFAULT_AI_MODEL: {self.DEFAULT_AI_MODEL}，设置为 openai")
            self.DEFAULT_AI_MODEL = "openai"
        
        # 检查所选模型的配置，但不抛出异常
        if self.DEFAULT_AI_MODEL == "openai" and not self.OPENAI_API_KEY:
            logger.warning("OpenAI API Key 未配置")
        
        if self.DEFAULT_AI_MODEL == "claude" and not self.CLAUDE_API_KEY:
            logger.warning("Claude API Key 未配置")
        
        if self.DEFAULT_AI_MODEL == "siliconflow" and not self.SILICONFLOW_API_KEY:
            logger.warning("SiliconFlow API Key 未配置")
        
        # Ollama 模型不需要API密钥，但需要服务运行
    
    def is_ai_available(self, model: str) -> bool:
        """检查指定AI模型是否可用
        
        Args:
            model: 模型名称 (openai/claude/ollama/siliconflow)
            
        Returns:
            bool: 模型是否配置可用
        """
        model = model.lower()
        
        if model == "openai":
            return bool(self.OPENAI_API_KEY)
        elif model == "claude":
            return bool(self.CLAUDE_API_KEY)
        elif model == "siliconflow":
            return bool(self.SILICONFLOW_API_KEY)
        elif model == "ollama":
            # Ollama 默认可用（需要本地服务运行）
            return True
        
        return False
    
    def get_available_models(self) -> List[str]:
        """获取可用的AI模型列表
        
        Returns:
            List[str]: 可用模型名称列表
        """
        models = []
        
        if self.OPENAI_API_KEY:
            models.append("openai")
        
        if self.CLAUDE_API_KEY:
            models.append("claude")
        
        if self.SILICONFLOW_API_KEY:
            models.append("siliconflow")
        
        # Ollama 默认添加（需要本地服务）
        models.append("ollama")
        
        return models
    
    def get_model_config(self, model: str) -> dict:
        """获取指定模型的配置信息
        
        Args:
            model: 模型名称 (openai/claude/ollama/siliconflow)
            
        Returns:
            dict: 模型配置字典
            
        Raises:
            ValueError: 不支持的模型名称
        """
        model = model.lower()
        
        if model == "openai":
            return {
                "api_key": self.OPENAI_API_KEY,
                "base_url": self.OPENAI_BASE_URL,
                "model": self.OPENAI_MODEL,
            }
        elif model == "claude":
            return {
                "api_key": self.CLAUDE_API_KEY,
                "model": self.CLAUDE_MODEL,
            }
        elif model == "siliconflow":
            return {
                "api_key": self.SILICONFLOW_API_KEY,
                "base_url": self.SILICONFLOW_BASE_URL,
                "model": self.SILICONFLOW_MODEL,
            }
        elif model == "ollama":
            return {
                "base_url": self.OLLAMA_BASE_URL,
                "model": self.OLLAMA_MODEL,
            }
        else:
            raise ValueError(f"不支持的模型: {model}")
    
    def get_wechat_config(self) -> dict:
        """获取微信公众号配置
        
        Returns:
            dict: 微信配置字典
        """
        return {
            "app_id": self.WECHAT_APP_ID,
            "app_secret": self.WECHAT_APP_SECRET,
        }
    
    def has_wechat_config(self) -> bool:
        """检查微信配置是否完整
        
        Returns:
            bool: 微信配置是否完整
        """
        return bool(self.WECHAT_APP_ID and self.WECHAT_APP_SECRET)
    
    def has_dingtalk_config(self) -> bool:
        """检查钉钉通知配置是否完整
        
        Returns:
            bool: 钉钉配置是否完整（webhook必需，secret可选）
        """
        return bool(self.DINGTALK_WEBHOOK)
    
    def __repr__(self) -> str:
        """安全的字符串表示（隐藏敏感信息）"""
        return (
            f"Settings("
            f"default_model={self.DEFAULT_AI_MODEL}, "
            f"available_models={self.get_available_models()}, "
            f"has_wechat={self.has_wechat_config()}, "
            f"debug={self.DEBUG_MODE})"
        )


# ==================== 全局配置实例 ====================

_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置实例（单例模式）
    
    Returns:
        Settings: 配置实例
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings(env_file: Optional[str] = None) -> Settings:
    """重新加载配置
    
    Args:
        env_file: 指定 .env 文件路径
        
    Returns:
        Settings: 新的配置实例
    """
    global _settings
    _settings = Settings(env_file=env_file)
    return _settings