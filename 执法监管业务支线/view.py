# -*- coding: utf-8 -*-
"""
执法监管业务线核心视图定义（角色适配+字段修复版）
修复：视图3关联字段错误（移除 le.region_id 依赖），适配 app.py 表结构
适配角色：执法人员、公园管理人员、系统管理员/技术人员
"""
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Connection
import pandas as pd
import time
from typing import Optional

# 数据库连接配置
DB_CONFIG = {
    "host": "10.152.230.97",
    "port": 3306,
    "user": "zyj",
    "password": "515408",
    "database": "sjk",
    "charset": "utf8mb4"
}

# 优化连接池配置（避免连接数耗尽）
engine = create_engine(
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}",
    echo=False,
    poolclass=QueuePool,
    pool_size=3,
    max_overflow=5,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_use_lifo=True
)


def get_db_connection() -> Optional[Connection]:
    """获取数据库连接（带重试机制）"""
    retry_count = 2
    retry_delay = 3
    for i in range(retry_count):
        try:
            conn = engine.connect()
            return conn
        except Exception as e:
            if "Too many connections" in str(e) and i < retry_count - 1:
                print(f"连接数不足，{retry_delay}秒后重试（{i + 1}/{retry_count}）...")
                time.sleep(retry_delay)
            else:
                print(f"连接失败：{str(e)}")
                return None


def init_views():
    """初始化所有视图（修复关联字段，拆分执行）"""
    print("开始初始化执法监管业务线核心视图...")
    conn = get_db_connection()
    if not conn:
        print("初始化失败：无法获取数据库连接")
        return

    try:
        # 视图1：执法人员个人工作台账视图（适配「执法人员」角色）
        view1_sql = """
        CREATE OR REPLACE VIEW `v_officer_work_tasks` AS
        SELECT
            `ir`.`record_id` AS `非法行为记录编号`,
            `ir`.`behavior_type` AS `行为类型`,
            `ri`.`region_name` AS `发生区域`,
            `ir`.`occurrence_time` AS `发生时间`,
            `ir`.`evidence_path` AS `证据路径`,
            `ir`.`status` AS `处理状态`,
            `ir`.`result` AS `处理结果`,
            `ld`.`dispatch_id` AS `调度编号`,
            `ld`.`dispatch_time` AS `调度时间`,
            `ld`.`response_time` AS `响应时间`,
            `ld`.`complete_time` AS `处置完成时间`,
            `ld`.`status` AS `调度状态`
        FROM `illegal_record` `ir`
        LEFT JOIN `law_dispatch` `ld` ON `ir`.`record_id` = `ld`.`illegal_behavior_record_id`
        LEFT JOIN `region_info` `ri` ON `ir`.`region_id` = `ri`.`region_id`
        LEFT JOIN `law_enforcer` `le` ON `ld`.`officer_id` = `le`.`office_id`
        ORDER BY `ir`.`occurrence_time` DESC;
        """
        conn.execute(text(view1_sql))
        print("✅ 视图 v_officer_work_tasks（执法人员台账）创建/更新成功")

        # 视图2：区域执法效率统计视图（适配「公园管理人员」角色）
        view2_sql = """
        CREATE OR REPLACE VIEW `v_region_law_enforcement_stats` AS
        SELECT
            `ri`.`region_id` AS `区域编号`,
            `ri`.`region_name` AS `区域名称`,
            COUNT(`ir`.`record_id`) AS `非法行为总数`,
            SUM(CASE WHEN `ir`.`status` = '已结案' THEN 1 ELSE 0 END) AS `已结案数量`,
            SUM(CASE WHEN `ir`.`status` = '处理中' THEN 1 ELSE 0 END) AS `处理中数量`,
            SUM(CASE WHEN `ir`.`status` = '未处理' THEN 1 ELSE 0 END) AS `未处理数量`,
            ROUND(
                IFNULL(SUM(CASE WHEN `ir`.`status` = '已结案' THEN 1 ELSE 0 END) / COUNT(`ir`.`record_id`) * 100, 0),
                2
            ) AS `结案率_百分比`,
            ROUND(
                IFNULL(AVG(TIMESTAMPDIFF(MINUTE, `ld`.`dispatch_time`, `ld`.`complete_time`)), 0),
                1
            ) AS `平均处置时长_分钟`,
            (SELECT `le`.`name` 
             FROM `law_dispatch` `ld2`
             LEFT JOIN `law_enforcer` `le` ON `ld2`.`officer_id` = `le`.`office_id`
             WHERE `ld2`.`illegal_behavior_record_id` IN (
                 SELECT `ir2`.`record_id` FROM `illegal_record` `ir2` WHERE `ir2`.`region_id` = `ri`.`region_id`
             )
             GROUP BY `le`.`office_id`
             ORDER BY COUNT(`ld2`.`dispatch_id`) DESC
             LIMIT 1) AS `主要执法人员`
        FROM `region_info` `ri`
        LEFT JOIN `illegal_record` `ir` ON `ri`.`region_id` = `ir`.`region_id`
        LEFT JOIN `law_dispatch` `ld` ON `ir`.`record_id` = `ld`.`illegal_behavior_record_id`
        GROUP BY `ri`.`region_id`, `ri`.`region_name`
        ORDER BY `非法行为总数` DESC;
        """
        conn.execute(text(view2_sql))
        print("✅ 视图 v_region_law_enforcement_stats（区域执法统计）创建/更新成功")

        # 视图3：执法设备与监控点运维视图（适配「系统管理员/技术人员」角色，修复关联字段）
        view3_sql = """
        CREATE OR REPLACE VIEW `v_law_enforcement_equipment_ops` AS
        SELECT
            `vm`.`monitor_id` AS `监控点编号`,
            `ri`.`region_name` AS `部署区域`,
            `vm`.`location` AS `安装位置（经纬度）`,
            `vm`.`status` AS `监控点设备状态`,
            `vm`.`storage_period` AS `数据存储周期（天）`,
            `vm`.`coverage` AS `监控范围`,
            COUNT(DISTINCT `rel`.`illegal_behavior_record_id`) AS `关联非法行为数量`,
            MAX(`ir`.`occurrence_time`) AS `最近证据采集时间`,
            -- 修复：通过非法行为记录间接关联执法人员，避免依赖 le.region_id
            (SELECT `le`.`device_no` 
             FROM `illegal_record` `ir2`
             LEFT JOIN `law_dispatch` `ld2` ON `ir2`.`record_id` = `ld2`.`illegal_behavior_record_id`
             LEFT JOIN `law_enforcer` `le` ON `ld2`.`officer_id` = `le`.`office_id`
             WHERE `ir2`.`region_id` = `vm`.`region_id`
             LIMIT 1) AS `执法设备编号`,
            (SELECT `le`.`name` 
             FROM `illegal_record` `ir2`
             LEFT JOIN `law_dispatch` `ld2` ON `ir2`.`record_id` = `ld2`.`illegal_behavior_record_id`
             LEFT JOIN `law_enforcer` `le` ON `ld2`.`officer_id` = `le`.`office_id`
             WHERE `ir2`.`region_id` = `vm`.`region_id`
             LIMIT 1) AS `绑定执法人员`,
            (SELECT `le`.`department` 
             FROM `illegal_record` `ir2`
             LEFT JOIN `law_dispatch` `ld2` ON `ir2`.`record_id` = `ld2`.`illegal_behavior_record_id`
             LEFT JOIN `law_enforcer` `le` ON `ld2`.`officer_id` = `le`.`office_id`
             WHERE `ir2`.`region_id` = `vm`.`region_id`
             LIMIT 1) AS `所属部门`
        FROM `video_monitor` `vm`
        LEFT JOIN `illegal_monitor_rel` `rel` ON `vm`.`monitor_id` = `rel`.`monitor_id`
        LEFT JOIN `illegal_record` `ir` ON `rel`.`illegal_behavior_record_id` = `ir`.`record_id`
        LEFT JOIN `region_info` `ri` ON `vm`.`region_id` = `ri`.`region_id`
        -- 移除：LEFT JOIN `law_enforcer` `le` ON `vm`.`region_id` = `le`.`region_id`（无该字段）
        GROUP BY `vm`.`monitor_id`, `ri`.`region_name`, `vm`.`location`, `vm`.`status`, 
                 `vm`.`storage_period`, `vm`.`coverage`
        ORDER BY `vm`.`status` ASC, `关联非法行为数量` DESC;
        """
        conn.execute(text(view3_sql))
        print("✅ 视图 v_law_enforcement_equipment_ops（设备运维）创建/更新成功")

        conn.commit()
        print("\n🎉 所有执法监管业务线核心视图初始化完成！")
        print("📌 视图说明：")
        print("  1. v_officer_work_tasks - 执法人员个人工作台账（查看个人任务）")
        print("  2. v_region_law_enforcement_stats - 区域执法统计（管理人员决策）")
        print("  3. v_law_enforcement_equipment_ops - 设备运维视图（运维人员监控）")
    except Exception as e:
        print(f"\n❌ 初始化失败：{str(e)}")
        conn.rollback()
    finally:
        conn.close()


def query_view(view_name: str, limit: int = 10, officer_id: str = "") -> Optional[pd.DataFrame]:
    """查询视图数据（支持执法人员ID筛选，适配角色权限）"""
    if not view_name:
        print("❌ 视图名称不能为空")
        return None

    # 执法人员台账视图支持按ID筛选
    if view_name == "v_officer_work_tasks" and officer_id:
        query_sql = f"""
        SELECT * FROM `{view_name}` 
        WHERE `调度编号` IN (
            SELECT `dispatch_id` FROM `law_dispatch` WHERE `officer_id` = '{officer_id}'
        ) LIMIT {limit};
        """
    else:
        query_sql = f"SELECT * FROM `{view_name}` LIMIT {limit};"

    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql(text(query_sql), conn)
            return df
        except Exception as e:
            print(f"❌ 查询视图 {view_name} 失败：{str(e)}")
            return None
        finally:
            conn.close()
    return None


def close_engine():
    """关闭数据库引擎，释放所有连接"""
    engine.dispose()
    print("\n🔌 数据库引擎已关闭，所有连接已释放")


if __name__ == "__main__":
    try:
        # 初始化视图（仅需执行一次）
        init_views()

        # 可选测试：查询不同角色视图
        print("\n📊 测试查询管理人员视图（区域执法统计）：")
        stats_df = query_view("v_region_law_enforcement_stats", limit=5)
        if stats_df is not None and not stats_df.empty:
            print(stats_df.to_string(index=False))
        else:
            print("📊 管理人员视图查询结果为空（可能暂无数据）")

        print("\n📊 测试查询运维人员视图（设备运维）：")
        ops_df = query_view("v_law_enforcement_equipment_ops", limit=5)
        if ops_df is not None and not ops_df.empty:
            print(ops_df.to_string(index=False))
        else:
            print("📊 运维人员视图查询结果为空（可能暂无数据）")

        print("\n📊 测试查询执法人员个人台账（示例ID：LE2025001）：")
        officer_df = query_view("v_officer_work_tasks", limit=5, officer_id="LE2025001")
        if officer_df is not None and not officer_df.empty:
            print(officer_df.to_string(index=False))
        else:
            print("📊 执法人员台账查询结果为空（可能无对应任务）")

    except KeyboardInterrupt:
        print("\n⚠️  程序被用户中断")
    finally:
        close_engine()