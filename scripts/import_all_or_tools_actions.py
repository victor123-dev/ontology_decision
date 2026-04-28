"""
批量导入所有OR-Tools优化Action到本体

包含5个Action:
1. predict_material_shortage - 缺料预测 (LP)
2. calculate_ctp - CTP可承诺量计算 (MIP)
3. optimize_purchase_plan - 采购计划优化 (MIP)
4. optimize_capacity_allocation - 产能优化分配 (MIP)
5. optimize_detailed_schedule - 详细排程优化 (CP-SAT)
"""
import subprocess
import sys

# Action导入脚本列表
ACTION_SCRIPTS = [
    {
        "name": "缺料预测",
        "file": "import_action_predict_material_shortage.py",
        "difficulty": "1星",
        "solver": "LP (GLOP)"
    },
    {
        "name": "CTP可承诺量计算",
        "file": "import_action_calculate_ctp.py",
        "difficulty": "2星",
        "solver": "MIP (CBC)"
    },
    {
        "name": "采购计划优化",
        "file": "import_action_optimize_purchase_plan.py",
        "difficulty": "2星",
        "solver": "MIP (CBC)"
    },
    {
        "name": "产能优化分配",
        "file": "import_action_optimize_capacity_allocation.py",
        "difficulty": "3星",
        "solver": "MIP (CBC)"
    },
    {
        "name": "详细排程优化",
        "file": "import_action_optimize_detailed_schedule.py",
        "difficulty": "4星",
        "solver": "CP-SAT"
    }
]

def main():
    print("=" * 80)
    print("批量导入OR-Tools优化Action到本体")
    print("=" * 80)
    print()
    
    success_count = 0
    failed_count = 0
    results = []
    
    for i, action in enumerate(ACTION_SCRIPTS, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/5] 导入Action: {action['name']}")
        print(f"{'='*80}")
        print(f"   求解器: {action['solver']}")
        print(f"   难度: {action['difficulty']}")
        print()
        
        # 运行导入脚本
        result = subprocess.run(
            [sys.executable, f"scripts/{action['file']}"],
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
