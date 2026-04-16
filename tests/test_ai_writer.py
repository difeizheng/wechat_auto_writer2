"""
AI Writer 模块测试
验证多模型抽象层的实现
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ai_writer import (
    AIWriter,
    AIProvider,
    OpenAIProvider,
    ClaudeProvider,
    OllamaProvider,
    AIWriterError,
    ModelNotAvailableError,
    APICallError,
    ResponseParseError,
    create_ai_writer,
    get_default_prompt
)
from config.settings import Settings


# ==================== Provider 测试 ====================

class TestOpenAIProvider:
    """OpenAI Provider测试"""
    
    def test_provider_init(self):
        """测试Provider初始化"""
        provider = OpenAIProvider(
            api_key="test_key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini"
        )
        
        assert provider.api_key == "test_key"
        assert provider.base_url == "https://api.openai.com/v1"
        assert provider.model == "gpt-4o-mini"
    
    def test_get_model_name(self):
        """测试模型名称获取"""
        provider = OpenAIProvider(
            api_key="test_key",
            model="gpt-4"
        )
        
        assert provider.get_model_name() == "OpenAI gpt-4"
    
    def test_get_provider_name(self):
        """测试提供商名称"""
        provider = OpenAIProvider(api_key="test_key")
        assert provider.get_provider_name() == "openai"
    
    def test_is_available_without_key(self):
        """测试无API密钥时的可用性"""
        provider = OpenAIProvider(api_key="")
        assert provider.is_available() is False
    
    def test_parse_response(self):
        """测试响应解析"""
        provider = OpenAIProvider(api_key="test_key")
        
        # 测试标准格式
        response = """
【标题】测试文章标题
【摘要】这是一篇测试文章的摘要内容
【正文】<p>这是第一段内容。</p><h2>小标题</h2><p>这是第二段内容。</p>
【关键词】测试,文章,AI
"""
        result = provider._parse_response(response)
        
        assert result["title"] == "测试文章标题"
        assert result["digest"] == "这是一篇测试文章的摘要内容"
        assert "<p>这是第一段内容。" in result["content"]
        assert result["keywords"] == ["测试", "文章", "AI"]
    
    def test_parse_response_without_keywords(self):
        """测试无关键词的响应解析"""
        provider = OpenAIProvider(api_key="test_key")
        
        response = """
【标题】无关键词文章
【摘要】摘要内容
【正文】<p>正文内容</p>
"""
        result = provider._parse_response(response)
        
        assert result["title"] == "无关键词文章"
        assert result["keywords"] == []


class TestClaudeProvider:
    """Claude Provider测试"""
    
    def test_provider_init(self):
        """测试Provider初始化"""
        provider = ClaudeProvider(
            api_key="test_key",
            model="claude-3-haiku-20240307"
        )
        
        assert provider.api_key == "test_key"
        assert provider.model == "claude-3-haiku-20240307"
    
    def test_get_model_name(self):
        """测试模型名称获取"""
        provider = ClaudeProvider(api_key="test_key")
        assert provider.get_model_name() == "Claude claude-3-haiku-20240307"
    
    def test_get_provider_name(self):
        """测试提供商名称"""
        provider = ClaudeProvider(api_key="test_key")
        assert provider.get_provider_name() == "claude"
    
    def test_is_available_with_key(self):
        """测试有API密钥时的可用性"""
        provider = ClaudeProvider(api_key="test_key")
        assert provider.is_available() is True
    
    def test_is_available_without_key(self):
        """测试无API密钥时的可用性"""
        provider = ClaudeProvider(api_key="")
        assert provider.is_available() is False


class TestOllamaProvider:
    """Ollama Provider测试"""
    
    def test_provider_init(self):
        """测试Provider初始化"""
        provider = OllamaProvider(
            base_url="http://localhost:11434",
            model="llama3"
        )
        
        assert provider.base_url == "http://localhost:11434"
        assert provider.model == "llama3"
    
    def test_get_model_name(self):
        """测试模型名称获取"""
        provider = OllamaProvider(model="mistral")
        assert provider.get_model_name() == "Ollama mistral"
    
    def test_get_provider_name(self):
        """测试提供商名称"""
        provider = OllamaProvider()
        assert provider.get_provider_name() == "ollama"
    
    def test_get_available_models_returns_list(self):
        """测试获取可用模型返回列表"""
        provider = OllamaProvider()
        models = provider.get_available_models()
        assert isinstance(models, list)


# ==================== AIWriter 主类测试 ====================

class TestAIWriter:
    """AIWriter主类测试"""
    
    def test_writer_init_without_settings(self):
        """测试无settings初始化"""
        writer = AIWriter(model="openai")
        
        assert writer.model == "openai"
        assert writer.provider is None
    
    def test_writer_init_with_invalid_model(self):
        """测试无效模型初始化"""
        with pytest.raises(ValueError) as exc_info:
            AIWriter(model="invalid_model")
        
        assert "不支持的模型" in str(exc_info.value)
    
    def test_writer_init_with_settings(self):
        """测试带settings初始化"""
        # 创建mock settings
        class MockSettings:
            OPENAI_API_KEY = "test_key"
            OPENAI_BASE_URL = "https://api.openai.com/v1"
            CLAUDE_API_KEY = ""
            OLLAMA_BASE_URL = "http://localhost:11434"
        
        settings = MockSettings()
        writer = AIWriter(model="openai", settings=settings)
        
        assert writer.model == "openai"
        assert writer.provider is not None
        assert isinstance(writer.provider, OpenAIProvider)
    
    def test_switch_model(self):
        """测试模型切换"""
        class MockSettings:
            OPENAI_API_KEY = "test_key"
            OPENAI_BASE_URL = "https://api.openai.com/v1"
            CLAUDE_API_KEY = "test_claude_key"
            OLLAMA_BASE_URL = "http://localhost:11434"
        
        settings = MockSettings()
        writer = AIWriter(model="openai", settings=settings)
        
        # 切换到Claude
        writer.switch_model("claude")
        
        assert writer.model == "claude"
        assert isinstance(writer.provider, ClaudeProvider)
    
    def test_switch_model_without_settings(self):
        """测试无settings时切换模型"""
        writer = AIWriter(model="openai")
        
        with pytest.raises(ValueError) as exc_info:
            writer.switch_model("claude")
        
        assert "未设置settings配置" in str(exc_info.value)
    
    def test_switch_model_to_same_model(self):
        """测试切换到相同模型"""
        class MockSettings:
            OPENAI_API_KEY = "test_key"
            OPENAI_BASE_URL = "https://api.openai.com/v1"
            CLAUDE_API_KEY = ""
            OLLAMA_BASE_URL = "http://localhost:11434"
        
        settings = MockSettings()
        writer = AIWriter(model="openai", settings=settings)
        
        # 切换到相同模型
        writer.switch_model("openai")
        
        assert writer.model == "openai"
    
    def test_get_supported_styles(self):
        """测试获取支持的风格"""
        writer = AIWriter(model="openai")
        styles = writer.get_supported_styles()
        
        assert isinstance(styles, list)
        assert "科普" in styles
        assert "故事" in styles
        assert "干货" in styles
        assert "互动" in styles
    
    def test_build_prompt_default(self):
        """测试默认Prompt构建"""
        writer = AIWriter(model="openai")
        prompt = writer._build_prompt(
            topic="人工智能的未来",
            style="科普",
            template=None,
            word_count=800
        )
        
        assert "人工智能的未来" in prompt
        assert "科普" in prompt
        assert "800" in prompt
        assert "【标题】" in prompt
        assert "【摘要】" in prompt
        assert "【正文】" in prompt
        assert "【关键词】" in prompt
    
    def test_build_prompt_with_template(self):
        """测试使用模板Prompt"""
        writer = AIWriter(model="openai")
        template = {
            "prompt_template": "请根据主题{topic}写一篇{style}风格的文章，字数约{word_count}字"
        }
        
        prompt = writer._build_prompt(
            topic="AI技术",
            style="干货",
            template=template,
            word_count=1000
        )
        
        assert "AI技术" in prompt
        assert "干货" in prompt
        assert "1000" in prompt
    
    def test_generate_article_validation_empty_topic(self):
        """测试文章生成参数验证（空主题）"""
        class MockSettings:
            OPENAI_API_KEY = "test_key"
            OPENAI_BASE_URL = "https://api.openai.com/v1"
            CLAUDE_API_KEY = ""
            OLLAMA_BASE_URL = "http://localhost:11434"
        
        settings = MockSettings()
        writer = AIWriter(model="openai", settings=settings)
        
        with pytest.raises(ValueError) as exc_info:
            writer.generate_article(topic="")
        
        assert "文章主题不能为空" in str(exc_info.value)
    
    def test_generate_article_validation_no_provider(self):
        """测试文章生成参数验证（无provider）"""
        writer = AIWriter(model="openai")
        
        with pytest.raises(ValueError) as exc_info:
            writer.generate_article(topic="测试主题")
        
        assert "Provider未初始化" in str(exc_info.value)
    
    def test_get_current_model(self):
        """测试获取当前模型"""
        class MockSettings:
            OPENAI_API_KEY = "test_key"
            OPENAI_BASE_URL = "https://api.openai.com/v1"
            CLAUDE_API_KEY = ""
            OLLAMA_BASE_URL = "http://localhost:11434"
        
        settings = MockSettings()
        writer = AIWriter(model="openai", settings=settings)
        
        model = writer.get_current_model()
        assert "OpenAI" in model
    
    def test_check_service_health(self):
        """测试服务健康检查"""
        class MockSettings:
            OPENAI_API_KEY = "test_key"
            OPENAI_BASE_URL = "https://api.openai.com/v1"
            CLAUDE_API_KEY = "test_claude_key"
            OLLAMA_BASE_URL = "http://localhost:11434"
        
        settings = MockSettings()
        writer = AIWriter(model="openai", settings=settings)
        
        health = writer.check_service_health()
        
        assert isinstance(health, dict)
        assert "openai" in health
        assert "claude" in health
        assert "ollama" in health


# ==================== 工厂函数测试 ====================

class TestFactoryFunctions:
    """工厂函数测试"""
    
    def test_create_ai_writer(self):
        """测试创建AI Writer"""
        writer = create_ai_writer(model="openai")
        assert isinstance(writer, AIWriter)
        assert writer.model == "openai"
    
    def test_get_default_prompt(self):
        """测试获取默认Prompt"""
        prompt = get_default_prompt(
            topic="测试主题",
            style="科普",
            word_count=800
        )
        
        assert "测试主题" in prompt
        assert "科普" in prompt
        assert "800" in prompt


# ==================== 异常类测试 ====================

class TestExceptions:
    """异常类测试"""
    
    def test_ai_writer_error(self):
        """测试基础异常"""
        error = AIWriterError("测试错误")
        assert str(error) == "测试错误"
    
    def test_model_not_available_error(self):
        """测试模型不可用异常"""
        error = ModelNotAvailableError("OpenAI API密钥未配置")
        assert isinstance(error, AIWriterError)
    
    def test_api_call_error(self):
        """测试API调用异常"""
        error = APICallError("API调用失败")
        assert isinstance(error, AIWriterError)
    
    def test_response_parse_error(self):
        """测试响应解析异常"""
        error = ResponseParseError("解析失败")
        assert isinstance(error, AIWriterError)


# ==================== 统一返回格式测试 ====================

class TestResponseFormat:
    """统一返回格式测试"""
    
    def test_parse_response_format(self):
        """测试响应格式包含所有必需字段"""
        provider = OpenAIProvider(api_key="test_key")
        
        response = """
【标题】完整格式测试
【摘要】这是摘要
【正文】<p>内容</p>
【关键词】关键词1,关键词2
"""
        result = provider._parse_response(response)
        
        # 验收标准：统一返回格式 {title, content, digest, keywords}
        assert "title" in result
        assert "content" in result
        assert "digest" in result
        assert "keywords" in result
        
        assert isinstance(result["title"], str)
        assert isinstance(result["content"], str)
        assert isinstance(result["digest"], str)
        assert isinstance(result["keywords"], list)


# ==================== 验收标准测试 ====================

def test_all_acceptance_criteria():
    """
    验收标准综合测试
    
    验收标准：
    - [ ] 三种模型均可正常调用（至少代码结构正确）
    - [ ] 统一返回格式 {title, content, digest, keywords}
    - [ ] 模型切换无需重启应用
    - [ ] Prompt构建正确（支持模板和默认）
    - [ ] 响应解析正确
    """
    
    # 1. 三种模型代码结构正确
    openai_provider = OpenAIProvider(api_key="test_key")
    claude_provider = ClaudeProvider(api_key="test_key")
    ollama_provider = OllamaProvider(base_url="http://localhost:11434")
    
    assert openai_provider.get_provider_name() == "openai"
    assert claude_provider.get_provider_name() == "claude"
    assert ollama_provider.get_provider_name() == "ollama"
    
    # 2. 统一返回格式
    response = """
【标题】验收测试
【摘要】摘要内容
【正文】<p>正文</p>
【关键词】关键词1,关键词2
"""
    result = openai_provider._parse_response(response)
    required_keys = ["title", "content", "digest", "keywords"]
    for key in required_keys:
        assert key in result, f"缺少必需字段: {key}"
    
    # 3. 模型切换无需重启应用
    class MockSettings:
        OPENAI_API_KEY = "test_key"
        OPENAI_BASE_URL = "https://api.openai.com/v1"
        CLAUDE_API_KEY = "test_claude_key"
        OLLAMA_BASE_URL = "http://localhost:11434"
    
    settings = MockSettings()
    writer = AIWriter(model="openai", settings=settings)
    
    writer.switch_model("claude")  # 切换模型
    assert writer.model == "claude"
    assert isinstance(writer.provider, ClaudeProvider)
    
    writer.switch_model("ollama")  # 再次切换
    assert writer.model == "ollama"
    assert isinstance(writer.provider, OllamaProvider)
    
    # 4. Prompt构建正确（默认和模板）
    prompt_default = writer._build_prompt(
        topic="测试", style="科普", template=None, word_count=800
    )
    assert "【标题】" in prompt_default
    
    template = {"prompt_template": "主题: {topic}, 风格: {style}, 字数: {word_count}"}
    prompt_template = writer._build_prompt(
        topic="测试", style="干货", template=template, word_count=1000
    )
    assert "主题: 测试" in prompt_template
    
    # 5. 响应解析正确
    result = openai_provider._parse_response(response)
    assert result["title"] == "验收测试"
    assert result["digest"] == "摘要内容"
    assert "<p>正文" in result["content"]
    assert result["keywords"] == ["关键词1", "关键词2"]
    
    print("[PASS] 所有验收标准测试通过！")


# ==================== 运行测试 ====================

if __name__ == "__main__":
    # 运行验收标准测试
    test_all_acceptance_criteria()
    
    print("\n" + "="*50)
    print("AI Writer 模块测试完成")
    print("="*50)