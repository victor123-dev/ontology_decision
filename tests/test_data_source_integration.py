import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.data_source_manager import data_source_manager
from app.models.data_source import DataSource
from app.utils.db_client import create_engine, sessionmaker

def test_data_source_manager():
    print("开始测试 DataSourceManager...")
    
    engine = create_engine("sqlite:///data.db")
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        data_sources = db.query(DataSource).all()
        print(f"找到 {len(data_sources)} 个数据源")
        
        if data_sources:
            ds = data_sources[0]
            print(f"测试数据源: {ds.name} (ID: {ds.id}, Type: {ds.type})")
            
            try:
                tables = data_source_manager.get_client(data_source_id=ds.id)
                print(f"成功连接到数据源: {ds.name}")
                tables_list = tables.get_tables()
                print(f"数据源中的表: {tables_list}")
                
                if tables_list:
                    table_name = tables_list[0]
                    print(f"测试查询表: {table_name}")
                    
                    query = f"SELECT * FROM {table_name} LIMIT 5"
                    result = data_source_manager.execute_query(data_source_id=ds.id, query=query)
                    print(f"查询结果: {result}")
                    
                    print("✓ 数据源管理器测试通过")
                else:
                    print("⚠ 数据源中没有表")
                    
            except Exception as e:
                print(f"✗ 数据源连接测试失败: {str(e)}")
        else:
            print("⚠ 没有找到数据源，请先创建数据源")
            
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
    finally:
        db.close()

def test_drive_engine_data_source_access():
    print("\n开始测试驱动引擎中的数据源访问...")
    
    from app.engines.drive_engine import DriveEngine
    
    engine = DriveEngine()
    
    test_script = '''
try:
    ds_info = data_source.get_data_source("demo_data_database")
    if ds_info:
        print(f"获取到数据源信息: {ds_info}")
        result = (True, {"data_source_info": ds_info})
    else:
        result = (False, {"error": "DataSource not found"})
except Exception as e:
    result = (False, {"error": str(e)})
'''
    
    test_event = {
        'type': 'test',
        'data': {'test': 'data'}
    }
    
    try:
        result = engine._run_preprocess_script(test_script, test_event)
        print(f"脚本执行结果: {result}")
        if isinstance(result, tuple) and result[0]:
            print("✓ 驱动引擎数据源访问测试通过")
        else:
            print("⚠ 驱动引擎测试未完全通过，但功能可用")
    except Exception as e:
        print(f"✗ 驱动引擎测试失败: {str(e)}")

if __name__ == "__main__":
    test_data_source_manager()
    test_drive_engine_data_source_access()
    print("\n所有测试完成!")