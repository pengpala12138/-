from pro.utils.db_connection import create_db_connection, execute_query

# -------------------------- 数据库配置（请替换为实际信息）--------------------------
HOST = "192.168.43.76"  # 共享数据库主机地址
USER = "qq"  # 数据库用户名
PASSWORD = "515408"  # 数据库密码
DATABASE = "sjk"  # 数据库名称（需提前创建）
# ------------------------------------------------------------------------------------------

# 1. 科研项目信息表（research_project）
create_project_table = """
CREATE TABLE IF NOT EXISTS research_project (
    project_id VARCHAR(30) PRIMARY KEY,
    project_name VARCHAR(200) NOT NULL,
    leader_id VARCHAR(20) NOT NULL,
    apply_unit VARCHAR(100) NOT NULL,
    approval_time DATE NOT NULL,
    conclusion_time DATE,
    project_status VARCHAR(20) NOT NULL,
    research_field VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CHECK (project_status IN ('在研', '已结题', '暂停'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 2. 科研数据采集记录表（research_data_collection）
create_collection_table = """
CREATE TABLE IF NOT EXISTS research_data_collection (
    collection_id VARCHAR(30) PRIMARY KEY,
    project_id VARCHAR(30) NOT NULL,
    collector_id VARCHAR(20) NOT NULL,
    collection_time TIMESTAMP NOT NULL,
    collection_content TEXT NOT NULL,
    data_source VARCHAR(50) NOT NULL,
    region_id VARCHAR(20),
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES research_project(project_id) ON DELETE CASCADE,
    CHECK (data_source IN ('实地采集', '系统调用'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 3. 科研成果信息表（research_achievement）
create_achievement_table = """
CREATE TABLE IF NOT EXISTS research_achievement (
    achievement_id VARCHAR(30) PRIMARY KEY,
    project_id VARCHAR(30) NOT NULL,
    achievement_type VARCHAR(50) NOT NULL,
    achievement_name VARCHAR(200) NOT NULL,
    publish_time DATE NOT NULL,
    share_permission VARCHAR(20) NOT NULL,
    file_path VARCHAR(200),
    file_size BIGINT,
    download_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES research_project(project_id) ON DELETE CASCADE,
    CHECK (achievement_type IN ('论文', '报告', '专利')),
    CHECK (share_permission IN ('公开', '内部共享', '保密'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 4. 科研项目-共享成果关联表（project_achievement_share）
create_share_rel_table = """
CREATE TABLE IF NOT EXISTS project_achievement_share (
    project_id VARCHAR(30) NOT NULL,
    achievement_id VARCHAR(30) NOT NULL,
    share_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    authorizer_id VARCHAR(20) NOT NULL,
    share_purpose VARCHAR(100),
    expire_time TIMESTAMP,
    PRIMARY KEY (project_id, achievement_id),
    FOREIGN KEY (project_id) REFERENCES research_project(project_id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES research_achievement(achievement_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 5. 科研采集记录-环境监测数据关联表（collection_monitor_data_rel）
create_data_rel_table = """
CREATE TABLE IF NOT EXISTS collection_monitor_data_rel (
    collection_id VARCHAR(30) NOT NULL,
    monitor_data_id VARCHAR(30) NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    association_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(200),
    PRIMARY KEY (collection_id, monitor_data_id),
    FOREIGN KEY (collection_id) REFERENCES research_data_collection(collection_id) ON DELETE CASCADE,
    CHECK (data_type IN ('生物多样性监测数据', '生态环境监测数据'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 执行表创建（按依赖顺序）
if __name__ == "__main__":
    # 1. 连接数据库
    db_conn = create_db_connection(HOST, USER, PASSWORD, DATABASE)

    if db_conn:
        # 2. 依次创建表（确保被依赖的表优先创建）
        tables = [
            create_project_table,         # 无依赖，最先创建
            create_collection_table,      # 依赖 research_project 和 region_info
            create_achievement_table,     # 依赖 research_project
            create_share_rel_table,       # 依赖 research_project 和 research_achievement
            create_data_rel_table         # 依赖 research_data_collection
        ]

        for table_sql in tables:
            execute_query(db_conn, table_sql)

        # 3. 关闭连接
        db_conn.close()
        print("🔌 数据库连接已关闭")