"""
数据库管理模块
提供完整的 CRUD 操作接口
使用原生 sqlite3 实现，简单可靠
"""
import sqlite3
import os
import shutil
from datetime import datetime
from typing import Optional, List, Union
from pathlib import Path
from contextlib import contextmanager
import logging

from database.models import Article, Template, ConfigItem

# 配置日志
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """数据库操作异常"""
    pass


class DatabaseManager:
    """数据库管理器
    
    负责数据库连接、表创建、CRUD操作和事务管理
    """
    
    DEFAULT_DB_PATH = "data/wechat_writer.db"
    
    def __init__(self, db_path: str = None):
        """初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径，默认为 data/wechat_writer.db
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self._ensure_db_dir()
        self._init_database()
    
    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建文章表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT,
                        digest TEXT,
                        style TEXT,
                        topic TEXT,
                        template_id INTEGER,
                        ai_model TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        wechat_draft_id TEXT,
                        wechat_media_id TEXT,
                        status TEXT DEFAULT 'draft'
                    )
                """)
                
                # === 数据库迁移：添加新列 ===
                # 检查并添加 cover_image_path 列
                cursor.execute("PRAGMA table_info(articles)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'cover_image_path' not in columns:
                    cursor.execute("""
                        ALTER TABLE articles ADD COLUMN cover_image_path TEXT DEFAULT ''
                    """)
                    logger.info("数据库迁移：添加 cover_image_path 列")
                
                # 创建模板表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        category TEXT,
                        prompt_template TEXT,
                        style_config TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active INTEGER DEFAULT 1
                    )
                """)
                
                # 创建配置表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS config (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 创建定时任务表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scheduled_tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        task_type TEXT NOT NULL,
                        schedule_time TEXT,
                        config TEXT,
                        status TEXT DEFAULT 'pending',
                        last_run_time TIMESTAMP,
                        last_run_result TEXT,
                        next_run_time TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active INTEGER DEFAULT 1
                    )
                """)
                
                # 创建索引以优化查询性能
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_articles_status 
                    ON articles(status)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_articles_created_at 
                    ON articles(created_at)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_templates_category 
                    ON templates(category)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_templates_is_active 
                    ON templates(is_active)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status 
                    ON scheduled_tasks(status)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run 
                    ON scheduled_tasks(next_run_time)
                """)
                
                # 初始化默认模板
                self._init_default_templates(cursor)
                
                conn.commit()
                logger.info(f"数据库初始化完成: {self.db_path}")
                
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
            raise DatabaseError(f"数据库初始化失败: {e}")
    
    def _init_default_templates(self, cursor):
        """初始化默认模板
        
        Args:
            cursor: 数据库游标
        """
        # 检查是否已有模板
        cursor.execute("SELECT COUNT(*) FROM templates")
        count = cursor.fetchone()[0]
        
        if count == 0:
            default_templates = [
                (
                    "科普文章",
                    "科普",
                    """你是一位专业的科普文章写手。
请根据以下主题创作一篇通俗易懂的科普文章：

主题：{topic}
字数：约{word_count}字

结构要求：
- 用生动的比喻开头
- 清晰的小标题分段
- 适当使用列表和加粗
- 引导读者思考的结尾

请输出：
【标题】...
【摘要】...
【正文】...
【关键词】...""",
                    '{"style": "科普", "tone": "轻松易懂"}'
                ),
                (
                    "故事分享",
                    "故事",
                    """你是一位擅长讲故事的文章写手。
请根据以下主题创作一篇引人入胜的故事类文章：

主题：{topic}
字数：约{word_count}字

结构要求：
- 有悬念的开头
- 情节层层递进
- 人物对话生动
- 有情感共鸣的结尾

请输出：
【标题】...
【摘要】...
【正文】...
【关键词】...""",
                    '{"style": "故事", "tone": "情感丰富"}'
                ),
                (
                    "干货总结",
                    "干货",
                    """你是一位专业的干货文章写手。
请根据以下主题创作一篇实用的干货文章：

主题：{topic}
字数：约{word_count}字

结构要求：
- 直接切入主题
- 分点清晰列出
- 提供具体方法
- 行动号召结尾

请输出：
【标题】...
【摘要】...
【正文】...
【关键词】...""",
                    '{"style": "干货", "tone": "专业实用"}'
                ),
                (
                    "互动问答",
                    "互动",
                    """你是一位擅长互动的文章写手。
请根据以下主题创作一篇引导读者参与的文章：

主题：{topic}
字数：约{word_count}字

结构要求：
- 用提问方式开头
- 列出多种观点
- 鼓励读者留言
- 设置悬念结尾

请输出：
【标题】...
【摘要】...
【正文】...
【关键词】...""",
                    '{"style": "互动", "tone": "亲切引导"}'
                ),
            ]
            
            for name, category, prompt, style_config in default_templates:
                cursor.execute(
                    "INSERT INTO templates (name, category, prompt_template, style_config) VALUES (?, ?, ?, ?)",
                    (name, category, prompt, style_config)
                )
            
            logger.info(f"初始化了 {len(default_templates)} 个默认模板")
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）
        
        自动处理连接的创建和关闭，确保资源正确释放
        
        Yields:
            sqlite3.Connection: 数据库连接对象
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        try:
            yield conn
        finally:
            conn.close()
    
    # ==================== 文章 CRUD ====================
    
    def save_article(self, article: Article) -> int:
        """保存文章，返回ID
        
        Args:
            article: 文章对象
            
        Returns:
            int: 新创建的文章ID
            
        Raises:
            DatabaseError: 保存失败时抛出
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute("""
                    INSERT INTO articles (title, content, digest, style, topic, 
                        template_id, ai_model, created_at, updated_at, status,
                        wechat_draft_id, wechat_media_id, cover_image_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article.title, 
                    article.content, 
                    article.digest, 
                    article.style,
                    article.topic, 
                    article.template_id, 
                    article.ai_model, 
                    now, 
                    now, 
                    article.status,
                    article.wechat_draft_id,
                    article.wechat_media_id,
                    article.cover_image_path
                ))
                
                conn.commit()
                article_id = cursor.lastrowid
                logger.info(f"保存文章成功: ID={article_id}, 标题={article.title}")
                return article_id
                
        except sqlite3.Error as e:
            logger.error(f"保存文章失败: {e}")
            raise DatabaseError(f"保存文章失败: {e}")
    
    def get_article(self, article_id: int) -> Optional[Article]:
        """获取单篇文章
        
        Args:
            article_id: 文章ID
            
        Returns:
            Article: 文章对象，不存在则返回 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
                row = cursor.fetchone()
                
                if row:
                    return Article.from_dict(dict(row))
                return None
                
        except sqlite3.Error as e:
            logger.error(f"获取文章失败: ID={article_id}, 错误={e}")
            raise DatabaseError(f"获取文章失败: {e}")
    
    def list_articles(
        self, 
        status: str = None, 
        style: str = None,
        limit: int = 20, 
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[Article]:
        """列出文章
        
        Args:
            status: 状态过滤（可选）
            style: 风格过滤（可选）
            limit: 返回数量限制
            offset: 偏移量（用于分页）
            order_by: 排序字段
            order_desc: 是否降序
            
        Returns:
            List[Article]: 文章列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建查询条件
                conditions = []
                params = []
                
                if status:
                    conditions.append("status = ?")
                    params.append(status)
                
                if style:
                    conditions.append("style = ?")
                    params.append(style)
                
                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
                order_direction = "DESC" if order_desc else "ASC"
                
                sql = f"""
                    SELECT * FROM articles 
                    {where_clause}
                    ORDER BY {order_by} {order_direction}
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [Article.from_dict(dict(row)) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"列出文章失败: {e}")
            raise DatabaseError(f"列出文章失败: {e}")
    
    def update_article(self, article_id: int, data: dict) -> bool:
        """更新文章
        
        Args:
            article_id: 文章ID
            data: 更新数据字典
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建更新SQL
                allowed_fields = [
                    "title", "content", "digest", "style", "topic", 
                    "template_id", "ai_model", "wechat_draft_id", 
                    "wechat_media_id", "status", "cover_image_path"
                ]
                
                fields = []
                values = []
                for key, value in data.items():
                    if key in allowed_fields:
                        fields.append(f"{key} = ?")
                        values.append(value)
                
                if not fields:
                    logger.warning(f"更新文章失败: 无有效字段")
                    return False
                
                fields.append("updated_at = ?")
                values.append(datetime.now().isoformat())
                values.append(article_id)
                
                sql = f"UPDATE articles SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(sql, values)
                conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"更新文章成功: ID={article_id}")
                else:
                    logger.warning(f"更新文章失败: ID={article_id} 不存在")
                return success
                
        except sqlite3.Error as e:
            logger.error(f"更新文章失败: ID={article_id}, 错误={e}")
            raise DatabaseError(f"更新文章失败: {e}")
    
    def delete_article(self, article_id: int) -> bool:
        """删除文章
        
        Args:
            article_id: 文章ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM articles WHERE id = ?", (article_id,))
                conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"删除文章成功: ID={article_id}")
                else:
                    logger.warning(f"删除文章失败: ID={article_id} 不存在")
                return success
                
        except sqlite3.Error as e:
            logger.error(f"删除文章失败: ID={article_id}, 错误={e}")
            raise DatabaseError(f"删除文章失败: {e}")
    
    def count_articles(self, status: str = None, style: str = None) -> int:
        """统计文章数量
        
        Args:
            status: 状态过滤（可选）
            style: 风格过滤（可选）
            
        Returns:
            int: 文章数量
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                conditions = []
                params = []
                
                if status:
                    conditions.append("status = ?")
                    params.append(status)
                
                if style:
                    conditions.append("style = ?")
                    params.append(style)
                
                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
                sql = f"SELECT COUNT(*) FROM articles {where_clause}"
                
                cursor.execute(sql, params)
                return cursor.fetchone()[0]
                
        except sqlite3.Error as e:
            logger.error(f"统计文章数量失败: {e}")
            raise DatabaseError(f"统计文章数量失败: {e}")
    
    # ==================== 模板 CRUD ====================
    
    def save_template(self, template: Template) -> int:
        """保存模板
        
        Args:
            template: 模板对象
            
        Returns:
            int: 新创建的模板ID
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute("""
                    INSERT INTO templates (name, category, prompt_template, style_config, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    template.name, 
                    template.category, 
                    template.prompt_template,
                    template.style_config, 
                    now, 
                    int(template.is_active)
                ))
                
                conn.commit()
                template_id = cursor.lastrowid
                logger.info(f"保存模板成功: ID={template_id}, 名称={template.name}")
                return template_id
                
        except sqlite3.Error as e:
            logger.error(f"保存模板失败: {e}")
            raise DatabaseError(f"保存模板失败: {e}")
    
    def get_template(self, template_id: int) -> Optional[Template]:
        """获取模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            Template: 模板对象，不存在则返回 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
                row = cursor.fetchone()
                
                if row:
                    return Template.from_dict(dict(row))
                return None
                
        except sqlite3.Error as e:
            logger.error(f"获取模板失败: ID={template_id}, 错误={e}")
            raise DatabaseError(f"获取模板失败: {e}")
    
    def get_template_by_name(self, name: str) -> Optional[Template]:
        """按名称获取模板
        
        Args:
            name: 模板名称
            
        Returns:
            Template: 模板对象，不存在则返回 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM templates WHERE name = ? AND is_active = 1", (name,))
                row = cursor.fetchone()
                
                if row:
                    return Template.from_dict(dict(row))
                return None
                
        except sqlite3.Error as e:
            logger.error(f"按名称获取模板失败: name={name}, 错误={e}")
            raise DatabaseError(f"获取模板失败: {e}")
    
    def list_templates(
        self, 
        category: str = None, 
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Template]:
        """列出模板
        
        Args:
            category: 分类过滤（可选）
            active_only: 是否只返回活跃模板
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            List[Template]: 模板列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                conditions = []
                params = []
                
                if category:
                    conditions.append("category = ?")
                    params.append(category)
                
                if active_only:
                    conditions.append("is_active = 1")
                
                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
                sql = f"""
                    SELECT * FROM templates 
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [Template.from_dict(dict(row)) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"列出模板失败: {e}")
            raise DatabaseError(f"列出模板失败: {e}")
    
    def update_template(self, template_id: int, data: dict) -> bool:
        """更新模板
        
        Args:
            template_id: 模板ID
            data: 更新数据字典
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                allowed_fields = ["name", "category", "prompt_template", "style_config", "is_active"]
                
                fields = []
                values = []
                for key, value in data.items():
                    if key in allowed_fields:
                        if key == "is_active":
                            value = int(value)
                        fields.append(f"{key} = ?")
                        values.append(value)
                
                if not fields:
                    return False
                
                values.append(template_id)
                sql = f"UPDATE templates SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(sql, values)
                conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"更新模板成功: ID={template_id}")
                return success
                
        except sqlite3.Error as e:
            logger.error(f"更新模板失败: ID={template_id}, 错误={e}")
            raise DatabaseError(f"更新模板失败: {e}")
    
    def delete_template(self, template_id: int, soft_delete: bool = True) -> bool:
        """删除模板
        
        Args:
            template_id: 模板ID
            soft_delete: 是否软删除（设置is_active=0）
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if soft_delete:
                    cursor.execute("UPDATE templates SET is_active = 0 WHERE id = ?", (template_id,))
                else:
                    cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
                
                conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"删除模板成功: ID={template_id}, soft_delete={soft_delete}")
                return success
                
        except sqlite3.Error as e:
            logger.error(f"删除模板失败: ID={template_id}, 错误={e}")
            raise DatabaseError(f"删除模板失败: {e}")
    
    def count_templates(self, category: str = None, active_only: bool = True) -> int:
        """统计模板数量
        
        Args:
            category: 分类过滤（可选）
            active_only: 是否只统计活跃模板
            
        Returns:
            int: 模板数量
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                conditions = []
                params = []
                
                if category:
                    conditions.append("category = ?")
                    params.append(category)
                
                if active_only:
                    conditions.append("is_active = 1")
                
                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
                sql = f"SELECT COUNT(*) FROM templates {where_clause}"
                
                cursor.execute(sql, params)
                return cursor.fetchone()[0]
                
        except sqlite3.Error as e:
            logger.error(f"统计模板数量失败: {e}")
            raise DatabaseError(f"统计模板数量失败: {e}")
    
    # ==================== 配置 CRUD ====================
    
    def get_config(self, key: str) -> Optional[str]:
        """获取配置值
        
        Args:
            key: 配置键名
            
        Returns:
            str: 配置值，不存在则返回 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row["value"] if row else None
                
        except sqlite3.Error as e:
            logger.error(f"获取配置失败: key={key}, 错误={e}")
            raise DatabaseError(f"获取配置失败: {e}")
    
    def get_config_item(self, key: str) -> Optional[ConfigItem]:
        """获取配置项对象
        
        Args:
            key: 配置键名
            
        Returns:
            ConfigItem: 配置项对象，不存在则返回 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM config WHERE key = ?", (key,))
                row = cursor.fetchone()
                
                if row:
                    return ConfigItem.from_dict(dict(row))
                return None
                
        except sqlite3.Error as e:
            logger.error(f"获取配置项失败: key={key}, 错误={e}")
            raise DatabaseError(f"获取配置项失败: {e}")
    
    def set_config(self, key: str, value: str) -> bool:
        """设置配置
        
        Args:
            key: 配置键名
            value: 配置值
            
        Returns:
            bool: 设置是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute(
                    "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, ?)",
                    (key, value, now)
                )
                conn.commit()
                
                logger.info(f"设置配置成功: key={key}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"设置配置失败: key={key}, 错误={e}")
            raise DatabaseError(f"设置配置失败: {e}")
    
    def delete_config(self, key: str) -> bool:
        """删除配置
        
        Args:
            key: 配置键名
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM config WHERE key = ?", (key,))
                conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"删除配置成功: key={key}")
                return success
                
        except sqlite3.Error as e:
            logger.error(f"删除配置失败: key={key}, 错误={e}")
            raise DatabaseError(f"删除配置失败: {e}")
    
    def list_configs(self) -> List[ConfigItem]:
        """列出所有配置
        
        Returns:
            List[ConfigItem]: 配置列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM config ORDER BY key")
                rows = cursor.fetchall()
                return [ConfigItem.from_dict(dict(row)) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"列出配置失败: {e}")
            raise DatabaseError(f"列出配置失败: {e}")
    
    # ==================== 数据库备份/恢复 ====================
    
    def backup_database(self, backup_path: str) -> bool:
        """备份数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 备份是否成功
        """
        try:
            # 确保备份目录存在
            backup_dir = Path(backup_path).parent
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用SQLite的备份API
            with self._get_connection() as conn:
                backup_conn = sqlite3.connect(backup_path)
                conn.backup(backup_conn)
                backup_conn.close()
            
            logger.info(f"数据库备份成功: {backup_path}")
            return True
            
        except (sqlite3.Error, OSError) as e:
            logger.error(f"数据库备份失败: {e}")
            raise DatabaseError(f"数据库备份失败: {e}")
    
    def restore_database(self, backup_path: str) -> bool:
        """恢复数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 恢复是否成功
        """
        try:
            if not os.path.exists(backup_path):
                raise DatabaseError(f"备份文件不存在: {backup_path}")
            
            # 关闭当前连接并删除旧数据库
            shutil.copy2(backup_path, self.db_path)
            
            logger.info(f"数据库恢复成功: 从 {backup_path}")
            return True
            
        except (sqlite3.Error, OSError) as e:
            logger.error(f"数据库恢复失败: {e}")
            raise DatabaseError(f"数据库恢复失败: {e}")
    
    # ==================== 工具方法 ====================
    
    def get_database_info(self) -> dict:
        """获取数据库信息
        
        Returns:
            dict: 数据库统计信息
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取各表记录数
                cursor.execute("SELECT COUNT(*) FROM articles")
                article_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM templates WHERE is_active = 1")
                template_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM config")
                config_count = cursor.fetchone()[0]
                
                # 获取数据库文件大小
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    "db_path": self.db_path,
                    "db_size_bytes": db_size,
                    "db_size_mb": round(db_size / 1024 / 1024, 2),
                    "article_count": article_count,
                    "template_count": template_count,
                    "config_count": config_count,
                    "last_modified": datetime.fromtimestamp(
                        os.path.getmtime(self.db_path)
                    ).isoformat() if os.path.exists(self.db_path) else None
                }
                
        except sqlite3.Error as e:
            logger.error(f"获取数据库信息失败: {e}")
            raise DatabaseError(f"获取数据库信息失败: {e}")
    
    def execute_raw_sql(self, sql: str, params: tuple = None) -> List[dict]:
        """执行原始SQL查询（仅用于调试）
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            List[dict]: 查询结果
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                
                if sql.strip().upper().startswith("SELECT"):
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
                else:
                    conn.commit()
                    return [{"affected_rows": cursor.rowcount}]
                    
        except sqlite3.Error as e:
            logger.error(f"执行SQL失败: {sql}, 错误={e}")
            raise DatabaseError(f"执行SQL失败: {e}")
    
    # ==================== 定时任务 CRUD ====================
    
    def save_scheduled_task(self, task_data: dict) -> int:
        """保存定时任务
        
        Args:
            task_data: 任务数据字典
            
        Returns:
            int: 任务ID
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute("""
                    INSERT INTO scheduled_tasks 
                    (name, task_type, schedule_time, config, status, 
                     last_run_time, last_run_result, next_run_time, 
                     created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_data.get("name", ""),
                    task_data.get("task_type", ""),
                    task_data.get("schedule_time", ""),
                    task_data.get("config", "{}"),
                    task_data.get("status", "pending"),
                    task_data.get("last_run_time"),
                    task_data.get("last_run_result", ""),
                    task_data.get("next_run_time"),
                    now,
                    now,
                    1 if task_data.get("is_active", True) else 0
                ))
                
                conn.commit()
                task_id = cursor.lastrowid
                logger.info(f"保存定时任务成功: ID={task_id}, 名称={task_data.get('name')}")
                return task_id
                
        except sqlite3.Error as e:
            logger.error(f"保存定时任务失败: {e}")
            raise DatabaseError(f"保存定时任务失败: {e}")
    
    def get_scheduled_task(self, task_id: int) -> Optional[dict]:
        """获取单个定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 任务数据，不存在则返回 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"获取定时任务失败: ID={task_id}, 错误={e}")
            raise DatabaseError(f"获取定时任务失败: {e}")
    
    def list_scheduled_tasks(
        self,
        status: str = None,
        task_type: str = None,
        is_active: bool = None,
        limit: int = 20
    ) -> List[dict]:
        """列出定时任务
        
        Args:
            status: 状态过滤
            task_type: 类型过滤
            is_active: 是否激活过滤
            limit: 返回数量
            
        Returns:
            List[dict]: 任务列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                conditions = []
                params = []
                
                if status:
                    conditions.append("status = ?")
                    params.append(status)
                
                if task_type:
                    conditions.append("task_type = ?")
                    params.append(task_type)
                
                if is_active is not None:
                    conditions.append("is_active = ?")
                    params.append(1 if is_active else 0)
                
                where_clause = " AND ".join(conditions) if conditions else ""
                
                sql = f"""
                    SELECT * FROM scheduled_tasks 
                    {f"WHERE {where_clause}" if where_clause else ""}
                    ORDER BY next_run_time ASC, created_at DESC
                    LIMIT ?
                """
                params.append(limit)
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"列出定时任务失败: {e}")
            raise DatabaseError(f"列出定时任务失败: {e}")
    
    def update_scheduled_task(self, task_id: int, data: dict) -> bool:
        """更新定时任务
        
        Args:
            task_id: 任务ID
            data: 更新数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                allowed_fields = [
                    "name", "task_type", "schedule_time", "config", "status",
                    "last_run_time", "last_run_result", "next_run_time", "is_active"
                ]
                
                fields = []
                values = []
                
                for key, value in data.items():
                    if key in allowed_fields:
                        fields.append(f"{key} = ?")
                        values.append(value)
                
                if not fields:
                    logger.warning("更新定时任务失败: 无有效字段")
                    return False
                
                fields.append("updated_at = ?")
                values.append(datetime.now().isoformat())
                values.append(task_id)
                
                sql = f"UPDATE scheduled_tasks SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(sql, values)
                conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"更新定时任务成功: ID={task_id}")
                else:
                    logger.warning(f"更新定时任务失败: ID={task_id} 不存在")
                return success
                
        except sqlite3.Error as e:
            logger.error(f"更新定时任务失败: ID={task_id}, 错误={e}")
            raise DatabaseError(f"更新定时任务失败: {e}")
    
    def delete_scheduled_task(self, task_id: int) -> bool:
        """删除定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
                conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"删除定时任务成功: ID={task_id}")
                return success
                
        except sqlite3.Error as e:
            logger.error(f"删除定时任务失败: ID={task_id}, 错误={e}")
            raise DatabaseError(f"删除定时任务失败: {e}")
    
    def get_pending_tasks_to_run(self) -> List[dict]:
        """获取需要执行的待运行任务
        
        查询所有激活且到达执行时间的任务
        
        Returns:
            List[dict]: 待执行任务列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute("""
                    SELECT * FROM scheduled_tasks 
                    WHERE is_active = 1 
                    AND status IN ('pending', 'completed')
                    AND (next_run_time IS NULL OR next_run_time <= ?)
                    ORDER BY next_run_time ASC
                """, (now,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"获取待执行任务失败: {e}")
            raise DatabaseError(f"获取待执行任务失败: {e}")
    
    def vacuum_database(self) -> bool:
        """清理数据库（优化空间）
        
        Returns:
            bool: 清理是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("VACUUM")
                conn.commit()
            
            logger.info(f"数据库清理完成")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"数据库清理失败: {e}")
            raise DatabaseError(f"数据库清理失败: {e}")


# 创建全局数据库管理器实例（延迟初始化）
_global_db_manager: Optional[DatabaseManager] = None


def get_db_manager(db_path: str = None) -> DatabaseManager:
    """获取数据库管理器实例（单例模式）
    
    Args:
        db_path: 数据库路径（可选，仅首次调用时生效）
        
    Returns:
        DatabaseManager: 数据库管理器实例
    """
    global _global_db_manager
    
    if _global_db_manager is None:
        _global_db_manager = DatabaseManager(db_path)
    
    return _global_db_manager


def reset_db_manager():
    """重置数据库管理器实例（用于测试）
    """
    global _global_db_manager
    _global_db_manager = None