"""  
半导体演示数据 - 数据库操作封装
提供仿真引擎所需的CRUD和查询接口
直接操作SQLite数据库
"""

import sqlite3
import json
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Callable
from simulation_logger import get_simulation_logger

# 获取日志记录器
logger = get_simulation_logger()


class SimulationDBWriter:
    """仿真数据库写入器"""
    
    def __init__(self, db_path: str = "data.db"):
        self.db_path = db_path
        self._conn = None
        self._cursor = None
        self._open()
    
    def _open(self):
        """打开数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._cursor = self._conn.cursor()
    
    def close(self):
        """关闭连接"""
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
            self._cursor = None
    
    def commit(self):
        """提交事务"""
        if self._conn:
            self._conn.commit()
    
    def _serialize_value(self, val) -> Any:
        """序列化值（处理datetime等类型）"""
        if isinstance(val, datetime):
            return val.isoformat()
        if isinstance(val, date):
            return val.isoformat()
        if isinstance(val, bool):
            return 1 if val else 0
        return val
    
    # ========================================================================
    # 基础CRUD
    # ========================================================================
    
    def insert(self, table: str, data: dict, auto_commit: bool = True):
        """单条插入"""
        if not data:
            return
        cols = list(data.keys())
        vals = [self._serialize_value(data[c]) for c in cols]
        placeholders = ",".join(["?"] * len(cols))
        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
        try:
            self._cursor.execute(sql, vals)
            if auto_commit:
                self._conn.commit()
        except Exception as e:
            logger.error(f"[DB Insert Error] {table}: {e}")
    
    def begin_transaction(self):
        """开始事务"""
        pass  # SQLite自动开始事务
    
    def commit_transaction(self):
        """提交事务"""
        if self._conn:
            self._conn.commit()
    
    def bulk_insert_with_transaction(self, table: str, data_list: list, batch_size: int = 1000):
        """批量插入（使用事务）
        
        参数：
        - table: 表名
        - data_list: 数据列表 [{}, {}, ...]
        - batch_size: 每批COMMIT的条数（默认1000）
        """
        if not data_list:
            return
        
        cols = list(data_list[0].keys())
        placeholders = ",".join(["?"] * len(cols))
        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
        
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i+batch_size]
            for data in batch:
                vals = [self._serialize_value(data[c]) for c in cols]
                try:
                    self._cursor.execute(sql, vals)
                except sqlite3.IntegrityError:
                    pass  # 忽略重复
            
            # 每batch_size条COMMIT一次
            self._conn.commit()
    
    def bulk_insert(self, table: str, data_list: List[dict]):
        """批量插入"""
        if not data_list:
            return
        cols = list(data_list[0].keys())
        placeholders = ",".join(["?"] * len(cols))
        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
        rows = []
        for data in data_list:
            rows.append([self._serialize_value(data.get(c)) for c in cols])
        try:
            self._cursor.executemany(sql, rows)
            self._conn.commit()
        except sqlite3.IntegrityError:
            pass
        except Exception as e:
            logger.error(f"[DB Bulk Insert Error] {table}: {e}")
    
    def update(self, table: str, where: dict, data: dict):
        """更新记录
        data中如果值是callable，表示基于当前值计算（如 lambda col: col - qty）
        """
        if not data:
            return
        
        # 先查询当前记录
        where_cols = list(where.keys())
        where_vals = [where[k] for k in where_cols]
        where_clause = " AND ".join([f"{c}=?" for c in where_cols])
        select_sql = f"SELECT * FROM {table} WHERE {where_clause}"
        self._cursor.execute(select_sql, where_vals)
        row = self._cursor.fetchone()
        if not row:
            return
        
        row_dict = dict(row)
        updates = []
        update_vals = []
        
        for col, val in data.items():
            if callable(val):
                # 基于当前值计算
                current_val = row_dict.get(col, 0)
                new_val = val(current_val)
                updates.append(f"{col}=?")
                update_vals.append(self._serialize_value(new_val))
            else:
                updates.append(f"{col}=?")
                update_vals.append(self._serialize_value(val))
        
        if not updates:
            return
        
        update_sql = f"UPDATE {table} SET {','.join(updates)} WHERE {where_clause}"
        try:
            self._cursor.execute(update_sql, update_vals + where_vals)
            self._conn.commit()
        except Exception as e:
            logger.error(f"[DB Update Error] {table}: {e}")
    
    def _query_sql(self, sql: str, params: tuple = ()) -> List[dict]:
        """执行原始SQL查询（内部方法）"""
        self._cursor.execute(sql, params)
        rows = self._cursor.fetchall()
        return [dict(r) for r in rows]

    def query(self, sql_or_table: str, params_or_where=()) -> List[dict]:
        """执行查询（向后兼容方法）
        支持两种调用形式:
        1. query(sql_str, tuple_params) - 原始 SQL
        2. query(table_name, dict_where) - 按字典查询表
        """
        if isinstance(params_or_where, dict):
            # 表名+字典模式
            return self.query_table(sql_or_table, params_or_where)
        return self._query_sql(sql_or_table, params_or_where)
    
    # ========================================================================
    # 仿真专用查询
    # ========================================================================
    
    def query_pending_woms(self) -> List[dict]:
        """查询待分配的物料需求"""
        sql = """
            SELECT wom.*, wo.priority, wo.planned_completion_date, wo.status as wo_status
            FROM work_order_material wom
            JOIN work_order wo ON wom.work_order_id = wo.work_order_id
            WHERE wom.status IN ('待分配', '部分分配')
            AND wo.status NOT IN ('已完成', '取消')
            ORDER BY wo.priority, wom.required_date
        """
        return self.query(sql)
    
    def query_shortage_woms(self) -> List[dict]:
        """查询缺料物料需求"""
        sql = """
            SELECT wom.*, wo.priority, wo.planned_completion_date, wo.status as wo_status
            FROM work_order_material wom
            JOIN work_order wo ON wom.work_order_id = wo.work_order_id
            WHERE wom.status IN ('缺料', '部分分配')
            AND wom.shortage_quantity > 0
            AND wo.status NOT IN ('已完成', '取消')
            ORDER BY wo.priority, wom.required_date
        """
        return self.query(sql)
    
    def find_transfer_candidates(self, material_id: str, exclude_wo_id: str) -> List[dict]:
        """查找可调拨的物料预留（其他工单有富余预留）"""
        sql = """
            SELECT wom.*, wo.priority as wo_priority, wo.planned_completion_date
            FROM work_order_material wom
            JOIN work_order wo ON wom.work_order_id = wo.work_order_id
            WHERE wom.material_id = ?
            AND wom.work_order_id != ?
            AND wom.allocated_quantity > wom.consumed_quantity
            AND wo.status NOT IN ('已完成', '取消')
            ORDER BY wo.priority DESC, wo.planned_completion_date DESC
        """
        return self.query(sql, (material_id, exclude_wo_id))
    
    def get_work_order(self, wo_id: str) -> Optional[dict]:
        """获取工单详情"""
        rows = self.query("SELECT * FROM work_order WHERE work_order_id=?", (wo_id,))
        return rows[0] if rows else None
    
    def get_wom(self, wom_id: str) -> Optional[dict]:
        """获取WOM详情"""
        rows = self.query("SELECT * FROM work_order_material WHERE wom_id=?", (wom_id,))
        return rows[0] if rows else None
    
    def get_production_task(self, task_id: str) -> Optional[dict]:
        """获取生产任务详情"""
        rows = self.query("SELECT * FROM production_task WHERE task_id=?", (task_id,))
        return rows[0] if rows else None
    
    def get_work_order_operations(self, wo_id: str) -> List[dict]:
        """获取工单的所有工序"""
        return self.query(
            "SELECT * FROM work_order_operation WHERE work_order_id=? ORDER BY sequence_no",
            (wo_id,)
        )
    
    def get_wip_lots_by_wo(self, wo_id: str) -> List[dict]:
        """获取工单的所有WIP Lot"""
        return self.query("SELECT * FROM wip_lot WHERE work_order_id=?", (wo_id,))
    
    def query_ready_operations_with_precedence(self) -> List[dict]:
        """P0-1: 查询待排程的已齐套工序（前驱工序必须已完成）"""
        sql = """
            SELECT woo.*, wo.priority, wo.product_id, wo.planned_quantity, wo.planned_start_date,
                   rs.wait_time_hours, rs.transport_time_hours,
                   (
                       SELECT COUNT(*) FROM work_order_operation rest
                       WHERE rest.work_order_id = woo.work_order_id
                       AND rest.sequence_no >= woo.sequence_no
                       AND rest.status != '已完成'
                   ) as remaining_op_count
            FROM work_order_operation woo
            JOIN work_order wo ON woo.work_order_id = wo.work_order_id
            LEFT JOIN route_step rs ON woo.step_id = rs.step_id
            WHERE woo.status = '待开工'
            AND wo.status NOT IN ('已完成', '取消')
            AND (
                SELECT COUNT(*) FROM work_order_material wom
                WHERE wom.work_order_id = wo.work_order_id
                AND wom.wo_op_id = woo.wo_op_id
                AND wom.status IN ('待分配', '缺料')
            ) = 0
            AND (
                SELECT COUNT(*) FROM work_order_operation prev
                WHERE prev.work_order_id = woo.work_order_id
                AND prev.sequence_no < woo.sequence_no
                AND prev.status != '已完成'
            ) = 0
            ORDER BY wo.priority, woo.planned_start
        """
        return self.query(sql)

    def query_shortage_woms_by_material(self, material_id: str) -> List[dict]:
        """P0-3: 查询指定物料的缺料工单（到货后增量MRP用）"""
        sql = """
            SELECT wom.*, wo.priority, wo.planned_completion_date, wo.status as wo_status
            FROM work_order_material wom
            JOIN work_order wo ON wom.work_order_id = wo.work_order_id
            WHERE wom.material_id = ?
            AND wom.status IN ('缺料', '部分分配')
            AND wom.shortage_quantity > 0
            AND wo.status NOT IN ('已完成', '取消')
            ORDER BY wo.priority, wom.required_date
        """
        return self.query(sql, (material_id,))
    
    def get_woms_for_op(self, wo_op_id: str) -> List[dict]:
        """获取工序对应的所有物料需求（含辅料）"""
        return self.query(
            "SELECT * FROM work_order_material WHERE wo_op_id=? AND status IN ('已齐套', '部分分配')",
            (wo_op_id,)
        )

    def get_finished_goods_inventory(self, product_id: str) -> Optional[dict]:
        """获取成品库存"""
        rows = self.query(
            "SELECT * FROM finished_goods_inventory WHERE product_id=?",
            (product_id,)
        )
        return rows[0] if rows else None

    def get_customer_order_by_wo(self, wo_id: str) -> Optional[dict]:
        """通过工单ID找到关联的客户订单"""
        rows = self.query(
            "SELECT co.* FROM customer_order co JOIN work_order wo ON co.order_id = wo.customer_order_id WHERE wo.work_order_id=?",
            (wo_id,)
        )
        return rows[0] if rows else None

    def get_supplier_by_po(self, po_id: str) -> Optional[dict]:
        """通过PO获取供应商信息"""
        rows = self.query(
            "SELECT s.* FROM supplier s JOIN purchase_order po ON s.supplier_id = po.supplier_id WHERE po.po_id=?",
            (po_id,)
        )
        return rows[0] if rows else None

    def count_records(self, table: str) -> int:
        """统计表记录数"""
        rows = self.query(f"SELECT COUNT(*) as cnt FROM {table}")
        return rows[0]["cnt"] if rows else 0

    def get(self, table: str, where: dict) -> Optional[dict]:
        """按条件查询单条记录"""
        if not where:
            return None
        conditions = " AND ".join(f"{k}=?" for k in where)
        params = tuple(where.values())
        rows = self.query(f"SELECT * FROM {table} WHERE {conditions} LIMIT 1", params)
        return rows[0] if rows else None

    def query_table(self, table: str, where: dict = None) -> List[dict]:
        """按条件查询多条记录（where为字典格式）"""
        if not where:
            rows = self.query(f"SELECT * FROM {table}")
        else:
            conditions = " AND ".join(f"{k}=?" for k in where)
            params = tuple(where.values())
            rows = self.query(f"SELECT * FROM {table} WHERE {conditions}", params)
        return rows or []

    def query_by_status(self, table: str, status: str) -> List[dict]:
        """按status字段查询记录"""
        return self.query_table(table, {"status": status})
    
    def query_active_work_orders(self) -> List[dict]:
        """查询所有生产中的工单（已下达或生产中）"""
        sql = """
            SELECT * FROM work_order 
            WHERE status IN ('已下达', '生产中', '延期')
            ORDER BY priority, planned_completion_date
        """
        rows = self._conn.execute(sql).fetchall()
        return [dict(row) for row in rows]
    
    def get_work_order_materials(self, work_order_id: str) -> List[dict]:
        """查询工单的物料需求"""
        sql = """
            SELECT * FROM work_order_material
            WHERE work_order_id = ?
            ORDER BY material_id
        """
        rows = self._conn.execute(sql, (work_order_id,)).fetchall()
        return [dict(row) for row in rows]

    def get_work_order_by_co(self, order_id: str) -> Optional[dict]:
        """通过客户订单ID获取工单"""
        rows = self._query_sql(
            "SELECT * FROM work_order WHERE customer_order_id=? LIMIT 1",
            (order_id,)
        )
        return rows[0] if rows else None
    
    def execute_sql(self, sql: str):
        """执行任意SQL"""
        self._cursor.execute(sql)
        self._conn.commit()
    
    def table_exists(self, table: str) -> bool:
        """检查表是否存在"""
        rows = self.query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        return len(rows) > 0
