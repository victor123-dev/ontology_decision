import threading
import time
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from cachetools import TTLCache
from app.models.drive_logic import DriveLogic, Task
from app.models.agent import Agent, Capability
from app.models.data_sensing import DataSensingConfig
from app.utils.db_client import Base, create_engine, sessionmaker
from app.config import settings
from app.utils.logger import get_logger
import traceback

logger = get_logger(__name__)


class DriveEngine:
    """数据驱动引擎 - 完整实现"""
    
    def __init__(self):
        self.is_running = False
        self.threads = []
        self.event_queue = []
        self.event_lock = threading.Lock()
        
        self.logic_cache = TTLCache(maxsize=100, ttl=300)
        
        self.stats = {
            'events_received': 0,
            'logics_matched': 0,
            'tasks_assigned': 0,
            'errors': 0
        }
    
    def start(self):
        """启动驱动引擎"""
        self.is_running = True
        
        process_thread = threading.Thread(target=self._process_events)
        process_thread.daemon = True
        process_thread.start()
        self.threads.append(process_thread)
        
        refresh_thread = threading.Thread(target=self._refresh_logic_cache)
        refresh_thread.daemon = True
        refresh_thread.start()
        self.threads.append(refresh_thread)
        
        logger.info("数据驱动引擎启动")
        logger.info("驱动引擎配置: 逻辑缓存(100条目, 5分钟)")
    
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
        logger.info(f"分配任务数: {self.stats['tasks_assigned']}")
        logger.info(f"错误数: {self.stats['errors']}")
        logger.info(f"逻辑缓存: {len(self.logic_cache)}/{self.logic_cache.maxsize} 条目")
        logger.info("=" * 60)
    
    def _refresh_logic_cache(self):
        """定期刷新逻辑缓存"""
        while self.is_running:
            time.sleep(300)
            if self.is_running:
                self._load_drive_logics()
    
    def _get_db_session(self):
        """获取数据库会话"""
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    def _load_drive_logics(self):
        """从数据库加载驱动逻辑"""
        try:
            db = self._get_db_session()
            try:
                logics = db.query(DriveLogic).all()
                for logic in logics:
                    self.logic_cache[logic.id] = logic
                logger.info(f"已加载 {len(logics)} 条驱动逻辑到缓存")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"加载驱动逻辑失败: {str(e)}")
    
    def handle_event(self, event: Dict[str, Any]):
        """处理事件"""
        self.stats['events_received'] += 1
        
        with self.event_lock:
            self.event_queue.append(event)
        
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
        """处理单个事件"""
        try:
            event_type = event.get('type')
            event_data = event.get('data', {})
            config_id = event_data.get('config_id')
            
            db = self._get_db_session()
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
                
                logger.info(f"事件 {event['type']} 匹配到 {len(matched_logics)} 条驱动逻辑")
                self.stats['logics_matched'] += len(matched_logics)
                
                for logic in matched_logics:
                    self._execute_logic(logic, event, db)
                    
            finally:
                db.close()
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"处理事件出错: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _execute_logic(self, logic: DriveLogic, event: Dict[str, Any], db):
        """执行驱动逻辑"""
        try:
            config = logic.config or {}
            logic_type = logic.type
            
            logger.info(f"执行驱动逻辑: {logic.name} (类型: {logic_type})")
            
            # 预处理（可选）
            processed_data = event.get('data', {})
            trigger_tasks = True
            
            if logic_type == 'script' and config.get('script_content'):
                result = self._run_preprocess_script(config.get('script_content'), event)
                # 检查脚本返回值
                if isinstance(result, tuple) and len(result) == 2:
                    # 脚本返回 (bool, dict) 形式
                    trigger_tasks = result[0]
                    processed_data = result[1]
                else:
                    # 兼容旧格式，只返回数据
                    processed_data = result
            elif logic_type == 'first_order' and config.get('pre_condition'):
                # 处理一阶函数的前置条件
                pre_condition = config.get('pre_condition')
                try:
                    # 评估前置条件表达式
                    # 创建一个包装类来支持点号语法访问字典
                    class DictWrapper:
                        def __init__(self, data):
                            self.__dict__ = data
                    
                    local_vars = {
                        'data': DictWrapper(processed_data),
                        'event': DictWrapper(event)
                    }
                    trigger_tasks = eval(pre_condition, {}, local_vars)
                except Exception as e:
                    logger.error(f"评估前置条件失败: {str(e)}")
                    trigger_tasks = False
            
            # 只有当条件满足时才触发任务
            if trigger_tasks:
                # 关联的任务
                tasks = logic.tasks
                if tasks:
                    # 更新事件数据为处理后的数据
                    event['data'] = processed_data
                    self._assign_tasks(tasks, event, db)
                else:
                    logger.warning(f"驱动逻辑 {logic.name} 没有关联任务")
            else:
                logger.info(f"驱动逻辑 {logic.name} 条件不满足，跳过任务触发")
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"执行驱动逻辑失败: {logic.name}, 错误: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _run_preprocess_script(self, script_content: str, event: Dict[str, Any]):
        """运行预处理脚本"""
        try:
            safe_globals = {
                '__builtins__': {
                    'print': print, 'str': str, 'int': int, 'float': float,
                    'bool': bool, 'list': list, 'dict': dict, 'len': len,
                    'range': range, 'enumerate': enumerate, 'zip': zip,
                    'map': map, 'filter': filter, 'sorted': sorted,
                    'min': min, 'max': max, 'sum': sum, 'abs': abs, 'round': round,
                }
            }
            
            local_vars = {'event': event.copy()}
            exec(script_content, safe_globals, local_vars)
            
            return local_vars.get('result', event.get('data', {}))
        except Exception as e:
            logger.error(f"预处理脚本执行失败: {str(e)}")
            return event.get('data', {})
    
    def _assign_tasks(self, tasks: List[Task], event: Dict[str, Any], db):
        """分配任务给Agent"""
        try:
            # 获取所有可用的Agent及其能力
            agents = db.query(Agent).filter(Agent.status == 'active').all()
            
            for task in tasks:
                matched_agent = None
                
                # 根据任务的能力类型匹配Agent
                for agent in agents:
                    agent_capability_types = [cap.task_type for cap in agent.capabilities]
                    if task.capability_type in agent_capability_types:
                        matched_agent = agent
                        break
                
                # 分配任务
                if matched_agent:
                    task.assigned_agent = matched_agent
                    task.status = 'assigned'
                    task.result = {
                        'event': event,
                        'assigned_at': datetime.now().isoformat()
                    }
                    logger.info(f"任务 '{task.name}' 已分配给 Agent: {matched_agent.name}")
                    self.stats['tasks_assigned'] += 1
                else:
                    task.status = 'pending'
                    logger.warning(f"没有找到支持能力类型 '{task.capability_type}' 的Agent，任务 '{task.name}' 等待分配")
                
                db.commit()
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"分配任务失败: {str(e)}")
            logger.error(traceback.format_exc())


drive_engine = DriveEngine()
