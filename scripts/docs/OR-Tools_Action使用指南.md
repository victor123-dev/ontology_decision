# OR-Tools优化Action使用指南

> 本文档说明如何导入和使用9个优化Action（5个OR-Tools求解器 + 2个启发式算法 + 1个CTP + 1个缺料预测）

---

## 一、Action概览

| # | Action名称 | 功能 | 求解器/算法 | 难度 | 脚本文件 |
|---|-----------|------|------------|------|---------|
| 1 | 缺料预测 | 预测未来30天物料短缺 | LP (GLOP) | ⭐ | `import_action_predict_material_shortage.py` |
| 2 | CTP可承诺量计算 | 计算订单可承诺交期 | MIP (CBC) | ⭐⭐ | `import_action_calculate_ctp.py` |
| 3 | 采购计划优化 | 优化采购计划降低成本 | MIP (CBC) | ⭐⭐ | `import_action_optimize_purchase_plan.py` |
| 4 | 产能优化分配 | 多工单产能最优分配 | MIP (CBC) | ⭐⭐⭐ | `import_action_optimize_capacity_allocation.py` |
| 5 | 产能优化分配（启发式） | 大规模快速产能分配 | EDD/SPT/CR规则 | ⭐ | `import_action_heuristic_capacity_allocation.py` |
| 6 | 详细排程优化 | CP-SAT详细排程 | CP-SAT | ⭐⭐⭐⭐ | `import_action_optimize_detailed_schedule.py` |
| 7 | 详细排程优化（启发式） | 大规模快速排程 | 贪婪算法 | ⭐⭐ | `import_action_heuristic_detailed_schedule.py` |

---

## 二、快速开始

### 2.1 批量导入所有Action

```bash
# 在项目根目录执行
python scripts/import_all_or_tools_actions.py
```

### 2.2 单独导入某个Action

```bash
# OR-Tools求解器Action
python scripts/import_action_predict_material_shortage.py           # 缺料预测
python scripts/import_action_calculate_ctp.py                       # CTP计算
python scripts/import_action_optimize_purchase_plan.py              # 采购计划优化
python scripts/import_action_optimize_capacity_allocation.py        # 产能优化分配（MIP）
python scripts/import_action_optimize_detailed_schedule.py          # 详细排程优化（CP-SAT）

# 启发式算法Action（无需求解器，超快速）
python scripts/import_action_heuristic_capacity_allocation.py       # 产能优化分配（启发式）
python scripts/import_action_heuristic_detailed_schedule.py         # 详细排程优化（启发式）
```

---

## 三、Action详细说明

### 3.1 缺料预测 (predict_material_shortage)

**数学模型**:
- **决策变量**: `I[m,t]`库存量, `G[m,t]`缺料量
- **目标函数**: Minimize ΣG[m,t] (虚拟目标)
- **约束条件**:
  1. 库存平衡: `I[m,t] = I[m,t-1] + R[m,t] - D[m,t]`
  2. 缺料计算: `G[m,t] >= safety_stock - I[m,t]`
  3. 非负约束: `G[m,t] >= 0`

**输入参数**:
```json
{
  "forecast_days": 30,
  "material_ids": ["MAT-DIE-BGA", "MAT-EMC-QFN"],
  "safety_stock_threshold": 100
}
```

**输出示例**:
```json
{
  "success": true,
  "message": "缺料预测完成，发现 3 个缺料点",
  "result": {
    "forecast_days": 30,
    "total_shortages": 3,
    "shortage_details": [
      {
        "material_id": "MAT-DIE-BGA",
        "material_name": "Die芯片-BGA",
        "date_offset_days": 5,
        "shortage_qty": 500,
        "inventory_level": 50,
        "safety_stock": 100,
        "affected_work_orders": [
          {"work_order_id": "WO-001", "product_id": "BGA-CPU", "status": "生产中"}
        ]
      }
    ]
  }
}
```

---

### 3.2 CTP可承诺量计算 (calculate_ctp)

**数学模型**:
- **决策变量**: `x[o,m,t]`工序分配, `S[o]`开始时间, `E[o]`结束时间, `Delay`延迟
- **目标函数**: Minimize Delay
- **约束条件**:
  1. 开始时间定义: `S[o] = Σ(t * x[o,m,t])`
  2. 结束时间: `E[o] = S[o] + P[o]`
  3. 工艺路线顺序: `S[o(i+1)] >= E[o(i)]`
  4. 机台产能: `Σx[o,m,t] <= 1`
  5. 工序必须调度: `Σx[o,m,t] = 1`
  6. 工作日历约束
  7. 物料可用性检查

**输入参数**:
```json
{
  "order_id": "CO-20260428-001",
  "quantity": 100,
  "planning_horizon_days": 30
}
```

**输出示例**:
```json
{
  "success": true,
  "message": "CTP计算完成，承诺交期: 2026-05-15",
  "result": {
    "order_id": "CO-20260428-001",
    "product_id": "BGA-CPU",
    "quantity": 100,
    "committed_date": "2026-05-15T18:00:00",
    "delay_hours": 12.5,
    "confidence": 0.85,
    "bottleneck_step": {
      "step_id": "STEP-BGA-CPU-060",
      "step_name": "塑封成型",
      "duration_hours": 8.5
    },
    "schedule": [...],
    "material_risks": []
  }
}
```

---

### 3.3 采购计划优化 (optimize_purchase_plan)

**数学模型**:
- **决策变量**: `y[m,s,t]`采购数量, `z[m,s,t]`是否采购, `I[m,t]`库存
- **目标函数**: Minimize Σ(P[m,s] * y[m,s,t])
- **约束条件**:
  1. 库存平衡: `I[m,t] = I[m,t-1] + Σy[m,s,t-L[m,s]] - D[m,t]`
  2. 最小订购量: `y[m,s,t] >= MOQ[m,s] * z[m,s,t]`
  3. 非负库存: `I[m,t] >= 0`
  4. 预算限制: `Σ(P[m,s] * y[m,s,t]) <= B`

**输入参数**:
```json
{
  "material_ids": ["MAT-DIE-BGA", "MAT-EMC-QFN"],
  "planning_days": 30,
  "budget_limit": 50000
}
```

**输出示例**:
```json
{
  "success": true,
  "message": "采购计划优化完成，总成本: ¥45230.50",
  "result": {
    "planning_days": 30,
    "total_orders": 8,
    "total_cost": 45230.50,
    "budget_limit": 50000,
    "budget_used_percent": 90.46,
    "purchase_plan": [
      {
        "material_id": "MAT-DIE-BGA",
        "material_name": "Die芯片-BGA",
        "supplier_id": "SUP-001",
        "supplier_name": "芯片供应商A",
        "order_date": "2026-04-30",
        "delivery_date": "2026-05-05",
        "quantity": 1000,
        "unit_price": 15.0,
        "total_cost": 15000.0,
        "lead_time_days": 5
      }
    ]
  }
}
```

---

### 3.4 产能优化分配 (optimize_capacity_allocation)

**数学模型**:
- **决策变量**: `x[w,o,m,t]`工单工序分配, `C[w]`是否按时交付
- **目标函数**: Maximize Σ(Priority[w] * C[w])
- **约束条件**:
  1. 按时交付: `E[w,last] <= D[w] + M*(1-C[w])`
  2. 工艺路线顺序: `S[o(i+1)] >= E[o(i)]`
  3. 机台产能: `Σx[w,o,m,t] <= 1`
  4. 工序必须调度: `Σx[w,o,m,t] = 1`

**输入参数**:
```json
{
  "work_order_ids": ["WO-001", "WO-002", "WO-003"],
  "planning_horizon_days": 30
}
```

**输出示例**:
```json
{
  "success": true,
  "message": "产能优化完成，按时交付率: 85.0%",
  "result": {
    "total_work_orders": 10,
    "on_time_count": 8,
    "on_time_rate": 85.0,
    "customer_weight_applied": true,
    "schedule": [...]
  }
}
```

---

### 3.5 产能优化分配（启发式）(optimize_capacity_allocation_heuristic)

**算法**:
- **调度规则**: EDD(最早交期优先) / SPT(最短加工时间) / CR(关键比率)
- **算法流程**:
  1. 计算每个工单的优先级分数
  2. 按分数排序
  3. 贪婪分配机台
  4. 检查按时交付情况

**输入参数**:
```json
{
  "work_order_ids": ["WO-001", "WO-002", "WO-003"],
  "planning_horizon_days": 30,
  "scheduling_rule": "EDD"
}
```

**输出示例**:
```json
{
  "success": true,
  "message": "产能优化完成，按时交付率: 90.0%，调度规则: EDD",
  "result": {
    "total_work_orders": 10,
    "on_time_count": 9,
    "on_time_rate": 90.0,
    "scheduling_rule": "EDD",
    "customer_weight_applied": true,
    "work_order_priorities": [
      {
        "work_order_id": "WO-001",
        "order_priority": 1,
        "customer_weight": 2.0,
        "total_weight": 20.0,
        "due_hours": 48.0,
        "score": 48.0
      }
    ],
    "schedule": [
      {
        "work_order_id": "WO-001",
        "operation_id": "WO-OP-001",
        "step_id": "STEP-010",
        "sequence_no": 1,
        "machine_id": "MACHINE-01",
        "start_time": "2026-05-03T08:00:00",
        "end_time": "2026-05-03T10:30:00",
        "start_minutes": 0,
        "end_minutes": 150
      }
    ]
  }
}
```

**性能对比**:
| 对比项 | MIP求解器 | 启发式算法 |
|-------|----------|----------|
| 求解时间 | 1-2分钟 | < 0.1秒 |
| 最大工单数 | 50 | 500+ |
| 规划天数 | ≤14天 | 无限制 |
| 解质量 | 最优解 | 近似解 |
| 适用场景 | 小规模精确优化 | 大规模快速排程 |

---

### 3.6 详细排程优化 (optimize_detailed_schedule)

**数学模型** (CP-SAT):
- **决策变量**: `Task[w,o]`区间变量(Start, End, Duration)
- **目标函数**: Minimize Makespan
- **约束条件**:
  1. 工艺路线顺序: `Start[o(i+1)] >= End[o(i)]`
  2. 机台不重叠: `NoOverlap(Tasks_on_same_machine)`
  3. 换线时间: `SetupTime(prev_product, curr_product)`
  4. 工作日历: 只在有效时间内排程

**为什么使用CP-SAT？**
| 对比项 | MIP | CP-SAT |
|-------|-----|--------|
| 变量类型 | 连续+整数 | 整数+区间 |
| 适合问题 | 资源分配 | 调度问题 |
| 换线约束 | 难建模 | 原生支持 |
| 求解速度 | 慢 | 快10-100倍 |

**输入参数**:
```json
{
  "work_order_ids": ["WO-001", "WO-002"],
  "planning_horizon_days": 7,
  "consider_setup": true
}
```

**输出示例**:
```json
{
  "success": true,
  "message": "详细排程完成，总工期: 156.5小时",
  "result": {
    "makespan_hours": 156.5,
    "makespan_days": 6.52,
    "total_tasks": 85,
    "schedule": [
      {
        "work_order_id": "WO-001",
        "operation_id": "WO-OP-001",
        "step_id": "STEP-BGA-CPU-010",
        "machine_id": "WC-MOLD-01",
        "start_time": "2026-04-28T08:00:00",
        "end_time": "2026-04-28T10:30:00",
        "duration_minutes": 150
      }
    ]
  }
}
```

---

### 3.7 详细排程优化（启发式）(optimize_detailed_schedule_heuristic)

**算法**:
- **核心算法**: 贪婪排程
- **算法流程**:
  1. 按工单优先级排序（高优先级先排）
  2. 同一工单内按工序顺序排
  3. 每道工序选择最早可用的合适机台

**输入参数**:
```json
{
  "work_order_ids": ["WO-001", "WO-002", "WO-003"],
  "planning_horizon_days": 30,
  "consider_setup": false
}
```

**输出示例**:
```json
{
  "success": true,
  "message": "启发式排程完成，总工期: 120.5小时",
  "result": {
    "makespan_hours": 120.5,
    "makespan_days": 5.02,
    "total_tasks": 45,
    "algorithm": "Greedy Scheduling",
    "schedule": [
      {
        "work_order_id": "WO-001",
        "operation_id": "WO-OP-001",
        "step_id": "STEP-010",
        "sequence_no": 0,
        "machine_id": "MACHINE-01",
        "start_time": "2026-05-03T08:00:00",
        "end_time": "2026-05-03T10:30:00",
        "duration_minutes": 150
      }
    ]
  }
}
```

**性能对比**:
| 对比项 | CP-SAT | 启发式算法 |
|-------|--------|----------|
| 求解时间 | 5分钟 | < 1秒 |
| 最大工单数 | 20 | 500+ |
| 规划天数 | ≤14天 | 无限制 |
| 换线约束 | 支持（简化版） | 不支持 |
| 解质量 | 最优解 | 近似解 |
| 适用场景 | 小规模精确排程 | 大规模快速排程 |

---

## 四、数据获取方式

所有Action都使用**ontologySDK**获取数据，示例：

```python
from my_ontology_sdk import OntologyClient

# 初始化客户端
client = OntologyClient("http://localhost:8080", api_key="your-api-key")

# 查询物料
materials = client.models.Material.find()
material = client.models.Material.get("MAT-DIE-BGA")

# 查询库存
inventory = client.models.Inventory.find(material_id="MAT-DIE-BGA")

# 查询工单
work_orders = client.models.WorkOrder.find(status="已计划")

# 查询工艺路线
routes = client.models.ProcessRoute.find(product_id="BGA-CPU", is_active=True)

# 查询BOM
boms = client.models.Bom.find(product_id="BGA-CPU")

# 查询供应商物料关系
supplier_materials = client.models.SupplierMaterial.find(
    supplier_id="SUP-001",
    material_id="MAT-DIE-BGA"
)
```

---

## 五、依赖安装

确保已安装OR-Tools：

```bash
pip install ortools
```

---

## 六、注意事项

1. **求解时间限制**: 所有Action都设置了求解时间限制，超时返回当前最优解
2. **数据质量**: 优化结果依赖于准确的主数据（工艺路线、机台能力、换线矩阵等）
3. **参数调优**: 根据实际业务场景调整参数（如规划天数、预算限制等）
4. **性能优化**: 
   - 缺料预测(LP): 最快，<5秒
   - CTP/采购优化(MIP): 30秒左右
   - 产能分配(MIP): 1-2分钟，规划天数≤14天
   - 详细排程(CP-SAT): 5分钟，规划天数≤7天
   - 启发式算法: <1秒，适合大规模场景

---

## 七、故障排查

### 问题1: 导入失败
```
❌ 导入失败: 400
```
**解决**: 检查API URL是否正确，后端服务是否运行

### 问题2: 求解失败
```
{"success": false, "error": "无可行解"}
```
**解决**: 
- 检查约束是否过严
- 增加planning_horizon_days
- 检查物料可用性

### 问题3: 求解超时
```
求解器返回非最优解
```
**解决**:
- 增加时间限制（修改solver.SetTimeLimit）
- 减少问题规模（减少工单数量或规划天数）

---

**文档版本**: v1.0  
**创建日期**: 2026-04-28  
**状态**: 已完成
