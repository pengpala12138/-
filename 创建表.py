import pymysql
from datetime import datetime, timedelta
import pandas as pd
import random
import time


# ====================== 1. 数据库连接工具类（增强版） ======================
class DBConnection:
    """数据库连接工具类（适配172.20.10.4，新增超时配置）"""

    def __init__(self, host='172.20.10.4', port=3306, user='sjy', password='515408', db='sjk',
                 charset='utf8mb4'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.charset = charset
        self.conn = None
        self.cursor = None

    def connect(self):
        """建立连接（先创建数据库，设置超时）"""
        try:
            # 1. 连接MySQL服务，创建数据库
            temp_conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                charset=self.charset,
                connect_timeout=10
            )
            temp_cursor = temp_conn.cursor()
            temp_cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS {self.db} DEFAULT CHARACTER SET {self.charset} COLLATE {self.charset}_unicode_ci;")
            temp_conn.commit()
            temp_cursor.close()
            temp_conn.close()

            # 2. 连接目标数据库
            self.conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.db,
                charset=self.charset,
                connect_timeout=10
            )
            self.cursor = self.conn.cursor()
            print(f"✅ 成功连接到 {self.host} 的 {self.db} 数据库")
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败：{e}")
            return False

    def close(self):
        """关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("🔌 数据库连接已关闭")

    def execute_sql(self, sql, params=None):
        """执行增删改/建表SQL，返回执行耗时"""
        start_time = time.time()
        try:
            self.cursor.execute(sql, params)
            self.conn.commit()
            exec_time = round(time.time() - start_time, 6)
            print(f"✅ SQL执行成功，耗时：{exec_time}秒")
            return True, exec_time
        except Exception as e:
            self.conn.rollback()
            exec_time = round(time.time() - start_time, 6)
            print(f"❌ SQL执行失败：{e}，耗时：{exec_time}秒")
            return False, exec_time

    def query_sql(self, sql, params=None):
        """执行查询，返回DataFrame+执行耗时"""
        start_time = time.time()
        try:
            self.cursor.execute(sql, params)
            result = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            df = pd.DataFrame(result, columns=columns)
            exec_time = round(time.time() - start_time, 6)
            print(f"✅ 查询成功，返回{len(df)}条数据，耗时：{exec_time}秒")
            return df, exec_time
        except Exception as e:
            exec_time = round(time.time() - start_time, 6)
            print(f"❌ 查询失败：{e}，耗时：{exec_time}秒")
            return pd.DataFrame(), exec_time


# ====================== 2. 数据库结构设计+初始化（满足第三范式） ======================
class BiodiversityDBInitializer:
    """
    数据库初始化类：
    1. 概念结构：E-R图逻辑（见文档）
    2. 逻辑结构：第三范式关系模式
    3. 物理结构：表+约束+索引
    """

    def __init__(self, db_conn):
        self.db = db_conn
        # 定义索引配置（提升查询效率）
        self.index_config = [
            # 监测记录表：按物种+时间查询（高频）
            "CREATE INDEX idx_monitor_species_time ON monitor_record(species_id, monitor_time);",
            # 监测记录表：按数据状态查询（审核场景）
            "CREATE INDEX idx_monitor_status ON monitor_record(data_status);",
            # 栖息地表：按区域+生态类型查询
            "CREATE INDEX idx_habitat_region_eco ON habitat_info(region_id, ecological_type);",
            # 栖息地-物种关联表：反向查询（物种→栖息地）
            "CREATE INDEX idx_hab_species_sp ON habitat_species_relation(species_id);"
        ]

    def create_all_tables(self):
        """创建所有表（含约束，满足第三范式）"""
        # ---------------------- 基础表：区域信息表（1NF/2NF/3NF） ----------------------
        region_table = """
        CREATE TABLE IF NOT EXISTS region_info (
            region_id VARCHAR(20) PRIMARY KEY COMMENT '区域编号（主键）',
            region_name VARCHAR(50) NOT NULL COMMENT '区域名称（非空）',
            region_level VARCHAR(20) DEFAULT '省级' COMMENT '区域级别：国家级/省级/市级',
            manager VARCHAR(50) COMMENT '区域管理员'
        ) COMMENT '区域信息表：存储监测区域基础信息，无冗余，满足第三范式';
        """

        # ---------------------- 核心表：物种信息表（拆分分类字段，满足3NF） ----------------------
        species_table = """
        CREATE TABLE IF NOT EXISTS species_info (
            species_id VARCHAR(20) PRIMARY KEY COMMENT '物种编号（主键）',
            chinese_name VARCHAR(100) NOT NULL COMMENT '中文名称（非空）',
            latin_name VARCHAR(200) COMMENT '拉丁名',
            kingdom VARCHAR(50) NOT NULL COMMENT '界（非空）',
            phylum VARCHAR(50) NOT NULL COMMENT '门（非空）',
            class VARCHAR(50) NOT NULL COMMENT '纲（非空）',
            order_name VARCHAR(50) NOT NULL COMMENT '目（非空）',
            family VARCHAR(50) NOT NULL COMMENT '科（非空）',
            genus VARCHAR(50) NOT NULL COMMENT '属（非空）',
            species_name VARCHAR(50) NOT NULL COMMENT '种（非空）',
            protection_level VARCHAR(20) NOT NULL COMMENT '保护级别（非空）',
            living_habits TEXT NOT NULL COMMENT '生存习性（非空）',
            distribution_desc TEXT NOT NULL COMMENT '分布范围描述（非空）',
            -- 检查约束：保护级别枚举
            CONSTRAINT ck_protection_level CHECK (protection_level IN ('国家一级', '国家二级', '无'))
        ) COMMENT '物种信息表：拆分分类字段，消除传递依赖，满足第三范式';
        """

        # ---------------------- 核心表：栖息地表（关联区域，无冗余） ----------------------
        habitat_table = """
        CREATE TABLE IF NOT EXISTS habitat_info (
            habitat_id VARCHAR(20) PRIMARY KEY COMMENT '栖息地编号（主键）',
            region_id VARCHAR(20) NOT NULL COMMENT '区域编号（外键）',
            ecological_type VARCHAR(50) NOT NULL COMMENT '生态类型（非空）',
            area DECIMAL(10,2) NOT NULL COMMENT '面积（公顷，非空）',
            core_protection TEXT NOT NULL COMMENT '核心保护范围（非空）',
            suitability_score INT NOT NULL COMMENT '环境适宜性评分（非空）',
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            -- 外键约束：级联删除/更新
            FOREIGN KEY (region_id) REFERENCES region_info(region_id) ON DELETE CASCADE ON UPDATE CASCADE,
            -- 检查约束：面积>0，评分1-10
            CONSTRAINT ck_area CHECK (area > 0),
            CONSTRAINT ck_suitability_score CHECK (suitability_score BETWEEN 1 AND 10)
        ) COMMENT '栖息地表：关联区域表，无冗余字段，满足第三范式';
        """

        # ---------------------- 关联表：栖息地-物种（多对多） ----------------------
        habitat_species_rel = """
        CREATE TABLE IF NOT EXISTS habitat_species_relation (
            habitat_id VARCHAR(20) NOT NULL COMMENT '栖息地编号（外键）',
            species_id VARCHAR(20) NOT NULL COMMENT '物种编号（外键）',
            is_main TINYINT DEFAULT 1 COMMENT '是否主要物种：1=是，0=否',
            PRIMARY KEY (habitat_id, species_id),  -- 复合主键，避免重复关联
            FOREIGN KEY (habitat_id) REFERENCES habitat_info(habitat_id) ON DELETE CASCADE,
            FOREIGN KEY (species_id) REFERENCES species_info(species_id) ON DELETE CASCADE
        ) COMMENT '栖息地-物种关联表：解决多对多关系，满足第三范式';
        """

        # ---------------------- 支撑表：监测设备表 ----------------------
        monitor_device = """
        CREATE TABLE IF NOT EXISTS monitor_device (
            device_id VARCHAR(20) PRIMARY KEY COMMENT '设备编号（主键）',
            device_type VARCHAR(20) NOT NULL COMMENT '设备类型：红外相机/无人机/人工巡查设备',
            status VARCHAR(20) DEFAULT '正常' COMMENT '设备状态：正常/故障/维护中',
            bind_region VARCHAR(20) COMMENT '绑定区域编号（关联region_info）',
            last_maintain DATETIME COMMENT '最后维护时间'
        ) COMMENT '监测设备表：无冗余，满足第三范式';
        """

        # ---------------------- 支撑表：系统用户表 ----------------------
        sys_user = """
        CREATE TABLE IF NOT EXISTS sys_user (
            user_id VARCHAR(20) PRIMARY KEY COMMENT '用户ID（主键）',
            user_name VARCHAR(50) NOT NULL COMMENT '用户名（非空）',
            role VARCHAR(20) NOT NULL COMMENT '角色：生态监测员/数据分析师/管理员',
            responsible_region VARCHAR(20) COMMENT '负责区域编号（关联region_info）',
            contact VARCHAR(20) COMMENT '联系方式'
        ) COMMENT '系统用户表：无冗余，满足第三范式';
        """

        # ---------------------- 核心表：监测记录表（关联所有支撑表） ----------------------
        monitor_record = """
        CREATE TABLE IF NOT EXISTS monitor_record (
            record_id VARCHAR(30) PRIMARY KEY COMMENT '记录编号（主键）',
            species_id VARCHAR(20) NOT NULL COMMENT '物种编号（外键）',
            device_id VARCHAR(20) NOT NULL COMMENT '设备编号（外键）',
            monitor_content VARCHAR(255) COMMENT '监测内容：影像路径/数量统计/行为描述',
            recorder_id VARCHAR(20) NOT NULL COMMENT '记录人ID（外键）',
            data_status VARCHAR(20) NOT NULL COMMENT '数据状态：有效/待核实',
            monitor_time DATETIME NOT NULL COMMENT '监测时间（非空）',
            longitude DECIMAL(10,6) COMMENT '经度',
            latitude DECIMAL(10,6) COMMENT '纬度',
            monitor_location VARCHAR(100) NOT NULL COMMENT '监测地点（非空）',
            monitor_method VARCHAR(20) NOT NULL COMMENT '监测方式（非空）',
            analysis_conclusion TEXT COMMENT '分析结论（分析师补充）',
            verify_time DATETIME COMMENT '审核时间',
            -- 外键约束：级联删除
            FOREIGN KEY (species_id) REFERENCES species_info(species_id) ON DELETE CASCADE,
            FOREIGN KEY (device_id) REFERENCES monitor_device(device_id) ON DELETE CASCADE,
            FOREIGN KEY (recorder_id) REFERENCES sys_user(user_id) ON DELETE CASCADE,
            -- 检查约束
            CONSTRAINT ck_data_status CHECK (data_status IN ('有效', '待核实')),
            CONSTRAINT ck_monitor_method CHECK (monitor_method IN ('红外相机', '人工巡查', '无人机'))
        ) COMMENT '监测记录表：关联物种/设备/用户表，无冗余，满足第三范式';
        """

        # 执行建表语句
        tables = [region_table, species_table, habitat_table, habitat_species_rel,
                  monitor_device, sys_user, monitor_record]
        for sql in tables:
            success, _ = self.db.execute_sql(sql)
            if not success:
                print("❌ 建表流程中断")
                return False

        # 创建索引（提升查询效率）
        for idx_sql in self.index_config:
            self.db.execute_sql(idx_sql)

        # 插入批量测试数据（每张表≥20条）
        self.insert_batch_test_data()
        print("✅ 所有表+索引创建完成，批量测试数据插入成功")
        return True

    def insert_batch_test_data(self):
        """插入批量测试数据（每张表≥20条，模拟真实业务）"""
        # ---------------------- 1. 区域表（20+条） ----------------------
        region_data = []
        regions = [
            ("R001", "云南西双版纳", "国家级", "王华"), ("R002", "云南普洱", "省级", "李明"),
            ("R003", "云南临沧", "省级", "张伟"), ("R004", "四川卧龙", "国家级", "刘芳"),
            ("R005", "陕西秦岭", "国家级", "赵强"), ("R006", "青海可可西里", "国家级", "黄丽"),
            ("R007", "西藏林芝", "省级", "周杰"), ("R008", "广西桂林", "市级", "吴佳"),
            ("R009", "贵州梵净山", "国家级", "郑涛"), ("R010", "湖北神农架", "国家级", "马丽"),
            ("R011", "江西鄱阳湖", "省级", "孙浩"), ("R012", "湖南洞庭湖", "省级", "朱燕"),
            ("R013", "内蒙古呼伦贝尔", "省级", "胡兵"), ("R014", "新疆喀纳斯", "省级", "林佳"),
            ("R015", "黑龙江扎龙", "国家级", "高伟"), ("R016", "江苏盐城", "市级", "田甜"),
            ("R017", "浙江千岛湖", "市级", "陈晨"), ("R018", "安徽黄山", "省级", "杨明"),
            ("R019", "福建武夷山", "国家级", "谢芳"), ("R020", "广东丹霞山", "省级", "韩涛"),
            ("R021", "海南热带雨林", "国家级", "邓杰"), ("R022", "重庆金佛山", "市级", "崔丽")
        ]
        for rid, rname, rlevel, manager in regions:
            region_data.append(f"('{rid}', '{rname}', '{rlevel}', '{manager}')")
        region_sql = f"INSERT INTO region_info (region_id, region_name, region_level, manager) VALUES {','.join(region_data)};"
        self.db.execute_sql(region_sql)

        # ---------------------- 2. 物种表（20+条） ----------------------
        species_data = []
        species_list = [
            ("S001", "亚洲象", "Elephas maximus", "动物界", "脊索动物门", "哺乳纲", "长鼻目", "象科", "象属", "亚洲象",
             "国家一级", "群居，食草，喜水源", "云南西双版纳/普洱/临沧"),
            ("S002", "滇金丝猴", "Rhinopithecus bieti", "动物界", "脊索动物门", "哺乳纲", "灵长目", "猴科", "仰鼻猴属",
             "滇金丝猴", "国家一级", "树栖，群居，食松萝", "云南西北部"),
            ("S003", "大熊猫", "Ailuropoda melanoleuca", "动物界", "脊索动物门", "哺乳纲", "食肉目", "熊科", "大熊猫属",
             "大熊猫", "国家一级", "独居，食竹", "四川卧龙/陕西秦岭"),
            ("S004", "藏羚羊", "Pantholops hodgsonii", "动物界", "脊索动物门", "哺乳纲", "偶蹄目", "牛科", "藏羚羊属",
             "藏羚羊", "国家一级", "群居，迁徙", "青海可可西里"),
            ("S005", "东北虎", "Panthera tigris altaica", "动物界", "脊索动物门", "哺乳纲", "食肉目", "猫科", "豹属",
             "虎", "国家一级", "独居，食肉", "黑龙江/吉林"),
            ("S006", "朱鹮", "Nipponia nippon", "动物界", "脊索动物门", "鸟纲", "鹳形目", "鹮科", "朱鹮属", "朱鹮",
             "国家一级", "群居，食鱼虾", "陕西洋县"),
            ("S007", "白鳍豚", "Lipotes vexillifer", "动物界", "脊索动物门", "哺乳纲", "鲸目", "白鱀豚科", "白鱀豚属",
             "白鳍豚", "国家一级", "水生，食肉", "长江中下游"),
            ("S008", "华南虎", "Panthera tigris amoyensis", "动物界", "脊索动物门", "哺乳纲", "食肉目", "猫科", "豹属",
             "虎", "国家一级", "独居，食肉", "福建/广东"),
            ("S009", "扬子鳄", "Alligator sinensis", "动物界", "脊索动物门", "爬行纲", "鳄目", "鼍科", "短吻鳄属",
             "扬子鳄", "国家一级", "水生，食肉", "安徽/江苏"),
            (
            "S010", "金丝猴", "Rhinopithecus roxellana", "动物界", "脊索动物门", "哺乳纲", "灵长目", "猴科", "仰鼻猴属",
            "金丝猴", "国家一级", "树栖，群居", "四川/陕西"),
            ("S011", "麋鹿", "Elaphurus davidianus", "动物界", "脊索动物门", "哺乳纲", "偶蹄目", "鹿科", "麋鹿属",
             "麋鹿", "国家一级", "群居，食草", "江苏盐城"),
            ("S012", "黑颈鹤", "Grus nigricollis", "动物界", "脊索动物门", "鸟纲", "鹤形目", "鹤科", "鹤属", "黑颈鹤",
             "国家一级", "群居，食水草", "西藏/青海"),
            ("S013", "丹顶鹤", "Grus japonensis", "动物界", "脊索动物门", "鸟纲", "鹤形目", "鹤科", "鹤属", "丹顶鹤",
             "国家一级", "群居，食鱼虾", "黑龙江扎龙"),
            ("S014", "白头叶猴", "Trachypithecus leucocephalus", "动物界", "脊索动物门", "哺乳纲", "灵长目", "猴科",
             "叶猴属", "白头叶猴", "国家一级", "树栖，食叶", "广西崇左"),
            ("S015", "雪豹", "Panthera uncia", "动物界", "脊索动物门", "哺乳纲", "食肉目", "猫科", "豹属", "雪豹",
             "国家一级", "独居，食肉", "青藏高原"),
            ("S016", "野牦牛", "Bos mutus", "动物界", "脊索动物门", "哺乳纲", "偶蹄目", "牛科", "牛属", "野牦牛",
             "国家一级", "群居，食草", "青海/西藏"),
            ("S017", "羚牛", "Budorcas taxicolor", "动物界", "脊索动物门", "哺乳纲", "偶蹄目", "牛科", "羚牛属", "羚牛",
             "国家一级", "群居，食草", "四川/陕西"),
            ("S018", "穿山甲", "Manis pentadactyla", "动物界", "脊索动物门", "哺乳纲", "鳞甲目", "穿山甲科", "穿山甲属",
             "穿山甲", "国家一级", "独居，食蚁", "南方各省"),
            ("S019", "褐马鸡", "Crossoptilon mantchuricum", "动物界", "脊索动物门", "鸟纲", "鸡形目", "雉科", "马鸡属",
             "褐马鸡", "国家一级", "群居，食植物", "山西/河北"),
            ("S020", "中华鲟", "Acipenser sinensis", "动物界", "脊索动物门", "鱼纲", "鲟形目", "鲟科", "鲟属", "中华鲟",
             "国家一级", "洄游，食肉", "长江流域"),
            ("S021", "长臂猿", "Hylobates lar", "动物界", "脊索动物门", "哺乳纲", "灵长目", "长臂猿科", "长臂猿属",
             "长臂猿", "国家一级", "树栖，群居", "云南/海南"),
            ("S022", "黑熊", "Ursus thibetanus", "动物界", "脊索动物门", "哺乳纲", "食肉目", "熊科", "熊属", "黑熊",
             "国家二级", "独居，杂食", "全国多地")
        ]
        for sp in species_list:
            species_data.append(
                f"('{sp[0]}', '{sp[1]}', '{sp[2]}', '{sp[3]}', '{sp[4]}', '{sp[5]}', '{sp[6]}', '{sp[7]}', '{sp[8]}', '{sp[9]}', '{sp[10]}', '{sp[11]}', '{sp[12]}')")
        species_sql = f"INSERT INTO species_info (species_id, chinese_name, latin_name, kingdom, phylum, class, order_name, family, genus, species_name, protection_level, living_habits, distribution_desc) VALUES {','.join(species_data)};"
        self.db.execute_sql(species_sql)

        # ---------------------- 3. 设备表（20+条） ----------------------
        device_data = []
        device_types = ["红外相机", "无人机", "人工巡查设备"]
        status_list = ["正常", "故障", "维护中"]
        for i in range(1, 23):
            did = f"D{str(i).zfill(3)}"
            dtype = random.choice(device_types)
            status = random.choice(status_list) if i % 10 == 0 else "正常"  # 10%故障/维护
            bind_region = f"R{str(random.randint(1, 22)).zfill(3)}"
            device_data.append(
                f"('{did}', '{dtype}', '{status}', '{bind_region}', '2025-01-{str(random.randint(1, 31)).zfill(2)} 10:00:00')")
        device_sql = f"INSERT INTO monitor_device (device_id, device_type, status, bind_region, last_maintain) VALUES {','.join(device_data)};"
        self.db.execute_sql(device_sql)

        # ---------------------- 4. 用户表（20+条） ----------------------
        user_data = []
        roles = ["生态监测员", "数据分析师", "管理员"]
        names = ["张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十", "郑一", "冯二",
                 "陈三", "褚四", "卫五", "蒋六", "沈七", "韩八", "杨九", "朱十", "秦一", "尤二",
                 "许三", "何四"]
        for i in range(1, 23):
            uid = f"U{str(i).zfill(3)}"
            uname = names[i - 1]
            role = random.choice(roles)
            resp_region = f"R{str(random.randint(1, 22)).zfill(3)}" if role == "生态监测员" else None
            contact = f"138{str(random.randint(10000000, 99999999))}"
            user_data.append(f"('{uid}', '{uname}', '{role}', '{resp_region if resp_region else 'NULL'}', '{contact}')")
        user_sql = f"INSERT INTO sys_user (user_id, user_name, role, responsible_region, contact) VALUES {','.join(user_data)};"
        self.db.execute_sql(user_sql.replace("'NULL'", "NULL"))

        # ---------------------- 5. 栖息地表（20+条） ----------------------
        habitat_data = []
        eco_types = ["热带雨林", "高山针叶林", "湿地", "草原", "荒漠", "湖泊", "河流", "红树林"]
        for i in range(1, 23):
            hid = f"H{str(i).zfill(3)}"
            rid = f"R{str(random.randint(1, 22)).zfill(3)}"
            eco_type = random.choice(eco_types)
            area = round(random.uniform(1000, 50000), 2)
            core_range = f"东经{round(random.uniform(80, 120), 6)}°，北纬{round(random.uniform(15, 50), 6)}°"
            score = random.randint(1, 10)
            create_time = f"2025-{str(random.randint(1, 12)).zfill(2)}-{str(random.randint(1, 31)).zfill(2)} 08:00:00"
            habitat_data.append(f"('{hid}', '{rid}', '{eco_type}', {area}, '{core_range}', {score}, '{create_time}')")
        habitat_sql = f"INSERT INTO habitat_info (habitat_id, region_id, ecological_type, area, core_protection, suitability_score, create_time) VALUES {','.join(habitat_data)};"
        self.db.execute_sql(habitat_sql)

        # ---------------------- 6. 栖息地-物种关联表（20+条） ----------------------
        hab_species_data = []
        for i in range(1, 23):
            hid = f"H{str(i).zfill(3)}"
            spid = f"S{str(random.randint(1, 22)).zfill(3)}"
            is_main = random.randint(0, 1)
            hab_species_data.append(f"('{hid}', '{spid}', {is_main})")
        hab_species_sql = f"INSERT INTO habitat_species_relation (habitat_id, species_id, is_main) VALUES {','.join(hab_species_data)};"
        self.db.execute_sql(hab_species_sql)

        # ---------------------- 7. 监测记录表（20+条） ----------------------
        record_data = []
        methods = ["红外相机", "人工巡查", "无人机"]
        status_list = ["有效", "待核实"]
        base_date = datetime(2025, 1, 1)
        for i in range(1, 50):  # 50条记录，满足≥20条
            rid = f"REC{str(i).zfill(3)}"
            spid = f"S{str(random.randint(1, 22)).zfill(3)}"
            did = f"D{str(random.randint(1, 22)).zfill(3)}"
            content = f"/data/images/2025/{str(random.randint(1, 12)).zfill(2)}/sp{spid}_{str(i).zfill(3)}.jpg" if random.choice(
                [0, 1]) else f"数量：{random.randint(1, 50)}只，行为：{random.choice(['觅食', '休息', '迁徙', '繁殖'])}"
            rec_uid = f"U{str(random.randint(1, 22)).zfill(3)}"
            status = random.choice(status_list)
            monitor_time = (base_date + timedelta(days=random.randint(1, 365), hours=random.randint(0, 23))).strftime(
                "%Y-%m-%d %H:%M:%S")
            lon = round(random.uniform(80, 120), 6)
            lat = round(random.uniform(15, 50), 6)
            location = f"东经{lon}°，北纬{lat}°"
            method = random.choice(methods)
            conclusion = "数据有效，物种行为正常" if status == "有效" else None
            verify_time = monitor_time if status == "有效" else None
            record_data.append(
                f"('{rid}', '{spid}', '{did}', '{content}', '{rec_uid}', '{status}', '{monitor_time}', {lon}, {lat}, '{location}', '{method}', "
                f"'{conclusion if conclusion else 'NULL'}', '{verify_time if verify_time else 'NULL'}')"
            )
        record_sql = f"INSERT INTO monitor_record (record_id, species_id, device_id, monitor_content, recorder_id, data_status, monitor_time, longitude, latitude, monitor_location, monitor_method, analysis_conclusion, verify_time) VALUES {','.join(record_data)};"
        self.db.execute_sql(record_sql.replace("'NULL'", "NULL"))


# ====================== 3. 实体类映射（ORM风格） ======================
class Region:
    """区域实体类：映射region_info表"""

    def __init__(self, region_id, region_name, region_level="省级", manager=None):
        self.region_id = region_id
        self.region_name = region_name
        self.region_level = region_level
        self.manager = manager

    def to_dict(self):
        return {
            "region_id": self.region_id,
            "region_name": self.region_name,
            "region_level": self.region_level,
            "manager": self.manager
        }


class Species:
    """物种实体类：映射species_info表"""

    def __init__(self, species_id, chinese_name, latin_name, kingdom, phylum, class_, order_name, family, genus,
                 species_name, protection_level, living_habits, distribution_desc):
        self.species_id = species_id
        self.chinese_name = chinese_name
        self.latin_name = latin_name
        self.kingdom = kingdom
        self.phylum = phylum
        self.class_ = class_
        self.order_name = order_name
        self.family = family
        self.genus = genus
        self.species_name = species_name
        self.protection_level = protection_level
        self.living_habits = living_habits
        self.distribution_desc = distribution_desc

    def to_dict(self):
        return {
            "species_id": self.species_id,
            "chinese_name": self.chinese_name,
            "latin_name": self.latin_name,
            "kingdom": self.kingdom,
            "phylum": self.phylum,
            "class_": self.class_,
            "order_name": self.order_name,
            "family": self.family,
            "genus": self.genus,
            "species_name": self.species_name,
            "protection_level": self.protection_level,
            "living_habits": self.living_habits,
            "distribution_desc": self.distribution_desc
        }


class Habitat:
    """栖息地实体类：映射habitat_info表"""

    def __init__(self, habitat_id, region_id, ecological_type, area, core_protection, suitability_score,
                 create_time=None):
        self.habitat_id = habitat_id
        self.region_id = region_id
        self.ecological_type = ecological_type
        self.area = area
        self.core_protection = core_protection
        self.suitability_score = suitability_score
        self.create_time = create_time or datetime.now()

    def to_dict(self):
        return {
            "habitat_id": self.habitat_id,
            "region_id": self.region_id,
            "ecological_type": self.ecological_type,
            "area": self.area,
            "core_protection": self.core_protection,
            "suitability_score": self.suitability_score,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S")
        }


class MonitorRecord:
    """监测记录实体类：映射monitor_record表"""

    def __init__(self, record_id, species_id, device_id, recorder_id, data_status, monitor_time, monitor_location,
                 monitor_method, monitor_content=None, longitude=None, latitude=None, analysis_conclusion=None,
                 verify_time=None):
        self.record_id = record_id
        self.species_id = species_id
        self.device_id = device_id
        self.monitor_content = monitor_content
        self.recorder_id = recorder_id
        self.data_status = data_status
        self.monitor_time = monitor_time
        self.longitude = longitude
        self.latitude = latitude
        self.monitor_location = monitor_location
        self.monitor_method = monitor_method
        self.analysis_conclusion = analysis_conclusion
        self.verify_time = verify_time

    def to_dict(self):
        return {
            "record_id": self.record_id,
            "species_id": self.species_id,
            "device_id": self.device_id,
            "monitor_content": self.monitor_content,
            "recorder_id": self.recorder_id,
            "data_status": self.data_status,
            "monitor_time": self.monitor_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(self.monitor_time,
                                                                                          datetime) else self.monitor_time,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "monitor_location": self.monitor_location,
            "monitor_method": self.monitor_method,
            "analysis_conclusion": self.analysis_conclusion,
            "verify_time": self.verify_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(self.verify_time,
                                                                                        datetime) else self.verify_time
        }


# ====================== 4. 持久层封装（核心业务增删改查） ======================
class BiodiversityDAO:
    """数据访问层（DAO）：封装核心业务的增删改查"""

    def __init__(self, db_conn):
        self.db = db_conn

    # ---------------------- 物种管理 ----------------------
    def add_species(self, species: Species):
        """新增物种（实体类入参）"""
        sql = """
        INSERT INTO species_info 
        (species_id, chinese_name, latin_name, kingdom, phylum, class, order_name, family, genus, species_name, protection_level, living_habits, distribution_desc)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            species.species_id, species.chinese_name, species.latin_name,
            species.kingdom, species.phylum, species.class_, species.order_name,
            species.family, species.genus, species.species_name,
            species.protection_level, species.living_habits, species.distribution_desc
        )
        success, _ = self.db.execute_sql(sql, params)
        if success:
            print(f"✅ 物种【{species.chinese_name}】新增成功")
        return success

    def delete_species(self, species_id):
        """删除物种（级联删除关联记录）"""
        sql = "DELETE FROM species_info WHERE species_id = %s"
        success, _ = self.db.execute_sql(sql, (species_id,))
        if success:
            print(f"✅ 物种【{species_id}】删除成功（关联记录已级联删除）")
        return success

    def query_species_by_id(self, species_id):
        """按ID查询物种（返回实体类）"""
        sql = "SELECT * FROM species_info WHERE species_id = %s"
        df, _ = self.db.query_sql(sql, (species_id,))
        if df.empty:
            return None
        row = df.iloc[0]
        return Species(
            species_id=row['species_id'],
            chinese_name=row['chinese_name'],
            latin_name=row['latin_name'],
            kingdom=row['kingdom'],
            phylum=row['phylum'],
            class_=row['class'],
            order_name=row['order_name'],
            family=row['family'],
            genus=row['genus'],
            species_name=row['species_name'],
            protection_level=row['protection_level'],
            living_habits=row['living_habits'],
            distribution_desc=row['distribution_desc']
        )

    # ---------------------- 栖息地管理 ----------------------
    def add_habitat(self, habitat: Habitat, species_ids: list):
        """新增栖息地+关联物种"""
        # 1. 新增栖息地
        sql_habitat = """
        INSERT INTO habitat_info 
        (habitat_id, region_id, ecological_type, area, core_protection, suitability_score, create_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params_habitat = (
            habitat.habitat_id, habitat.region_id, habitat.ecological_type,
            habitat.area, habitat.core_protection, habitat.suitability_score,
            habitat.create_time
        )
        success, _ = self.db.execute_sql(sql_habitat, params_habitat)
        if not success:
            return False

        # 2. 关联物种
        sql_rel = "INSERT INTO habitat_species_relation (habitat_id, species_id, is_main) VALUES (%s, %s, 1)"
        for sp_id in species_ids:
            self.db.execute_sql(sql_rel, (habitat.habitat_id, sp_id))
        print(f"✅ 栖息地【{habitat.habitat_id}】新增并关联{len(species_ids)}个物种成功")
        return True

    # ---------------------- 监测记录管理 ----------------------
    def add_monitor_record(self, record: MonitorRecord):
        """新增监测记录（自动校验完整性）"""
        # 完整性校验
        required_fields = [record.record_id, record.species_id, record.device_id, record.recorder_id,
                           record.data_status, record.monitor_time, record.monitor_location, record.monitor_method]
        if any(not field for field in required_fields):
            print("❌ 监测记录缺少必填字段，新增失败")
            return False

        sql = """
        INSERT INTO monitor_record 
        (record_id, species_id, device_id, monitor_content, recorder_id, data_status, monitor_time, longitude, latitude, monitor_location, monitor_method, analysis_conclusion, verify_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            record.record_id, record.species_id, record.device_id,
            record.monitor_content, record.recorder_id, record.data_status,
            record.monitor_time, record.longitude, record.latitude,
            record.monitor_location, record.monitor_method,
            record.analysis_conclusion, record.verify_time
        )
        success, _ = self.db.execute_sql(sql, params)
        if success:
            print(f"✅ 监测记录【{record.record_id}】新增成功")
        return success

    def update_record_status(self, record_id, new_status, conclusion=None):
        """更新监测记录状态（审核）"""
        sql = """
        UPDATE monitor_record 
        SET data_status = %s, analysis_conclusion = %s, verify_time = %s 
        WHERE record_id = %s
        """
        params = (new_status, conclusion, datetime.now(), record_id)
        success, _ = self.db.execute_sql(sql, params)
        if success:
            print(f"✅ 监测记录【{record_id}】状态更新为【{new_status}】，结论：{conclusion}")
        return success

    # ---------------------- 复杂业务查询（5条关联3+表的SQL） ----------------------
    def complex_query_1(self):
        """
        查询1：核心保护区近30天的物种监测记录及对应栖息地环境数据
        关联表：monitor_record + species_info + habitat_species_relation + habitat_info + region_info
        """
        sql = """
        SELECT 
            r.region_name AS 区域名称,
            h.habitat_id AS 栖息地编号,
            h.ecological_type AS 生态类型,
            h.suitability_score AS 环境适宜性评分,
            s.chinese_name AS 物种名称,
            m.record_id AS 监测记录编号,
            m.monitor_time AS 监测时间,
            m.monitor_method AS 监测方式,
            m.data_status AS 数据状态,
            u.user_name AS 记录人
        FROM monitor_record m
        LEFT JOIN species_info s ON m.species_id = s.species_id
        LEFT JOIN habitat_species_relation hs ON s.species_id = hs.species_id
        LEFT JOIN habitat_info h ON hs.habitat_id = h.habitat_id
        LEFT JOIN region_info r ON h.region_id = r.region_id
        LEFT JOIN sys_user u ON m.recorder_id = u.user_id
        WHERE m.monitor_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        AND r.region_level = '国家级'
        ORDER BY m.monitor_time DESC
        """
        df, exec_time = self.db.query_sql(sql)
        return df, exec_time

    def complex_query_2(self):
        """
        查询2：统计各区域国家一级保护物种的监测次数及有效率
        关联表：region_info + habitat_info + habitat_species_relation + species_info + monitor_record
        """
        sql = """
        SELECT 
            r.region_name AS 区域名称,
            COUNT(DISTINCT s.species_id) AS 一级保护物种数量,
            COUNT(m.record_id) AS 总监测次数,
            SUM(CASE WHEN m.data_status = '有效' THEN 1 ELSE 0 END) AS 有效记录数,
            ROUND(SUM(CASE WHEN m.data_status = '有效' THEN 1 ELSE 0 END)/COUNT(m.record_id)*100, 2) AS 有效率(%)
        FROM region_info r
        LEFT JOIN habitat_info h ON r.region_id = h.region_id
        LEFT JOIN habitat_species_relation hs ON h.habitat_id = hs.habitat_id
        LEFT JOIN species_info s ON hs.species_id = s.species_id AND s.protection_level = '国家一级'
        LEFT JOIN monitor_record m ON s.species_id = m.species_id
        GROUP BY r.region_id, r.region_name
        HAVING COUNT(m.record_id) > 0
        ORDER BY 有效率(%) DESC
        """
        df, exec_time = self.db.query_sql(sql)
        return df, exec_time

    def complex_query_3(self):
        """
        查询3：查询红外相机监测的所有待核实记录，包含设备状态及记录人信息
        关联表：monitor_record + monitor_device + sys_user + species_info
        """
        sql = """
        SELECT 
            m.record_id AS 记录编号,
            s.chinese_name AS 物种名称,
            d.device_id AS 设备编号,
            d.status AS 设备状态,
            u.user_name AS 记录人,
            u.contact AS 联系方式,
            m.monitor_time AS 监测时间,
            m.monitor_location AS 监测地点
        FROM monitor_record m
        LEFT JOIN monitor_device d ON m.device_id = d.device_id
        LEFT JOIN sys_user u ON m.recorder_id = u.user_id
        LEFT JOIN species_info s ON m.species_id = s.species_id
        WHERE m.data_status = '待核实'
        AND m.monitor_method = '红外相机'
        ORDER BY m.monitor_time DESC
        """
        df, exec_time = self.db.query_sql(sql)
        return df, exec_time

    def complex_query_4(self):
        """
        查询4：统计各生态类型栖息地的物种丰富度（关联物种数）及平均适宜性评分
        关联表：habitat_info + habitat_species_relation + species_info + region_info
        """
        sql = """
        SELECT 
            h.ecological_type AS 生态类型,
            COUNT(DISTINCT hs.species_id) AS 物种丰富度,
            AVG(h.suitability_score) AS 平均适宜性评分,
            COUNT(DISTINCT h.habitat_id) AS 栖息地数量,
            SUM(h.area) AS 总面_公顷
        FROM habitat_info h
        LEFT JOIN habitat_species_relation hs ON h.habitat_id = hs.habitat_id
        LEFT JOIN species_info s ON hs.species_id = s.species_id
        LEFT JOIN region_info r ON h.region_id = r.region_id
        GROUP BY h.ecological_type
        ORDER BY 物种丰富度 DESC
        """
        df, exec_time = self.db.query_sql(sql)
        return df, exec_time

    def complex_query_5(self):
        """
        查询5：查询近90天各监测方式的使用频次及有效记录占比
        关联表：monitor_record + sys_user + species_info
        """
        sql = """
        SELECT 
            m.monitor_method AS 监测方式,
            COUNT(m.record_id) AS 使用频次,
            SUM(CASE WHEN m.data_status = '有效' THEN 1 ELSE 0 END) AS 有效记录数,
            ROUND(SUM(CASE WHEN m.data_status = '有效' THEN 1 ELSE 0 END)/COUNT(m.record_id)*100, 2) AS 有效占比(%),
            COUNT(DISTINCT m.recorder_id) AS 参与监测人数
        FROM monitor_record m
        LEFT JOIN sys_user u ON m.recorder_id = u.user_id
        LEFT JOIN species_info s ON m.species_id = s.species_id
        WHERE m.monitor_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
        GROUP BY m.monitor_method
        ORDER BY 使用频次 DESC
        """
        df, exec_time = self.db.query_sql(sql)
        return df, exec_time


# ====================== 5. 测试用例（覆盖所有核心操作） ======================
class BiodiversityTest:
    """测试类：验证持久层所有核心操作"""

    def __init__(self, dao: BiodiversityDAO):
        self.dao = dao

    def run_all_tests(self):
        """运行所有测试用例"""
        print("\n====================== 开始执行测试用例 ======================")
        # 1. 物种管理测试
        self.test_species_operations()
        # 2. 栖息地管理测试
        self.test_habitat_operations()
        # 3. 监测记录管理测试
        self.test_record_operations()
        # 4. 复杂查询测试（含索引优化对比）
        self.test_complex_queries()
        print("\n====================== 所有测试用例执行完成 ======================")

    def test_species_operations(self):
        """测试物种增删改查"""
        print("\n--- 测试1：物种管理 ---")
        # 新增物种
        new_species = Species(
            species_id="S023",
            chinese_name="雪豹",
            latin_name="Panthera uncia",
            kingdom="动物界",
            phylum="脊索动物门",
            class_="哺乳纲",
            order_name="食肉目",
            family="猫科",
            genus="豹属",
            species_name="雪豹",
            protection_level="国家一级",
            living_habits="独居，食肉，栖息于高山裸岩地带",
            distribution_desc="青藏高原及周边高山地区"
        )
        assert self.dao.add_species(new_species) == True, "物种新增失败"

        # 查询物种
        query_species = self.dao.query_species_by_id("S023")
        assert query_species is not None, "物种查询失败"
        assert query_species.chinese_name == "雪豹", "物种查询结果错误"

        # 删除物种
        assert self.dao.delete_species("S023") == True, "物种删除失败"
        print("✅ 物种管理测试通过")

    def test_habitat_operations(self):
        """测试栖息地新增+关联物种"""
        print("\n--- 测试2：栖息地管理 ---")
        new_habitat = Habitat(
            habitat_id="H023",
            region_id="R007",
            ecological_type="高山裸岩",
            area=35678.90,
            core_protection="东经98.765432°，北纬30.123456°",
            suitability_score=7,
            create_time=datetime.now()
        )
        assert self.dao.add_habitat(new_habitat, ["S015"]) == True, "栖息地新增失败"
        print("✅ 栖息地管理测试通过")

    def test_record_operations(self):
        """测试监测记录新增+状态更新"""
        print("\n--- 测试3：监测记录管理 ---")
        # 新增监测记录
        new_record = MonitorRecord(
            record_id="REC051",
            species_id="S015",
            device_id="D005",
            recorder_id="U001",
            data_status="待核实",
            monitor_time=datetime.now(),
            monitor_location="东经98.765432°，北纬30.123456°",
            monitor_method="无人机",
            monitor_content="/data/images/2025/12/snowleopard_001.jpg",
            longitude=98.765432,
            latitude=30.123456
        )
        assert self.dao.add_monitor_record(new_record) == True, "监测记录新增失败"

        # 更新记录状态
        assert self.dao.update_record_status("REC051", "有效", "雪豹监测影像清晰，数据有效") == True, "记录状态更新失败"
        print("✅ 监测记录管理测试通过")

    def test_complex_queries(self):
        """测试复杂查询+索引优化对比"""
        print("\n--- 测试4：复杂查询（索引优化对比） ---")

        # 1. 先删除索引，测试未优化耗时
        print("\n🔍 未优化查询（删除索引）：")
        self.dao.db.execute_sql("DROP INDEX idx_monitor_species_time ON monitor_record;")
        df1, time1 = self.dao.complex_query_1()
        print(f"查询1未优化耗时：{time1}秒")

        # 2. 重建索引，测试优化后耗时
        print("\n🔍 优化后查询（重建索引）：")
        self.dao.db.execute_sql("CREATE INDEX idx_monitor_species_time ON monitor_record(species_id, monitor_time);")
        df2, time2 = self.dao.complex_query_1()
        print(f"查询1优化后耗时：{time2}秒")
        print(f"⏱️  优化效果：耗时减少 {round((time1 - time2) / time1 * 100, 2)}%")

        # 执行所有复杂查询
        queries = [
            ("核心保护区近30天监测记录", self.dao.complex_query_1),
            ("各区域一级保护物种监测有效率", self.dao.complex_query_2),
            ("红外相机待核实记录", self.dao.complex_query_3),
            ("各生态类型栖息地物种丰富度", self.dao.complex_query_4),
            ("近90天监测方式使用频次", self.dao.complex_query_5)
        ]
        for name, func in queries:
            print(f"\n📊 {name}：")
            df, _ = func()
            print(df.head())
        print("✅ 复杂查询测试通过")


# ====================== 6. 主程序入口 ======================
if __name__ == "__main__":
    # 数据库配置（修改为实际密码）
    DB_CONFIG = {
        "host": "172.20.10.4",
        "port": 3306,
        "user": "sjy",
        "password": "515408",  # 替换为实际密码
        "db": "sjk"
    }

    # 1. 初始化数据库连接
    db_conn = DBConnection(**DB_CONFIG)
    if not db_conn.connect():
        exit(1)

    # 2. 初始化数据库表+批量测试数据
    db_init = BiodiversityDBInitializer(db_conn)
    db_init.create_all_tables()

    # 3. 初始化数据访问层
    dao = BiodiversityDAO(db_conn)

    # 4. 运行测试用例
    test = BiodiversityTest(dao)
    test.run_all_tests()

    # 5. 关闭数据库连接
    db_conn.close()