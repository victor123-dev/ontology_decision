# Python Ontology SDK 使用说明

本SDK基于项目中的业务模型、关系和行动自动生成，提供面向对象的编程接口来操作业务数据。

## 目录结构

生成的SDK包含以下主要组件：

```
my_ontology_sdk/
├── __init__.py                # SDK入口点
├── core/                      # 核心模块
│   ├── client.py              # 本体客户端
│   ├── business_model.py      # 业务模型基类
│   ├── session.py             # 会话管理
│   └── types.py               # 类型定义
├── models/                    # 业务对象模型
│   ├── work_order.py          # 工单模型
│   ├── customer.py            # 客户模型
│   └── ... (其他业务模型)
├── query/                     # 查询模块
│   ├── builder.py             # 查询构建器
│   └── executor.py            # 查询执行器
├── actions/                   # 行动模块
│   └── registry.py            # 行动注册表
├── config.py                  # 配置文件
└── setup.py                   # 安装配置
```

## 生成SDK

### 前端界面操作（推荐）

1. **打开本体视图页面**
   - 在浏览器中访问本体视图页面
   - 确保已定义业务模型、关系和行动

2. **点击"生成SDK"按钮**
   - 在页面左上角工具栏找到"生成SDK"按钮
   - 点击后会弹出SDK生成配置模态框

3. **配置SDK参数**
   - **包名**：输入Python包名称（例如：`my_business_sdk`）
   - **版本号**：输入版本号（默认：`1.0.0`）
   - **输出路径**：自动生成为 `./sdk/{包名}`，不可编辑

4. **生成SDK**
   - 点击"生成SDK"按钮开始生成
   - 系统会显示"正在生成SDK，请稍候..."的加载提示
   - 生成完成后会显示成功消息

5. **获取生成的SDK**
   - SDK源码位于：`./sdk/{包名}/`
   - 可安装的包文件位于：`./dist/` 目录下
   - 包含 `.tar.gz` 和 `.whl` 两种格式

### API端点

- **获取SDK信息**：`GET /api/v1/sdk/info`
- **生成SDK**：`POST /api/v1/sdk/generate`

### 生成参数

```json
{
  "output_path": "./sdk/my_ontology_sdk",
  "package_name": "my_ontology_sdk", 
  "version": "1.0.0"
}
```

## 安装SDK

### 开发阶段（推荐）

```bash
# 卸载旧版本（如果有）
pip uninstall my-ontology-sdk -y

# 可编辑安装，代码修改立即生效
pip install -e ./sdk/my_ontology_sdk

# 或直接安装Wheel包
pip install ./dist/my_ontology_sdk-1.0.0-py3-none-any.whl
```

### 生产环境

在 `requirements.txt` 中添加：

```txt
# 方式1：本地路径依赖
./dist/my_ontology_sdk-1.0.0-py3-none-any.whl

# 方式2：可编辑安装（如果需要）
-e ./sdk/my_ontology_sdk
```

## 基本使用

### 初始化客户端

```python
from my_ontology_sdk import OntologyClient

# 初始化客户端
client = OntologyClient(
    api_url="http://localhost:8080",  # 后端API地址
    api_key="your-api-key"           # API密钥（如果需要）
)
```

### 操作业务对象

#### 查找对象

SDK支持三种查找方式：

##### 方式1：属性访问（推荐）
```python
# 通过models命名空间直接访问模型管理器（类型安全，IDE支持好）

# 查找多个对象
work_orders = client.models.workOrder.find(
    production_workshop="Assembly",
    status="active"
)

# 获取单个对象（通过主键值）
work_order = client.models.workOrder.get("WO-001")

# 创建新对象
new_order = client.models.workOrder.create(
    work_order_number="WO-002",
    item_code="PROD-001",
    production_quantity=200,
    production_workshop="Assembly"
)

# 统计记录数
count = client.models.workOrder.count(status="active")

# 检查记录是否存在  
exists = client.models.workOrder.exists(status="active")
```

##### 方式2：查询构建器（链式调用）
```python
# 复杂查询使用Query Builder
orders = (client.query
          .from_model("workOrder")
          .where_eq("production_workshop", "Assembly")
          .where_gt("production_quantity", 100)
          .order_by("created_at")
          .desc()
          .take(10)
          .execute())

# 查询结果集支持链式操作
active_orders = orders.filter(lambda x: x.status in ["pending", "in_progress"])
order_numbers = active_orders.pluck("work_order_number")
first_order = active_orders.first()
```

##### 方式3：向后兼容（字符串方式）
```python
# 保留原有的字符串方式（向后兼容）
work_orders = client.get_model("workOrder").find(
    production_workshop="Assembly",
    status="active"
)
```

#### 更新和删除对象

```python
# 更新对象（自动使用正确的主键字段）
success = work_order.update(
    status="completed",
    actual_quantity=195
)

# 删除对象（自动使用正确的主键字段）
# 注意：删除操作只在服务器端执行，本地对象不会自动销毁
# 建议删除后将对象置为 None
success = work_order.delete()
work_order = None  # 推荐做法

# 刷新对象数据（重新从服务器获取最新数据）
success = work_order.refresh()
```

### 主键处理说明

SDK 自动处理不同业务模型的主键字段差异：

- **每个模型知道自己的主键字段名**：例如 `work_order` 的主键可能是 `order_id`，而 `customer` 的主键可能是 `customer_code`
- **实例方法自动使用正确的主键**：`update()`、`delete()`、`refresh()` 方法会自动识别并使用正确的主键字段
- **对象表示显示实际主键**：`print(work_order)` 会显示 `<WorkOrder(order_id=WO-001)>` 而不是 `<WorkOrder(id=None)>`

```python
# 无论主键字段名是什么，API 使用方式保持一致
work_order = client.models.workOrder.get("WO-001")  # "WO-001" 是主键值
work_order.update(status="completed")                # 自动使用 order_id 作为主键
work_order.delete()                                 # 自动使用 order_id 作为主键
```

### 关系查询

SDK自动为业务模型间的关系生成导航方法：

```python
# 正向关系查询（工单 -> 材料明细）
material_details = work_order.get_material_detail_by_work_order_number()

# 反向关系查询（一对多关系）
dispatch_details = work_order.get_dispatch_details_by_work_order_number()

# 对关系结果进行链式操作
completed_dispatches = dispatch_details.filter(lambda x: x.status == "completed")
```

### 执行行动

SDK 支持多种 action 执行方式，推荐使用参数对象化的方式：

#### 方式1：参数对象化（推荐）
```python
# 创建参数对象（类型安全，IDE支持好）
params = AddAlertRuleParameters(
    rule_code="RULE_001",
    rule_name="库存预警规则", 
    message_template="库存低于阈值: {{item_code}}",
    trigger_condition="inventory_quantity < 100",
    trigger_timing="real_time",
    risk_level_classification="high",
    effective_time="2026-04-09",
    expiration_time="2027-04-09"
)

# 执行行动
result = client.actions.AddAlertRuleAction.execute(params)
```

#### 方式2：字典参数（向后兼容）
```python
# 使用字典参数
dict_params = {
    "rule_code": "RULE_002",
    "rule_name": "销售预警规则",
    "message_template": "销售额异常: {{customer_id}}",
    "trigger_condition": "sales_amount > 10000", 
    "trigger_timing": "daily",
    "risk_level_classification": "medium",
    "effective_time": "2026-04-09",
    "expiration_time": "2027-04-09"
}

# 执行行动
result = client.actions.AddAlertRuleAction.execute_with_dict(dict_params)
```

#### 方式3：传统方式（完全向后兼容）
```python
# 传统的字符串方式
result = client.execute_action("AddAlertRuleAction", dict_params)
```

#### 参数对象优势
- **类型安全**：编译时检查参数类型和必需性
- **IDE支持**：自动补全、跳转、重构
- **参数验证**：内置 `validate()` 方法
- **文档友好**：参数有详细类型注解

#### 参数对象方法
```python
# 验证参数
is_valid, errors = params.validate()

# 转换为字典
param_dict = params.to_dict()

# 从字典创建
params = AddAlertRuleParameters.from_dict(param_dict)
```

## 高级功能

### ModelNamespace 属性访问

`client.models` 是一个 `ModelNamespace` 对象，提供以下特性：

- **属性访问**：`client.models.workOrder`
- **IDE自动补全**：输入 `client.models.` 显示所有可用模型
- **类型安全**：编译时检查模型是否存在
- **动态发现**：`client.models.list_models()` 列出所有模型

```python
# 动态获取模型列表
available_models = client.models.list_models()
print(f"可用模型: {available_models}")

# 迭代所有模型
for model_instance in client.models:
    print(f"模型: {model_instance.__class__.__name__}")
```

### QueryResult 链式操作

查询结果返回 `QueryResult` 对象，支持丰富的链式操作：

```python
# 基础操作
orders = client.models.workOrder.find(production_workshop="Assembly")

# 长度和布尔判断
print(f"找到 {len(orders)} 个订单")
if orders:
    print("有订单存在")

# 索引和迭代
first_order = orders[0]  # 索引访问
for order in orders:      # 迭代
    print(order.work_order_number)

# 链式过滤和转换
high_priority_orders = (orders
                       .filter(lambda x: x.production_quantity > 100)
                       .filter(lambda x: x.status != "cancelled"))

# 数据提取
order_ids = high_priority_orders.pluck("work_order_number")
order_info = high_priority_orders.map(lambda x: {
    "id": x.work_order_number,
    "quantity": x.production_quantity,
    "workshop": x.production_workshop
})

# 转换格式
order_list = high_priority_orders.to_list()
order_dict_list = high_priority_orders.to_dict()
```

### 复杂查询条件

支持多种查询操作符：

```python
# 基础条件
.where_eq("status", "active")        # 等于
.where_ne("status", "cancelled")     # 不等于
.where_gt("production_quantity", 100) # 大于
.where_gte("priority", 1)            # 大于等于
.where_lt("priority", 5)             # 小于
.where_lte("quantity", 1000)         # 小于等于

# 高级条件
.where_contains("work_order_number", "WO")  # 字符串包含
.where_in("status", ["pending", "active"])  # IN条件
.where_between("quantity", 50, 500)        # 范围条件

# 排序和分页
.order_by("created_at", "desc")      # 排序
.asc()                               # 升序（链式）
.desc()                              # 降序（链式）
.take(10)                            # 限制数量
.skip(20)                            # 跳过记录
.page(2, 20)                         # 分页（第2页，每页20条）

# 快捷方法
.count()                             # 获取记录数
.exists()                            # 检查是否存在
.first()                             # 获取第一条
```

### 错误处理

```python
try:
    # 属性访问方式
    work_order = client.models.workOrder.create(**data)
    if work_order:
        print(f"创建成功: {work_order.work_order_number}")
    else:
        print("创建失败")
        
except AttributeError as e:
    print(f"模型不存在: {e}")
except Exception as e:
    print(f"操作异常: {e}")
```

## 配置选项

### 自定义API设置

```python
from my_ontology_sdk.config import DEFAULT_API_URL, DEFAULT_TIMEOUT

client = OntologyClient(
    api_url="https://your-production-api.com",
    api_key="production-api-key"
)
```

### 会话管理

```python
# 获取底层会话对象进行自定义请求
session = client.get_session()
response = session.get("/custom-endpoint")
```

## 最佳实践

### 1. 优先使用属性访问方式
```python
# 推荐：类型安全，IDE支持好
orders = client.models.workOrder.find(production_workshop="Assembly")

# 不推荐：运行时才能发现问题
orders = client.get_model("workOrder").find(production_workshop="Assembly")
```

### 2. 客户端复用
创建一个全局客户端实例并在整个应用中复用：

```python
# app/core/sdk_client.py
from my_ontology_sdk import OntologyClient
import os

sdk_client = OntologyClient(
    api_url=os.getenv("ONTOLOGY_API_URL", "http://localhost:8080"),
    api_key=os.getenv("ONTOLOGY_API_KEY")
)
```

### 3. 业务服务封装
将SDK操作封装到业务服务中：

```python
# app/services/work_order_service.py
from app.core.sdk_client import sdk_client

class WorkOrderService:
    def get_active_orders(self, workshop):
        # 使用属性访问方式
        return sdk_client.models.workOrder.find(
            production_workshop=workshop,
            status="active"
        )
    
    def complete_order(self, order_id, actual_quantity):
        order = sdk_client.models.workOrder.get(order_id)
        if order:
            return order.execute_action("complete_work_order", {
                "actual_quantity": actual_quantity
            })
        return None
    
    def get_high_volume_orders(self, workshop, min_quantity=100):
        # 使用Query Builder进行复杂查询
        return (sdk_client.query
                .from_model("workOrder")
                .where_eq("production_workshop", workshop)
                .where_gt("production_quantity", min_quantity)
                .order_by("created_at", "desc")
                .take(50)
                .execute())
```

### 4. 异常处理
始终处理SDK操作可能的异常：

```python
def safe_create_work_order(data):
    try:
        return sdk_client.models.workOrder.create(**data)
    except AttributeError as e:
        logger.error(f"模型不存在: {e}")
        return None
    except Exception as e:
        logger.error(f"创建工单失败: {e}")
        return None
```

### 5. 组合使用模式
```python
# 完整示例：属性访问 + 链式查询 + 结果处理
def process_assembly_orders():
    # 1. 使用属性访问获取模型
    orders = client.models.workOrder.find(production_workshop="Assembly")
    
    # 2. 使用QueryResult进行链式过滤
    pending_orders = orders.filter(lambda x: x.status == "pending")
    
    # 3. 提取关键信息
    order_summary = pending_orders.map(lambda x: {
        "number": x.work_order_number,
        "quantity": x.production_quantity,
        "due_date": x.planned_completion_date
    })
    
    # 4. 返回处理结果
    return {
        "total_count": len(pending_orders),
        "orders": order_summary,
        "high_priority": pending_orders.filter(lambda x: x.production_quantity > 500)
    }
```

## 维护和更新

### 重新生成SDK

当业务模型发生变化时，重新生成SDK：

1. 调用SDK生成API
2. 如果使用可编辑安装，代码变更自动生效
3. 如果使用Wheel包安装，需要重新安装新版本

### 版本管理

建议为SDK建立版本管理策略：

- 开发阶段：使用可编辑安装
- 测试阶段：生成特定版本的Wheel包
- 生产阶段：使用固定版本的Wheel包

## 故障排除

### 常见问题

1. **导入错误**：确保SDK已正确安装
   ```bash
   pip list | grep ontology
   ```

2. **API连接失败**：检查API URL和密钥配置
   
3. **字段不存在**：确认业务模型字段名称是否正确

4. **权限错误**：检查API密钥是否有足够权限

5. **模型不存在**：使用 `client.models.list_models()` 查看可用模型

### 调试技巧

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

检查生成的模型代码：

```python
# 查看模型可用字段、主键信息和方法
print("主键字段:", client.models.workOrder._primary_key_field)
print("所有字段:", client.models.workOrder._fields)
print("可用方法:", [method for method in dir(client.models.workOrder) if not method.startswith('_')])

# 查看具体对象的数据和主键值
order = client.models.workOrder.get("WO-001")
if order:
    print("主键值:", order._get_primary_key_value())
    print("对象数据:", order.__dict__)
    print("字典格式:", order.to_dict())
    print("对象表示:", repr(order))
```

## 支持的业务模型

生成的SDK包含项目中所有业务模型，具体模型列表可通过以下方式获取：

```python
# 获取SDK信息
import requests
response = requests.get("http://localhost:8080/api/v1/sdk/info")
models = response.json()["data"]["models"]
for model in models:
    print(f"模型: {model['name']}, 字段: {[f['name'] for f in model['fields']]}")

# 或者通过SDK客户端
client = OntologyClient("http://localhost:8080", "api-key")
print("可用模型:", client.models.list_models())

# 查看特定模型的主键字段
work_order_manager = client.models.workOrder
print(f"工单模型主键字段: {work_order_manager._primary_key_field}")
```

---
*本文档基于自动生成的SDK，具体可用的模型、字段和关系请以实际生成的代码为准。*