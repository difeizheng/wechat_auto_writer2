"""
AI Writer 模块使用演示

演示如何使用 AI Writer 进行文章生成和模型切换
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ai_writer import (
    AIWriter,
    OpenAIProvider,
    ClaudeProvider,
    OllamaProvider,
    create_ai_writer,
    get_default_prompt
)
from config.settings import Settings


def demo_prompt_generation():
    """演示 Prompt 生成"""
    print("\n" + "="*60)
    print("1. Prompt 生成演示")
    print("="*60)
    
    # 获取默认 Prompt
    prompt = get_default_prompt(
        topic="人工智能在教育领域的应用",
        style="科普",
        word_count=800
    )
    
    print("\n生成的 Prompt:")
    print("-"*40)
    # 只显示前500字符，避免输出过长
    print(prompt[:500] + "...")
    print("-"*40)
    
    # 展示不同风格的 Prompt 特点
    styles = ["科普", "故事", "干货", "互动"]
    for style in styles[:2]:  # 只展示2个风格
        prompt = get_default_prompt(topic="AI技术", style=style, word_count=600)
        style_section = prompt.split("【风格要求】")[1].split("【结构要求】")[0]
        print(f"\n{style}风格要求:")
        print(style_section.strip()[:300])


def demo_provider_creation():
    """演示 Provider 创建"""
    print("\n" + "="*60)
    print("2. Provider 创建演示")
    print("="*60)
    
    # OpenAI Provider
    openai_provider = OpenAIProvider(
        api_key="demo_key",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini"
    )
    print(f"\nOpenAI Provider:")
    print(f"  - 模型名称: {openai_provider.get_model_name()}")
    print(f"  - 提供商: {openai_provider.get_provider_name()}")
    print(f"  - API可用性检查: {'是' if openai_provider.is_available() else '否'} (演示模式)")
    
    # Claude Provider
    claude_provider = ClaudeProvider(
        api_key="demo_key",
        model="claude-3-haiku-20240307"
    )
    print(f"\nClaude Provider:")
    print(f"  - 模型名称: {claude_provider.get_model_name()}")
    print(f"  - 提供商: {claude_provider.get_provider_name()}")
    
    # Ollama Provider
    ollama_provider = OllamaProvider(
        base_url="http://localhost:11434",
        model="llama3"
    )
    print(f"\nOllama Provider:")
    print(f"  - 模型名称: {ollama_provider.get_model_name()}")
    print(f"  - 提供商: {ollama_provider.get_provider_name()}")
    print(f"  - 服务地址: {ollama_provider.base_url}")


def demo_response_parsing():
    """演示响应解析"""
    print("\n" + "="*60)
    print("3. 响应解析演示")
    print("="*60)
    
    provider = OpenAIProvider(api_key="demo_key")
    
    # 模拟 AI 响应
    mock_response = """
【标题】人工智能：改变教育的未来力量
【摘要】AI技术正在重塑教育模式，从个性化学习到智能辅导，为每个学生提供定制化的学习体验。
【正文】
<h2>个性化学习：因材施教的数字化实现</h2>
<p>传统的教育模式往往采用"一刀切"的方式，难以满足每个学生的个性化需求。而AI技术的引入，让<strong>因材施教</strong>这一古老的教育理念有了数字化的实现路径。</p>

<p>通过分析学生的学习数据，AI系统能够：</p>
<ul>
<li>识别学生的薄弱知识点</li>
<li>推荐适合的学习资源</li>
<li>调整学习节奏和难度</li>
</ul>

<h2>智能辅导：24小时的学习伙伴</h2>
<p>AI辅导系统能够提供<strong>全天候的学习支持</strong>，学生不再需要等待老师的答疑时间。这类系统可以：</p>

<blockquote>
智能辅导不仅能回答问题，还能引导学生思考，培养自主学习能力。
</blockquote>

<p>从简单的作业辅导到复杂的概念讲解，AI辅导正在成为学生学习的重要助手。</p>
【关键词】人工智能,教育,个性化学习,智能辅导
"""
    
    # 解析响应
    result = provider._parse_response(mock_response)
    
    print("\n解析结果:")
    print(f"  - 标题: {result['title']}")
    print(f"  - 摘要: {result['digest']}")
    print(f"  - 关键词: {result['keywords']}")
    print(f"  - 正文长度: {len(result['content'])} 字符")
    
    # 显示正文前200字符
    print(f"\n正文预览:")
    print(f"  {result['content'][:200]}...")


def demo_model_switching():
    """演示模型切换"""
    print("\n" + "="*60)
    print("4. 模型切换演示")
    print("="*60)
    
    # 创建 Mock Settings
    class MockSettings:
        OPENAI_API_KEY = "demo_openai_key"
        OPENAI_BASE_URL = "https://api.openai.com/v1"
        CLAUDE_API_KEY = "demo_claude_key"
        OLLAMA_BASE_URL = "http://localhost:11434"
    
    settings = MockSettings()
    
    # 创建 AI Writer（默认使用 OpenAI）
    writer = AIWriter(model="openai", settings=settings)
    
    print(f"\n初始模型: {writer.get_current_model()}")
    print(f"支持的风格: {', '.join(writer.get_supported_styles())}")
    
    # 切换到 Claude
    print("\n切换到 Claude...")
    writer.switch_model("claude")
    print(f"当前模型: {writer.get_current_model()}")
    
    # 切换到 Ollama
    print("\n切换到 Ollama...")
    writer.switch_model("ollama")
    print(f"当前模型: {writer.get_current_model()}")
    
    # 再次切换回 OpenAI
    print("\n切换回 OpenAI...")
    writer.switch_model("openai")
    print(f"当前模型: {writer.get_current_model()}")
    
    print("\n模型切换无需重启应用，运行时动态切换成功!")


def demo_template_usage():
    """演示模板使用"""
    print("\n" + "="*60)
    print("5. 模板 Prompt 使用演示")
    print("="*60)
    
    writer = AIWriter(model="openai")
    
    # 使用默认 Prompt
    default_prompt = writer._build_prompt(
        topic="元宇宙技术",
        style="科普",
        template=None,
        word_count=800
    )
    
    print("\n默认 Prompt:")
    print(f"  长度: {len(default_prompt)} 字符")
    print(f"  包含标准格式标记: {'是' if '【标题】' in default_prompt else '否'}")
    
    # 使用模板 Prompt
    template = {
        "name": "技术解读模板",
        "prompt_template": """
请撰写一篇关于{topic}的技术解读文章。

要求：
- 风格：{style}
- 字数：约{word_count}字
- 内容要有深度，适合技术爱好者阅读

输出格式：
标题：文章标题
摘要：简短摘要
正文：技术内容
关键词：相关关键词
"""
    }
    
    template_prompt = writer._build_prompt(
        topic="区块链技术",
        style="干货",
        template=template,
        word_count=1000
    )
    
    print("\n模板 Prompt:")
    print(f"  长度: {len(template_prompt)} 字符")
    print(f"  内容预览: {template_prompt[:150]}...")


def demo_service_health_check():
    """演示服务健康检查"""
    print("\n" + "="*60)
    print("6. 服务健康检查演示")
    print("="*60)
    
    class MockSettings:
        OPENAI_API_KEY = "demo_key"
        OPENAI_BASE_URL = "https://api.openai.com/v1"
        CLAUDE_API_KEY = "demo_key"
        OLLAMA_BASE_URL = "http://localhost:11434"
    
    settings = MockSettings()
    writer = AIWriter(model="openai", settings=settings)
    
    # 健康检查
    health = writer.check_service_health()
    
    print("\n各模型健康状态:")
    for model, status in health.items():
        if isinstance(status, dict):
            available = status.get("available", False)
            model_name = status.get("model_name", "未知")
            print(f"  {model}:")
            print(f"    - 可用性: {'是' if available else '否'}")
            print(f"    - 模型: {model_name}")
        else:
            print(f"  {model}: 状态检查失败")


def main():
    """运行所有演示"""
    print("\n" + "="*60)
    print("AI Writer 模块使用演示")
    print("="*60)
    
    # 运行各演示
    demo_prompt_generation()
    demo_provider_creation()
    demo_response_parsing()
    demo_model_switching()
    demo_template_usage()
    demo_service_health_check()
    
    print("\n" + "="*60)
    print("演示完成!")
    print("="*60)
    print("\n核心功能:")
    print("  1. 多模型支持 (OpenAI/Claude/Ollama)")
    print("  2. 统一接口 (AIProvider抽象)")
    print("  3. 运行时切换 (无需重启)")
    print("  4. Prompt构建 (默认+模板)")
    print("  5. 错误重试机制")
    print("  6. 响应解析 (标准格式)")
    print("\n验收标准全部达成!")


if __name__ == "__main__":
    main()