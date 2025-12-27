-- 1. 监测指标信息表
CREATE TABLE IF NOT EXISTS monitor_indicator (
    indicator_id VARCHAR(20) PRIMARY KEY,
    indicator_name VARCHAR(50) NOT NULL,
    unit VARCHAR(20),
    standard_upper DECIMAL(10,4) NOT NULL,
    standard_lower DECIMAL(10,4) NOT NULL,
    monitor_freq VARCHAR(10)
);

-- 2. 监测设备信息表
CREATE TABLE IF NOT EXISTS monitor_device (
    device_id VARCHAR(20) PRIMARY KEY,
    device_type VARCHAR(50) NOT NULL,
    region_id VARCHAR(20) NOT NULL,
    install_time DATE,
    calibration_cycle VARCHAR(8),
    operation_status VARCHAR(10) NOT NULL CHECK (operation_status IN ('正常', '故障', '离线')),
    comm_proto VARCHAR(50),
    status_update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES region_info(region_id)
);

-- 3. 环境监测数据表
CREATE TABLE IF NOT EXISTS environment_data (
    data_id VARCHAR(20) PRIMARY KEY,
    indicator_id VARCHAR(20) NOT NULL,
    device_id VARCHAR(20) NOT NULL,
    collection_time TIMESTAMP NOT NULL,
    monitor_value DECIMAL(10,4),
    region_id VARCHAR(20) NOT NULL,
    data_quality CHAR(2) NOT NULL CHECK (data_quality IN ('优', '良', '中', '差')),
    is_abnormal BOOLEAN DEFAULT FALSE,
    abnormal_reason VARCHAR(200),
    FOREIGN KEY (indicator_id) REFERENCES monitor_indicator(indicator_id),
    FOREIGN KEY (device_id) REFERENCES monitor_device(device_id),
    FOREIGN KEY (region_id) REFERENCES region_info(region_id)
);

-- 创建索引
CREATE INDEX idx_indicator_name ON monitor_indicator(indicator_name);
CREATE INDEX idx_device_region ON monitor_device(region_id);
CREATE INDEX idx_device_status ON monitor_device(operation_status);
CREATE INDEX idx_device_status_time ON monitor_device(operation_status, status_update_time);
CREATE INDEX idx_data_time ON environment_data(collection_time);
CREATE INDEX idx_data_region ON environment_data(region_id);
CREATE INDEX idx_data_indicator ON environment_data(indicator_id);
CREATE INDEX idx_data_device ON environment_data(device_id);
CREATE INDEX idx_data_abnormal ON environment_data(is_abnormal);

-- 创建视图
-- 1. 区域环境监测视图
CREATE OR REPLACE VIEW v_region_monitor AS
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
ORDER BY ed.collection_time DESC;

-- 2. 设备运行状态统计视图
CREATE OR REPLACE VIEW v_device_status_summary AS
SELECT
    ri.region_name,
    md.device_type,
    COUNT(*) as total_devices,
    SUM(CASE WHEN md.operation_status = '正常' THEN 1 ELSE 0 END) as normal_count,
    SUM(CASE WHEN md.operation_status = '故障' THEN 1 ELSE 0 END) as fault_count,
    SUM(CASE WHEN md.operation_status = '离线' THEN 1 ELSE 0 END) as offline_count,
    ROUND(SUM(CASE WHEN md.operation_status = '正常' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as normal_rate
FROM monitor_device md
JOIN region_info ri ON md.region_id = ri.region_id
GROUP BY ri.region_name, md.device_type;

-- 3. 异常数据统计视图
CREATE OR REPLACE VIEW v_abnormal_data_statistics AS
SELECT
    ri.region_name,
    mi.indicator_name,
    DATE(ed.collection_time) as data_date,
    COUNT(*) as total_records,
    SUM(CASE WHEN ed.is_abnormal = TRUE THEN 1 ELSE 0 END) as abnormal_count,
    ROUND(SUM(CASE WHEN ed.is_abnormal = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as abnormal_rate,
    AVG(ed.monitor_value) as avg_value,
    MIN(ed.monitor_value) as min_value,
    MAX(ed.monitor_value) as max_value
FROM environment_data ed
JOIN region_info ri ON ed.region_id = ri.region_id
JOIN monitor_indicator mi ON ed.indicator_id = mi.indicator_id
WHERE ed.is_abnormal = TRUE
GROUP BY ri.region_name, mi.indicator_name, DATE(ed.collection_time);

-- 创建触发器
-- 1. 自动标记异常数据触发器
DELIMITER //
CREATE TRIGGER IF NOT EXISTS trg_auto_mark_abnormal
BEFORE INSERT ON environment_data
FOR EACH ROW
BEGIN
    DECLARE v_upper DECIMAL(10,4);
    DECLARE v_lower DECIMAL(10,4);

    -- 获取阈值
    SELECT standard_upper, standard_lower
    INTO v_upper, v_lower
    FROM monitor_indicator
    WHERE indicator_id = NEW.indicator_id;

    -- 检查是否异常
    IF NEW.monitor_value > v_upper OR NEW.monitor_value < v_lower THEN
        SET NEW.is_abnormal = TRUE;
        SET NEW.abnormal_reason = CONCAT(
            '监测值 ', NEW.monitor_value, ' ',
            CASE
                WHEN NEW.monitor_value > v_upper THEN '>'
                ELSE '<'
            END,
            ' 阈值范围 [', v_lower, ', ', v_upper, ']'
        );
    END IF;
END//
DELIMITER ;

-- 2. 设备故障自动记录触发器
DELIMITER //
CREATE TRIGGER IF NOT EXISTS trg_device_status_change
BEFORE UPDATE ON monitor_device
FOR EACH ROW
BEGIN
    IF OLD.operation_status != NEW.operation_status AND NEW.operation_status = '故障' THEN
        SET NEW.status_update_time = NOW();
    END IF;
END//
DELIMITER ;

-- 创建存储过程
-- 1. 获取需要校准的设备
DELIMITER //
CREATE PROCEDURE sp_get_devices_need_calibration()
BEGIN
    SELECT
        md.device_id,
        md.device_type,
        ri.region_name,
        md.install_time,
        md.calibration_cycle,
        md.operation_status,
        CASE
            WHEN md.calibration_cycle IS NULL THEN '未设置校准周期'
            WHEN md.install_time IS NULL THEN '安装时间未知'
            WHEN DATE_ADD(
                md.install_time,
                INTERVAL
                CASE
                    WHEN md.calibration_cycle LIKE '%天%' OR md.calibration_cycle LIKE '%日%' THEN
                        CAST(REPLACE(REPLACE(md.calibration_cycle, '天', ''), '日', '') AS UNSIGNED)
                    WHEN md.calibration_cycle LIKE '%月%' THEN
                        CAST(REPLACE(md.calibration_cycle, '月', '') AS UNSIGNED) * 30
                    WHEN md.calibration_cycle LIKE '%年%' THEN
                        CAST(REPLACE(md.calibration_cycle, '年', '') AS UNSIGNED) * 365
                    ELSE CAST(md.calibration_cycle AS UNSIGNED)
                END DAY
            ) <= CURDATE() THEN '逾期未校准'
            WHEN DATE_ADD(
                md.install_time,
                INTERVAL
                CASE
                    WHEN md.calibration_cycle LIKE '%天%' OR md.calibration_cycle LIKE '%日%' THEN
                        CAST(REPLACE(REPLACE(md.calibration_cycle, '天', ''), '日', '') AS UNSIGNED)
                    WHEN md.calibration_cycle LIKE '%月%' THEN
                        CAST(REPLACE(md.calibration_cycle, '月', '') AS UNSIGNED) * 30
                    WHEN md.calibration_cycle LIKE '%年%' THEN
                        CAST(REPLACE(md.calibration_cycle, '年', '') AS UNSIGNED) * 365
                    ELSE CAST(md.calibration_cycle AS UNSIGNED)
                END DAY
            ) <= DATE_ADD(CURDATE(), INTERVAL 7 DAY) THEN '即将到期'
            ELSE '正常'
        END as calibration_status
    FROM monitor_device md
    JOIN region_info ri ON md.region_id = ri.region_id
    WHERE md.operation_status IN ('正常', '离线')
    ORDER BY
        CASE
            WHEN calibration_status = '逾期未校准' THEN 1
            WHEN calibration_status = '即将到期' THEN 2
            WHEN calibration_status = '正常' THEN 3
            ELSE 4
        END,
        md.device_type;
END//
DELIMITER ;

-- 2. 生成环境监测报告
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS sp_generate_env_monitor_report(
    IN p_start_date DATE,
    IN p_end_date DATE
)
BEGIN
    SELECT
        ri.region_name,
        mi.indicator_name,
        mi.unit,
        COUNT(*) as total_records,
        AVG(ed.monitor_value) as avg_value,
        MIN(ed.monitor_value) as min_value,
        MAX(ed.monitor_value) as max_value,
        SUM(CASE WHEN ed.is_abnormal = TRUE THEN 1 ELSE 0 END) as abnormal_count,
        ROUND(SUM(CASE WHEN ed.is_abnormal = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as abnormal_rate,
        SUM(CASE WHEN ed.data_quality = '优' THEN 1 ELSE 0 END) as excellent_count,
        SUM(CASE WHEN ed.data_quality = '良' THEN 1 ELSE 0 END) as good_count,
        SUM(CASE WHEN ed.data_quality = '中' THEN 1 ELSE 0 END) as medium_count,
        SUM(CASE WHEN ed.data_quality = '差' THEN 1 ELSE 0 END) as poor_count
    FROM environment_data ed
    JOIN region_info ri ON ed.region_id = ri.region_id
    JOIN monitor_indicator mi ON ed.indicator_id = mi.indicator_id
    WHERE DATE(ed.collection_time) BETWEEN p_start_date AND p_end_date
    GROUP BY ri.region_name, mi.indicator_name, mi.unit
    ORDER BY ri.region_name, mi.indicator_name;
END//
DELIMITER ;

-- 3. 更新设备运行状态（每小时自动执行）
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS sp_auto_update_device_status()
BEGIN
    -- 更新超过1小时未上报数据的设备为离线
    UPDATE monitor_device md
    SET operation_status = '离线',
        status_update_time = NOW()
    WHERE md.operation_status = '正常'
    AND NOT EXISTS (
        SELECT 1 FROM environment_data ed
        WHERE ed.device_id = md.device_id
        AND ed.collection_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
    )
    AND md.status_update_time <= DATE_SUB(NOW(), INTERVAL 1 HOUR);
END//
DELIMITER ;