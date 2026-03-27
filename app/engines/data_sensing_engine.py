import json
import threading
import time
from typing import Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from concurrent.futures import ThreadPoolExecutor
from app.models.data_sensing import DataSensingConfig
from app.models.business_model import BusinessModel
from app.models.data_source import DataSource
from app.utils.db_client import DBClient
from app.utils.logger import get_logger
from .cache_manager import CacheManager
from app.utils.shared_utils import get_db_session, log_event_with_parent

logger = get_logger(__name__)


class DataSensingEngine:
    """数据感知引擎 - 使用APScheduler排程系统"""
    
    def __init__(self):
        self.is_running = False
        self.event_callbacks = []
        
        # APScheduler调度器
        self.scheduler = BackgroundScheduler()
        
        # 线程池 - 用于执行检查任务
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="sensing_")
        
        # 缓存管理器
        self.cache_manager = CacheManager()
        
        # 配置任务映射 - 记录config_id对应的job_id
        self.config_jobs: Dict[int, str] = {}
        
        # 统计信息
        self.stats = {
            'events_triggered': 0,
            'tasks_executed': 0,
            'tasks_failed': 0,
            'db_queries': 0
        }
        
        # 锁 - 用于线程安全地管理任务
        self._lock = threading.RLock()
    
    def start(self):
        """启动数据感知引擎"""
        self.is_running = True
        
        # 启动调度器
        self.scheduler.start()
        
        # 加载所有配置并创建调度任务
        self._load_all_configs()
        
        logger.info("数据感知引擎启动")
        logger.info(f"调度器已启动，线程池大小: 10")
    
    def stop(self):
        """停止数据感知引擎"""
        self.is_running = False
        
        # 关闭调度器
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        
        logger.info("数据感知引擎停止")
        self._print_stats()
    

    def register_event_callback(self, callback):
        """注册事件回调函数"""
        self.event_callbacks.append(callback)
    
    def _print_stats(self):
        """打印统计信息"""

        logger.info("=" * 60)
        logger.info("数据感知引擎统计信息")
        logger.info("=" * 60)
        logger.info(f"事件触发次数: {self.stats['events_triggered']}")
        logger.info(f"任务执行次数: {self.stats['tasks_executed']}")
        logger.info(f"任务失败次数: {self.stats['tasks_failed']}")
        logger.info(f"数据库查询次数: {self.stats['db_queries']}")
        logger.info(f"调度任务数: {len(self.config_jobs)}")
        logger.info(f"数据状态缓存: {len(self.cache_manager.data_states)} 条目")
        logger.info(f"阈值状态缓存: {len(self.cache_manager.threshold_states)} 条目")
        logger.info("=" * 60)
    

    def _load_all_configs(self):
        """加载所有配置并创建调度任务"""
        try:
            db = get_db_session()
            try:
                # 只加载生效的配置
                configs = db.query(DataSensingConfig).filter(DataSensingConfig.status == True).all()
                for config in configs:
                    self._add_config_job(config)
                logger.info(f"已加载 {len(configs)} 个生效的数据感知配置")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
    
    def _add_config_job(self, config: DataSensingConfig):
        """为配置添加调度任务"""
        with self._lock:
            config_id = config.id
            
            # 如果已存在任务，先移除
            if config_id in self.config_jobs:
                self._remove_config_job(config_id)
            
            check_interval = config.config.get('check_interval', 5)
            
            # 创建触发器
            trigger = IntervalTrigger(seconds=check_interval)
            
            # 添加任务
            job = self.scheduler.add_job(
                func=self._execute_config_check,
                trigger=trigger,
                args=[config_id],
                id=f"config_{config_id}",
                replace_existing=True,
                max_instances=1,  # 同一配置同时只能执行一个实例
                misfire_grace_time=check_interval  # 错过执行后的宽限时间
            )
            
            self.config_jobs[config_id] = job.id
            logger.debug(f"已为配置 '{config.name}' (ID: {config_id}) 创建调度任务，间隔: {check_interval}秒")
    
    def _remove_config_job(self, config_id: int):
        """移除配置的调度任务"""
        with self._lock:
            if config_id in self.config_jobs:
                job_id = self.config_jobs[config_id]
                try:
                    self.scheduler.remove_job(job_id)
                except Exception as e:
                    logger.warning(f"移除任务失败: {e}")
                del self.config_jobs[config_id]
                logger.debug(f"已移除配置 {config_id} 的调度任务")
    
    def _execute_config_check(self, config_id: int):
        """执行配置检查（在线程池中运行）"""
        self.executor.submit(self._check_config_wrapper, config_id)
    
    def _check_config_wrapper(self, config_id: int):
        """包装配置检查，添加错误处理"""
        try:
            self.stats['tasks_executed'] += 1
            
            db = get_db_session()
            try:
                config = db.query(DataSensingConfig).filter(DataSensingConfig.id == config_id).first()
                if not config:
                    logger.warning(f"配置不存在: {config_id}")
                    return
                
                # 检查配置是否生效
                if not config.status:
                    logger.debug(f"配置未生效，跳过执行: {config_id}")
                    return
                
                if config.type == 'data_change':
                    self._monitor_data_change(config, db)
                elif config.type == 'threshold':
                    self._monitor_threshold(config, db)
                    
            finally:
                db.close()
                
        except Exception as e:
            self.stats['tasks_failed'] += 1
            logger.error(f"执行配置检查失败 (config_id: {config_id}): {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def add_config(self, config: DataSensingConfig):
        """添加新配置（动态添加调度任务）"""
        if config.status:
            self._add_config_job(config)
            logger.info(f"动态添加配置 '{config.name}' (ID: {config.id}) 的调度任务")
        else:
            logger.info(f"配置 '{config.name}' (ID: {config.id}) 未生效，跳过添加调度任务")
    
    def update_config(self, config: DataSensingConfig):
        """更新配置（重新创建调度任务）"""
        if config.status:
            self._add_config_job(config)
            logger.info(f"更新配置 '{config.name}' (ID: {config.id}) 的调度任务")
        else:
            # 如果配置变为未生效，移除调度任务
            self._remove_config_job(config.id)
            logger.info(f"配置 '{config.name}' (ID: {config.id}) 未生效，移除调度任务")
    
    def remove_config(self, config_id: int):
        """移除配置（删除调度任务）"""
        self._remove_config_job(config_id)
        # 清理相关缓存
        if config_id in self.cache_manager.data_states:
            del self.cache_manager.data_states[config_id]
        if config_id in self.cache_manager.threshold_states:
            del self.cache_manager.threshold_states[config_id]
        logger.info(f"移除配置 {config_id} 的调度任务和相关缓存")
    
    def _monitor_data_change(self, config: DataSensingConfig, db):
        """监控数据变化"""
        try:
            model = db.query(BusinessModel).filter(BusinessModel.id == config.model_id).first()
            if not model:
                logger.warning(f"业务模型不存在: {config.model_id}")
                return
            
            data_source = db.query(DataSource).filter(DataSource.id == model.data_source_id).first()
            if not data_source:
                logger.warning(f"数据源不存在: {model.data_source_id}")
                return
            
            trigger_conditions = config.config.get('trigger_conditions', ['create', 'update', 'delete'])
            monitored_fields = config.config.get('monitored_fields', [])
            primary_key = model.primary_key_id or 'id'
            
            # 构建查询缓存键
            query_cache_key = f"{model.id}:{','.join(monitored_fields) if monitored_fields else '*'}"
            
            client = DBClient(data_source.type, data_source.connection_string)
            client.connect()
            
            try:
                table_name = model.id
                
                # 执行查询 - 总是查询所有字段，确保记录完整
                fields_str = '*'
                query = f"SELECT {fields_str} FROM {table_name}"
                current_data = client.execute_query(query)
                self.stats['db_queries'] += 1
                
                current_records = {self.cache_manager.get_record_key(row, primary_key): row for row in current_data}
                
                config_id = config.id
                last_state = self.cache_manager.get_data_state(config_id) or {}
                last_records = last_state.get('records', {})
                
                # 初始化变化记录变量
                created_records = []
                deleted_records = []
                updated_records = []
                
                # 调试日志：记录当前和上次的数据状态
                current_record_count = len(current_records)
                last_record_count = len(last_records)
                logger.debug(f"配置 {config_id} 数据状态 - 当前记录数: {current_record_count}, 上次记录数: {last_record_count}")
                
                # 检测新增
                if 'create' in trigger_conditions:
                    created_records = []
                    for key, record in current_records.items():
                        if key not in last_records:
                            created_records.append({
                                "record": record
                            })
                    
                    if created_records:
                        logger.info(f"检测到 {len(created_records)} 条新增记录，触发创建事件")
                        self.trigger_event(
                            config.name,
                            config.model_id,
                            {
                                "config_id": config.id,
                                "config_name": config.name,
                                "change_type": "create",
                                "monitored_fields": monitored_fields,
                                "affected_records": created_records,
                                "affected_count": len(created_records)
                            }
                        )
                
                # 检测删除
                if 'delete' in trigger_conditions:
                    deleted_records = []
                    for key, record in last_records.items():
                        if key not in current_records:
                            deleted_records.append({
                                "record": record
                            })
                    
                    if deleted_records:
                        logger.info(f"检测到 {len(deleted_records)} 条删除记录，触发删除事件")
                        self.trigger_event(
                            config.name,
                            config.model_id,
                            {
                                "config_id": config.id,
                                "config_name": config.name,
                                "change_type": "delete",
                                "monitored_fields": monitored_fields,
                                "affected_records": deleted_records,
                                "affected_count": len(deleted_records)
                            }
                        )
                
                # 检测更新
                if 'update' in trigger_conditions:
                    updated_records = []
                    for key, current_record in current_records.items():
                        if key in last_records:
                            last_record = last_records[key]
                            
                            changed_fields = []
                            fields_to_check = monitored_fields if monitored_fields else current_record.keys()
                            
                            for field in fields_to_check:
                                if field == primary_key:
                                    continue
                                current_value = current_record.get(field)
                                last_value = last_record.get(field)
                                if current_value != last_value:
                                    changed_fields.append({
                                        "field": field,
                                        "old_value": last_value,
                                        "new_value": current_value
                                    })
                            
                            if changed_fields:
                                updated_records.append({
                                    "record": current_record,
                                    "changed_fields": changed_fields
                                })
                    
                    if updated_records:
                        logger.info(f"检测到 {len(updated_records)} 条更新记录，触发更新事件")
                        # 记录具体的变更字段用于调试
                        for record_info in updated_records[:3]:  # 只记录前3条的详细信息
                            changed_fields = record_info.get('changed_fields', [])
                            if changed_fields:
                                field_names = [f['field'] for f in changed_fields]
                                logger.debug(f"记录变更字段: {field_names}")
                        self.trigger_event(
                            config.name,
                            config.model_id,
                            {
                                "config_id": config.id,
                                "config_name": config.name,
                                "change_type": "update",
                                "monitored_fields": monitored_fields,
                                "affected_records": updated_records,
                                "affected_count": len(updated_records)
                            }
                        )
                
                # 检查是否有任何变化
                has_changes = (created_records or deleted_records or updated_records)
                
                if not has_changes:
                    logger.debug(f"配置 {config_id} 未检测到数据变化，跳过事件触发")
                
                # 更新状态缓存
                state_data = {
                    'records': current_records,
                    'record_count': len(current_data)
                }
                self.cache_manager.set_data_state(config_id, state_data)
                
            finally:
                client.close()
                
        except Exception as e:
            logger.error(f"监控数据变化出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _monitor_threshold(self, config: DataSensingConfig, db):
        """监控阈值触发"""
        try:
            model = db.query(BusinessModel).filter(BusinessModel.id == config.model_id).first()
            if not model:
                logger.warning(f"业务模型不存在: {config.model_id}")
                return
            
            data_source = db.query(DataSource).filter(DataSource.id == model.data_source_id).first()
            if not data_source:
                logger.warning(f"数据源不存在: {model.data_source_id}")
                return
            
            config_dict = config.config
            monitored_field = config_dict.get('monitored_field')
            threshold_type = config_dict.get('threshold_type')
            operator = config_dict.get('operator')
            primary_key = model.primary_key_id or 'id'
            
            if not monitored_field or not threshold_type or not operator:
                logger.warning(f"阈值配置不完整: {config.name}")
                return
            
            client = DBClient(data_source.type, data_source.connection_string)
            client.connect()
            
            try:
                table_name = model.id
                
                query_fields = [primary_key, monitored_field]
                threshold_field = config_dict.get('threshold_field')
                if threshold_type == 'dynamic' and threshold_field:
                    query_fields.append(threshold_field)
                
                query = f"SELECT {', '.join(query_fields)} FROM {table_name}"
                data = client.execute_query(query)
                self.stats['db_queries'] += 1
                
                config_id = config.id
                if config_id not in self.threshold_states:
                    self.cache_manager.set_threshold_state(config_id, {})
                
                triggered_records = []
                
                for row in data:
                    record_key = self.cache_manager.get_record_key(row, primary_key)
                    value = row.get(monitored_field)
                    
                    if value is None:
                        continue
                    
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        continue
                    
                    threshold_val = None
                    if threshold_type == 'static':
                        threshold_value = config_dict.get('threshold_value')
                        if threshold_value is not None:
                            try:
                                threshold_val = float(threshold_value)
                            except (ValueError, TypeError):
                                logger.warning(f"阈值配置值无法转换为数字: {threshold_value}")
                                continue
                    elif threshold_type == 'dynamic' and threshold_field:
                        threshold_value = row.get(threshold_field)
                        if threshold_value is not None:
                            try:
                                threshold_val = float(threshold_value)
                            except (ValueError, TypeError):
                                continue
                    
                    if threshold_val is None:
                        continue
                    
                    is_triggered = False
                    if operator == 'gt' and value > threshold_val:
                        is_triggered = True
                    elif operator == 'lt' and value < threshold_val:
                        is_triggered = True
                    elif operator == 'eq' and value == threshold_val:
                        is_triggered = True
                    elif operator == 'neq' and value != threshold_val:
                        is_triggered = True
                    elif operator == 'gte' and value >= threshold_val:
                        is_triggered = True
                    elif operator == 'lte' and value <= threshold_val:
                        is_triggered = True
                    
                    threshold_state = self.cache_manager.get_threshold_state(config_id) or {}
                    was_triggered = threshold_state.get(record_key, False)
                    
                    if is_triggered and not was_triggered:
                        triggered_records.append({
                            "record_key": record_key,
                            "monitored_field": monitored_field,
                            "current_value": value,
                            "threshold_value": threshold_val,
                            "threshold_type": threshold_type
                        })
                    
                    # 获取当前阈值状态
                    threshold_state = self.cache_manager.get_threshold_state(config_id) or {}
                    threshold_state[record_key] = is_triggered
                    # 更新缓存并设置过期时间
                    self.cache_manager.set_threshold_state(config_id, threshold_state)
                
                if triggered_records:
                    # 对于静态阈值，使用配置中的阈值；对于动态阈值，不传递全局阈值（因为每条记录的阈值可能不同）
                    event_data = {
                        "config_id": config.id,
                        "config_name": config.name,
                        "monitored_field": monitored_field,
                        "threshold_type": threshold_type,
                        "triggered_records": triggered_records,
                        "triggered_count": len(triggered_records)
                    }
                    if threshold_type == 'static':
                        event_data["threshold_value"] = config_dict.get('threshold_value')
                    
                    self.trigger_event(
                        config.name,
                        config.model_id,
                        event_data
                    )
                
            finally:
                client.close()
                
        except Exception as e:
            logger.error(f"监控阈值出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def trigger_event(self, event_type: str, model_id: int, data: Dict[str, Any], parent_log_id: int = None):
        """触发事件（增强版）"""
        import uuid
        trace_id = str(uuid.uuid4())
        event = {
            "type": event_type,
            "model_id": model_id,
            "data": data,
            "timestamp": time.time(),
            "trace_id": trace_id,
            "parent_log_id": parent_log_id
        }
        
        # 记录数据感知日志，并获取日志ID
        log_id = self._log_sensing_event(event_type, model_id, data, trace_id)
        event["log_id"] = log_id
        
        self.stats['events_triggered'] += 1
        
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"事件回调出错: {str(e)}")
        
        return log_id  # 返回日志ID供后续使用
    
    def _log_sensing_event(self, event_type: str, model_id: int, data: Dict[str, Any], trace_id: str):
        """记录数据感知事件日志"""
        log_id = log_event_with_parent(
            'info', 'data_sensing', 
            f"触发事件: {event_type}, 模型: {model_id}", 
            {
                "event_type": event_type,
                "model_id": model_id,
                "data": data
            }, 
            trace_id, 
            None  # 数据感知是根节点，parent_id为None
        )
        return log_id


# 全局引擎实例
data_sensing_engine = DataSensingEngine()
