"""
业务逻辑示例函数 - 供后续撰写函数参考
"""

from typing import Any, Dict, Tuple, List, Optional, Union
from datetime import datetime
import math
from app.utils.data_source_manager import data_source_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


def process_sensor_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理传感器数据

    输入:
        data: 原始传感器数据，包含 temp, humidity 等字段

    输出:
        处理后的数据，包含 temperature(华氏度), humidity, alert_level
    """
    if not isinstance(data, dict):
        return {'error': 'Invalid input data'}

    processed = {
        'temperature': data.get('temp', 0) * 1.8 + 32,
        'humidity': data.get('humidity', 0),
        'pressure': data.get('pressure', 0),
        'alert_level': 'normal',
        'processed_at': datetime.now().isoformat()
    }

    # 计算告警级别
    temp = processed['temperature']
    humidity = processed['humidity']

    if temp > 100 or humidity > 90:
        processed['alert_level'] = 'high'
    elif temp > 80 or humidity > 70:
        processed['alert_level'] = 'medium'
    elif temp > 70 or humidity > 60:
        processed['alert_level'] = 'low'

    return processed


def calculate_risk_score(data: Dict[str, Any]) -> float:
    """
    计算风险评分

    输入:
        data: 处理后的传感器数据

    输出:
        0-1 之间的风险评分
    """
    if not isinstance(data, dict):
        return 0.0

    score = 0.0

    # 基于温度评分
    temp = data.get('temperature', 0)
    if temp > 100:
        score += 0.5
    elif temp > 80:
        score += 0.3
    elif temp > 70:
        score += 0.1

    # 基于湿度评分
    humidity = data.get('humidity', 0)
    if humidity > 90:
        score += 0.3
    elif humidity > 70:
        score += 0.2
    elif humidity > 60:
        score += 0.1

    # 基于告警级别评分
    alert_level = data.get('alert_level', 'normal')
    alert_scores = {'high': 0.2, 'medium': 0.1, 'low': 0.05, 'normal': 0}
    score += alert_scores.get(alert_level, 0)

    return min(score, 1.0)


def check_threshold(value: float, threshold: float, operator: str = 'gt') -> bool:
    """
    检查阈值

    输入:
        value: 要检查的值
        threshold: 阈值
        operator: 操作符 (gt, gte, lt, lte, eq, ne)

    输出:
        是否满足条件
    """
    ops = {
        'gt': lambda a, b: a > b,
        'gte': lambda a, b: a >= b,
        'lt': lambda a, b: a < b,
        'lte': lambda a, b: a <= b,
        'eq': lambda a, b: a == b,
        'ne': lambda a, b: a != b,
    }

    if operator not in ops:
        raise ValueError(f"未知的操作符: {operator}")

    try:
        return ops[operator](value, threshold)
    except TypeError:
        return False


def validate_data(data: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, str]:
    """
    验证数据完整性

    输入:
        data: 要验证的数据
        required_fields: 必需字段列表

    输出:
        (是否有效, 错误信息)
    """
    if not isinstance(data, dict):
        return False, "数据必须是字典类型"

    missing = [f for f in required_fields if f not in data or data[f] is None]

    if missing:
        return False, f"缺少字段: {', '.join(missing)}"

    return True, "验证通过"


def complex_condition(data: Dict[str, Any], event: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    复杂条件判断 - 组合多个函数

    输入:
        data: 原始数据
        event: 事件数据

    输出:
        (是否触发, 处理后的数据)
    """
    # 处理数据
    processed = process_sensor_data(data)

    # 计算风险评分
    risk = calculate_risk_score(processed)

    # 判断是否触发
    should_trigger = risk > 0.5

    # 合并结果
    result = {**processed, 'risk_score': risk, 'triggered': should_trigger}

    return should_trigger, result


def aggregate_values(values: List[float], method: str = 'avg') -> float:
    """
    聚合数值

    输入:
        values: 数值列表
        method: 聚合方法 (avg, sum, max, min, median)

    输出:
        聚合结果
    """
    if not values:
        return 0.0

    clean_values = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]

    if not clean_values:
        return 0.0

    if method == 'avg':
        return sum(clean_values) / len(clean_values)
    elif method == 'sum':
        return sum(clean_values)
    elif method == 'max':
        return max(clean_values)
    elif method == 'min':
        return min(clean_values)
    elif method == 'median':
        sorted_vals = sorted(clean_values)
        n = len(sorted_vals)
        if n % 2 == 0:
            return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        else:
            return sorted_vals[n // 2]
    else:
        raise ValueError(f"未知的聚合方法: {method}")


def time_based_check(data: Dict[str, Any], hour_start: int, hour_end: int) -> bool:
    """
    基于时间的检查

    输入:
        data: 数据（可能包含时间戳）
        hour_start: 开始小时 (0-23)
        hour_end: 结束小时 (0-23)

    输出:
        当前时间是否在指定范围内
    """
    current_hour = datetime.now().hour

    if hour_start <= hour_end:
        return hour_start <= current_hour <= hour_end
    else:
        # 跨天的情况，如 22:00 - 06:00
        return current_hour >= hour_start or current_hour <= hour_end


def multi_condition_check(data: Dict[str, Any], conditions: List[Dict[str, Any]]) -> bool:
    """
    多条件检查

    输入:
        data: 数据
        conditions: 条件列表，每个条件是 {field, operator, value}

    输出:
        是否所有条件都满足
    """
    for condition in conditions:
        field = condition.get('field')
        operator = condition.get('operator', 'eq')
        expected_value = condition.get('value')

        # 获取字段值
        actual_value = data
        for key in field.split('.'):
            if isinstance(actual_value, dict):
                actual_value = actual_value.get(key)
            else:
                return False

        # 检查条件
        if not check_threshold(actual_value, expected_value, operator):
            return False

    return True


def calculate_trend(values: List[float]) -> str:
    """
    计算趋势

    输入:
        values: 数值序列

    输出:
        趋势方向 (rising, falling, stable)
    """
    if len(values) < 2:
        return 'stable'

    clean_values = [v for v in values if isinstance(v, (int, float))]
    if len(clean_values) < 2:
        return 'stable'

    # 简单线性回归斜率
    n = len(clean_values)
    x = list(range(n))
    y = clean_values

    x_mean = sum(x) / n
    y_mean = sum(y) / n

    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 'stable'

    slope = numerator / denominator

    if slope > 0.1:
        return 'rising'
    elif slope < -0.1:
        return 'falling'
    else:
        return 'stable'


def filter_by_condition(items: List[Dict], field: str, operator: str, value: Any) -> List[Dict]:
    """
    根据条件过滤列表

    输入:
        items: 字典列表
        field: 字段路径
        operator: 操作符
        value: 比较值

    输出:
        符合条件的项目列表
    """
    result = []

    for item in items:
        # 获取字段值
        actual_value = item
        for key in field.split('.'):
            if isinstance(actual_value, dict):
                actual_value = actual_value.get(key)
            else:
                actual_value = None
                break

        # 检查条件
        if actual_value is not None and check_threshold(actual_value, value, operator):
            result.append(item)

    return result


def get_data_by_primary_key(data_source_name: str, table: str, primary_key: str, key_value: Any) -> Dict[str, Any]:
    """
    通过主键查询数据
    
    输入:
        data_source_name: 数据源名称
        table: 表名
        primary_key: 主键字段名
        key_value: 主键值
    
    输出:
        查询到的数据字典，未找到返回空字典
    """
    try:
        query = f"SELECT * FROM {table} WHERE {primary_key} = ?"
        params = {primary_key: key_value}
        results = data_source_manager.execute_query(
            data_source_name=data_source_name,
            query=query,
            params=params,
            max_rows=1
        )
        return results[0] if results else {}
    except Exception as e:
        logger.error(f"查询数据失败: {str(e)}")
        return {}


def check_threshold_from_db(data_source_name: str, table: str, primary_key: str, key_value: Any, 
                           threshold_field: str, threshold: float, operator: str = 'gt') -> bool:
    """
    从数据库查询数据并检查阈值
    
    输入:
        data_source_name: 数据源名称
        table: 表名
        primary_key: 主键字段名
        key_value: 主键值
        threshold_field: 要检查的字段
        threshold: 阈值
        operator: 操作符 (gt, gte, lt, lte, eq, ne)
    
    输出:
        是否满足阈值条件
    """
    data = get_data_by_primary_key(data_source_name, table, primary_key, key_value)
    
    if not data or threshold_field not in data:
        return False
    
    field_value = data[threshold_field]
    
    # 使用之前定义的 check_threshold 函数
    return check_threshold(field_value, threshold, operator)


def multi_data_source_check(sources: List[Dict[str, Any]], threshold: float) -> bool:
    """
    从多个数据源查询并进行综合判断
    
    输入:
        sources: 数据源配置列表，每个元素包含 data_source_name, table, primary_key, key_value, field
        threshold: 综合阈值
    
    输出:
        是否满足综合条件
    """
    values = []
    
    for source in sources:
        data = get_data_by_primary_key(
            source['data_source_name'],
            source['table'],
            source['primary_key'],
            source['key_value']
        )
        if source['field'] in data:
            values.append(data[source['field']])
    
    if not values:
        return False
    
    # 计算平均值并检查阈值
    avg_value = sum(values) / len(values)
    return check_threshold(avg_value, threshold, 'gt')


def query_and_process(data_source_name: str, query: str, params: Dict = None, 
                      process_func: str = 'avg', threshold: float = None) -> Tuple[bool, Dict[str, Any]]:
    """
    执行查询并处理结果
    
    输入:
        data_source_name: 数据源名称
        query: SQL 查询语句
        params: 查询参数
        process_func: 处理函数 (avg, sum, max, min)
        threshold: 阈值（可选）
    
    输出:
        (是否满足阈值, 处理结果)
    """
    try:
        results = data_source_manager.execute_query(
            data_source_name=data_source_name,
            query=query,
            params=params
        )
        
        if not results:
            return False, {'error': 'No data found'}
        
        # 提取数值字段
        numeric_fields = []
        for result in results:
            for value in result.values():
                if isinstance(value, (int, float)):
                    numeric_fields.append(value)
        
        # 处理数据
        if not numeric_fields:
            return False, {'error': 'No numeric data'}
        
        if process_func == 'avg':
            processed_value = sum(numeric_fields) / len(numeric_fields)
        elif process_func == 'sum':
            processed_value = sum(numeric_fields)
        elif process_func == 'max':
            processed_value = max(numeric_fields)
        elif process_func == 'min':
            processed_value = min(numeric_fields)
        else:
            processed_value = sum(numeric_fields) / len(numeric_fields)
        
        # 检查阈值
        triggered = False
        if threshold is not None:
            triggered = processed_value > threshold
        
        return triggered, {
            'original_data': results,
            'processed_value': processed_value,
            'triggered': triggered
        }
        
    except Exception as e:
        logger.error(f"查询处理失败: {str(e)}")
        return False, {'error': str(e)}
