import threading
import time
from typing import Dict, Any, List
from datetime import datetime
from app.models.drive_logic import DriveLogic
from app.models.drive_log import DriveLog
from app.utils.logger import get_logger
from .logic_executor import LogicExecutor
from app.utils.shared_utils import get_db_session, log_event_with_parent

logger = get_logger(__name__)


class DriveEngine:
    """数据驱动引擎 - 完整实现"""
    
    def __init__(self):
        self.is_running = False
        self.threads = []
        self.event_queue = []
        self.event_lock = threading.Lock()
        self.logic_executor = LogicExecutor()
        
        self.stats = {
            'events_received': 0,
            'logics_matched': 0,
            'actions_executed': 0,
            'errors': 0
        }
    
    def start(self):
        """启动驱动引擎"""
        self.is_running = True
        
        process_thread = threading.Thread(target=self._process_events)
        process_thread.daemon = True
        process_thread.start()
        self.threads.append(process_thread)
        
        logger.info("数据驱动引擎启动")
    
    def stop(self):
        """停止驱动引擎"""
        self.is_running = False
        for thread in self.threads:
            thread.join()
        logger.info("数据驱动引擎停止")
        self._print_stats()
    
    def _print_stats(self):
        """打印统计信息"""
        logger.info("=" * 60)
        logger.info("数据驱动引擎统计信息")
        logger.info("=" * 60)
        logger.info(f"接收事件数: {self.stats['events_received']}")
        logger.info(f"匹配逻辑数: {self.stats['logics_matched']}")
        logger.info(f"执行行动数: {self.stats['actions_executed']}")
        logger.info(f"错误数: {self.stats['errors']}")
        logger.info("=" * 60)


    
    def handle_event(self, event: Dict[str, Any]):
        """处理事件"""
        self.stats['events_received'] += 1
        
        with self.event_lock:
            self.event_queue.append(event)
        
        trace_id = event.get('trace_id')
        logger.info(f"接收事件: {event['type']}, 模型: {event.get('model_id')}")
    
    def _process_events(self):
        """处理事件队列"""
        while self.is_running:
            if self.event_queue:
                with self.event_lock:
                    event = self.event_queue.pop(0)
                self._process_event(event)
            time.sleep(0.1)
    
    def _process_event(self, event: Dict[str, Any]):
        """处理单个事件（增强版）"""
        try:
            event_type = event.get('type')
            event_data = event.get('data', {})
            config_id = event_data.get('config_id')
            parent_log_id = event.get('log_id')  # 获取父日志ID
            
            db = get_db_session()
            try:
                logics = db.query(DriveLogic).all()
                
                matched_logics = []
                for logic in logics:
                    event_ids = [e.id for e in logic.events]
                    if config_id in event_ids:
                        matched_logics.append(logic)
                
                if not matched_logics:
                    for logic in logics:
                        if not logic.events:
                            matched_logics.append(logic)
                
                trace_id = event.get('trace_id')
                logger.info(f"事件 {event['type']} 匹配到 {len(matched_logics)} 条驱动逻辑")
                self.stats['logics_matched'] += len(matched_logics)
                
                # 记录驱动逻辑匹配日志
                drive_log_id = log_event_with_parent(
                    'info', 'drive_logic', 
                    f"事件 {event['type']} 匹配到 {len(matched_logics)} 条驱动逻辑", 
                    {'event_type': event['type'], 'matched_count': len(matched_logics)}, 
                    trace_id, parent_log_id
                )
                
                for logic in matched_logics:
                    self.logic_executor.execute_logic(logic, event, db, trace_id, drive_log_id)
                    
            finally:
                db.close()
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"处理事件出错: {str(e)}")
            logger.error(traceback.format_exc())

drive_engine = DriveEngine()