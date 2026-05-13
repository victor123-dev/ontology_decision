"""
语义一致性验证器 - Ontology Management MCP
提供本体元素的命名规范、枚举标准化、跨元素一致性等语义验证功能
"""
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
import re
from app.models.business_model import BusinessModel, BusinessModelField
from app.models.business_model_link import BusinessModelLink


class SemanticValidator:
    """本体语义一致性验证器"""
    
    # 命名规范正则
    SNAKE_CASE_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')
    CAMEL_CASE_PATTERN = re.compile(r'^[a-z][a-zA-Z0-9]*$')
    ENUM_VALUE_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]*$')
    
    # 推荐的字段类型映射
    RECOMMENDED_PK_TYPES = {'string', 'integer'}
    RECOMMENDED_DATE_TYPES = {'date', 'datetime'}
    RECOMMENDED_NUMERIC_TYPES = {'integer', 'float'}
    
    @classmethod
    def validate_object_type_semantics(cls, db: Session, object_type_id: str) -> Dict:
        """
        验证对象类型的语义一致性
        
        Args:
            db: 数据库会话
            object_type_id: 对象类型ID
            
        Returns:
            验证结果字典
        """
        issues = []
        warnings = []
        suggestions = []
        
        model = db.query(BusinessModel).filter(BusinessModel.id == object_type_id).first()
        if not model:
            return {"valid": False, "errors": ["对象类型不存在"], "compliance_score": 0}
        
        # 1. 对象类型ID命名规范检查
        if not cls.SNAKE_CASE_PATTERN.match(model.id):
            issues.append({
                "type": "naming_violation",
                "field": "object_type_id",
                "value": model.id,
                "message": f"对象类型ID '{model.id}' 不符合 snake_case 命名规范",
                "suggestion": "建议使用小写字母和下划线，如 'production_order'"
            })
        
        # 2. API名称检查
        if model.api_name:
            if not cls.CAMEL_CASE_PATTERN.match(model.api_name):
                warnings.append({
                    "type": "api_naming_warning",
                    "field": "api_name",
                    "value": model.api_name,
                    "message": f"API名称 '{model.api_name}' 不符合 camelCase 命名规范"
                })
        
        # 3. 字段验证
        fields = model.fields or []
        field_issues = cls._validate_fields(fields, model.primary_key_id)
        issues.extend(field_issues["issues"])
        warnings.extend(field_issues["warnings"])
        suggestions.extend(field_issues["suggestions"])
        
        # 4. 主键字段语义检查
        pk_field = next((f for f in fields if f.field_id == model.primary_key_id), None)
        if pk_field:
            if pk_field.data_type not in cls.RECOMMENDED_PK_TYPES:
                warnings.append({
                    "type": "pk_type_warning",
                    "field": pk_field.field_id,
                    "message": f"主键字段 '{pk_field.field_id}' 类型为 '{pk_field.data_type}'，建议使用 {cls.RECOMMENDED_PK_TYPES}"
                })
            if not pk_field.required:
                warnings.append({
                    "type": "pk_required_warning",
                    "field": pk_field.field_id,
                    "message": f"主键字段 '{pk_field.field_id}' 应设置为必填"
                })
        
        # 5. 必填字段完整性
        required_fields = [f for f in fields if f.required]
        if len(required_fields) < 2 and len(fields) > 2:
            suggestions.append({
                "type": "completeness_suggestion",
                "message": f"建议至少设置2个必填字段以保证数据质量（当前{len(required_fields)}个）"
            })
        
        # 6. 描述完整性
        if not model.description or len(model.description.strip()) < 10:
            suggestions.append({
                "type": "description_suggestion",
                "message": "建议提供更详细的对象类型描述（至少10个字符）"
            })
        
        # 计算合规分数
        compliance_score = cls._calculate_compliance_score(len(issues), len(warnings), len(fields))
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "suggestions": suggestions,
            "compliance_score": compliance_score,
            "summary": {
                "total_fields": len(fields),
                "required_fields": len(required_fields),
                "enum_fields": len([f for f in fields if f.is_enum]),
                "has_description": bool(model.description and len(model.description.strip()) > 0)
            }
        }
    
    @classmethod
    def _validate_fields(cls, fields: List[BusinessModelField], primary_key_id: str) -> Dict:
        """验证字段列表的语义一致性"""
        issues = []
        warnings = []
        suggestions = []
        
        field_ids = set()
        field_names = set()
        
        for field in fields:
            # 字段ID唯一性检查
            if field.field_id in field_ids:
                issues.append({
                    "type": "duplicate_field_id",
                    "field": field.field_id,
                    "message": f"字段ID '{field.field_id}' 重复"
                })
            field_ids.add(field.field_id)
            
            # 字段名称唯一性检查
            if field.name in field_names:
                warnings.append({
                    "type": "duplicate_field_name",
                    "field": field.field_id,
                    "message": f"字段名称 '{field.name}' 重复（不同字段应有不同名称）"
                })
            field_names.add(field.name)
            
            # 字段ID命名规范
            if not cls.SNAKE_CASE_PATTERN.match(field.field_id):
                issues.append({
                    "type": "field_naming_violation",
                    "field": field.field_id,
                    "message": f"字段ID '{field.field_id}' 不符合 snake_case 命名规范"
                })
            
            # 枚举值标准化检查
            if field.is_enum and field.enum_values:
                enum_issues = cls._validate_enum_values(field.field_id, field.enum_values)
                issues.extend(enum_issues["issues"])
                warnings.extend(enum_issues["warnings"])
            
            # 日期字段类型建议
            if any(keyword in field.field_id.lower() for keyword in ['date', 'time']):
                if field.data_type not in cls.RECOMMENDED_DATE_TYPES:
                    warnings.append({
                        "type": "date_type_warning",
                        "field": field.field_id,
                        "message": f"字段 '{field.field_id}' 名称包含日期关键词，建议使用 {cls.RECOMMENDED_DATE_TYPES} 类型"
                    })
            
            # 数值字段类型建议
            if any(keyword in field.field_id.lower() for keyword in ['count', 'amount', 'quantity', 'price', 'cost']):
                if field.data_type not in cls.RECOMMENDED_NUMERIC_TYPES:
                    warnings.append({
                        "type": "numeric_type_warning",
                        "field": field.field_id,
                        "message": f"字段 '{field.field_id}' 名称包含数值关键词，建议使用 {cls.RECOMMENDED_NUMERIC_TYPES} 类型"
                    })
            
            # 描述完整性
            if not field.description or len(field.description.strip()) < 5:
                suggestions.append({
                    "type": "field_description_suggestion",
                    "field": field.field_id,
                    "message": f"建议为字段 '{field.field_id}' 提供更详细的描述"
                })
        
        return {"issues": issues, "warnings": warnings, "suggestions": suggestions}
    
    @classmethod
    def _validate_enum_values(cls, field_id: str, enum_values: List) -> Dict:
        """验证枚举值的标准化"""
        issues = []
        warnings = []
        
        if not isinstance(enum_values, list):
            issues.append({
                "type": "enum_format_error",
                "field": field_id,
                "message": f"字段 '{field_id}' 的枚举值应为列表格式"
            })
            return {"issues": issues, "warnings": warnings}
        
        # 检查枚举值命名
        for enum_val in enum_values:
            if isinstance(enum_val, str) and not cls.ENUM_VALUE_PATTERN.match(enum_val):
                warnings.append({
                    "type": "enum_naming_warning",
                    "field": field_id,
                    "value": enum_val,
                    "message": f"枚举值 '{enum_val}' 建议使用大写蛇形命名（如 'PENDING_APPROVAL'）"
                })
        
        # 检查枚举值唯一性
        if len(enum_values) != len(set(str(v) for v in enum_values)):
            issues.append({
                "type": "duplicate_enum_values",
                "field": field_id,
                "message": f"字段 '{field_id}' 存在重复的枚举值"
            })
        
        # 检查枚举值数量
        if len(enum_values) > 50:
            warnings.append({
                "type": "too_many_enum_values",
                "field": field_id,
                "message": f"字段 '{field_id}' 枚举值过多（{len(enum_values)}个），建议考虑是否需要拆分"
            })
        
        return {"issues": issues, "warnings": warnings}
    
    @classmethod
    def validate_link_type_semantics(cls, db: Session, link_type_id: str) -> Dict:
        """
        验证关系类型的语义一致性
        
        Args:
            db: 数据库会话
            link_type_id: 关系类型ID
            
        Returns:
            验证结果字典
        """
        link = db.query(BusinessModelLink).filter(BusinessModelLink.id == link_type_id).first()
        if not link:
            return {"valid": False, "errors": ["关系类型不存在"], "compliance_score": 0}
        
        issues = []
        warnings = []
        suggestions = []
        
        # 1. 关系类型ID命名规范
        if not cls.SNAKE_CASE_PATTERN.match(link.id):
            issues.append({
                "type": "naming_violation",
                "field": "link_type_id",
                "value": link.id,
                "message": f"关系类型ID '{link.id}' 不符合 snake_case 命名规范"
            })
        
        # 2. 获取源和目标模型
        source_model = db.query(BusinessModel).filter(BusinessModel.id == link.source_model).first()
        target_model = db.query(BusinessModel).filter(BusinessModel.id == link.target_model).first()
        
        if source_model and target_model:
            # 3. 关系命名语义检查
            expected_keywords = []
            if source_model.id:
                expected_keywords.append(source_model.id.split('_')[0])
            if target_model.id:
                expected_keywords.append(target_model.id.split('_')[0])
            
            link_id_lower = link.id.lower()
            if not any(kw in link_id_lower for kw in expected_keywords if kw):
                suggestions.append({
                    "type": "naming_suggestion",
                    "message": f"关系命名建议包含源对象 '{source_model.id}' 和目标对象 '{target_model.id}' 的关键信息"
                })
            
            # 4. 字段存在性检查
            source_field = db.query(BusinessModelField).filter(
                BusinessModelField.model_id == link.source_model,
                BusinessModelField.field_id == link.source_key
            ).first()
            
            if not source_field:
                issues.append({
                    "type": "missing_source_field",
                    "message": f"源对象 '{source_model.id}' 中不存在字段 '{link.source_key}'"
                })
            
            target_field = db.query(BusinessModelField).filter(
                BusinessModelField.model_id == link.target_model,
                BusinessModelField.field_id == link.target_key
            ).first()
            
            if not target_field:
                issues.append({
                    "type": "missing_target_field",
                    "message": f"目标对象 '{target_model.id}' 中不存在字段 '{link.target_key}'"
                })
            
            # 5. many-to-many 中间表检查
            if link.cardinality == "many-to-many":
                if not link.intermediate_model:
                    issues.append({
                        "type": "missing_intermediate_model",
                        "message": "many-to-many 关系需要提供中间对象类型"
                    })
                else:
                    intermediate_model = db.query(BusinessModel).filter(
                        BusinessModel.id == link.intermediate_model
                    ).first()
                    if not intermediate_model:
                        issues.append({
                            "type": "invalid_intermediate_model",
                            "message": f"中间对象类型 '{link.intermediate_model}' 不存在"
                        })
        
        # 6. 描述完整性
        if not link.description or len(link.description.strip()) < 10:
            suggestions.append({
                "type": "description_suggestion",
                "message": "建议提供更详细的关系描述（至少10个字符）"
            })
        
        compliance_score = cls._calculate_compliance_score(len(issues), len(warnings), 1)
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "suggestions": suggestions,
            "compliance_score": compliance_score
        }
    
    @classmethod
    def cross_validate_consistency(cls, db: Session) -> Dict:
        """
        跨元素一致性验证
        
        Args:
            db: 数据库会话
            
        Returns:
            验证结果字典
        """
        all_models = db.query(BusinessModel).all()
        all_links = db.query(BusinessModelLink).all()
        
        issues = []
        warnings = []
        suggestions = []
        
        # 1. 检查孤立对象（没有任何关系）
        connected_models: Set[str] = set()
        for link in all_links:
            connected_models.add(link.source_model)
            connected_models.add(link.target_model)
        
        orphaned_models = [m for m in all_models if m.id not in connected_models]
        if orphaned_models:
            warnings.append({
                "type": "orphaned_objects",
                "objects": [m.id for m in orphaned_models],
                "message": f"发现 {len(orphaned_models)} 个孤立对象，建议建立关联关系以提高本体连通性"
            })
        
        # 2. 检查命名冲突（对象和关系ID不应重复）
        model_ids = {m.id for m in all_models}
        link_ids = {l.id for l in all_links}
        conflicts = model_ids.intersection(link_ids)
        if conflicts:
            issues.append({
                "type": "naming_conflicts",
                "conflicts": list(conflicts),
                "message": "对象类型和关系类型存在ID冲突，应保持唯一性"
            })
        
        # 3. 检查悬空引用
        for link in all_links:
            if link.source_model not in model_ids:
                issues.append({
                    "type": "dangling_source_reference",
                    "link_id": link.id,
                    "message": f"关系 '{link.id}' 的源对象 '{link.source_model}' 不存在"
                })
            if link.target_model not in model_ids:
                issues.append({
                    "type": "dangling_target_reference",
                    "link_id": link.id,
                    "message": f"关系 '{link.id}' 的目标对象 '{link.target_model}' 不存在"
                })
        
        # 4. 计算连通性指标
        total_models = len(all_models)
        connected_count = len(connected_models)
        connectivity_rate = connected_count / total_models if total_models > 0 else 0
        
        if connectivity_rate < 0.7 and total_models > 3:
            suggestions.append({
                "type": "connectivity_suggestion",
                "message": f"本体连通性为 {connectivity_rate:.1%}，建议提高对象间的关联度（目标>70%）"
            })
        
        # 5. 检查循环依赖（简单检查）
        cycles = cls._detect_cycles(all_models, all_links)
        if cycles:
            warnings.append({
                "type": "circular_dependencies",
                "cycles": cycles,
                "message": f"检测到 {len(cycles)} 个循环依赖，请确认是否为预期设计"
            })
        
        compliance_score = cls._calculate_compliance_score(len(issues), len(warnings), total_models)
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "suggestions": suggestions,
            "compliance_score": compliance_score,
            "metrics": {
                "total_objects": total_models,
                "total_links": len(all_links),
                "connected_objects": connected_count,
                "orphaned_objects": len(orphaned_models),
                "connectivity_rate": connectivity_rate,
                "circular_dependencies": len(cycles)
            }
        }
    
    @classmethod
    def _detect_cycles(cls, models: List[BusinessModel], links: List[BusinessModelLink]) -> List[List[str]]:
        """检测循环依赖（简化版DFS）"""
        # 构建邻接表
        graph: Dict[str, List[str]] = {}
        for model in models:
            graph[model.id] = []
        
        for link in links:
            if link.source_model in graph and link.target_model in graph:
                graph[link.source_model].append(link.target_model)
        
        # DFS检测循环
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # 找到循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
            
            path.pop()
            rec_stack.remove(node)
        
        for model in models:
            if model.id not in visited:
                dfs(model.id, [])
        
        return cycles[:5]  # 最多返回5个循环
    
    @classmethod
    def _calculate_compliance_score(cls, issues_count: int, warnings_count: int, total_items: int) -> float:
        """
        计算合规分数 (0-100)
        
        Args:
            issues_count: 问题数量
            warnings_count: 警告数量
            total_items: 总项目数
            
        Returns:
            合规分数
        """
        if total_items == 0:
            return 0.0
        
        base_score = 100.0
        issue_penalty = issues_count * 15
        warning_penalty = warnings_count * 5
        
        score = max(0, base_score - issue_penalty - warning_penalty)
        return round(score, 2)
