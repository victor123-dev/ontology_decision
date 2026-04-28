"""
仿真模拟日志配置
独立于app的日志系统，专门用于记录仿真模拟过程
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# 创建日志目录（放在scripts/logs下）
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(thread)d - %(module)s - %(funcName)s - %(lineno)d - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 创建仿真模拟日志记录器
simulation_logger = logging.getLogger('simulation')
simulation_logger.setLevel(logging.DEBUG)
# 禁止向父日志记录器传播
simulation_logger.propagate = False

# 避免重复添加处理器
if not simulation_logger.handlers:
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # 创建文件处理器（带滚动功能）
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'simulation.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # 添加处理器到记录器
    simulation_logger.addHandler(console_handler)
    simulation_logger.addHandler(file_handler)


def get_simulation_logger() -> logging.Logger:
    """获取仿真模拟日志记录器"""
    return simulation_logger
