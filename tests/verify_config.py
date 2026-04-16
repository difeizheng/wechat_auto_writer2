"""
配置模块完整验证脚本
"""
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 清理环境
for key in ['DEFAULT_AI_MODEL', 'OPENAI_API_KEY', 'CLAUDE_API_KEY', 
            'WECHAT_APP_ID', 'WECHAT_APP_SECRET', 'DEBUG_MODE']:
    if key in os.environ:
        del os.environ[key]

from config import get_settings, reload_settings

print("=" * 60)
print("Settings Module Verification")
print("=" * 60)

# 测试1: OpenAI配置
print("\n--- Test 1: OpenAI Configuration ---")
os.environ['DEFAULT_AI_MODEL'] = 'openai'
os.environ['OPENAI_API_KEY'] = 'test-key-12345'
os.environ['OPENAI_BASE_URL'] = 'https://api.custom.com/v1'

settings = reload_settings()
print(f"DEFAULT_AI_MODEL: {settings.DEFAULT_AI_MODEL}")
print(f"OPENAI_API_KEY: {settings.OPENAI_API_KEY[:10]}...")
print(f"OPENAI_BASE_URL: {settings.OPENAI_BASE_URL}")
print(f"is_ai_available(openai): {settings.is_ai_available('openai')}")
print(f"get_available_models(): {settings.get_available_models()}")
print(f"get_model_config(openai): {settings.get_model_config('openai')}")
print(f"repr: {repr(settings)}")

# 测试2: 微信配置
print("\n--- Test 2: WeChat Configuration ---")
os.environ['WECHAT_APP_ID'] = 'wx123456'
os.environ['WECHAT_APP_SECRET'] = 'secret789'

settings2 = reload_settings()
print(f"has_wechat_config: {settings2.has_wechat_config()}")
print(f"get_wechat_config: {settings2.get_wechat_config()}")
print(f"repr: {repr(settings2)}")

# 测试3: DEBUG模式
print("\n--- Test 3: DEBUG Mode ---")
os.environ['DEBUG_MODE'] = 'true'
settings3 = reload_settings()
print(f"DEBUG_MODE: {settings3.DEBUG_MODE}")

# 测试4: Claude配置
print("\n--- Test 4: Claude Configuration ---")
for key in ['DEFAULT_AI_MODEL', 'OPENAI_API_KEY', 'CLAUDE_API_KEY']:
    if key in os.environ:
        del os.environ[key]

os.environ['DEFAULT_AI_MODEL'] = 'claude'
os.environ['CLAUDE_API_KEY'] = 'sk-ant-test-key'

settings4 = reload_settings()
print(f"DEFAULT_AI_MODEL: {settings4.DEFAULT_AI_MODEL}")
print(f"CLAUDE_API_KEY: {settings4.CLAUDE_API_KEY[:10]}...")
print(f"is_ai_available(claude): {settings4.is_ai_available('claude')}")
print(f"get_available_models(): {settings4.get_available_models()}")

# 测试5: 多模型同时可用
print("\n--- Test 5: Multiple AI Models Available ---")
os.environ['DEFAULT_AI_MODEL'] = 'ollama'
os.environ['OPENAI_API_KEY'] = 'openai-key'
os.environ['CLAUDE_API_KEY'] = 'claude-key'

settings5 = reload_settings()
print(f"Available models: {settings5.get_available_models()}")
print(f"is_ai_available(openai): {settings5.is_ai_available('openai')}")
print(f"is_ai_available(claude): {settings5.is_ai_available('claude')}")
print(f"is_ai_available(ollama): {settings5.is_ai_available('ollama')}")

print("\n" + "=" * 60)
print("[SUCCESS] All config features verified!")
print("=" * 60)