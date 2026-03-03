import logging
import os
from logging.handlers import RotatingFileHandler
from app.config import settings

# 创建日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(thread)d - %(module)s - %(funcName)s - %(lineno)d - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 创建主日志记录器
logger = logging.getLogger('neo4j-graph-service')
logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

# 避免重复添加处理器
if not logger.handlers:
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # 创建文件处理器（带滚动功能）
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # 添加处理器到记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# 创建请求/响应日志记录器
request_logger = logging.getLogger('request-response-logger')
request_logger.setLevel(logging.DEBUG)
# 禁止向父日志记录器传播
request_logger.propagate = False

# 避免重复添加处理器
if not request_logger.handlers:
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # 创建请求/响应日志文件处理器
    request_file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'request_response.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    request_file_handler.setLevel(logging.DEBUG)
    request_file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # 添加处理器到记录器
    request_logger.addHandler(console_handler)
    request_logger.addHandler(request_file_handler)

# 创建LLM日志记录器
llm_logger = logging.getLogger('llm-logger')
llm_logger.setLevel(logging.DEBUG)
# 禁止向父日志记录器传播
llm_logger.propagate = False

# 避免重复添加处理器
if not llm_logger.handlers:

    # 创建LLM日志文件处理器
    llm_file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'llm.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    llm_file_handler.setLevel(logging.DEBUG)
    llm_file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # 添加处理器到记录器
    llm_logger.addHandler(llm_file_handler)


# 为不同模块创建子日志记录器
def get_logger(name: str) -> logging.Logger:
    return logger.getChild(name)

# 获取请求/响应日志记录器
def get_request_logger() -> logging.Logger:
    return request_logger

# 获取LLM日志记录器
def get_llm_logger() -> logging.Logger:
    return llm_logger