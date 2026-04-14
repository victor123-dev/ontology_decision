// 供应链控制塔 - 模拟数据层
// 数据来源：缺料分析本体_预警案例.xlsx

// ==================== KPI 数据 ====================
export const kpiData = { purchaseOnTimeRate: 87.3,
  monthlySalesAmount: 4823.56,
  monthlySalesQty: 1247.0,
  alertCount: 42,
  autoExecCount: 18 };

// ==================== 图表数据 ====================
export const chartData = [
  { month: '2025-01', salesForecast: 8200, salesOrder: 7850, purchaseQty: 9100 },
  { month: '2025-02', salesForecast: 7600, salesOrder: 7200, purchaseQty: 8400 },
  { month: '2025-03', salesForecast: 9100, salesOrder: 8950, purchaseQty: 10200 },
  { month: '2025-04', salesForecast: 9800, salesOrder: 9600, purchaseQty: 11000 },
  { month: '2025-05', salesForecast: 10500, salesOrder: 10200, purchaseQty: 11800 },
  { month: '2025-06', salesForecast: 11200, salesOrder: 10800, purchaseQty: 12500 },
  { month: '2025-07', salesForecast: 10800, salesOrder: 10500, purchaseQty: 12100 },
  { month: '2025-08', salesForecast: 11500, salesOrder: 11200, purchaseQty: 13000 },
  { month: '2025-09', salesForecast: 12000, salesOrder: 11800, purchaseQty: 13500 },
  { month: '2025-10', salesForecast: 12800, salesOrder: 12400, purchaseQty: 14200 },
  { month: '2025-11', salesForecast: 13500, salesOrder: 13100, purchaseQty: 15000 },
  { month: '2025-12', salesForecast: 14200, salesOrder: 13800, purchaseQty: 15800 },
];

// ==================== 物流动态 ====================
export const logisticsData = [
  { id: 'LOG000001', time: '09:42', carrier: '联邦快递FedEx', from: '日本信越化学工业', to: '厂区A栋收货区', material: 'ArF光刻胶KrF-248nm', status: '在途', po: 'PO000001' },
  { id: 'LOG000002', time: '09:18', carrier: '德邦物流', from: '德国默克半导体材料', to: '厂区B栋收货区', material: '12英寸硅晶圆P型', status: '已到达', po: 'PO000002' },
  { id: 'LOG000003', time: '08:55', carrier: 'DHL快递', from: '美国应用材料AMAT', to: '厂区C栋设备区', material: 'CVD沉积机配件', status: '清关中', po: 'PO000003' },
  { id: 'LOG000004', time: '08:30', carrier: '顺丰速运', from: '台湾台积电代工厂', to: '厂区A栋收货区', material: 'LPDDR4内存颗粒', status: '延误', po: 'PO000004' },
  { id: 'LOG000005', time: '07:58', carrier: '中远海运', from: '韩国三星半导体', to: '上海港口', material: 'NAND Flash存储芯片', status: '在途', po: 'PO000005' },
  { id: 'LOG000006', time: '07:35', carrier: '联邦快递FedEx', from: '荷兰ASML光刻机', to: '厂区D栋洁净室', material: 'EUV光刻机配件', status: '已到达', po: 'PO000006' },
  { id: 'LOG000007', time: '07:12', carrier: '德邦物流', from: '日本东京电子TEL', to: '厂区B栋设备区', material: '干法蚀刻机耗材', status: '在途', po: 'PO000007' },
  { id: 'LOG000008', time: '06:50', carrier: 'UPS快递', from: '美国泛林集团Lam', to: '厂区C栋收货区', material: 'CMP研磨液', status: '已到达', po: 'PO000008' },
  { id: 'LOG000009', time: '06:28', carrier: '顺丰速运', from: '中国台积电南京厂', to: '厂区A栋收货区', material: 'MCU微控制器芯片', status: '在途', po: 'PO000009' },
  { id: 'LOG000010', time: '06:05', carrier: '中远海运', from: '德国英飞凌科技', to: '上海港口', material: 'IGBT功率模块', status: '清关中', po: 'PO000010' },
  { id: 'LOG000011', time: '05:42', carrier: '联邦快递FedEx', from: '日本信越化学工业', to: '厂区A栋收货区', material: '高纯氨气NH3', status: '延误', po: 'PO000011' },
  { id: 'LOG000012', time: '05:20', carrier: 'DHL快递', from: '美国空气化工', to: '厂区气体站', material: '高纯氮气N2', status: '已到达', po: 'PO000012' },
];

// ==================== 需求预测表 ====================
export const forecastMonths = ['2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12'];

export const forecastData = [
  { productCode: 'IC-MOS-001', productName: 'N沟道MOSFET晶体管', months: { '2025-07': 75300, '2025-08': 82000, '2025-09': 78500, '2025-10': 91200, '2025-11': 88600, '2025-12': 95000 } },
  { productCode: 'IC-MOS-002', productName: 'P沟道MOSFET晶体管', months: { '2025-07': 62400, '2025-08': 68000, '2025-09': 71500, '2025-10': 76800, '2025-11': 73200, '2025-12': 80000 } },
  { productCode: 'IC-MCU-001', productName: 'ARM Cortex-M4 MCU', months: { '2025-07': 45200, '2025-08': 48600, '2025-09': 52100, '2025-10': 55800, '2025-11': 58400, '2025-12': 62000 } },
  { productCode: 'IC-FPGA-001', productName: 'Xilinx FPGA芯片', months: { '2025-07': 12800, '2025-08': 14200, '2025-09': 13600, '2025-10': 15900, '2025-11': 16800, '2025-12': 18200 } },
  { productCode: 'MEM-NAND-001', productName: 'NAND Flash 256GB', months: { '2025-07': 38500, '2025-08': 42000, '2025-09': 45600, '2025-10': 48200, '2025-11': 51800, '2025-12': 55000 } },
  { productCode: 'MEM-LPDDR-001', productName: 'LPDDR4 8GB内存', months: { '2025-07': 28600, '2025-08': 31200, '2025-09': 33800, '2025-10': 36500, '2025-11': 38900, '2025-12': 42000 } },
  { productCode: 'IC-PMIC-001', productName: '电源管理IC PMIC', months: { '2025-07': 92000, '2025-08': 98500, '2025-09': 105200, '2025-10': 112000, '2025-11': 108600, '2025-12': 118000 } },
  { productCode: 'IC-RF-001', productName: '5G射频前端芯片', months: { '2025-07': 18200, '2025-08': 20500, '2025-09': 22800, '2025-10': 25100, '2025-11': 27600, '2025-12': 30000 } },
];

// ==================== 地图节点 ====================
export const mapNodes = [
  { id: 'factory', name: '半导体制造厂（本厂）', type: 'factory', city: '上海', lat: 31.23, lng: 121.47 },
  { id: 'cus001', name: '华为海思半导体', type: 'customer', city: '深圳', lat: 22.54, lng: 114.06 },
  { id: 'cus002', name: '中芯国际', type: 'customer', city: '北京', lat: 39.90, lng: 116.41 },
  { id: 'cus003', name: '紫光展锐', type: 'customer', city: '上海', lat: 31.28, lng: 121.52 },
  { id: 'cus004', name: '长江存储', type: 'customer', city: '武汉', lat: 30.59, lng: 114.31 },
  { id: 'sup001', name: '日本信越化学工业', type: 'supplier', city: '上海港', lat: 31.38, lng: 121.62 },
  { id: 'sup002', name: '德国默克半导体', type: 'supplier', city: '天津港', lat: 39.02, lng: 117.72 },
  { id: 'sup003', name: '荷兰ASML光刻机', type: 'supplier', city: '广州港', lat: 23.12, lng: 113.42 },
  { id: 'sup004', name: '美国应用材料AMAT', type: 'supplier', city: '深圳港', lat: 22.62, lng: 114.12 },
  { id: 'log001', name: '联邦快递FedEx上海', type: 'logistics', city: '上海', lat: 31.20, lng: 121.58 },
  { id: 'log002', name: '中远海运天津', type: 'logistics', city: '天津', lat: 39.12, lng: 117.20 },
  { id: 'log003', name: 'DHL广州枢纽', type: 'logistics', city: '广州', lat: 23.18, lng: 113.26 },
];

export const mapRoutes = [
  { from: 'sup001', to: 'factory', type: 'supply', active: true },
  { from: 'sup002', to: 'factory', type: 'supply', active: true },
  { from: 'sup003', to: 'factory', type: 'supply', active: false },
  { from: 'sup004', to: 'factory', type: 'supply', active: true },
  { from: 'factory', to: 'cus001', type: 'delivery', active: true },
  { from: 'factory', to: 'cus002', type: 'delivery', active: true },
  { from: 'factory', to: 'cus003', type: 'delivery', active: true },
  { from: 'factory', to: 'cus004', type: 'delivery', active: true },
  { from: 'log001', to: 'factory', type: 'logistics', active: true },
  { from: 'log002', to: 'factory', type: 'logistics', active: true },
];

// ==================== 预警消息 ====================
export const alertMessages = [
  { id: 'MSG000001',
    title: '【供应中断预警】ArF光刻胶单一来源供应商交期异常',
    content: '供应商日本信越化学工业(SUP0001)的ArF光刻胶(IC-PHR-001)预计到货日2025-04-15，已超出需求日期2025-04-08，延误7天。该物料为关键单一来源，当前库存覆盖仅3天，低于安全库存阈值14天。影响工单WO000023、WO000024，涉及销售订单SO000015(华为海思)。',
    status: '未处理',
    riskLevel: '最高风险',
    poId: 'PO000001',
    supplier: '日本信越化学工业',
    soId: 'SO000015',
    customer: '华为海思半导体',
    ruleCode: 'SCRULE-001',
    createdAt: '2025-04-09 08:30:00',
    rootCause: '根因分析（5Why法）：\n① 为何触发预警？→ ArF光刻胶库存覆盖天数3天 < 安全库存14天\n② 为何库存不足？→ 采购订单PO000001延误7天到货\n③ 为何采购延误？→ 供应商信越化学日本工厂计划外停产检修\n④ 为何停产检修？→ 关键蒸馏设备故障，零件从德国进口需2周\n⑤ 为何无备用供应商？→ ArF光刻胶技术壁垒高，全球仅信越、JSR、陶氏三家，其余两家已满产\n\n关键证据：采购物流单LOG000001.预计到达时间(2025-04-15) vs 工单WO000023.计划开始日期(2025-04-08)，差值+7天；存货IC-PHR-001.安全库存量=14天用量，当前库存=3天用量',
    action: { id: 'ACT000001',
      description: '该预警为最高风险级别的关键物料供应中断。ArF光刻胶是光刻工序的核心耗材，断供将直接导致生产线停工。建议立即启动紧急采购程序，同时评估是否可临时切换至KrF光刻胶工艺（需工艺评估），并向客户华为海思提前沟通交期风险，争取2-3天缓冲期。',
      steps: [
        { id: 'S1', step: '立即通知采购总监和生产总监', role: '系统自动/预警负责人', deadline: '30分钟内', output: '紧急会议通知', type: 'action' },
        { id: 'S2', step: '联系信越化学确认最新到货时间', role: '采购员', deadline: '2小时内', output: '供应商确认函', type: 'action' },
        { id: 'S3', step: '评估是否可向JSR/陶氏紧急采购', role: '采购经理', deadline: '4小时内', output: '替代供应商评估报告', type: 'decision', branches: [{ label: '可替代', nextStep: 'S4A' }, { label: '无法替代', nextStep: 'S4B' }] },
        { id: 'S4A', step: '向JSR或陶氏发出紧急采购订单', role: '采购员', deadline: '当日', output: '紧急采购订单', type: 'action' },
        { id: 'S4B', step: '评估工艺切换可行性（KrF替代ArF）', role: '工艺工程师', deadline: '当日', output: '工艺评估报告', type: 'action' },
        { id: 'S5', step: '向华为海思提前沟通交期风险', role: '销售经理', deadline: '当日下班前', output: '客户沟通记录', type: 'action' },
        { id: 'S6', step: '更新工单WO000023/WO000024排程', role: '生产计划员', deadline: '次日', output: '更新后的生产计划', type: 'action' },
        { id: 'END', step: '关闭预警，记录处理结果', role: '预警负责人', deadline: '处理完成后', output: '预警处理报告', type: 'end' },
      ] } },
  { id: 'MSG000002',
    title: '【库存预警】12英寸硅晶圆库存跌破动态安全库存',
    content: '物料12英寸硅晶圆P型(IC-WAF-001)当前库存量1,250片，低于动态安全库存2,100片（覆盖14天生产需求）。MRP计划需求日期2025-04-12，当前库存仅可维持6天生产。在途采购订单PO000008数量500片，预计到货2025-04-18，到货后仍有缺口350片。',
    status: '处理中',
    riskLevel: '高风险',
    poId: 'PO000008',
    supplier: '日本信越化学工业',
    soId: 'SO000022',
    customer: '中芯国际',
    ruleCode: 'SCRULE-002',
    createdAt: '2025-04-09 07:15:00',
    rootCause: '根因分析（MRP差异分析）：\n需求侧：销售订单SO000022（中芯国际，NAND Flash代工）需求量3,500片，需求日2025-04-12\n供应侧：在库1,250片 + 在途500片(PO000008) = 1,750片\n缺口：3,500 - 1,750 = 1,750片\n\n根因：Q1季度需求预测偏低（预测2,800片，实际接单3,500片），导致安全库存设置不足；叠加PO000008供应商产能紧张，交期从标准21天延长至28天。',
    action: { id: 'ACT000002',
      description: '12英寸硅晶圆是核心基础物料，库存不足将影响整个生产线。需立即追加采购订单，同时优化MRP参数，提高安全库存设置。短期内可考虑向友商借货或调配其他规格晶圆。',
      steps: [
        { id: 'S1', step: '确认当前实际库存和在途数量', role: '仓库管理员', deadline: '1小时内', output: '库存盘点报告', type: 'action' },
        { id: 'S2', step: '向信越化学追加紧急采购1,750片', role: '采购员', deadline: '当日', output: '追加采购订单', type: 'action' },
        { id: 'S3', step: '评估是否可向其他供应商分散采购', role: '采购经理', deadline: '当日', output: '多供应商采购方案', type: 'decision', branches: [{ label: '可分散', nextStep: 'S4A' }, { label: '集中采购', nextStep: 'S4B' }] },
        { id: 'S4A', step: '向Siltronic/SK Siltron发出补充订单', role: '采购员', deadline: '次日', output: '补充采购订单', type: 'action' },
        { id: 'S4B', step: '与信越化学谈判加急费用和交期', role: '采购经理', deadline: '次日', output: '谈判纪要', type: 'action' },
        { id: 'S5', step: '更新MRP安全库存参数至3,000片', role: '供应链规划师', deadline: '本周内', output: 'MRP参数变更单', type: 'action' },
        { id: 'END', step: '关闭预警', role: '预警负责人', deadline: '处理完成后', output: '处理报告', type: 'end' },
      ] } },
  { id: 'MSG000003',
    title: '【供应商绩效预警】德国默克半导体材料OTD连续下滑',
    content: '供应商德国默克半导体材料(SUP0002)近3个月准时交货率(OTD)持续下滑：1月92%→2月85%→3月76%，已连续3个月低于KPI阈值90%，且呈下降趋势。涉及物料：光刻胶显影液、CMP抛光液、蚀刻液等5种关键化学品。当前有3张在途采购订单存在延误风险。',
    status: '未处理',
    riskLevel: '中风险',
    poId: 'PO000015',
    supplier: '德国默克半导体材料',
    soId: 'SO000031',
    customer: '长江存储',
    ruleCode: 'SCRULE-003',
    createdAt: '2025-04-09 06:00:00',
    rootCause: '根因分析（供应商绩效分析SPA）：\n绩效维度分析：\n- 产能：默克德国工厂Q1扩产改造，临时产能下降15%\n- 物流：欧洲→亚洲海运时间从28天延长至35天（苏伊士运河绕行）\n- 质量：2月批次出现显影液浓度偏差，返工导致交期延误\n\n趋势预测：若不干预，4月OTD预计降至68%，将影响光刻/蚀刻工序连续性。',
    action: { id: 'ACT000003',
      description: '供应商OTD持续下滑是系统性风险信号。需立即启动供应商绩效改善计划（SIP），同时评估备用供应商，避免过度依赖单一供应商。短期内增加安全库存缓冲。',
      steps: [
        { id: 'S1', step: '发起供应商绩效改善会议邀请', role: '采购经理', deadline: '3个工作日内', output: '会议邀请函', type: 'action' },
        { id: 'S2', step: '收集默克近3月延误根因报告', role: '供应商质量工程师', deadline: '5个工作日内', output: '根因分析报告', type: 'action' },
        { id: 'S3', step: '评估备用供应商（陶氏化学/巴斯夫）', role: '采购经理', deadline: '本周内', output: '备用供应商评估报告', type: 'decision', branches: [{ label: '有合格备选', nextStep: 'S4A' }, { label: '无合格备选', nextStep: 'S4B' }] },
        { id: 'S4A', step: '启动备用供应商认证流程', role: '供应商质量工程师', deadline: '30天内', output: '供应商认证报告', type: 'action' },
        { id: 'S4B', step: '与默克签订绩效改善协议(SIP)', role: '采购总监', deadline: '10个工作日内', output: 'SIP协议', type: 'action' },
        { id: 'S5', step: '临时增加相关化学品安全库存至30天', role: '供应链规划师', deadline: '本周内', output: '库存调整方案', type: 'action' },
        { id: 'END', step: '建立月度OTD监控机制', role: '采购经理', deadline: '持续', output: '月度供应商绩效报告', type: 'end' },
      ] } },
  { id: 'MSG000004',
    title: '【生产缺料预警】工单WO000045因LPDDR4内存缺料面临完工延期',
    content: '工单WO000045（产品：LPDDR4内存模组，计划完工2025-04-14）因物料LPDDR4内存颗粒(MEM-LPDDR-001)缺料，当前缺口2,400片。采购订单PO000004在途，但预计到货2025-04-18，晚于计划完工日4天。影响销售订单SO000018（三星电子，金额¥856万），客户要求交期不可延误。',
    status: '未处理',
    riskLevel: '高风险',
    poId: 'PO000004',
    supplier: '韩国SK海力士',
    soId: 'SO000018',
    customer: '三星电子',
    ruleCode: 'SCRULE-004',
    createdAt: '2025-04-08 16:45:00',
    rootCause: '根因分析（缺料分析矩阵）：\n缺料物料：MEM-LPDDR-001 LPDDR4内存颗粒\n需求量：2,400片（工单WO000045）\n当前库存：0片（已被WO000042、WO000043消耗）\n在途数量：2,000片（PO000004，到货2025-04-18）\n净缺口：400片\n\n根因：①需求预测低估（Q2订单量超预期+35%）；②WO000042/43优先级调度消耗了预留库存；③SK海力士产能紧张，交期从14天延长至21天。',
    action: { id: 'ACT000004',
      description: '工单缺料直接威胁客户交期，三星电子为战略客户，违约将面临高额罚款。需紧急协调：一是加快在途物料清关，二是向三星提前沟通，三是评估是否可拆分工单先交付部分数量。',
      steps: [
        { id: 'S1', step: '确认PO000004最新在途状态', role: '采购员', deadline: '2小时内', output: '物流跟踪报告', type: 'action' },
        { id: 'S2', step: '联系顺丰速运加急清关', role: '物流专员', deadline: '当日', output: '加急清关申请', type: 'action' },
        { id: 'S3', step: '评估是否可拆分工单先交付1,600片', role: '生产计划员', deadline: '当日', output: '工单拆分方案', type: 'decision', branches: [{ label: '可拆分', nextStep: 'S4A' }, { label: '不可拆分', nextStep: 'S4B' }] },
        { id: 'S4A', step: '向三星提交部分交货方案', role: '销售经理', deadline: '当日下班前', output: '客户沟通记录', type: 'action' },
        { id: 'S4B', step: '向三星申请延期4天并提供补偿方案', role: '销售总监', deadline: '当日下班前', output: '延期申请函', type: 'action' },
        { id: 'S5', step: '向SK海力士追加紧急采购400片', role: '采购员', deadline: '次日', output: '紧急采购订单', type: 'action' },
        { id: 'END', step: '关闭预警，更新工单排程', role: '生产计划员', deadline: '处理完成后', output: '更新后工单', type: 'end' },
      ] } },
  { id: 'MSG000005',
    title: '【地缘政治预警】FPGA芯片出口管制风险，供应中断概率>80%',
    content: '美国商务部BIS最新出口管制清单（2025-04-07更新）新增对华FPGA芯片出口限制，涉及Xilinx Virtex-7及以上系列。本公司当前有2张在途采购订单（PO000031、PO000032，合计3,200片）面临被扣押风险。库存仅剩450片，可维持生产约8天。涉及销售订单SO000041（中科院计算所，金额¥1,240万）。',
    status: '未处理',
    riskLevel: '最高风险',
    poId: 'PO000031',
    supplier: '美国赛灵思Xilinx',
    soId: 'SO000041',
    customer: '中科院计算所',
    ruleCode: 'SCRULE-005',
    createdAt: '2025-04-09 09:00:00',
    rootCause: '根因分析（PESTLE分析）：\nP（政治）：中美贸易摩擦升级，美国扩大半导体出口管制范围\nE（经济）：FPGA为高端可编程芯片，美国厂商（Xilinx/Intel Altera）占全球90%市场份额\nS（社会）：国内FPGA替代品（紫光同创/安路科技）性能差距2-3代，短期无法替代\nT（技术）：Virtex-7采用28nm工艺，国内最先进量产为14nm，但FPGA设计工具链依赖美国EDA软件\nL（法律）：出口管制违规将面临企业制裁，需立即停止相关采购\nE（环境）：全球FPGA供应链高度集中，无法快速分散风险\n\n结论：短期（0-3个月）面临严重供应中断风险，需立即启动国产替代评估和库存保护措施。',
    action: { id: 'ACT000005',
      description: '地缘政治导致的供应中断是最高级别风险，需要公司最高管理层介入。短期需保护现有库存，中期需加速国产FPGA替代评估，长期需重构供应链战略。这将影响公司核心产品路线图。',
      steps: [
        { id: 'S1', step: '立即上报CEO和董事会，启动应急响应', role: '供应链总监', deadline: '2小时内', output: '应急响应启动通知', type: 'action' },
        { id: 'S2', step: '咨询法律顾问确认合规要求', role: '法务总监', deadline: '当日', output: '法律合规意见书', type: 'action' },
        { id: 'S3', step: '暂停PO000031/PO000032执行，避免违规', role: '采购总监', deadline: '当日', output: '采购暂停通知', type: 'action' },
        { id: 'S4', step: '评估国产FPGA替代方案（紫光同创/安路）', role: '技术总监', deadline: '5个工作日内', output: '国产替代技术评估报告', type: 'decision', branches: [{ label: '可替代', nextStep: 'S5A' }, { label: '短期不可替代', nextStep: 'S5B' }] },
        { id: 'S5A', step: '启动国产FPGA替代项目，制定12个月路线图', role: '技术总监', deadline: '10个工作日内', output: '国产替代路线图', type: 'action' },
        { id: 'S5B', step: '通过合法渠道（第三国）评估替代采购可行性', role: '采购总监', deadline: '5个工作日内', output: '合规采购方案', type: 'action' },
        { id: 'S6', step: '向中科院计算所说明情况，协商解决方案', role: '销售总监', deadline: '当日下班前', output: '客户沟通纪要', type: 'action' },
        { id: 'END', step: '建立地缘政治风险监控机制', role: '供应链总监', deadline: '持续', output: '风险监控月报', type: 'end' },
      ] } },
  { id: 'MSG000006',
    title: '【交期预警】采购订单PO000022预计到货超出需求日期',
    content: '采购订单PO000022（物料：CVD沉积机靶材，供应商：美国应用材料AMAT）预计到货日2025-04-20，超出工单WO000067需求日期2025-04-16，延误4天。',
    status: '已处理',
    riskLevel: '中风险',
    poId: 'PO000022',
    supplier: '美国应用材料AMAT',
    soId: 'SO000028',
    customer: '紫光展锐',
    ruleCode: 'SCRULE-001',
    createdAt: '2025-04-07 14:20:00',
    rootCause: '供应商产能排期冲突，已协商加急处理，预计提前2天到货。',
    action: { id: 'ACT000006',
      description: '已联系AMAT加急处理，预计提前2天到货，工单延期2天，已获客户紫光展锐确认。',
      steps: [
        { id: 'S1', step: '联系AMAT确认加急可行性', role: '采购员', deadline: '已完成', output: '供应商确认函', type: 'action' },
        { id: 'END', step: '已处理完毕', role: '采购员', deadline: '已完成', output: '处理报告', type: 'end' },
      ] } },
  { id: 'MSG000007',
    title: '【库存预警】高纯氨气NH3库存低于安全库存',
    content: '高纯氨气NH3(GAS-NH3-001)当前库存12瓶，低于安全库存20瓶。用于CVD氮化硅沉积工序，日消耗约2瓶，当前库存可维持6天。',
    status: '处理中',
    riskLevel: '中风险',
    poId: 'PO000045',
    supplier: '美国空气化工',
    soId: 'SO000035',
    customer: '华为海思半导体',
    ruleCode: 'SCRULE-002',
    createdAt: '2025-04-08 11:30:00',
    rootCause: '季度末采购计划未及时更新，导致补货订单延迟下达。已下达补货订单PO000045，预计3天到货。',
    action: { id: 'ACT000007',
      description: '已下达补货订单，预计3天内到货，库存可维持至到货，风险可控。',
      steps: [
        { id: 'S1', step: '确认PO000045在途状态', role: '采购员', deadline: '当日', output: '物流确认', type: 'action' },
        { id: 'END', step: '到货后关闭预警', role: '仓库管理员', deadline: '3天内', output: '入库记录', type: 'end' },
      ] } },
  { id: 'MSG000008',
    title: '【供应商绩效预警】日本东京电子TEL交货准时率下滑至78%',
    content: '供应商日本东京电子TEL近2个月OTD：2月88%→3月78%，连续下滑10个百分点，低于KPI阈值85%。涉及干法蚀刻机耗材等3种物料。',
    status: '未处理',
    riskLevel: '中风险',
    poId: 'PO000038',
    supplier: '日本东京电子TEL',
    soId: 'SO000042',
    customer: '中芯国际',
    ruleCode: 'SCRULE-003',
    createdAt: '2025-04-09 07:45:00',
    rootCause: '东京电子日本工厂受地震影响，部分产线停工2周，导致交期延误。目前已恢复生产，预计下月OTD回升。',
    action: { id: 'ACT000008',
      description: '不可抗力导致的OTD下滑，需关注后续恢复情况，同时临时增加安全库存缓冲。',
      steps: [
        { id: 'S1', step: '获取TEL工厂恢复生产证明', role: '采购员', deadline: '3个工作日内', output: '供应商证明文件', type: 'action' },
        { id: 'S2', step: '临时增加相关耗材安全库存', role: '供应链规划师', deadline: '本周内', output: '库存调整方案', type: 'action' },
        { id: 'END', step: '持续监控OTD，下月评估是否关闭', role: '采购经理', deadline: '持续', output: '月度监控报告', type: 'end' },
      ] } },
];

// 获取风险等级颜色
export function getRiskColor(level) { switch (level) { case '最高风险': return 'sct-badge-critical';
    case '高风险': return 'sct-badge-high';
    case '中风险': return 'sct-badge-medium';
    case '低风险': return 'sct-badge-low';
    default: return 'sct-badge-low'; } }

export function getRiskTextColor(level) { switch (level) { case '最高风险': return '#ff4d4d';
    case '高风险': return '#ff7043';
    case '中风险': return '#ffa726';
    case '低风险': return '#66bb6a';
    default: return '#66bb6a'; } }

export function getStatusColor(status) { switch (status) { case '未处理': return '#ef4444';
    case '处理中': return '#f59e0b';
    case '已处理': return '#22c55e';
    default: return '#94a3b8'; } }

export function getLogisticsStatusColor(status) { switch (status) { case '在途': return '#3b82f6';
    case '已到达': return '#22c55e';
    case '延误': return '#ef4444';
    case '清关中': return '#f59e0b';
    default: return '#94a3b8'; } }
