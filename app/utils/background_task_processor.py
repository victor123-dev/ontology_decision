import threading
import queue
import time
from typing import Callable, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from app.utils.logger import get_logger

logger = get_logger(__name__)

class BackgroundTaskProcessor:
    """轻量级后台任务处理器，用于处理异步任务如自然语言描述生成"""
    
    def __init__(self, max_workers: int = 3):
        self.is_running = False
        self.task_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="bg_task")
        self.main_thread: Optional[threading.Thread] = None
        
    def start(self):
        """启动后台任务处理器"""
        if self.is_running:
            return
            
        self.is_running = True
        self.main_thread = threading.Thread(target=self._process_tasks, daemon=True)
        self.main_thread.start()
        logger.info("后台任务处理器已启动")
        
    def stop(self):
        """停止后台任务处理器"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.main_thread:
            self.main_thread.join(timeout=5)
        self.executor.shutdown(wait=True)
        logger.info("后台任务处理器已停止")
        
    def submit_task(self, func: Callable, *args, **kwargs):
        """提交任务到后台队列"""
        if not self.is_running:
            logger.warning("后台任务处理器未运行，任务将被忽略")
            return
            
        task = {
            'func': func,
            'args': args,
            'kwargs': kwargs
        }
        self.task_queue.put(task)
        logger.debug(f"任务已提交到队列，当前队列大小: {self.task_queue.qsize()}")
        
    def _process_tasks(self):
        """处理任务队列的主循环"""
        while self.is_running:
            try:
                # 从队列中获取任务，超时1秒以允许检查is_running标志
                task = self.task_queue.get(timeout=1)
                
                # 提交任务到线程池执行
                future = self.executor.submit(self._execute_task, task)
                future.add_done_callback(self._task_completed)
                
            except queue.Empty:
                # 队列为空，继续循环
                continue
            except Exception as e:
                logger.error(f"处理任务队列时发生错误: {e}")
                
    def _execute_task(self, task: dict) -> Any:
        """执行单个任务"""
        try:
            func = task['func']
            args = task['args']
            kwargs = task['kwargs']
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"执行任务时发生错误: {e}")
            raise
            
    def _task_completed(self, future):
        """任务完成回调"""
        try:
            result = future.result()
            logger.debug(f"任务执行成功: {result}")
        except Exception as e:
            logger.error(f"任务执行失败: {e}")

# 全局后台任务处理器实例
background_task_processor = BackgroundTaskProcessor()