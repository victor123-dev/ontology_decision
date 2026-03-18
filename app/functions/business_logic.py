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
        # 检查参数是否为 None
        if spec_requirement is None:
            logger.warning("规格要求为 None")
            return False
            
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


def check_material_price_fluctuation(material_id: int) -> bool:
    """
    物料价格波动判断
    
    输入:
        material_id: 物料ID
    
    输出:
        bool: 是否需要关注价格波动
              - 若查到小于三笔价格快照，返回true
              - 若价格波动大于阈值，返回true
              - 否则返回false
    """
    try:
        # 检查参数
        if material_id is None:
            logger.warning("物料ID为 None")
            return True
        
        # 1. 查询最新的三笔价格快照
        price_query = f"""
        SELECT price, valid_from 
        FROM price_snapshot 
        WHERE material_id = {material_id} 
        ORDER BY valid_from DESC 
        LIMIT 3
        """
        
        price_results = data_source_manager.execute_query(
            data_source_name='commander_data_database',
            query=price_query,
            max_rows=3
        )
        
        # 若查到小于三笔，返回true
        if len(price_results) < 3:
            logger.info(f"物料 {material_id} 的价格快照少于3笔: {len(price_results)}笔")
            return True
        
        # 2. 获取价格阈值
        threshold_query = """
        SELECT threshold_percent 
        FROM rule_price 
        WHERE status = 'ACTIVE' 
        LIMIT 1
        """
        
        threshold_results = data_source_manager.execute_query(
            data_source_name='commander_data_database',
            query=threshold_query,
            max_rows=1
        )
        
        if not threshold_results:
            logger.warning("未找到有效的价格波动规则")
            return True
        
        threshold_percent = threshold_results[0].get('threshold_percent', 5.0)
        logger.debug(f"价格波动阈值: {threshold_percent}%")
        
        # 3. 提取价格并计算波动
        prices = [result.get('price', 0) for result in price_results]
        logger.debug(f"最新三笔价格: {prices}")
        
        # 计算价格间的波动
        for i in range(len(prices) - 1):
            price1 = prices[i]
            price2 = prices[i + 1]
            
            if price2 == 0:
                continue
                
            # 计算波动百分比
            fluctuation = abs((price1 - price2) / price2 * 100)
            logger.debug(f"价格波动: {fluctuation:.2f}%")
            
            # 若波动大于阈值，返回true
            if fluctuation > threshold_percent:
                logger.info(f"物料 {material_id} 价格波动超过阈值: {fluctuation:.2f}% > {threshold_percent}%")
                return True
        
        # 价格波动在阈值范围内
        logger.info(f"物料 {material_id} 价格波动在正常范围内")
        return False
    except Exception as e:
        logger.error(f"检查物料价格波动失败: {str(e)}")
        return True
