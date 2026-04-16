"""
文章生成页面
核心功能：AI生成 + 微信上传
整合 AI Writer 和微信 API，提供完整的文章创作流程
"""
import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import logging
import tempfile
import os
import traceback

from config import get_settings
from core.ai_writer import AIWriter, AIWriterError
from core.wechat_api import WeChatAPI, WeChatAPIError
from database import get_db_manager, Article, Template

# 配置日志
logger = logging.getLogger(__name__)


def show_article_generation():
    """显示文章生成页面
    
    页面布局：
    - 侧边栏：配置选项（模型、风格、模板、字数、封面图）
    - 主区域：主题输入、生成按钮、预览、编辑、保存/上传
    """
    st.title("📝 文章生成")
    
    # 初始化配置和数据库（添加错误处理）
    try:
        settings = get_settings()
    except ValueError as e:
        st.error(f"⚠️ 配置错误: {str(e)}")
        st.info("💡 请检查 .env 文件中的配置，或在「设置」页面进行配置")
        
        # 显示配置帮助
        with st.expander("配置帮助"):
            st.markdown("""
            **必需配置**：
            - 至少配置一个AI模型的API Key
            - OpenAI: `OPENAI_API_KEY=sk-xxx`
            - Claude: `CLAUDE_API_KEY=xxx`
            - SiliconFlow: `SILICONFLOW_API_KEY=xxx`
            - Ollama: 本地安装即可使用
            
            **SiliconFlow推荐**（国内用户）：
            - 注册: https://siliconflow.cn
            - 新用户有免费额度
            """)
        return
    
    try:
        db = get_db_manager()
    except Exception as e:
        st.error(f"⚠️ 数据库初始化失败: {str(e)}")
        logger.error(f"数据库错误: {e}")
        return
    
    # === 侧边栏配置 ===
    with st.sidebar:
        st.header("⚙️ 配置选项")
        
        # 1. AI模型选择
        available_models = settings.get_available_models()
        
        if not available_models:
            st.error("⚠️ 请先在设置页面配置AI模型API Key")
            st.info("提示：至少需要配置一个AI模型（OpenAI、Claude或Ollama）")
            return
        
        # 添加模型可用性检查提示
        model_status = {}
        for model in available_models:
            model_status[model] = settings.is_ai_available(model)
        
        # 显示模型可用状态
        model_options = []
        for model in available_models:
            if model_status[model]:
                status_icon = "✅"
            else:
                status_icon = "⚠️"
            model_options.append(f"{status_icon} {model}")
        
        selected_model_idx = st.selectbox(
            "选择AI模型",
            range(len(model_options)),
            format_func=lambda i: model_options[i],
            index=0,
            help="✅ 表示已配置可用，⚠️ 表示可能需要检查配置"
        )
        
        model = available_models[selected_model_idx]
        
        # 2. 文章风格
        style_options = ["科普", "故事", "干货", "互动", "资讯", "教程"]
        style = st.selectbox(
            "文章风格",
            style_options,
            index=0,
            help="不同风格会影响文章的写作方式和结构"
        )
        
        # 3. 模板选择（可选）
        try:
            templates = db.list_templates(active_only=True) or []
        except Exception as e:
            logger.warning(f"获取模板列表失败: {e}")
            templates = []
        
        template_names = ["不使用模板"] + [t.name for t in templates if t]
        
        template_idx = st.selectbox(
            "选择模板（可选）",
            range(len(template_names)),
            format_func=lambda i: template_names[i],
            index=0,
            help="模板可以提供预定义的写作结构"
        )
        
        selected_template: Optional[Template] = None
        if template_idx > 0 and templates and len(templates) > 0:
            # 确保索引有效
            template_index = template_idx - 1
            if template_index < len(templates):
                selected_template = templates[template_index]
                if selected_template:
                    # 显示模板信息
                    st.caption(f"分类: {selected_template.category or '未分类'}")
        
        # 4. 字数设置
        word_count = st.slider(
            "目标字数",
            min_value=500,
            max_value=2000,
            value=800,
            step=100,
            help="建议800-1200字，适合公众号阅读"
        )
        
        # 5. 封面图上传（微信上传必需）
        st.markdown("---")
        st.subheader("🖼️ 封面图（上传微信必需）")
        st.warning("⚠️ 微信公众号草稿必须有封面图才能上传")
        
        uploaded_image = st.file_uploader(
            "上传封面图",
            type=["jpg", "jpeg", "png"],
            help="建议尺寸：900x500像素，格式：jpg/png，小于2MB"
        )
        
        if uploaded_image:
            # 显示上传的图片
            st.image(uploaded_image, width=200)
            # 检查文件大小
            if uploaded_image.size > 2 * 1024 * 1024:
                st.warning("⚠️ 图片超过2MB，微信上传可能失败")
            else:
                st.success(f"✅ 封面图已上传（{uploaded_image.size // 1024}KB）")
        else:
            st.info("💡 请上传一张封面图（侧边栏）后再点击「上传到微信」")
    
    # === 主区域 ===
    
    # 1. 主题输入
    st.markdown("### 输入文章主题")
    topic = st.text_input(
        "文章主题/关键词",
        placeholder="例如：人工智能如何改变教育、健康饮食的重要性...",
        max_chars=200,
        help="输入您想要写作的主题，AI将根据此生成文章"
    )
    
    # 显示当前配置摘要
    if topic:
        st.caption(f"当前配置：模型={model} | 风格={style} | 字数≈{word_count}字")
    
    # 2. 生成按钮
    col_gen, col_clear = st.columns([3, 1])
    
    with col_gen:
        generate_btn = st.button(
            "🚀 生成文章",
            type="primary",
            disabled=not topic,
            use_container_width=True
        )
    
    with col_clear:
        if st.button("🗑️ 清除", use_container_width=True):
            if "generated_article" in st.session_state:
                del st.session_state.generated_article
            st.rerun()
    
    # 3. 生成逻辑
    if generate_btn:
        if not topic:
            st.warning("请输入文章主题")
        else:
            generate_article(topic, model, style, selected_template, word_count, settings)
    
    # === 显示生成的文章 ===
    if "generated_article" in st.session_state:
        article = st.session_state.generated_article
        # 确保article是有效的字典对象
        if article and isinstance(article, dict):
            display_article_editor(
                article,
                topic,
                style,
                model,
                selected_template,
                uploaded_image,
                settings,
                db
            )
        else:
            # 如果article无效，清除它
            if article is None:
                st.warning("生成的文章数据无效，请重新生成")
                del st.session_state.generated_article


def generate_article(
    topic: str,
    model: str,
    style: str,
    template: Optional[Template],
    word_count: int,
    settings: Any
):
    """生成文章
    
    Args:
        topic: 文章主题
        model: AI模型名称
        style: 文章风格
        template: 模板对象（可选）
        word_count: 目标字数
        settings: 配置对象
    """
    # 创建AI Writer
    try:
        writer = AIWriter(model=model, settings=settings)
    except Exception as e:
        st.error(f"初始化AI Writer失败: {str(e)}")
        logger.error(f"AI Writer初始化失败: {e}")
        return
    
    # 显示生成进度
    progress_bar = st.progress(0, text="正在准备生成...")
    
    with st.spinner(f"正在使用 {model} 生成文章..."):
        try:
            # 准备模板数据（如果有）
            template_data = None
            if template:
                template_data = {
                    "prompt_template": template.prompt_template,
                    "name": template.name,
                    "category": template.category
                }
            
            progress_bar.progress(30, text="正在调用AI模型...")
            
            # 生成文章
            result = writer.generate_article(
                topic=topic,
                style=style,
                template=template_data,
                word_count=word_count,
                max_retries=3
            )
            
            progress_bar.progress(100, text="生成完成！")
            
            # 保存到session state
            st.session_state.generated_article = result
            
            # 显示成功消息
            st.success(f"✅ 文章生成成功！使用模型: {result.get('model', model)}")
            
            # 显示生成统计
            content_length = len(result.get("content", ""))
            st.caption(f"标题: {result.get('title', '未命名')} | 内容长度: {content_length}字符")
            
            logger.info(f"文章生成成功: topic={topic}, model={model}, style={style}")
            
        except AIWriterError as e:
            progress_bar.empty()
            st.error(f"❌ 生成失败: {str(e)}")
            logger.error(f"AI生成失败: {e}")
            
            # 显示可能的解决方案
            if "API" in str(e):
                st.info("💡 建议：请检查API Key是否正确配置，或尝试切换其他模型")
            elif "timeout" in str(e).lower():
                st.info("💡 建议：模型响应时间过长，请稍后重试或增加timeout参数")
            
        except Exception as e:
            progress_bar.empty()
            st.error(f"❌ 生成失败: {str(e)}")
            logger.error(f"未知错误: {e}")


def display_article_editor(
    article: Dict[str, Any],
    topic: str,
    style: str,
    model: str,
    template: Optional[Template],
    uploaded_image: Any,
    settings: Any,
    db: Any
):
    """显示文章编辑器和操作按钮
    
    Args:
        article: 生成的文章数据
        topic: 文章主题
        style: 文章风格
        model: AI模型
        template: 模板对象
        uploaded_image: 上传的封面图
        settings: 配置对象
        db: 数据库管理器
    """
    # 空值检查
    if not article or not isinstance(article, dict):
        st.error("文章数据无效")
        return
    
    st.markdown("---")
    
    # === 标题显示 ===
    title = article.get('title', '') or '未命名文章'
    
    # 显示标题长度提示
    title_len = len(title)
    if title_len > 64:
        st.warning(f"⚠️ 标题长度 {title_len} 字符，超过微信限制（64字符）。上传时会自动截断为：{title[:64]}")
        st.subheader(f"📄 {title[:64]}...")
    elif title_len < 5:
        st.warning(f"⚠️ 标题长度 {title_len} 字符，少于微信最小要求（5字符）。上传时会自动补充为「文章1」")
        st.subheader(f"📄 {title}")
    else:
        st.subheader(f"📄 {title}")
        st.caption(f"标题长度：{title_len} 字符（符合要求）")
    
    # === 摘要显示 ===
    digest = article.get("digest", "") or ""
    if digest:
        digest_len = len(digest)
        if digest_len > 120:
            st.warning(f"⚠️ 摘要长度 {digest_len} 字符，超过微信限制（120字符）。上传时会自动截断")
            st.info(f"📝 **摘要**: {digest[:120]}...")
        else:
            st.info(f"📝 **摘要**: {digest}")
    
    # === 关键词显示 ===
    keywords = article.get("keywords", []) or []
    if keywords:
        st.caption(f"关键词: {', '.join(keywords)}")
    
    # === 内容预览（Markdown渲染） ===
    st.markdown("---")
    st.markdown("**📖 文章内容预览：**")
    
    # 内容容器
    content = article.get("content", "") or ""
    
    # 使用tabs切换预览和原始内容
    preview_tab, raw_tab = st.tabs(["渲染预览", "原始HTML"])
    
    with preview_tab:
        # 渲染HTML内容（公众号格式）
        st.markdown(content, unsafe_allow_html=True)
    
    with raw_tab:
        # 显示原始HTML代码
        st.code(content, language="html")
    
    # === 编辑区域 ===
    st.markdown("---")
    st.markdown("**✏️ 编辑内容（可选）：**")
    
    # 标题编辑
    edited_title = st.text_input(
        "标题",
        value=title[:64] if len(title) > 64 else title,  # 预截断显示
        max_chars=64,
        help="公众号标题要求：最少5字符，最多64字符"
    )
    
    # 检查编辑后的标题长度
    if len(edited_title) < 5:
        st.warning("⚠️ 标题少于5字符，上传微信时会自动补充")
    
    # 摘要编辑
    edited_digest = st.text_input(
        "摘要",
        value=digest,
        max_chars=120,
        help="公众号摘要最多120字符"
    )
    
    # 内容编辑（大文本框）
    edited_content = st.text_area(
        "内容（HTML格式）",
        value=content,
        height=400,
        help="可以修改生成的HTML内容"
    )
    
    # 更新session state中的编辑内容
    st.session_state.edited_article = {
        "title": edited_title,
        "content": edited_content,
        "digest": edited_digest
    }
    
    # === 操作按钮 ===
    st.markdown("---")
    st.markdown("**📤 操作选项：**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 保存到本地数据库
        if st.button("💾 保存到本地", type="secondary", use_container_width=True):
            save_to_local(
                edited_title,
                edited_content,
                edited_digest,
                topic,
                style,
                model,
                template,
                db,
                uploaded_image  # 传入封面图
            )
    
    with col2:
        # 上传到微信草稿箱
        if st.button("📤 上传到微信", type="primary", use_container_width=True):
            upload_to_wechat(
                edited_title,
                edited_content,
                edited_digest,
                uploaded_image,
                settings
            )
    
    with col3:
        # 复制内容
        if st.button("📋 复制内容", type="secondary", use_container_width=True):
            st.code(edited_content, language="html")
            st.info("内容已显示在上方代码框中，可手动复制")


def save_to_local(
    title: str,
    content: str,
    digest: str,
    topic: str,
    style: str,
    model: str,
    template: Optional[Template],
    db: Any,
    uploaded_image: Any = None
):
    """保存文章到本地数据库
    
    Args:
        title: 文章标题
        content: 文章内容
        digest: 文章摘要
        topic: 文章主题
        style: 文章风格
        model: AI模型
        template: 模板对象
        db: 数据库管理器
        uploaded_image: 封面图（可选）
    """
    try:
        # 处理封面图：如果有上传的图片，保存到本地
        cover_image_path = ""
        if uploaded_image:
            # 创建封面图保存目录
            covers_dir = Path("data/covers")
            covers_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = uploaded_image.name.split('.')[-1] if '.' in uploaded_image.name else 'jpg'
            cover_filename = f"cover_{timestamp}_{hash(title) % 10000}.{file_extension}"
            cover_path = covers_dir / cover_filename
            
            # 保存封面图
            with open(cover_path, "wb") as f:
                f.write(uploaded_image.getvalue())
            
            cover_image_path = str(cover_path)
            logger.info(f"封面图已保存: {cover_image_path}")
        
        # 创建Article对象
        new_article = Article(
            title=title,
            content=content,
            digest=digest,
            style=style,
            topic=topic,
            ai_model=model,
            template_id=template.id if template else None,
            status="draft",
            cover_image_path=cover_image_path
        )
        
        # 保存到数据库
        article_id = db.save_article(new_article)
        
        st.success(f"✅ 已保存到本地数据库，文章ID: {article_id}")
        if cover_image_path:
            st.caption(f"封面图已保存: {cover_filename}")
        st.info("💡 可以在「历史记录」页面查看和管理已保存的文章")
        
        logger.info(f"文章保存成功: ID={article_id}, title={title}, cover={cover_image_path}")
        
    except Exception as e:
        st.error(f"❌ 保存失败: {str(e)}")
        logger.error(f"文章保存失败: {e}")


def upload_to_wechat(
    title: str,
    content: str,
    digest: str,
    uploaded_image: Any,
    settings: Any
):
    """上传文章到微信公众号草稿箱
    
    Args:
        title: 文章标题
        content: 文章内容（HTML）
        digest: 文章摘要
        uploaded_image: 封面图文件（必需）
        settings: 配置对象
    """
    # 检查微信配置
    if not settings.has_wechat_config():
        st.error("⚠️ 请先在设置页面配置微信公众号App ID和App Secret")
        st.info("💡 提示：需要在 .env 文件中设置 WECHAT_APP_ID 和 WECHAT_APP_SECRET")
        return
    
    # 检查标题和内容
    if not title:
        st.error("文章标题不能为空")
        return
    
    if not content:
        st.error("文章内容不能为空")
        return
    
    # ⚠️ 重要：微信公众号草稿必须有封面图
    if not uploaded_image:
        st.error("⚠️ 微信公众号草稿必须包含封面图！")
        st.info("💡 请在侧边栏上传一张封面图（建议尺寸：900x500像素，格式：jpg/png）")
        st.warning("提示：微信要求每篇图文消息都必须有封面图")
        return
    
    # 创建微信API实例
    try:
        api = WeChatAPI(
            app_id=settings.WECHAT_APP_ID,
            app_secret=settings.WECHAT_APP_SECRET
        )
    except Exception as e:
        st.error(f"初始化微信API失败: {str(e)}")
        return
    
    # 上传进度
    progress_bar = st.progress(0, text="正在连接微信公众号...")
    
    try:
        # 1. 测试连接
        progress_bar.progress(20, text="正在验证账号...")
        test_result = api.test_connection()
        
        if not test_result.get("success"):
            st.error(f"微信账号验证失败: {test_result.get('message')}")
            progress_bar.empty()
            return
        
        progress_bar.progress(40, text="正在上传封面图...")
        
        # 2. 先上传封面图获取media_id
        thumb_media_id = None
        
        # 保存上传的图片到临时文件
        file_extension = uploaded_image.name.split('.')[-1] if '.' in uploaded_image.name else 'jpg'
        
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f".{file_extension}"
        ) as tmp_file:
            tmp_file.write(uploaded_image.getvalue())
            tmp_path = tmp_file.name
        
        try:
            image_result = api.upload_image(tmp_path)
            thumb_media_id = image_result.get("media_id")
            
            if not thumb_media_id:
                st.error("封面图上传失败，未获取到media_id")
                progress_bar.empty()
                return
            
            st.caption(f"✅ 封面图已上传，media_id: {thumb_media_id}")
            logger.info(f"封面图上传成功: media_id={thumb_media_id}")
            
        except WeChatAPIError as e:
            st.error(f"封面图上传失败: {e.message}")
            logger.error(f"封面图上传失败: code={e.code}, message={e.message}")
            progress_bar.empty()
            return
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        progress_bar.progress(70, text="正在上传文章到草稿箱...")
        
        # 3. 构造文章数据（包含封面图）
        articles_data = [{
            "title": title,
            "author": "AI助手",
            "digest": digest,
            "content": content,
            "thumb_media_id": thumb_media_id,  # 必须包含封面图
            "need_open_comment": 0,
            "only_fans_can_comment": 0
        }]
        
        # 4. 上传草稿
        result = api.add_draft(articles_data)
        media_id = result.get("media_id")
        
        progress_bar.progress(100, text="上传完成！")
        
        # 显示成功信息
        st.success(f"✅ 上传成功！草稿ID: {media_id}")
        st.balloons()
        st.info("💡 请在微信公众号后台查看和管理此草稿")
        
        # 显示草稿链接提示
        st.caption("提示：登录 mp.weixin.qq.com 进入草稿箱管理")
        
        logger.info(f"文章上传微信成功: media_id={media_id}, title={title}")
        
    except WeChatAPIError as e:
        progress_bar.empty()
        st.error(f"❌ 微信API错误 [{e.code}]: {e.message}")
        logger.error(f"微信API错误: code={e.code}, message={e.message}")
        
        # 显示错误详情和解决方案
        error_solutions = {
            40001: "AppSecret错误或不属于公众平台，请检查配置",
            40014: "不合法的access_token，请检查AppID和AppSecret",
            42001: "access_token已过期，请刷新后重试",
            45009: "接口调用超过限制，请稍后重试",
            45066: "草稿箱功能未开启，请在公众号后台启用",
            45067: "文章需要封面图，请上传封面图后重试",
            45068: "标题不合法，请检查标题长度（最长64字符）",
            45069: "内容不合法，请检查内容是否包含违规信息",
            87009: "内容包含违法违规内容，请修改后重试",
        }
        
        solution = error_solutions.get(e.code, "请检查配置和内容是否正确")
        st.info(f"💡 解决方案：{solution}")
        
    except Exception as e:
        progress_bar.empty()
        st.error(f"❌ 上传失败: {str(e)}")
        logger.error(f"上传微信失败: {e}")
        st.info("💡 请检查网络连接和配置是否正确")