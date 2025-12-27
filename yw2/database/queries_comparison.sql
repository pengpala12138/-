-- SQL查询语句两种实现方式对比

-- =======================================
-- 查询1: 查询各区域近30天的环境监测数据及设备状态
-- =======================================

-- 实现方式1: 传统JOIN查询
SELECT
    ri.region_name,
    mi.indicator_name,
    mi.unit,
    ed.collection_time,
    ed.monitor_value,
    mi.standard_upper,
    mi.standard_lower,
    CASE
        WHEN ed.monitor_value > mi.standard_upper THEN '超出上限'
        WHEN ed.monitor_value < mi.standard_lower THEN '低于下限'
        ELSE '正常'
    END as threshold_status,
    ed.data_quality,
    ed.is_abnormal,
    ed.abnormal_reason,
    md.device_type,
    md.operation_status as device_status
FROM environment_data ed
JOIN region_info ri ON ed.region_id = ri.region_id
JOIN monitor_indicator mi ON ed.indicator_id = mi.indicator_id
JOIN monitor_device md ON ed.device_id = md.device_id
WHERE ed.collection_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY ed.collection_time DESC
LIMIT 100;

-- 实现方式2: 使用CTE(Common Table Expressions)和连接顺序调整
WITH recent_data AS (
    SELECT *
    FROM environment_data
    WHERE collection_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    ORDER BY collection_time DESC
    LIMIT 100
)
SELECT
    ri.region_name,
    mi.indicator_name,
    mi.unit,
    rd.collection_time,
    rd.monitor_value,
    mi.standard_upper,
    mi.standard_lower,
    CASE
        WHEN rd.monitor_value > mi.standard_upper THEN '超出上限'
        WHEN rd.monitor_value < mi.standard_lower THEN '低于下限'
        ELSE '正常'
    END as threshold_status,
    rd.data_quality,
    rd.is_abnormal,
    rd.abnormal_reason,
    md.device_type,
    md.operation_status as device_status
FROM recent_data rd
JOIN monitor_device md ON rd.device_id = md.device_id
JOIN region_info ri ON rd.region_id = ri.region_id
JOIN monitor_indicator mi ON rd.indicator_id = mi.indicator_id
ORDER BY rd.collection_time DESC;

-- 差异对比:
-- 1. 实现方式1使用传统的JOIN顺序，先筛选再连接，最后排序和分页
-- 2. 实现方式2使用CTE先筛选出最近30天的数据并分页，再进行连接操作
-- 3. 性能差异：方式2可能更高效，因为先减少了需要连接的数据量
-- 4. 可读性：方式2的逻辑更清晰，先定义最近数据，再进行后续查询
-- 5. 数据一致性：两种方式结果应该一致，但方式2在大表情况下可能更快

-- =======================================
-- 查询2: 统计各区域设备运行状况及监测数据质量
-- =======================================

-- 实现方式1: 传统GROUP BY查询
SELECT
    ri.region_name,
    md.device_type,
    COUNT(DISTINCT md.device_id) as device_count,
    ROUND(SUM(CASE WHEN md.operation_status = '正常' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as device_normal_rate,
    COUNT(DISTINCT ed.data_id) as data_count,
    ROUND(SUM(CASE WHEN ed.data_quality = '优' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as data_excellent_rate,
    ROUND(SUM(CASE WHEN ed.is_abnormal = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as abnormal_rate
FROM region_info ri
JOIN monitor_device md ON ri.region_id = md.region_id
LEFT JOIN environment_data ed ON md.device_id = ed.device_id
    AND ed.collection_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY ri.region_name, md.device_type
HAVING device_count > 0
ORDER BY ri.region_name, device_normal_rate DESC;

-- 实现方式2: 使用子查询预先计算设备状态和数据质量
SELECT
    ri.region_name,
    md.device_type,
    COUNT(DISTINCT md.device_id) as device_count,
    ROUND(AVG(device_status_flag) * 100, 2) as device_normal_rate,
    COALESCE(data_stats.data_count, 0) as data_count,
    COALESCE(data_stats.excellent_rate, 0) as data_excellent_rate,
    COALESCE(data_stats.abnormal_rate, 0) as abnormal_rate
FROM region_info ri
JOIN monitor_device md ON ri.region_id = md.region_id
LEFT JOIN (
    SELECT
        device_id,
        COUNT(DISTINCT data_id) as data_count,
        ROUND(SUM(CASE WHEN data_quality = '优' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as excellent_rate,
        ROUND(SUM(CASE WHEN is_abnormal = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as abnormal_rate
    FROM environment_data
    WHERE collection_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    GROUP BY device_id
) data_stats ON md.device_id = data_stats.device_id
GROUP BY ri.region_name, md.device_type
HAVING device_count > 0
ORDER BY ri.region_name, device_normal_rate DESC;

-- 差异对比:
-- 1. 实现方式1将所有计算放在一个查询中，使用LEFT JOIN直接连接环境数据
-- 2. 实现方式2使用子查询预先计算每个设备的数据统计，再与设备信息连接
-- 3. 性能差异：方式2可能更高效，因为子查询减少了重复计算
-- 4. 灵活性：方式2的子查询可以单独维护和优化
-- 5. 空值处理：方式2使用COALESCE函数更明确地处理无数据的情况

-- =======================================
-- 查询3: 分析不同设备类型的运行状况与数据质量关联性
-- =======================================

-- 实现方式1: 直接GROUP BY设备类型
SELECT
    md.device_type,
    COUNT(DISTINCT md.device_id) as device_count,
    ROUND(SUM(CASE WHEN md.operation_status = '正常' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as device_normal_rate,
    COUNT(DISTINCT ed.data_id) as data_count,
    ROUND(SUM(CASE WHEN ed.data_quality = '优' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as data_excellent_rate,
    ROUND(SUM(CASE WHEN ed.is_abnormal = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as abnormal_rate
FROM monitor_device md
LEFT JOIN environment_data ed ON md.device_id = ed.device_id
    AND ed.collection_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY md.device_type
HAVING device_count > 0
ORDER BY device_normal_rate DESC;

-- 实现方式2: 使用CTE分步骤计算
WITH device_stats AS (
    SELECT
        device_type,
        COUNT(DISTINCT device_id) as device_count,
        ROUND(SUM(CASE WHEN operation_status = '正常' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as device_normal_rate
    FROM monitor_device
    GROUP BY device_type
    HAVING device_count > 0
),
data_stats AS (
    SELECT
        md.device_type,
        COUNT(DISTINCT ed.data_id) as data_count,
        ROUND(SUM(CASE WHEN ed.data_quality = '优' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as data_excellent_rate,
        ROUND(SUM(CASE WHEN ed.is_abnormal = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as abnormal_rate
    FROM monitor_device md
    JOIN environment_data ed ON md.device_id = ed.device_id
    WHERE ed.collection_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    GROUP BY md.device_type
)
SELECT
    ds.device_type,
    ds.device_count,
    ds.device_normal_rate,
    COALESCE(ds_stats.data_count, 0) as data_count,
    COALESCE(ds_stats.data_excellent_rate, 0) as data_excellent_rate,
    COALESCE(ds_stats.abnormal_rate, 0) as abnormal_rate
FROM device_stats ds
LEFT JOIN data_stats ds_stats ON ds.device_type = ds_stats.device_type
ORDER BY ds.device_normal_rate DESC;

-- 差异对比:
-- 1. 实现方式1是单查询直接计算所有指标
-- 2. 实现方式2使用两个CTE分别计算设备状态和数据质量，再进行连接
-- 3. 可读性：方式2逻辑更清晰，每个CTE负责一个统计任务
-- 4. 维护性：方式2的CTE可以独立修改和测试
-- 5. 性能：在复杂查询中，方式2可能更容易被优化器处理

-- =======================================
-- 查询4: 查询异常数据分析报告
-- =======================================

-- 实现方式1: 直接GROUP BY和HAVING筛选异常数据
SELECT
    ri.region_name,
    mi.indicator_name,
    mi.unit,
    DATE(ed.collection_time) as data_date,
    COUNT(*) as total_records,
    SUM(CASE WHEN ed.is_abnormal = TRUE THEN 1 ELSE 0 END) as abnormal_count,
    ROUND(SUM(CASE WHEN ed.is_abnormal = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as abnormal_rate,
    AVG(ed.monitor_value) as avg_value,
    MIN(ed.monitor_value) as min_value,
    MAX(ed.monitor_value) as max_value,
    MIN(mi.standard_lower) as standard_lower,
    MAX(mi.standard_upper) as standard_upper
FROM environment_data ed
JOIN region_info ri ON ed.region_id = ri.region_id
JOIN monitor_indicator mi ON ed.indicator_id = mi.indicator_id
WHERE ed.collection_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY ri.region_name, mi.indicator_name, mi.unit, DATE(ed.collection_time)
HAVING abnormal_count > 0
ORDER BY data_date DESC, abnormal_rate DESC;

-- 实现方式2: 先筛选异常数据，再进行统计
SELECT
    ri.region_name,
    mi.indicator_name,
    mi.unit,
    DATE(ed.collection_time) as data_date,
    COUNT(*) as total_records,
    SUM(abnormal_flag) as abnormal_count,
    ROUND(SUM(abnormal_flag) * 100.0 / COUNT(*), 2) as abnormal_rate,
    AVG(ed.monitor_value) as avg_value,
    MIN(ed.monitor_value) as min_value,
    MAX(ed.monitor_value) as max_value,
    MIN(mi.standard_lower) as standard_lower,
    MAX(mi.standard_upper) as standard_upper
FROM (
    SELECT
        *, 
        CASE WHEN is_abnormal = TRUE THEN 1 ELSE 0 END as abnormal_flag
    FROM environment_data
    WHERE collection_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
) ed
JOIN region_info ri ON ed.region_id = ri.region_id
JOIN monitor_indicator mi ON ed.indicator_id = mi.indicator_id
GROUP BY ri.region_name, mi.indicator_name, mi.unit, DATE(ed.collection_time)
HAVING SUM(abnormal_flag) > 0
ORDER BY data_date DESC, abnormal_rate DESC;

-- 差异对比:
-- 1. 实现方式1在主查询中直接计算异常标志并筛选
-- 2. 实现方式2在子查询中预先计算异常标志，再进行统计
-- 3. 性能：方式2可能更高效，因为异常标志只计算一次
-- 4. 可读性：方式2的异常标志计算逻辑更明确
-- 5. 扩展性：方式2的子查询可以方便地添加更多预处理逻辑

-- =======================================
-- 查询5: 统计设备校准状态及运行效率
-- =======================================

-- 实现方式1: 直接JOIN和CASE语句计算校准状态
SELECT
    ri.region_name,
    md.device_type,
    md.device_id,
    md.install_time,
    md.calibration_cycle,
    md.operation_status,
    CASE
        WHEN md.calibration_cycle IS NULL THEN '未设置校准周期'
        WHEN md.install_time IS NULL THEN '安装时间未知'
        WHEN DATE_ADD(md.install_time, INTERVAL CAST(SUBSTRING(md.calibration_cycle, 1, LENGTH(md.calibration_cycle)-1) AS UNSIGNED) DAY) <= CURDATE() THEN '逾期未校准'
        WHEN DATE_ADD(md.install_time, INTERVAL CAST(SUBSTRING(md.calibration_cycle, 1, LENGTH(md.calibration_cycle)-1) AS UNSIGNED) DAY) <= DATE_ADD(CURDATE(), INTERVAL 7 DAY) THEN '即将到期'
        ELSE '正常'
    END as calibration_status,
    COUNT(ed.data_id) as recent_data_count,
    ROUND(AVG(CASE WHEN ed.data_quality = '优' THEN 1 ELSE 0 END) * 100, 2) as excellent_rate
FROM monitor_device md
JOIN region_info ri ON md.region_id = ri.region_id
LEFT JOIN environment_data ed ON md.device_id = ed.device_id
    AND ed.collection_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY ri.region_name, md.device_type, md.device_id, md.install_time, md.calibration_cycle, md.operation_status
ORDER BY calibration_status, ri.region_name, md.device_type;

-- 实现方式2: 使用CTE分离校准状态计算和数据统计
WITH device_calibration AS (
    SELECT
        md.*,
        ri.region_name,
        CASE
            WHEN md.calibration_cycle IS NULL THEN '未设置校准周期'
            WHEN md.install_time IS NULL THEN '安装时间未知'
            WHEN DATE_ADD(md.install_time, INTERVAL CAST(SUBSTRING(md.calibration_cycle, 1, LENGTH(md.calibration_cycle)-1) AS UNSIGNED) DAY) <= CURDATE() THEN '逾期未校准'
            WHEN DATE_ADD(md.install_time, INTERVAL CAST(SUBSTRING(md.calibration_cycle, 1, LENGTH(md.calibration_cycle)-1) AS UNSIGNED) DAY) <= DATE_ADD(CURDATE(), INTERVAL 7 DAY) THEN '即将到期'
            ELSE '正常'
        END as calibration_status
    FROM monitor_device md
    JOIN region_info ri ON md.region_id = ri.region_id
),
data_quality AS (
    SELECT
        device_id,
        COUNT(data_id) as recent_data_count,
        ROUND(AVG(CASE WHEN data_quality = '优' THEN 1 ELSE 0 END) * 100, 2) as excellent_rate
    FROM environment_data
    WHERE collection_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    GROUP BY device_id
)
SELECT
    dc.region_name,
    dc.device_type,
    dc.device_id,
    dc.install_time,
    dc.calibration_cycle,
    dc.operation_status,
    dc.calibration_status,
    COALESCE(dq.recent_data_count, 0) as recent_data_count,
    COALESCE(dq.excellent_rate, 0) as excellent_rate
FROM device_calibration dc
LEFT JOIN data_quality dq ON dc.device_id = dq.device_id
ORDER BY dc.calibration_status, dc.region_name, dc.device_type;

-- 差异对比:
-- 1. 实现方式1将所有计算放在一个查询中，逻辑较为集中
-- 2. 实现方式2使用两个CTE分别处理校准状态和数据质量统计
-- 3. 可读性：方式2的逻辑更清晰，每个CTE负责一个功能模块
-- 4. 维护性：方式2的CTE可以独立修改和优化
-- 5. 性能：在复杂查询中，方式2可能更容易被数据库优化器处理
-- 6. 空值处理：方式2使用COALESCE更明确地处理无数据的情况

-- =======================================
-- 总结: 两种实现方式的主要差异维度
-- =======================================
-- 1. 代码结构：单查询 vs 模块化查询(CTE/子查询)
-- 2. 执行效率：不同的连接顺序和筛选时机可能影响性能
-- 3. 可读性：CTE和子查询通常提供更好的逻辑分离
-- 4. 维护性：模块化查询更容易修改和扩展
-- 5. 空值处理：显式处理vs隐式处理
-- 6. 索引利用：不同的查询结构可能导致不同的索引使用策略
-- 7. 复杂度：简单查询适合单查询，复杂逻辑适合模块化方式

-- 在实际应用中，应根据具体的数据库系统、数据量大小和性能需求选择合适的实现方式。
