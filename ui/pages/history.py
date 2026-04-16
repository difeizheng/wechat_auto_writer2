"""
历史记录页面
展展示已生成文章的历史，支持查看、编辑、删除、上传微信操作
整合数据库管理，提供完整的文章管理功能
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path
import logging
import os

from database import get_db_manager, Article, ArticleStatus
from config import get_settings
from core.wechat_api import WeChatAPI, WeChatAPIError

# 配置日志
logger = logging.getLogger(__name__)


def show_history():
    """显示历史记录页面
    
    功能：
    - 查看已生成的文章列表
    - 状态筛选（草稿/已上传/已发布）
    - 搜索和分页
    - 查看、编辑、删除文章
    """
    st.title("📚 历史记录")
    
    db = get_db_manager()
    
    # === 筛选条件 ===
    st.subheader("🔍 筛选条件")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # 状态筛选
        status_options = ["全部", ArticleStatus.DRAFT, ArticleStatus.UPLOADED, ArticleStatus.PUBLISHED]
        status_filter = st.selectbox("状态", status_options, index=0)
    
    with col2:
        # 风格筛选
        style_options = ["全部", "科普", "故事", "干货", "互动", "资讯", "教程"]
        style_filter = st.selectbox("风格", style_options, index=0)
    
    with col3:
        # 日期范围
        date_range = st.date_input(
            "日期范围",
            [datetime.now() - timedelta(days=30), datetime.now()],
            help="选择起止日期筛选文章"
        )
    
    with col4:
        # 搜索关键词
        search_keyword = st.text_input(
            "搜索标题",
            placeholder="输入关键词...",
            help="按标题关键词搜索"
        )
    
    # === 文章列表 ===
    st.markdown("---")
    st.subheader("📄 文章列表")
    
    # 查询参数
    query_status = None if status_filter == "全部" else status_filter
    query_style = None if style_filter == "全部" else style_filter
    
    # 获取文章列表
    try:
        articles = db.list_articles(
            status=query_status,
            style=query_style,
            limit=50,
            offset=0,
            order_by="created_at",
            order_desc=True
        )
        
        # 搜索过滤
        if search_keyword:
            articles = [a for a in articles if search_keyword.lower() in a.title.lower()]
        
        # 日期过滤（简化处理）
        if len(date_range) == 2:
            start_date = date_range[0]
            end_date = date_range[1]
            articles = [a for a in articles 
                       if a.created_at and 
                       start_date <= a.created_at.date() <= end_date]
        
    except Exception as e:
        st.error(f"加载文章列表失败: {str(e)}")
        logger.error(f"加载文章列表失败: {e}")
        return
    
    # 显示统计信息
    total_count = db.count_articles(status=query_status, style=query_style)
    st.caption(f"共找到 {len(articles)} 条记录（总数: {total_count}）")
    
    # 文章列表展示
    if articles:
        for article in articles:
            display_article_item(article, db)
    else:
        st.info("暂无文章记录")
        st.caption("提示：在「文章生成」页面创建新文章")
    
    # === 数据库信息 ===
    st.markdown("---")
    show_database_info(db)


def display_article_item(article: Article, db):
    """显示单篇文章
    
    Args:
        article: 文章对象
        db: 数据库管理器
    """
    # 状态图标映射
    status_icons = {
        ArticleStatus.DRAFT: "📝",
        ArticleStatus.UPLOADED: "📤",
        ArticleStatus.PUBLISHED: "✅"
    }
    
    status_icon = status_icons.get(article.status, "📄")
    
    # 检查是否处于编辑模式
    is_editing = st.session_state.get("edit_article_id") == article.id
    
    with st.expander(
        f"{status_icon} {article.title} - {article.created_at.strftime('%Y-%m-%d %H:%M') if article.created_at else '未知时间'}",
        expanded=is_editing  # 编辑时自动展开
    ):
        # 如果处于编辑模式，显示编辑界面
        if is_editing:
            show_edit_interface(article, db)
        else:
            # 正常显示模式
            # 文章信息
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 基本信息
                st.markdown(f"""
                **摘要**: {article.digest or '无摘要'}
                
                **主题**: {article.topic or '未知'}
                
                **风格**: {article.style or '未知'}
                
                **AI模型**: {article.ai_model or '未知'}
                """)
                
                # 状态和微信信息
                st.caption(f"状态: {article.status}")
                if article.wechat_draft_id:
                    st.caption(f"微信草稿ID: {article.wechat_draft_id}")
                
# 显示封面图信息
                if article.cover_image_path:
                    st.caption(f"封面图: ✅ 已保存")
                    # 尝试显示封面图预览
                    try:
                        if os.path.exists(article.cover_image_path):
                            st.image(article.cover_image_path, width=100)
                    except Exception:
                        pass
                else:
                    st.caption("封面图: ❌ 未上传")
                    # 快速上传封面图按钮
                    if st.button("📷 添加封面图", key=f"quick_add_cover_{article.id}"):
                        st.session_state.quick_upload_cover_id = article.id
            
            with col2:
                # 操作按钮
                if st.button("👁️ 查看", key=f"view_{article.id}"):
                    st.session_state.view_article_id = article.id
                    st.rerun()
                
                # 上传到微信按钮（草稿状态且有封面图时可用）
                if article.status == ArticleStatus.DRAFT and article.cover_image_path:
                    if st.button("📤 上传微信", key=f"upload_{article.id}"):
                        upload_article_to_wechat(article, db)
                
                if article.status == ArticleStatus.DRAFT:
                    if st.button("✏️ 编辑", key=f"edit_{article.id}"):
                        st.session_state.edit_article_id = article.id
                        st.rerun()
                
                if st.button("🗑️ 删除", key=f"del_{article.id}"):
                    try:
                        db.delete_article(article.id)
                        # 同时删除封面图文件
                        if article.cover_image_path and os.path.exists(article.cover_image_path):
                            os.unlink(article.cover_image_path)
                        st.success(f"文章 '{article.title}' 已删除")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {str(e)}")
        
        # === 快速上传封面图界面 ===
        if st.session_state.get("quick_upload_cover_id") == article.id:
            show_quick_upload_cover(article, db)
    
    # 显示文章详情（如果选择了查看）
    if st.session_state.get("view_article_id") == article.id and not is_editing:
        show_article_detail(article)


def show_quick_upload_cover(article: Article, db):
    """快速上传封面图界面
    
    Args:
        article: 文章对象
        db: 数据库管理器
    """
    st.markdown("---")
    st.info(f"📷 为文章「{article.title}」上传封面图")
    
    # 上传封面图
    new_cover = st.file_uploader(
        "选择封面图",
        type=["jpg", "jpeg", "png", "gif"],
        help="建议尺寸: 900x500像素，文件大小不超过2MB",
        key=f"quick_cover_upload_{article.id}"
    )
    
    if new_cover:
        # 显示预览
        st.image(new_cover, width=200, caption="封面图预览")
    
    # 确认/取消按钮
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ 确认保存", key=f"quick_confirm_cover_{article.id}", type="primary"):
            if new_cover:
                try:
                    # 创建封面图保存目录
                    covers_dir = Path("data/covers")
                    covers_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 生成唯一文件名
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_extension = new_cover.name.split('.')[-1] if '.' in new_cover.name else 'jpg'
                    cover_filename = f"cover_{timestamp}_{article.id}.{file_extension}"
                    cover_path = covers_dir / cover_filename
                    
                    # 保存封面图
                    with open(cover_path, "wb") as f:
                        f.write(new_cover.getvalue())
                    
                    # 更新数据库
                    db.update_article(article.id, {"cover_image_path": str(cover_path)})
                    
                    # 清除上传模式
                    st.session_state.quick_upload_cover_id = None
                    
                    st.success(f"✅ 封面图已保存，现在可以上传到微信了！")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"保存封面图失败: {str(e)}")
                    logger.error(f"保存封面图失败: {e}")
            else:
                st.error("请先选择封面图文件")
    
    with col2:
        if st.button("❌ 取消", key=f"quick_cancel_cover_{article.id}"):
            st.session_state.quick_upload_cover_id = None
            st.rerun()


def show_edit_interface(article: Article, db):
    """显示编辑界面
    
    Args:
        article: 文章对象
        db: 数据库管理器
    """
    st.markdown("---")
    st.subheader("✏️ 编辑文章")
    
    # === 封面图区域（form外部，因为st.form不支持文件上传）===
    st.markdown("**📷 封面图管理**")
    
    # 显示当前封面图状态
    if article.cover_image_path and os.path.exists(article.cover_image_path):
        col_img1, col_img2 = st.columns([1, 2])
        with col_img1:
            try:
                st.image(article.cover_image_path, width=150, caption="当前封面图")
            except Exception as e:
                st.warning(f"封面图加载失败: {str(e)}")
        
        with col_img2:
            st.info("✅ 已有封面图，可以直接上传到微信")
            
            # 替换封面图按钮
            if st.button("🔄 替换封面图", key=f"replace_cover_{article.id}"):
                st.session_state.replace_cover_mode = article.id
    else:
        st.warning("⚠️ 此文章没有封面图，无法上传到微信")
        
        # 上传封面图按钮
        if st.button("📤 上传封面图", key=f"add_cover_{article.id}", type="primary"):
            st.session_state.upload_cover_mode = article.id
    
    # === 上传/替换封面图界面 ===
    upload_mode = st.session_state.get("upload_cover_mode") == article.id
    replace_mode = st.session_state.get("replace_cover_mode") == article.id
    
    if upload_mode or replace_mode:
        st.markdown("---")
        
        # 上传新封面图
        new_cover = st.file_uploader(
            "选择封面图",
            type=["jpg", "jpeg", "png", "gif"],
            help="建议尺寸: 900x500像素，文件大小不超过2MB",
            key=f"cover_upload_{article.id}"
        )
        
        if new_cover:
            # 显示预览
            st.image(new_cover, width=200, caption="新封面图预览")
        
        # 确认/取消按钮
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("✅ 确认保存封面图", key=f"confirm_cover_{article.id}", type="primary"):
                if new_cover:
                    try:
                        # 创建封面图保存目录
                        covers_dir = Path("data/covers")
                        covers_dir.mkdir(parents=True, exist_ok=True)
                        
                        # 生成唯一文件名
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        file_extension = new_cover.name.split('.')[-1] if '.' in new_cover.name else 'jpg'
                        cover_filename = f"cover_{timestamp}_{article.id}.{file_extension}"
                        cover_path = covers_dir / cover_filename
                        
                        # 保存封面图
                        with open(cover_path, "wb") as f:
                            f.write(new_cover.getvalue())
                        
                        # 删除旧封面图（如果存在）
                        if article.cover_image_path and os.path.exists(article.cover_image_path):
                            try:
                                os.unlink(article.cover_image_path)
                                logger.info(f"删除旧封面图: {article.cover_image_path}")
                            except Exception:
                                pass
                        
                        # 更新数据库
                        db.update_article(article.id, {"cover_image_path": str(cover_path)})
                        
                        # 清除上传模式
                        st.session_state.upload_cover_mode = None
                        st.session_state.replace_cover_mode = None
                        
                        st.success(f"✅ 封面图已保存: {cover_filename}")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"保存封面图失败: {str(e)}")
                        logger.error(f"保存封面图失败: {e}")
                else:
                    st.error("请先选择封面图文件")
        
        with col_btn2:
            if st.button("❌ 取消", key=f"cancel_cover_{article.id}"):
                st.session_state.upload_cover_mode = None
                st.session_state.replace_cover_mode = None
                st.rerun()
    
    st.markdown("---")
    
    # === 文章内容编辑表单 ===
    st.markdown("**📝 文章内容**")
    
    # 编辑表单
    with st.form("edit_article_form"):
        # 标题编辑
        new_title = st.text_input(
            "标题",
            value=article.title,
            max_chars=64,
            help="公众号标题最少5字符，最多64字符"
        )
        
        # 摘要编辑
        new_digest = st.text_area(
            "摘要",
            value=article.digest or "",
            max_chars=120,
            help="公众号摘要最多120字符"
        )
        
        # 内容编辑
        new_content = st.text_area(
            "内容（HTML格式）",
            value=article.content,
            height=400,
            help="可以修改文章内容"
        )
        
        # 风格选择
        style_options = ["科普", "故事", "干货", "互动", "资讯", "教程"]
        current_style = article.style or "科普"
        style_index = style_options.index(current_style) if current_style in style_options else 0
        new_style = st.selectbox("风格", style_options, index=style_index)
        
        # 提交按钮
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("💾 保存修改", type="primary")
        
        with col2:
            cancelled = st.form_submit_button("❌ 取消编辑")
    
    # 处理表单提交
    if submitted:
        # 验证
        if not new_title:
            st.error("标题不能为空")
        elif len(new_title) < 5:
            st.warning("标题建议至少5字符")
        elif not new_content:
            st.error("内容不能为空")
        else:
            try:
                # 更新文章（使用 dict 格式）
                update_data = {
                    "title": new_title,
                    "content": new_content,
                    "digest": new_digest,
                    "style": new_style
                }
                
                db.update_article(article.id, update_data)
                
                # 清除编辑状态
                del st.session_state.edit_article_id
                
                st.success(f"✅ 文章 '{new_title}' 已更新")
                st.rerun()
                
            except Exception as e:
                st.error(f"更新失败: {str(e)}")
                logger.error(f"更新文章失败: {e}")
    
    if cancelled:
        # 清除编辑状态
        del st.session_state.edit_article_id
        st.rerun()


def upload_article_to_wechat(article: Article, db):
    """上传文章到微信公众号草稿箱
    
    Args:
        article: 文章对象
        db: 数据库管理器
    """
    # 获取配置
    try:
        settings = get_settings()
    except Exception as e:
        st.error(f"配置加载失败: {str(e)}")
        return
    
    # 检查微信配置
    if not settings.has_wechat_config():
        st.error("⚠️ 请先在设置页面配置微信公众号App ID和App Secret")
        return
    
    # 检查封面图
    if not article.cover_image_path:
        st.error("⚠️ 此文章没有封面图，无法上传到微信")
        st.info("💡 提示：编辑文章时可以重新上传封面图")
        return
    
    if not os.path.exists(article.cover_image_path):
        st.error(f"⚠️ 封面图文件不存在: {article.cover_image_path}")
        return
    
    # 检查标题和内容
    if not article.title:
        st.error("文章标题不能为空")
        return
    
    if not article.content:
        st.error("文章内容不能为空")
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
        
        # 2. 上传封面图
        image_result = api.upload_image(article.cover_image_path)
        thumb_media_id = image_result.get("media_id")
        
        if not thumb_media_id:
            st.error("封面图上传失败，未获取到media_id")
            progress_bar.empty()
            return
        
        st.caption(f"✅ 封面图已上传，media_id: {thumb_media_id}")
        
        progress_bar.progress(70, text="正在上传文章到草稿箱...")
        
        # 3. 构造文章数据
        articles_data = [{
            "title": article.title,
            "author": "AI助手",
            "digest": article.digest or "",
            "content": article.content,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 0,
            "only_fans_can_comment": 0
        }]
        
        # 4. 上传草稿
        result = api.add_draft(articles_data)
        media_id = result.get("media_id")
        
        progress_bar.progress(100, text="上传完成！")
        
        # 更新文章状态
        db.update_article(article.id, {
            "status": ArticleStatus.UPLOADED,
            "wechat_draft_id": media_id
        })
        
        # 显示成功信息
        st.success(f"✅ 上传成功！草稿ID: {media_id}")
        st.balloons()
        st.info("💡 请在微信公众号后台查看和管理此草稿")
        st.caption("提示：登录 mp.weixin.qq.com 进入草稿箱管理")
        
        logger.info(f"文章上传微信成功: media_id={media_id}, title={article.title}")
        
        # 刷新页面
        st.rerun()
        
    except WeChatAPIError as e:
        progress_bar.empty()
        st.error(f"❌ 微信API错误 [{e.code}]: {e.message}")
        logger.error(f"上传微信失败: code={e.code}, message={e.message}")
        
    except Exception as e:
        progress_bar.empty()
        st.error(f"❌ 上传失败: {str(e)}")
        logger.error(f"上传微信失败: {e}")


def show_article_detail(article: Article):
    """显示文章详情
    
    Args:
        article: 文章对象
    """
    st.markdown("---")
    st.markdown(f"### 文章详情: {article.title}")
    
    # 文章内容
    st.markdown("**内容：**")
    st.markdown(article.content, unsafe_allow_html=True)
    
    # 操作按钮
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 复制内容"):
            st.code(article.content, language="html")
            st.info("内容已显示在代码框中，可手动复制")
    
    with col2:
        if st.button("❌ 关闭详情"):
            del st.session_state.view_article_id
            st.rerun()


def show_database_info(db):
    """显示数据库信息
    
    Args:
        db: 数据库管理器
    """
    try:
        info = db.get_database_info()
        
        with st.expander("📊 数据库统计"):
            st.markdown(f"""
            - **数据库路径**: {info['db_path']}
            - **数据库大小**: {info['db_size_mb']} MB
            - **文章数量**: {info['article_count']}
            - **模板数量**: {info['template_count']}
            - **最后修改**: {info['last_modified'] or '未知'}
            """)
            
            # 操作按钮
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 清理数据库"):
                    try:
                        db.vacuum_database()
                        st.success("数据库已清理优化")
                    except Exception as e:
                        st.error(f"清理失败: {str(e)}")
            
            with col2:
                if st.button("💾 备份数据库"):
                    backup_path = f"data/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    try:
                        db.backup_database(backup_path)
                        st.success(f"备份成功: {backup_path}")
                    except Exception as e:
                        st.error(f"备份失败: {str(e)}")
            
            with col3:
                if st.button("📊 查看原始数据"):
                    st.session_state.show_raw_data = True
            
            # 显示原始数据（如果选择了）
            if st.session_state.get("show_raw_data"):
                st.subheader("原始数据查询")
                raw_sql = st.text_input("SQL查询（仅SELECT）", "SELECT * FROM articles LIMIT 10")
                
                if st.button("执行查询"):
                    try:
                        if raw_sql.strip().upper().startswith("SELECT"):
                            results = db.execute_raw_sql(raw_sql)
                            st.dataframe(results)
                        else:
                            st.warning("仅支持SELECT查询")
                    except Exception as e:
                        st.error(f"查询失败: {str(e)}")
                
                if st.button("关闭原始数据"):
                    del st.session_state.show_raw_data
                    st.rerun()
    
    except Exception as e:
        st.warning(f"无法获取数据库信息: {str(e)}")