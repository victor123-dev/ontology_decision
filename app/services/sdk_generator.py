from typing import Dict, Any, List
import os
import shutil
import tempfile
import jinja2
from sqlalchemy.orm import Session
from app.models.business_model import BusinessModel, BusinessModelField
from app.models.business_model_link import BusinessModelLink
from app.dao.action_dao import get_action_dao, ActionDAO
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SDKGenerator:
    def __init__(self):
        self.action_dao: ActionDAO = get_action_dao()
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
            autoescape=False,
            enable_async=False
        )
    
    def get_info(self, db: Session) -> Dict[str, Any]:
        """
        获取SDK生成的基本信息
        """
        # 收集业务模型
        business_models = db.query(BusinessModel).all()
        models_info = []
        
        for model in business_models:
            model_info = {
                "id": model.id,
                "api_name": model.api_name,
                "name": model.name,
                "description": model.description,
                "primary_key_id": model.primary_key_id,  # 添加主键字段名
                "fields": [
                    {
                        "field_id": field.field_id,
                        "name": field.name,
                        "data_type": field.data_type,
                        "description": field.description,
                        "required": field.required,
                        "is_enum": getattr(field, 'is_enum', False),  # 新增：包含is_enum字段
                        "enum_values": getattr(field, 'enum_values', None)  # 新增：包含enum_values字段
                    }
                    for field in model.fields
                ]
            }
            models_info.append(model_info)
        
        # 收集关系
        links = db.query(BusinessModelLink).all()
        links_info = []
        
        for link in links:
            link_info = {
                "id": link.id,
                "name": link.name,
                "description": link.description,
                "source_model": link.source_model,
                "source_api_name": link.source_api_name,
                "source_key": link.source_key,
                "target_model": link.target_model,
                "target_api_name": link.target_api_name,
                "target_key": link.target_key,
                "cardinality": link.cardinality
            }
            links_info.append(link_info)
        
        # 收集行动
        actions = self.action_dao.get_actions()
        
        return {
            "models": models_info,
            "links": links_info,
            "actions": actions
        }
    
    def generate(self, db: Session, output_path: str, package_name: str, version: str, trigger_reload: bool = True) -> Dict[str, Any]:
        """
        生成SDK代码
        
        Args:
            db: 数据库会话
            output_path: SDK输出路径
            package_name: 包名
            version: 版本号
            trigger_reload: 是否在生成完成后触发reload（通过移动文件到app目录）
        """
        # 如果需要在app目录生成MCP文件，先使用临时目录
        mcp_temp_dir = None
        mcp_target_dir = None
        
        if trigger_reload:
            # 创建临时目录用于生成MCP文件
            mcp_temp_dir = tempfile.mkdtemp(prefix="sdk_mcp_")
            mcp_target_dir = os.path.join(os.path.dirname(__file__), "..", "api", "dynamic_mcp")
            mcp_target_dir = os.path.abspath(mcp_target_dir)
        
        # 清理输出目录
        if os.path.exists(output_path):
            shutil.rmtree(output_path)
        os.makedirs(output_path, exist_ok=True)
        
        # 创建包目录（在output_path下创建package_name子目录）
        package_dir = os.path.join(output_path, package_name)
        os.makedirs(package_dir, exist_ok=True)
        
        # 收集数据
        business_models = db.query(BusinessModel).all()
        links = db.query(BusinessModelLink).all()
        actions = self.action_dao.get_actions()
        
        # 生成核心文件
        self._generate_core_files(package_dir, package_name, business_models)
        
        # 生成业务模型文件
        model_files = self._generate_model_files(package_dir, business_models, links)
        
        # 生成查询模块
        self._generate_query_files(package_dir, business_models)
        
        # 生成行动模块
        self._generate_action_files(package_dir, actions)
        
        # 生成MCP服务文件（到临时目录或目标目录）
        mcp_output_dir = mcp_temp_dir if trigger_reload else mcp_target_dir
        self._generate_mcp_files(db, actions, mcp_output_dir)
        
        # 生成配置文件
        self._generate_config_file(package_dir, version)
        
        # 生成setup.py（在output_path根目录，不在package_dir内）
        self._generate_setup_file(output_path, package_name, version)
        
        # 构建SDK包
        build_result = self.build(output_path)
        
        # 如果使用了临时目录，在返回前移动到目标位置（触发reload）
        reload_triggered = False
        if trigger_reload and mcp_temp_dir and mcp_target_dir:
            try:
                # 确保目标目录存在
                os.makedirs(mcp_target_dir, exist_ok=True)
                
                # 移动所有文件到目标目录
                for item in os.listdir(mcp_temp_dir):
                    source = os.path.join(mcp_temp_dir, item)
                    dest = os.path.join(mcp_target_dir, item)
                    if os.path.isfile(source):
                        shutil.move(source, dest)
                
                reload_triggered = True
                logger.info(f"MCP文件已移动到 {mcp_target_dir}，将触发reload")
            except Exception as e:
                logger.error(f"移动MCP文件失败: {e}")
            finally:
                # 清理临时目录
                if os.path.exists(mcp_temp_dir):
                    shutil.rmtree(mcp_temp_dir, ignore_errors=True)
        
        return {
            "output_path": output_path,
            "package_name": package_name,
            "version": version,
            "models_generated": len(model_files),
            "actions_generated": len(actions),
            "build": build_result,
            "reload_triggered": reload_triggered
        }
    
    def _generate_core_files(self, output_path: str, package_name: str, business_models):
        """
        生成核心文件
        """
        # 创建核心目录
        core_dir = os.path.join(output_path, "core")
        os.makedirs(core_dir, exist_ok=True)
        
        # 生成__init__.py
        with open(os.path.join(core_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("from .client import OntologyClient\nfrom .business_model import BusinessModel\n")
        
        # 生成client.py
        client_template = self.template_env.get_template("client.py.j2")
        client_content = client_template.render(
            package_name=package_name,
            models=[{"id": model.id, "name": model.api_name} for model in business_models]
        )
        with open(os.path.join(core_dir, "client.py"), "w", encoding="utf-8") as f:
            f.write(client_content)
        
        # 生成business_model.py
        model_template = self.template_env.get_template("business_model.py.j2")
        model_content = model_template.render()
        with open(os.path.join(core_dir, "business_model.py"), "w", encoding="utf-8") as f:
            f.write(model_content)
        
        # 生成session.py
        session_template = self.template_env.get_template("session.py.j2")
        session_content = session_template.render()
        with open(os.path.join(core_dir, "session.py"), "w", encoding="utf-8") as f:
            f.write(session_content)
        
        # 生成types.py
        types_template = self.template_env.get_template("types.py.j2")
        types_content = types_template.render()
        with open(os.path.join(core_dir, "types.py"), "w", encoding="utf-8") as f:
            f.write(types_content)
        
        # 生成根__init__.py
        root_init = f"from .core import OntologyClient, BusinessModel\nfrom . import models\nfrom . import query\nfrom . import actions\n\n__version__ = '1.0.0'\n"
        with open(os.path.join(output_path, "__init__.py"), "w", encoding="utf-8") as f:
            f.write(root_init)
    
    def _generate_model_files(self, output_path: str, business_models: List[BusinessModel], links: List[BusinessModelLink]):
        """
        生成业务模型文件
        """
        models_dir = os.path.join(output_path, "models")
        os.makedirs(models_dir, exist_ok=True)
        
        # 生成models/__init__.py
        models_init = ""
        model_files = []
        
        for model in business_models:
            # 生成模型文件
            model_name = model.api_name
            model_filename = model.id.lower() + ".py"
            model_files.append(model_filename)
            
            # 收集关系
            model_links = []
            for link in links:
                if link.source_model == model.id:
                    # 获取目标模型的API名称
                    target_model_obj = next((m for m in business_models if m.id == link.target_model), None)
                    target_model_api_name = target_model_obj.api_name
                    
                    intermediate_model_name = None
                    if link.cardinality == 'many-to-many' and hasattr(link, 'intermediate_model') and link.intermediate_model:
                        intermediate_model_obj = next((m for m in business_models if m.id == link.intermediate_model), None)
                        intermediate_model_name = intermediate_model_obj.api_name
                    
                    model_links.append({
                        "type": "outgoing",
                        "link": link,
                        "target_model": link.target_model,
                        "target_model_name": target_model_api_name,
                        "source_api_name": link.source_api_name,
                        "cardinality": link.cardinality,
                        "intermediate_model_name": intermediate_model_name
                    })
                elif link.target_model == model.id:
                    # 获取源模型的API名称  
                    source_model_obj = next((m for m in business_models if m.id == link.source_model), None)
                    source_model_api_name = source_model_obj.api_name
                    
                    intermediate_model_name = None
                    if link.cardinality == 'many-to-many' and hasattr(link, 'intermediate_model') and link.intermediate_model:
                        intermediate_model_obj = next((m for m in business_models if m.id == link.intermediate_model), None)
                        intermediate_model_name = intermediate_model_obj.api_name
                    
                    model_links.append({
                        "type": "incoming",
                        "link": link,
                        "source_model": link.source_model,
                        "source_model_name": source_model_api_name,
                        "target_api_name": link.target_api_name,
                        "cardinality": link.cardinality,
                        "intermediate_model_name": intermediate_model_name
                    })
            
            # 准备字段数据
            prepared_fields = self._prepare_fields(model.fields)

            # 生成模型文件
            model_template = self.template_env.get_template("model.py.j2")
            model_content = model_template.render(
                model=model,
                model_name=model_name,
                fields=prepared_fields,
                links=model_links
            )
            
            with open(os.path.join(models_dir, model_filename), "w", encoding="utf-8") as f:
                f.write(model_content)
            
            # 更新models/__init__.py
            models_init += f"from .{model.id.lower()} import {model_name}\n"
        
        # 写入models/__init__.py
        with open(os.path.join(models_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write(models_init)
        
        return model_files
    
    def _generate_query_files(self, output_path: str, business_models):
        """
        生成查询模块
        """
        query_dir = os.path.join(output_path, "query")
        os.makedirs(query_dir, exist_ok=True)
        
        # 生成__init__.py
        with open(os.path.join(query_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("from .builder import QueryBuilder\nfrom .executor import QueryExecutor\n")
        
        # 生成builder.py
        builder_template = self.template_env.get_template("query_builder.py.j2")
        builder_content = builder_template.render()
        with open(os.path.join(query_dir, "builder.py"), "w", encoding="utf-8") as f:
            f.write(builder_content)
        
        # 生成executor.py
        executor_template = self.template_env.get_template("query_executor.py.j2")
        executor_content = executor_template.render(
            models=[{"id": model.id, "name": model.api_name} for model in business_models]
        )
        with open(os.path.join(query_dir, "executor.py"), "w", encoding="utf-8") as f:
            f.write(executor_content)
    
    def _generate_action_files(self, output_path: str, actions: List[Dict[str, Any]]):
        """
        生成行动模块
        """
        actions_dir = os.path.join(output_path, "actions")
        os.makedirs(actions_dir, exist_ok=True)
        
        # 创建parameters子目录
        params_dir = os.path.join(actions_dir, "parameters")
        os.makedirs(params_dir, exist_ok=True)
        
        # 生成每个action的参数类和action类
        for action in actions:
            action_name = action.get('api_name')
            # 准备action参数
            if "parameters" in action and action["parameters"]:
                prepared_params = self._prepare_action_parameters(action["parameters"])
                action_with_params = {**action, "parameters": prepared_params}
            else:
                action_with_params = action
            
            # 生成参数类（如果有参数）
            if "parameters" in action_with_params and action_with_params["parameters"]:
                param_template = self.template_env.get_template("action_parameters.py.j2")
                param_content = param_template.render(action_name=action_name, action=action_with_params)
                param_filename = f"{action['id']}_parameters.py"
                with open(os.path.join(params_dir, param_filename), "w", encoding="utf-8") as f:
                    f.write(param_content)
            
            # 生成action类
            action_template = self.template_env.get_template("action_class.py.j2")
            action_content = action_template.render(action_name=action_name, action=action_with_params)
            action_filename = f"{action['id']}.py"
            with open(os.path.join(actions_dir, action_filename), "w", encoding="utf-8") as f:
                f.write(action_content)
        
        # 生成actions/__init__.py
        actions_init = "from .registry import ActionRegistry\n"
        for action in actions:
            action_class_name = action['api_name']
            actions_init += f"from .{action['id']} import {action_class_name}Action\n"
        with open(os.path.join(actions_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write(actions_init)
        
        # 生成parameters/__init__.py
        if os.path.exists(params_dir):
            params_init = ""
            for action in actions:
                if "parameters" in action and action["parameters"]:
                    param_class_name = action['api_name'] + "Parameters"
                    params_init += f"from .{action['id']}_parameters import {param_class_name}\n"
            with open(os.path.join(params_dir, "__init__.py"), "w", encoding="utf-8") as f:
                f.write(params_init)
        
        # 生成registry.py
        registry_template = self.template_env.get_template("action_registry.py.j2")
        registry_content = registry_template.render(actions=actions)
        with open(os.path.join(actions_dir, "registry.py"), "w", encoding="utf-8") as f:
            f.write(registry_content)
    
    def _generate_config_file(self, output_path: str, version: str):
        """
        生成配置文件
        """
        config_template = self.template_env.get_template("config.py.j2")
        config_content = config_template.render(version=version)
        with open(os.path.join(output_path, "config.py"), "w", encoding="utf-8") as f:
            f.write(config_content)
    
    def _generate_setup_file(self, output_path: str, package_name: str, version: str):
        """
        生成setup.py文件
        """
        setup_template = self.template_env.get_template("setup.py.j2")
        setup_content = setup_template.render(
            package_name=package_name,
            version=version
        )
        with open(os.path.join(output_path, "setup.py"), "w", encoding="utf-8") as f:
            f.write(setup_content)
    
    def build(self, sdk_path: str) -> Dict[str, Any]:
        """
        构建SDK包
        """
        import subprocess
        import os
        import shutil
        
        # 转换为绝对路径
        if not os.path.isabs(sdk_path):
            sdk_path = os.path.abspath(sdk_path)
        
        original_cwd = os.getcwd()
        try:
            # 进入SDK根目录（setup.py所在目录）
            os.chdir(sdk_path)
            
            # 执行构建命令
            result = subprocess.run(
                ["python", "setup.py", "sdist", "bdist_wheel"],
                capture_output=True,
                text=True
            )
            
            # 检查构建结果
            if result.returncode == 0:
                # 查找生成的包文件
                sdk_dist_dir = os.path.join(sdk_path, "dist")
                packages = []
                if os.path.exists(sdk_dist_dir):
                    packages = [f for f in os.listdir(sdk_dist_dir) if f.endswith((".tar.gz", ".whl"))]
                
                # 创建根目录的dist目录
                root_dist_dir = os.path.join(original_cwd, "dist")
                os.makedirs(root_dist_dir, exist_ok=True)
                
                # 复制包文件到根目录dist
                for package in packages:
                    source_path = os.path.join(sdk_dist_dir, package)
                    dest_path = os.path.join(root_dist_dir, package)
                    shutil.copy2(source_path, dest_path)
                
                return {
                    "success": True,
                    "message": "SDK built successfully",
                    "packages": packages,
                    "dist_path": sdk_dist_dir,
                    "root_dist_path": root_dist_dir
                }
            else:
                return {
                    "success": False,
                    "message": "SDK build failed",
                    "error": result.stderr
                }
        finally:
            os.chdir(original_cwd)
    
    def _camel_case(self, s: str) -> str:
        """
        将下划线分隔的字符串转换为驼峰命名
        """
        parts = s.split('_')
        return ''.join([part.capitalize() for part in parts])

    def _get_python_type(self, data_type: str) -> str:
        """
        将数据库类型映射为Python类型
        """
        type_mapping = {
            'string': 'str',
            'text': 'str',
            'integer': 'int',
            'float': 'float',
            'boolean': 'bool',
            'date': 'str',
            'datetime': 'str',
            'object': 'Dict[str, Any]',
            'array': 'List[Any]'
        }
        return type_mapping.get(data_type.lower(), 'Any')
    
    def _get_action_parameter_python_type(self, param: Dict[str, Any]) -> str:
        """
        获取action参数的Python类型
        """
        return self._get_python_type(param.get('type', 'string'))
    
    def _prepare_action_parameters(self, parameters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        准备action参数数据，添加Python类型
        """
        prepared_params = []
        for param in parameters:
            prepared_param = {
                'name': param.get('name', ''),
                'type': param.get('type', 'string'),
                'python_type': self._get_action_parameter_python_type(param),
                'required': param.get('required', False),
                'description': param.get('description', ''),
                'default_value': param.get('default_value', None),
                'is_enum': param.get('is_enum', False),
                'enum_values': param.get('enum_values', None)
            }
            prepared_params.append(prepared_param)
        return prepared_params

    def _prepare_fields(self, fields):
        """
        准备字段数据，添加Python类型
        """
        prepared_fields = []
        for field in fields:
            prepared_field = {
                'field_id': field.field_id,
                'name': field.name,
                'data_type': field.data_type,
                'python_type': self._get_python_type(field.data_type),
                'description': field.description or field.field_id,
                'required': getattr(field, 'required', False),
                'default': getattr(field, 'default', None),
                'is_enum': getattr(field, 'is_enum', False),
                'enum_values': getattr(field, 'enum_values', None)  # JSON类型已自动反序列化为列表
            }
            prepared_fields.append(prepared_field)
        return prepared_fields

    def _generate_mcp_files(self, db: Session, actions: List[Dict[str, Any]], mcp_dir: str = None):
        """
        生成MCP服务文件到指定目录
        使用静态代码生成方式，为每个action和object生成独立的函数
        
        Args:
            db: 数据库会话
            actions: 行动列表
            mcp_dir: MCP文件输出目录（如果为None，则使用默认的dynamic_mcp目录）
        """
        import os
        
        # API目录路径
        api_dir = os.path.join(os.path.dirname(__file__), "..", "api")
        api_dir = os.path.abspath(api_dir)
        
        # 确定MCP目录
        if mcp_dir is None:
            mcp_dir = os.path.join(api_dir, "dynamic_mcp")
        
        # 确保目录存在
        os.makedirs(mcp_dir, exist_ok=True)
        
        # 生成Action MCP文件
        self._generate_action_mcp_files(mcp_dir, actions)
        
        # 生成Object MCP文件
        # TODO 这里先不生成了吧，先使用通用的，生成以后工具太多直接上下文溢出了
        # self._generate_object_mcp_files(mcp_dir, db)
        
        # 生成Link Query MCP文件
        # TODO 这里先不生成了吧，先使用通用的，生成以后工具太多直接上下文溢出了
        # self._generate_link_query_mcp_files(mcp_dir, db)

    def _generate_action_mcp_files(self, mcp_dir: str, actions: List[Dict[str, Any]]):
        """生成Action MCP文件"""
        # 准备action参数数据（用于模板渲染）
        prepared_actions = []
        for action in actions:
            # 准备action参数
            if "parameters" in action and action["parameters"]:
                prepared_params = self._prepare_action_parameters(action["parameters"])
                action_with_params = {**action, "parameters": prepared_params}
            else:
                action_with_params = action
            prepared_actions.append(action_with_params)
        
        # 生成action_execute_mcp.py文件
        action_mcp_template = self.template_env.get_template("action_execute_mcp.py.j2")
        action_mcp_content = action_mcp_template.render(actions=prepared_actions)
        action_mcp_path = os.path.join(mcp_dir, "action_execute_mcp.py")
        with open(action_mcp_path, "w", encoding="utf-8") as f:
            f.write(action_mcp_content)

    def _generate_object_mcp_files(self, mcp_dir: str, db: Session):
        """生成Object MCP文件"""
        # 收集业务模型
        business_models = db.query(BusinessModel).all()
        models_info = []
        
        for model in business_models:
            model_info = {
                "id": model.id,
                "api_name": model.api_name,
                "name": model.name,
                "description": model.description,
                "primary_key_id": model.primary_key_id,  # 添加主键字段名
                "fields": [
                    {
                        "field_id": field.field_id,
                        "name": field.name,
                        "data_type": field.data_type,
                        "description": field.description,
                        "required": field.required,
                        "is_enum": getattr(field, 'is_enum', False),  # 新增：包含is_enum字段
                        "enum_values": getattr(field, 'enum_values', None)  # 新增：包含enum_values字段
                    }
                    for field in model.fields
                ]
            }
            models_info.append(model_info)
        
        # 生成object_get_by_id_mcp.py文件
        object_mcp_template = self.template_env.get_template("object_get_by_id_mcp.py.j2")
        object_mcp_content = object_mcp_template.render(models=models_info)
        object_mcp_path = os.path.join(mcp_dir, "object_get_by_id_mcp.py")
        with open(object_mcp_path, "w", encoding="utf-8") as f:
            f.write(object_mcp_content)

    def _generate_link_query_mcp_files(self, mcp_dir: str, db: Session):
        """生成Link Query MCP文件（支持双向查询）"""
        # 收集业务模型和关系
        business_models = db.query(BusinessModel).all()
        model_map = {model.id: model for model in business_models}
        
        links = db.query(BusinessModelLink).all()
        query_directions = []
        
        for link in links:
            source_model = model_map.get(link.source_model)
            target_model = model_map.get(link.target_model)
            
            if source_model and target_model:
                # 准备源模型信息
                source_model_info = {
                    "id": source_model.id,
                    "api_name": source_model.api_name,
                    "name": source_model.name,
                    "description": source_model.description,
                    "primary_key_id": source_model.primary_key_id,
                    "fields": [
                        {
                            "field_id": field.field_id,
                            "name": field.name,
                            "data_type": field.data_type,
                            "description": field.description,
                            "required": field.required,
                            "is_enum": getattr(field, 'is_enum', False),  # 新增：包含is_enum字段
                            "enum_values": getattr(field, 'enum_values', None)  # 新增：包含enum_values字段
                        }
                        for field in source_model.fields
                    ]
                }
                
                # 准备目标模型信息
                target_model_info = {
                    "id": target_model.id,
                    "api_name": target_model.api_name,
                    "name": target_model.name,
                    "description": target_model.description,
                    "primary_key_id": target_model.primary_key_id,
                    "fields": [
                        {
                            "field_id": field.field_id,
                            "name": field.name,
                            "data_type": field.data_type,
                            "description": field.description,
                            "required": field.required,
                            "is_enum": getattr(field, 'is_enum', False),  # 新增：包含is_enum字段
                            "enum_values": getattr(field, 'enum_values', None)  # 新增：包含enum_values字段
                        }
                        for field in target_model.fields
                    ]
                }
                
                # 正向查询：source -> target
                forward_query = {
                    "direction": "forward",
                    "link_id": link.id,
                    "link_name": link.name,
                    "link_description": link.description,
                    "source_model": source_model_info,
                    "target_model": target_model_info,
                    "cardinality": link.cardinality,
                    "intermediate_model": link.intermediate_model,
                    "intermediate_source_key": link.intermediate_source_key,
                    "intermediate_target_key": link.intermediate_target_key,
                    "source_key": link.source_key,
                    "target_key": link.target_key,
                    "query_name": f"{source_model.id}_get_{target_model.id}_by_{link.id}",
                    "param_field_name": source_model.primary_key_id or (source_model.fields[0].field_id if source_model.fields else "id"),
                    "param_description": f"源{source_model.name}对象的主键ID列表"
                }
                
                # 反向查询：target -> source
                reverse_query = {
                    "direction": "reverse", 
                    "link_id": link.id,
                    "link_name": link.name,
                    "link_description": link.description,
                    "source_model": target_model_info,
                    "target_model": source_model_info,
                    "cardinality": link.cardinality,
                    "intermediate_model": link.intermediate_model,
                    "intermediate_source_key": link.intermediate_target_key,  # 注意：反向时交换
                    "intermediate_target_key": link.intermediate_source_key,  # 注意：反向时交换
                    "source_key": link.target_key,  # 注意：反向时交换
                    "target_key": link.source_key,  # 注意：反向时交换
                    "query_name": f"{target_model.id}_get_{source_model.id}_by_{link.id}",
                    "param_field_name": target_model.primary_key_id or (target_model.fields[0].field_id if target_model.fields else "id"),
                    "param_description": f"源{target_model.name}对象的主键ID列表"
                }
                
                query_directions.append(forward_query)
                query_directions.append(reverse_query)
        
        # 生成object_link_query_mcp.py文件
        if query_directions:
            link_mcp_template = self.template_env.get_template("object_link_query_mcp.py.j2")
            link_mcp_content = link_mcp_template.render(query_directions=query_directions)
            link_mcp_path = os.path.join(mcp_dir, "object_link_query_mcp.py")
            with open(link_mcp_path, "w", encoding="utf-8") as f:
                f.write(link_mcp_content)


def get_sdk_generator() -> SDKGenerator:
    return SDKGenerator()
