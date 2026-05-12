import sqlite3
from pathlib import Path

# 数据库路径（项目根目录）
DB_PATH = Path(__file__).parent.parent / "semiconductor_data.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("采购订单行状态分布")
print("=" * 80)

# 1. 统计各状态的订单行数量
cursor.execute("""
    SELECT status, COUNT(*) as cnt 
    FROM purchase_order_line 
    GROUP BY status
    ORDER BY cnt DESC
""")
print("\n状态分布:")
for status, cnt in cursor.fetchall():
    print(f"  {status:10s}: {cnt} 行")

# 2. 查看具体的订单行
print("\n" + "=" * 80)
print("前10个采购订单行详情")
print("=" * 80)
cursor.execute("""
    SELECT po_id, line_id, material_id, quantity, received_quantity, status 
    FROM purchase_order_line 
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"\n  PO: {row[0]}")
    print(f"  Line: {row[1]}")
    print(f"  Material: {row[2]}")
    print(f"  Quantity: {row[3]}")
    print(f"  Received: {row[4]}")
    print(f"  Status: {row[5]}")
    print(f"  在途: {row[3] - row[4] if row[4] else row[3]}")

# 3. 检查"未开始"、"待收货"、"部分收货"状态的订单行
print("\n" + "=" * 80)
print("应该计入在途的订单行")
print("=" * 80)
cursor.execute("""
    SELECT po_id, line_id, material_id, quantity, received_quantity, status 
    FROM purchase_order_line 
    WHERE status IN ('未开始', '待收货', '部分收货')
    LIMIT 10
""")
rows = cursor.fetchall()
if rows:
    for row in rows:
        transit = row[3] - (row[4] or 0)
        print(f"\n  PO: {row[0]}, Line: {row[1]}")
        print(f"  Material: {row[2]}, Status: {row[5]}")
        print(f"  Quantity: {row[3]}, Received: {row[4] or 0}, 在途: {transit}")
else:
    print("\n  ❌ 没有找到状态为'未开始'、'待收货'、'部分收货'的订单行")
    print("\n  检查实际使用的状态值:")
    cursor.execute("SELECT DISTINCT status FROM purchase_order_line")
    print("  实际状态:", [r[0] for r in cursor.fetchall()])

conn.close()
