import pymysql
import pymysql.cursors
from datetime import datetime, timedelta
import random
import time
import os

# 数据库配置（保持原配置不变）
DB_CONFIG = {
    "host": "10.152.230.97",
    "user": "zyj",
    "password": "515408",
    "database": "sjk",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

class LawEnforcementDB:
    def __init__(self):
        self.connection = None
        self.connect()
        self.region_ids = []  # 存储region_info中已存在的合法region_id

    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(**DB_CONFIG)
            print(f"✅ 成功连接数据库：{DB_CONFIG['host']}/{DB_CONFIG['database']}")
        except pymysql.Error as e:
            print(f"❌ 数据库连接失败：{e}")
            raise

    def verify_region_info(self):
        """校验region_info表及region_id字段，获取合法region_id列表"""
        print("\n🔍 开始校验region_info表...")
        try:
            with self.connection.cursor() as cursor:
                # 1. 检查region_info表是否存在
                cursor.execute("""
                    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'region_info'
                """, (DB_CONFIG['database'],))
                if not cursor.fetchone():
                    raise Exception("region_info表不存在，请先创建该表")

                # 2. 检查region_id字段是否存在且为主键
                cursor.execute("""
                    SELECT COLUMN_NAME, COLUMN_KEY FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'region_info' AND COLUMN_NAME = 'region_id'
                """, (DB_CONFIG['database'],))
                region_id_col = cursor.fetchone()
                if not region_id_col:
                    raise Exception("region_info表中不存在region_id字段")
                if region_id_col['COLUMN_KEY'] != 'PRI':
                    raise Exception("region_id字段不是region_info表的主键")

                # 3. 获取所有合法的region_id（用于后续数据插入匹配）
                cursor.execute("SELECT region_id FROM region_info")
                self.region_ids = [row['region_id'] for row in cursor.fetchall()]
                if len(self.region_ids) < 2:
                    raise Exception("region_info表中至少需要2个有效区域编号（region_id）")

                print(f"✅ region_info表校验通过，获取到{len(self.region_ids)}个合法区域编号")
                print(f"📋 部分合法region_id：{self.region_ids[:5]}")
                return True
        except Exception as e:
            print(f"❌ region_info表校验失败：{e}")
            raise

    def execute_ddl(self):
        """执行DDL（拆分索引创建语句，修复语法错误）"""
        print("\n🏗️  开始创建执法监管业务线表...")
        # 表创建语句（每个表单独一条SQL）
        table_scripts = [
            # 1. 执法人员信息表
            """
            CREATE TABLE IF NOT EXISTS law_enforcer (
                office_id VARCHAR(20) PRIMARY KEY COMMENT '执法ID',
                name VARCHAR(50) NOT NULL COMMENT '姓名',
                department VARCHAR(100) NOT NULL COMMENT '所属部门',
                authority_level VARCHAR(50) NOT NULL COMMENT '执法权限',
                contact VARCHAR(20) COMMENT '联系方式',
                device_no VARCHAR(30) NOT NULL COMMENT '执法设备编号'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='执法人员信息表';
            """,
            # 2. 视频监控点信息表
            """
            CREATE TABLE IF NOT EXISTS video_monitor (
                monitor_id VARCHAR(30) PRIMARY KEY COMMENT '监控点编号',
                region_id VARCHAR(20) NOT NULL COMMENT '部署区域编号（与region_info一致）',
                location VARCHAR(100) NOT NULL COMMENT '安装位置（经纬度）',
                coverage VARCHAR(200) COMMENT '监控范围',
                status VARCHAR(10) NOT NULL CHECK (status IN ('正常', '故障')) COMMENT '设备状态',
                storage_period INT COMMENT '数据存储周期（天）'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频监控点信息表';
            """,
            # 3. 非法行为记录表
            """
            CREATE TABLE IF NOT EXISTS illegal_record (
                record_id VARCHAR(30) PRIMARY KEY COMMENT '记录编号',
                behavior_type VARCHAR(50) NOT NULL CHECK (behavior_type IN ('非法进入', '盗猎', '破坏植被', '非法露营', '乱扔垃圾')) COMMENT '非法行为类型',
                occurrence_time TIMESTAMP NOT NULL COMMENT '发生时间',
                region_id VARCHAR(20) NOT NULL COMMENT '发生区域编号（与region_info一致）',
                evidence_path VARCHAR(200) COMMENT '影像证据路径',
                status VARCHAR(10) NOT NULL CHECK (status IN ('未处理', '处理中', '已结案')) COMMENT '处理状态',
                officer_id VARCHAR(20) COMMENT '执法ID',
                result TEXT COMMENT '处理结果',
                basis VARCHAR(100) COMMENT '处罚依据'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='非法行为记录表';
            """,
            # 4. 非法行为-视频监控点关联表
            """
            CREATE TABLE IF NOT EXISTS illegal_monitor_rel (
                illegal_behavior_record_id VARCHAR(30) NOT NULL COMMENT '非法行为记录编号',
                monitor_id VARCHAR(30) NOT NULL COMMENT '监控点编号',
                PRIMARY KEY (illegal_behavior_record_id, monitor_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='非法行为-视频监控点关联表';
            """,
            # 5. 执法调度信息表
            """
            CREATE TABLE IF NOT EXISTS law_dispatch (
                dispatch_id VARCHAR(30) PRIMARY KEY COMMENT '调度编号',
                illegal_behavior_record_id VARCHAR(30) NOT NULL COMMENT '非法行为记录编号',
                officer_id VARCHAR(20) NOT NULL COMMENT '执法ID',
                dispatch_time TIMESTAMP NOT NULL COMMENT '调度时间',
                response_time TIMESTAMP COMMENT '响应时间',
                complete_time TIMESTAMP COMMENT '处置完成时间',
                status VARCHAR(10) NOT NULL CHECK (status IN ('待响应', '已派单', '已完成')) COMMENT '调度状态'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='执法调度信息表';
            """
        ]

        # 索引创建语句（每条索引单独一条SQL，避免语法错误）
        index_scripts = [
            "CREATE INDEX idx_illegal_region_time ON illegal_record(region_id, occurrence_time);",
            "CREATE INDEX idx_illegal_status ON illegal_record(status);",
            "CREATE INDEX idx_dispatch_illegal ON law_dispatch(illegal_behavior_record_id);",
            "CREATE INDEX idx_video_region ON video_monitor(region_id);",
            "CREATE INDEX idx_rel_monitor ON illegal_monitor_rel(monitor_id);",
            "CREATE INDEX idx_illegal_officer ON illegal_record(officer_id);",
            "CREATE INDEX idx_dispatch_officer ON law_dispatch(officer_id);"
        ]

        try:
            with self.connection.cursor() as cursor:
                # 1. 执行表创建语句
                for script in table_scripts:
                    clean_script = '\n'.join([line.strip() for line in script.split('\n') if line.strip() and not line.strip().startswith('--')])
                    if clean_script:
                        cursor.execute(clean_script)
                print("✅ 所有表创建完成")

                # 2. 执行索引创建语句（单独执行，避免语法冲突）
                for idx_sql in index_scripts:
                    cursor.execute(idx_sql)
                print("✅ 所有索引创建完成")

            self.connection.commit()
            print("✅ 执法监管业务线表和索引创建全部完成")
        except pymysql.Error as e:
            self.connection.rollback()
            print(f"❌ DDL执行失败：{e}")
            raise

    def insert_test_data(self):
        """插入测试数据（每个表≥20条，region_id完全匹配region_info）"""
        print("\n📥 开始插入测试数据...")
        try:
            with self.connection.cursor() as cursor:
                # 1. 执法人员（25条）
                law_enforcer_data = [
                    (f"LE{2025001+i:06d}", f"执法人员{i+1}", f"执法{i//6+1}队",
                     "非法行为处置、现场取证、应急调度",
                     f"138{random.randint(10000000, 99999999)}" if random.choice([True, False]) else f"139{random.randint(10000000, 99999999)}",
                     f"LD{2025001+i:08d}")
                    for i in range(25)
                ]
                cursor.executemany("""
                    INSERT INTO law_enforcer (office_id, name, department, authority_level, contact, device_no)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE name=VALUES(name)
                """, law_enforcer_data)
                print(f"✅ 执法人员数据插入完成（25条）")

                # 2. 视频监控点（30条）
                video_monitor_data = [
                    (f"VM{2025001+i:08d}", random.choice(self.region_ids),
                     f"{round(110+random.uniform(0, 10), 6)},{round(30+random.uniform(0, 10), 6)}",
                     f"{random.randint(30, 150)}米半径",
                     random.choice(['正常', '故障']),
                     random.randint(90, 365))
                    for i in range(30)
                ]
                cursor.executemany("""
                    INSERT INTO video_monitor (monitor_id, region_id, location, coverage, status, storage_period)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE monitor_id=VALUES(monitor_id)
                """, video_monitor_data)
                print(f"✅ 视频监控点数据插入完成（30条）")

                # 3. 非法行为记录（40条）
                behavior_types = ['非法进入', '盗猎', '破坏植被', '非法露营', '乱扔垃圾']
                illegal_record_data = [
                    (f"IR{2025001+i:08d}", random.choice(behavior_types),
                     datetime.now() - timedelta(days=random.randint(0, 90)),
                     random.choice(self.region_ids),
                     f"/data/evidence/illegal/{2025001+i}.mp4" if random.choice([True, False]) else None,
                     random.choice(['未处理', '处理中', '已结案']),
                     f"LE{2025001+random.randint(0,24):06d}" if random.choice([True, False]) else None,
                     random.choice(['警告教育', '罚款500元', '罚款1000元', '移交林业部门', '限期整改']) if random.choice([True, False]) else None,
                     "《国家公园管理条例》第二十三条" if random.choice([True, False]) else "《野生动物保护法》第十六条")
                    for i in range(40)
                ]
                cursor.executemany("""
                    INSERT INTO illegal_record (record_id, behavior_type, occurrence_time, region_id, evidence_path, 
                                              status, officer_id, result, basis)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE record_id=VALUES(record_id)
                """, illegal_record_data)
                print(f"✅ 非法行为记录数据插入完成（40条）")

                # 4. 多对多关联（40条）
                rel_data = [
                    (f"IR{2025001+i:08d}", f"VM{2025001+random.randint(0,29):08d}")
                    for i in range(40)
                ]
                cursor.executemany("""
                    INSERT INTO illegal_monitor_rel (illegal_behavior_record_id, monitor_id)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE illegal_behavior_record_id=VALUES(illegal_behavior_record_id)
                """, rel_data)
                print(f"✅ 多对多关联数据插入完成（40条）")

                # 5. 执法调度（35条）
                law_dispatch_data = [
                    (f"LD{2025001+i:08d}", f"IR{2025001+i:08d}",
                     f"LE{2025001+random.randint(0,24):06d}",
                     datetime.now() - timedelta(days=random.randint(0, 90)),
                     datetime.now() - timedelta(days=random.randint(0, 90)) + timedelta(minutes=random.randint(5, 60))
                     if random.choice([True, False]) else None,
                     datetime.now() - timedelta(days=random.randint(0, 90)) + timedelta(hours=random.randint(1, 12))
                     if random.choice([True, False]) else None,
                     random.choice(['待响应', '已派单', '已完成']))
                    for i in range(35)
                ]
                cursor.executemany("""
                    INSERT INTO law_dispatch (dispatch_id, illegal_behavior_record_id, officer_id, dispatch_time, 
                                            response_time, complete_time, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE dispatch_id=VALUES(dispatch_id)
                """, law_dispatch_data)
                print(f"✅ 执法调度数据插入完成（35条）")

            self.connection.commit()
            print("\n🎉 所有测试数据插入完成！（各表均≥20条）")
        except pymysql.Error as e:
            self.connection.rollback()
            print(f"\n❌ 测试数据插入失败：{e}")
            raise

    def execute_complex_sql(self):
        """执行5条复杂查询（验证数据可用性）"""
        print("\n📊 开始执行复杂查询测试：")
        complex_sqls = [
            # 场景1：核心保护区近30天未处理的非法行为
            """
            SELECT 
                ir.record_id, ir.behavior_type, ir.occurrence_time, ri.region_name,
                vm.monitor_id, vm.location, ir.evidence_path
            FROM 
                illegal_record ir
            JOIN 
                region_info ri ON ir.region_id = ri.region_id
            JOIN 
                illegal_monitor_rel rel ON ir.record_id = rel.illegal_behavior_record_id
            JOIN 
                video_monitor vm ON rel.monitor_id = vm.monitor_id
            WHERE 
                ir.occurrence_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                AND ir.status = '未处理'
            ORDER BY 
                ir.occurrence_time DESC
            """,
            # 场景2：执法人员近90天处理量统计
            """
            SELECT 
                le.office_id, le.name, le.department,
                COUNT(ld.dispatch_id) AS handle_count,
                AVG(TIMESTAMPDIFF(HOUR, ld.dispatch_time, ld.complete_time)) AS avg_handle_hours
            FROM 
                law_enforcer le
            LEFT JOIN 
                law_dispatch ld ON le.office_id = ld.officer_id
            WHERE 
                ld.complete_time IS NOT NULL
                AND ld.dispatch_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            GROUP BY 
                le.office_id, le.name, le.department
            ORDER BY 
                handle_count DESC
            """,
            # 场景3：区域非法行为类型分布
            """
            SELECT 
                ri.region_id, ri.region_name, ir.behavior_type,
                COUNT(ir.record_id) AS behavior_count
            FROM 
                region_info ri
            JOIN 
                illegal_record ir ON ri.region_id = ir.region_id
            WHERE 
                ir.occurrence_time >= DATE_SUB(NOW(), INTERVAL 60 DAY)
            GROUP BY 
                ri.region_id, ri.region_name, ir.behavior_type
            ORDER BY 
                behavior_count DESC
            """,
            # 场景4：故障监控点关联的未处理非法行为
            """
            SELECT 
                vm.monitor_id, vm.region_id, ri.region_name, vm.status,
                ir.record_id, ir.behavior_type, ir.occurrence_time
            FROM 
                video_monitor vm
            JOIN 
                illegal_monitor_rel rel ON vm.monitor_id = rel.monitor_id
            JOIN 
                illegal_record ir ON rel.illegal_behavior_record_id = ir.record_id
            JOIN 
                region_info ri ON vm.region_id = ri.region_id
            WHERE 
                vm.status = '故障'
                AND ir.status = '未处理'
            ORDER BY 
                ir.occurrence_time ASC
            """,
            # 场景5：调度响应超时记录
            """
            SELECT 
                ld.dispatch_id, ir.record_id, ir.behavior_type,
                le.name, le.department,
                TIMESTAMPDIFF(MINUTE, ld.dispatch_time, ld.response_time) AS response_delay
            FROM 
                law_dispatch ld
            JOIN 
                illegal_record ir ON ld.illegal_behavior_record_id = ir.record_id
            JOIN 
                law_enforcer le ON ld.officer_id = le.office_id
            WHERE 
                ld.response_time IS NOT NULL
                AND TIMESTAMPDIFF(MINUTE, ld.dispatch_time, ld.response_time) > 30
                AND ld.dispatch_time >= DATE_SUB(NOW(), INTERVAL 45 DAY)
            ORDER BY 
                response_delay DESC
            """
        ]

        for i, sql in enumerate(complex_sqls, 1):
            print(f"\n--- 第{i}条查询（场景{i}）---")
            start_time = time.time()
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    end_time = time.time()
                    exec_time = round(end_time - start_time, 4)
                    print(f"执行耗时：{exec_time}秒，返回结果数：{len(results)}")
                    if results:
                        for j, res in enumerate(results[:2]):
                            print(f"  结果{j+1}：{res}")
            except pymysql.Error as e:
                print(f"❌ 查询失败：{e}")

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("\n✅ 数据库连接已关闭")

# 主函数（按流程执行）
if __name__ == "__main__":
    db = LawEnforcementDB()
    try:
        db.verify_region_info()  # 1. 校验region_info
        db.execute_ddl()         # 2. 创建表和索引
        db.insert_test_data()    # 3. 插入足量数据
        db.execute_complex_sql() # 4. 验证查询
    finally:
        db.close()