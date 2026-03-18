"""
测试 First Order 驱动逻辑的函数调用功能
"""

import sys
sys.path.insert(0, 'd:\\PythonProject\\commander_demo')

from app.functions.business_logic import check_product_spec_coverage, check_material_price_fluctuation
from app.utils.function_registry import prepare_function_environment


def test_check_product_spec_coverage():
    """测试产品规格覆盖检查"""
    print("=" * 60)
    print("测试 1: 产品规格覆盖检查")
    print("=" * 60)

    test_cases = [
        {
            'name': '完全匹配的规格',
            'spec': '食品级塑料容器，容量500ml，耐高温100℃',
            'expected': True
        },
        {
            'name': '不完全匹配的规格',
            'spec': '食品级塑料容器，容量200ml，耐高温80℃',
            'expected': False
        },
        {
            'name': '部分匹配的规格',
            'spec': '食品级塑料容器，容量500ml',
            'expected': True
        },
        {
            'name': '空规格',
            'spec': '',
            'expected': False
        },
        {
            'name': '只有空格的规格',
            'spec': '   ',
            'expected': False
        },
    ]

    for case in test_cases:
        print(f"\n测试: {case['name']}")
        print(f"规格: {case['spec']}")
        print(f"期望: {case['expected']}")

        try:
            result = check_product_spec_coverage(case['spec'])
            print(f"结果: {result}")

            if result == case['expected']:
                print("✓ 通过")
            else:
                print("✗ 失败")
        except Exception as e:
            print(f"✗ 错误: {str(e)}")


def test_integration_with_first_order():
    """测试与 First Order 表达式的集成"""
    print("\n" + "=" * 60)
    print("测试 2: 与 First Order 表达式集成")
    print("=" * 60)

    test_expressions = [
        {
            'name': '完全匹配的规格',
            'expression': "check_product_spec_coverage('食品级塑料容器，容量500ml，耐高温100℃')",
            'expected': True
        },
        {
            'name': '不完全匹配的规格',
            'expression': "check_product_spec_coverage('食品级塑料容器，容量200ml，耐高温80℃')",
            'expected': False
        },
    ]

    for test in test_expressions:
        print(f"\n测试: {test['name']}")
        print(f"表达式: {test['expression']}")
        print(f"期望: {test['expected']}")

        try:
            local_vars = prepare_function_environment(test['expression'], {}, {})
            result = eval(test['expression'], {'__builtins__': {}}, local_vars)
            print(f"结果: {result}")

            if result == test['expected']:
                print("✓ 通过")
            else:
                print("✗ 失败")
        except Exception as e:
            print(f"✗ 错误: {str(e)}")


def test_material_price_fluctuation():
    """测试物料价格波动判断"""
    print("\n" + "=" * 60)
    print("测试 3: 物料价格波动判断")
    print("=" * 60)

    # 测试物料 ID 为 1
    material_id = 1
    print(f"\n测试: 物料 ID = {material_id}")
    print(f"期望: True (因为价格快照少于3笔)")
    
    try:
        result = check_material_price_fluctuation(material_id)
        print(f"结果: {result}")
        # 由于只有1笔价格快照，应该返回 True
        if result == True:
            print("✓ 通过")
        else:
            print("✗ 失败")
    except Exception as e:
        print(f"✗ 错误: {str(e)}")

    # 测试与 First Order 表达式的集成
    test_expression = "check_material_price_fluctuation(1)"
    print(f"\n测试: 与 First Order 表达式集成")
    print(f"表达式: {test_expression}")
    print(f"期望: True")
    
    try:
        local_vars = prepare_function_environment(test_expression, {}, {})
        result = eval(test_expression, {'__builtins__': {}}, local_vars)
        print(f"结果: {result}")
        if result == True:
            print("✓ 通过")
        else:
            print("✗ 失败")
    except Exception as e:
        print(f"✗ 错误: {str(e)}")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("First Order 函数测试")
    print("=" * 60)

    test_check_product_spec_coverage()
    test_integration_with_first_order()
    test_material_price_fluctuation()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
