"""
定时任务调度模块
实现文章自动生成、定时发布、钉钉通知等功能

功能特性：
- 定时生成文章（支持自定义时间）
- 定时上传微信草稿箱
- 钉钉机器人通知（支持加签验证）
- 任务执行日志记录
"""
import json
import logging
import requests
import threading
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import time

logger = logging.getLogger(__name__)


# ==================== 任务状态枚举 ====================

class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    DISABLED = "disabled"    # 已禁用


class TaskType(str, Enum):
    """任务类型"""
    GENERATE_ARTICLE = "generate_article"   # 生成文章
    UPLOAD_WECHAT = "upload_wechat"         # 上传微信
    FULL_WORKFLOW = "full_workflow"         # 完整流程（生成+上传）


# ==================== 任务数据模型 ====================

@dataclass
class ScheduledTask:
    """定时任务模型"""
    id: Optional[int] = None
    name: str = ""
    task_type: str = ""
    schedule_time: str = ""         # cron表达式 或 简单时间格式
    config: Dict = field(default_factory=dict)  # 任务配置
    status: str = TaskStatus.PENDING
    last_run_time: Optional[datetime] = None
    last_run_result: str = ""
    next_run_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "schedule_time": self.schedule_time,
            "config": json.dumps(self.config) if self.config else "{}",
            "status": self.status,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "last_run_result": self.last_run_result,
            "next_run_time": self.next_run_time.isoformat() if self.next_run_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledTask":
        """从字典创建"""
        config_str = data.get("config", "{}")
        try:
            config = json.loads(config_str) if isinstance(config_str, str) else config_str
        except json.JSONDecodeError:
            config = {}
        
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            task_type=data.get("task_type", ""),
            schedule_time=data.get("schedule_time", ""),
            config=config,
            status=data.get("status", TaskStatus.PENDING),
            last_run_time=datetime.fromisoformat(data["last_run_time"]) if data.get("last_run_time") else None,
            last_run_result=data.get("last_run_result", ""),
            next_run_time=datetime.fromisoformat(data["next_run_time"]) if data.get("next_run_time") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            is_active=bool(data.get("is_active", True))
        )


# ==================== 钉钉通知模块 ====================


class DingTalkNotifier:
    """钉钉机器人通知
    
    支持加签安全设置（需要配置secret）
    """
    
    def __init__(self, webhook_url: str, secret: str = None):
        """初始化钉钉通知
        
        Args:
            webhook_url: 钉钉机器人Webhook URL
            secret: 签名密钥（如果机器人设置了加签验证）
        """
        self.webhook_url = webhook_url
        self.secret = secret
    
    def _generate_sign(self) -> tuple:
        """生成签名
        
        钉钉加签验证算法：
        1. timestamp = 当前时间戳（毫秒）
        2. stringToSign = timestamp + "\\n" + secret
        3. sign = HMAC-SHA256(secret, stringToSign) -> base64 -> URL编码
        
        Returns:
            tuple: (timestamp, sign)
        """
        if not self.secret:
            return None, None
        
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}"
        
        # HMAC-SHA256 签名
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        # Base64 编码
        sign = base64.b64encode(hmac_code).decode('utf-8')
        
        # URL 编码
        sign = urllib.parse.quote_plus(sign)
        
        return timestamp, sign
    
    def _get_signed_url(self) -> str:
        """获取带签名的完整URL
        
        Returns:
            str: 带签名参数的URL
        """
        if not self.secret:
            return self.webhook_url
        
        timestamp, sign = self._generate_sign()
        
        if timestamp and sign:
            return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
        
        return self.webhook_url
    
    def send_message(
        self,
        title: str,
        content: str,
        at_all: bool = False,
        at_mobiles: List[str] = None
    ) -> bool:
        """发送钉钉消息
        
        Args:
            title: 消息标题
            content: 消息内容
            at_all: 是否@所有人
            at_mobiles: @指定手机号列表
            
        Returns:
            bool: 发送是否成功
        """
        if not self.webhook_url:
            logger.warning("钉钉Webhook未配置，跳过通知")
            return False
        
        # 构建消息内容
        message = {
            "msgtype": "text",
            "text": {
                "content": f"{title}\n\n{content}"
            },
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": at_all
            }
        }
        
        try:
            # 获取带签名的URL
            url = self._get_signed_url()
            
            response = requests.post(
                url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    logger.info(f"钉钉消息发送成功: {title}")
                    return True
                else:
                    logger.warning(f"钉钉消息发送失败: {result.get('errmsg')}")
                    return False
            else:
                logger.warning(f"钉钉消息发送失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"钉钉消息发送异常: {e}")
            return False
    
    def send_task_notification(
        self,
        task_name: str,
        task_type: str,
        status: str,
        result: str = "",
        articles_info: List[Dict] = None
    ) -> bool:
        """发送任务执行通知
        
        Args:
            task_name: 任务名称
            task_type: 任务类型
            status: 执行状态
            result: 执行结果描述
            articles_info: 生成的文章信息列表
            
        Returns:
            bool: 发送是否成功
        """
        # 状态图标
        status_icons = {
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.RUNNING: "⏳"
        }
        
        status_icon = status_icons.get(status, "📄")
        
        # 构建消息内容
        content_lines = [
            f"任务类型: {task_type}",
            f"执行状态: {status_icon} {status}",
            f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        
        if result:
            content_lines.append(f"执行结果: {result}")
        
        if articles_info:
            content_lines.append("\n生成的文章:")
            for article in articles_info:
                title = article.get("title", "未命名")
                content_lines.append(f"  • {title}")
        
        content = "\n".join(content_lines)
        
        return self.send_message(
            title=f"【定时任务通知】{task_name}",
            content=content,
            at_all=False
        )


# ==================== 任务执行器 ====================

class TaskExecutor:
    """任务执行器"""
    
    def __init__(self, settings: any, db_manager: any):
        """初始化执行器
        
        Args:
            settings: 配置对象
            db_manager: 数据库管理器
        """
        self.settings = settings
        self.db_manager = db_manager
        self.dingtalk = None
        
        # 初始化钉钉通知
        if settings.has_dingtalk_config():
            self.dingtalk = DingTalkNotifier(settings.DINGTALK_WEBHOOK, settings.DINGTALK_SECRET)
    
    def execute_task(self, task: ScheduledTask) -> Dict:
        """执行任务
        
        Args:
            task: 定时任务
            
        Returns:
            Dict: 执行结果
        """
        logger.info(f"开始执行任务: {task.name} (类型: {task.task_type})")
        
        result = {
            "status": TaskStatus.RUNNING,
            "message": "",
            "articles": [],
            "errors": []
        }
        
        try:
            # 根据任务类型执行不同逻辑
            if task.task_type == TaskType.GENERATE_ARTICLE:
                result = self._execute_generate_article(task)
            elif task.task_type == TaskType.UPLOAD_WECHAT:
                result = self._execute_upload_wechat(task)
            elif task.task_type == TaskType.FULL_WORKFLOW:
                result = self._execute_full_workflow(task)
            else:
                result["status"] = TaskStatus.FAILED
                result["message"] = f"未知的任务类型: {task.task_type}"
                
        except Exception as e:
            result["status"] = TaskStatus.FAILED
            result["message"] = f"任务执行异常: {str(e)}"
            result["errors"].append(str(e))
            logger.error(f"任务执行异常: {task.name} - {e}")
        
        # 更新任务状态
        task.status = result["status"]
        task.last_run_time = datetime.now()
        task.last_run_result = result["message"]
        
        # 发送钉钉通知
        if self.dingtalk:
            self.dingtalk.send_task_notification(
                task_name=task.name,
                task_type=task.task_type,
                status=result["status"],
                result=result["message"],
                articles_info=result.get("articles")
            )
        
        return result
    
    def _execute_generate_article(self, task: ScheduledTask) -> Dict:
        """执行生成文章任务
        
        Args:
            task: 任务配置
            
        Returns:
            Dict: 执行结果
        """
        from core.ai_writer import AIWriter, AIWriterError
        
        result = {
            "status": TaskStatus.RUNNING,
            "message": "",
            "articles": [],
            "errors": []
        }
        
        config = task.config
        
        # 获取配置参数
        model = config.get("model", self.settings.DEFAULT_AI_MODEL)
        topics = config.get("topics", [])
        style = config.get("style", "科普")
        word_count = config.get("word_count", 800)
        template_id = config.get("template_id")
        
        if not topics:
            topics = ["今日热点", "科技前沿", "生活小技巧"]  # 默认主题
        
        logger.info(f"准备生成 {len(topics)} 篇文章，模型: {model}")
        
        # 初始化AI Writer（需要传入settings）
        try:
            writer = AIWriter(model=model, settings=self.settings)
        except Exception as e:
            result["status"] = TaskStatus.FAILED
            result["message"] = f"AI Writer初始化失败: {e}"
            return result
        
        # 生成文章
        success_count = 0
        
        for topic in topics:
            try:
                logger.info(f"正在生成文章: {topic}")
                
                article_result = writer.generate_article(
                    topic=topic,
                    style=style,
                    word_count=word_count
                )
                
                # 保存到数据库
                from database import Article
                
                new_article = Article(
                    title=article_result.get("title", topic),
                    content=article_result.get("content", ""),
                    digest=article_result.get("digest", ""),
                    style=style,
                    topic=topic,
                    ai_model=model,
                    template_id=template_id,
                    status="draft"
                )
                
                article_id = self.db_manager.save_article(new_article)
                
                result["articles"].append({
                    "id": article_id,
                    "title": article_result.get("title", topic),
                    "topic": topic
                })
                
                success_count += 1
                logger.info(f"文章生成成功: {article_result.get('title')}")
                
            except AIWriterError as e:
                result["errors"].append(f"生成失败 [{topic}]: {e.message}")
                logger.warning(f"文章生成失败: {topic} - {e.message}")
            except Exception as e:
                result["errors"].append(f"生成异常 [{topic}]: {str(e)}")
                logger.error(f"文章生成异常: {topic} - {e}")
        
        # 设置最终状态
        if success_count == len(topics):
            result["status"] = TaskStatus.COMPLETED
            result["message"] = f"成功生成 {success_count} 篇文章"
        elif success_count > 0:
            result["status"] = TaskStatus.COMPLETED
            result["message"] = f"部分成功: {success_count}/{len(topics)} 篇文章生成完成"
        else:
            result["status"] = TaskStatus.FAILED
            result["message"] = f"全部失败: {len(result['errors'])} 个错误"
        
        return result
    
    def _execute_upload_wechat(self, task: ScheduledTask) -> Dict:
        """执行上传微信任务
        
        Args:
            task: 任务配置
            
        Returns:
            Dict: 执行结果
        """
        from core.wechat_api import WeChatAPI, WeChatAPIError
        
        result = {
            "status": TaskStatus.RUNNING,
            "message": "",
            "articles": [],
            "errors": []
        }
        
        config = task.config
        
        # 获取配置参数
        article_ids = config.get("article_ids", [])
        auto_draft = config.get("auto_draft", True)  # 自动选择草稿文章
        
        if auto_draft and not article_ids:
            # 自动选择未上传的草稿文章
            draft_articles = self.db_manager.list_articles(status="draft", limit=5)
            article_ids = [a.id for a in draft_articles if a.cover_image_path]
            
            if not article_ids:
                result["status"] = TaskStatus.COMPLETED
                result["message"] = "没有可上传的草稿文章（需要封面图）"
                return result
        
        logger.info(f"准备上传 {len(article_ids)} 篇文章到微信")
        
        # 初始化微信API
        try:
            api = WeChatAPI(
                app_id=self.settings.WECHAT_APP_ID,
                app_secret=self.settings.WECHAT_APP_SECRET
            )
        except Exception as e:
            result["status"] = TaskStatus.FAILED
            result["message"] = f"微信API初始化失败: {e}"
            return result
        
        # 上传文章
        success_count = 0
        
        for article_id in article_ids:
            try:
                article = self.db_manager.get_article(article_id)
                
                if not article:
                    result["errors"].append(f"文章不存在: ID={article_id}")
                    continue
                
                if not article.cover_image_path:
                    result["errors"].append(f"文章缺少封面图: {article.title}")
                    logger.warning(f"文章缺少封面图，无法上传: ID={article.id}, title={article.title}")
                    continue
                
                logger.info(f"正在上传文章: {article.title}")
                
                # 上传封面图
                image_result = api.upload_image(article.cover_image_path)
                thumb_media_id = image_result.get("media_id")
                
                # 上传草稿
                draft_result = api.add_draft([{
                    "title": article.title,
                    "author": "AI助手",
                    "digest": article.digest or "",
                    "content": article.content,
                    "thumb_media_id": thumb_media_id
                }])
                
                media_id = draft_result.get("media_id")
                
                # 更新文章状态
                self.db_manager.update_article(article.id, {
                    "status": "uploaded",
                    "wechat_draft_id": media_id
                })
                
                result["articles"].append({
                    "id": article.id,
                    "title": article.title,
                    "media_id": media_id
                })
                
                success_count += 1
                logger.info(f"文章上传成功: {article.title} -> {media_id}")
                
            except WeChatAPIError as e:
                result["errors"].append(f"上传失败 [{article.title}]: {e.message}")
                logger.warning(f"文章上传失败: {article.title} - {e.message}")
            except Exception as e:
                result["errors"].append(f"上传异常 [{article.title}]: {str(e)}")
                logger.error(f"文章上传异常: {article.title} - {e}")
        
        # 设置最终状态
        if success_count == len(article_ids):
            result["status"] = TaskStatus.COMPLETED
            result["message"] = f"成功上传 {success_count} 篇文章到微信草稿箱"
        elif success_count > 0:
            result["status"] = TaskStatus.COMPLETED
            result["message"] = f"部分成功: {success_count}/{len(article_ids)} 篇文章上传完成"
        else:
            result["status"] = TaskStatus.FAILED
            result["message"] = f"全部失败: {len(result['errors'])} 个错误"
        
        return result
    
    def _execute_full_workflow(self, task: ScheduledTask) -> Dict:
        """执行完整工作流（生成 + 上传）
        
        Args:
            task: 任务配置
            
        Returns:
            Dict: 执行结果
        """
        result = {
            "status": TaskStatus.RUNNING,
            "message": "",
            "articles": [],
            "errors": []
        }
        
        # 第一步：生成文章
        gen_result = self._execute_generate_article(task)
        
        if gen_result["status"] == TaskStatus.FAILED:
            result["status"] = TaskStatus.FAILED
            result["message"] = f"生成文章失败: {gen_result['message']}"
            result["errors"] = gen_result["errors"]
            return result
        
        result["articles"] = gen_result["articles"]
        result["errors"].extend(gen_result["errors"])
        
        # 第二步：上传文章（如果有封面图）
        upload_config = {
            "article_ids": [a["id"] for a in gen_result["articles"]],
            "auto_draft": False
        }
        
        # 添加封面图（从配置中获取）
        cover_image_path = task.config.get("cover_image_path")
        if cover_image_path:
            # 为生成的文章添加封面图
            for article in result["articles"]:
                self.db_manager.update_article(article["id"], {
                    "cover_image_path": cover_image_path
                })
        
        upload_task = ScheduledTask(
            name=f"{task.name}_upload",
            task_type=TaskType.UPLOAD_WECHAT,
            config=upload_config
        )
        
        upload_result = self._execute_upload_wechat(upload_task)
        
        result["errors"].extend(upload_result["errors"])
        
        # 设置最终状态
        if upload_result["status"] == TaskStatus.COMPLETED:
            result["status"] = TaskStatus.COMPLETED
            result["message"] = f"完整流程执行成功: 生成并上传 {len(upload_result['articles'])} 篇文章"
        else:
            result["status"] = upload_result["status"]
            result["message"] = f"生成成功但上传失败: {upload_result['message']}"
        
        return result


# ==================== 定时任务调度器 ====================

class Scheduler:
    """定时任务调度器"""
    
    def __init__(self, db_manager: any, settings: any):
        """初始化调度器
        
        Args:
            db_manager: 数据库管理器
            settings: 配置对象
        """
        self.db_manager = db_manager
        self.settings = settings
        self.executor = TaskExecutor(settings, db_manager)
        self._running = False
        self._thread = None
        self._tasks = {}
        
        logger.info("定时任务调度器初始化完成")
    
    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        logger.info("定时任务调度器已启动")
        
        # 发送启动通知
        if self.settings.has_dingtalk_config():
            dingtalk = DingTalkNotifier(self.settings.DINGTALK_WEBHOOK)
            dingtalk.send_message(
                title="【系统通知】定时任务调度器已启动",
                content=f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n调度器已开始监控定时任务..."
            )
    
    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        
        logger.info("定时任务调度器已停止")
        
        # 发送停止通知
        if self.settings.has_dingtalk_config():
            dingtalk = DingTalkNotifier(self.settings.DINGTALK_WEBHOOK)
            dingtalk.send_message(
                title="【系统通知】定时任务调度器已停止",
                content=f"停止时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
    
    def _run_loop(self):
        """调度循环"""
        logger.info("调度循环开始运行")
        
        while self._running:
            try:
                # 检查需要执行的任务
                self._check_and_execute_tasks()
                
                # 每60秒检查一次
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"调度循环异常: {e}")
                time.sleep(60)
    
    def _check_and_execute_tasks(self):
        """检查并执行到期任务"""
        now = datetime.now()
        
        # 获取所有活跃的任务
        try:
            # 需要在数据库中添加查询活跃任务的方法
            # 这里暂时模拟
            pass
        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
    
    def execute_task_now(self, task_id: int) -> Dict:
        """立即执行指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict: 执行结果
        """
        try:
            # 获取任务
            task = self._get_task_from_db(task_id)
            
            if not task:
                return {
                    "status": TaskStatus.FAILED,
                    "message": f"任务不存在: ID={task_id}"
                }
            
            if not task.is_active:
                return {
                    "status": TaskStatus.FAILED,
                    "message": "任务已禁用"
                }
            
            # 执行任务
            result = self.executor.execute_task(task)
            
            # 更新任务状态到数据库
            self._update_task_in_db(task)
            
            return result
            
        except Exception as e:
            logger.error(f"执行任务失败: {task_id} - {e}")
            return {
                "status": TaskStatus.FAILED,
                "message": f"执行异常: {str(e)}"
            }
    
    def _get_task_from_db(self, task_id: int) -> Optional[ScheduledTask]:
        """从数据库获取任务"""
        # 需要在数据库管理器中实现
        # 这里暂时返回None
        return None
    
    def _update_task_in_db(self, task: ScheduledTask):
        """更新任务到数据库"""
        # 需要在数据库管理器中实现
        pass
    
    def create_task(
        self,
        name: str,
        task_type: str,
        schedule_time: str,
        config: Dict
    ) -> ScheduledTask:
        """创建新任务
        
        Args:
            name: 任务名称
            task_type: 任务类型
            schedule_time: 执行时间
            config: 任务配置
            
        Returns:
            ScheduledTask: 创建的任务对象
        """
        task = ScheduledTask(
            name=name,
            task_type=task_type,
            schedule_time=schedule_time,
            config=config,
            status=TaskStatus.PENDING,
            is_active=True,
            created_at=datetime.now()
        )
        
        # 解析执行时间，计算下次执行时间
        task.next_run_time = self._parse_schedule_time(schedule_time)
        
        # 保存到数据库
        # task_id = self.db_manager.save_scheduled_task(task)
        # task.id = task_id
        
        logger.info(f"创建任务: {name} (类型: {task_type}, 时间: {schedule_time})")
        
        return task
    
    def _parse_schedule_time(self, schedule_time: str) -> Optional[datetime]:
        """解析执行时间
        
        支持格式：
        - "HH:MM" - 每天指定时间
        - "HH:MM,HH:MM" - 每天多个时间
        - "cron表达式" - 使用cron格式
        
        Args:
            schedule_time: 时间表达式
            
        Returns:
            datetime: 下次执行时间
        """
        try:
            # 简单时间格式 HH:MM
            if ":" in schedule_time and "," not in schedule_time:
                hour, minute = schedule_time.split(":")
                now = datetime.now()
                next_run = now.replace(
                    hour=int(hour),
                    minute=int(minute),
                    second=0,
                    microsecond=0
                )
                
                # 如果时间已过，设置为明天
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                return next_run
            
            # TODO: 支持更多格式
            
        except Exception as e:
            logger.warning(f"解析时间失败: {schedule_time} - {e}")
        
        return None


# ==================== 单例调度器 ====================

_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    """获取调度器实例（单例模式）"""
    global _scheduler
    
    if _scheduler is None:
        from config import get_settings
        from database import get_db_manager
        
        settings = get_settings()
        db_manager = get_db_manager()
        
        _scheduler = Scheduler(db_manager, settings)
    
    return _scheduler


def send_dingtalk_notification(
    title: str,
    content: str,
    at_all: bool = False
) -> bool:
    """发送钉钉通知（便捷函数）
    
    Args:
        title: 消息标题
        content: 消息内容
        at_all: 是否@所有人
        
    Returns:
        bool: 发送是否成功
    """
    from config import get_settings
    
    settings = get_settings()
    
    if not settings.has_dingtalk_config():
        logger.warning("钉钉通知未配置")
        return False
    
    notifier = DingTalkNotifier(settings.DINGTALK_WEBHOOK, settings.DINGTALK_SECRET)
    return notifier.send_message(title, content, at_all)