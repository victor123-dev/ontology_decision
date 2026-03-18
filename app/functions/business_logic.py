"""
业务逻辑函数 - First Order 驱动逻辑可调用的业务函数
"""

from app.utils.data_source_manager import data_source_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


def check_product_spec_coverage(spec_requirement: str) -> bool:
    """
    新旧品判断 - 检查规格是否被现有产品覆盖
    
    输入:
        spec_requirement: 规格要求，格式为"xxx，yyy，zzz"（中文逗号分隔）
    
    输出:
        是否有产品完全覆盖该规格要求
    """
    try:
        # 解析规格要求
        req_specs = set([spec.strip() for spec in spec_requirement.split('，') if spec.strip()])
        if not req_specs:
            logger.warning("规格要求为空")
            return False
        
        # 构建带有过滤条件的查询
        # 提取关键词进行初步过滤，减少数据量
        keywords = list(req_specs)
        if keywords:
            # 构建 LIKE 条件
            where_conditions = []
            for keyword in keywords:
                where_conditions.append(f"specification LIKE '%{keyword}%'")
            
            where_clause = " WHERE " + " AND ".join(where_conditions)
            query = f"SELECT specification FROM product{where_clause}"
        else:
            query = "SELECT specification FROM product"
        
        logger.debug(f"执行查询: {query}")
        
        results = data_source_manager.execute_query(
            data_source_name='commander_data_database',
            query=query,
            max_rows=1000
        )
        
        if not results:
            logger.warning("未查询到产品数据")
            return False
        
        # 检查每个产品的规格是否覆盖要求
        for result in results:
            product_spec = result.get('specification', '')
            if not product_spec:
                continue
            
            # 解析产品规格
            product_specs = set([spec.strip() for spec in product_spec.split('，') if spec.strip()])
            
            # 检查规格要求是否完全被产品规格覆盖
            if req_specs.issubset(product_specs):
                logger.info(f"找到匹配的产品规格: {product_spec}")
                return True
        
        # 没有找到匹配的产品
        logger.info(f"未找到覆盖规格要求的产品: {spec_requirement}")
        return False
    except Exception as e:
        logger.error(f"检查产品规格失败: {str(e)}")
        return False
