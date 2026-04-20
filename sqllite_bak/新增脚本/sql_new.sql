
CREATE TABLE IF NOT EXISTS supply_chain_map_nodes (
    node_id TEXT PRIMARY KEY,
    node_name TEXT NOT NULL,
    node_type TEXT NOT NULL,
    city TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    primary_key TEXT
);

INSERT INTO supply_chain_map_nodes (node_id, node_name, node_type, city, latitude, longitude, primary_key) VALUES
('factory', '半导体制造厂（本厂）', 'factory', '上海', 31.23, 121.47, 'cus001'),
('cus001', '华为海思半导体', 'customer', '深圳', 22.54, 114.06, 'cus001'),
('cus002', '中芯国际', 'customer', '北京', 39.9, 116.41, 'cus002'),
('cus003', '紫光展锐', 'customer', '上海', 31.28, 121.52, 'cus003'),
('cus004', '长江存储', 'customer', '武汉', 30.59, 114.31, 'cus004'),
('sup001', '日本信越化学工业', 'supplier', '上海港', 31.38, 121.62, 'sup001'),
('sup002', '德国默克半导体', 'supplier', '天津港', 39.02, 117.72, 'sup002'),
('sup003', '荷兰ASML光刻机', 'supplier', '广州港', 23.12, 113.42, 'sup003'),
('sup004', '美国应用材料AMAT', 'supplier', '深圳港', 22.62, 114.12, 'sup004'),
('log001', '联邦快递FedEx上海', 'logistics', '上海', 31.2, 121.58, 'log001'),
('log002', '中远海运天津', 'logistics', '天津', 39.12, 117.2, 'log002'),
('log003', 'DHL广州枢纽', 'logistics', '广州', 23.18, 113.26, 'log003');

-- 2. Supply Chain Map Routes Table
CREATE TABLE IF NOT EXISTS supply_chain_map_routes (
    start_node TEXT NOT NULL,
    end_node TEXT NOT NULL,
    route_type TEXT NOT NULL,
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1)),
    FOREIGN KEY (start_node) REFERENCES supply_chain_map_nodes(node_id),
    FOREIGN KEY (end_node) REFERENCES supply_chain_map_nodes(node_id)
);

INSERT INTO supply_chain_map_routes (start_node, end_node, route_type, is_active) VALUES
('sup001', 'factory', 'supply', 1),
('sup002', 'factory', 'supply', 1),
('sup003', 'factory', 'supply', 0),
('sup004', 'factory', 'supply', 1),
('factory', 'cus001', 'delivery', 1),
('factory', 'cus002', 'delivery', 1),
('factory', 'cus003', 'delivery', 1),
('factory', 'cus004', 'delivery', 1),
('log001', 'factory', 'logistics', 1),
('log002', 'factory', 'logistics', 1);


CREATE TABLE IF NOT EXISTS logistics_dynamic (
    logistics_id TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    carrier TEXT NOT NULL,
    shipper TEXT NOT NULL,
    consignee TEXT NOT NULL,
    material_name TEXT NOT NULL,
    logistics_status TEXT NOT NULL,
    related_po TEXT NOT NULL,
    primary_key TEXT
);

INSERT INTO logistics_dynamic (logistics_id, time, carrier, shipper, consignee, material_name, logistics_status, related_po, primary_key) VALUES
('LOG000001', '09:42', '联邦快递FedEx', '日本信越化学工业', '厂区A栋收货区', 'ArF光刻胶KrF-248nm', '在途', 'PO000001', 'LOG000001'),
('LOG000002', '09:18', '德邦物流', '德国默克半导体材料', '厂区B栋收货区', '12英寸硅晶圆P型', '已到达', 'PO000002', 'LOG000002'),
('LOG000003', '08:55', 'DHL快递', '美国应用材料AMAT', '厂区C栋设备区', 'CVD沉积机配件', '清关中', 'PO000003', 'LOG000003'),
('LOG000004', '08:30', '顺丰速运', '台湾台积电代工厂', '厂区A栋收货区', 'LPDDR4内存颗粒', '延误', 'PO000004', 'LOG000004'),
('LOG000005', '07:58', '中远海运', '韩国三星半导体', '上海港口', 'NAND Flash存储芯片', '在途', 'PO000005', 'LOG000005'),
('LOG000006', '07:35', '联邦快递FedEx', '荷兰ASML光刻机', '厂区D栋洁净室', 'EUV光刻机配件', '已到达', 'PO000006', 'LOG000006'),
('LOG000007', '07:12', '德邦物流', '日本东京电子TEL', '厂区B栋设备区', '干法蚀刻机耗材', '在途', 'PO000007', 'LOG000007'),
('LOG000008', '06:50', 'UPS快递', '美国泛林集团Lam', '厂区C栋收货区', 'CMP研磨液', '已到达', 'PO000008', 'LOG000008'),
('LOG000009', '06:28', '顺丰速运', '中国台积电南京厂', '厂区A栋收货区', 'MCU微控制器芯片', '在途', 'PO000009', 'LOG000009'),
('LOG000010', '06:05', '中远海运', '德国英飞凌科技', '上海港口', 'IGBT功率模块', '清关中', 'PO000010', 'LOG000010'),
('LOG000011', '05:42', '联邦快递FedEx', '日本信越化学工业', '厂区A栋收货区', '高纯氨气NH3', '延误', 'PO000011', 'LOG000011'),
('LOG000012', '05:20', 'DHL快递', '美国空气化工', '厂区气体站', '高纯氮气N2', '已到达', 'PO000012', 'LOG000012');


-- ============================================
-- SQLite 需求预测表建表与数据插入脚本
-- 说明：无临时表过渡，移除primary_key字段
-- ============================================

-- 1. 创建需求预测表（新增需求数量、月份字段）
-- =========================================================
-- 1. 创建需求预测表（含在库量、在途量）
-- =========================================================
CREATE TABLE IF NOT EXISTS demand_forecast (
    product_id TEXT NOT NULL,           -- 产品ID
    product_name TEXT NOT NULL,         -- 产品名称
    demand_quantity INTEGER NOT NULL,   -- 需求数量
    stock_quantity INTEGER NOT NULL,   -- 在库量
    in_transit_quantity INTEGER NOT NULL, -- 在途量
    forecast_month TEXT NOT NULL        -- 预测月份（YYYY-MM）
);

-- =========================================================
-- 2. 插入需求预测及库存数据（48条记录）
-- =========================================================
INSERT INTO demand_forecast (
    product_id, product_name, 
    demand_quantity, stock_quantity, in_transit_quantity, 
    forecast_month
) VALUES

-- IC-MOS-001（N沟道MOSFET晶体管）
('IC-MOS-001', 'N沟道MOSFET晶体管', 75300, 32000, 18000, '2025-07'),
('IC-MOS-001', 'N沟道MOSFET晶体管', 82000, 28000, 22000, '2025-08'),
('IC-MOS-001', 'N沟道MOSFET晶体管', 78500, 26000, 25000, '2025-09'),
('IC-MOS-001', 'N沟道MOSFET晶体管', 91200, 31000, 30000, '2025-10'),
('IC-MOS-001', 'N沟道MOSFET晶体管', 88600, 29000, 27000, '2025-11'),
('IC-MOS-001', 'N沟道MOSFET晶体管', 95000, 33000, 32000, '2025-12'),

-- IC-MOS-002（P沟道MOSFET晶体管）
('IC-MOS-002', 'P沟道MOSFET晶体管', 62400, 25000, 15000, '2025-07'),
('IC-MOS-002', 'P沟道MOSFET晶体管', 68000, 23000, 18000, '2025-08'),
('IC-MOS-002', 'P沟道MOSFET晶体管', 71500, 24000, 21000, '2025-09'),
('IC-MOS-002', 'P沟道MOSFET晶体管', 76800, 26000, 22000, '2025-10'),
('IC-MOS-002', 'P沟道MOSFET晶体管', 73200, 25000, 20000, '2025-11'),
('IC-MOS-002', 'P沟道MOSFET晶体管', 80000, 27000, 23000, '2025-12'),

-- IC-MCU-001（ARM Cortex-M4 MCU）
('IC-MCU-001', 'ARM Cortex-M4 MCU', 45200, 18000, 12000, '2025-07'),
('IC-MCU-001', 'ARM Cortex-M4 MCU', 48600, 17000, 14000, '2025-08'),
('IC-MCU-001', 'ARM Cortex-M4 MCU', 52100, 19000, 16000, '2025-09'),
('IC-MCU-001', 'ARM Cortex-M4 MCU', 55800, 20000, 18000, '2025-10'),
('IC-MCU-001', 'ARM Cortex-M4 MCU', 58400, 21000, 17000, '2025-11'),
('IC-MCU-001', 'ARM Cortex-M4 MCU', 62000, 22000, 20000, '2025-12'),

-- IC-FPGA-001（Xilinx FPGA芯片）
('IC-FPGA-001', 'Xilinx FPGA芯片', 12800, 6000, 4000, '2025-07'),
('IC-FPGA-001', 'Xilinx FPGA芯片', 14200, 6500, 4500, '2025-08'),
('IC-FPGA-001', 'Xilinx FPGA芯片', 13600, 6200, 4200, '2025-09'),
('IC-FPGA-001', 'Xilinx FPGA芯片', 15900, 7000, 5000, '2025-10'),
('IC-FPGA-001', 'Xilinx FPGA芯片', 16800, 7200, 5200, '2025-11'),
('IC-FPGA-001', 'Xilinx FPGA芯片', 18200, 7500, 6000, '2025-12'),

-- MEM-NAND-001（NAND Flash 256GB）
('MEM-NAND-001', 'NAND Flash 256GB', 38500, 16000, 10000, '2025-07'),
('MEM-NAND-001', 'NAND Flash 256GB', 42000, 17000, 12000, '2025-08'),
('MEM-NAND-001', 'NAND Flash 256GB', 45600, 18000, 14000, '2025-09'),
('MEM-NAND-001', 'NAND Flash 256GB', 48200, 19000, 13000, '2025-10'),
('MEM-NAND-001', 'NAND Flash 256GB', 51800, 20000, 15000, '2025-11'),
('MEM-NAND-001', 'NAND Flash 256GB', 55000, 21000, 16000, '2025-12'),

-- MEM-LPDDR-001（LPDDR4 8GB内存）
('MEM-LPDDR-001', 'LPDDR4 8GB内存', 28600, 12000, 8000, '2025-07'),
('MEM-LPDDR-001', 'LPDDR4 8GB内存', 31200, 13000, 9000, '2025-08'),
('MEM-LPDDR-001', 'LPDDR4 8GB内存', 33800, 14000, 10000, '2025-09'),
('MEM-LPDDR-001', 'LPDDR4 8GB内存', 36500, 15000, 11000, '2025-10'),
('MEM-LPDDR-001', 'LPDDR4 8GB内存', 38900, 16000, 10500, '2025-11'),
('MEM-LPDDR-001', 'LPDDR4 8GB内存', 42000, 17000, 12000, '2025-12'),

-- IC-PMIC-001（电源管理IC PMIC）
('IC-PMIC-001', '电源管理IC PMIC', 92000, 35000, 22000, '2025-07'),
('IC-PMIC-001', '电源管理IC PMIC', 98500, 36000, 25000, '2025-08'),
('IC-PMIC-001', '电源管理IC PMIC', 105200, 38000, 27000, '2025-09'),
('IC-PMIC-001', '电源管理IC PMIC', 112000, 40000, 30000, '2025-10'),
('IC-PMIC-001', '电源管理IC PMIC', 108600, 39000, 28000, '2025-11'),
('IC-PMIC-001', '电源管理IC PMIC', 118000, 42000, 32000, '2025-12'),

-- IC-RF-001（5G射频前端芯片）
('IC-RF-001', '5G射频前端芯片', 18200, 8000, 5000, '2025-07'),
('IC-RF-001', '5G射频前端芯片', 20500, 8500, 6000, '2025-08'),
('IC-RF-001', '5G射频前端芯片', 22800, 9000, 7000, '2025-09'),
('IC-RF-001', '5G射频前端芯片', 25100, 9500, 7500, '2025-10'),
('IC-RF-001', '5G射频前端芯片', 27600, 10000, 8000, '2025-11'),
('IC-RF-001', '5G射频前端芯片', 30000, 11000, 9000, '2025-12');