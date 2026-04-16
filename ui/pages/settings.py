"""
设置页面
管理AI模型配置、微信公众号账号设置
支持配置保存和连接测试
"""
import streamlit as st
import os
from pathlib import Path
from typing import Optional
import logging

from config import get_settings
from core.ai_writer import AIWriter
from core.wechat_api import WeChatAPI, WeChatAPIError
from database import get_db_manager

# 配置日志
logger = logging.getLogger(__name__)


def show_settings():
    """显示设置页面
    
    功能：
    - AI模型配置（OpenAI、Claude、Ollama）
    - 微信公众号配置（App ID、App Secret）
    - 配置保存和测试
    """
    st.title("⚙️ 设置")
    
    settings = get_settings()
    db = get_db_manager()
    
    # === AI模型配置 ===
    with st.expander("🤖 AI模型配置", expanded=True):
        st.markdown("""
        配置AI模型API密钥，用于文章生成。
        
        **提示**：
        - OpenAI: 需配置API Key，可自定义Base URL（支持第三方代理）
        - Claude: 需配置Anthropic API Key
        - Ollama: 需本地运行Ollama服务（默认localhost:11434）
        """)
        
        # OpenAI配置
        st.subheader("OpenAI")
        
        current_openai_key = settings.OPENAI_API_KEY
        openai_key_masked = "已配置" if current_openai_key else "未配置"
        
        openai_key = st.text_input(
            "API Key",
            value="",
            type="password",
            placeholder="sk-..." if not current_openai_key else openai_key_masked,
            help="OpenAI API密钥"
        )
        
        openai_base = st.text_input(
            "Base URL",
            value=settings.OPENAI_BASE_URL,
            help="API基础地址，可使用第三方代理"
        )
        
        # OpenAI测试按钮
        if st.button("测试OpenAI连接", key="test_openai"):
            test_ai_connection("openai", openai_key or current_openai_key, openai_base)
        
        st.markdown("---")
        
        # Claude配置
        st.subheader("Claude (Anthropic)")
        
        current_claude_key = settings.CLAUDE_API_KEY
        claude_key_masked = "已配置" if current_claude_key else "未配置"
        
        claude_key = st.text_input(
            "API Key",
            value="",
            type="password",
            placeholder="sk-ant-..." if not current_claude_key else claude_key_masked,
            help="Anthropic API密钥"
        )
        
        # Claude测试按钮
        if st.button("测试Claude连接", key="test_claude"):
            test_ai_connection("claude", claude_key or current_claude_key)
        
        st.markdown("---")
        
        # Ollama配置
        st.subheader("Ollama (本地模型)")
        
        ollama_url = st.text_input(
            "Ollama URL",
            value=settings.OLLAMA_BASE_URL,
            help="本地Ollama服务地址"
        )
        
        # Ollama测试按钮
        if st.button("测试Ollama连接", key="test_ollama"):
            test_ai_connection("ollama", None, ollama_url)
        
        st.markdown("---")
        
        # 默认模型选择
        st.subheader("默认模型")
        
        available_models = settings.get_available_models()
        default_model = st.selectbox(
            "默认AI模型",
            available_models if available_models else ["openai", "claude", "ollama"],
            index=available_models.index(settings.DEFAULT_AI_MODEL) if settings.DEFAULT_AI_MODEL in available_models else 0,
            help="选择默认使用的AI模型"
        )
    
    # === 微信公众号配置 ===
    with st.expander("📱 微信公众号配置", expanded=False):
        st.markdown("""
        配置微信公众号账号信息，用于上传文章到草稿箱。
        
        **获取方式**：
        1. 登录 mp.weixin.qq.com
        2. 进入「设置」-「基本配置」
        3. 获取AppID和AppSecret
        """)
        
        st.subheader("公众号信息")
        
        current_appid = settings.WECHAT_APP_ID
        appid_masked = "已配置" if current_appid else "未配置"
        
        wechat_appid = st.text_input(
            "App ID",
            value="",
            placeholder="wx..." if not current_appid else appid_masked,
            help="微信公众号AppID"
        )
        
        current_secret = settings.WECHAT_APP_SECRET
        secret_masked = "已配置" if current_secret else "未配置"
        
        wechat_secret = st.text_input(
            "App Secret",
            value="",
            type="password",
            placeholder="请输入App Secret" if not current_secret else secret_masked,
            help="微信公众号AppSecret"
        )
        
        # 微信测试按钮
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("测试微信连接", type="secondary"):
                test_wechat_connection(
                    wechat_appid or current_appid,
                    wechat_secret or current_secret
                )
        
        with col2:
            if st.button("刷新Token", type="secondary"):
                refresh_wechat_token(
                    wechat_appid or current_appid,
                    wechat_secret or current_secret
                )
        
        # 显示Token状态
        if settings.has_wechat_config():
            show_token_status(wechat_appid or current_appid, wechat_secret or current_secret)
    
    # === 应用配置 ===
    with st.expander("🔧 应用配置", expanded=False):
        st.subheader("应用设置")
        
        debug_mode = st.checkbox(
            "调试模式",
            value=settings.DEBUG_MODE,
            help="开启调试模式，显示更多日志信息"
        )
        
        database_path = st.text_input(
            "数据库路径",
            value=settings.DATABASE_PATH,
            help="本地数据库文件路径"
        )
    
    # === 保存配置 ===
    st.markdown("---")
    st.subheader("💾 保存配置")
    
    st.warning("""
    ⚠️ **重要提示**：
    配置将保存到 `.env` 文件或环境变量。
    保存后需要重启应用才能生效（部分配置）。
    """)
    
    if st.button("保存配置到.env文件", type="primary"):
        save_config_to_env(
            openai_key, openai_base,
            claude_key,
            ollama_url,
            default_model,
            wechat_appid, wechat_secret,
            debug_mode, database_path
        )
    
    # === 当前配置状态 ===
    st.markdown("---")
    show_current_config_status(settings)


def test_ai_connection(model: str, api_key: Optional[str], base_url: Optional[str] = None):
    """测试AI模型连接
    
    Args:
        model: 模型名称
        api_key: API密钥
        base_url: Base URL（可选）
    """
    with st.spinner(f"正在测试 {model} 连接..."):
        try:
            settings = get_settings()
            
            # 创建临时配置
            temp_settings = type('TempSettings', (), {
                'OPENAI_API_KEY': api_key or settings.OPENAI_API_KEY,
                'OPENAI_BASE_URL': base_url or settings.OPENAI_BASE_URL,
                'CLAUDE_API_KEY': api_key or settings.CLAUDE_API_KEY,
                'OLLAMA_BASE_URL': base_url or settings.OLLAMA_BASE_URL,
            })()
            
            writer = AIWriter(model=model, settings=temp_settings)
            
            # 测试连接
            if model == "openai":
                # 使用健康检查
                health = writer.check_service_health()
                if health.get(model, {}).get("available"):
                    st.success(f"✅ OpenAI连接成功！模型可用")
                    st.caption(f"模型: {health[model].get('model_name')}")
                else:
                    error = health.get(model, {}).get("error", "未知错误")
                    st.error(f"❌ OpenAI连接失败: {error}")
            
            elif model == "claude":
                health = writer.check_service_health()
                if health.get(model, {}).get("available"):
                    st.success(f"✅ Claude连接成功！模型可用")
                else:
                    st.error(f"❌ Claude连接失败: API Key无效")
            
            elif model == "ollama":
                health = writer.check_service_health()
                if health.get(model, {}).get("available"):
                    st.success(f"✅ Ollama连接成功！服务可用")
                    st.caption(f"地址: {base_url or settings.OLLAMA_BASE_URL}")
                else:
                    st.error(f"❌ Ollama连接失败: 无法连接到服务")
                    st.info("💡 提示: 请确保Ollama服务正在运行（ollama serve）")
            
        except Exception as e:
            st.error(f"❌ 连接测试失败: {str(e)}")
            logger.error(f"AI连接测试失败: model={model}, error={e}")


def test_wechat_connection(app_id: str, app_secret: str):
    """测试微信公众号连接
    
    Args:
        app_id: App ID
        app_secret: App Secret
    """
    if not app_id or not app_secret:
        st.warning("请输入App ID和App Secret")
        return
    
    with st.spinner("正在测试微信连接..."):
        try:
            api = WeChatAPI(app_id=app_id, app_secret=app_secret)
            result = api.test_connection()
            
            if result.get("success"):
                st.success(f"✅ 微信公众号连接成功！")
                st.caption(f"App ID: {result.get('app_id')}")
                st.caption(f"Token预览: {result.get('token_preview')}")
                
                # 显示缓存信息
                cache_info = result.get("cache_info")
                if cache_info:
                    st.caption(f"Token有效期至: {cache_info.get('expires_at')}")
            else:
                st.error(f"❌ 连接失败: {result.get('message')}")
                if result.get("error_code"):
                    st.caption(f"错误码: {result.get('error_code')}")
            
        except WeChatAPIError as e:
            st.error(f"❌ 微信API错误: {e.message}")
            st.caption(f"错误码: {e.code}")
        except Exception as e:
            st.error(f"❌ 连接测试失败: {str(e)}")


def refresh_wechat_token(app_id: str, app_secret: str):
    """刷新微信Token
    
    Args:
        app_id: App ID
        app_secret: App Secret
    """
    if not app_id or not app_secret:
        st.warning("请输入App ID和App Secret")
        return
    
    with st.spinner("正在刷新Token..."):
        try:
            api = WeChatAPI(app_id=app_id, app_secret=app_secret)
            token = api.refresh_token()
            
            st.success(f"✅ Token已刷新！")
            st.caption(f"新Token预览: {token[:10]}...")
            
            # 显示新Token状态
            status = api.get_token_status()
            st.caption(f"有效期至: {status.get('expires_at')}")
            
        except Exception as e:
            st.error(f"❌ Token刷新失败: {str(e)}")


def show_token_status(app_id: str, app_secret: str):
    """显示Token状态
    
    Args:
        app_id: App ID
        app_secret: App Secret
    """
    try:
        api = WeChatAPI(app_id=app_id, app_secret=app_secret)
        status = api.get_token_status()
        
        if status.get("has_cache"):
            remaining = status.get("remaining_seconds", 0)
            if remaining > 300:
                st.info(f"🟢 Token有效，剩余时间: {int(remaining/60)}分钟")
            elif remaining > 0:
                st.warning(f"🟡 Token即将过期，剩余时间: {int(remaining)}秒")
            else:
                st.error("🔴 Token已过期，需要刷新")
        else:
            st.info("⚪ 暂无Token缓存，将在首次使用时获取")
        
    except Exception as e:
        logger.warning(f"获取Token状态失败: {e}")


def save_config_to_env(
    openai_key: str,
    openai_base: str,
    claude_key: str,
    ollama_url: str,
    default_model: str,
    wechat_appid: str,
    wechat_secret: str,
    debug_mode: bool,
    database_path: str
):
    """保存配置到.env文件
    
    Args:
        各配置项参数
    """
    try:
        # 获取当前配置
        settings = get_settings()
        
        # 构建配置内容
        config_lines = [
            "# WeChat Auto Writer 配置文件",
            "# 请勿将此文件提交到公共仓库",
            "",
            "# === AI模型配置 ===",
            f"OPENAI_API_KEY={openai_key if openai_key else settings.OPENAI_API_KEY}",
            f"OPENAI_BASE_URL={openai_base}",
            f"CLAUDE_API_KEY={claude_key if claude_key else settings.CLAUDE_API_KEY}",
            f"OLLAMA_BASE_URL={ollama_url}",
            f"DEFAULT_AI_MODEL={default_model}",
            "",
            "# === 微信公众号配置 ===",
            f"WECHAT_APP_ID={wechat_appid if wechat_appid else settings.WECHAT_APP_ID}",
            f"WECHAT_APP_SECRET={wechat_secret if wechat_secret else settings.WECHAT_APP_SECRET}",
            "",
            "# === 应用配置 ===",
            f"DEBUG_MODE={str(debug_mode).lower()}",
            f"DATABASE_PATH={database_path}",
        ]
        
        # 写入.env文件
        env_path = Path(".env")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(config_lines))
        
        st.success(f"✅ 配置已保存到 {env_path}")
        st.info("💡 重启应用以加载新配置")
        
        # 显示保存的配置摘要
        st.markdown("**配置摘要：**")
        st.caption(f"- OpenAI: {'已配置' if (openai_key or settings.OPENAI_API_KEY) else '未配置'}")
        st.caption(f"- Claude: {'已配置' if (claude_key or settings.CLAUDE_API_KEY) else '未配置'}")
        st.caption(f"- Ollama: {ollama_url}")
        st.caption(f"- 微信: {'已配置' if (wechat_appid or settings.WECHAT_APP_ID) else '未配置'}")
        st.caption(f"- 默认模型: {default_model}")
        
        logger.info(f"配置已保存到 {env_path}")
        
    except Exception as e:
        st.error(f"❌ 保存失败: {str(e)}")
        logger.error(f"配置保存失败: {e}")


def show_current_config_status(settings):
    """显示当前配置状态
    
    Args:
        settings: 配置对象
    """
    st.subheader("📊 当前配置状态")
    
    # 创建状态表格
    status_data = {
        "配置项": [
            "OpenAI API Key",
            "Claude API Key",
            "Ollama服务",
            "微信公众号",
            "默认模型"
        ],
        "状态": [
            "✅ 已配置" if settings.OPENAI_API_KEY else "❌ 未配置",
            "✅ 已配置" if settings.CLAUDE_API_KEY else "❌ 未配置",
            "🟡 需本地服务",
            "✅ 已配置" if settings.has_wechat_config() else "❌ 未配置",
            settings.DEFAULT_AI_MODEL
        ],
        "详情": [
            f"Base URL: {settings.OPENAI_BASE_URL}",
            "Anthropic API",
            f"地址: {settings.OLLAMA_BASE_URL}",
            f"App ID: {settings.WECHAT_APP_ID[:8]}..." if settings.WECHAT_APP_ID else "未配置",
            f"可用模型: {', '.join(settings.get_available_models())}"
        ]
    }
    
    st.dataframe(status_data, use_container_width=True)
    
    # 可用模型提示
    available_models = settings.get_available_models()
    if not available_models:
        st.warning("⚠️ 暂无可用的AI模型，请至少配置一个")
    else:
        st.success(f"✅ 可用模型: {', '.join(available_models)}")