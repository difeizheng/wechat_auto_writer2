"""
WeChat Auto Writer - 公众号文章智能写作助手
主入口文件

功能：
- 文章智能生成（支持多种AI模型）
- 模板管理
- 历史记录查看
- 微信公众号集成
"""
import streamlit as st
import logging
from pathlib import Path
import os

os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 导入页面模块
from ui.pages import article_gen, templates, history, settings, scheduler
from database import get_db_manager


def main():
    """主函数 - 应用入口"""
    
    # === 页面配置 ===
    st.set_page_config(
        page_title="公众号文章智能写作助手",
        page_icon="📝",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'About': """
            # 公众号文章智能写作助手
            
            **功能特性**：
            - 🤖 支持多种AI模型（OpenAI、Claude、Ollama）
            - 📝 自动生成公众号风格文章
            - 📋 模板管理，自定义写作风格
            - 📤 直接上传到微信公众号草稿箱
            
            **版本**: v1.0.0
            """
        }
    )
    
    # === 应用初始化 ===
    init_app()
    
    # === 侧边栏导航 ===
    with st.sidebar:
        # 应用标题
        st.title("📝 智能写作助手")
        st.markdown("---")
        
        # 功能导航
        page_options = [
            "📝 文章生成",
            "⏰ 定时任务",
            "📋 模板管理",
            "📚 历史记录",
            "⚙️ 设置"
        ]
        
        selected_page = st.radio(
            "功能导航",
            page_options,
            label_visibility="collapsed",
            index=0
        )
        
        # 显示版本信息
        st.markdown("---")
        st.caption("v1.0.0")
        
        # 显示快速统计
        show_sidebar_stats()
    
    # === 页面路由 ===
    route_to_page(selected_page)


def init_app():
    """初始化应用
    
    功能：
    - 初始化数据库
    - 初始化session state（不覆盖已有值）
    - 确保必要目录存在
    - 启动定时任务调度器
    """
    # 初始化数据库
    try:
        db = get_db_manager()
        logger.info(f"数据库初始化完成: {db.db_path}")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        st.error(f"数据库初始化失败: {str(e)}")
    
    # 初始化session state（只在不存在时初始化）
    if "generated_article" not in st.session_state:
        st.session_state.generated_article = None
    
    if "edited_article" not in st.session_state:
        st.session_state.edited_article = None
    
    # 启动定时任务调度器（子进程方式，持久运行）
    if "scheduler_process" not in st.session_state:
        try:
            import subprocess
            import sys
            
            pid_file = Path("data/scheduler.pid")
            scheduler_already_running = False
            
            # 检查调度器是否已在运行
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                            capture_output=True, text=True)
                    if str(pid) in result.stdout:
                        logger.info(f"调度器已在运行 (PID: {pid})")
                        st.session_state.scheduler_process = pid
                        scheduler_already_running = True
                except:
                    pass
            
            if not scheduler_already_running:
                scheduler_script = os.path.join(os.path.dirname(__file__), "scripts", "run_scheduler.py")
                
                process = subprocess.Popen(
                    [sys.executable, scheduler_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                st.session_state.scheduler_process = process.pid
                logger.info(f"定时任务调度器已启动 (PID: {process.pid})")
        except Exception as e:
            logger.warning(f"启动调度器失败: {e}")
    
    # 确保必要目录存在
    Path("data").mkdir(exist_ok=True)


def show_sidebar_stats():
    """显示侧边栏统计信息"""
    try:
        db = get_db_manager()
        
        # 文章统计
        article_count = db.count_articles()
        draft_count = db.count_articles(status="draft")
        uploaded_count = db.count_articles(status="uploaded")
        
        st.markdown("**📊 统计**")
        st.caption(f"文章总数: {article_count}")
        st.caption(f"草稿: {draft_count} | 已上传: {uploaded_count}")
        
    except Exception as e:
        logger.warning(f"获取统计信息失败: {e}")


def route_to_page(page_name: str):
    """路由到对应页面
    
    Args:
        page_name: 页面名称
    """
    try:
        if page_name == "📝 文章生成":
            article_gen.show_article_generation()
        
        elif page_name == "⏰ 定时任务":
            scheduler.show_scheduler()
        
        elif page_name == "📋 模板管理":
            templates.show_template_management()
        
        elif page_name == "📚 历史记录":
            history.show_history()
        
        elif page_name == "⚙️ 设置":
            settings.show_settings()
        
        else:
            st.warning(f"未知页面: {page_name}")
            
    except Exception as e:
        import traceback
        logger.error(f"页面渲染错误: page={page_name}, error={e}")
        logger.error(traceback.format_exc())
        
        st.error(f"❌ 页面渲染错误: {str(e)}")
        
        # 显示错误详情和堆栈
        with st.expander("🔍 错误详情（点击查看）"):
            st.code(traceback.format_exc(), language="python")
            
            st.markdown("---")
            st.markdown("**可能的解决方案**：")
            st.markdown("""
            1. 检查 `.env` 文件是否正确配置
            2. 确保至少配置了一个AI模型的API Key
            3. 检查数据库文件是否正常
            4. 尝试重新启动应用
            """)


if __name__ == "__main__":
    main()