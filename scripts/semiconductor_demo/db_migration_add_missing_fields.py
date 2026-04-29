#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为work_order、work_order_operation、wip_lot表添加缺失字段
执行时间：2026-04-29
"""

import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'semiconductor_data.db')

def migrate():
    """执行迁移"""
    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. work_order表添加work_order_type字段
        cursor.execute("PRAGMA table_info(work_order)")
        wo_columns = [col[1] for col in cursor.fetchall()]
        
        if 'work_order_type' not in wo_columns:
            cursor.execute("ALTER TABLE work_order ADD COLUMN work_order_type VARCHAR(50) DEFAULT '正常'")
            print("✅ work_order表添加 work_order_type 字段")
        else:
            print("⏭️  work_order_type 字段已存在")
        
        # 2. work_order_operation表添加is_rework字段
        cursor.execute("PRAGMA table_info(work_order_operation)")
        woo_columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_rework' not in woo_columns:
            cursor.execute("ALTER TABLE work_order_operation ADD COLUMN is_rework BOOLEAN DEFAULT 0")
            print("✅ work_order_operation表添加 is_rework 字段")
        else:
            print("⏭️  is_rework 字段已存在")
        
        # 3. wip_lot表添加lot_size字段
        cursor.execute("PRAGMA table_info(wip_lot)")
        wip_columns = [col[1] for col in cursor.fetchall()]
        
        if 'lot_size' not in wip_columns:
            cursor.execute("ALTER TABLE wip_lot ADD COLUMN lot_size FLOAT DEFAULT 25")
            print("✅ wip_lot表添加 lot_size 字段")
        else:
            print("⏭️  lot_size 字段已存在")
        
        conn.commit()
        
        # 验证
        print("\n📋 验证表结构:")
        for table in ['work_order', 'work_order_operation', 'wip_lot']:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [col[1] for col in cursor.fetchall()]
            print(f"  {table}: {len(cols)} 个字段")
        
        print("\n✅ 迁移完成！")
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("数据库迁移：添加work_order_type、is_rework、lot_size字段")
    print("=" * 60)
    migrate()
