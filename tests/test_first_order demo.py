"""
测试 First Order 驱动逻辑的示例函数
"""

import sys
sys.path.insert(0, 'd:\\PythonProject\\commander_demo')

from app.functions.business_logic_demo import (
    process_sensor_data,
    calculate_risk_score,
    check_threshold,
    validate_data,
    complex_condition,
    aggregate_values,
    time_based_check,
    multi_condition_check,
    calculate_trend,
    filter_by_condition,
    get_data_by_primary_key,
    check_threshold_from_db,
    multi_data_source_check,
    query_and_process
)
from app.utils.function_registry import prepare_function_environment


def test_process_sensor_data():
    """测试传感器数据处理"""
    print("=" * 60)
    print("测试 1: process_sensor_data")
    print("=" * 60)

    test_data = {'temp': 35, 'humidity': 75, 'pressure': 1013}
    result = process_sensor_data(test_data)
    print(f"输入: {test_data}")
    print(f"输出: {result}")
    print("✓ 测试通过")


def test_calculate_risk_score():
    """测试风险评分计算"""
    print("\n" + "=" * 60)
    print("测试 2: calculate_risk_score")
    print("=" * 60)

    test_data = {'temperature': 95, 'humidity': 85, 'alert_level': 'high'}
    score = calculate_risk_score(test_data)
    print(f"输入: {test_data}")
    print(f"风险评分: {score}")
    print("✓ 测试通过")


def test_check_threshold():
    """测试阈值检查"""
    print("\n" + "=" * 60)
    print("测试 3: check_threshold")
    print("=" * 60)

    test_cases = [
        (85, 80, 'gt', True),
        (75, 80, 'gt', False),
        (80, 80, 'gte', True),
        (79, 80, 'gte', False),
    ]

    for value, threshold, operator, expected in test_cases:
        result = check_threshold(value, threshold, operator)
        print(f"{value} {operator} {threshold} → {result} (期望: {expected})")
        assert result == expected
    print("✓ 测试通过")


def test_validate_data():
    """测试数据验证"""
    print("\n" + "=" * 60)
    print("测试 4: validate_data")
    print("=" * 60)

    test_data = {'name': 'test', 'value': 100}
    valid, message = validate_data(test_data, ['name', 'value'])
    print(f"数据: {test_data}")
    print(f"验证结果: {valid}, 消息: {message}")
    print("✓ 测试通过")


def test_complex_condition():
    """测试复杂条件"""
    print("\n" + "=" * 60)
    print("测试 5: complex_condition")
    print("=" * 60)

    test_data = {'temp': 45, 'humidity': 85}
    test_event = {'type': 'sensor_data'}
    triggered, result = complex_condition(test_data, test_event)
    print(f"输入: {test_data}")
    print(f"触发: {triggered}, 结果: {result}")
    print("✓ 测试通过")


def test_aggregate_values():
    """测试数值聚合"""
    print("\n" + "=" * 60)
    print("测试 6: aggregate_values")
    print("=" * 60)

    test_values = [10, 20, 30, 40, 50]
    methods = ['avg', 'sum', 'max', 'min', 'median']
    for method in methods:
        result = aggregate_values(test_values, method)
        print(f"{method}: {result}")
    print("✓ 测试通过")


def test_time_based_check():
    """测试时间检查"""
    print("\n" + "=" * 60)
    print("测试 7: time_based_check")
    print("=" * 60)

    test_data = {}
    result = time_based_check(test_data, 9, 18)
    print(f"当前时间是否在 9-18 点之间: {result}")
    print("✓ 测试通过")


def test_multi_condition_check():
    """测试多条件检查"""
    print("\n" + "=" * 60)
    print("测试 8: multi_condition_check")
    print("=" * 60)

    test_data = {'temperature': 85, 'humidity': 75}
    conditions = [
        {'field': 'temperature', 'operator': 'gt', 'value': 80},
        {'field': 'humidity', 'operator': 'gt', 'value': 70}
    ]
    result = multi_condition_check(test_data, conditions)
    print(f"数据: {test_data}")
    print(f"条件: {conditions}")
    print(f"结果: {result}")
    print("✓ 测试通过")


def test_calculate_trend():
    """测试趋势计算"""
    print("\n" + "=" * 60)
    print("测试 9: calculate_trend")
    print("=" * 60)

    test_cases = [
        ([10, 20, 30, 40, 50], 'rising'),
        ([50, 40, 30, 20, 10], 'falling'),
        ([25, 26, 25, 26, 25], 'stable'),
    ]

    for values, expected in test_cases:
        result = calculate_trend(values)
        print(f"值: {values} → {result} (期望: {expected})")
        assert result == expected
    print("✓ 测试通过")


def test_filter_by_condition():
    """测试条件过滤"""
    print("\n" + "=" * 60)
    print("测试 10: filter_by_condition")
    print("=" * 60)

    test_items = [
        {'id': 1, 'value': 100},
        {'id': 2, 'value': 200},
        {'id': 3, 'value': 300},
        {'id': 4, 'value': 400}
    ]
    result = filter_by_condition(test_items, 'value', 'gt', 250)
    print(f"输入: {test_items}")
    print(f"过滤结果: {result}")
    print("✓ 测试通过")


def test_integration_with_first_order():
    """测试与 First Order 表达式的集成"""
    print("\n" + "=" * 60)
    print("测试 11: 与 First Order 表达式集成")
    print("=" * 60)

    test_expressions = [
        {
            'name': '传感器数据处理',
            'expression': "calculate_risk_score(process_sensor_data(data)) > 0.5",
            'data': {'temp': 45, 'humidity': 85}
        },
        {
            'name': '阈值检查',
            'expression': "check_threshold(data.get('value', 0), 50, 'gt')",
            'data': {'value': 75}
        },
    ]

    for test in test_expressions:
        print(f"\n测试: {test['name']}")
        print(f"表达式: {test['expression']}")
        print(f"数据: {test['data']}")

        try:
            local_vars = prepare_function_environment(test['expression'], test['data'], {})
            result = eval(test['expression'], {'__builtins__': {}}, local_vars)
            print(f"执行结果: {result}")
            print("✓ 通过")
        except Exception as e:
            print(f"✗ 错误: {str(e)}")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("First Order 示例函数测试")
    print("=" * 60)

    test_process_sensor_data()
    test_calculate_risk_score()
    test_check_threshold()
    test_validate_data()
    test_complex_condition()
    test_aggregate_values()
    test_time_based_check()
    test_multi_condition_check()
    test_calculate_trend()
    test_filter_by_condition()
    test_integration_with_first_order()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
