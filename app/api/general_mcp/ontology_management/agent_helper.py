"""
Agent 辅助工具 - Ontology Management MCP
提供智能推荐、工作流引导、自然语言摘要等 Agent 友好功能
"""
from typing import Dict, List, Optional, Any
from datetime import datetime


class AgentHelper:
    """Agent 辅助工具类"""
    
    @staticmethod
    def generate_recommended_workflow(
        objects: List[Dict],
        links: List[Dict],
        actions: List[Dict]
    ) -> List[Dict]:
        """
        根据当前本体状态推荐工作流程
        
        Args:
            objects: 对象类型列表
            links: 关系类型列表
            actions: 行动类型列表
            
        Returns:
            推荐工作流列表
        """
        workflow = []
        
        # 场景1: 初期建设 - 对象较少
        if len(objects) < 5:
            workflow.append({
                "step": 1,
                "priority": "high",
                "action": "完善核心对象类型",
                "reason": f"当前仅有 {len(objects)} 个对象类型，建议先定义核心业务实体",
                "suggested_tools": ["create_object_type"],
                "tips": "从业务核心实体开始，如订单、产品、客户等",
                "example": "创建 'production_order' (生产订单) 对象类型"
            })
        
        # 场景2: 关系不足
        connected_objects = set()
        for link in links:
            connected_objects.add(link.get("source_object_type_id"))
            connected_objects.add(link.get("target_object_type_id"))
        
        unconnected_count = len(objects) - len(connected_objects)
        if unconnected_count > len(objects) * 0.3 and len(objects) >= 3:
            workflow.append({
                "step": 2,
                "priority": "high",
                "action": "建立对象间关系",
                "reason": f"有 {unconnected_count} 个对象未建立关联，本体连通性不足",
                "suggested_tools": ["create_link_type"],
                "tips": "优先考虑业务逻辑上紧密相关的对象",
                "example": "创建 'order_has_product' 关系连接订单和产品"
            })
        
        # 场景3: Action 覆盖不足
        objects_with_actions = set()
        for action in actions:
            target_id = action.get("target_object_type_id")
            if target_id:
                objects_with_actions.add(target_id)
        
        objects_without_actions = len(objects) - len(objects_with_actions)
        if objects_without_actions > len(objects) * 0.5 and len(objects) >= 3:
            workflow.append({
                "step": 3,
                "priority": "medium",
                "action": "为对象添加操作能力",
                "reason": f"有 {objects_without_actions} 个对象缺乏 Action，无法进行数据操作",
                "suggested_tools": ["create_action_type"],
                "tips": "为核心对象添加 CRUD 操作，特别是创建和查询",
                "example": "为 'production_order' 创建 'create_production_order' Action"
            })
        
        # 场景4: 字段完善
        avg_fields = sum(obj.get("fields_count", 0) for obj in objects) / len(objects) if objects else 0
        if avg_fields < 3 and len(objects) > 0:
            workflow.append({
                "step": 4,
                "priority": "medium",
                "action": "完善对象字段定义",
                "reason": f"平均每个对象仅有 {avg_fields:.1f} 个字段，建议增加必要属性",
                "suggested_tools": ["update_object_type"],
                "tips": "添加业务必需字段，如状态、时间、数量等",
                "example": "为订单添加 'status', 'created_time', 'total_amount' 字段"
            })
        
        # 场景5: 本体已较完善，建议测试和优化
        if len(objects) >= 5 and len(links) >= len(objects) and len(actions) >= len(objects):
            workflow.append({
                "step": 1,
                "priority": "low",
                "action": "测试和优化本体",
                "reason": "本体结构已较完善，建议进行测试和语义优化",
                "suggested_tools": ["test_action_type", "validate_action_code", "search_ontology_for_management"],
                "tips": "运行测试验证 Action 逻辑，检查命名规范一致性",
                "example": "使用 test_action_type 测试创建订单的 Action"
            })
        
        # 如果没有特殊场景，提供通用建议
        if not workflow:
            workflow.append({
                "step": 1,
                "priority": "medium",
                "action": "继续完善本体",
                "reason": "根据业务需求持续优化本体结构",
                "suggested_tools": ["get_ontology_management_context"],
                "tips": "定期查看本体上下文，发现可优化点",
                "example": "使用 get_ontology_management_context 查看完整本体状态"
            })
        
        return workflow
    
    @staticmethod
    def generate_natural_language_summary(ontology_context: Dict) -> str:
        """
        生成本体的自然语言摘要
        
        Args:
            ontology_context: 本体上下文数据
            
        Returns:
            自然语言摘要字符串
        """
        summary = ontology_context.get("summary", {})
        completeness = ontology_context.get("completeness_score", 0)
        
        objects_count = summary.get("total_object_types", 0)
        links_count = summary.get("total_link_types", 0)
        actions_count = summary.get("total_action_types", 0)
        
        # 构建摘要
        parts = []
        parts.append(f"当前本体包含 {objects_count} 个对象类型、{links_count} 个关系类型和 {actions_count} 个行动类型。")
        
        # 完整性评价
        if completeness >= 80:
            parts.append(f"本体完整性评分为 {completeness:.1f} 分，结构较为完善。")
        elif completeness >= 60:
            parts.append(f"本体完整性评分为 {completeness:.1f} 分，建议继续完善。")
        else:
            parts.append(f"本体完整性评分为 {completeness:.1f} 分，需要大量补充。")
        
        # 孤立对象提示
        orphaned = summary.get("object_types_without_link_types", 0)
        if orphaned > 0 and objects_count > 0:
            parts.append(f"有 {orphaned} 个对象类型未建立任何关系，建议增加关联以提升连通性。")
        
        # Action 覆盖提示
        with_action = summary.get("object_types_with_action_types", 0)
        if objects_count > 0:
            coverage = with_action / objects_count * 100
            if coverage < 50:
                parts.append(f"仅 {coverage:.0f}% 的对象类型有对应的 Action，建议为核心对象添加操作能力。")
        
        # 连通性评价
        if objects_count > 0:
            connectivity = (objects_count - orphaned) / objects_count * 100
            if connectivity < 70:
                parts.append(f"本体连通性为 {connectivity:.0f}%，建议建立更多关系连接孤立对象。")
        
        return " ".join(parts)
    
    @staticmethod
    def predict_next_operations(
        recent_operation: str,
        operation_result: Dict
    ) -> List[Dict]:
        """
        预测用户可能的下一步操作
        
        Args:
            recent_operation: 最近执行的操作
            operation_result: 操作结果
            
        Returns:
            预测的下一步操作列表
        """
        predictions = []
        
        # 基于操作类型预测
        if recent_operation == "create_object_type":
            predictions.extend([
                {
                    "operation": "create_object_field",
                    "reason": "为新创建的对象类型添加更多字段",
                    "confidence": 0.8,
                    "parameters_hint": {"object_type_id": operation_result.get("object_type_id")}
                },
                {
                    "operation": "create_link_type",
                    "reason": "建立该对象与其他对象的关系",
                    "confidence": 0.7,
                    "parameters_hint": {"source_object_type_id": operation_result.get("object_type_id")}
                },
                {
                    "operation": "create_action_type",
                    "reason": "为该对象创建操作能力",
                    "confidence": 0.75,
                    "parameters_hint": {"target_object_type_id": operation_result.get("object_type_id")}
                }
            ])
        
        elif recent_operation == "create_link_type":
            predictions.extend([
                {
                    "operation": "get_link_type",
                    "reason": "验证刚创建的关系类型",
                    "confidence": 0.9,
                    "parameters_hint": {"link_type_id": operation_result.get("link_type_id")}
                },
                {
                    "operation": "create_link_type",
                    "reason": "继续创建其他关系",
                    "confidence": 0.6,
                    "parameters_hint": {}
                }
            ])
        
        elif recent_operation == "create_action_type":
            predictions.extend([
                {
                    "operation": "test_action_type",
                    "reason": "测试刚创建的 Action 是否正常工作",
                    "confidence": 0.85,
                    "parameters_hint": {"action_type_id": operation_result.get("action_type_id")}
                },
                {
                    "operation": "validate_action_code",
                    "reason": "验证 Action 代码的语法和安全性",
                    "confidence": 0.7,
                    "parameters_hint": {}
                }
            ])
        
        elif recent_operation == "update_object_type":
            predictions.extend([
                {
                    "operation": "get_object_type",
                    "reason": "查看更新后的对象类型详情",
                    "confidence": 0.8,
                    "parameters_hint": {"object_type_id": operation_result.get("object_type_id")}
                },
                {
                    "operation": "batch_update_fields",
                    "reason": "继续批量更新字段",
                    "confidence": 0.5,
                    "parameters_hint": {"object_type_id": operation_result.get("object_type_id")}
                }
            ])
        
        elif recent_operation == "get_ontology_management_context":
            predictions.extend([
                {
                    "operation": "search_ontology_for_management",
                    "reason": "搜索特定的本体元素",
                    "confidence": 0.6,
                    "parameters_hint": {}
                },
                {
                    "operation": "create_object_type",
                    "reason": "基于当前本体状态创建新对象",
                    "confidence": 0.5,
                    "parameters_hint": {}
                }
            ])
        
        return predictions
    
    @staticmethod
    def create_agent_friendly_response(
        data: Dict,
        operation: str,
        success: bool = True
    ) -> Dict:
        """
        创建 Agent 友好的响应格式
        
        Args:
            data: 操作返回的数据
            operation: 执行的操作名称
            success: 是否成功
            
        Returns:
            增强后的响应字典
        """
        # 生成下一步推荐
        next_actions = AgentHelper._suggest_next_actions(data, operation)
        
        # 获取相关工具
        related_tools = AgentHelper._get_related_tools(operation)
        
        # 学习提示
        learning_tips = AgentHelper._get_learning_tips(operation)
        
        return {
            "operation": operation,
            "success": success,
            "data": data,
            "agent_metadata": {
                "timestamp": datetime.now().isoformat(),
                "next_suggested_actions": next_actions,
                "related_tools": related_tools,
                "learning_tips": learning_tips,
                "predicted_next_operations": AgentHelper.predict_next_operations(operation, data)
            }
        }
    
    @staticmethod
    def _suggest_next_actions(data: Dict, operation: str) -> List[str]:
        """根据操作结果推荐下一步操作"""
        suggestions = []
        
        if operation == "create_object_type":
            obj_id = data.get("object_type_id")
            suggestions.extend([
                f"使用 update_object_type 为 '{obj_id}' 添加更多字段",
                f"使用 create_link_type 建立 '{obj_id}' 与其他对象的关系",
                f"使用 create_action_type 为 '{obj_id}' 创建操作能力",
                f"使用 get_object_type/{obj_id} 验证创建结果"
            ])
        
        elif operation == "create_link_type":
            link_id = data.get("link_type_id")
            suggestions.extend([
                f"使用 get_link_type/{link_id} 验证关系",
                "考虑为相关对象创建更多关系以提升连通性",
                "使用 create_action_type 为关系操作创建 Action"
            ])
        
        elif operation == "create_action_type":
            action_id = data.get("action_type_id")
            suggestions.extend([
                f"使用 test_action_type/{action_id} 测试 Action",
                f"使用 validate_action_code 验证代码质量",
                f"使用 get_action_type/{action_id} 查看完整定义"
            ])
        
        elif operation == "update_object_type":
            obj_id = data.get("object_type_id")
            suggestions.extend([
                f"使用 get_object_type/{obj_id} 查看更新结果",
                "考虑为更新后的对象创建或更新相关 Action",
                "使用语义验证检查更新是否符合规范"
            ])
        
        elif operation == "delete_object_type":
            suggestions.extend([
                "检查是否有其他对象引用了被删除的对象",
                "更新相关的关系类型",
                "使用 get_ontology_management_context 查看更新后的本体状态"
            ])
        
        else:
            suggestions.append("使用 get_ontology_management_context 查看当前本体状态")
        
        return suggestions
    
    @staticmethod
    def _get_related_tools(operation: str) -> List[str]:
        """获取相关工具列表"""
        tool_groups = {
            "create_object_type": ["update_object_type", "create_object_field", "batch_update_fields"],
            "update_object_type": ["get_object_type", "batch_update_fields"],
            "delete_object_type": ["get_ontology_management_context"],
            "create_link_type": ["get_link_type", "validate_link_type_compatibility"],
            "update_link_type": ["get_link_type"],
            "delete_link_type": ["get_ontology_management_context"],
            "create_action_type": ["test_action_type", "validate_action_code", "get_action_type"],
            "update_action_type": ["test_action_type", "get_action_type"],
            "delete_action_type": ["list_action_types"],
            "get_ontology_management_context": ["search_ontology_for_management"],
            "search_ontology_for_management": ["get_object_type", "get_link_type", "get_action_type"]
        }
        
        return tool_groups.get(operation, ["get_ontology_management_context"])
    
    @staticmethod
    def _get_learning_tips(operation: str) -> str:
        """获取学习提示"""
        tips = {
            "create_object_type": "💡 提示：对象类型ID建议使用 snake_case 命名，如 'production_order'。至少包含主键字段和2-3个业务字段。",
            "update_object_type": "💡 提示：可以使用 batch_update_fields 一次性增删改多个字段，提高效率。",
            "create_link_type": "💡 提示：创建关系前建议先用 validate_link_type_compatibility 验证兼容性。",
            "create_action_type": "💡 提示：function 类型的 Action 需要提供 Python 函数代码。"
                                 "代码必须包含: 1)定义执行函数 2)使用OntologySDK处理数据 3)返回标准格式 4)最后调用result=execute(parameters)。"
                                 "建议先用 validate_action_code 验证代码。",
            "test_action_type": "💡 提示：测试执行在事务中完成，不会影响实际数据，可以放心测试。",
            "get_ontology_management_context": "💡 提示：完整性评分基于字段完整度(40%)、关系覆盖度(30%)和Action覆盖度(30%)计算。",
            "search_ontology_for_management": "💡 提示：搜索时会自动检查依赖关系，删除前请注意查看 warnings。"
        }
        
        return tips.get(operation, "💡 提示：使用 get_ontology_management_context 可以全面了解当前本体状态。")
