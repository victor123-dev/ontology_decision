# OR-Tools优化Action数学模型详解

> 本文档详细说明7个优化Action的数学模型，包括：
> - 5个OR-Tools求解器Action
> - 2个启发式算法Action
> 
> 涵盖：决策变量定义、目标函数推导、约束条件解释、OR-Tools代码实现要点
> 
> 目标：让你能够完全理解每个模型，并能自行修改和扩展

---

## Action 1: predictMaterialShortage（缺料预测）

**难度**: ⭐ 最简单  
**求解器类型**: LP（线性规划，无需整数约束）  
**预计实现时间**: 1-2天

---

### 1.1 业务场景

**问题**: 未来30天内，哪些物料会在什么时候短缺？短缺多少？

**输入数据**:
- 当前库存: `inventory[material_id]`
- 在途采购: `po_receipts[material_id, date]`
- 生产计划消耗: `production_demand[material_id, date]`
- 安全库存: `safety_stock[material_id]`

**输出**:
```
缺料清单:
  - MAT-DIE-BGA: 4月8日缺口500片，影响工单WO-001, WO-003
  - MAT-EMC-QFN: 4月12日缺口80KG，影响工单WO-002
```

---

### 1.2 数学模型

#### 1.2.1 符号定义

| 符号 | 含义 | 类型 |
|-----|------|------|
| $M$ | 物料集合 | 已知 |
| $T$ | 时间集合（天）| 已知 |
| $I_{m,t}$ | 物料$m$在第$t$天的库存量 | **决策变量** |
| $D_{m,t}$ | 物料$m$在第$t$天的需求量 | 已知（从生产计划计算） |
| $R_{m,t}$ | 物料$m$在第$t$天的到货量 | 已知（在途采购） |
| $S_m$ | 物料$m$的安全库存 | 已知 |
| $X_{m,t}$ | 物料$m$在第$t$天是否缺料 | **决策变量**（0或1） |
| $G_{m,t}$ | 物料$m$在第$t$天的缺料数量 | **决策变量** |

#### 1.2.2 目标函数

这个模型**不需要优化目标**，因为这是一个**预测模型**而非优化模型。

我们只需要模拟库存变化，找出缺料点。

但在OR-Tools中，我们需要一个虚拟目标：

$$\text{Minimize } Z = \sum_{m \in M} \sum_{t \in T} G_{m,t}$$

**解释**: 最小化总缺料量（实际上这个值是由约束决定的，无法优化）

#### 1.2.3 约束条件

**约束1: 库存平衡方程**（核心约束）

$$I_{m,t} = I_{m,t-1} + R_{m,t} - D_{m,t} \quad \forall m \in M, t \in T$$

**通俗解释**:
```
今天库存 = 昨天库存 + 今天到货 - 今天消耗
```

**边界条件**:
$$I_{m,0} = \text{当前库存}$$

---

**约束2: 缺料量计算**

$$G_{m,t} \geq S_m - I_{m,t} \quad \forall m \in M, t \in T$$
$$G_{m,t} \geq 0$$

**通俗解释**:
```
缺料量 = max(0, 安全库存 - 实际库存)
```

如果库存低于安全库存，就产生缺料。

---

**约束3: 缺料标志**

$$X_{m,t} = \begin{cases} 
1 & \text{if } G_{m,t} > 0 \\
0 & \text{otherwise}
\end{cases}$$

**OR-Tools实现技巧**:
```python
# 使用大M法
model.Add(G[m,t] <= M * X[m,t])  # 如果X=0，则G必须=0
model.Add(G[m,t] >= 1 - M * (1 - X[m,t]))  # 如果X=1，则G>=1
```

---

### 1.3 OR-Tools代码实现

```python
from ortools.linear_solver import pywraplp

def predict_material_shortage(self, forecast_days=30):
    """缺料预测 - LP模型"""
    
    # 1. 创建求解器
    solver = pywraplp.Solver.CreateSolver('GLOP')  # GLOP是LP求解器
    
    # 2. 准备数据
    materials = self.ontology.get_all_materials()  # 物料列表
    days = range(1, forecast_days + 1)  # 未来30天
    
    # 3. 创建决策变量
    inventory = {}  # I[m,t]
    shortage = {}   # G[m,t]
    
    for m in materials:
        # 初始库存
        inventory[m, 0] = solver.NumVar(
            0,  # 下界
            100000,  # 上界
            f'inv_{m.material_id}_0'
        )
        inventory[m, 0].ub = m.current_inventory  # 设为当前库存
        
        for t in days:
            # 库存变量
            inventory[m, t] = solver.NumVar(0, 100000, f'inv_{m.material_id}_{t}')
            
            # 缺料量变量
            shortage[m, t] = solver.NumVar(0, 100000, f'short_{m.material_id}_{t}')
    
    # 4. 添加约束
    
    # 约束1: 库存平衡
    for m in materials:
        for t in days:
            demand = self.get_production_demand(m.material_id, t)  # 从生产计划计算
            receipt = self.get_po_receipts(m.material_id, t)  # 在途采购
            
            solver.Add(
                inventory[m, t] == inventory[m, t-1] + receipt - demand
            )
    
    # 约束2: 缺料量计算
    for m in materials:
        for t in days:
            solver.Add(
                shortage[m, t] >= m.safety_stock - inventory[m, t]
            )
            solver.Add(
                shortage[m, t] >= 0
            )
    
    # 5. 目标函数（虚拟）
    objective = solver.Objective()
    for m in materials:
        for t in days:
            objective.SetCoefficient(shortage[m, t], 1)
    objective.SetMinimization()
    
    # 6. 求解
    solver.SetTimeLimit(5000)  # 5秒
    status = solver.Solve()
    
    # 7. 解析结果
    shortages = []
    for m in materials:
        for t in days:
            gap = shortage[m, t].solution_value()
            if gap > 0.1:  # 阈值过滤
                shortages.append({
                    'material_id': m.material_id,
                    'date': t,
                    'shortage_qty': gap,
                    'inventory_level': inventory[m, t].solution_value()
                })
    
    return shortages
```

---

### 1.4 为什么这个最简单？

1. ✅ **无需整数变量** - 纯线性规划，求解极快
2. ✅ **数据简单** - 只需要库存、BOM、生产计划
3. ✅ **无复杂约束** - 只有库存平衡方程
4. ✅ **结果直观** - 直接输出缺料清单

---

## Action 2: calculateCTP（CTP可承诺量计算）

**难度**: ⭐⭐ 中等  
**求解器类型**: MIP（混合整数规划）  
**预计实现时间**: 3-5天

---

### 2.1 业务场景

**问题**: 客户下了一个订单，我们什么时候能交付？

**输入数据**:
- 订单信息: 产品ID、数量、优先级
- 工艺路线: 该产品的工序序列、标准工时
- 产能负荷: 各工作中心未来30天的负荷情况
- 物料可用性: 关键物料库存

**输出**:
```
承诺交期: 2026-04-15
置信度: 85%
瓶颈工序: WC-MOLD（塑封成型）
风险提示: 物料MAT-DIE-BGA库存不足，需提前采购
```

---

### 2.2 数学模型

#### 2.2.1 符号定义

| 符号 | 含义 | 类型 |
|-----|------|------|
| $O$ | 工序集合（该产品的工艺路线）| 已知 |
| $M$ | 可用机台集合 | 已知 |
| $T$ | 时间槽集合（小时）| 已知 |
| $x_{o,m,t}$ | 工序$o$是否在机台$m$、时间$t$开始执行 | **决策变量**（0或1） |
| $S_o$ | 工序$o$的开始时间 | **决策变量** |
| $E_o$ | 工序$o$的结束时间 | **决策变量** |
| $P_o$ | 工序$o$的加工时长 | 已知 |
| $C_m$ | 机台$m$的产能（每小时）| 已知 |
| $Q$ | 订单数量 | 已知 |
| $D$ | 订单要求交期 | 已知 |

#### 2.2.2 目标函数

**最小化交付延迟**:

$$\text{Minimize } Z = \max(0, E_{\text{last}} - D)$$

其中$E_{\text{last}}$是最后一道工序的结束时间。

**OR-Tools线性化技巧**:

引入辅助变量$Delay$:

$$\text{Minimize } Z = Delay$$

约束:
$$Delay \geq E_{\text{last}} - D$$
$$Delay \geq 0$$

---

#### 2.2.3 约束条件

**约束1: 工序开始时间定义**

$$S_o = \sum_{m \in M} \sum_{t \in T} t \cdot x_{o,m,t} \quad \forall o \in O$$

**通俗解释**: 工序的开始时间 = 它被调度到的时间槽

---

**约束2: 工序结束时间**

$$E_o = S_o + P_o \quad \forall o \in O$$

**通俗解释**: 结束时间 = 开始时间 + 加工时长

---

**约束3: 工艺路线顺序**（关键约束）

$$S_{o_{i+1}} \geq E_{o_i} \quad \forall i = 1, 2, ..., |O|-1$$

**通俗解释**: 下一道工序必须等上一道完成才能开始

---

**约束4: 机台产能**

$$\sum_{o \in O} x_{o,m,t} \leq 1 \quad \forall m \in M, t \in T$$

**通俗解释**: 一台机台在同一时间只能执行一道工序

---

**约束5: 工序必须被调度**

$$\sum_{m \in M} \sum_{t \in T} x_{o,m,t} = 1 \quad \forall o \in O$$

**通俗解释**: 每道工序都必须被安排

---

**约束6: 工作日历**（只在有效时间内生产）

$$x_{o,m,t} = 0 \quad \text{如果时间}t\text{是非工作时间}$$

**通俗解释**: 周末和夜班（如果配置）不生产

---

**约束7: 物料可用性**

$$\text{Inventory}(material) \geq \text{Required}(product, quantity)$$

**通俗解释**: 关键物料必须有足够库存，否则无法开始

---

### 2.3 OR-Tools代码实现

```python
from ortools.linear_solver import pywraplp

def calculate_ctp(self, order_id, quantity, planning_horizon_days=30):
    """CTP计算 - MIP模型"""
    
    # 1. 创建求解器
    solver = pywraplp.Solver.CreateSolver('CBC')  # CBC是MIP求解器
    
    # 2. 准备数据
    order = self.ontology.get_object('CustomerOrder', order_id)
    product = self.ontology.get_object('Product', order.product_id)
    route = self.ontology.get_route(product.product_id)
    operations = route.operations  # 工序列表
    
    # 时间槽（按小时，30天 = 720小时）
    time_slots = range(720)
    
    # 可用机台
    machines = self.ontology.get_available_machines()
    
    # 3. 创建决策变量
    
    # x[o, m, t]: 工序o是否在机台m、时间t开始
    x = {}
    for o in operations:
        for m in machines:
            for t in time_slots:
                x[o.step_id, m.machine_id, t] = solver.IntVar(
                    0, 1, f'x_{o.step_id}_{m.machine_id}_{t}'
                )
    
    # S[o]: 工序o的开始时间
    S = {}
    for o in operations:
        S[o.step_id] = solver.NumVar(0, 720, f'S_{o.step_id}')
    
    # E[o]: 工序o的结束时间
    E = {}
    for o in operations:
        E[o.step_id] = solver.NumVar(0, 720, f'E_{o.step_id}')
    
    # Delay: 交付延迟
    Delay = solver.NumVar(0, 720, 'Delay')
    
    # 4. 添加约束
    
    # 约束1: 开始时间定义
    for o in operations:
        solver.Add(
            S[o.step_id] == sum(
                t * x[o.step_id, m.machine_id, t]
                for m in machines
                for t in time_slots
            )
        )
    
    # 约束2: 结束时间
    for o in operations:
        processing_time = o.standard_time_hours
        solver.Add(E[o.step_id] == S[o.step_id] + processing_time)
    
    # 约束3: 工艺路线顺序
    for i in range(len(operations) - 1):
        o_current = operations[i]
        o_next = operations[i + 1]
        solver.Add(S[o_next.step_id] >= E[o_current.step_id])
    
    # 约束4: 机台产能
    for m in machines:
        for t in time_slots:
            solver.Add(
                sum(x[o.step_id, m.machine_id, t] for o in operations) <= 1
            )
    
    # 约束5: 工序必须被调度
    for o in operations:
        solver.Add(
            sum(x[o.step_id, m.machine_id, t] 
                for m in machines 
                for t in time_slots) == 1
        )
    
    # 6. 目标函数：最小化延迟
    required_date = (order.order_date - self.start_date).total_seconds() / 3600
    solver.Add(Delay >= E[operations[-1].step_id] - required_date)
    solver.Add(Delay >= 0)
    
    objective = solver.Objective()
    objective.SetCoefficient(Delay, 1)
    objective.SetMinimization()
    
    # 7. 求解
    solver.SetTimeLimit(30000)  # 30秒
    status = solver.Solve()
    
    # 8. 解析结果
    if status == pywraplp.Solver.OPTIMAL:
        committed_date = self.start_date + timedelta(
            hours=E[operations[-1].step_id].solution_value()
        )
        
        return {
            'committed_date': committed_date,
            'delay_hours': Delay.solution_value(),
            'bottleneck': self.find_bottleneck(E, operations),
            'schedule': self.extract_schedule(x, operations, machines)
        }
    else:
        return {'error': '无可行解'}
```

---

### 2.4 关键难点

1. ⚠️ **变量数量巨大** - 如果工序50道、机台96台、时间720小时，变量数 = 50×96×720 = 3,456,000
   - **解决方案**: 使用列生成或限制时间窗口
   
2. ⚠️ **求解时间可能较长** - MIP问题是NP-Hard
   - **解决方案**: 设置时间限制，返回当前最优解

---

## Action 3: optimizePurchasePlan（采购计划优化）

**难度**: ⭐⭐ 中等  
**求解器类型**: MIP  
**预计实现时间**: 3-5天

---

### 3.1 业务场景

**问题**: 未来30天需要采购哪些物料？向哪个供应商采购？采购多少？

**输入数据**:
- 物料需求（来自生产计划）
- 供应商信息（交期、价格、最小订购量）
- 当前库存
- 预算限制

**输出**:
```
采购计划:
  - 4月5日向SUP-001采购MAT-SUB-BGA 500片，单价2.5元，小计1250元
  - 4月8日向SUP-003采购MAT-DIE-BGA 1000片，单价15元，小计15000元
  总成本: 16250元
```

---

### 3.2 数学模型

#### 3.2.1 符号定义

| 符号 | 含义 | 类型 |
|-----|------|------|
| $M$ | 物料集合 | 已知 |
| $S$ | 供应商集合 | 已知 |
| $T$ | 时间集合 | 已知 |
| $y_{m,s,t}$ | 物料$m$在时间$t$向供应商$s$采购的数量 | **决策变量**（连续） |
| $z_{m,s,t}$ | 是否在时间$t$向供应商$s$采购物料$m$ | **决策变量**（0或1） |
| $I_{m,t}$ | 物料$m$在时间$t$的库存 | **决策变量** |
| $D_{m,t}$ | 物料$m$在时间$t$的需求 | 已知 |
| $P_{m,s}$ | 供应商$s$的物料$m$单价 | 已知 |
| $L_{m,s}$ | 供应商$s$的物料$m$交期（天）| 已知 |
| $MOQ_{m,s}$ | 供应商$s$的物料$m$最小订购量 | 已知 |
| $B$ | 总预算 | 已知 |

#### 3.2.2 目标函数

**最小化总采购成本**:

$$\text{Minimize } Z = \sum_{m \in M} \sum_{s \in S} \sum_{t \in T} P_{m,s} \cdot y_{m,s,t}$$

**通俗解释**: 所有采购订单的总金额最小

---

#### 3.2.3 约束条件

**约束1: 库存平衡**

$$I_{m,t} = I_{m,t-1} + \sum_{s \in S} y_{m,s,t-L_{m,s}} - D_{m,t} \quad \forall m \in M, t \in T$$

**通俗解释**:
```
今天库存 = 昨天库存 + 今天到货（L天前的采购） - 今天消耗
```

注意：$y_{m,s,t-L_{m,s}}$表示$L$天前下的订单今天到货。

---

**约束2: 最小订购量**（关键约束，需要整数变量）

$$y_{m,s,t} \geq MOQ_{m,s} \cdot z_{m,s,t} \quad \forall m, s, t$$
$$y_{m,s,t} \leq 100000 \cdot z_{m,s,t} \quad \forall m, s, t$$

**通俗解释**:
```
如果采购（z=1），则采购量 >= 最小订购量
如果不采购（z=0），则采购量 = 0
```

这就是**固定成本约束**的经典建模方式。

---

**约束3: 非负库存**

$$I_{m,t} \geq 0 \quad \forall m, t$$

**通俗解释**: 库存不能为负（不允许缺货）

如果要允许缺货，可以改为：
$$I_{m,t} \geq -Shortage_{m,t}$$

---

**约束4: 预算限制**

$$\sum_{m \in M} \sum_{s \in S} \sum_{t \in T} P_{m,s} \cdot y_{m,s,t} \leq B$$

**通俗解释**: 总采购金额不超过预算

---

**约束5: 供应商产能**（如果有）

$$\sum_{m \in M} y_{m,s,t} \leq Capacity_{s,t} \quad \forall s, t$$

**通俗解释**: 每个供应商每天能供应的量有限

---

### 3.3 OR-Tools代码实现

```python
def optimize_purchase_plan(self, material_ids, budget_limit=None):
    """采购计划优化 - MIP模型"""
    
    solver = pywraplp.Solver.CreateSolver('CBC')
    
    materials = [self.ontology.get_material(mid) for mid in material_ids]
    suppliers = self.ontology.get_all_suppliers()
    days = range(30)
    
    # 决策变量
    y = {}  # 采购数量
    z = {}  # 是否采购
    
    for m in materials:
        for s in suppliers:
            if self.ontology.can_supply(s.supplier_id, m.material_id):
                for t in days:
                    y[m.material_id, s.supplier_id, t] = solver.NumVar(
                        0, 100000, f'y_{m}_{s}_{t}'
                    )
                    z[m.material_id, s.supplier_id, t] = solver.IntVar(
                        0, 1, f'z_{m}_{s}_{t}'
                    )
                    
                    # 最小订购量约束
                    moq = self.ontology.get_moq(s.supplier_id, m.material_id)
                    solver.Add(y[m.material_id, s.supplier_id, t] >= moq * z[m.material_id, s.supplier_id, t])
                    solver.Add(y[m.material_id, s.supplier_id, t] <= 100000 * z[m.material_id, s.supplier_id, t])
    
    # 库存变量
    I = {}
    for m in materials:
        for t in days:
            I[m.material_id, t] = solver.NumVar(0, 100000, f'I_{m}_{t}')
    
    # 库存平衡约束
    for m in materials:
        for t in days:
            demand = self.get_demand(m.material_id, t)
            receipts = sum(
                y[m.material_id, s.supplier_id, t - lead_time]
                for s in suppliers
                if t >= (lead_time := self.ontology.get_lead_time(s.supplier_id, m.material_id))
            )
            
            if t == 0:
                solver.Add(I[m.material_id, t] == m.current_inventory + receipts - demand)
            else:
                solver.Add(I[m.material_id, t] == I[m.material_id, t-1] + receipts - demand)
    
    # 目标函数：最小化成本
    objective = solver.Objective()
    for m in materials:
        for s in suppliers:
            for t in days:
                price = self.ontology.get_price(s.supplier_id, m.material_id)
                objective.SetCoefficient(y[m.material_id, s.supplier_id, t], price)
    objective.SetMinimization()
    
    # 预算约束
    if budget_limit:
        solver.Add(
            sum(
                self.ontology.get_price(s.supplier_id, m.material_id) * y[m.material_id, s.supplier_id, t]
                for m in materials
                for s in suppliers
                for t in days
            ) <= budget_limit
        )
    
    # 求解
    solver.SetTimeLimit(30000)
    status = solver.Solve()
    
    # 解析结果
    if status == pywraplp.Solver.OPTIMAL:
        purchase_plan = []
        for m in materials:
            for s in suppliers:
                for t in days:
                    qty = y[m.material_id, s.supplier_id, t].solution_value()
                    if qty > 0.1:
                        purchase_plan.append({
                            'material_id': m.material_id,
                            'supplier_id': s.supplier_id,
                            'order_date': t,
                            'quantity': qty,
                            'unit_price': self.ontology.get_price(s.supplier_id, m.material_id)
                        })
        return purchase_plan
```

---

## Action 4: optimizeCapacityAllocation（产能优化分配）

**难度**: ⭐⭐⭐ 较难  
**求解器类型**: MIP  
**预计实现时间**: 5-7天

---

### 4.1 业务场景

**问题**: 有多个工单竞争有限产能，如何分配才能最大化按时交付率？

**输入**: 多个工单、各工单的工艺路线、设备产能、交期  
**输出**: 每个工单的最优排程方案

---

### 4.2 数学模型（简化版）

#### 4.2.1 符号定义

| 符号 | 含义 | 类型 |
|-----|------|------|
| $W$ | 工单集合 | 已知 |
| $O_w$ | 工单$w$的工序集合 | 已知 |
| $M$ | 机台集合 | 已知 |
| $T$ | 时间槽集合 | 已知 |
| $x_{w,o,m,t}$ | 工单$w$的工序$o$是否在机台$m$、时间$t$执行 | **决策变量**（0或1） |
| $C_w$ | 工单$w$是否按时交付 | **决策变量**（0或1） |
| $D_w$ | 工单$w$的交期 | 已知 |
| $Priority_w$ | 工单$w$的优先级权重 | 已知 |

#### 4.2.2 目标函数

**最大化按时交付的工单优先级加权和**:

$$\text{Maximize } Z = \sum_{w \in W} Priority_w \cdot C_w$$

---

#### 4.2.3 约束条件

**约束1: 按时交付定义**

$$E_{w, \text{last}} \leq D_w + M \cdot (1 - C_w) \quad \forall w \in W$$

其中$M$是一个很大的数（如10000）。

**通俗解释**:
```
如果C_w=1（按时），则结束时间 <= 交期
如果C_w=0（延迟），则约束自动满足（因为M很大）
```

**约束2-6**: 与Action 2类似（工艺路线顺序、机台产能等）

---

## Action 5: optimizeDetailedSchedule（详细排程优化）

**难度**: ⭐⭐⭐⭐ 最难  
**求解器类型**: CP-SAT（约束规划）  
**预计实现时间**: 7-14天

---

### 5.1 为什么用CP-SAT而不是MIP？

| 对比项 | MIP | CP-SAT |
|-------|-----|--------|
| 变量类型 | 连续+整数 | 整数+区间 |
| 适合问题 | 资源分配 | 调度问题 |
| 换线约束 | 难建模 | 原生支持 |
| 求解速度 | 慢 | 快10-100倍 |
| 规模 | <1000变量 | <100000变量 |

**CP-SAT的核心优势**: 使用`IntervalVar`（区间变量）直接表示任务时间，无需时间槽离散化。

---

### 5.2 数学模型

#### 5.2.1 符号定义

| 符号 | 含义 | 类型 |
|-----|------|------|
| $Task_{w,o}$ | 工单$w$的工序$o$的时间区间 | **决策变量**（IntervalVar） |
| $Start_{w,o}$ | 开始时间 | 由IntervalVar导出 |
| $End_{w,o}$ | 结束时间 | 由IntervalVar导出 |
| $Duration_{w,o}$ | 加工时长 | 已知 |

#### 5.2.2 CP-SAT建模

```python
from ortools.sat.python import cp_model

model = cp_model.CpModel()

# 创建区间变量
tasks = {}
for wo in work_orders:
    for op in wo.operations:
        tasks[wo.wo_id, op.step_id] = model.NewIntervalVar(
            start=model.NewIntVar(0, horizon, f'start_{wo}_{op}'),
            size=op.duration,  # 固定时长
            end=model.NewIntVar(0, horizon, f'end_{wo}_{op}'),
            name=f'task_{wo}_{op}'
        )

# 约束1: 工艺路线顺序
for i in range(len(operations) - 1):
    model.Add(tasks[wo, operations[i+1]].StartExpr() >= 
              tasks[wo, operations[i]].EndExpr())

# 约束2: 机台不重叠（使用NoOverlap约束）
for machine in machines:
    machine_tasks = [tasks[wo, op] for wo, op in assignments if op.machine == machine]
    model.AddNoOverlap(machine_tasks)

# 目标: 最小化makespan
makespan = model.NewIntVar(0, horizon, 'makespan')
for wo in work_orders:
    last_op = wo.operations[-1]
    model.Add(makespan >= tasks[wo.wo_id, last_op.step_id].EndExpr())

model.Minimize(makespan)
```

---

### 5.3 关键难点

1. ⚠️ **换线矩阵建模复杂**
2. ⚠️ **需要考虑人员、模具等多资源**
3. ⚠️ **动态重排程需要增量求解**

---

## Action 5: optimizeCapacityAllocationHeuristic（产能优化分配-启发式）

**难度**: ⭐ 最简单（无需数学建模）  
**算法类型**: 启发式规则（EDD/SPT/CR）  
**预计实现时间**: 1天

---

### 5.1 业务场景

与Action 4相同，但针对**大规模工单场景**（500+工单），MIP求解器无法在合理时间内完成。

---

### 5.2 算法设计

#### 5.2.1 核心思想

不使用数学优化，而是使用**贪婪启发式规则**快速排程。

#### 5.2.2 调度规则

| 规则 | 全称 | 排序依据 | 适用场景 |
|-----|------|---------|---------|
| EDD | Earliest Due Date | 交期越早越先排 | 交期敏感 |
| SPT | Shortest Processing Time | 加工时间越短越先排 | 效率优先 |
| CR | Critical Ratio | CR = (交期-当前时间)/剩余加工时间，CR越小越先排 | 均衡考虑 |

#### 5.2.3 算法流程

```
输入: 工单列表
输出: 排程结果

1. 计算每个工单的优先级分数
   score = f(交期, 加工时间, 客户等级, 订单优先级)

2. 按分数排序（分数小的优先）
   sorted_work_orders.sort(key=score)

3. 贪婪分配机台
   for each work_order in sorted_work_orders:
     for each operation in work_order:
       best_machine = find_earliest_available_machine(operation)
       assign(operation, best_machine)

4. 检查按时交付率
   on_time_rate = count(on_time) / total_work_orders
```

#### 5.2.4 优先级计算

```python
order_priority_weight = {1: 10, 3: 5, 5: 1}.get(priority, 5)
customer_weight = {"VIP": 2.0, "重要": 1.5, "普通": 1.0}.get(customer_level, 1.0)
total_weight = customer_weight * order_priority_weight
```

---

### 5.3 代码实现要点

```python
def execute_optimize_capacity_allocation_heuristic(parameters):
    # 1. 获取数据和客户信息
    work_orders = get_work_orders()
    customer_weights = calculate_customer_weights(work_orders)
    
    # 2. 计算调度分数
    scored_work_orders = []
    for wo in work_orders:
        score = calculate_score(wo, scheduling_rule)
        scored_work_orders.append({
            "wo": wo,
            "score": score,
            "priority_weight": calculate_weight(wo)
        })
    
    # 3. 排序
    scored_work_orders.sort(key=lambda x: x["score"])
    
    # 4. 贪婪分配
    machine_available_time = {m.machine_id: 0 for m in machines}
    for scored_wo in scored_work_orders:
        for op in scored_wo["ops"]:
            best_machine = select_best_machine(op, machine_available_time)
            assign_operation(op, best_machine, machine_available_time)
    
    return build_result()
```

---

### 5.4 性能对比

| 对比项 | MIP求解器 | 启发式算法 |
|-------|----------|----------|
| 求解时间 | 1-2分钟 | < 0.1秒 |
| 最大工单数 | 50 | 500+ |
| 规划天数 | ≤14天 | 无限制 |
| 解质量 | 最优解 | 近似解（通常90%+） |
| 实现复杂度 | 高 | 低 |

---

## Action 6: optimizeDetailedScheduleHeuristic（详细排程优化-启发式）

**难度**: ⭐⭐ 简单  
**算法类型**: 贪婪算法  
**预计实现时间**: 1-2天

---

### 6.1 业务场景

与Action 6（CP-SAT详细排程）相同，但针对**大规模场景**（500+工单），CP-SAT无法在合理时间内完成。

---

### 6.2 算法设计

#### 6.2.1 核心思想

使用**纯贪婪算法**快速构造排程，无需数学建模。

#### 6.2.2 算法策略

1. **按工单优先级排序**（高优先级先排）
2. **同一工单内按工序顺序排**（工艺路线顺序）
3. **每道工序选择最早可用的合适机台**

#### 6.2.3 算法流程

```
输入: 工单列表、机台列表
输出: 详细排程

1. 构造任务列表
   tasks = [
     {wo_id, op_id, step_id, seq, priority, duration, valid_machine_ids}
     for each work_order
     for each operation
   ]

2. 排序
   sorted_tasks.sort(key=lambda t: (t["priority"], t["wo_id"], t["seq"]))

3. 贪婪排程
   for task in sorted_tasks:
     earliest_start = get_earliest_start(task)  # 考虑工序顺序
     best_machine = find_earliest_machine(task, earliest_start)
     assign(task, best_machine)

4. 计算总工期
   makespan = max(end_time for all tasks)
```

---

### 6.3 代码实现要点

```python
def _greedy_schedule(tasks, machines_dict):
    # 1. 排序
    sorted_tasks = sorted(tasks, key=lambda t: (t["priority"], t["wo_id"], t["seq"]))
    
    # 2. 初始化机台可用时间
    machine_available_time = {m: 0 for m in machines_dict.keys()}
    wo_op_end_time = {}  # 记录每个工序的结束时间
    
    schedule = []
    
    # 3. 贪婪分配
    for task in sorted_tasks:
        # 计算最早开始时间
        earliest_start = wo_op_end_time.get((task["wo_id"], task["seq"] - 1), 0)
        
        # 找到最佳机台
        best_machine_id = None
        best_start = float("inf")
        
        for mid in task["valid_machine_ids"]:
            machine_start = max(earliest_start, machine_available_time.get(mid, 0))
            if machine_start < best_start:
                best_start = machine_start
                best_machine_id = mid
        
        # 分配
        if best_machine_id:
            task["machine_id"] = best_machine_id
            task["start_time"] = best_start
            task["end_time"] = best_start + task["duration"]
            
            machine_available_time[best_machine_id] = task["end_time"]
            wo_op_end_time[(task["wo_id"], task["seq"])] = task["end_time"]
            
            schedule.append(task)
    
    return schedule
```

---

### 6.4 性能对比

| 对比项 | CP-SAT | 启发式算法 |
|-------|--------|----------|
| 求解时间 | 5分钟 | < 1秒 |
| 最大工单数 | 20 | 500+ |
| 规划天数 | ≤14天 | 无限制 |
| 换线约束 | 支持（简化版） | 不支持 |
| 解质量 | 最优解 | 近似解 |
| 适用场景 | 小规模精确排程 | 大规模快速排程 |

---

## 总结对比

| Action | 类型 | 变量数 | 约束数 | 求解时间 | 实现难度 | 适用场景 |
|-------|------|-------|-------|---------|---------|---------|
| predictMaterialShortage | LP | ~1000 | ~2000 | <5秒 | ⭐ | 物料短缺预测 |
| calculateCTP | MIP | ~10000 | ~20000 | 30秒 | ⭐⭐ | 订单交期承诺 |
| optimizePurchasePlan | MIP | ~5000 | ~10000 | 30秒 | ⭐⭐ | 采购计划优化 |
| optimizeCapacityAllocation | MIP | ~50000 | ~100000 | 2分钟 | ⭐⭐⭐ | 小规模产能分配(≤50工单) |
| optimizeCapacityAllocationHeuristic | 启发式 | - | - | <0.1秒 | ⭐ | 大规模产能分配(500+工单) |
| optimizeDetailedSchedule | CP-SAT | ~20000 | ~50000 | 5分钟 | ⭐⭐⭐⭐ | 小规模精确排程(≤20工单) |
| optimizeDetailedScheduleHeuristic | 启发式 | - | - | <1秒 | ⭐⭐ | 大规模快速排程(500+工单) |

---

**文档版本**: v2.0  
**创建日期**: 2026-04-28  
**更新日期**: 2026-05-03  
**状态**: 已完成所有7个Action的数学模型和算法说明
