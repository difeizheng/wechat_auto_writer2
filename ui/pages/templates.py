"""
模板管理页面
提供模板的创建、编辑、删除功能
整合数据库管理，支持完整的模板CRUD操作
"""
import streamlit as st
from typing import Optional
import logging

from database import get_db_manager, Template, TemplateCategory

# 配置日志
logger = logging.getLogger(__name__)


def show_template_management():
    """显示模板管理页面
    
    功能：
    - 查看现有模板列表
    - 创建新模板
    - 编辑/删除模板
    """
    st.title("📋 模板管理")
    
    db = get_db_manager()
    
    # === 模板列表 ===
    st.subheader("📚 已有模板")
    
    # 分类筛选
    category_filter = st.selectbox(
        "分类筛选",
        ["全部", TemplateCategory.SCIENCE, TemplateCategory.STORY,
         TemplateCategory.DRY_GOODS, TemplateCategory.INTERACTIVE],
        index=0
    )
    
    # 加载模板列表
    if category_filter == "全部":
        templates = db.list_templates(active_only=True)
    else:
        templates = db.list_templates(category=category_filter, active_only=True)
    
    if templates:
        # 显示模板列表
        for template in templates:
            with st.expander(f"📄 {template.name}（分类: {template.category}）"):
                # 模板信息
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("**Prompt模板：**")
                    st.code(template.prompt_template, language="markdown")
                    
                    if template.style_config:
                        st.markdown("**风格配置：**")
                        st.json(template.get_style_config_dict())
                
                with col2:
                    st.caption(f"创建时间: {template.created_at}")
                    
                    # 编辑按钮
                    if st.button("✏️ 编辑", key=f"edit_{template.id}"):
                        st.session_state.edit_template_id = template.id
                    
                    # 删除按钮
                    if st.button("🗑️ 删除", key=f"del_{template.id}"):
                        try:
                            db.delete_template(template.id, soft_delete=True)
                            st.success(f"模板 '{template.name}' 已删除")
                            st.rerun()
                        except Exception as e:
                            st.error(f"删除失败: {str(e)}")
    else:
        st.info("暂无模板，请创建新模板")
    
    # === 编辑模板（如果选择了） ===
    if "edit_template_id" in st.session_state:
        edit_template(db, st.session_state.edit_template_id)
    
    # === 创建新模板 ===
    st.markdown("---")
    st.subheader("➕ 创建新模板")
    
    create_new_template(db)


def edit_template(db, template_id: int):
    """编辑模板
    
    Args:
        db: 数据库管理器
        template_id: 模板ID
    """
    template = db.get_template(template_id)
    
    if not template:
        st.error("模板不存在")
        del st.session_state.edit_template_id
        return
    
    st.markdown(f"### 编辑模板: {template.name}")
    
    with st.form("edit_template_form"):
        edited_name = st.text_input("模板名称", value=template.name)
        edited_category = st.selectbox(
            "分类",
            [TemplateCategory.SCIENCE, TemplateCategory.STORY,
             TemplateCategory.DRY_GOODS, TemplateCategory.INTERACTIVE],
            index=[TemplateCategory.SCIENCE, TemplateCategory.STORY,
                   TemplateCategory.DRY_GOODS, TemplateCategory.INTERACTIVE].index(template.category)
            if template.category in [TemplateCategory.SCIENCE, TemplateCategory.STORY,
                                     TemplateCategory.DRY_GOODS, TemplateCategory.INTERACTIVE] else 0
        )
        
        edited_prompt = st.text_area(
            "Prompt模板",
            value=template.prompt_template,
            height=300,
            help="使用 {topic}, {word_count}, {style} 作为变量"
        )
        
        # 风格配置（JSON格式）
        style_config_dict = template.get_style_config_dict()
        edited_style_config = st.text_area(
            "风格配置（JSON格式）",
            value=template.style_config,
            height=100
        )
        
        submitted = st.form_submit_button("💾 保存修改")
        
        if submitted:
            try:
                update_data = {
                    "name": edited_name,
                    "category": edited_category,
                    "prompt_template": edited_prompt,
                    "style_config": edited_style_config
                }
                
                db.update_template(template_id, update_data)
                st.success("模板已更新！")
                del st.session_state.edit_template_id
                st.rerun()
                
            except Exception as e:
                st.error(f"更新失败: {str(e)}")
    
    # 取消编辑按钮
    if st.button("取消编辑"):
        del st.session_state.edit_template_id
        st.rerun()


def create_new_template(db):
    """创建新模板
    
    Args:
        db: 数据库管理器
    """
    with st.form("create_template_form"):
        new_name = st.text_input("模板名称", placeholder="例如：产品介绍模板")
        
        new_category = st.selectbox(
            "模板分类",
            [TemplateCategory.SCIENCE, TemplateCategory.STORY,
             TemplateCategory.DRY_GOODS, TemplateCategory.INTERACTIVE]
        )
        
        # Prompt模板说明
        st.markdown("**Prompt模板内容：**")
        st.caption("提示：使用 {topic}, {word_count}, {style} 作为可替换变量")
        
        new_prompt = st.text_area(
            "Prompt模板",
            height=300,
            placeholder="""你是一位专业的科普文章写手。
请根据以下主题创作一篇通俗易懂的科普文章：

主题：{topic}
字数：约{word_count}字
风格：{style}

结构要求：
- 用生动的比喻开头
- 清晰的小标题分段
- 适当使用列表和加粗
- 引导读者思考的结尾

请输出：
【标题】...
【摘要】...
【正文】...
【关键词】..."""
        )
        
        # 风格配置
        new_style_config = st.text_area(
            "风格配置（JSON格式，可选）",
            value='{"style": "科普", "tone": "轻松易懂"}',
            height=100
        )
        
        submitted = st.form_submit_button("➕ 创建模板", type="primary")
        
        if submitted:
            if not new_name or not new_prompt:
                st.warning("请填写模板名称和Prompt模板")
            else:
                try:
                    # 创建模板对象
                    new_template = Template(
                        name=new_name,
                        category=new_category,
                        prompt_template=new_prompt,
                        style_config=new_style_config,
                        is_active=True
                    )
                    
                    # 保存到数据库
                    template_id = db.save_template(new_template)
                    
                    st.success(f"✅ 模板创建成功！ID: {template_id}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"创建失败: {str(e)}")
                    logger.error(f"创建模板失败: {e}")