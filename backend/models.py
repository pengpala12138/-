from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import CheckConstraint, Index

db = SQLAlchemy()


# 1. 区域表
class RegionInfo(db.Model):
    __tablename__ = "region_info"
    region_id = db.Column(db.String(20), primary_key=True, comment="区域编号")
    region_name = db.Column(db.String(50), nullable=False, comment="区域名称")

    # 关联：栖息地/设备
    habitats = db.relationship("HabitatInfo", backref="region", cascade="all, delete-orphan")
    devices = db.relationship("MonitorDevice", backref="region", cascade="all, delete-orphan")


# 2. 物种表
class SpeciesInfo(db.Model):
    __tablename__ = "species_info"
    species_id = db.Column(db.String(20), primary_key=True, comment="物种编号")
    chinese_name = db.Column(db.String(100), nullable=False, comment="中文名称")
    latin_name = db.Column(db.String(200), nullable=False, comment="拉丁名")
    kingdom = db.Column(db.String(50), nullable=False, comment="界")
    phylum = db.Column(db.String(50), nullable=False, comment="门")
    class_name = db.Column("class", db.String(50), nullable=False, comment="纲")  # 规避关键字
    order_name = db.Column(db.String(50), nullable=False, comment="目")
    family = db.Column(db.String(50), nullable=False, comment="科")
    genus = db.Column(db.String(50), nullable=False, comment="属")
    species_name = db.Column(db.String(50), nullable=False, comment="种")
    protection_level = db.Column(db.String(20), nullable=False, comment="保护级别")
    living_habits = db.Column(db.Text, nullable=False, comment="生存习性")
    distribution_desc = db.Column(db.Text, nullable=False, comment="分布范围")

    # 约束+索引（修复：补充保护级别枚举约束）
    __table_args__ = (
        CheckConstraint("protection_level IN ('国家一级', '国家二级', '无')", name="ck_protection_level"),
        Index("idx_protection_level", "protection_level"),
        Index("idx_species_name", "chinese_name", "latin_name", unique=True),
    )

    # 关联：监测记录/栖息地-物种关联
    monitor_records = db.relationship("MonitorRecord", backref="species", cascade="all, delete-orphan")
    habitat_relations = db.relationship("HabitatSpeciesRelation", backref="species", cascade="all, delete-orphan")


# 3. 栖息地表
class HabitatInfo(db.Model):
    __tablename__ = "habitat_info"
    habitat_id = db.Column(db.String(20), primary_key=True, comment="栖息地编号")
    region_id = db.Column(db.String(20), db.ForeignKey("region_info.region_id", ondelete="CASCADE"), nullable=False)
    ecological_type = db.Column(db.String(50), nullable=False, comment="生态类型")
    area = db.Column(db.DECIMAL(10, 2), nullable=False, comment="面积（公顷）")
    core_protection = db.Column(db.Text, nullable=False, comment="核心保护范围")
    suitability_score = db.Column(db.Integer, nullable=False, comment="适宜性评分")

    # 约束+索引（修复：补充面积/评分约束）
    __table_args__ = (
        CheckConstraint("area > 0", name="ck_habitat_area"),
        CheckConstraint("suitability_score BETWEEN 1 AND 10", name="ck_suitability_score"),
        Index("idx_ecological_type", "ecological_type"),
        Index("idx_suitability_score", "suitability_score"),
    )

    # 关联：栖息地-物种关联
    species_relations = db.relationship("HabitatSpeciesRelation", backref="habitat", cascade="all, delete-orphan")


# 4. 栖息地-物种关联表
class HabitatSpeciesRelation(db.Model):
    __tablename__ = "habitat_species_relation"
    habitat_id = db.Column(db.String(20), db.ForeignKey("habitat_info.habitat_id", ondelete="CASCADE"),
                           primary_key=True)
    species_id = db.Column(db.String(20), db.ForeignKey("species_info.species_id", ondelete="CASCADE"),
                           primary_key=True)
    is_main = db.Column(db.Integer, default=1, comment="是否主要物种（1=是，0=否）")

    __table_args__ = (
        Index("idx_species_habitat", "species_id", "habitat_id"),
    )


# 5. 用户表（修复：补充密码/登录安全字段 + 外键级联策略）
class SysUser(db.Model):
    __tablename__ = "sys_user"
    user_id = db.Column(db.String(20), primary_key=True, comment="用户ID")
    user_name = db.Column(db.String(50), nullable=False, comment="用户名")
    password_hash = db.Column(db.String(128), nullable=False, comment="密码哈希（SHA256）")
    role = db.Column(db.String(20), nullable=False, comment="角色")
    # 修复：补充ondelete="SET NULL"，避免删除区域时用户表报错
    responsible_region = db.Column(db.String(20), db.ForeignKey("region_info.region_id", ondelete="SET NULL"), comment="负责区域")
    login_failed = db.Column(db.Integer, default=0, comment="登录失败次数")
    is_locked = db.Column(db.Integer, default=0, comment="是否锁定（1=是，0=否）")
    last_login = db.Column(db.DateTime, comment="最后登录时间")

    __table_args__ = (
        Index("idx_role", "role"),
        Index("idx_responsible_region", "responsible_region"),
    )

    # 关联：监测记录
    monitor_records = db.relationship("MonitorRecord", backref="recorder", cascade="all, delete-orphan")


# 6. 设备表（修复：补充关联字段+约束）
class MonitorDevice(db.Model):
    __tablename__ = "monitor_device"
    device_id = db.Column(db.String(20), primary_key=True, comment="设备编号")
    device_type = db.Column(db.String(50), nullable=False, comment="设备类型")
    region_id = db.Column(db.String(20), db.ForeignKey("region_info.region_id", ondelete="CASCADE"), nullable=False)
    install_time = db.Column(db.Date, comment="安装时间")
    calibration_cycle = db.Column(db.String(8), comment="校准周期")
    operation_status = db.Column(db.String(10), nullable=False, comment="运行状态")
    comm_proto = db.Column(db.String(50), comment="通信协议")
    status_update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="状态更新时间")

    # 约束+索引
    __table_args__ = (
        CheckConstraint("operation_status IN ('正常', '故障', '离线')", name="ck_operation_status"),
        Index("idx_device_type", "device_type"),
        Index("idx_operation_status", "operation_status"),
    )

    # 关联：监测记录
    monitor_records = db.relationship("MonitorRecord", backref="device", cascade="all, delete-orphan")


# 7. 监测记录表（修复：补充约束+关联）
class MonitorRecord(db.Model):
    __tablename__ = "monitor_record"
    record_id = db.Column(db.String(30), primary_key=True, comment="记录编号")
    species_id = db.Column(db.String(20), db.ForeignKey("species_info.species_id", ondelete="CASCADE"), nullable=False)
    device_id = db.Column(db.String(20), db.ForeignKey("monitor_device.device_id", ondelete="CASCADE"), nullable=False)
    monitor_time = db.Column(db.DateTime, nullable=False, comment="监测时间")
    longitude = db.Column(db.DECIMAL(10, 6), comment="经度")
    latitude = db.Column(db.DECIMAL(10, 6), comment="纬度")
    monitor_location = db.Column(db.String(100), nullable=False, comment="监测地点")
    monitor_method = db.Column(db.String(20), nullable=False, comment="监测方式")
    monitor_content = db.Column(db.String(255), comment="监测内容")
    recorder_id = db.Column(db.String(20), db.ForeignKey("sys_user.user_id", ondelete="CASCADE"), nullable=False)
    data_status = db.Column(db.String(20), default="待核实", nullable=False, comment="数据状态")
    analysis_conclusion = db.Column(db.Text, comment="分析结论")
    verify_time = db.Column(db.DateTime, comment="审核时间")

    # 约束+索引
    __table_args__ = (
        CheckConstraint("monitor_method IN ('红外相机', '人工巡查', '无人机')", name="ck_monitor_method"),
        CheckConstraint("data_status IN ('有效', '待核实')", name="ck_data_status"),
        Index("idx_species_time", "species_id", "monitor_time"),
        Index("idx_device_id", "device_id"),
        Index("idx_data_status", "data_status"),
        Index("idx_recorder_time", "recorder_id", "monitor_time"),
        Index("idx_monitor_time", "monitor_time"),
    )