-- create_tables.sql
DROP TABLE IF EXISTS monitor_record;
DROP TABLE IF EXISTS habitat_species_relation;
DROP TABLE IF EXISTS habitat_info;
DROP TABLE IF EXISTS sys_user;
DROP TABLE IF EXISTS species_info;


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

-- 6. 系统用户表（支撑记录人关联，文档表4.1简化）
CREATE TABLE IF NOT EXISTS sys_user (
    user_id VARCHAR(20) PRIMARY KEY COMMENT '用户ID/记录人ID（主键）',
    user_name VARCHAR(50) NOT NULL COMMENT '用户名（非空）',
    role VARCHAR(20) NOT NULL COMMENT '角色（非空，如生态监测员）',
    responsible_region VARCHAR(20) COMMENT '负责区域编号（关联区域表）',
    -- 索引：按角色、负责区域检索
    INDEX idx_role (role),
    INDEX idx_responsible_region (responsible_region)
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

