-- 1. 查询各区域近30天的环境监测数据及设备状态
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

-- 2. 统计各区域设备运行状况及监测数据质量
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

-- 3. 分析不同设备类型的运行状况与数据质量关联性
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

-- 4. 查询异常数据分析报告
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

-- 5. 统计设备校准状态及运行效率
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

-- 性能优化对比（针对查询2）
-- 优化前：查看执行计划
EXPLAIN
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

-- 优化后：添加复合索引（如果尚未创建）
-- CREATE INDEX idx_env_data_device_time ON environment_data(device_id, collection_time, data_quality, is_abnormal);
-- CREATE INDEX idx_device_region_type ON monitor_device(region_id, device_type, operation_status);

-- 再次查看优化后的执行计划
EXPLAIN
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

-- 执行时间对比
SET profiling = 1;
-- 执行优化前的查询
-- 执行优化后的查询
SHOW PROFILES;