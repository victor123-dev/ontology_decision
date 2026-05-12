"""
DAG Service - 逻辑编排执行器
支持节点执行、条件分支、上下文管理
"""
from typing import Dict, Any, Optional, List
from collections import defaultdict, deque
import re
import copy
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DictAccessor:
    """字典访问器，支持 .属性 方式访问字典"""
    
    def __init__(self, data: dict):
        self._data = data
    
    def __getattr__(self, name: str):
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name)
    
    def __setattr__(self, name: str, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value
    
    def __delattr__(self, name: str):
        if name in self._data:
            del self._data[name]


class DAGExecutionContext:
    """DAG执行上下文，管理变量和状态"""
    
    def __init__(self, request_data: Dict[str, Any] = None):
        self.variables: Dict[str, Any] = {
            "req": request_data or {},
            "context": {},
            "res": {}
        }
        self.node_results: Dict[str, Dict[str, Any]] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.node_logs: List[Dict[str, Any]] = []
    
    def get(self, path: str) -> Any:
        """获取变量值，支持链式访问"""
        if not path:
            return None
        
        parts = path.split('.')
        if not parts:
            return None
        
        root = parts[0]
        if root not in self.variables:
            return None
        
        value = self.variables[root]
        for part in parts[1:]:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                idx = int(part)
                value = value[idx] if idx < len(value) else None
            else:
                return None
            if value is None:
                return None
        return value
    
    def set(self, path: str, value: Any):
        """设置变量值"""
        if not path:
            return
        
        parts = path.split('.')
        if len(parts) == 1:
            self.variables[path] = value
            return
        
        root = parts[0]
        if root not in self.variables:
            self.variables[root] = {}
        
        current = self.variables[root]
        for part in parts[1:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    def set_context(self, key: str, value: Any):
        """设置上下文变量"""
        self.variables["context"][key] = value
    
    def get_context(self, key: str) -> Any:
        """获取上下文变量"""
        return self.variables["context"].get(key)
    
    def set_node_result(self, node_id: str, result: Dict[str, Any]):
        """存储节点执行结果"""
        self.node_results[node_id] = result
        self.variables["res"] = result

    def add_node_log(self, node_id: str, node_label: str, node_type: str, 
                     status: str, input_params: Any = None, output: Any = None, 
                     context_snapshot: Dict = None, error: str = "",
                     selected_branch: str = None):
        """添加节点执行日志"""
        self.node_logs.append({
            "node_id": node_id,
            "node_label": node_label,
            "node_type": node_type,
            "status": status,
            "input_params": input_params,
            "output": output,
            "context_snapshot": copy.deepcopy(context_snapshot) if context_snapshot else None,
            "error": error,
            "selected_branch": selected_branch,
        })
    
    def add_history(self, node_id: str, status: str, message: str = ""):
        """添加执行历史"""
        self.execution_history.append({
            "node_id": node_id,
            "status": status,
            "message": message
        })


class DAGService:
    """逻辑编排执行服务"""
    
    def __init__(self):
        self._node_registry: Dict[str, callable] = {}
        self._register_builtin_nodes()
    
    def _register_builtin_nodes(self):
        """注册内置节点类型"""
        self._node_registry["action"] = self._execute_action_node
        self._node_registry["condition"] = self._execute_condition_node
    
    def register_node_type(self, node_type: str, handler: callable):
        """注册自定义节点类型处理器"""
        self._node_registry[node_type] = handler
    
    def execute(self, dag_definition: Dict[str, Any], request_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行DAG编排
        
        Args:
            dag_definition: DAG定义，包含nodes和edges
            request_data: 请求参数
            
        Returns:
            执行结果
        """
        nodes = dag_definition.get("nodes", [])
        edges = dag_definition.get("edges", [])
        
        if not nodes:
            return {"success": False, "error": "No nodes in DAG definition", "node_logs": [], "context": {}}
        
        # 构建节点映射
        node_map = {node["id"]: node for node in nodes}
        
        # 构建邻接表和入度表
        adjacency = defaultdict(list)
        in_degree = defaultdict(int)
        
        for node in nodes:
            node_id = node["id"]
            if in_degree[node_id] == 0:
                in_degree[node_id] = 0
        
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            adjacency[source].append(target)
            in_degree[target] += 1
        
        # 拓扑排序获取执行顺序
        execution_order = self._topological_sort(node_map, adjacency, in_degree)
        
        if execution_order is None:
            return {"success": False, "error": "Circular dependency detected in DAG", "node_logs": [], "context": {}}
        
        # 创建执行上下文
        context = DAGExecutionContext(request_data)
        
        # 构建节点出边映射（source -> list of edges）
        outgoing_edges = defaultdict(list)
        for edge in edges:
            outgoing_edges[edge["source"]].append(edge)
        
        # 记录所有节点ID，用于后续标记未执行的节点
        all_node_ids = set(node_map.keys())
        executed_nodes = set()
        skipped_nodes = set()
        
        for node_id in execution_order:
            node = node_map[node_id]
            node_type = node.get("type", "action")
            node_data = node.get("data", {})
            node_label = node_data.get("label", node_id)
            
            # 检查条件节点是否应该跳过此分支
            # 如果节点的入边来自条件节点的未选中分支，则跳过
            should_skip = self._should_skip_node(node_id, node_map, edges, context, outgoing_edges)
            if should_skip:
                skipped_nodes.add(node_id)
                context.add_node_log(
                    node_id=node_id, node_label=node_label, node_type=node_type,
                    status="skipped"
                )
                continue
            
            try:
                logger.info(f"Executing node: {node_id} (type: {node_type})")
                
                # 记录执行前的参数
                if node_type == "action":
                    param_values = node_data.get("paramValues", {})
                    input_params = self._resolve_parameters(param_values, context)
                else:
                    input_params = None
                
                # 执行节点
                result = self._execute_node(node, context, adjacency, outgoing_edges)
                
                # 处理上下文处理器（将结果存入context）
                context_handler = node_data.get("contextHandler", "")
                if context_handler:
                    self._execute_context_handler(context_handler, result, context)

                # 存储节点结果
                context.set_node_result(node_id, result)
                context.add_history(node_id, "success")
                executed_nodes.add(node_id)
                
                # 记录节点执行日志（context_snapshot为上下文处理器处理后的值）
                selected_branch = result.get("selected_branch") if node_type == "condition" else None
                context.add_node_log(
                    node_id=node_id, node_label=node_label, node_type=node_type,
                    status="success", input_params=input_params, output=result,
                    context_snapshot=copy.deepcopy(context.variables.get("context", {})),
                    selected_branch=selected_branch,
                )
                
            except Exception as e:
                logger.error(f"Node execution failed: {node_id}, error: {e}")
                context.add_history(node_id, "failed", str(e))
                executed_nodes.add(node_id)
                
                # 记录失败日志
                if node_type == "action":
                    param_values = node_data.get("paramValues", {})
                    input_params = self._resolve_parameters(param_values, context)
                else:
                    input_params = None
                context.add_node_log(
                    node_id=node_id, node_label=node_label, node_type=node_type,
                    status="failed", input_params=input_params, output=None,
                    context_snapshot=context.variables.get("context", {}),
                    error=str(e),
                )
                
                # 标记剩余未执行节点
                for remaining_id in execution_order:
                    if remaining_id not in executed_nodes and remaining_id not in skipped_nodes:
                        remaining_node = node_map[remaining_id]
                        context.add_node_log(
                            node_id=remaining_id,
                            node_label=remaining_node.get("data", {}).get("label", remaining_id),
                            node_type=remaining_node.get("type", "action"),
                            status="not_reached",
                        )
                
                return {
                    "success": False,
                    "error": f"Node {node_id} execution failed: {str(e)}",
                    "executed_nodes": list(executed_nodes),
                    "history": context.execution_history,
                    "node_logs": context.node_logs,
                    "context": context.variables.get("context", {}),
                }
        
        # 标记跳过的节点
        for nid in all_node_ids - executed_nodes - skipped_nodes:
            n = node_map[nid]
            context.add_node_log(
                node_id=nid,
                node_label=n.get("data", {}).get("label", nid),
                node_type=n.get("type", "action"),
                status="skipped",
            )
        
        return {
            "success": True,
            "result": context.variables.get("context", {}),
            "history": context.execution_history,
            "all_nodes": list(executed_nodes),
            "node_logs": context.node_logs,
            "context": context.variables.get("context", {}),
        }
    
    def _should_skip_node(self, node_id: str, node_map: Dict, edges: List[Dict],
                          context: DAGExecutionContext, outgoing_edges: Dict) -> bool:
        """判断节点是否应该跳过（条件分支未选中的下游节点）"""
        # 查找入边
        incoming_edges = [e for e in edges if e["target"] == node_id]
        
        for edge in incoming_edges:
            source_id = edge["source"]
            source_handle = edge.get("sourceHandle", "")
            
            # 如果入边来自条件节点的分支
            if source_handle.startswith("branch"):
                source_node = node_map.get(source_id)
                if source_node and source_node.get("type") == "condition":
                    # 检查条件节点的执行结果
                    source_result = context.node_results.get(source_id)
                    if source_result:
                        selected_branch = source_result.get("selected_branch")
                        # 如果当前节点不在选中分支上，则跳过
                        if selected_branch and node_id != selected_branch:
                            return True
        
        return False
    
    def _topological_sort(self, node_map: Dict, adjacency: Dict, in_degree: Dict) -> Optional[List[str]]:
        """拓扑排序，返回执行顺序"""
        queue = deque()
        result = []
        
        # 找到入度为0的节点
        for node_id in node_map:
            if in_degree[node_id] == 0:
                queue.append(node_id)
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(node_map):
            return None  # 存在环
        
        return result
    
    def _execute_node(self, node: Dict[str, Any], context: DAGExecutionContext,
                      adjacency: Dict, outgoing_edges: Dict) -> Dict[str, Any]:
        """执行单个节点"""
        node_type = node.get("type", "action")
        handler = self._node_registry.get(node_type)
        
        if handler is None:
            raise ValueError(f"Unknown node type: {node_type}")
        
        return handler(node, context, outgoing_edges)
    
    def _execute_action_node(self, node: Dict[str, Any], context: DAGExecutionContext,
                             outgoing_edges: Dict) -> Dict[str, Any]:
        """执行动作节点"""
        from app.services.action_service import get_action_service
        from app.utils.shared_utils import get_db
        
        data = node.get("data", {})
        action_id = data.get("actionId")
        
        if not action_id:
            raise ValueError(f"Action ID not found for node: {node['id']}")
        
        # 解析参数值
        param_values = data.get("paramValues", {})
        resolved_params = self._resolve_parameters(param_values, context)
        
        logger.info(f"Executing action: {action_id} with params: {resolved_params}")
        
        # 获取数据库会话
        db = next(get_db())
        
        try:
            # 执行动作
            action_service = get_action_service()
            result = action_service.execute_action(action_id, resolved_params, db)
            return result
        except Exception as e:
            logger.error(f"Action execution failed: {action_id}, error: {e}")
            raise
        finally:
            db.close()
    
    def _execute_condition_node(self, node: Dict[str, Any], context: DAGExecutionContext,
                                 outgoing_edges: Dict) -> Dict[str, Any]:
        """执行条件节点"""
        node_id = node["id"]
        edges = outgoing_edges.get(node_id, [])
        
        # 找到条件分支边
        branch_edges = [e for e in edges if e.get("sourceHandle", "").startswith("branch")]
        
        # 按分支顺序排序（branch0, branch1, branch2...）
        branch_edges = sorted(branch_edges, key=lambda e: e.get("sourceHandle", ""))
        
        # 评估每个分支条件，使用表达式解析（与变量/上下文一致）
        selected_branch = None
        for edge in branch_edges:
            condition = edge.get("condition", "")
            condition = condition.strip() if condition else ""
            
            # 修正常见拼写错误
            condition = condition.replace("contex.", "context.")
            
            # 使用表达式解析器评估条件
            result = self._resolve_expression(condition, context)
            logger.info(f"Condition expression: {condition}, resolved result: {result}")

            # 如果表达式结果为 truthy，选择该分支
            if result and result not in ("False", "false", "0", 0, "null", "None"):
                selected_branch = edge
                break
        
        return {
            "selected_branch": selected_branch["target"] if selected_branch else None,
            "branch_handle": selected_branch.get("sourceHandle") if selected_branch else None
        }
    
    def _resolve_parameters(self, param_values: Dict[str, Any], context: DAGExecutionContext) -> Dict[str, Any]:
        """解析参数值，支持变量引用"""
        resolved = {}
        
        for key, value in param_values.items():
            if isinstance(value, str):
                # 检查是否是变量引用
                if self._is_variable_reference(value):
                    resolved[key] = self._resolve_variable(value, context)
                else:
                    # 尝试解析为表达式
                    resolved[key] = self._resolve_expression(value, context)
            else:
                resolved[key] = value
        
        return resolved
    
    def _is_variable_reference(self, value: str) -> bool:
        """检查是否是变量引用"""
        if not isinstance(value, str):
            return False
        # 检查是否以 req. context. res. 开头
        patterns = ["req.", "context.", "res."]
        return any(value.startswith(p) for p in patterns)
    
    def _resolve_variable(self, value: str, context: DAGExecutionContext) -> Any:
        """解析变量引用"""
        return context.get(value)
    
    def _resolve_expression(self, expr: str, context: DAGExecutionContext) -> Any:
        """解析表达式"""
        expr = expr.strip()
        
        # 尝试提取变量引用
        var_pattern = r'(req|context|res)\.[a-zA-Z0-9_.\[\]]+'
        matches = re.findall(var_pattern, expr)
        
        if not matches:
            # 没有变量引用，直接返回原值
            return expr
        
        # 替换变量为实际值
        for match in re.finditer(var_pattern, expr):
            var_ref = match.group()
            var_value = context.get(var_ref)
            # 数字类型直接使用值，字符串使用repr（带引号）
            if isinstance(var_value, (int, float)) and var_value is not None:
                expr = expr.replace(var_ref, str(var_value))
            else:
                expr = expr.replace(var_ref, repr(var_value))
        
        try:
            # 处理数字字符串：尝试将引号包裹的数字转为真正的数字
            # 例如：'300' < 100 -> 300 < 100
            expr_processed = re.sub(r"'(-?\d+\.?\d*)'", r'\1', expr)
            
            # 安全执行表达式
            safe_globals = {
                "__builtins__": {
                    "len": len, "str": str, "int": int, "float": float,
                    "bool": bool, "max": max, "min": min, "abs": abs,
                    "list": list, "dict": dict, "range": range
                }
            }
            result = eval(expr_processed, safe_globals, {})
            return result
        except Exception as e:
            logger.warning(f"Expression evaluation failed: {expr}, error: {e}")
            return expr
    
    def _evaluate_condition(self, condition: str, context: DAGExecutionContext) -> bool:
        """评估条件表达式"""
        if not condition:
            return False
        
        condition = condition.strip()
        
        # 修正常见的拼写错误
        condition = condition.replace("contex.", "context.")
        
        try:
            # 提取变量引用
            var_pattern = r'(req|context|res)\.[a-zA-Z0-9_.\[\]]+'
            matches = re.findall(var_pattern, condition)
            
            if not matches:
                return False
            
            # 替换变量为实际值
            eval_expr = condition
            for match in re.finditer(var_pattern, condition):
                var_ref = match.group()
                var_value = context.get(var_ref)
                eval_expr = eval_expr.replace(var_ref, repr(var_value))
            
            # 安全执行
            safe_globals = {
                "__builtins__": {
                    "len": len, "str": str, "int": int, "float": float,
                    "bool": bool, "max": max, "min": min, "abs": abs,
                    "True": True, "False": False, "None": None
                }
            }
            result = eval(eval_expr, safe_globals, {})
            return bool(result)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition}, error: {e}")
            return False
    
    def _execute_context_handler(self, handler: str, result: Dict[str, Any], context: DAGExecutionContext):
        """执行上下文处理器 - 将handler作为脚本执行，context/res/req作为全局变量"""
        if not handler:
            return
        
        try:
            # 使用 DictAccessor 包装，支持 .属性 访问字典
            ctx_accessor = DictAccessor(context.variables["context"])
            res_accessor = DictAccessor(result)
            req_accessor = DictAccessor(context.variables.get("req", {}))
            
            # 安全执行环境
            safe_globals = {
                "__builtins__": {
                    "len": len, "str": str, "int": int, "float": float,
                    "bool": bool, "max": max, "min": min, "abs": abs,
                    "list": list, "dict": dict, "range": range, "type": type,
                    "True": True, "False": False, "None": None
                }
            }
            
            # 执行脚本
            exec(handler, safe_globals, {
                "context": ctx_accessor,
                "res": res_accessor,
                "req": req_accessor
            })
            
            logger.info(f"Context handler executed: {handler}, context: {context.variables['context']}, req: {context.variables.get("req", {})}")
        except Exception as e:
            logger.warning(f"Context handler execution failed: {handler}, error: {e}")
    
    def _extract_from_result(self, path: str, result: Dict[str, Any]) -> Any:
        """从结果中提取值"""
        if path.startswith("res['data']"):
            inner_path = path.replace("res['data']", "").strip("[]'")
            if inner_path:
                return result.get("data", {}).get(inner_path)
            return result.get("data")
        return result.get("data", {}).get(path.replace("res['data']['", "").replace("']", ""))


def get_dag_service() -> DAGService:
    """获取DAG服务实例"""
    return DAGService()
