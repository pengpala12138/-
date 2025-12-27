-- create_tables.sql

-- 1. 区域信息表（支撑栖息地表关联，文档表2.2）
CREATE TABLE IF NOT EXISTS region_info (
    region_id VARCHAR(20) PRIMARY KEY COMMENT '区域编号（主键）',
    region_name VARCHAR(50) NOT NULL COMMENT '区域名称（非空）'
) COMMENT '区域信息表：存储监测区域基础信息';

-- 2. 物种信息表（文档表1.1，拆分分类字段）
CREATE TABLE IF NOT EXISTS species_info (
    species_id VARCHAR(20) PRIMARY KEY COMMENT '物种编号（唯一标识，主键）',
    chinese_name VARCHAR(100) NOT NULL COMMENT '物种中文名称（非空）',
    latin_name VARCHAR(200) NOT NULL COMMENT '物种拉丁名（非空）',
    kingdom VARCHAR(50) NOT NULL COMMENT '物种分类-界（非空）',
    phylum VARCHAR(50) NOT NULL COMMENT '物种分类-门（非空）',
    class VARCHAR(50) NOT NULL COMMENT '物种分类-纲（非空）',
    order_name VARCHAR(50) NOT NULL COMMENT '物种分类-目（非空，避免关键字）',
    family VARCHAR(50) NOT NULL COMMENT '物种分类-科（非空）',
    genus VARCHAR(50) NOT NULL COMMENT '物种分类-属（非空）',
    species_name VARCHAR(50) NOT NULL COMMENT '物种分类-种（非空）',
    protection_level VARCHAR(20) NOT NULL COMMENT '保护级别（非空）',
    living_habits TEXT NOT NULL COMMENT '生存习性（非空）',
    distribution_desc TEXT NOT NULL COMMENT '分布范围描述（非空）',
    -- 检查约束：保护级别枚举（文档表1.1约束）
    CONSTRAINT ck_protection_level CHECK (protection_level IN ('国家一级', '国家二级', '无')),
    -- 索引：按保护级别、物种名称检索（文档索引设计表1.1）
    INDEX idx_protection_level (protection_level),
    UNIQUE INDEX idx_species_name (chinese_name, latin_name)
) COMMENT '物种信息表：存储物种基础信息及分类体系';

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

-- 3. 栖息地表（文档表1.3，关联区域+多物种）
CREATE TABLE IF NOT EXISTS habitat_info (
    habitat_id VARCHAR(20) PRIMARY KEY COMMENT '栖息地编号（主键）',
    region_id VARCHAR(20) NOT NULL COMMENT '区域编号（外键，关联区域表）',
    ecological_type VARCHAR(50) NOT NULL COMMENT '生态类型（非空，如森林/湿地）',
    area DECIMAL(10,2) NOT NULL COMMENT '面积（公顷，非空）',
    core_protection TEXT NOT NULL COMMENT '核心保护范围（非空）',
    suitability_score INT NOT NULL COMMENT '环境适宜性评分（非空）',
    -- 外键约束：级联删除（文档表1.4业务规则）
    FOREIGN KEY (region_id) REFERENCES region_info(region_id) ON DELETE CASCADE,
    -- 检查约束：面积>0，评分1-10（文档表1.3约束）
    CONSTRAINT ck_habitat_area CHECK (area > 0),
    CONSTRAINT ck_suitability_score CHECK (suitability_score BETWEEN 1 AND 10),
    -- 索引：按生态类型、评分检索（文档索引设计表1.3）
    INDEX idx_ecological_type (ecological_type),
    INDEX idx_suitability_score (suitability_score)
) COMMENT '栖息地表：存储栖息地基础信息及环境评估数据';

-- 4. 栖息地-物种关联表（多对多，文档表1.4）
CREATE TABLE IF NOT EXISTS habitat_species_relation (
    habitat_id VARCHAR(20) NOT NULL COMMENT '栖息地编号（外键）',
    species_id VARCHAR(20) NOT NULL COMMENT '物种编号（外键）',
    is_main TINYINT DEFAULT 1 COMMENT '是否主要物种：1=是，0=否',
    -- 复合主键：避免重复关联（文档表1.4业务规则）
    PRIMARY KEY (habitat_id, species_id),
    -- 外键约束：级联删除（文档表1.4业务规则）
    FOREIGN KEY (habitat_id) REFERENCES habitat_info(habitat_id) ON DELETE CASCADE,
    FOREIGN KEY (species_id) REFERENCES species_info(species_id) ON DELETE CASCADE,
    -- 索引：反向查询（物种→栖息地，文档索引设计表1.4）
    INDEX idx_species_habitat (species_id, habitat_id)
) COMMENT '栖息地-物种关联表：实现多对多关联，标记主要物种';

-- 6. 系统用户表
DROP TABLE IF EXISTS monitor_record;
DROP TABLE IF EXISTS sys_user;
CREATE TABLE IF NOT EXISTS sys_user (
    user_id VARCHAR(30) NOT NULL COMMENT '用户ID/记录人ID（主键）',
    user_name VARCHAR(50) NOT NULL COMMENT '用户名（非空）',
    password_hash VARCHAR(128) NOT NULL COMMENT '密码哈希（SHA-256加密）',
    role VARCHAR(20) NOT NULL COMMENT '角色（非空，如生态监测员/数据分析师/数据录入员/监测主管）',
    responsible_region VARCHAR(20) COMMENT '负责区域编号（关联区域表）',
    login_failed INT DEFAULT 0 COMMENT '登录失败次数',
    is_locked TINYINT DEFAULT 0 COMMENT '是否锁定：1=是，0=否',
    last_login DATETIME COMMENT '最后登录时间',
    session_expire DATETIME COMMENT '会话过期时间',
    PRIMARY KEY (user_id),
    -- 索引
    INDEX idx_role (role),
    INDEX idx_responsible_region (responsible_region),
    INDEX idx_is_locked (is_locked)
) COMMENT '系统用户表：存储生态监测员、分析师等用户信息';

-- 7. 监测记录表（核心业务表，文档表1.2）
CREATE TABLE IF NOT EXISTS monitor_record (
    record_id VARCHAR(30) PRIMARY KEY COMMENT '记录编号（主键）',
    species_id VARCHAR(20) NOT NULL COMMENT '物种编号（外键，关联物种表）',
    device_id VARCHAR(20) NOT NULL COMMENT '监测设备编号（外键，关联设备表）',
    monitor_time DATETIME NOT NULL COMMENT '监测时间（非空）',
    longitude DECIMAL(10,6) COMMENT '监测地点-经度',
    latitude DECIMAL(10,6) COMMENT '监测地点-纬度',
    monitor_location VARCHAR(100) NOT NULL COMMENT '监测地点（非空，经纬度文本描述）',
    monitor_method VARCHAR(20) NOT NULL COMMENT '监测方式（非空）',
    monitor_content VARCHAR(255) COMMENT '监测内容（影像路径/数量统计/行为描述）',
    recorder_id VARCHAR(20) NOT NULL COMMENT '记录人ID（外键，关联用户表）',
    data_status VARCHAR(20) NOT NULL DEFAULT '待核实' COMMENT '数据状态（非空，默认待核实）',
    analysis_conclusion TEXT COMMENT '分析结论（分析师补充）',
    verify_time DATETIME COMMENT '审核时间',
    -- 外键约束：级联删除（文档表1.4业务规则）
    FOREIGN KEY (species_id) REFERENCES species_info(species_id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES monitor_device(device_id) ON DELETE CASCADE,
    FOREIGN KEY (recorder_id) REFERENCES sys_user(user_id) ON DELETE CASCADE,
    -- 检查约束：监测方式、数据状态枚举（文档表1.2约束）
    CONSTRAINT ck_monitor_method CHECK (monitor_method IN ('红外相机', '人工巡查', '无人机')),
    CONSTRAINT ck_data_status CHECK (data_status IN ('有效', '待核实')),
    -- 索引：高频查询场景（文档索引设计表1.2）
    INDEX idx_species_time (species_id, monitor_time),
    INDEX idx_device_id (device_id),
    INDEX idx_data_status (data_status),
    INDEX idx_recorder_time (recorder_id, monitor_time)
) COMMENT '监测记录表：存储物种监测的核心业务数据';



-- ===================== 视图定义（满足不同角色需求） =====================
-- 视图1：物种保护级别统计视图（管理员/分析师)
DROP VIEW IF EXISTS v_species_protection_stat;
CREATE VIEW v_species_protection_stat AS
SELECT
    protection_level,
    COUNT(*) AS species_count,
    GROUP_CONCAT(chinese_name SEPARATOR ',') AS species_list,
    GROUP_CONCAT(DISTINCT kingdom) AS kingdom_list
FROM species_info
GROUP BY protection_level
ORDER BY
    CASE protection_level
        WHEN '国家一级' THEN 1
        WHEN '国家二级' THEN 2
        WHEN '无' THEN 3
    END;

-- 视图2：栖息地适宜性分析视图（生态监测员）
DROP VIEW IF EXISTS v_habitat_suitability_analysis;
CREATE VIEW v_habitat_suitability_analysis AS
SELECT
    h.habitat_id,
    r.region_name,
    h.ecological_type,
    h.area,
    h.suitability_score,
    COUNT(hs.species_id) AS related_species_num,
    GROUP_CONCAT(CASE WHEN hs.is_main=1 THEN s.chinese_name ELSE NULL END SEPARATOR ',') AS main_species
FROM habitat_info h
LEFT JOIN region_info r ON h.region_id = r.region_id
LEFT JOIN habitat_species_relation hs ON h.habitat_id = hs.habitat_id
LEFT JOIN species_info s ON hs.species_id = s.species_id
GROUP BY h.habitat_id, r.region_name, h.ecological_type, h.area, h.suitability_score;

-- 视图3：监测数据有效性汇总视图（数据分析师）
DROP VIEW IF EXISTS v_monitor_data_validity;
CREATE VIEW v_monitor_data_validity AS
SELECT
    r.region_name,
    m.monitor_method,
    COUNT(*) AS total_records,
    SUM(CASE WHEN m.data_status = '有效' THEN 1 ELSE 0 END) AS valid_count,
    ROUND(SUM(CASE WHEN m.data_status = '有效' THEN 1 ELSE 0 END)/COUNT(*)*100, 2) AS valid_rate,
    AVG(TIMESTAMPDIFF(HOUR, m.monitor_time, m.verify_time)) AS avg_verify_hours
FROM monitor_record m
LEFT JOIN monitor_device d ON m.device_id = d.device_id
LEFT JOIN region_info r ON d.region_id = r.region_id
WHERE m.data_status = '有效'
GROUP BY r.region_name, m.monitor_method;

-- 视图4：设备运行状态及监测覆盖率视图（设备管理员）
DROP VIEW IF EXISTS v_device_monitor_coverage;
CREATE VIEW v_device_monitor_coverage AS
SELECT
    d.device_id,
    d.device_type,
    r.region_name,
    d.operation_status,
    COUNT(m.record_id) AS monitor_count,
    DATE_FORMAT(d.status_update_time, '%Y-%m-%d') AS last_status_update
FROM monitor_device d
LEFT JOIN region_info r ON d.region_id = r.region_id
LEFT JOIN monitor_record m ON d.device_id = m.device_id
GROUP BY d.device_id, d.device_type, r.region_name, d.operation_status, d.status_update_time;

-- 视图5：待核实数据详情视图（数据分析师）
DROP VIEW IF EXISTS v_pending_record_detail;
CREATE VIEW v_pending_record_detail AS
SELECT
    m.record_id,
    s.chinese_name AS species_name,
    s.protection_level,
    d.device_type,
    u.user_name AS recorder_name,
    u.role,
    m.monitor_time,
    m.monitor_location,
    m.monitor_content
FROM monitor_record m
LEFT JOIN species_info s ON m.species_id = s.species_id
LEFT JOIN monitor_device d ON m.device_id = d.device_id
LEFT JOIN sys_user u ON m.recorder_id = u.user_id
WHERE m.data_status = '待核实'
ORDER BY m.monitor_time DESC;
