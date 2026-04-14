from typing import Dict, Any, List
import os
import shutil
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
                        "description": field.description
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
    
    def generate(self, db: Session, output_path: str, package_name: str, version: str) -> Dict[str, Any]:
        """
        生成SDK代码
        """
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
        
        # 生成配置文件
        self._generate_config_file(package_dir, version)
        
        # 生成setup.py（在output_path根目录，不在package_dir内）
        self._generate_setup_file(output_path, package_name, version)
        
        # 构建SDK包
        build_result = self.build(output_path)
        
        return {
            "output_path": output_path,
            "package_name": package_name,
            "version": version,
            "models_generated": len(model_files),
            "actions_generated": len(actions),
            "build": build_result
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
        registry_content = registry_template.render(action_name=action_name, actions=actions)
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
            'decimal': 'float',
            'boolean': 'bool',
            'date': 'str',
            'datetime': 'str',
            'time': 'str',
            'json': 'Dict[str, Any]',
            'object': 'Dict[str, Any]',
            'array': 'List[Any]',
            'uuid': 'str',
            'binary': 'bytes'
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
                'default_value': param.get('default_value', None)
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
                'default': getattr(field, 'default', None)
            }
            prepared_fields.append(prepared_field)
        return prepared_fields


def get_sdk_generator() -> SDKGenerator:
    return SDKGenerator()
