"""
外部供应链风险服务类
提供风险事件查询、统计和分析功能
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter

from app.services.dashbaord.sdk_client import get_ontology_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RiskService:
    """外部供应链风险服务类"""
    
    def __init__(self):
        self.client = get_ontology_client()
    
    def get_active_risks(self, limit: int = 50) -> List[Dict]:
        """获取活跃风险事件(status in ['新发现', '待处理', '分析中', '缓解中'])"""
        try:
            all_risks = self.client.models.ExternalSupplyChainRisk.find()
            
            active_risks = []
            for risk in all_risks:
                status = getattr(risk, 'status', '')
                if status in ['新发现', '待处理', '分析中', '缓解中']:
                    # 获取供应商信息
                    supplier_id = getattr(risk, 'supplier_id', '')
                    supplier_name = ''
                    if supplier_id:
                        suppliers = self.client.models.Supplier.find(supplier_id=supplier_id)
                        if suppliers:
                            supplier_name = getattr(suppliers[0], 'supplier_name', '')
                    
                    # 获取关联供应商列表(通过SupplierRiskAssociation)
                    affected_suppliers = self._get_affected_suppliers(getattr(risk, 'risk_id', ''))
                    
                    active_risks.append({
                        'risk_id': getattr(risk, 'risk_id', ''),
                        'title': getattr(risk, 'title', ''),
                        'risk_category': getattr(risk, 'risk_category', ''),
                        'risk_level': getattr(risk, 'risk_level', ''),
                        'supplier_id': supplier_id,
                        'supplier_name': supplier_name,
                        'customer_id': getattr(risk, 'customer_id', ''),
                        'material_id': getattr(risk, 'material_id', ''),
                        'status': status,
                        'impact_scope': getattr(risk, 'impact_scope', ''),
                        'estimated_impact_days': getattr(risk, 'estimated_impact_days', 0),
                        'detected_at': getattr(risk, 'detected_at', ''),
                        'event_date': getattr(risk, 'event_date', ''),
                        'source_name': getattr(risk, 'source_name', ''),
                        'confidence_score': getattr(risk, 'confidence_score', 0),
                        'affected_suppliers': affected_suppliers,
                        'description': getattr(risk, 'description', '')
                    })
            
            # 按检测时间倒序
            active_risks.sort(key=lambda x: x.get('detected_at', ''), reverse=True)
            return active_risks[:limit]
        except Exception as e:
            logger.error(f"获取活跃风险失败: {e}")
            return []
    
    def _get_affected_suppliers(self, risk_id: str) -> List[Dict]:
        """获取风险事件关联的供应商列表"""
        try:
            if not risk_id:
                return []
            
            associations = self.client.models.SupplierRiskAssociation.find(risk_id=risk_id)
            result = []
            
            for assoc in associations:
                supplier_id = getattr(assoc, 'supplier_id', '')
                if supplier_id:
                    suppliers = self.client.models.Supplier.find(supplier_id=supplier_id)
                    supplier_name = getattr(suppliers[0], 'supplier_name', '') if suppliers else ''
                    
                    result.append({
                        'supplier_id': supplier_id,
                        'supplier_name': supplier_name,
                        'association_type': getattr(assoc, 'association_type', ''),
                        'impact_level': getattr(assoc, 'impact_level', ''),
                        'note': getattr(assoc, 'note', '')
                    })
            
            return result
        except Exception as e:
            logger.error(f"获取关联供应商失败: {e}")
            return []
    
    def get_risk_statistics(self) -> Dict:
        """获取风险统计数据(按类别、等级、状态分组)"""
        try:
            all_risks = self.client.models.ExternalSupplyChainRisk.find()
            
            by_category = Counter()
            by_level = Counter()
            by_status = Counter()
            
            for risk in all_risks:
                category = getattr(risk, 'risk_category', 'unknown')
                level = getattr(risk, 'risk_level', 'unknown')
                status = getattr(risk, 'status', 'unknown')
                
                by_category[category] += 1
                by_level[level] += 1
                by_status[status] += 1
            
            return {
                'by_category': dict(by_category),
                'by_level': dict(by_level),
                'by_status': dict(by_status),
                'total_count': len(all_risks)
            }
        except Exception as e:
            logger.error(f"获取风险统计失败: {e}")
            return {'by_category': {}, 'by_level': {}, 'by_status': {}, 'total_count': 0}
    
    def get_risk_trend(self, days: int = 30) -> List[Dict]:
        """获取近N天风险趋势"""
        try:
            all_risks = self.client.models.ExternalSupplyChainRisk.find()
            now = datetime.now()
            start_date = now - timedelta(days=days)
            
            # 按日期统计
            daily_count = Counter()
            for risk in all_risks:
                detected_at_str = getattr(risk, 'detected_at', '')
                if detected_at_str:
                    try:
                        detected_at = datetime.fromisoformat(detected_at_str.replace('Z', '+00:00').replace('+00:00', ''))
                        if detected_at >= start_date:
                            date_key = detected_at.strftime('%Y-%m-%d')
                            daily_count[date_key] += 1
                    except:
                        continue
            
            # 生成完整日期序列
            trend_data = []
            for i in range(days):
                date = start_date + timedelta(days=i)
                date_key = date.strftime('%Y-%m-%d')
                trend_data.append({
                    'date': date_key,
                    'count': daily_count.get(date_key, 0)
                })
            
            return trend_data
        except Exception as e:
            logger.error(f"获取风险趋势失败: {e}")
            return []
    
    def get_top_affected_suppliers(self, limit: int = 5) -> List[Dict]:
        """获取受影响最严重的TOP5供应商"""
        try:
            all_associations = self.client.models.SupplierRiskAssociation.find()
            
            supplier_stats = {}
            for assoc in all_associations:
                supplier_id = getattr(assoc, 'supplier_id', '')
                if not supplier_id:
                    continue
                
                if supplier_id not in supplier_stats:
                    supplier_stats[supplier_id] = {
                        'risk_count': 0,
                        'max_impact_level': '低',
                        'association_types': []
                    }
                
                supplier_stats[supplier_id]['risk_count'] += 1
                
                impact_level = getattr(assoc, 'impact_level', '低')
                assoc_type = getattr(assoc, 'association_type', '')
                
                # 更新最高影响等级
                level_priority = {'严重': 4, '高': 3, '中': 2, '低': 1}
                current_max = supplier_stats[supplier_id]['max_impact_level']
                if level_priority.get(impact_level, 0) > level_priority.get(current_max, 0):
                    supplier_stats[supplier_id]['max_impact_level'] = impact_level
                
                if assoc_type:
                    supplier_stats[supplier_id]['association_types'].append(assoc_type)
            
            # 构建结果
            result = []
            for supplier_id, stats in supplier_stats.items():
                suppliers = self.client.models.Supplier.find(supplier_id=supplier_id)
                supplier_name = getattr(suppliers[0], 'supplier_name', '') if suppliers else ''
                
                result.append({
                    'supplier_id': supplier_id,
                    'supplier_name': supplier_name,
                    'risk_count': stats['risk_count'],
                    'max_impact_level': stats['max_impact_level'],
                    'association_types': list(set(stats['association_types']))
                })
            
            # 按风险数量排序
            result.sort(key=lambda x: x['risk_count'], reverse=True)
            return result[:limit]
        except Exception as e:
            logger.error(f"获取受影响供应商失败: {e}")
            return []
    
    def get_active_risk_count(self) -> int:
        """获取活跃风险事件数量"""
        try:
            all_risks = self.client.models.ExternalSupplyChainRisk.find()
            count = sum(1 for risk in all_risks if getattr(risk, 'status', '') in ['新发现', '待处理', '分析中', '缓解中'])
            return count
        except Exception as e:
            logger.error(f"获取活跃风险数量失败: {e}")
            return 0
    
    def get_high_risk_supplier_count(self) -> int:
        """获取高风险供应商数量(受critical/high影响的供应商)"""
        try:
            all_associations = self.client.models.SupplierRiskAssociation.find()
            
            high_risk_suppliers = set()
            for assoc in all_associations:
                impact_level = getattr(assoc, 'impact_level', '')
                if impact_level in ['严重', '高']:
                    supplier_id = getattr(assoc, 'supplier_id', '')
                    if supplier_id:
                        high_risk_suppliers.add(supplier_id)
            
            return len(high_risk_suppliers)
        except Exception as e:
            logger.error(f"获取高风险供应商数量失败: {e}")
            return 0
