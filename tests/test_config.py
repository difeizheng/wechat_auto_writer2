"""
配置模块测试脚本
"""
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 清除可能存在的环境变量
for key in ['OPENAI_API_KEY', 'CLAUDE_API_KEY', 'WECHAT_APP_ID', 'DEFAULT_AI_MODEL']:
    if key in os.environ:
        del os.environ[key]

def test_import():
    """测试1：模块导入"""
    try:
        from config import Settings, get_settings, reload_settings
        print('[OK] 模块导入成功')
        return True
    except ImportError as e:
        print(f'[FAIL] 模块导入失败: {e}')
        return False

def test_init_with_ollama():
    """测试2：使用 Ollama 模型初始化"""
    os.environ['DEFAULT_AI_MODEL'] = 'ollama'
    
    from config import Settings
    try:
        settings = Settings()
        print('[OK] 使用 Ollama 模型时配置初始化成功')
        print(f'  - DEFAULT_AI_MODEL: {settings.DEFAULT_AI_MODEL}')
        print(f'  - DATABASE_PATH: {settings.DATABASE_PATH}')
        print(f'  - DEBUG_MODE: {settings.DEBUG_MODE}')
        return True
    except Exception as e:
        print(f'[FAIL] 配置初始化失败: {e}')
        return False

def test_is_ai_available():
    """测试3：is_ai_available 方法"""
    os.environ['DEFAULT_AI_MODEL'] = 'ollama'
    
    from config import Settings
    settings = Settings()
    
    print('[OK] is_ai_available 方法测试:')
    print(f'  - openai 可用: {settings.is_ai_available("openai")}')
    print(f'  - claude 可用: {settings.is_ai_available("claude")}')
    print(f'  - ollama 可用: {settings.is_ai_available("ollama")}')
    
    # 验证返回值
    assert settings.is_ai_available("openai") == False, "openai 应该不可用"
    assert settings.is_ai_available("claude") == False, "claude 应该不可用"
    assert settings.is_ai_available("ollama") == True, "ollama 应该可用"
    
    return True

def test_get_available_models():
    """测试4：get_available_models 方法"""
    os.environ['DEFAULT_AI_MODEL'] = 'ollama'
    
    from config import Settings
    settings = Settings()
    
    models = settings.get_available_models()
    print(f'[OK] get_available_models 方法: {models}')
    
    assert "ollama" in models, "ollama 应该在可用模型列表中"
    
    return True

def test_has_wechat_config():
    """测试5：has_wechat_config 方法"""
    os.environ['DEFAULT_AI_MODEL'] = 'ollama'
    
    from config import Settings
    settings = Settings()
    
    result = settings.has_wechat_config()
    print(f'[OK] has_wechat_config: {result}')
    
    assert result == False, "微信配置应该不可用"
    
    return True

def test_get_model_config():
    """测试6：get_model_config 方法"""
    os.environ['DEFAULT_AI_MODEL'] = 'ollama'
    
    from config import Settings
    settings = Settings()
    
    print('[OK] get_model_config 方法测试:')
    ollama_config = settings.get_model_config('ollama')
    print(f'  - ollama 配置: {ollama_config}')
    
    assert "base_url" in ollama_config, "ollama 配置应该包含 base_url"
    
    return True

def test_invalid_model_error():
    """测试7：无效模型名称错误处理"""
    os.environ['DEFAULT_AI_MODEL'] = 'invalid_model'
    
    from config import Settings
    try:
        settings = Settings()
        print('[FAIL] 应该抛出错误但没有')
        return False
    except ValueError as e:
        print('[OK] 无效模型名称正确抛出错误')
        return True

def test_missing_api_key_error():
    """测试8：缺少API密钥错误处理"""
    os.environ['DEFAULT_AI_MODEL'] = 'openai'
    
    from config import reload_settings
    try:
        reload_settings()
        print('[FAIL] 应该抛出错误但没有')
        return False
    except ValueError as e:
        print(f'[OK] 缺少API密钥正确抛出错误')
        return True

def test_singleton():
    """测试9：单例模式"""
    os.environ['DEFAULT_AI_MODEL'] = 'ollama'
    
    from config import get_settings, reload_settings
    reload_settings()
    
    settings1 = get_settings()
    settings2 = get_settings()
    
    is_singleton = settings1 is settings2
    print(f'[OK] 单例模式测试: {is_singleton}')
    
    return is_singleton

def test_reload():
    """测试10：重新加载"""
    os.environ['DEFAULT_AI_MODEL'] = 'ollama'
    
    from config import reload_settings
    settings = reload_settings()
    
    print(f'[OK] reload_settings 测试通过')
    return True

def test_repr():
    """测试11：__repr__ 方法"""
    os.environ['DEFAULT_AI_MODEL'] = 'ollama'
    
    from config import reload_settings
    settings = reload_settings()
    
    repr_str = repr(settings)
    print(f'[OK] __repr__: {repr_str}')
    
    # 验证敏感信息不在repr中
    assert "OPENAI_API_KEY" not in repr_str, "repr 不应包含API密钥"
    
    return True

def main():
    """运行所有测试"""
    print("=" * 60)
    print("配置模块测试")
    print("=" * 60)
    print()
    
    tests = [
        ("模块导入", test_import),
        ("Ollama初始化", test_init_with_ollama),
        ("is_ai_available", test_is_ai_available),
        ("get_available_models", test_get_available_models),
        ("has_wechat_config", test_has_wechat_config),
        ("get_model_config", test_get_model_config),
        ("无效模型错误", test_invalid_model_error),
        ("缺少API密钥错误", test_missing_api_key_error),
        ("单例模式", test_singleton),
        ("重新加载", test_reload),
        ("__repr__", test_repr),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n--- 测试: {name} ---")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f'[FAIL] 测试异常: {e}')
            results.append(False)
    
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过")
    print("=" * 60)
    
    if passed == total:
        print("\n[PASS] All tests passed! Config module works correctly.")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())