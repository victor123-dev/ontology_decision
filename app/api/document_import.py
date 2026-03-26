from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import tempfile
import os
import time
from app.utils.db_client import Base, create_engine, sessionmaker
from app.config import settings
from app.utils.logger import get_logger
from app.utils.llm_translator import llm_translator
from app.models.business_model import BusinessModel
from app.models.data_sensing import DataSensingConfig
from app.models.drive_logic import DriveLogic, Task
from app.services.document_parser import DocumentParser
from app.engines.data_sensing_engine import data_sensing_engine

logger = get_logger(__name__)


def _standardize_sensing_config(config: dict) -> dict:
    """标准化数据感知配置格式"""
    standardized = config.copy()
    config_data = config.get('config', {})
    
    if config.get('type') == 'data_change':
        # 数据变化感知标准化
        trigger_conditions = []
        monitored_fields = []
        check_interval = 5
        
        # 处理触发条件
        if 'trigger_conditions' in config_data:
            trigger_conditions = config_data['trigger_conditions']
        elif 'change_condition' in config_data:
            # 转换旧格式
            condition = config_data['change_condition']
            if 'create' in condition or '新增' in condition:
                trigger_conditions.append('create')
            if 'update' in condition or '更新' in condition or '变更' in condition:
                trigger_conditions.append('update')
            if 'delete' in condition or '删除' in condition:
                trigger_conditions.append('delete')
            if not trigger_conditions:
                trigger_conditions = ['update']  # 默认更新
        
        # 处理监控字段
        if 'monitored_fields' in config_data:
            monitored_fields = config_data['monitored_fields']
        elif 'field' in config_data:
            monitored_fields = [config_data['field']]
        elif 'fields' in config_data:
            monitored_fields = config_data['fields']
        
        # 处理检查间隔
        if 'check_interval' in config_data:
            check_interval = config_data['check_interval']
        elif isinstance(config_data.get('check_interval'), (int, float)):
            check_interval = int(config_data['check_interval'])
        
        standardized['config'] = {
            'trigger_conditions': trigger_conditions,
            'monitored_fields': monitored_fields,
            'check_interval': check_interval
        }
        
    elif config.get('type') == 'threshold':
        # 阈值触发感知标准化
        monitored_field = None
        threshold_type = 'static'
        threshold_value = None
        threshold_field = None
        operator = 'gt'
        check_interval = 5
        
        # 处理监控字段
        if 'monitored_field' in config_data:
            monitored_field = config_data['monitored_field']
        elif 'field' in config_data:
            monitored_field = config_data['field']
        
        # 处理阈值类型和值
        if 'threshold_type' in config_data:
            threshold_type = config_data['threshold_type']
        if 'threshold_value' in config_data:
            threshold_value = config_data['threshold_value']
        elif 'threshold' in config_data:
            threshold_value = config_data['threshold']
            threshold_type = 'static'
        
        # 处理阈值字段（动态阈值）
        if 'threshold_field' in config_data:
            threshold_field = config_data['threshold_field']
            threshold_type = 'dynamic'
        
        # 处理操作符
        if 'operator' in config_data:
            op = config_data['operator']
            if op in ['>', '大于', 'greater than']:
                operator = 'gt'
            elif op in ['<', '小于', 'less than']:
                operator = 'lt'
            elif op in ['=', '等于', 'equal']:
                operator = 'eq'
            elif op in ['!=', '不等于', 'not equal']:
                operator = 'ne'
            elif op in ['>=', '大于等于']:
                operator = 'gte'
            elif op in ['<=', '小于等于']:
                operator = 'lte'
        
        # 处理检查间隔
        if 'check_interval' in config_data:
            check_interval = config_data['check_interval']
        elif isinstance(config_data.get('check_interval'), (int, float)):
            check_interval = int(config_data['check_interval'])
        
        standardized['config'] = {
            'monitored_field': monitored_field,
            'threshold_type': threshold_type,
            'operator': operator,
            'check_interval': check_interval
        }
        
        if threshold_type == 'static':
            standardized['config']['threshold_value'] = threshold_value
        else:
            standardized['config']['threshold_field'] = threshold_field
    
    return standardized


def _standardize_drive_logic_config(config: dict) -> dict:
    """标准化驱动逻辑配置格式"""
    standardized = config.copy()
    config_data = config.get('config', {})
    
    if config.get('type') == 'first_order':
        # 一阶函数标准化 - 主要使用场景
        pre_condition = ""
        
        # 优先使用正确的字段
        if 'pre_condition' in config_data:
            pre_condition = config_data['pre_condition']
        elif 'condition' in config_data:
            pre_condition = config_data['condition']
        elif 'rule' in config_data:
            pre_condition = config_data['rule']
        else:
            # 如果有业务字段，尝试生成合理的Python条件表达式
            conditions = []
            
            # 处理阈值条件
            if 'threshold' in config_data and 'field' in config_data:
                field = config_data['field']
                threshold = config_data['threshold']
                operator = config_data.get('operator', '>')
                
                # 转换操作符为Python格式
                if operator in ['>', '大于']:
                    py_op = '>'
                elif operator in ['<', '小于']:
                    py_op = '<'
                elif operator in ['>=', '大于等于']:
                    py_op = '>='
                elif operator in ['<=', '小于等于']:
                    py_op = '<='
                elif operator in ['=', '==', '等于']:
                    py_op = '=='
                elif operator in ['!=', '不等于']:
                    py_op = '!='
                else:
                    py_op = '>'
                
                # 生成data.get()格式的条件
                if isinstance(threshold, (int, float)):
                    conditions.append(f"data.get('{field}', 0) {py_op} {threshold}")
                else:
                    conditions.append(f"data.get('{field}', '') {py_op} '{threshold}'")
            
            # 处理状态条件
            if 'status' in config_data:
                status_val = config_data['status']
                conditions.append(f"data.get('status', '') == '{status_val}'")
            
            if conditions:
                pre_condition = " and ".join(conditions)
            else:
                # 默认条件
                pre_condition = "True"
        
        # 修复可能的JavaScript语法错误
        pre_condition = pre_condition.replace('&&', 'and')
        pre_condition = pre_condition.replace('||', 'or')
        pre_condition = pre_condition.replace('!', 'not ')
        pre_condition = pre_condition.replace('true', 'True')
        pre_condition = pre_condition.replace('false', 'False')
        pre_condition = pre_condition.replace('null', 'None')
        
        standardized['config'] = {
            'pre_condition': pre_condition
        }
    elif config.get('type') == 'script':
        # 脚本函数标准化 - 生成正确的脚本格式
        script_content = ""
        if 'script_content' in config_data:
            script_content = config_data['script_content']
        elif 'script' in config_data:
            script_content = config_data['script']
        elif 'code' in config_data:
            script_content = config_data['code']
        else:
            # 如果有业务字段，生成正确的脚本模板
            script_lines = []
            script_lines.append("# 自动生成的驱动逻辑脚本")
            script_lines.append("event_data = event.get('data', {})")
            script_lines.append("record_data = event_data.get('affected_records', [{}])[0].get('record', {})")
            script_lines.append("")
            
            # 处理阈值条件
            if 'threshold' in config_data and 'field' in config_data:
                field = config_data['field']
                threshold = config_data['threshold']
                operator = config_data.get('operator', '>')
                
                # 转换操作符为Python格式
                if operator in ['>', '大于']:
                    py_op = '>'
                elif operator in ['<', '小于']:
                    py_op = '<'
                elif operator in ['>=', '大于等于']:
                    py_op = '>='
                elif operator in ['<=', '小于等于']:
                    py_op = '<='
                elif operator in ['=', '==', '等于']:
                    py_op = '=='
                elif operator in ['!=', '不等于']:
                    py_op = '!='
                else:
                    py_op = '>'
                
                # 生成条件判断
                if isinstance(threshold, (int, float)):
                    condition = f"record_data.get('{field}', 0) {py_op} {threshold}"
                else:
                    condition = f"record_data.get('{field}', '') {py_op} '{threshold}'"
                
                script_lines.append(f"if {condition}:")
                
                # 处理动作（如果有）
                actions = config_data.get('actions', [])
                if actions:
                    script_lines.append(f"    # 执行动作: {', '.join(actions)}")
                
                script_lines.append(f"    result = (True, event_data)")
                script_lines.append("else:")
                script_lines.append(f"    result = (False, event_data)")
            else:
                # 默认脚本
                script_lines.append("# 默认处理逻辑")
                script_lines.append("result = (True, event_data)")
            
            script_content = "\n".join(script_lines)
        
        standardized['config'] = {
            'script_content': script_content
        }
    
    return standardized


router = APIRouter()

def get_db():
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/document-import/parse")
async def parse_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """解析文档内容，返回原始文本"""
    if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
        raise HTTPException(status_code=400, detail="不支持的文件格式，仅支持PDF、DOCX、TXT")
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # 解析文档
        parser = DocumentParser()
        document_content = parser.parse(temp_file_path)
        
        return {
            "success": True,
            "content": document_content,
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@router.post("/document-import/generate-configs")
def generate_configs_from_document(
    document_content: str = Form(...),
    db: Session = Depends(get_db)
):
    """基于文档内容生成配置预览"""
    
    try:
        # 获取所有业务模型
        business_models = []
        models = db.query(BusinessModel).all()
        for model in models:
            db.refresh(model)  # 确保加载字段
            business_models.append({
                "id": model.id,
                "name": model.name,
                "description": model.description,
                "fields": [{"field_id": f.field_id, "name": f.name} for f in model.fields] if model.fields else []
            })
        
        # 获取所有任务
        tasks = []
        task_list = db.query(Task).all()
        for task in task_list:
            db.refresh(task)  # 确保加载能力
            tasks.append({
                "id": task.id,
                "name": task.name,
                "capability_ids": [cap.id for cap in task.capabilities] if task.capabilities else [],
                "capability_names": [cap.name for cap in task.capabilities] if task.capabilities else []
            })
        
        # 提取数据感知配置
        sensing_configs = llm_translator.extract_sensing_configs_from_document(
            document_content, business_models
        )
        # 标准化配置格式
        sensing_configs = [_standardize_sensing_config(config) for config in sensing_configs]
        # 为每个配置添加临时ID，用于驱动逻辑引用
        for i, config in enumerate(sensing_configs):
            config['temp_id'] = f"temp_{i}"
        
        # 提取驱动逻辑配置（需要先有感知配置）
        drive_logics = llm_translator.extract_drive_logics_from_document(
            document_content, sensing_configs, tasks
        )
        # 标准化驱动逻辑配置格式
        drive_logics = [_standardize_drive_logic_config(config) for config in drive_logics]
        
        return {
            "success": True,
            "sensing_configs": sensing_configs,
            "drive_logics": drive_logics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置生成失败: {str(e)}")

@router.post("/document-import/apply-configs")
def apply_configs_from_document(
    sensing_configs: List[dict],
    drive_logics: List[dict],
    db: Session = Depends(get_db)
):
    """应用生成的配置到系统中"""
    try:
        # 创建数据感知配置
        created_sensing_configs = []
        temp_id_to_db_id = {}  # 临时ID到数据库ID的映射
        for config_data in sensing_configs:
            db_config = DataSensingConfig(
                name=config_data.get("name"),
                type=config_data.get("type"),
                model_id=config_data.get("model_id"),
                config=config_data.get("config", {}),
                description=config_data.get("description"),
                status=True
            )
            db.add(db_config)
            db.commit()
            db.refresh(db_config)
            created_sensing_configs.append(db_config)
            # 建立临时ID到数据库ID的映射
            if 'temp_id' in config_data:
                temp_id_to_db_id[config_data['temp_id']] = db_config.id
            
            # 通知引擎添加调度任务
            try:
                data_sensing_engine.add_config(db_config)
            except Exception as e:
                # 记录错误但不影响API返回
                logger.error(f"添加调度任务失败: {e}")
        
        # 创建驱动逻辑配置
        created_drive_logics = []
        for logic_data in drive_logics:
            db_logic = DriveLogic(
                name=logic_data.get("name"),
                type=logic_data.get("type"),
                config=logic_data.get("config", {}),
                description=logic_data.get("description")
            )
            db.add(db_logic)
            db.commit()
            db.refresh(db_logic)
            
            # 关联事件 - 使用临时ID映射到实际数据库ID
            event_temp_ids = logic_data.get("event_temp_ids", [])
            if event_temp_ids:
                # 将临时ID转换为数据库ID
                actual_event_ids = [temp_id_to_db_id[temp_id] for temp_id in event_temp_ids if temp_id in temp_id_to_db_id]
                if actual_event_ids:
                    events = db.query(DataSensingConfig).filter(DataSensingConfig.id.in_(actual_event_ids)).all()
                    db_logic.events = events
            
            # 关联任务
            task_ids = logic_data.get("task_ids", [])
            if task_ids:
                tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
                db_logic.tasks = tasks
            
            db.commit()
            db.refresh(db_logic)
            created_drive_logics.append(db_logic)
        
        return {
            "success": True,
            "message": f"成功创建 {len(created_sensing_configs)} 个数据感知配置和 {len(created_drive_logics)} 个驱动逻辑"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"配置应用失败: {str(e)}")