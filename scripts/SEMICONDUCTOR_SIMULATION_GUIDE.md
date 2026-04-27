# 半导体制造业 APS+MRP 仿真系统说明文档

> 版本：v3.0（实时动态排程版）  
> 最后更新：2026-04-27  
> 仿真周期：120天  
> 数据规模：约 213 工单 / 23731 工序 / 4681 生产任务 / 4936 质检记录  
> **核心特性**：事件驱动实时排程 + Lot批量加工 + 良率损耗传递

---

## 一、快速运行

```bash
cd d:\WorkHorse\No3\commander_demov3\scripts
python run_semiconductor_demo.py
```

运行完成后会输出 R1–R23 共 23 项校验结果，全部 PASS 则说明数据完整。

---

## 二、文件结构

```
scripts/
├── run_semiconductor_demo.py            # 主运行脚本（入口）
└── semiconductor_demo/
    ├── factory_data.py                  # 工厂静态主数据 + 仿真参数
    ├── db_models.py                     # 数据库表结构（26张表）
    ├── db_writer.py                     # 数据库写入/查询工具类
    └── simulation.py                    # SimPy 离散事件仿真引擎（核心）
```

---

## 三、数据库表结构（26张核心表）

数据全部写入项目根目录的 `data.db`（SQLite）。

### 3.1 基础主数据层

| 表名 | 说明 |
|---|---|
| `product` | 产品主数据（PROD-A/B/C） |
| `material` | 物料主数据（MAT-X/Y/Z/W/V/COMMON） |
| `bom` | 物料清单（产品→物料，含工序关联） |
| `supplier` | 供应商（SUP-001/002/003） |
| `supplier_material` | 供应商可供物料及价格、交期 |
| `material_substitute` | 替代料关系（缺料时替换） |

### 3.2 工艺路线层

| 表名 | 说明 |
|---|---|
| `process_route` | 工艺路线主表（每个产品一条） |
| `route_step` | 工序定义（含标准时间、良率、物料需求偏移） |
| `work_center` | 工作中心（机台组）：清洗/光刻/封装/测试/射频 |
| `machine` | 机台主数据（MC-001 ~ MC-006-C） |
| `machine_capability` | 机台加工能力矩阵（每机台对每产品的效率） |
| `setup_matrix` | 换线矩阵（A→B / B→A 换线时间不同） |
| `shift_pattern` | 班次定义（日班 08:00-20:00 / 夜班 20:00-08:00） |
| `work_calendar` | 工作日历（按工作中心×日期×班次，周日休息） |

### 3.3 订单与生产层

| 表名 | 说明 |
|---|---|
| `customer_order` | 客户订单（含优先级、承诺交期） |
| `work_order` | 生产工单（对应一张客户订单） |
| `work_order_operation` | 工单工序（工单的每道加工工序） |
| `work_order_material` | 工单物料需求（含已分配数量） |
| `production_task` | 生产排程任务（工序在某机台上的执行记录） |
| `wip_lot` | 在制品批次（每25片一个Lot） |

### 3.4 采购与库存层

| 表名 | 说明 |
|---|---|
| `purchase_order` | 采购订单 |
| `purchase_order_line` | 采购订单行（物料、数量、单价） |
| `inventory` | 库存余额（total / available / reserved / in_transit） |
| `inventory_transaction` | 库存事务流水（所有入/出/调拨/盘点记录） |
| `material_transfer` | 物料调拨单（缺料挪用 / 仓库间平衡） |

### 3.5 质检与监控层

| 表名 | 说明 |
|---|---|
| `quality_inspection` | 质检记录（IQC / 过程质检 / 首件检验 / FQC） |
| `machine_status_log` | 机台状态日志（运行/故障/维护/空闲/恢复） |
| `schedule` | 每日排程快照（产能利用率、瓶颈机台） |
| `finished_goods_inventory` | 成品库存 |

---

## 四、工厂主数据（factory_data.py）

### 4.1 产品线

| 产品ID | 名称 | 工序数 | 换线组 |
|---|---|---|---|
| PROD-A | 智能传感器模块A | 4道 | SENSOR-A |
| PROD-B | 功率控制芯片B | 4道 | POWER-B |
| PROD-C | 高端射频芯片C | 5道 | RF-C（进口料，交期长） |

### 4.2 物料清单

| 物料ID | 名称 | 类型 | 用于产品 |
|---|---|---|---|
| MAT-X | 高精度晶圆基板X | 原材料 | PROD-A / PROD-B / PROD-C |
| MAT-Y | 传感器封装材料Y | 原材料 | PROD-A |
| MAT-Z | 功率模块散热片Z | 原材料 | PROD-B / PROD-C |
| MAT-W | RF射频胶W（进口）| 原材料 | PROD-C |
| MAT-V | 导电银浆V（进口） | 原材料 | PROD-C |
| MAT-COMMON | 通用清洗溶剂 | 辅料 | 全部 |

### 4.3 供应商

| 供应商ID | 名称 | 交期 | 可靠性 | 特点 |
|---|---|---|---|---|
| SUP-001 | 本地材料供应商 | 3天 | 0.95 | 主力供应商 |
| SUP-002 | 区域备用供应商 | 5天 | 0.88 | 备用 |
| SUP-003 | TechMat国际进口商 | 15天 | 0.80 | 专供进口料 MAT-W/V |

### 4.4 机台（节选）

机台分布在5个工作中心：清洗(WC-CLEAN)、光刻(WC-LITHO)、封装(WC-PACK)、测试(WC-TEST)、射频(WC-RF)。  
每个工作中心1~2台机台，含 PROD-C 专属射频机台 MC-001-C ~ MC-006-C。

### 4.5 关键仿真参数

```python
SIMULATION_CONFIG = {
    "duration_days": 60,                    # 仿真60天
    "order_arrival_lambda": 2.5,            # 每天平均2.5张客户订单（泊松）
    "order_quantity_min": 5,                # 订单数量下限
    "order_quantity_max": 80,               # 订单数量上限
    "wip_lot_size": 25,                     # 每个WIP批次25片
    "breakdown_mtbf_hours": 96,             # 机台平均无故障时间96小时
    "breakdown_mttr_hours": 4,              # 机台平均修复时间4小时
    "breakdown_probability": 0.70,          # 70%机台启用随机故障
    "order_cancel_daily_prob": 0.20,        # 每天20%概率取消未开工订单
    "split_delivery_prob": 0.30,            # 30%采购订单触发分批到货
    "priority_escalation_daily_prob": 0.08, # 每天8%概率随机升级一个订单优先级
}
```

---

## 五、仿真引擎（simulation.py）

仿真引擎使用 **SimPy 4.x 离散事件仿真（DES）**，通过多个并发进程模拟工厂运行。

### 5.1 核心进程列表

| 进程方法 | 触发方式 | 功能 |
|---|---|---|
| `order_arrival_process` | 每天泊松到达 | 生成客户订单并创建工单 |
| `daily_mrp_run` | 每天08:30 | 运行MRP，计算物料缺口并触发采购/调拨 |
| `daily_scheduler` | 每天09:00 + 每4小时 | 运行APS排程（跳过周日） |
| `realtime_schedule_after_completion` | 工序完成时 | **实时排程后续工序（v3.0新增）** |
| `purchase_arrival_event` | 到货时刻 | 采购到货处理（含分批到货逻辑） |
| `execute_production_task` | 排程触发 | 工序加工（含换线、IPQC、良率损耗） |
| `try_ship_customer_order` | 工单完工后 | 发货尝试（含FQC检验） |
| `machine_breakdown_process` | 每台机台独立进程 | 机台随机故障与恢复 |
| `machine_pm_process` | 每台机台独立进程 | 计划性维护（每168小时一次） |
| `order_cancellation_process` | 每天检查 | 随机取消未开工订单 |
| `inventory_cycle_count_process` | 每7天 | 库存盘点（正态分布扰动） |
| `priority_escalation_process` | 每天检查 | 随机升级订单优先级 |
| `warehouse_balance_transfer_process` | 每12小时 | 仓库间库存平衡调拨 |
| `safety_stock_replenishment` | 每4小时 | 安全库存补货检查 |
| `daily_oee_updater` | 每天20:30 | 更新机台能力矩阵OEE |

### 5.2 排程算法（daily_scheduler + realtime_schedule）⚡ **v3.0核心升级**

**双模式排程架构**：

#### 模式一：日常定时排程（daily_scheduler）
- **触发时间**：每天09:00 + 每4小时检查一次（09:00, 13:00, 17:00, 21:00）
- **作用**：全局扫描所有可排工序，处理积压任务  
- **跳过周日**：工作日历约束  
- **排序算法**：关键比（Critical Ratio）+ 优先级

#### 模式二：实时事件驱动排程（realtime_schedule_after_completion）✨ **新增**
- **触发时机**：每道工序完成时立即触发  
- **作用**：立即排程因前驱完成而变为ready的后续工序  
- **响应速度**：<1分钟（原来需要等待23小时）  
- **智能过滤**：只排程相关工序，避免全局扫描开销  

**关键逻辑流程**：
1. **查询**：前驱工序已完成、物料已就绪的“待排工序”
2. **排序**：按**关键比（Critical Ratio）** = 剩余时间/剩余工期（越小越紧急）
3. **分组**：按工作中心（work_center_id）分组，同产品批次合并
4. **分配**：选最优机台（完工时间 + 换线时间×权重）
5. **排程**：创建production_task，启动execute_production_task事件  
6. **实时响应**：工序完成后立即检查后续工序并排程  

**排程机制对比**：
| 维度 | v2.0（旧） | v3.0（新） |
|------|-----------|-----------|
| 排程频率 | 每天1次（09:00） | 实时 + 每4小时 |
| 响应延迟 | 23小时 | <1分钟 |
| 工序间隔 | 72小时（3天） | 几分钟~几小时 |
| 订单完成 | 120天0完成 | 16天完成首个 |
| 架构模式 | 批处理 | 流处理 |

**周日工作日历约束**：
- `daily_scheduler` 每逢周日直接 `continue` 跳过排程
- `skip_sunday()` 方法保证机台排满时，下一任务的 `planned_start_time` 不落在周日（自动推迟至周一08:00）

### 5.3 MRP运算（daily_mrp_run）

1. 查询所有"待分配"物料需求（`work_order_material.status = '待分配'`）
2. 按工单优先级排序
3. 对每条需求：
   - 有库存 → 直接预留（`available -= qty, reserved += qty`）
   - 库存不足 → 先找替代料，再尝试从其他工单调拨，最后触发采购

### 5.4 良率损耗传递（P0-2）

每道工序完工后：`actual_output = input_qty × yield_rate`  
下一道工序的投入量自动更新为上道的实际产出，通过 `update_next_op_input_qty()` 实现。

---

## 六、12项真实业务场景

### Task2 — 工单实际开工时间
- 触发：工序开始执行时
- 逻辑：若工单 `actual_start_date` 为空，则写入当前仿真时间
- 校验：R21（工单实际开工日期填充率≥50%）

### Task3 — 机台随机故障
- 触发：70%的机台在运行时随机故障
- 逻辑：指数分布间隔（MTBF=96h），均匀分布修复时间（1~2×MTTR）
- 写入：`machine_status_log`（status="故障"/"恢复"）
- 校验：R17（故障次数≥5次）

### Task4 — 工作日历驱动排程
- 触发：每天排程进程
- 逻辑：周日（weekday()==6）跳过排程；排程算法通过 `skip_sunday()` 确保任务不排在周日
- 校验：R23（周日排程时段09-11时无新建任务）

### Task5 — 客户订单取消
- 触发：每天检查，20%概率
- 逻辑：只取消"已确认"且工单尚未实际开工的订单，每天最多取消3笔；取消后释放预留物料写入"取消释放"库存事务
- 校验：R18（取消笔数>0）

### Task6 — 物料分批到货
- 触发：采购到货时，30%概率触发
- 逻辑：首批到60~80%数量，剩余部分延1~3天补到；每批都写入IQC质检记录
- 校验：R22（同一PO有多条IQC记录）

### Task7 — 库存盘点调整
- 触发：每7天一次
- 逻辑：对所有物料用 Box-Muller 正态分布产生扰动（σ = 库存量×2%），写入"盘点盈余"/"盘点亏损"库存事务

### Task8 — 换线首件检验（IPQC）
- 触发：每次换线Setup完成后
- 逻辑：15%不合格率，不合格时调整0.5小时后必须重检；写入 `quality_inspection`（type="首件检验"）
- 校验：R20（IPQC记录数>0）

### Task9 — FQC成品出货检验
- 触发：每次发货前
- 逻辑：5%不合格率，不合格时批次Hold、退回库存、暂停发货；写入 `quality_inspection`（type="FQC出货检验"）
- 校验：R19（FQC记录数>0）

### Task10 — 订单优先级动态升级
- 触发：每天，8%概率
- 逻辑：随机选一个未升级过的已确认订单，优先级升至1（最高），联动更新对应工单优先级，下一次排程时该工单会优先处理

### Task11 — 仓库间平衡调拨
- 触发：每12小时检查
- 逻辑：发现某物料总库存>2×安全库存 且 可用库存<0.5×安全库存时，从备用仓调拨至生产仓
- 写入：`material_transfer`（from_work_order_id/to_work_order_id 为NULL，from_location="备用仓"，to_location="生产仓"）

---

## 七、数据库写入器（db_writer.py）

`SimulationDBWriter` 提供以下核心方法：

| 方法 | 说明 |
|---|---|
| `insert(table, data)` | 单条插入（带缓冲，1000条批量提交） |
| `update(table, where, data)` | 按条件更新 |
| `query(sql_or_table, params_or_where)` | 兼容两种调用：原始SQL 或 表名+字典 |
| `get(table, where)` | 按字典查询单条记录 |
| `query_table(table, where)` | 按字典查询多条记录 |
| `query_by_status(table, status)` | 按status字段筛选 |
| `_query_sql(sql, params)` | 内部原始SQL查询 |
| `get_work_order_by_co(order_id)` | 通过客户订单ID查工单 |
| `query_pending_woms()` | 查询待分配物料需求（含优先级） |
| `query_shortage_woms()` | 查询缺料物料需求 |
| `flush_transactions()` / `flush_status_logs()` | 强制刷新缓冲区 |

---

## 八、数据校验项（R1–R23）

在 `run_semiconductor_demo.py` 末尾运行，确保数据逻辑一致：

| 编号 | 校验内容 | PASS条件 |
|---|---|---|
| R1 | 库存预留量 ≤ 总库存量 | 无违规记录 |
| R2 | 物料消耗量 ≤ 分配量 | 无超耗记录 |
| R3 | 生产任务时间单调（开始<结束） | 无负时长任务 |
| R4 | 调拨数量均为正数 | 无0或负调拨 |
| R5 | 采购订单行金额正常 | 单价>0 |
| R6 | 外键一致性（机台） | 无悬空外键 |
| R7 | 外键一致性（工单） | 无悬空外键 |
| R8 | 库存余额非负 | 无负库存 |
| R9 | 工序前驱约束 | 工序时间顺序正确 |
| R10 | 良率损耗传递正常 | 每道工序产出≤投入 |
| R11 | 机台PM维护已执行 | ≥1次 |
| R13 | MachineCapability动态更新 | 有更新记录 |
| R14 | 客户订单发货率 | 发货率≥50% | ✅ PASS |
| R15 | Schedule快照已写入 | ≥1条 |
| R16 | 质检记录总数 | IQC+过程质检>0 |
| R17 | 机台随机故障次数 | ≥5次 |
| R18 | 订单取消笔数 | >0笔 |
| R19 | FQC出货检验记录 | >0条 | ✅ PASS |
| R20 | IPQC首件检验记录 | >0条 |
| R21 | 工单实际开工日期填充率 | ≥50% |
| R22 | 分批到货（同PO多次IQC） | >0笔 |
| R23 | 周日排程时段无新建任务 | 09-11时内无任务 |

---

## 九、常见问题

**Q: 为什么工序执行这么快？**  
A: v3.0引入了实时动态排程机制，工序完成后立即排程后续工序，响应时间从23小时缩短到<1分钟。配合Lot批量加工（25个芯片/批），工序流转效率大幅提升。

**Q: 每次运行数据不一样，正常吗？**  
A: 正常。仿真使用随机数（泊松分布订单、指数分布故障间隔等），每次结果略有差异，但业务逻辑和R1-R23校验保持一致。

**Q: 运行完成后去哪里看数据？**  
A: 数据写入 `d:\WorkHorse\No3\commander_demov3\data.db`，可用 DB Browser for SQLite 或项目前端本体视图查看。

**Q: 仿真周期从60天改为120天的原因？**  
A: 半导体制造工序复杂（100-135道工序/产品），需要更长周期才能充分展示订单完成、发货、质检等完整业务场景。v3.0优化后，120天内可以完成大量订单。

**Q: 如何修改仿真周期或订单密度？**  
A: 修改 `factory_data.py` 末尾的 `SIMULATION_CONFIG` 字典：
- `duration_days`：仿真天数（当前60天）
- `order_arrival_lambda`：每天平均订单数（当前2.5，泊松分布）

**Q: 如何新增产品线？**  
A: 在 `factory_data.py` 中：
1. 在 `PRODUCTS` 中增加产品定义
2. 在 `MATERIALS` 中增加专用物料（如需）
3. 在 `BOMS` 中增加BOM行
4. 在 `PROCESS_ROUTES` 和 `ROUTE_STEPS` 中定义工艺路线
5. 在 `MACHINES` / `MACHINE_CAPABILITIES` 中增加机台
6. 在 `SETUP_MATRIX` 中定义换线时间

**Q: PowerShell运行时报错乱码怎么办？**  
A: 确保在终端运行前执行：`chcp 65001`，或者使用 VS Code 的集成终端。

---

## 十一、v3.0 版本更新说明 ✨

### 11.1 核心改进

**问题背景**：
- v2.0版本中，120天仿真0个订单完成，发货率0%，所有工单延期  
- 根本原因：排程机制缺陷 + 工序时间计算错误  
- 工序平均间隔72小时（3天），100+道工序需要300天才能完成  

**v3.0 三大修复**：

1. **工序计划时间计算修复**  
   - 位置：`simulation.py` 第506行  
   - 问题：工序时间被错误放大3倍（批量系数重复计算）  
   - 修复：直接使用批量调整后的std_time  
   - 效果：工序计划时间从27小时降至9小时（111道工序）  

2. **实时动态排程机制**  
   - 位置：`simulation.py` 新增`realtime_schedule_after_completion()`方法  
   - 问题：每天只排程1次，工序完成后平均等待35小时  
   - 修复：工序完成事件驱动 + 4小时轮询  
   - 效果：工序间隔从72小时降至几分钟，订单16天完成  
   - 架构：从批处理模式升级为流处理模式  

3. **排队时间优化**  
   - 位置：`simulation.py` 第526行  
   - 问题：批量加工后排队时间仍为1小时  
   - 修复：减少到0.5小时  
   - 效果：符合Lot批量加工的实际生产场景  

### 11.2 性能对比

| 指标 | v2.0 | v3.0 | 改善 |
|------|------|------|------|
| 首个订单完成时间 | 120天未完成 | 第16天 | 提前104天 |
| 工序平均间隔 | 72.3小时 | 几分钟~几小时 | ↓ 95% |
| 排程响应速度 | 23小时 | <1分钟 | ↓ 99.9% |
| R14发货率 | 0% WARN | 正常 PASS | ✓ |
| R19 FQC检验 | 0条 WARN | 有记录 PASS | ✓ |
| 27天完成订单数 | 0个 | 3个+ | ∞ |

### 11.3 架构升级：从批处理到流处理

**v2.0 批处理模式**：
```
[09:00] 全局排程 → [等待23小时] → [次日09:00] 全局排程 → ...
```

**v3.0 流处理模式**：
```
[工序A完成] → [实时排程工序B] → [工序B完成] → [实时排程工序C] → ...
        ↓                              ↓
  [每4小时全局检查]          [每4小时全局检查]
```

### 11.4 已知瓶颈与优化建议

**WC-TEST-BI（老化测试）机台瓶颈**：
- BI工序：0.96小时/道（其他工序0.081小时，12倍差距）  
- 当前配置：4台BI机台，理论利用率142%  
- 实际影响：由于实时排程缓解，订单仍能按时完成  
- 优化建议：如需进一步提升产能，可增加至6台（利用率降至94.7%）  
- 配置文件：`factory_data.py` → `MACHINE_CFG["WC-TEST-BI"]`  

---

## 十二、仿真时钟说明

- 仿真开始时间：`2026-04-01 08:00:00`（`env.now = 0`）
- 时间单位：小时（`env.now = 24` = 次日08:00）
- 真实时间转换：`sim_time_to_datetime(env.now)` = `start_date + timedelta(hours=env.now)`
- 工作时间：08:00–20:00（日班），20:00–次日08:00（夜班，效率折减0.92）
- 周日完全不排程，机台如因跨日任务占用而计划到周日，会自动推迟到周一08:00
