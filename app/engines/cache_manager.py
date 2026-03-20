"""缓存管理器 - 管理数据感知引擎的缓存操作"""
import json
import hashlib
from typing import Dict, Any, List, Optional
from diskcache import Cache


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        # 使用 DiskCache 管理数据变化状态
        # 存储在 .cache 目录中，使用不同的子缓存
        self.data_states = Cache('.cache/data_states')  # 数据变化状态
        
        # 使用 DiskCache 管理阈值触发状态
        self.threshold_states = Cache('.cache/threshold_states')  # 阈值触发状态
        
        # 缓存过期时间设置
        self.DATA_STATE_TTL = 86400  # 数据变化状态：24小时
        self.THRESHOLD_STATE_TTL = 86400  # 阈值触发状态：24小时
    
    def get_record_key(self, record: Dict, primary_key: str = "id") -> str:
        """获取记录的唯一标识"""
        return str(record.get(primary_key, json.dumps(record, sort_keys=True)))

    def get_data_state(self, key: str) -> Optional[Dict[str, Any]]:
        """获取数据状态"""
        try:
            return self.data_states[key]
        except KeyError:
            return None
    
    def set_data_state(self, key: str, value: Dict[str, Any]):
        """设置数据状态"""
        self.data_states.set(key, value, expire=self.DATA_STATE_TTL)
    
    def get_threshold_state(self, key: str) -> Optional[bool]:
        """获取阈值触发状态"""
        try:
            return self.threshold_states[key]
        except KeyError:
            return None
    
    def set_threshold_state(self, key: str, value: bool):
        """设置阈值触发状态"""
        self.threshold_states.set(key, value, expire=self.THRESHOLD_STATE_TTL)
    
    def clear_all_caches(self):
        """清除所有缓存"""
        self.data_states.clear()
        self.threshold_states.clear()