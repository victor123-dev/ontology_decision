from typing import Union, Optional
from sqlalchemy.orm import Session
from app.models.data_sensing import DataSensingConfig
from app.models.drive_logic import DriveLogic
from app.utils.llm_translator import llm_translator
from app.utils.logger import get_logger
from app.utils.shared_utils import get_db_session

logger = get_logger(__name__)

def generate_natural_language_description_for_sensing_config(config_id: int):
    """为数据感知配置生成自然语言描述"""
    
    try:
        db = get_db_session()
        config = db.query(DataSensingConfig).filter(DataSensingConfig.id == config_id).first()
        
        if not config:
            logger.warning(f"数据感知配置 {config_id} 不存在")
            return
            
        # 转换为字典格式用于LLM处理
        config_dict = {
            "id": config.id,
            "name": config.name,
            "type": config.type,
            "model_id": config.model_id,
            "config": config.config,
            "description": config.description
        }
        
        # 生成自然语言描述
        natural_language_desc = llm_translator.convert_sensing_config_to_natural_language(config_dict)
        
        # 更新数据库
        config.natural_language_description = natural_language_desc
        db.commit()
        
        logger.info(f"成功为数据感知配置 {config_id} ({config.name}) 生成自然语言描述")
        
    except Exception as e:
        logger.error(f"为数据感知配置 {config_id} 生成自然语言描述失败: {e}")
        # 不抛出异常，避免影响主流程
    finally:
        db.close()

def generate_natural_language_description_for_drive_logic(logic_id: int):
    """为驱动逻辑配置生成自然语言描述"""
    
    try:
        db = get_db_session()
        logic = db.query(DriveLogic).filter(DriveLogic.id == logic_id).first()
        
        if not logic:
            logger.warning(f"驱动逻辑配置 {logic_id} 不存在")
            return
            
        # 获取关联的事件和任务信息用于更好的描述生成
        event_ids = [event.id for event in logic.events]
        task_ids = [task.id for task in logic.tasks]
        
        # 转换为字典格式用于LLM处理
        logic_dict = {
            "id": logic.id,
            "name": logic.name,
            "type": logic.type,
            "config": logic.config,
            "description": logic.description,
            "event_ids": event_ids,
            "task_ids": task_ids
        }
        
        # 生成自然语言描述
        natural_language_desc = llm_translator.convert_drive_logic_to_natural_language(logic_dict)
        
        # 更新数据库
        logic.natural_language_description = natural_language_desc
        db.commit()
        
        logger.info(f"成功为驱动逻辑配置 {logic_id} ({logic.name}) 生成自然语言描述")
        
    except Exception as e:
        logger.error(f"为驱动逻辑配置 {logic_id} 生成自然语言描述失败: {e}")
        # 不抛出异常，避免影响主流程
    finally:
        db.close()