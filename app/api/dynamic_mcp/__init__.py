import os
import importlib
from pathlib import Path

# 获取当前目录路径
current_dir = Path(__file__).parent

# 自动发现并导入所有 .py 文件（除了 __init__.py）
__all__ = []
for file_path in current_dir.glob("*.py"):
    if file_path.name != "__init__.py":
        module_name = file_path.stem
        # 动态导入模块
        module = importlib.import_module(f".{module_name}", package=__name__)
        # 将模块添加到命名空间
        globals()[module_name] = module
        __all__.append(module_name)