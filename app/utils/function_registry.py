"""
Function Registry - 管理 First Order 驱动逻辑可调用的函数
"""

import ast
import importlib
from typing import Dict, Callable, Any, List, Set
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Python 内置函数和关键字黑名单
BUILT_IN_FUNCTIONS: Set[str] = {
    'abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes', 'chr', 'classmethod',
    'compile', 'complex', 'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval',
    'exec', 'filter', 'float', 'format', 'frozenset', 'getattr', 'globals', 'hasattr',
    'hash', 'help', 'hex', 'id', 'input', 'int', 'isinstance', 'issubclass', 'iter',
    'len', 'list', 'locals', 'map', 'max', 'memoryview', 'min', 'next', 'object',
    'oct', 'open', 'ord', 'pow', 'print', 'property', 'range', 'repr', 'reversed',
    'round', 'set', 'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum',
    'super', 'tuple', 'type', 'vars', 'zip', '__import__',
    'True', 'False', 'None', 'true', 'false', 'null',
    'and', 'or', 'not', 'in', 'is', 'if', 'else', 'for', 'while', 'return',
}


class FunctionRegistry:
    """函数注册表 - 单例模式"""

    _instance = None
    _functions: Dict[str, Callable] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._register_builtin_functions()
        return cls._instance

    def _register_builtin_functions(self):
        """注册内置工具函数"""
        self.register('utils.extract_field', self._extract_field)
        self.register('utils.compare', self._compare)
        self.register('utils.in_range', self._in_range)
        self.register('utils.contains', self._contains)
        self.register('utils.is_empty', self._is_empty)
        logger.info("函数注册表初始化完成，已注册内置函数")

    def register(self, name: str, func: Callable):
        """注册函数"""
        self._functions[name] = func
        logger.debug(f"注册函数: {name}")

    def get(self, name: str) -> Callable:
        """获取函数，支持动态导入"""
        if name in self._functions:
            return self._functions[name]
        return self._dynamic_import(name)

    def _dynamic_import(self, path: str) -> Callable:
        """动态导入函数"""
        try:
            # 检查是否包含模块路径
            if '.' in path:
                module_path, func_name = path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                func = getattr(module, func_name)
            else:
                # 尝试从 functions 包下的所有模块导入
                func_name = path
                
                # 扫描 functions 目录下的所有 Python 模块
                import os
                import glob
                
                functions_dir = os.path.dirname(os.path.abspath(__file__))
                functions_dir = os.path.join(functions_dir, '..', 'functions')
                functions_dir = os.path.normpath(functions_dir)
                
                # 找到所有 .py 文件（排除 __init__.py）
                module_files = glob.glob(os.path.join(functions_dir, '*.py'))
                module_names = []
                
                for file_path in module_files:
                    file_name = os.path.basename(file_path)
                    if file_name != '__init__.py':
                        module_name = file_name[:-3]  # 移除 .py 后缀
                        module_names.append(f'app.functions.{module_name}')
                
                # 按优先级排序：business_logic 优先，然后是其他模块
                if 'app.functions.business_logic' in module_names:
                    module_names.remove('app.functions.business_logic')
                    module_names.insert(0, 'app.functions.business_logic')
                
                # 尝试从每个模块导入
                func = None
                for module_path in module_names:
                    try:
                        module = importlib.import_module(module_path)
                        if hasattr(module, func_name):
                            func = getattr(module, func_name)
                            logger.info(f"从模块 {module_path} 加载函数: {func_name}")
                            break
                    except Exception as e:
                        logger.debug(f"从模块 {module_path} 加载函数 {func_name} 失败: {str(e)}")
                
                if func is None:
                    raise ImportError(f"在 functions 包中未找到函数 {func_name}")

            self._functions[path] = func
            logger.info(f"动态加载函数: {path}")
            return func
        except Exception as e:
            raise ImportError(f"无法加载函数 {path}: {str(e)}")

    def get_all(self) -> Dict[str, Callable]:
        """获取所有已注册函数"""
        return self._functions.copy()

    @staticmethod
    def _extract_field(data: dict, field: str, default=None):
        """从嵌套字典中提取字段值"""
        if not isinstance(data, dict):
            return default
        keys = field.split('.')
        result = data
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return default
        return result

    @staticmethod
    def _compare(value, operator: str, threshold):
        """比较操作"""
        ops = {
            'eq': lambda a, b: a == b,
            'ne': lambda a, b: a != b,
            'gt': lambda a, b: a > b,
            'gte': lambda a, b: a >= b,
            'lt': lambda a, b: a < b,
            'lte': lambda a, b: a <= b,
        }
        if operator not in ops:
            raise ValueError(f"未知的操作符: {operator}")
        return ops[operator](value, threshold)

    @staticmethod
    def _in_range(value, min_val, max_val):
        """判断值是否在范围内"""
        try:
            return min_val <= value <= max_val
        except TypeError:
            return False

    @staticmethod
    def _contains(container, item):
        """判断是否包含"""
        try:
            return item in container
        except TypeError:
            return False

    @staticmethod
    def _is_empty(value):
        """判断是否为空"""
        if value is None:
            return True
        if isinstance(value, (str, list, dict, set, tuple)):
            return len(value) == 0
        return False


def extract_function_names(expression: str) -> List[str]:
    """
    使用 AST 从表达式中提取函数名
    安全、准确地识别所有函数调用
    """
    if not expression or not isinstance(expression, str):
        return []

    try:
        tree = ast.parse(expression, mode='eval')
    except SyntaxError as e:
        logger.error(f"表达式语法错误: {str(e)}")
        return []

    function_names = set()

    class FunctionVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            func_name = self._get_func_name(node.func)
            if func_name and self._is_valid_function(func_name):
                function_names.add(func_name)
            self.generic_visit(node)

        def _get_func_name(self, node) -> str:
            """获取函数调用的完整名称"""
            if isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Attribute):
                parts = []
                current = node
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                    return '.'.join(reversed(parts))
            return None

        def _is_valid_function(self, name: str) -> bool:
            """检查是否为有效的自定义函数（排除内置函数和方法）"""
            # 排除内置函数和关键字
            if name in BUILT_IN_FUNCTIONS:
                return False

            # 排除单一下划线开头的（私有方法）
            if name.startswith('_'):
                return False

            # 排除明显是对象方法的调用（如 data.get, list.append）
            parts = name.split('.')
            if len(parts) == 1:
                # 单一名称，检查是否在黑名单
                return name not in BUILT_IN_FUNCTIONS

            # 多段名称，如 module.func 或 obj.method
            # 允许 module.submodule.func 形式
            return True

    visitor = FunctionVisitor()
    visitor.visit(tree)

    return list(function_names)


class FunctionNamespace:
    """函数命名空间 - 支持 utils.xxx 形式的调用"""

    def __init__(self, functions: Dict[str, Callable]):
        self._functions = functions

    def __getattr__(self, name: str) -> Callable:
        if name in self._functions:
            return self._functions[name]
        raise AttributeError(f"函数 '{name}' 不存在")


def prepare_function_environment(expression: str, data: dict, event: dict) -> Dict[str, Any]:
    """
    准备函数执行环境
    从表达式提取函数并加载到局部变量中
    """
    registry = FunctionRegistry()

    # 基础环境变量
    local_vars = {
        'data': data,
        'event': event,
        'true': True,
        'false': False,
        'null': None,
    }

    # 从表达式提取函数名
    function_names = extract_function_names(expression)
    logger.debug(f"从表达式提取的函数: {function_names}")

    # 按命名空间分组
    namespace_funcs = {}
    simple_funcs = {}

    for func_name in function_names:
        try:
            func = registry.get(func_name)

            if '.' in func_name:
                # 命名空间形式: utils.extract_field
                parts = func_name.split('.')
                namespace = parts[0]
                short_name = parts[-1]

                if namespace not in namespace_funcs:
                    namespace_funcs[namespace] = {}
                namespace_funcs[namespace][short_name] = func
            else:
                # 简单形式: process_sensor_data
                simple_funcs[func_name] = func

            logger.debug(f"加载函数 {func_name}")
        except ImportError as e:
            logger.warning(f"无法加载函数 {func_name}: {str(e)}")

    # 添加简单函数到局部变量
    local_vars.update(simple_funcs)

    # 创建命名空间对象
    for namespace, funcs in namespace_funcs.items():
        local_vars[namespace] = FunctionNamespace(funcs)

    return local_vars


# 全局注册表实例
function_registry = FunctionRegistry()
