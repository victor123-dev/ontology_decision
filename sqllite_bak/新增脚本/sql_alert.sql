ALTER TABLE alert_message ADD COLUMN status TEXT;
ALTER TABLE alert_message ADD COLUMN related_po TEXT;
ALTER TABLE alert_message ADD COLUMN related_so TEXT;
ALTER TABLE alert_message ADD COLUMN supplier TEXT;
ALTER TABLE alert_message ADD COLUMN related_customer TEXT;
ALTER TABLE alert_message ADD COLUMN create_time TEXT;

-- MSG000001（图片第1行）
UPDATE alert_message
SET status = '未处理',
    related_po = 'P0000001',
    related_so = 'S0000015',
    supplier = '日本信越化学工业',
    related_customer = '华为海思半导体',
    create_time = '2025-04-09 08:30:00'
WHERE message_id = 'MSG000001';

-- MSG000002（图片第2行）
UPDATE alert_message
SET status = '处理中',
    related_po = 'P0000008',
    related_so = 'S0000022',
    supplier = '日本信越化学工业',
    related_customer = '中芯国际',
    create_time = '2025-04-09 07:15:00'
WHERE message_id = 'MSG000002';

-- MSG000003（图片第3行）
UPDATE alert_message
SET status = '未处理',
    related_po = 'P0000015',
    related_so = 'S0000031',
    supplier = '德国默克半导体材料',
    related_customer = '长江存储',
    create_time = '2025-04-09 06:00:00'
WHERE message_id = 'MSG000003';

-- MSG000004（图片第4行）
UPDATE alert_message
SET status = '未处理',
    related_po = 'P0000004',
    related_so = 'S0000018',
    supplier = '韩国SK海力士',
    related_customer = '三星电子',
    create_time = '2025-04-08 16:45:00'
WHERE message_id = 'MSG000004';

-- MSG000005（图片第5行）
UPDATE alert_message
SET status = '未处理',
    related_po = 'P0000031',
    related_so = 'S0000041',
    supplier = '美国赛灵思Xilinx',
    related_customer = '中科院计算所',
    create_time = '2025-04-09 09:00:00'
WHERE message_id = 'MSG000005';

-- MSG000006（图片第6行）
UPDATE alert_message
SET status = '已处理',
    related_po = 'P0000022',
    related_so = 'S0000028',
    supplier = '美国应用材料AMAT',
    related_customer = '紫光展锐',
    create_time = '2025-04-07 14:20:00'
WHERE message_id = 'MSG000006';

-- MSG000007（图片第7行）
UPDATE alert_message
SET status = '处理中',
    related_po = 'P0000045',
    related_so = 'S0000035',
    supplier = '美国空气化工',
    related_customer = '华为海思半导体',
    create_time = '2025-04-08 11:30:00'
WHERE message_id = 'MSG000007';

-- MSG000008（图片第8行）
UPDATE alert_message
SET status = '未处理',
    related_po = 'P0000038',
    related_so = 'S0000042',
    supplier = '日本东京电子TEL',
    related_customer = '中芯国际',
    create_time = '2025-04-09 07:45:00'
WHERE message_id = 'MSG000008';