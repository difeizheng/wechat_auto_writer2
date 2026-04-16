"""
定时任务管理页面
提供定时任务的创建、管理和执行功能
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import logging

from database import get_db_manager
from config import get_settings
from core.scheduler import (
    TaskStatus, TaskType, ScheduledTask,
    DingTalkNotifier, send_dingtalk_notification
)

# 配置日志
logger = logging.getLogger(__name__)


def show_scheduler():
    """显示定时任务管理页面"""
    st.title("⏰ 定时任务管理")
    
    # 获取配置和数据库
    settings = get_settings()
    db = get_db_manager()
    
    # === 页面布局 ===
    tab1, tab2, tab3 = st.tabs(["📋 任务列表", "➕ 创建任务", "📊 执行日志"])
    
    with tab1:
        show_task_list(db, settings)
    
    with tab2:
        show_create_task(db, settings)
    
    with tab3:
        show_execution_logs(db)


def show_task_list(db, settings):
    """显示任务列表"""
    st.subheader("📋 已创建的定时任务")
    
    # 筛选条件
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "状态筛选",
            ["全部", "pending", "running", "completed", "failed", "disabled"],
            index=0
        )
    
    with col2:
        type_filter = st.selectbox(
            "类型筛选",
            ["全部", "generate_article", "upload_wechat", "full_workflow"],
            index=0,
            format_func=lambda x: {
                "全部": "全部",
                "generate_article": "生成文章",
                "upload_wechat": "上传微信",
                "full_workflow": "完整流程"
            }.get(x, x)
        )
    
    with col3:
        active_filter = st.selectbox(
            "激活状态",
            ["全部", "激活", "未激活"],
            index=0
        )
    
    # 查询任务
    query_status = None if status_filter == "全部" else status_filter
    query_type = None if type_filter == "全部" else type_filter
    query_active = None if active_filter == "全部" else (active_filter == "激活")
    
    try:
        tasks = db.list_scheduled_tasks(
            status=query_status,
            task_type=query_type,
            is_active=query_active,
            limit=50
        )
    except Exception as e:
        st.error(f"获取任务列表失败: {str(e)}")
        return
    
    # 显示统计
    st.caption(f"共找到 {len(tasks)} 个定时任务")
    
    if not tasks:
        st.info("暂无定时任务，请切换到「创建任务」标签页创建新任务")
        return
    
    # 显示任务列表
    for task in tasks:
        display_task_item(task, db, settings)


def display_task_item(task: dict, db, settings):
    """显示单个任务项"""
    # 状态图标
    status_icons = {
        "pending": "⏳",
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
        "disabled": "🔴"
    }
    
    status_icon = status_icons.get(task.get("status", "pending"), "📄")
    
    # 类型名称
    type_names = {
        "generate_article": "生成文章",
        "upload_wechat": "上传微信",
        "full_workflow": "完整流程"
    }
    
    type_name = type_names.get(task.get("task_type", ""), task.get("task_type", ""))
    
    with st.expander(
        f"{status_icon} {task.get('name', '未命名')} - {type_name}",
        expanded=False
    ):
        # 任务信息
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"""
            **任务类型**: {type_name}
            
            **执行时间**: {task.get('schedule_time', '未设置')}
            
            **下次执行**: {task.get('next_run_time', '未计算') or '未计算'}
            
            **上次执行**: {task.get('last_run_time', '从未执行') or '从未执行'}
            
            **执行结果**: {task.get('last_run_result', '无') or '无'}
            
            **创建时间**: {task.get('created_at', '未知')}
            """)
        
        with col2:
            # 操作按钮
            task_id = task.get("id")
            is_active = task.get("is_active", 1) == 1
            
            # 立即执行按钮
            if st.button("▶️ 立即执行", key=f"run_{task_id}"):
                execute_task_now(task_id, db, settings)
            
            # 启用/禁用按钮
            if is_active:
                if st.button("🔴 禁用任务", key=f"disable_{task_id}"):
                    toggle_task_status(task_id, db, False)
            else:
                if st.button("🟢 启用任务", key=f"enable_{task_id}"):
                    toggle_task_status(task_id, db, True)
            
            # 删除按钮
            if st.button("🗑️ 删除任务", key=f"delete_{task_id}"):
                delete_task(task_id, db)
            
            # 查看配置
            if st.button("⚙️ 查看配置", key=f"config_{task_id}"):
                st.session_state.view_task_config = task_id
        
        # 显示配置详情
        if st.session_state.get("view_task_config") == task_id:
            show_task_config(task)


def show_task_config(task: dict):
    """显示任务配置详情"""
    st.markdown("---")
    st.subheader("⚙️ 任务配置详情")
    
    config_str = task.get("config", "{}")
    try:
        config = json.loads(config_str) if isinstance(config_str, str) else config_str
        st.json(config)
    except json.JSONDecodeError:
        st.code(config_str, language="json")
    
    if st.button("关闭配置"):
        del st.session_state.view_task_config
        st.rerun()


def show_create_task(db, settings):
    """显示创建任务界面"""
    st.subheader("➕ 创建新的定时任务")
    
    # 任务类型选择
    task_type = st.selectbox(
        "任务类型",
        ["generate_article", "upload_wechat", "full_workflow"],
        format_func=lambda x: {
            "generate_article": "📝 生成文章",
            "upload_wechat": "📤 上传微信",
            "full_workflow": "🔄 完整流程（生成+上传）"
        }.get(x, x),
        help="选择任务类型"
    )
    
    # 任务名称
    task_name = st.text_input(
        "任务名称",
        value=f"定时{task_type}",
        help="给任务起一个描述性的名称"
    )
    
    # 执行时间设置
    st.markdown("---")
    st.markdown("**⏰ 执行时间设置**")
    
    schedule_type = st.radio(
        "执行方式",
        ["单次执行", "定时执行", "循环执行"],
        horizontal=True
    )
    
    schedule_time = ""
    next_run_time = None
    
    if schedule_type == "单次执行":
        run_date = st.date_input("执行日期", datetime.now())
        run_time = st.time_input("执行时间", datetime.now())
        schedule_time = f"{run_date} {run_time}"
        next_run_time = datetime.combine(run_date, run_time)
        
    elif schedule_type == "定时执行":
        schedule_time = st.text_input(
            "执行时间（格式: HH:MM）",
            value="09:00",
            help="例如: 09:00 表示每天早上9点执行"
        )
        
        # 计算下次执行时间
        try:
            hour, minute = schedule_time.split(":")
            now = datetime.now()
            next_run = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            next_run_time = next_run
            st.caption(f"下次执行时间: {next_run_time.strftime('%Y-%m-%d %H:%M')}")
        except:
            st.warning("时间格式错误，请使用 HH:MM 格式")
    
    elif schedule_type == "循环执行":
        interval_hours = st.number_input("间隔小时", min_value=1, value=6)
        schedule_time = f"every_{interval_hours}h"
        next_run_time = datetime.now() + timedelta(hours=interval_hours)
        st.caption(f"下次执行时间: {next_run_time.strftime('%Y-%m-%d %H:%M')}")
    
    # 任务配置
    st.markdown("---")
    st.markdown("**⚙️ 任务配置**")
    
    task_config = {}
    
    if task_type == "generate_article" or task_type == "full_workflow":
        # AI模型选择
        available_models = settings.get_available_models()
        if not available_models:
            st.error("请先配置AI模型")
            return
        
        selected_model = st.selectbox(
            "AI模型",
            available_models,
            format_func=lambda x: {
                "openai": "OpenAI GPT",
                "claude": "Claude",
                "siliconflow": "SiliconFlow",
                "ollama": "Ollama（本地）"
            }.get(x, x)
        )
        
        # 文章主题
        topics_input = st.text_area(
            "文章主题（多个主题用换行分隔）",
            value="今日热点\n科技前沿",
            help="每行一个主题，将生成多篇文章"
        )
        topics = [t.strip() for t in topics_input.split("\n") if t.strip()]
        
        # 文章风格
        style = st.selectbox(
            "文章风格",
            ["科普", "故事", "干货", "互动", "资讯", "教程"]
        )
        
        # 字数
        word_count = st.number_input(
            "目标字数",
            min_value=200,
            max_value=5000,
            value=800
        )
        
        # 封面图（可选）
        cover_image = st.file_uploader(
            "封面图（可选，用于上传微信）",
            type=["jpg", "jpeg", "png"],
            help="如果需要上传到微信，请上传封面图"
        )
        
        task_config = {
            "model": selected_model,
            "topics": topics,
            "style": style,
            "word_count": word_count
        }
        
        if cover_image:
            import os
            import uuid
            covers_dir = os.path.join("data", "covers")
            os.makedirs(covers_dir, exist_ok=True)
            cover_ext = os.path.splitext(cover_image.name)[1] or ".jpg"
            cover_filename = f"task_cover_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d')}{cover_ext}"
            cover_path = os.path.join(covers_dir, cover_filename)
            with open(cover_path, "wb") as f:
                f.write(cover_image.getbuffer())
            task_config["cover_image_uploaded"] = True
            task_config["cover_image_path"] = cover_path
            st.success(f"封面图已保存: {cover_filename}")
    
    elif task_type == "upload_wechat":
        # 文章选择
        st.info("将自动选择未上传的草稿文章（需要封面图）")
        
        auto_draft = st.checkbox("自动选择草稿文章", value=True)
        
        if not auto_draft:
            # 显示可选文章列表
            try:
                draft_articles = db.list_articles(status="draft", limit=20)
                article_options = {f"{a.id}: {a.title}": a.id for a in draft_articles if a.cover_image_path}
                
                if article_options:
                    selected_articles = st.multiselect(
                        "选择要上传的文章",
                        list(article_options.keys())
                    )
                    task_config["article_ids"] = [article_options[a] for a in selected_articles]
                else:
                    st.warning("没有可上传的草稿文章（需要封面图）")
            except Exception as e:
                st.error(f"获取文章列表失败: {str(e)}")
        
        task_config["auto_draft"] = auto_draft
    
    # 钉钉通知设置
    st.markdown("---")
    st.markdown("**🔔 通知设置**")
    
    if settings.has_dingtalk_config():
        st.success("✅ 钉钉通知已配置")
        
        # 显示配置详情
        with st.expander("查看配置详情"):
            st.caption(f"Webhook: {settings.DINGTALK_WEBHOOK[:50]}...")
            if settings.DINGTALK_SECRET:
                st.caption(f"签名密钥: ✅ 已配置（加签验证）")
            else:
                st.caption(f"签名密钥: ⚠️ 未配置（如机器人设置了加签，请配置 DINGTALK_SECRET）")
        
        send_notification = st.checkbox("执行后发送钉钉通知", value=True)
        task_config["send_notification"] = send_notification
    else:
        st.warning("⚠️ 钉钉通知未配置，请在 .env 中设置 DINGTALK_WEBHOOK")
        st.caption("获取方式：在钉钉群中添加自定义机器人")
        with st.expander("配置帮助"):
            st.markdown("""
            **步骤：**
            1. 在钉钉群中点击「群设置」→「智能群助手」→「添加机器人」
            2. 选择「自定义」机器人
            3. 设置机器人名称
            4. 安全设置选择「加签」（推荐）
            5. 复制 Webhook URL 和 密钥
            
            **配置示例：**
            ```
            DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
            DINGTALK_SECRET=SECxxxx...
            ```
            """)
    
    # 创建按钮
    st.markdown("---")
    
    if st.button("✅ 创建任务", type="primary"):
        create_new_task(
            db=db,
            task_name=task_name,
            task_type=task_type,
            schedule_time=schedule_time,
            task_config=task_config,
            next_run_time=next_run_time
        )


def create_new_task(
    db,
    task_name: str,
    task_type: str,
    schedule_time: str,
    task_config: dict,
    next_run_time: datetime
):
    """创建新任务"""
    try:
        task_data = {
            "name": task_name,
            "task_type": task_type,
            "schedule_time": schedule_time,
            "config": json.dumps(task_config),
            "status": "pending",
            "next_run_time": next_run_time.isoformat() if next_run_time else None,
            "is_active": True
        }
        
        task_id = db.save_scheduled_task(task_data)
        
        st.success(f"✅ 任务创建成功！任务ID: {task_id}")
        st.balloons()
        
        # 发送钉钉通知
        if task_config.get("send_notification"):
            send_dingtalk_notification(
                title="【定时任务】新任务已创建",
                content=f"任务名称: {task_name}\n任务类型: {task_type}\n执行时间: {schedule_time}\n下次执行: {next_run_time.strftime('%Y-%m-%d %H:%M') if next_run_time else '待计算'}"
            )
        
        logger.info(f"创建定时任务成功: ID={task_id}, name={task_name}")
        
    except Exception as e:
        st.error(f"❌ 创建任务失败: {str(e)}")
        logger.error(f"创建定时任务失败: {e}")


def execute_task_now(task_id: int, db, settings):
    """立即执行任务"""
    st.info(f"正在执行任务 ID: {task_id}...")
    
    try:
        task = db.get_scheduled_task(task_id)
        
        if not task:
            st.error("任务不存在")
            return
        
        # 导入执行器
        from core.scheduler import TaskExecutor
        
        executor = TaskExecutor(settings, db)
        
        # 创建任务对象
        scheduled_task = ScheduledTask.from_dict(task)
        
        # 执行任务
        with st.spinner("任务执行中..."):
            result = executor.execute_task(scheduled_task)
        
        # 更新数据库
        db.update_scheduled_task(task_id, {
            "status": result.get("status", "completed"),
            "last_run_time": datetime.now().isoformat(),
            "last_run_result": result.get("message", ""),
            "next_run_time": None  # 清除下次执行时间（单次任务）
        })
        
        # 显示结果
        if result.get("status") == "completed":
            st.success(f"✅ 任务执行成功: {result.get('message', '')}")
            
            # 显示生成的文章
            articles = result.get("articles", [])
            if articles:
                st.markdown("**生成的文章:**")
                for article in articles:
                    st.caption(f"  • {article.get('title', '未命名')} (ID: {article.get('id')})")
        else:
            st.error(f"❌ 任务执行失败: {result.get('message', '')}")
            
            errors = result.get("errors", [])
            if errors:
                st.markdown("**错误详情:**")
                for error in errors:
                    st.warning(f"  • {error}")
        
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ 执行失败: {str(e)}")
        logger.error(f"执行任务失败: {task_id} - {e}")


def toggle_task_status(task_id: int, db, enable: bool):
    """切换任务激活状态"""
    try:
        db.update_scheduled_task(task_id, {
            "is_active": 1 if enable else 0,
            "status": "pending" if enable else "disabled"
        })
        
        status_text = "启用" if enable else "禁用"
        st.success(f"✅ 任务已{status_text}")
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ 操作失败: {str(e)}")


def delete_task(task_id: int, db):
    """删除任务"""
    try:
        db.delete_scheduled_task(task_id)
        st.success("✅ 任务已删除")
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ 删除失败: {str(e)}")


def show_execution_logs(db):
    """显示执行日志"""
    st.subheader("📊 执行日志")
    
    # 获取最近执行的任务
    try:
        # 查询最近执行的任务（有 last_run_time 的）
        recent_tasks = db.list_scheduled_tasks(limit=20)
        
        # 筛选有执行记录的
        executed_tasks = [t for t in recent_tasks if t.get("last_run_time")]
        
        if not executed_tasks:
            st.info("暂无执行记录")
            return
        
        # 显示执行记录
        for task in executed_tasks:
            status_icon = {
                "completed": "✅",
                "failed": "❌",
                "running": "🔄"
            }.get(task.get("status"), "📄")
            
            with st.expander(
                f"{status_icon} {task.get('name', '未命名')} - {task.get('last_run_time', '未知时间')}",
                expanded=False
            ):
                st.markdown(f"""
                **执行时间**: {task.get('last_run_time', '未知')}
                
                **执行结果**: {task.get('last_run_result', '无结果')}
                
                **任务类型**: {task.get('task_type', '未知')}
                
                **执行状态**: {task.get('status', '未知')}
                """)
                
                # 显示配置
                config_str = task.get("config", "{}")
                try:
                    config = json.loads(config_str)
                    st.json(config)
                except:
                    st.code(config_str, language="json")
        
    except Exception as e:
        st.error(f"获取执行日志失败: {str(e)}")