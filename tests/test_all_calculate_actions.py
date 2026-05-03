"""
测试所有优化算法 Action
基于真实本体实例数据，逐个验证启发式和 OR-Tools 算法
"""
import requests
import json
import time
from datetime import datetime

API = "http://localhost:8080/api/v1"

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(title, success, data, duration):
    print(f"\n{'=' * 70}")
    print(f"  {title} - {'成功 ✅' if success else '失败 ❌'} ({duration:.2f}秒)")
    print(f"{'=' * 70}")
    if success:
        result = data.get("result", data)
        if isinstance(result, dict):
            for key, value in result.items():
                if key not in ["schedule", "purchase_plan", "shortage_details", "debug_info", "work_order_priorities"]:
                    print(f"  {key}: {value}")
            for key, value in result.items():
                if isinstance(value, list):
                    print(f"  {key}: {len(value)} 条记录")
                    if value and len(value) > 0:
                        print(f"    样例: {json.dumps(value[0], ensure_ascii=False, indent=6)[:120]}...")
    else:
        error = data.get("error", "Unknown error") if data else "No response"
        print(f"  错误: {error}")
    print()

def test_action(action_id, action_name, parameters, timeout=120):
    print_header(f"测试: {action_name}")
    print(f"Action ID: {action_id}")
    print(f"参数: {json.dumps(parameters, ensure_ascii=False, indent=2)}")
    
    start = time.time()
    try:
        r = requests.post(
            f"{API}/actions/execute",
            json={
                "action_id": action_id,
                "parameters": parameters
            },
            # timeout=timeout
        )
        duration = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            success = data.get("success", False)
            print_result(action_name, success, data, duration)
            return success, data, duration
        else:
            print(f"  HTTP 错误: {r.status_code}")
            print(f"  响应: {r.text[:500]}")
            return False, None, duration
    except requests.exceptions.Timeout:
        duration = time.time() - start
        print(f"  ⏱️ 超时 ({duration:.2f}秒 > {timeout}秒)")
        return False, None, duration
    except Exception as e:
        duration = time.time() - start
        print(f"  ❌ 异常: {str(e)}")
        return False, None, duration

def main():
    print_header("优化算法 Action 测试套件")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取工单数据
    r = requests.post(f"{API}/business-data/work_order/query", json={"filters": []})
    all_work_orders = r.json().get("data", []) if r.status_code == 200 else []
    all_wo_ids = [wo["work_order_id"] for wo in all_work_orders[:10]]
    print(f"\n工单数据: {len(all_work_orders)} 条，测试用前 {len(all_wo_ids)} 个: {all_wo_ids[:3]}...")
    
    # 获取客户订单
    r = requests.post(f"{API}/business-data/customer_order/query", json={"filters": []})
    customer_orders = r.json().get("data", []) if r.status_code == 200 else []
    sample_co = customer_orders[0] if customer_orders else None
    sample_co_id = sample_co.get("order_id") if sample_co else None
    print(f"客户订单: {len(customer_orders)} 条，测试用: {sample_co_id}")
    
    # 获取物料数据
    r = requests.post(f"{API}/business-data/material/query", json={"filters": []})
    all_materials = r.json().get("data", []) if r.status_code == 200 else []
    all_material_ids = [m["material_id"] for m in all_materials[:20]]
    print(f"物料数据: {len(all_materials)} 条，测试用前 {len(all_material_ids)} 个: {all_material_ids[:3]}...")
    
    results = []
    
    # ==========================================
    # 测试 1: 启发式详细排程
    # ==========================================
    if all_wo_ids:
        success, data, duration = test_action(
            "optimize_detailed_schedule_heuristic",
            "启发式详细排程 (Greedy)",
            {
                "work_order_ids": all_wo_ids,
                "planning_horizon_days": 30,
                "consider_setup": False
            },
            timeout=60
        )
        results.append(("启发式详细排程", success, duration))
    
    # ==========================================
    # 测试 2: 启发式产能优化
    # ==========================================
    if all_wo_ids:
        success, data, duration = test_action(
            "optimize_capacity_allocation_heuristic",
            "启发式产能优化 (EDD/SPT/CR)",
            {
                "work_order_ids": all_wo_ids,
                "planning_horizon_days": 30,
                "scheduling_rule": "EDD"
            },
            timeout=60
        )
        results.append(("启发式产能优化", success, duration))
    
    # ==========================================
    # 测试 3: CTP 可承诺量计算
    # ==========================================
    if sample_co:
        product_id = sample_co.get("product_id")
        quantity = sample_co.get("quantity", 1000)
        success, data, duration = test_action(
            "calculate_ctp",
            "CTP可承诺量计算 (MIP)",
            {
                "product_id": product_id,
                "quantity": quantity
            },
            timeout=120
        )
        results.append(("CTP计算", success, duration))
    
    # ==========================================
    # 测试 4: CP-SAT 详细排程
    # ==========================================
    if all_wo_ids:
        success, data, duration = test_action(
            "optimize_detailed_schedule",
            "CP-SAT详细排程",
            {
                "work_order_ids": all_wo_ids[:3],  # 限制工单数
                "planning_horizon_days": 7,
                "consider_setup": False
            },
            timeout=300
        )
        results.append(("CP-SAT详细排程", success, duration))
    
    # ==========================================
    # 测试 5: MIP 产能优化
    # ==========================================
    if all_wo_ids:
        success, data, duration = test_action(
            "optimize_capacity_allocation",
            "MIP产能优化 (CBC)",
            {
                "work_order_ids": all_wo_ids[:2],  # 限制工单数
                "planning_horizon_days": 7
            },
            timeout=180
        )
        results.append(("MIP产能优化", success, duration))
    
    # ==========================================
    # 测试 6: 缺料预测
    # ==========================================
    success, data, duration = test_action(
        "predict_material_shortage",
        "缺料预测 (LP)",
        {
            "forecast_days": 30,
            "material_ids": all_material_ids if all_material_ids else []
        },
        timeout=60
    )
    results.append(("缺料预测", success, duration))
    
    # ==========================================
    # 测试 7: MIP 采购计划优化
    # ==========================================
    if all_material_ids:
        success, data, duration = test_action(
            "optimize_purchase_plan",
            "MIP采购计划优化 (CBC)",
            {
                "material_ids": all_material_ids,
                "forecast_days": 30
            },
            timeout=60
        )
        results.append(("MIP采购计划优化", success, duration))
    
    # ==========================================
    # 汇总结果
    # ==========================================
    print_header("测试汇总")
    print(f"\n{'Action名称':<30} {'结果':<10} {'耗时(秒)':<10}")
    print("-" * 50)
    for name, success, duration in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{name:<30} {status:<10} {duration:<10.2f}")
    
    total = len(results)
    success_count = sum(1 for _, s, _ in results if s)
    failed_count = total - success_count
    total_time = sum(d for _, _, d in results)
    
    print(f"\n总计: {total} 个测试")
    print(f"成功: {success_count} 个")
    print(f"失败: {failed_count} 个")
    print(f"总耗时: {total_time:.2f} 秒 ({total_time/60:.1f} 分钟)")
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
