"""
AI文章生成模块
支持 OpenAI GPT / Claude / Ollama 多模型切换
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
import requests
import json
import re
import time
import logging

# 配置日志
logger = logging.getLogger(__name__)


# ==================== 异常定义 ====================

class AIWriterError(Exception):
    """AI Writer基础异常"""
    pass


class ModelNotAvailableError(AIWriterError):
    """模型不可用异常"""
    pass


class APICallError(AIWriterError):
    """API调用异常"""
    pass


class ResponseParseError(AIWriterError):
    """响应解析异常"""
    pass


# ==================== 抽象接口 ====================

class AIProvider(ABC):
    """AI提供商抽象接口
    
    所有AI模型提供商必须实现此接口，确保统一调用方式。
    """
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成文章内容
        
        Args:
            prompt: 生成提示词
            **kwargs: 额外参数（temperature, max_tokens等）
        
        Returns:
            dict: 包含以下字段的字典
                - title: str - 文章标题
                - content: str - HTML格式的正文内容
                - digest: str - 文章摘要
                - keywords: list - 关键词列表
        
        Raises:
            APICallError: API调用失败时抛出
            ResponseParseError: 响应解析失败时抛出
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        检查服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        获取模型名称
        
        Returns:
            str: 模型名称（如 "OpenAI gpt-4o-mini"）
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        获取提供商名称
        
        Returns:
            str: 提供商名称（如 "openai"）
        """
        pass
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """
        解析AI响应内容
        
        Args:
            content: AI返回的原始文本
        
        Returns:
            dict: 结构化的文章数据
        
        Raises:
            ResponseParseError: 解析失败时抛出
        """
        try:
            # 提取标题
            title_match = re.search(r"【标题】(.+)", content)
            title = title_match.group(1).strip() if title_match else "未命名文章"
            
            # 提取摘要
            digest_match = re.search(r"【摘要】(.+)", content)
            digest = digest_match.group(1).strip() if digest_match else ""
            
            # 提取正文
            content_match = re.search(r"【正文】(.+?)(?=【关键词】|$)", content, re.DOTALL)
            article_content = content_match.group(1).strip() if content_match else content
            
            # 提取关键词
            keywords_match = re.search(r"【关键词】(.+)", content)
            keywords_str = keywords_match.group(1).strip() if keywords_match else ""
            keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
            
            # 如果解析失败，尝试使用全文作为内容
            if not title_match and not content_match:
                logger.warning("响应格式不标准，使用全文作为内容")
                # 尝试提取第一行作为标题
                lines = content.strip().split('\n')
                title = lines[0] if lines else "未命名文章"
                article_content = content
            
            return {
                "title": title,
                "content": article_content,
                "digest": digest,
                "keywords": keywords
            }
        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            raise ResponseParseError(f"解析AI响应失败: {e}")


# ==================== OpenAI 实现 ====================

class OpenAIProvider(AIProvider):
    """OpenAI GPT模型提供商
    
    使用OpenAI官方API进行文章生成。
    支持自定义base_url（兼容第三方API）。
    """
    
    def __init__(
        self, 
        api_key: str, 
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini"
    ):
        """
        初始化OpenAI Provider
        
        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL（支持第三方代理）
            model: 模型名称（默认使用成本较低的gpt-4o-mini）
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client = None
    
    def _get_client(self):
        """
        获取OpenAI客户端实例（延迟加载）
        
        Returns:
            OpenAI: OpenAI客户端实例
        """
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise APICallError("未安装openai库，请运行: pip install openai")
        return self._client
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        使用OpenAI生成文章
        
        Args:
            prompt: 生成提示词
            **kwargs: 
                - temperature: 温度参数 (0-2)
                - max_tokens: 最大token数
        
        Returns:
            dict: 文章数据字典
        
        Raises:
            APICallError: API调用失败
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2000)
        
        try:
            logger.info(f"调用OpenAI API: model={self.model}, temperature={temperature}")
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            
            if not content:
                raise APICallError("OpenAI返回空响应")
            
            logger.info("OpenAI API调用成功，解析响应")
            return self._parse_response(content)
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            raise APICallError(f"OpenAI API调用失败: {e}")
    
    def is_available(self) -> bool:
        """
        检查OpenAI服务是否可用
        
        Returns:
            bool: 是否可用
        """
        if not self.api_key:
            return False
        
        try:
            client = self._get_client()
            # 尝试获取模型列表来验证连接
            client.models.list()
            return True
        except Exception as e:
            logger.warning(f"OpenAI服务检查失败: {e}")
            return False
    
    def get_model_name(self) -> str:
        """
        获取模型名称
        
        Returns:
            str: 模型名称
        """
        return f"OpenAI {self.model}"
    
    def get_provider_name(self) -> str:
        """
        获取提供商名称
        
        Returns:
            str: 提供商名称
        """
        return "openai"


# ==================== Claude 实现 ====================

class ClaudeProvider(AIProvider):
    """Anthropic Claude模型提供商
    
    使用Anthropic官方API进行文章生成。
    """
    
    def __init__(
        self, 
        api_key: str,
        model: str = "claude-3-haiku-20240307"
    ):
        """
        初始化Claude Provider
        
        Args:
            api_key: Anthropic API密钥
            model: 模型名称（默认使用成本较低的claude-3-haiku）
        """
        self.api_key = api_key
        self.model = model
        self._client = None
    
    def _get_client(self):
        """
        获取Anthropic客户端实例（延迟加载）
        
        Returns:
            Anthropic: Anthropic客户端实例
        """
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise APICallError("未安装anthropic库，请运行: pip install anthropic")
        return self._client
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        使用Claude生成文章
        
        Args:
            prompt: 生成提示词
            **kwargs:
                - max_tokens: 最大token数
        
        Returns:
            dict: 文章数据字典
        
        Raises:
            APICallError: API调用失败
        """
        client = self._get_client()
        
        max_tokens = kwargs.get("max_tokens", 2000)
        
        try:
            logger.info(f"调用Claude API: model={self.model}, max_tokens={max_tokens}")
            
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            if not content:
                raise APICallError("Claude返回空响应")
            
            logger.info("Claude API调用成功，解析响应")
            return self._parse_response(content)
            
        except Exception as e:
            logger.error(f"Claude API调用失败: {e}")
            raise APICallError(f"Claude API调用失败: {e}")
    
    def is_available(self) -> bool:
        """
        检查Claude服务是否可用
        
        Returns:
            bool: 是否可用
        """
        return bool(self.api_key)
    
    def get_model_name(self) -> str:
        """
        获取模型名称
        
        Returns:
            str: 模型名称
        """
        return f"Claude {self.model}"
    
    def get_provider_name(self) -> str:
        """
        获取提供商名称
        
        Returns:
            str: 提供商名称
        """
        return "claude"


# ==================== Ollama 实现 ====================

class OllamaProvider(AIProvider):
    """Ollama本地模型提供商
    
    使用本地Ollama服务进行文章生成。
    支持多种本地模型（llama3, mistral等）。
    """
    
    def __init__(
        self, 
        base_url: str = "http://localhost:11434",
        model: str = "llama3"
    ):
        """
        初始化Ollama Provider
        
        Args:
            base_url: Ollama服务地址
            model: 模型名称（默认llama3）
        """
        self.base_url = base_url
        self.model = model
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        使用Ollama生成文章
        
        Args:
            prompt: 生成提示词
            **kwargs:
                - temperature: 温度参数
                - timeout: 请求超时时间
        
        Returns:
            dict: 文章数据字典
        
        Raises:
            APICallError: API调用失败
        """
        timeout = kwargs.get("timeout", 120)
        
        try:
            logger.info(f"调用Ollama API: model={self.model}, base_url={self.base_url}")
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.7)
                    }
                },
                timeout=timeout
            )
            
            if response.status_code != 200:
                raise APICallError(f"Ollama返回错误状态码: {response.status_code}")
            
            data = response.json()
            content = data.get("response", "")
            
            if not content:
                raise APICallError("Ollama返回空响应")
            
            logger.info("Ollama API调用成功，解析响应")
            return self._parse_response(content)
            
        except requests.exceptions.Timeout:
            logger.error("Ollama请求超时")
            raise APICallError("Ollama请求超时，请检查服务状态或增加timeout参数")
        except requests.exceptions.ConnectionError:
            logger.error("Ollama连接失败")
            raise APICallError(f"无法连接到Ollama服务: {self.base_url}")
        except Exception as e:
            logger.error(f"Ollama API调用失败: {e}")
            raise APICallError(f"Ollama API调用失败: {e}")
    
    def is_available(self) -> bool:
        """
        检查Ollama服务是否可用
        
        Returns:
            bool: 是否可用
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama服务检查失败: {e}")
            return False
    
    def get_model_name(self) -> str:
        """
        获取模型名称
        
        Returns:
            str: 模型名称
        """
        return f"Ollama {self.model}"
    
    def get_provider_name(self) -> str:
        """
        获取提供商名称
        
        Returns:
            str: 提供商名称
        """
        return "ollama"
    
    def get_available_models(self) -> List[str]:
        """
        获取Ollama服务上可用的模型列表
        
        Returns:
            list: 可用模型名称列表
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return models
        except Exception as e:
            logger.warning(f"获取Ollama模型列表失败: {e}")
        return []


# ==================== SiliconFlow 实现 ====================

class SiliconFlowProvider(AIProvider):
    """SiliconFlow模型提供商
    
    SiliconFlow是国内AI模型服务平台，提供多种大模型API。
    使用OpenAI兼容的API格式，支持多种模型（Qwen、DeepSeek等）。
    """
    
    def __init__(
        self, 
        api_key: str, 
        base_url: str = "https://api.siliconflow.cn/v1",
        model: str = "Qwen/Qwen2.5-7B-Instruct"
    ):
        """
        初始化SiliconFlow Provider
        
        Args:
            api_key: SiliconFlow API密钥
            base_url: API基础URL
            model: 模型名称（如 Qwen/Qwen2.5-7B-Instruct, deepseek-ai/DeepSeek-V2.5等）
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client = None
    
    def _get_client(self):
        """
        获取OpenAI兼容客户端实例（延迟加载）
        
        Returns:
            OpenAI: OpenAI兼容客户端实例
        """
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise APICallError("未安装openai库，请运行: pip install openai")
        return self._client
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        使用SiliconFlow生成文章
        
        Args:
            prompt: 生成提示词
            **kwargs: 
                - temperature: 温度参数 (0-2)
                - max_tokens: 最大token数
        
        Returns:
            dict: 文章数据字典
        
        Raises:
            APICallError: API调用失败
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2000)
        
        try:
            logger.info(f"调用SiliconFlow API: model={self.model}, temperature={temperature}")
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            
            if not content:
                raise APICallError("SiliconFlow返回空响应")
            
            logger.info("SiliconFlow API调用成功，解析响应")
            return self._parse_response(content)
            
        except Exception as e:
            logger.error(f"SiliconFlow API调用失败: {e}")
            raise APICallError(f"SiliconFlow API调用失败: {e}")
    
    def is_available(self) -> bool:
        """
        检查SiliconFlow服务是否可用
        
        Returns:
            bool: 是否可用
        """
        return bool(self.api_key)
    
    def get_model_name(self) -> str:
        """
        获取模型名称
        
        Returns:
            str: 模型名称
        """
        return f"SiliconFlow {self.model}"
    
    def get_provider_name(self) -> str:
        """
        获取提供商名称
        
        Returns:
            str: 提供商名称
        """
        return "siliconflow"


# ==================== AI Writer 主类 ====================

class AIWriter:
    """AI文章生成器
    
    核心功能：
    - 多模型切换（OpenAI/Claude/Ollama）
    - 文章生成（支持风格、模板、字数设置）
    - Prompt构建（默认和模板两种方式）
    - 错误重试机制
    """
    
    # 支持的提供商映射
    _providers = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "ollama": OllamaProvider,
        "siliconflow": SiliconFlowProvider
    }
    
    # 支持的文章风格
    _styles = ["科普", "故事", "干货", "互动", "资讯", "教程"]
    
    def __init__(self, model: str = "openai", settings: Any = None):
        """
        初始化AI Writer
        
        Args:
            model: 模型名称 (openai/claude/ollama)
            settings: Settings配置对象
        
        Raises:
            ValueError: 不支持的模型名称
        """
        self.model = model.lower()
        self.settings = settings
        self.provider: Optional[AIProvider] = None
        
        # 验证模型名称
        if self.model not in self._providers:
            raise ValueError(
                f"不支持的模型: {self.model}。"
                f"支持的模型: {', '.join(self._providers.keys())}"
            )
        
        # 初始化Provider
        if settings:
            self.provider = self._create_provider(self.model, settings)
        else:
            # 如果没有settings，需要后续手动设置
            logger.warning("未提供settings配置，需要手动初始化provider")
    
    def _create_provider(self, model: str, settings: Any) -> AIProvider:
        """
        创建Provider实例
        
        Args:
            model: 模型名称
            settings: Settings配置对象
        
        Returns:
            AIProvider: Provider实例
        
        Raises:
            ValueError: 不支持的模型
            ModelNotAvailableError: 模型配置缺失
        """
        model = model.lower()
        
        if model not in self._providers:
            raise ValueError(
                f"不支持的模型: {model}。"
                f"支持的模型: {', '.join(self._providers.keys())}"
            )
        
        provider_class = self._providers[model]
        
        try:
            if model == "openai":
                if not settings.OPENAI_API_KEY:
                    raise ModelNotAvailableError(
                        "OpenAI API密钥未配置。请在.env中设置OPENAI_API_KEY"
                    )
                return provider_class(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    model=settings.OPENAI_MODEL
                )
            
            elif model == "claude":
                if not settings.CLAUDE_API_KEY:
                    raise ModelNotAvailableError(
                        "Claude API密钥未配置。请在.env中设置CLAUDE_API_KEY"
                    )
                return provider_class(
                    api_key=settings.CLAUDE_API_KEY,
                    model=settings.CLAUDE_MODEL
                )
            
            elif model == "siliconflow":
                if not settings.SILICONFLOW_API_KEY:
                    raise ModelNotAvailableError(
                        "SiliconFlow API密钥未配置。请在.env中设置SILICONFLOW_API_KEY"
                    )
                return provider_class(
                    api_key=settings.SILICONFLOW_API_KEY,
                    base_url=settings.SILICONFLOW_BASE_URL,
                    model=settings.SILICONFLOW_MODEL
                )
            
            elif model == "ollama":
                return provider_class(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_MODEL
                )
        
        except ModelNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"创建Provider失败: {e}")
            raise ValueError(f"创建{model} Provider失败: {e}")
    
    def switch_model(self, model: str) -> None:
        """
        切换AI模型（无需重启应用）
        
        Args:
            model: 目标模型名称 (openai/claude/ollama)
        
        Raises:
            ValueError: 不支持的模型或配置缺失
        """
        model = model.lower()
        
        if model == self.model and self.provider:
            logger.info(f"模型已经是{model}，无需切换")
            return
        
        if not self.settings:
            raise ValueError("未设置settings配置，无法切换模型")
        
        logger.info(f"切换模型: {self.model} -> {model}")
        self.model = model
        self.provider = self._create_provider(model, self.settings)
        logger.info(f"模型切换成功: {self.provider.get_model_name()}")
    
    def generate_article(
        self,
        topic: str,
        style: str = "科普",
        template: Optional[Dict] = None,
        word_count: int = 800,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成公众号文章
        
        Args:
            topic: 文章主题
            style: 文章风格（科普/故事/干货/互动）
            template: 模板数据（可选）
            word_count: 目标字数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            **kwargs: 传递给provider的额外参数
        
        Returns:
            dict: 文章数据字典
                - title: str - 标题
                - content: str - HTML格式正文
                - digest: str - 摘要
                - keywords: list - 关键词
                - model: str - 使用的模型
                - provider: str - 提供商
                - timestamp: float - 生成时间
        
        Raises:
            ValueError: 参数验证失败
            AIWriterError: 生成失败
        """
        # 参数验证
        if not topic or len(topic.strip()) == 0:
            raise ValueError("文章主题不能为空")
        
        if not self.provider:
            raise ValueError("Provider未初始化，请先设置settings或手动初始化provider")
        
        # 构建Prompt
        prompt = self._build_prompt(topic, style, template, word_count)
        
        # 重试机制
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"生成文章 (尝试 {attempt + 1}/{max_retries}): "
                    f"topic={topic}, style={style}, model={self.model}"
                )
                
                result = self.provider.generate(
                    prompt,
                    temperature=kwargs.get("temperature", 0.7),
                    max_tokens=kwargs.get("max_tokens", 2000),
                    **kwargs
                )
                
                # 添加元数据
                result["model"] = self.provider.get_model_name()
                result["provider"] = self.provider.get_provider_name()
                result["timestamp"] = time.time()
                result["topic"] = topic
                result["style"] = style
                result["word_count"] = word_count
                
                logger.info(f"文章生成成功: {result['title']}")
                return result
                
            except APICallError as e:
                last_error = e
                logger.warning(f"生成失败 (尝试 {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    logger.info(f"等待 {retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"达到最大重试次数 {max_retries}，生成失败")
        
        # 所有重试都失败
        raise AIWriterError(
            f"文章生成失败（重试{max_retries}次后）: {last_error}"
        )
    
    def _build_prompt(
        self,
        topic: str,
        style: str,
        template: Optional[Dict],
        word_count: int
    ) -> str:
        """
        构建生成Prompt
        
        Args:
            topic: 文章主题
            style: 文章风格
            template: 模板数据（可选）
            word_count: 目标字数
        
        Returns:
            str: 完整的Prompt字符串
        """
        # 如果有模板，使用模板的prompt_template
        if template and template.get("prompt_template"):
            prompt_template = template["prompt_template"]
            
            try:
                prompt = prompt_template.format(
                    topic=topic,
                    word_count=word_count,
                    style=style
                )
                logger.info("使用模板Prompt")
                return prompt
            except KeyError as e:
                logger.warning(f"模板格式化失败: {e}，使用默认Prompt")
        
        # 使用默认Prompt
        logger.info("使用默认Prompt")
        prompt = self._get_default_prompt(topic, style, word_count)
        return prompt
    
    def _get_default_prompt(self, topic: str, style: str, word_count: int) -> str:
        """
        获取默认Prompt
        
        Args:
            topic: 文章主题
            style: 文章风格
            word_count: 目标字数
        
        Returns:
            str: 默认Prompt字符串
        """
        # 根据风格调整指令
        style_instructions = {
            "科普": """
- 用通俗易懂的语言解释专业概念
- 使用类比和案例让读者更好理解
- 适当引用权威数据或研究成果
- 激发读者的好奇心和学习兴趣""",
            
            "故事": """
- 构建生动的人物和情节
- 使用悬念和转折吸引读者
- 在故事中融入要传递的观点或知识
- 结尾要有情感共鸣或启发""",
            
            "干货": """
- 提供具体的方法和步骤
- 使用列表、表格等清晰展示要点
- 给出可执行的行动建议
- 内容要有实用价值，解决实际问题""",
            
            "互动": """
- 设计问题引导读者思考
- 鼓励读者参与讨论或分享经验
- 使用投票、问答等形式增强互动
- 结尾设置互动话题或行动号召""",
            
            "资讯": """
- 客观报道最新动态或趋势
- 提供背景信息和影响分析
- 引用可靠的信息来源
- 帮助读者快速了解要点""",
            
            "教程": """
- 分步骤详细讲解操作流程
- 配合实例演示每个步骤
- 说明注意事项和常见问题
- 让读者能够实际操作成功"""
        }
        
        style_guide = style_instructions.get(style, style_instructions["科普"])
        
        prompt = f"""
你是一位专业的公众号文章写手，擅长创作高质量、有吸引力的内容。
请根据以下要求创作一篇公众号文章：

【主题】{topic}
【风格】{style}
【字数】约{word_count}字

【风格要求】
{style_guide}

【结构要求】
- 开头：用1-2句话抓住读者注意力，引出主题
- 主体：分3-5个小节，每节有小标题，内容清晰有条理
- 重点：使用<strong>加粗</strong>或<ul><li>列表</li></ul>呈现关键信息
- 结尾：总结要点，引导读者互动（点赞、评论、转发等）

【格式要求】
请严格按以下格式输出，不要输出其他内容：

【标题】文章标题（简短有力，不超过15字）
【摘要】50字以内的摘要（概括文章核心内容）
【正文】
使用HTML标签格式化正文：
- 使用<p>标签包裹段落
- 使用<h2>标签标记小标题
- 使用<strong>标签加粗重点内容
- 使用<ul>和<li>标签呈现列表
- 使用<blockquote>标签引用重要内容

【关键词】关键词1,关键词2,关键词3（3-5个关键词，用逗号分隔）

现在开始创作文章：
"""
        
        return prompt
    
    def get_available_models(self) -> List[str]:
        """
        获取可用的AI模型列表
        
        Returns:
            list: 可用模型名称列表
        """
        if not self.settings:
            logger.warning("未设置settings，无法检查模型可用性")
            return list(self._providers.keys())
        
        models = []
        for model_name in self._providers.keys():
            try:
                provider = self._create_provider(model_name, self.settings)
                if provider.is_available():
                    models.append(model_name)
                    logger.info(f"模型可用: {model_name}")
            except (ValueError, ModelNotAvailableError) as e:
                logger.warning(f"模型不可用: {model_name} - {e}")
            except Exception as e:
                logger.warning(f"模型检查失败: {model_name} - {e}")
        
        return models
    
    def get_current_model(self) -> str:
        """
        获取当前使用的模型
        
        Returns:
            str: 当前模型名称
        """
        if self.provider:
            return self.provider.get_model_name()
        return self.model
    
    def get_supported_styles(self) -> List[str]:
        """
        获取支持的文章风格列表
        
        Returns:
            list: 风格名称列表
        """
        return self._styles.copy()
    
    def check_service_health(self) -> Dict[str, Any]:
        """
        检查服务健康状态
        
        Returns:
            dict: 各模型的健康状态
        """
        health_status = {}
        
        for model_name in self._providers.keys():
            try:
                if self.settings:
                    provider = self._create_provider(model_name, self.settings)
                    health_status[model_name] = {
                        "available": provider.is_available(),
                        "model_name": provider.get_model_name(),
                        "provider": provider.get_provider_name()
                    }
                else:
                    health_status[model_name] = {
                        "available": False,
                        "error": "未配置settings"
                    }
            except Exception as e:
                health_status[model_name] = {
                    "available": False,
                    "error": str(e)
                }
        
        return health_status


# ==================== 工厂函数 ====================

def create_ai_writer(model: str = "openai", settings: Any = None) -> AIWriter:
    """
    创建AI Writer实例的工厂函数
    
    Args:
        model: 模型名称
        settings: Settings配置对象
    
    Returns:
        AIWriter: AI Writer实例
    """
    return AIWriter(model=model, settings=settings)


def get_default_prompt(topic: str, style: str = "科普", word_count: int = 800) -> str:
    """
    获取默认Prompt（独立函数，可用于测试）
    
    Args:
        topic: 文章主题
        style: 文章风格
        word_count: 目标字数
    
    Returns:
        str: Prompt字符串
    """
    writer = AIWriter()  # 不需要settings来生成prompt
    return writer._get_default_prompt(topic, style, word_count)