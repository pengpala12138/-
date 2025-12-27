import mysql.connector
from mysql.connector import Error

# -------------------------- 数据库配置（请替换为实际信息）--------------------------
HOST = "192.168.69.97"  # 共享数据库主机地址
USER = "qq"  # 数据库用户名
PASSWORD = "515408"  # 数据库密码
DATABASE = "sjk"  # 数据库名称（需提前创建）
# ------------------------------------------------------------------------------------------

# 数据库连接和查询执行函数
def create_db_connection(host_name, user_name, user_password, db_name):
    """创建数据库连接"""
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
        print(f"✅ 成功连接到 {db_name} 数据库")
    except Error as e:
        print(f"❌ 数据库连接错误: {e}")
    return connection


def execute_query(connection, query):
    """执行SQL查询"""
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print(f"  ✅ SQL执行成功")
    except Error as e:
        print(f"  ❌ SQL执行错误: {e}")
        cursor.close()
        raise
    cursor.close()

# 1. 科研项目信息表（research_project）
create_project_table = """
CREATE TABLE IF NOT EXISTS research_project (
    project_id VARCHAR(30) PRIMARY KEY COMMENT '项目编号（主键）',
    project_name VARCHAR(200) NOT NULL COMMENT '项目名称（非空）',
    leader_id VARCHAR(30) NOT NULL COMMENT '负责人ID',
    apply_unit VARCHAR(100) NOT NULL COMMENT '申请单位（非空）',
    approval_time DATE NOT NULL COMMENT '批准时间（非空）',
    conclusion_time DATE COMMENT '结题时间',
    project_status VARCHAR(20) NOT NULL COMMENT '项目状态（非空）',
    research_field VARCHAR(50) NOT NULL COMMENT '研究领域（非空）',
    responsible_region VARCHAR(20) NOT NULL COMMENT '负责区域编号',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    -- 约束
    CHECK (project_status IN ('在研', '已结题', '暂停'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT '科研项目信息表：存储科研项目基础信息';
"""

# 2. 科研数据采集记录表（research_data_collection）
create_collection_table = """
CREATE TABLE IF NOT EXISTS research_data_collection (
    collection_id VARCHAR(30) PRIMARY KEY COMMENT '采集记录编号（主键）',
    project_id VARCHAR(30) NOT NULL COMMENT '项目编号（关联research_project）',
    collector_id VARCHAR(30) NOT NULL COMMENT '采集员ID',
    region_id VARCHAR(20) NOT NULL COMMENT '区域编号',
    collection_time TIMESTAMP NOT NULL COMMENT '采集时间（非空）',
    collection_content TEXT NOT NULL COMMENT '采集内容（非空）',
    data_source VARCHAR(50) NOT NULL COMMENT '数据来源（非空）',
    data_quality VARCHAR(20) DEFAULT '合格' COMMENT '数据质量',
    verification_status VARCHAR(20) DEFAULT '待审核' COMMENT '审核状态',
    verification_notes TEXT COMMENT '审核备注',
    verification_time TIMESTAMP COMMENT '审核时间',
    verifier_id VARCHAR(30) COMMENT '审核人ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    -- 约束
    CHECK (data_source IN ('实地采集', '系统调用')),
    CHECK (data_quality IN ('优秀', '合格', '不合格')),
    CHECK (verification_status IN ('待审核', '已通过', '已驳回')),
    -- 外键约束
    FOREIGN KEY (project_id) REFERENCES research_project(project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT '科研数据采集记录表：存储科研数据采集记录信息';
"""

# 3. 科研成果信息表（research_achievement）
create_achievement_table = """
CREATE TABLE IF NOT EXISTS research_achievement (
    achievement_id VARCHAR(30) PRIMARY KEY COMMENT '成果编号（主键）',
    project_id VARCHAR(30) NOT NULL COMMENT '项目编号（关联research_project）',
    achievement_type VARCHAR(50) NOT NULL COMMENT '成果类型（非空）',
    achievement_name VARCHAR(200) NOT NULL COMMENT '成果名称（非空）',
    publish_time DATE NOT NULL COMMENT '发表时间（非空）',
    share_permission VARCHAR(20) NOT NULL COMMENT '共享权限（非空）',
    author_id VARCHAR(30) NOT NULL COMMENT '作者ID',
    file_path VARCHAR(200) COMMENT '文件路径',
    file_size BIGINT COMMENT '文件大小（字节）',
    file_format VARCHAR(20) COMMENT '文件格式',
    download_count INT DEFAULT 0 COMMENT '下载次数',
    citation_count INT DEFAULT 0 COMMENT '引用次数',
    is_published TINYINT DEFAULT 1 COMMENT '是否公开：1=是，0=否',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    -- 约束
    CHECK (achievement_type IN ('论文', '报告', '专利', '软件著作权', '技术标准')),
    CHECK (share_permission IN ('公开', '内部共享', '保密')),
    CHECK (file_format IN ('PDF', 'DOC', 'DOCX', 'PPT', 'PPTX', '其他')),
    -- 外键约束
    FOREIGN KEY (project_id) REFERENCES research_project(project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT '科研成果信息表：存储科研成果信息';
"""

# 4. 科研项目-共享成果关联表（project_achievement_share）
create_share_rel_table = """
CREATE TABLE IF NOT EXISTS project_achievement_share (
    share_id VARCHAR(30) PRIMARY KEY COMMENT '共享记录编号（主键）',
    project_id VARCHAR(30) NOT NULL COMMENT '项目编号（关联research_project）',
    achievement_id VARCHAR(30) NOT NULL COMMENT '成果编号（关联research_achievement）',
    authorizer_id VARCHAR(30) NOT NULL COMMENT '授权人ID',
    recipient_id VARCHAR(30) NOT NULL COMMENT '接收人ID',
    share_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '共享时间（非空）',
    share_purpose VARCHAR(200) NOT NULL COMMENT '共享目的（非空）',
    permission_level VARCHAR(20) NOT NULL COMMENT '权限等级',
    expire_time TIMESTAMP COMMENT '过期时间',
    is_active TINYINT DEFAULT 1 COMMENT '是否有效：1=是，0=否',
    share_notes TEXT COMMENT '共享备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    -- 约束
    CHECK (permission_level IN ('只读', '下载', '编辑', '管理')),
    -- 外键约束
    FOREIGN KEY (project_id) REFERENCES research_project(project_id),
    FOREIGN KEY (achievement_id) REFERENCES research_achievement(achievement_id),
    -- 唯一约束
    UNIQUE KEY uk_project_achievement (project_id, achievement_id, recipient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT '科研项目-共享成果关联表：存储成果共享记录';
"""

# 5. 科研采集记录-环境监测数据关联表（collection_monitor_data_rel）
create_data_rel_table = """
CREATE TABLE IF NOT EXISTS collection_monitor_data_rel (
    relation_id VARCHAR(30) PRIMARY KEY COMMENT '关联记录编号（主键）',
    collection_id VARCHAR(30) NOT NULL COMMENT '采集记录编号（关联research_data_collection）',
    monitor_data_id VARCHAR(30) NOT NULL COMMENT '监测数据编号',
    data_type VARCHAR(50) NOT NULL COMMENT '数据类型（非空）',
    data_category VARCHAR(50) NOT NULL COMMENT '数据分类',
    association_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '关联时间',
    association_reason VARCHAR(200) COMMENT '关联原因',
    data_volume DECIMAL(10,2) COMMENT '数据量（MB）',
    data_format VARCHAR(20) COMMENT '数据格式',
    is_verified TINYINT DEFAULT 0 COMMENT '是否已验证：1=是，0=否',
    verification_time TIMESTAMP COMMENT '验证时间',
    verifier_id VARCHAR(30) COMMENT '验证人ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    -- 约束
    CHECK (data_type IN ('生物多样性监测数据', '生态环境监测数据', '气象监测数据', '水质监测数据', '土壤监测数据')),
    CHECK (data_category IN ('原始数据', '处理数据', '分析数据', '报告数据')),
    CHECK (data_format IN ('CSV', 'Excel', 'JSON', 'XML', '数据库', '其他')),
    -- 外键约束
    FOREIGN KEY (collection_id) REFERENCES research_data_collection(collection_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT '科研采集记录-环境监测数据关联表：存储采集记录与监测数据关联关系';
"""

# ==============================
# 索引创建语句（优化查询性能）
# ==============================

# 科研项目表索引
create_project_indexes = [
    "CREATE INDEX idx_project_status ON research_project(project_status);",
    "CREATE INDEX idx_project_leader ON research_project(leader_id);",
    "CREATE INDEX idx_project_region ON research_project(responsible_region);",
    "CREATE INDEX idx_approval_time ON research_project(approval_time);",
    "CREATE INDEX idx_research_field ON research_project(research_field);"
]

# 采集记录表索引
create_collection_indexes = [
    "CREATE INDEX idx_collection_project ON research_data_collection(project_id);",
    "CREATE INDEX idx_collection_collector ON research_data_collection(collector_id);",
    "CREATE INDEX idx_collection_region ON research_data_collection(region_id);",
    "CREATE INDEX idx_collection_time ON research_data_collection(collection_time);",
    "CREATE INDEX idx_data_source ON research_data_collection(data_source);",
    "CREATE INDEX idx_verification_status ON research_data_collection(verification_status);",
    "CREATE INDEX idx_verifier ON research_data_collection(verifier_id);"
]

# 科研成果表索引
create_achievement_indexes = [
    "CREATE INDEX idx_achievement_project ON research_achievement(project_id);",
    "CREATE INDEX idx_achievement_type ON research_achievement(achievement_type);",
    "CREATE INDEX idx_achievement_author ON research_achievement(author_id);",
    "CREATE INDEX idx_publish_time ON research_achievement(publish_time);",
    "CREATE INDEX idx_share_permission ON research_achievement(share_permission);",
    "CREATE INDEX idx_is_published ON research_achievement(is_published);"
]

# 共享关联表索引
create_share_indexes = [
    "CREATE INDEX idx_share_project ON project_achievement_share(project_id);",
    "CREATE INDEX idx_share_achievement ON project_achievement_share(achievement_id);",
    "CREATE INDEX idx_share_authorizer ON project_achievement_share(authorizer_id);",
    "CREATE INDEX idx_share_recipient ON project_achievement_share(recipient_id);",
    "CREATE INDEX idx_share_time ON project_achievement_share(share_time);",
    "CREATE INDEX idx_is_active ON project_achievement_share(is_active);"
]

# 监测数据关联表索引
create_data_rel_indexes = [
    "CREATE INDEX idx_relation_collection ON collection_monitor_data_rel(collection_id);",
    "CREATE INDEX idx_monitor_data_id ON collection_monitor_data_rel(monitor_data_id);",
    "CREATE INDEX idx_data_type ON collection_monitor_data_rel(data_type);",
    "CREATE INDEX idx_data_category ON collection_monitor_data_rel(data_category);",
    "CREATE INDEX idx_is_verified ON collection_monitor_data_rel(is_verified);"
]

# ==============================
# 视图创建语句（常用查询视图）
# ==============================

# 视图1：项目综合信息视图
create_project_summary_view = """
CREATE OR REPLACE VIEW v_project_summary AS
SELECT 
    rp.project_id,
    rp.project_name,
    rp.project_status,
    rp.research_field,
    rp.approval_time,
    rp.conclusion_time,
    COUNT(DISTINCT rdc.collection_id) as collection_count,
    COUNT(DISTINCT ra.achievement_id) as achievement_count,
    COUNT(DISTINCT pas.share_id) as share_count
FROM research_project rp
LEFT JOIN research_data_collection rdc ON rp.project_id = rdc.project_id
LEFT JOIN research_achievement ra ON rp.project_id = ra.project_id
LEFT JOIN project_achievement_share pas ON rp.project_id = pas.project_id
GROUP BY rp.project_id, rp.project_name, rp.project_status, rp.research_field, 
         rp.approval_time, rp.conclusion_time;
"""

# 视图2：采集活动详情视图
create_collection_detail_view = """
CREATE OR REPLACE VIEW v_collection_detail AS
SELECT 
    rdc.collection_id,
    rdc.collection_time,
    rdc.collection_content,
    rdc.data_source,
    rdc.data_quality,
    rdc.verification_status,
    rp.project_name,
    rp.project_status
FROM research_data_collection rdc
JOIN research_project rp ON rdc.project_id = rp.project_id;
"""

# 视图3：科研成果统计视图
create_achievement_statistics_view = """
CREATE OR REPLACE VIEW v_achievement_statistics AS
SELECT 
    ra.achievement_type,
    ra.share_permission,
    YEAR(ra.publish_time) as publish_year,
    MONTH(ra.publish_time) as publish_month,
    COUNT(*) as achievement_count,
    SUM(ra.download_count) as total_downloads,
    SUM(ra.citation_count) as total_citations,
    COUNT(DISTINCT ra.author_id) as author_count
FROM research_achievement ra
GROUP BY ra.achievement_type, ra.share_permission, 
         YEAR(ra.publish_time), MONTH(ra.publish_time);
"""

# 视图4：科研成果使用视图
create_achievement_usage_view = """
CREATE OR REPLACE VIEW v_achievement_usage AS
SELECT 
    ra.achievement_id,
    ra.achievement_name,
    ra.publish_time,
    ra.share_permission,
    ra.download_count,
    ra.citation_count,
    COUNT(DISTINCT pas.share_id) as share_count
FROM research_achievement ra
LEFT JOIN project_achievement_share pas ON ra.achievement_id = pas.achievement_id
GROUP BY ra.achievement_id, ra.achievement_name, ra.publish_time, ra.share_permission,
         ra.download_count, ra.citation_count;
"""

# 视图5：共享成果使用视图
create_share_usage_view = """
CREATE OR REPLACE VIEW v_share_usage AS
SELECT 
    pas.share_id,
    pas.project_id,
    pas.achievement_id,
    pas.permission_level,
    pas.is_active,
    pas.share_time,
    pas.expire_time,
    ra.achievement_name,
    ra.share_permission,
    COUNT(sol.log_id) as operation_count
FROM project_achievement_share pas
JOIN research_achievement ra ON pas.achievement_id = ra.achievement_id
LEFT JOIN share_operation_log sol ON pas.share_id = sol.share_id
GROUP BY pas.share_id, pas.project_id, pas.achievement_id, pas.permission_level,
         pas.is_active, pas.share_time, pas.expire_time, ra.achievement_name, ra.share_permission;
"""

# ==============================
# 存储过程和触发器
# ==============================

# 存储过程：自动更新项目状态
create_update_project_status_proc = """
CREATE PROCEDURE IF NOT EXISTS update_project_status()
BEGIN
    -- 自动将已过结题时间且状态为'在研'的项目标记为'已结题'
    UPDATE research_project
    SET project_status = '已结题',
        updated_at = CURRENT_TIMESTAMP
    WHERE project_status = '在研' AND conclusion_time <= CURRENT_DATE;
    
    -- 输出更新的记录数
    SELECT ROW_COUNT() AS updated_projects;
END;
"""

# 触发器：记录成果共享操作日志
create_share_log_trigger = """
CREATE TABLE IF NOT EXISTS share_operation_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    share_id VARCHAR(30) NOT NULL COMMENT '共享记录编号',
    authorizer_id VARCHAR(30) NOT NULL COMMENT '授权人ID',
    recipient_id VARCHAR(30) NOT NULL COMMENT '接收人ID',
    operation_type VARCHAR(20) NOT NULL COMMENT '操作类型（创建/更新/删除）',
    operation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    ip_address VARCHAR(45) COMMENT '操作IP地址',
    FOREIGN KEY (share_id) REFERENCES project_achievement_share(share_id) ON DELETE CASCADE,
    FOREIGN KEY (authorizer_id) REFERENCES sys_user(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (recipient_id) REFERENCES sys_user(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT '成果共享操作日志表';

CREATE TRIGGER IF NOT EXISTS trg_share_after_insert
AFTER INSERT ON project_achievement_share
FOR EACH ROW
BEGIN
    INSERT INTO share_operation_log (share_id, authorizer_id, recipient_id, operation_type)
    VALUES (NEW.share_id, NEW.authorizer_id, NEW.recipient_id, '创建');
END;

CREATE TRIGGER IF NOT EXISTS trg_share_after_update
AFTER UPDATE ON project_achievement_share
FOR EACH ROW
BEGIN
    INSERT INTO share_operation_log (share_id, authorizer_id, recipient_id, operation_type)
    VALUES (NEW.share_id, NEW.authorizer_id, NEW.recipient_id, '更新');
END;

CREATE TRIGGER IF NOT EXISTS trg_share_after_delete
AFTER DELETE ON project_achievement_share
FOR EACH ROW
BEGIN
    INSERT INTO share_operation_log (share_id, authorizer_id, recipient_id, operation_type)
    VALUES (OLD.share_id, OLD.authorizer_id, OLD.recipient_id, '删除');
END;
"""

# ==============================
# 执行函数
# ==============================

def create_research_tables(create_user_contribution_view=None):
    """创建科研相关数据表"""

    # 1. 连接数据库
    db_conn = create_db_connection(HOST, USER, PASSWORD, DATABASE)

    if not db_conn:
        print("❌ 数据库连接失败！")
        return False

    try:
        print("🔗 数据库连接成功，开始创建科研数据表...")

        # 2. 依次创建表（按依赖顺序）
        tables = [
            ("科研项目信息表", create_project_table),
            ("科研数据采集记录表", create_collection_table),
            ("科研成果信息表", create_achievement_table),
            ("项目-成果共享关联表", create_share_rel_table),
            ("采集-监测数据关联表", create_data_rel_table),
            ("共享操作日志表", """CREATE TABLE IF NOT EXISTS share_operation_log (
                log_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
                share_id VARCHAR(30) NOT NULL COMMENT '共享记录编号',
                authorizer_id VARCHAR(30) NOT NULL COMMENT '授权人ID',
                recipient_id VARCHAR(30) NOT NULL COMMENT '接收人ID',
                operation_type VARCHAR(20) NOT NULL COMMENT '操作类型（创建/更新/删除）',
                operation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
                ip_address VARCHAR(45) COMMENT '操作IP地址',
                FOREIGN KEY (share_id) REFERENCES project_achievement_share(share_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT '成果共享操作日志表';""")
        ]

        for table_name, table_sql in tables:
            print(f"📊 正在创建 {table_name}...")
            execute_query(db_conn, table_sql)
            print(f"  ✅ {table_name} 创建成功")

        print("\n📈 开始创建索引...")

        # 3. 创建所有索引
        all_indexes = [
            ("科研项目表索引", create_project_indexes),
            ("采集记录表索引", create_collection_indexes),
            ("科研成果表索引", create_achievement_indexes),
            ("共享关联表索引", create_share_indexes),
            ("监测数据关联表索引", create_data_rel_indexes)
        ]

        for index_name, index_list in all_indexes:
            print(f"  🔍 正在创建 {index_name}...")
            for index_sql in index_list:
                execute_query(db_conn, index_sql)
            print(f"    ✅ {index_name} 创建成功")

        print("\n👁️  开始创建视图...")

        # 4. 创建视图
        views = [
            ("项目综合信息视图", create_project_summary_view),
            ("采集活动详情视图", create_collection_detail_view),
            ("科研成果统计视图", create_achievement_statistics_view),
            ("用户贡献统计视图", create_user_contribution_view),
            ("共享成果使用视图", create_share_usage_view)
        ]

        for view_name, view_sql in views:
            print(f"  👁️  正在创建 {view_name}...")
            execute_query(db_conn, view_sql)
            print(f"    ✅ {view_name} 创建成功")

        print("\n⚙️  开始创建存储过程和触发器...")
        
        # 5. 创建存储过程
        print("  📦 正在创建自动更新项目状态存储过程...")
        execute_query(db_conn, create_update_project_status_proc)
        print("    ✅ 存储过程创建成功")
        
        # 6. 创建触发器
        print("  ⚡ 正在创建成果共享操作日志触发器...")
        execute_query(db_conn, """CREATE TRIGGER IF NOT EXISTS trg_share_after_insert
AFTER INSERT ON project_achievement_share
FOR EACH ROW
BEGIN
    INSERT INTO share_operation_log (share_id, authorizer_id, recipient_id, operation_type)
    VALUES (NEW.share_id, NEW.authorizer_id, NEW.recipient_id, '创建');
END;""")
        execute_query(db_conn, """CREATE TRIGGER IF NOT EXISTS trg_share_after_update
AFTER UPDATE ON project_achievement_share
FOR EACH ROW
BEGIN
    INSERT INTO share_operation_log (share_id, authorizer_id, recipient_id, operation_type)
    VALUES (NEW.share_id, NEW.authorizer_id, NEW.recipient_id, '更新');
END;""")
        execute_query(db_conn, """CREATE TRIGGER IF NOT EXISTS trg_share_after_delete
AFTER DELETE ON project_achievement_share
FOR EACH ROW
BEGIN
    INSERT INTO share_operation_log (share_id, authorizer_id, recipient_id, operation_type)
    VALUES (OLD.share_id, OLD.authorizer_id, OLD.recipient_id, '删除');
END;""")
        print("    ✅ 触发器创建成功")

        print("\n" + "=" * 50)
        print("🎉 科研数据表创建完成！")
        print("=" * 50)

        # 7. 输出数据备份与恢复策略
        print("\n📋 数据备份与恢复策略")
        print("=" * 50)
        print("1. 备份策略：")
        print("   - 每日增量备份：每天凌晨2点执行，使用mysqldump --single-transaction --flush-logs --master-data=2 --incremental backup")
        print("   - 每周全量备份：每周日凌晨1点执行，使用mysqldump --single-transaction --all-databases")
        print("   - 备份存储路径：/backup/mysql/")
        print("     - 全量备份：/backup/mysql/full/YYYY-MM-DD/")
        print("     - 增量备份：/backup/mysql/incremental/YYYY-MM-DD/")
        print("   - 备份保留期限：全量备份保留4周，增量备份保留1周")
        
        print("\n2. 恢复流程：")
        print("   - 全量恢复：")
        print("     1. 停止MySQL服务")
        print("     2. 清空数据目录")
        print("     3. 启动MySQL服务")
        print("     4. 执行：mysql < /backup/mysql/full/YYYY-MM-DD/full_backup.sql")
        print("   - 增量恢复：")
        print("     1. 先执行全量恢复到最近的全量备份点")
        print("     2. 依次执行增量备份文件：mysql < /backup/mysql/incremental/YYYY-MM-DD/incremental_1.sql")
        print("     3. 重复步骤2直到所有增量备份恢复完成")
        
        print("\n3. 自动备份脚本示例：")
        print("   - 全量备份脚本：/backup/scripts/full_backup.sh")
        print("   - 增量备份脚本：/backup/scripts/incremental_backup.sh")
        print("   - 使用crontab定时执行")
        
        print("\n4. 数据验证：")
        print("   - 备份后自动验证：使用mysqlcheck验证备份文件完整性")
        print("   - 定期恢复测试：每月进行一次恢复测试，确保备份可用")

        return True

    except Exception as e:
        print(f"❌ 创建过程中发生错误: {str(e)}")
        return False

    finally:
        # 关闭连接
        if db_conn:
            db_conn.close()
            print("\n🔌 数据库连接已关闭")


# ==============================
# 主执行程序
# ==============================

if __name__ == "__main__":
    print("🚀 开始执行科研数据表创建脚本...")
    print("=" * 50)

    success = create_research_tables()

    if success:
        print("\n✅ 科研数据表创建完成！")
        print("\n📋 创建的表清单：")
        print("  1. research_project - 科研项目信息表")
        print("  2. research_data_collection - 科研数据采集记录表")
        print("  3. research_achievement - 科研成果信息表")
        print("  4. project_achievement_share - 项目-成果共享关联表")
        print("  5. collection_monitor_data_rel - 采集-监测数据关联表")
        print("  6. share_operation_log - 共享操作日志表")
        print("\n📋 创建的视图清单：")
        print("  1. v_project_summary - 项目综合信息视图")
        print("  2. v_collection_detail - 采集活动详情视图")
        print("  3. v_achievement_statistics - 科研成果统计视图")
        print("  4. v_user_contribution - 用户贡献统计视图")
        print("  5. v_share_usage - 共享成果使用视图")
        print("\n📋 存储过程和触发器：")
        print("  1. update_project_status - 自动更新项目状态存储过程")
        print("  2. trg_share_after_insert - 成果共享创建触发器")
        print("  3. trg_share_after_update - 成果共享更新触发器")
        print("  4. trg_share_after_delete - 成果共享删除触发器")
    else:
        print("\n❌ 科研数据表创建失败！")
