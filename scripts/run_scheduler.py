"""
定时任务调度服务
独立运行的调度服务，用于执行定时任务

使用方法：
    python scripts/run_scheduler.py

功能：
    - 后台运行定时任务调度器
    - 自动检查并执行到期任务
    - 执行完成后发送钉钉通知
"""
import sys
import os
import time
import signal
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(project_root / 'data' / 'scheduler.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务调度服务"""
    
    def __init__(self):
        """初始化调度服务"""
        self.running = False
        self.check_interval = 60  # 检查间隔（秒）
        
        # 导入必要模块
        try:
            from config import get_settings
            from database import get_db_manager
            from core.scheduler import TaskExecutor, DingTalkNotifier
            
            self.settings = get_settings()
            self.db = get_db_manager()
            self.executor = TaskExecutor(self.settings, self.db)
            
            # 初始化钉钉通知
            if self.settings.has_dingtalk_config():
                self.dingtalk = DingTalkNotifier(self.settings.DINGTALK_WEBHOOK, self.settings.DINGTALK_SECRET)
            else:
                self.dingtalk = None
            
            logger.info("调度服务初始化完成")
            
        except Exception as e:
            logger.error(f"调度服务初始化失败: {e}")
            raise
    
    def start(self):
        """启动调度服务"""
        self.running = True
        
        logger.info("=" * 50)
        logger.info("定时任务调度服务启动")
        logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"检查间隔: {self.check_interval} 秒")
        logger.info("=" * 50)
        
        # 发送启动通知
        if self.dingtalk:
            self.dingtalk.send_message(
                title="【系统通知】定时任务调度服务已启动",
                content=f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n服务开始监控定时任务..."
            )
        
        # 运行主循环
        self._run_loop()
    
    def stop(self):
        """停止调度服务"""
        self.running = False
        
        logger.info("=" * 50)
        logger.info("定时任务调度服务停止")
        logger.info(f"停止时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)
        
        # 发送停止通知
        if self.dingtalk:
            self.dingtalk.send_message(
                title="【系统通知】定时任务调度服务已停止",
                content=f"停止时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
    
    def _run_loop(self):
        """主调度循环"""
        while self.running:
            try:
                # 检查待执行任务
                self._check_tasks()
                
                # 等待下次检查
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，准备停止...")
                self.stop()
                break
                
            except Exception as e:
                logger.error(f"调度循环异常: {e}")
                time.sleep(10)  # 异常后等待10秒
    
    def _check_tasks(self):
        """检查并执行到期任务"""
        try:
            # 获取待执行任务
            pending_tasks = self.db.get_pending_tasks_to_run()
            
            if not pending_tasks:
                logger.debug("当前无待执行任务")
                return
            
            logger.info(f"发现 {len(pending_tasks)} 个待执行任务")
            
            # 执行每个任务
            for task_data in pending_tasks:
                self._execute_task(task_data)
                
        except Exception as e:
            logger.error(f"检查任务失败: {e}")
    
    def _execute_task(self, task_data: dict):
        """执行单个任务"""
        from core.scheduler import ScheduledTask
        
        task_id = task_data.get("id")
        task_name = task_data.get("name", "未命名")
        
        logger.info(f"开始执行任务: {task_name} (ID: {task_id})")
        
        # 更新任务状态为运行中
        self.db.update_scheduled_task(task_id, {
            "status": "running"
        })
        
        try:
            # 创建任务对象
            task = ScheduledTask.from_dict(task_data)
            
            # 执行任务
            result = self.executor.execute_task(task)
            
            # 更新任务状态
            update_data = {
                "status": result.get("status", "completed"),
                "last_run_time": datetime.now().isoformat(),
                "last_run_result": result.get("message", "")
            }
            
            # 计算下次执行时间（如果是循环任务）
            schedule_time = task_data.get("schedule_time", "")
            if schedule_time.startswith("every_"):
                # 解析间隔
                try:
                    hours = int(schedule_time.split("_")[1].replace("h", ""))
                    update_data["next_run_time"] = (
                        datetime.now() + timedelta(hours=hours)
                    ).isoformat()
                except:
                    pass
            elif ":" in schedule_time and "," not in schedule_time:
                # 每天定时执行，计算明天的时间
                try:
                    hour, minute = schedule_time.split(":")
                    next_run = datetime.now().replace(
                        hour=int(hour), minute=int(minute), second=0
                    ) + timedelta(days=1)
                    update_data["next_run_time"] = next_run.isoformat()
                except:
                    pass
            
            self.db.update_scheduled_task(task_id, update_data)
            
            logger.info(f"任务执行完成: {task_name} - {result.get('status')}")
            
        except Exception as e:
            logger.error(f"任务执行失败: {task_name} - {e}")
            
            # 更新失败状态
            self.db.update_scheduled_task(task_id, {
                "status": "failed",
                "last_run_time": datetime.now().isoformat(),
                "last_run_result": f"执行异常: {str(e)}"
            })


def main():
    """主入口"""
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser(description="定时任务调度服务")
    parser.add_argument("--interval", type=int, default=60, help="检查间隔（秒）")
    parser.add_argument("--once", action="store_true", help="只执行一次检查")
    
    args = parser.parse_args()
    
    # 创建服务
    service = SchedulerService()
    service.check_interval = args.interval
    
    if args.once:
        # 单次执行
        logger.info("执行单次任务检查...")
        service._check_tasks()
        logger.info("检查完成")
    else:
        # 持续运行
        # 注册信号处理
        signal.signal(signal.SIGINT, lambda s, f: service.stop())
        signal.signal(signal.SIGTERM, lambda s, f: service.stop())
        
        service.start()


if __name__ == "__main__":
    main()