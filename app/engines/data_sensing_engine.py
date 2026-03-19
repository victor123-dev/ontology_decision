import threading
import time
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from diskcache import Cache
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from concurrent.futures import ThreadPoolExecutor
from app.models.data_sensing import DataSensingConfig
from app.models.business_model import BusinessModel
from app.models.data_source import DataSource
from app.models.drive_log import DriveLog
from app.utils.db_client import DBClient
from app.utils.logger import get_logger
from app.config import settings

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
        
        # 使用 DiskCache 管理数据变化状态
        # 存储在 .cache 目录中，使用不同的子缓存
        self.data_states = Cache('.cache/data_states')  # 数据变化状态
        
        # 使用 DiskCache 管理阈值触发状态
        self.threshold_states = Cache('.cache/threshold_states')  # 阈值触发状态
        
        # 使用 DiskCache 缓存查询结果，减少数据库压力
        self.query_cache = Cache('.cache/query_cache')  # 查询结果缓存
        
        # 缓存过期时间设置（与原来的TTL保持一致）
        self.DATA_STATE_TTL = 3600  # 数据变化状态：1小时
        self.THRESHOLD_STATE_TTL = 86400  # 阈值触发状态：24小时
        self.QUERY_CACHE_TTL = 30  # 查询结果缓存：30秒
        
        # 配置任务映射 - 记录config_id对应的job_id
        self.config_jobs: Dict[int, str] = {}
        
        # 统计信息
        self.stats = {
            'events_triggered': 0,
            'tasks_executed': 0,
            'tasks_failed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
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
        
        # 启动统计信息打印线程（每5分钟打印一次）
        stats_thread = threading.Thread(target=self._print_stats_periodically)
        stats_thread.daemon = True
        stats_thread.start()
        
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
    
    def _log(self, level: str, category: str, message: str, data: Dict[str, Any] = None, trace_id: str = None):
        """记录驱动日志"""
        try:
            from sqlalchemy.orm import sessionmaker
            from app.utils.db_client import create_engine
            from app.config import settings
            import uuid
            
            engine = create_engine(settings.DATABASE_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            try:
                log = DriveLog(
                    level=level,
                    category=category,
                    message=message,
                    data=data,
                    trace_id=trace_id or str(uuid.uuid4())
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"记录驱动日志失败: {str(e)}")
    
    def register_event_callback(self, callback):
        """注册事件回调函数"""
        self.event_callbacks.append(callback)
    
    def _print_stats_periodically(self):
        """定期打印统计信息"""
        while self.is_running:
            time.sleep(300)  # 每5分钟
            if self.is_running:
                self._print_stats()
    
    def _print_stats(self):
        """打印统计信息"""
        total_cache_ops = self.stats['cache_hits'] + self.stats['cache_misses']
        cache_hit_rate = (self.stats['cache_hits'] / total_cache_ops * 100) if total_cache_ops > 0 else 0
        
        logger.info("=" * 60)
        logger.info("数据感知引擎统计信息")
        logger.info("=" * 60)
        logger.info(f"事件触发次数: {self.stats['events_triggered']}")
        logger.info(f"任务执行次数: {self.stats['tasks_executed']}")
        logger.info(f"任务失败次数: {self.stats['tasks_failed']}")
        logger.info(f"数据库查询次数: {self.stats['db_queries']}")
        logger.info(f"缓存命中率: {cache_hit_rate:.1f}% ({self.stats['cache_hits']}/{total_cache_ops})")
        logger.info(f"调度任务数: {len(self.config_jobs)}")
        logger.info(f"数据状态缓存: {len(self.data_states)} 条目")
        logger.info(f"阈值状态缓存: {len(self.threshold_states)} 条目")
        logger.info(f"查询缓存: {len(self.query_cache)} 条目")
        logger.info("=" * 60)
    
    def _get_db_session(self):
        """获取数据库会话"""
        from sqlalchemy.orm import sessionmaker
        from app.utils.db_client import create_engine, Base
        
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    def _compute_data_hash(self, data: List[Dict]) -> str:
        """计算数据的哈希值，用于比较数据变化"""
        if not data:
            return ""
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _get_record_key(self, record: Dict, primary_key: str = "id") -> str:
        """获取记录的唯一标识"""
        return str(record.get(primary_key, json.dumps(record, sort_keys=True)))
    
    def _get_cached_query(self, cache_key: str) -> Optional[List[Dict]]:
        """获取缓存的查询结果"""
        try:
            result = self.query_cache[cache_key]
            self.stats['cache_hits'] += 1
            return result
        except KeyError:
            self.stats['cache_misses'] += 1
            return None
    
    def _set_cached_query(self, cache_key: str, data: List[Dict]):
        """设置查询缓存"""
        self.query_cache.set(cache_key, data, expire=self.QUERY_CACHE_TTL)
    
    def _load_all_configs(self):
        """加载所有配置并创建调度任务"""
        try:
            db = self._get_db_session()
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
            
            db = self._get_db_session()
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
        if config_id in self.data_states:
            del self.data_states[config_id]
        if config_id in self.threshold_states:
            del self.threshold_states[config_id]
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
                
                # 检查查询缓存
                cached_data = self._get_cached_query(query_cache_key)
                if cached_data is not None:
                    current_data = cached_data
                else:
                    # 执行查询 - 总是查询所有字段，确保记录完整
                    fields_str = '*'
                    query = f"SELECT {fields_str} FROM {table_name}"
                    current_data = client.execute_query(query)
                    self.stats['db_queries'] += 1
                    
                    # 缓存查询结果
                    self._set_cached_query(query_cache_key, current_data)
                
                current_records = {self._get_record_key(row, primary_key): row for row in current_data}
                
                config_id = config.id
                last_state = self.data_states.get(config_id, {})
                last_records = last_state.get('records', {})
                
                # 检测新增
                if 'create' in trigger_conditions:
                    created_records = []
                    for key, record in current_records.items():
                        if key not in last_records:
                            created_records.append(record)
                    
                    if created_records:
                        self.trigger_event(
                            "data_change",
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
                            deleted_records.append(record)
                    
                    if deleted_records:
                        self.trigger_event(
                            "data_change",
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
                        self.trigger_event(
                            "data_change",
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
                
                # 更新状态缓存
                state_data = {
                    'records': current_records,
                    'record_count': len(current_data),
                    'data_hash': self._compute_data_hash(current_data)
                }
                self.data_states.set(config_id, state_data, expire=self.DATA_STATE_TTL)
                
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
                
                query_cache_key = f"{model.id}:{','.join(query_fields)}"
                
                cached_data = self._get_cached_query(query_cache_key)
                if cached_data is not None:
                    data = cached_data
                else:
                    query = f"SELECT {', '.join(query_fields)} FROM {table_name}"
                    data = client.execute_query(query)
                    self.stats['db_queries'] += 1
                    self._set_cached_query(query_cache_key, data)
                
                config_id = config.id
                if config_id not in self.threshold_states:
                    self.threshold_states.set(config_id, {}, expire=self.THRESHOLD_STATE_TTL)
                
                triggered_records = []
                
                for row in data:
                    record_key = self._get_record_key(row, primary_key)
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
                    
                    threshold_state = self.threshold_states.get(config_id, {})
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
                    threshold_state = self.threshold_states.get(config_id, {})
                    threshold_state[record_key] = is_triggered
                    # 更新缓存并设置过期时间
                    self.threshold_states.set(config_id, threshold_state, expire=self.THRESHOLD_STATE_TTL)
                
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
                        "threshold",
                        config.model_id,
                        event_data
                    )
                
            finally:
                client.close()
                
        except Exception as e:
            logger.error(f"监控阈值出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def trigger_event(self, event_type: str, model_id: int, data: Dict[str, Any]):
        """触发事件"""
        import uuid
        trace_id = str(uuid.uuid4())
        event = {
            "type": event_type,
            "model_id": model_id,
            "data": data,
            "timestamp": time.time(),
            "trace_id": trace_id
        }
        
        self.stats['events_triggered'] += 1
        
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"事件回调出错: {str(e)}")
        
        logger.info(f"触发事件: {event_type}, 模型: {model_id}, 数据: {json.dumps(data, ensure_ascii=False, default=str)[:200]}")
        self._log('info', 'data_sensing', f"触发事件: {event_type}, 模型: {model_id}", event, trace_id)


# 全局引擎实例
data_sensing_engine = DataSensingEngine()
