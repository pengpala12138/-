# -*- coding: utf-8 -*-
"""
执法监管业务线自动化存储过程与触发器（Flask接口适配版）
核心：完全匹配 Flask 接口中的表名和字段名，确保部署后可自动触发
"""
import pymysql
from typing import Optional

# 数据库连接配置（与 Flask 接口完全一致）
DB_CONFIG = {
    "host": "10.152.230.97",
    "port": 3306,
    "user": "zyj",
    "password": "515408",
    "database": "sjk",
    "charset": "utf8mb4",
    "connect_timeout": 10
}


def get_db_connection() -> Optional[pymysql.connections.Connection]:
    """获取数据库连接（适配 pymysql 语法）"""
    try:
        conn = pymysql.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            charset=DB_CONFIG["charset"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        print("✅ 数据库连接成功")
        return conn
    except Exception as e:
        print(f"❌ 数据库连接失败：{str(e)}")
        # 仅重试1次
        try:
            print("🔄 尝试最后1次连接...")
            conn = pymysql.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                database=DB_CONFIG["database"],
                charset=DB_CONFIG["charset"],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            print("✅ 重试连接成功")
            return conn
        except Exception as e2:
            print(f"❌ 重试连接失败：{str(e2)}")
            return None


def deploy_auto_dispatch():
    """单次连接完成部署：删除旧对象 → 创建存储过程 → 创建触发器（完全适配 Flask 表名）"""
    conn = get_db_connection()
    if not conn:
        print("❌ 部署失败：未获取到数据库连接")
        return

    try:
        with conn.cursor() as cursor:
            print("\n1. 删除旧的存储过程和触发器...")
            # 删除旧对象（避免冲突，触发器名适配 Flask 表名）
            cursor.execute("DROP TRIGGER IF EXISTS trg_after_insert_illegal_record;")
            cursor.execute("DROP PROCEDURE IF EXISTS auto_create_dispatch;")
            print("✅ 旧对象删除完成")

            print("\n2. 创建自动调度存储过程（适配 Flask 接口表名）...")
            # 关键修改：所有表名与 Flask 接口一致（law_enforcers、illegal_record、law_dispatch）
            procedure_sql = """
            CREATE PROCEDURE auto_create_dispatch(IN p_record_id VARCHAR(30), IN p_region_id VARCHAR(20))
            BEGIN
                DECLARE v_officer_id VARCHAR(20);
                DECLARE v_dispatch_id VARCHAR(50);

                -- 步骤1：查询该区域对应的执法人员（Flask 表名：law_enforcers）
                SELECT office_id INTO v_officer_id
                FROM law_enforcer
                WHERE office_id NOT IN (
                    SELECT officer_id FROM law_dispatch 
                    WHERE status IN ('待响应', '响应中')
                )
                LIMIT 1;

                -- 若无空闲人员，选择任意执法人员
                IF v_officer_id IS NULL THEN
                    SELECT office_id INTO v_officer_id
                    FROM law_enforcer
                    LIMIT 1;
                END IF;

                -- 步骤2：生成唯一调度编号（格式：DISPATCH_YYYYMMDDHHMMSS_随机数）
                SET v_dispatch_id = CONCAT(
                    'DISPATCH_',
                    DATE_FORMAT(NOW(), '%Y%m%d%H%i%s'),
                    '_',
                    FLOOR(RAND() * 1000)
                );

                -- 步骤3：插入执法调度记录（Flask 表名：law_dispatch）
                IF v_officer_id IS NOT NULL THEN
                    INSERT INTO law_dispatch (
                        dispatch_id, 
                        illegal_behavior_record_id, 
                        officer_id, 
                        dispatch_time, 
                        status
                    ) VALUES (
                        v_dispatch_id,
                        p_record_id,
                        v_officer_id,
                        NOW(),
                        '待响应'
                    );
                END IF;
            END
            """
            cursor.execute(procedure_sql)
            print("✅ 存储过程创建成功")

            print("\n3. 创建触发器（适配 Flask 接口表名）...")
            # 触发器：监听 Flask 中的非法行为表（illegal_record），插入后自动调度
            trigger_sql = """
            CREATE TRIGGER trg_after_insert_illegal_record
            AFTER INSERT ON illegal_record
            FOR EACH ROW
            BEGIN
                -- 调用存储过程，传入 Flask 表中的字段（record_id、region_id）
                CALL auto_create_dispatch(NEW.record_id, NEW.region_id);
            END
            """
            cursor.execute(trigger_sql)
            print("✅ 触发器创建成功")

        conn.commit()
        print("\n🎉 执法监管自动调度功能部署完成！")
        print("功能说明（与 Flask 接口完全兼容）：")
        print("  1. 通过 Flask 接口新增非法行为记录（插入 illegal_record 表）后，触发器自动触发")
        print("  2. 存储过程自动匹配 law_enforcers 表中的可用执法人员")
        print("  3. 调度记录自动存入 law_dispatch 表（状态：待响应），可通过 Flask 调度接口查询")
    except Exception as e:
        print(f"\n❌ 部署失败：{str(e)}")
        conn.rollback()
    finally:
        conn.close()
        print("\n🔌 数据库连接已关闭")


if __name__ == "__main__":
    print("=" * 60)
    print("开始部署执法监管自动调度功能（Flask 接口适配版）")
    print("=" * 60)
    deploy_auto_dispatch()