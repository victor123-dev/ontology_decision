"""
批量导入所有Action到本体

包含9个Action:
1. predict_material_shortage - 缺料预测 (LP)
2. calculate_ctp - CTP可承诺量计算 (MIP)
3. optimize_purchase_plan - 采购计划优化 (MIP)
4. optimize_capacity_allocation - 产能优化分配 (MIP)
5. optimize_detailed_schedule - 详细排程优化 (CP-SAT)
6. optimize_capacity_allocation_fast - 产能优化分配 (启发式)
7. optimize_detailed_schedule_fast - 详细排程优化 (启发式)
8. recommend_suppliers - 推荐供应商 (紧急采购)
9. emergency_purchase - 紧急采购 (库存预警响应)

功能:
- 导入前先删除已存在的Action（避免重复导入报错）
- 批量导入所有Action
- 输出详细导入结果
"""

import subprocess
import sys
import os
import requests
import time

# API配置
API_URL = "http://localhost:8080/api/v1"

# Action目录
ACTION_DIR = os.path.join(os.path.dirname(__file__), "action_tools")

# Action导入脚本列表
ACTION_SCRIPTS = [
    {
        "name": "缺料预测",
        "file": "import_action_predict_material_shortage.py",
        "action_id": "predict_material_shortage",
        "difficulty": "1星",
        "solver": "LP (GLOP)"
    },
    {
        "name": "CTP可承诺量计算",
        "file": "import_action_calculate_ctp.py",
        "action_id": "calculate_ctp",
        "difficulty": "2星",
        "solver": "MIP (CBC)"
    },
    {
        "name": "采购计划优化",
        "file": "import_action_optimize_purchase_plan.py",
        "action_id": "optimize_purchase_plan",
        "difficulty": "2星",
        "solver": "MIP (CBC)"
    },
    {
        "name": "产能优化分配",
        "file": "import_action_optimize_capacity_allocation.py",
        "action_id": "optimize_capacity_allocation",
        "difficulty": "3星",
        "solver": "MIP (CBC)"
    },
    {
        "name": "详细排程优化",
        "file": "import_action_optimize_detailed_schedule.py",
        "action_id": "optimize_detailed_schedule",
        "difficulty": "4星",
        "solver": "CP-SAT"
    },
    # {  TODO
    #     "name": "产能优化分配（快速）",
    #     "file": "import_action_optimize_capacity_allocation_fast.py",
    #     "action_id": "optimize_capacity_allocation_fast",
    #     "difficulty": "1星",
    #     "solver": "启发式 (EDD/SPT/CR)"
    # },
    # {
    #     "name": "详细排程优化（快速）",
    #     "file": "import_action_optimize_detailed_schedule_fast.py",
    #     "action_id": "optimize_detailed_schedule_fast",
    #     "difficulty": "2星",
    #     "solver": "启发式 (贪婪+2-opt)"
    # },
    {
        "name": "推荐供应商",
        "file": "import_action_recommend_suppliers.py",
        "action_id": "recommend_suppliers",
        "difficulty": "1星",
        "solver": "综合评分模型"
    },
    {
        "name": "紧急采购",
        "file": "import_action_emergency_purchase.py",
        "action_id": "emergency_purchase",
        "difficulty": "1星",
        "solver": "业务逻辑"
    },
    {
        "name": "机会预测工单",
        "file": "import_action_create_opportunity_work_order.py",
        "action_id": "create_opportunity_work_order",
        "difficulty": "1星",
        "solver": "业务逻辑"
    },
]

def delete_existing_actions():
    """删除所有已存在的Action"""
    print("\n" + "=" * 80)
    print("步骤1: 清理已存在的Action")
    print("=" * 80)
    
    deleted_count = 0
    failed_count = 0
    
    for action in ACTION_SCRIPTS:
        action_id = action["action_id"]
        try:
            # 尝试删除Action
            response = requests.delete(f"{API_URL}/actions/{action_id}", timeout=10)
            
            if response.status_code in [200, 204]:
                print(f"  ✅ 已删除: {action['name']} ({action_id})")
                deleted_count += 1
            elif response.status_code == 404:
                print(f"  ⏭️  不存在: {action['name']} ({action_id})")
            else:
                print(f"  ⚠️  删除失败: {action['name']} ({response.status_code})")
                failed_count += 1
        except Exception as e:
            print(f"  ❌ 删除异常: {action['name']} ({str(e)})")
            failed_count += 1
    
    print(f"\n清理完成: 删除 {deleted_count} 个, 失败 {failed_count} 个")
    return failed_count == 0

def main():
    print("=" * 80)
    print("批量导入所有Action到本体")
    print("=" * 80)
    
    # 步骤1: 删除已存在的Action
    cleanup_success = delete_existing_actions()
    
    if not cleanup_success:
        print("\n⚠️  部分Action删除失败，但仍将继续导入...")
    
    # 等待一下确保删除完成
    import time
    time.sleep(1)
    
    # 步骤2: 导入所有Action
    print("\n" + "=" * 80)
    print("步骤2: 导入所有Action")
    print("=" * 80)
    
    success_count = 0
    failed_count = 0
    results = []
    
    for i, action in enumerate(ACTION_SCRIPTS, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(ACTION_SCRIPTS)}] 导入Action: {action['name']}")
        print(f"{'='*80}")
        print(f"   求解器: {action['solver']}")
        print(f"   难度: {action['difficulty']}")
        print()
        
        # 运行导入脚本
        script_path = os.path.join(ACTION_DIR, action['file'])
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            success_count += 1
            results.append({"name": action['name'], "status": "[SUCCESS] 成功"})
            print(f"\n[SUCCESS] {action['name']} 导入成功")
        else:
            failed_count += 1
            results.append({"name": action['name'], "status": "[FAILED] 失败"})
            print(f"\n[FAILED] {action['name']} 导入失败")
            print(f"   错误输出: {result.stderr}")
    
    # 打印汇总
    print(f"\n{'='*80}")
    print("导入完成汇总")
    print(f"{'='*80}")
    print(f"\n总计: {len(ACTION_SCRIPTS)} 个Action")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {failed_count}")
    print()
    
    print("详细结果:")
    for result in results:
        print(f"  {result['status']} {result['name']}")
    
    print(f"\n{'='*80}")
    
    if failed_count == 0:
        print("[SUCCESS] 所有Action导入成功！")
        print()
        print("下一步:")
        print("  1. 在前端本体视图中查看Action")
        print("  2. 测试每个Action的执行")
        print("  3. 根据实际数据调整参数")
    else:
        print("[WARNING] 部分Action导入失败，请检查错误信息")
    
    print(f"{'='*80}\n")
    
    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    exit(main())
