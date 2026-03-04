import threading
import time
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from cachetools import TTLCache
from app.models.data_sensing import DataSensingConfig
from app.models.business_model import BusinessModel
from app.models.data_source import DataSource
from app.utils.db_client import DBClient
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class DataSensingEngine:
    """数据感知引擎 - 使用缓存管理状态"""
    
    def __init__(self):
        self.is_running = False
        self.threads = []
        self.event_callbacks = []
        
        # 使用 TTLCache 管理数据变化状态
        # 最大100个配置，状态有效期1小时（3600秒）
        self.data_states = TTLCache(maxsize=100, ttl=3600)
        
        # 使用 TTLCache 管理阈值触发状态
        # 最大100个配置，状态有效期24小时（86400秒）- 阈值状态需要更长时间保持
        self.threshold_states = TTLCache(maxsize=100, ttl=86400)
        
        # 使用 TTLCache 缓存查询结果，减少数据库压力
        # 最大50个表，缓存有效期30秒
        self.query_cache = TTLCache(maxsize=50, ttl=30)
        
        # 统计信息
        self.stats = {
            'events_triggered': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'db_queries': 0
        }
    
    def start(self):
        """启动数据感知引擎"""
        self.is_running = True
        
        # 启动监控线程
        monitor_thread = threading.Thread(target=self._monitor_configs)
        monitor_thread.daemon = True
        monitor_thread.start()
        self.threads.append(monitor_thread)
        
        # 启动统计信息打印线程（每5分钟打印一次）
        stats_thread = threading.Thread(target=self._print_stats_periodically)
        stats_thread.daemon = True
        stats_thread.start()
        self.threads.append(stats_thread)
        
        logger.info("数据感知引擎启动")
        logger.info(f"缓存配置: 数据状态缓存(100条目, 1小时), 阈值状态缓存(100条目, 24小时), 查询缓存(50条目, 30秒)")
    
    def stop(self):
        """停止数据感知引擎"""
        self.is_running = False
        for thread in self.threads:
            thread.join()
        logger.info("数据感知引擎停止")
        self._print_stats()
    
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
        logger.info(f"数据库查询次数: {self.stats['db_queries']}")
        logger.info(f"缓存命中率: {cache_hit_rate:.1f}% ({self.stats['cache_hits']}/{total_cache_ops})")
        logger.info(f"数据状态缓存: {len(self.data_states)}/{self.data_states.maxsize} 条目")
        logger.info(f"阈值状态缓存: {len(self.threshold_states)}/{self.threshold_states.maxsize} 条目")
        logger.info(f"查询缓存: {len(self.query_cache)}/{self.query_cache.maxsize} 条目")
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
        if cache_key in self.query_cache:
            self.stats['cache_hits'] += 1
            return self.query_cache[cache_key]
        self.stats['cache_misses'] += 1
        return None
    
    def _set_cached_query(self, cache_key: str, data: List[Dict]):
        """设置查询缓存"""
        self.query_cache[cache_key] = data
    
    def _monitor_configs(self):
        """监控数据感知配置"""
        while self.is_running:
            try:
                db = self._get_db_session()
                try:
                    configs = db.query(DataSensingConfig).all()
                    
                    for config in configs:
                        check_interval = config.config.get('check_interval', 5)
                        config_id = config.id
                        
                        # 检查是否需要执行
                        last_check = 0
                        if config_id in self.data_states:
                            last_check = self.data_states[config_id].get('last_check_time', 0)
                        
                        current_time = time.time()
                        
                        if current_time - last_check >= check_interval:
                            if config.type == 'data_change':
                                self._monitor_data_change(config, db)
                            elif config.type == 'threshold':
                                self._monitor_threshold(config, db)
                            
                            # 更新最后检查时间
                            if config_id not in self.data_states:
                                self.data_states[config_id] = {}
                            self.data_states[config_id]['last_check_time'] = current_time
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"监控配置出错: {str(e)}")
            
            time.sleep(1)
    
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
                    # 执行查询
                    if monitored_fields:
                        fields_str = ', '.join([primary_key] + monitored_fields)
                    else:
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
                if config_id not in self.data_states:
                    self.data_states[config_id] = {}
                self.data_states[config_id]['records'] = current_records
                self.data_states[config_id]['record_count'] = len(current_data)
                self.data_states[config_id]['data_hash'] = self._compute_data_hash(current_data)
                
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
                    self.threshold_states[config_id] = {}
                
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
                            threshold_val = float(threshold_value)
                    elif threshold_type == 'dynamic' and threshold_field:
                        threshold_value = row.get(threshold_field)
                        if threshold_value is not None:
                            threshold_val = float(threshold_value)
                    
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
                    
                    was_triggered = self.threshold_states[config_id].get(record_key, False)
                    
                    if is_triggered and not was_triggered:
                        triggered_records.append({
                            "record_key": record_key,
                            "monitored_field": monitored_field,
                            "current_value": value,
                            "threshold_value": threshold_val,
                            "threshold_type": threshold_type
                        })
                    
                    self.threshold_states[config_id][record_key] = is_triggered
                
                if triggered_records:
                    self.trigger_event(
                        "threshold",
                        config.model_id,
                        {
                            "config_id": config.id,
                            "config_name": config.name,
                            "monitored_field": monitored_field,
                            "threshold_type": threshold_type,
                            "threshold_value": threshold_value,
                            "triggered_records": triggered_records,
                            "triggered_count": len(triggered_records)
                        }
                    )
                
            finally:
                client.close()
                
        except Exception as e:
            logger.error(f"监控阈值出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def trigger_event(self, event_type: str, model_id: str, data: Dict[str, Any]):
        """触发事件"""
        event = {
            "type": event_type,
            "model_id": model_id,
            "data": data,
            "timestamp": time.time()
        }
        
        self.stats['events_triggered'] += 1
        
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"事件回调出错: {str(e)}")
        
        logger.info(f"触发事件: {event_type}, 模型: {model_id}, 数据: {json.dumps(data, ensure_ascii=False, default=str)[:200]}")


# 全局引擎实例
data_sensing_engine = DataSensingEngine()
