from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import hashlib
import re

# 移除 SysUser 导入（删除登录功能后无需用户表）
from models import db, RegionInfo, SpeciesInfo, MonitorRecord, MonitorDevice, HabitatInfo, \
    HabitatSpeciesRelation, SysUser
from config import DB_CONFIG, get_db

app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['db']}?charset={DB_CONFIG['charset']}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "echo": False,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 300
}
app.config['SECRET_KEY'] = 'your-secret-key-123456'

# 初始化
db.init_app(app)
CORS(app)


# -------------------- 工具函数 --------------------
def hash_password(password):
    """SHA256加密密码（保留，若后续有其他用途）"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_species_id():
    """生成物种ID：SP+6位数字"""
    db_session = next(get_db())
    try:
        max_id = db_session.query(db.func.max(SpeciesInfo.species_id)).scalar()
        if not max_id:
            return "SP000001"
        num_part = int(max_id[2:]) + 1
        return f"SP{num_part:06d}"
    finally:
        db_session.close()


def generate_habitat_id():
    """生成栖息地ID：HB+6位数字"""
    db_session = next(get_db())
    try:
        max_id = db_session.query(db.func.max(HabitatInfo.habitat_id)).scalar()
        if not max_id:
            return "HB000001"
        num_part = int(max_id[2:]) + 1
        return f"HB{num_part:06d}"
    finally:
        db_session.close()


def extract_count_from_content(content):
    """从监测内容中提取数量"""
    if not content:
        return "无"
    count_match = re.search(r'(\d+)只', content)
    return f"{count_match.group(1)}只" if count_match else "无"


def generate_record_id():
    """生成唯一记录ID：REC+毫秒级时间戳"""
    return f"REC{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}"


# -------------------- 页面路由（删除login路由） --------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/species')
def species_page():
    return render_template('species.html')


@app.route('/monitor')
def monitor_page():
    return render_template('monitor.html')


@app.route('/habitat')
def habitat_page():
    return render_template('habitat.html')


# -------------------- 接口：获取物种列表 --------------------
@app.route('/api/species', methods=['GET'])
def get_species():
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 10))
    page = max(page, 1)
    size = max(1, min(size, 100))

    keyword = request.args.get('keyword', '')
    protection_level = request.args.get('protectionLevel', '')

    db_session = next(get_db())
    try:
        query = db_session.query(SpeciesInfo)
        if keyword:
            query = query.filter(SpeciesInfo.chinese_name.like(f'%{keyword}%'))
        if protection_level:
            query = query.filter(SpeciesInfo.protection_level == protection_level)

        total = query.count()
        species_list = query.offset((page - 1) * size).limit(size).all()

        data = [{
            "speciesId": s.species_id,
            "chineseName": s.chinese_name,
            "latinName": s.latin_name,
            "kingdom": s.kingdom,
            "phylum": s.phylum,
            "class": s.class_name,
            "order": s.order_name,
            "family": s.family,
            "genus": s.genus,
            "species": s.species_name,
            "protectionLevel": s.protection_level,
            "livingHabits": s.living_habits,
            "distribution": s.distribution_desc
        } for s in species_list]

        return jsonify({
            "code": 200,
            "msg": "查询成功",
            "data": data,
            "total": total,
            "page": page,
            "size": size
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：新增物种 --------------------
@app.route('/api/species', methods=['POST'])
def add_species():
    data = request.json
    db_session = next(get_db())
    try:
        species_id = generate_species_id()

        new_species = SpeciesInfo(
            species_id=species_id,
            chinese_name=data['chineseName'],
            latin_name=data['latinName'],
            kingdom=data['kingdom'],
            phylum=data['phylum'],
            class_name=data['class'],
            order_name=data['order'],
            family=data['family'],
            genus=data['genus'],
            species_name=data['species'],
            protection_level=data['protectionLevel'],
            living_habits=data['livingHabits'],
            distribution_desc=data['distribution']
        )

        db_session.add(new_species)
        db_session.commit()

        return jsonify({
            "code": 200,
            "msg": "物种新增成功",
            "data": {"speciesId": species_id}
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"新增失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：编辑物种 --------------------
@app.route('/api/species/<species_id>', methods=['PUT'])
def update_species(species_id):
    data = request.json
    db_session = next(get_db())
    try:
        species = db_session.query(SpeciesInfo).filter_by(species_id=species_id).first()
        if not species:
            return jsonify({"code": 404, "msg": "物种不存在"})

        species.chinese_name = data['chineseName']
        species.latin_name = data['latinName']
        species.kingdom = data['kingdom']
        species.phylum = data['phylum']
        species.class_name = data['class']
        species.order_name = data['order']
        species.family = data['family']
        species.genus = data['genus']
        species.species_name = data['species']
        species.protection_level = data['protectionLevel']
        species.living_habits = data['livingHabits']
        species.distribution_desc = data['distribution']

        db_session.commit()

        return jsonify({"code": 200, "msg": "物种更新成功"})
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"更新失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：删除物种 --------------------
@app.route('/api/species/<species_id>', methods=['DELETE'])
def delete_species(species_id):
    db_session = next(get_db())
    try:
        species = db_session.query(SpeciesInfo).filter_by(species_id=species_id).first()
        if not species:
            return jsonify({"code": 404, "msg": "物种不存在"})

        db_session.delete(species)
        db_session.commit()

        return jsonify({"code": 200, "msg": "物种删除成功"})
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"删除失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：获取监测记录 --------------------
@app.route('/api/monitor-records', methods=['GET'])
def get_monitor_records():
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 10))
    page = max(page, 1)
    size = max(1, min(size, 100))

    species_name = request.args.get('speciesName', '')
    monitor_date = request.args.get('monitorDate', '')
    monitor_region = request.args.get('monitorRegion', '')
    data_status = request.args.get('status', '')

    db_session = next(get_db())
    try:
        # 移除 SysUser 关联查询
        query = db_session.query(MonitorRecord).join(
            SpeciesInfo, MonitorRecord.species_id == SpeciesInfo.species_id, isouter=True
        )

        if species_name:
            query = query.filter(SpeciesInfo.chinese_name.like(f'%{species_name}%'))
        if monitor_date:
            query = query.filter(db.func.date(MonitorRecord.monitor_time) == monitor_date)
        if monitor_region:
            query = query.filter(MonitorRecord.monitor_location.like(f'%{monitor_region}%'))
        if data_status:
            query = query.filter(MonitorRecord.data_status == data_status)

        total = query.count()
        records = query.offset((page - 1) * size).limit(size).all()

        data = [{
            "recordId": r.record_id,
            "speciesName": r.species.chinese_name if r.species else "未知物种",
            "monitorDate": r.monitor_time.strftime('%Y-%m-%d'),
            "monitorRegion": r.monitor_location,
            "count": extract_count_from_content(r.monitor_content),
            "recorderName": "系统默认" if not r.recorder_id else r.recorder_id,  # 简化记录人展示
            "status": r.data_status,
            "statusBadge": "bg-success" if r.data_status == "有效" else "bg-warning",
            "deviceId": r.device_id,
            "monitorTime": r.monitor_time.strftime('%Y-%m-%d %H:%M:%S'),
            "monitorMethod": r.monitor_method,
            "longitude": r.longitude,
            "latitude": r.latitude,
            "monitorContent": r.monitor_content,
            "analysisConclusion": r.analysis_conclusion,
            "verifyTime": r.verify_time.strftime('%Y-%m-%d %H:%M:%S') if r.verify_time else ""
        } for r in records]

        return jsonify({
            "code": 200,
            "msg": "查询成功",
            "data": data,
            "total": total,
            "page": page,
            "size": size
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：获取单条监测记录 --------------------
@app.route('/api/monitor-records/<record_id>', methods=['GET'])
def get_single_monitor_record(record_id):
    db_session = next(get_db())
    try:
        record = db_session.query(MonitorRecord).filter_by(record_id=record_id).first()
        if not record:
            return jsonify({"code": 404, "msg": "记录不存在"})

        data = {
            "recordId": record.record_id,
            "speciesId": record.species_id,
            "speciesName": record.species.chinese_name if record.species else "",
            "deviceId": record.device_id,
            "monitorTime": record.monitor_time.strftime('%Y-%m-%d %H:%M:%S'),
            "longitude": record.longitude,
            "latitude": record.latitude,
            "monitorLocation": record.monitor_location,
            "monitorMethod": record.monitor_method,
            "monitorContent": record.monitor_content,
            "analysisConclusion": record.analysis_conclusion,
            "recorderId": record.recorder_id or "system",
            "recorderName": "系统默认" if not record.recorder_id else record.recorder_id,
            "dataStatus": record.data_status,
            "verifyTime": record.verify_time.strftime('%Y-%m-%d %H:%M:%S') if record.verify_time else ""
        }
        return jsonify({"code": 200, "msg": "查询成功", "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：新增监测记录（删除用户校验） --------------------
@app.route('/api/monitor-records', methods=['POST'])
def add_monitor_record():
    data = request.json
    db_session = next(get_db())
    try:
        # 校验必填字段（保留，但移除 recorderId 关联用户校验）
        required_fields = ['speciesId', 'deviceId', 'monitorTime', 'monitorLocation', 'monitorMethod']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"code": 400, "msg": f"字段 {field} 不能为空"})

        # 处理经纬度
        longitude = None
        if data.get('longitude'):
            try:
                longitude = float(data['longitude'])
                if not (-180 <= longitude <= 180):
                    return jsonify({"code": 400, "msg": "经度范围必须在-180到180之间"})
            except ValueError:
                return jsonify({"code": 400, "msg": "经度必须是有效的数字"})

        latitude = None
        if data.get('latitude'):
            try:
                latitude = float(data['latitude'])
                if not (-90 <= latitude <= 90):
                    return jsonify({"code": 400, "msg": "纬度范围必须在-90到90之间"})
            except ValueError:
                return jsonify({"code": 400, "msg": "纬度必须是有效的数字"})

        # 处理日期
        monitor_time_str = data['monitorTime']
        try:
            monitor_time_str = monitor_time_str.replace('T', ' ')
            if len(monitor_time_str.split(':')) == 2:
                monitor_time_str += ':00'
            monitor_time = datetime.strptime(monitor_time_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"code": 400, "msg": "监测日期格式错误，需为YYYY-MM-DD HH:MM:SS"})

        # 生成记录ID
        record_id = generate_record_id()

        # 创建记录（recorderId 设为默认值）
        new_record = MonitorRecord(
            record_id=record_id,
            species_id=data['speciesId'],
            device_id=data['deviceId'],
            monitor_time=monitor_time,
            longitude=longitude,
            latitude=latitude,
            monitor_location=data['monitorLocation'],
            monitor_method=data['monitorMethod'],
            monitor_content=data.get('monitorContent', ''),
            analysis_conclusion=data.get('analysisConclusion', ''),
            recorder_id=data.get('recorderId', 'system'),
            data_status="待核实",
            verify_time=None
        )

        db_session.add(new_record)
        db_session.commit()

        return jsonify({
            "code": 200,
            "msg": "监测记录新增成功",
            "data": {
                "recordId": record_id,
                "recorderName": "系统默认"
            }
        })
    except ValueError as e:
        db_session.rollback()
        return jsonify({"code": 400, "msg": f"参数格式错误：{str(e)}"})
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"新增失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：编辑监测记录（删除用户校验） --------------------
@app.route('/api/monitor-records/<record_id>', methods=['PUT'])
def update_monitor_record(record_id):
    data = request.json
    db_session = next(get_db())
    try:
        record = db_session.query(MonitorRecord).filter_by(record_id=record_id).first()
        if not record:
            return jsonify({"code": 404, "msg": "记录不存在"})

        # 校验必填字段（移除 recorderId 校验）
        required_fields = ['speciesId', 'deviceId', 'monitorTime', 'monitorLocation', 'monitorMethod']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"code": 400, "msg": f"字段 {field} 不能为空"})

        # 处理经纬度
        longitude = record.longitude
        if data.get('longitude'):
            try:
                longitude = float(data['longitude'])
                if not (-180 <= longitude <= 180):
                    return jsonify({"code": 400, "msg": "经度范围必须在-180到180之间"})
            except ValueError:
                return jsonify({"code": 400, "msg": "经度必须是有效的数字"})

        latitude = record.latitude
        if data.get('latitude'):
            try:
                latitude = float(data['latitude'])
                if not (-90 <= latitude <= 90):
                    return jsonify({"code": 400, "msg": "纬度范围必须在-90到90之间"})
            except ValueError:
                return jsonify({"code": 400, "msg": "纬度必须是有效的数字"})

        # 处理日期
        try:
            monitor_time_str = data['monitorTime'].replace('T', ' ')
            if len(monitor_time_str.split(':')) == 2:
                monitor_time_str += ':00'
            monitor_time = datetime.strptime(monitor_time_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"code": 400, "msg": "监测日期格式错误"})

        # 更新字段
        record.species_id = data['speciesId']
        record.device_id = data['deviceId']
        record.monitor_time = monitor_time
        record.longitude = longitude
        record.latitude = latitude
        record.monitor_location = data['monitorLocation']
        record.monitor_method = data['monitorMethod']
        record.monitor_content = data.get('monitorContent', record.monitor_content)
        record.analysis_conclusion = data.get('analysisConclusion', record.analysis_conclusion)
        record.recorder_id = data.get('recorderId', 'system')  # 默认值
        record.data_status = data.get('dataStatus', record.data_status)
        if data.get('dataStatus') == "有效" and not record.verify_time:
            record.verify_time = datetime.now()

        db_session.commit()

        return jsonify({
            "code": 200,
            "msg": "监测记录更新成功",
            "data": {"recorderName": "系统默认"}
        })
    except ValueError as e:
        db_session.rollback()
        return jsonify({"code": 400, "msg": f"参数格式错误：{str(e)}"})
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"更新失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：获取系统用户列表（记录人ID） --------------------
@app.route('/api/sys-users', methods=['GET'])
def get_sys_users():
    db_session = next(get_db())
    try:
        # 可选：支持按角色/负责区域筛选（前端可扩展）
        role = request.args.get('role', '')
        region = request.args.get('region', '')

        # 修复：使用定义好的 SysUser 模型类，而非未定义的 sys_user.c
        query = db_session.query(
            SysUser.user_id,
            SysUser.user_name,
            SysUser.role,
            SysUser.responsible_region
        )

        # 条件筛选
        if role:
            query = query.filter(SysUser.role == role)
        if region:
            query = query.filter(SysUser.responsible_region == region)

        # 执行查询
        users = query.all()

        # 格式化为前端需要的结构（userId/userName 字段名适配前端）
        data = [{
            "userId": user.user_id,  # 对应前端的 recorderId
            "userName": user.user_name,  # 对应前端的 monitorPerson
            "role": user.role,  # 扩展字段：用户角色
            "responsibleRegion": user.responsible_region  # 扩展字段：负责区域
        } for user in users]

        # 兜底：如果用户表为空，返回模拟数据避免前端加载失败
        if not data:
            data = [
                {"userId": "US001", "userName": "张三", "role": "生态监测员", "responsibleRegion": "REG001"},
                {"userId": "US002", "userName": "李四", "role": "数据分析师", "responsibleRegion": "REG002"},
                {"userId": "US003", "userName": "王五", "role": "监测主管", "responsibleRegion": "REG003"}
            ]

        return jsonify({
            "code": 200,
            "msg": "查询成功",
            "data": data,
            "total": len(data)
        })
    except Exception as e:
        # 详细的错误日志，方便调试
        print(f"查询系统用户失败：{str(e)}")
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}", "data": []})
    finally:
        db_session.close()


# -------------------- 接口：删除监测记录 --------------------
@app.route('/api/monitor-records/<record_id>', methods=['DELETE'])
def delete_monitor_record(record_id):
    db_session = next(get_db())
    try:
        record = db_session.query(MonitorRecord).filter_by(record_id=record_id).first()
        if not record:
            return jsonify({"code": 404, "msg": "记录不存在"})

        db_session.delete(record)
        db_session.commit()

        return jsonify({"code": 200, "msg": "监测记录删除成功"})
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"删除失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：获取监测设备列表 --------------------
@app.route('/api/monitor-devices', methods=['GET'])
def get_monitor_devices():
    db_session = next(get_db())
    try:
        devices = db_session.query(MonitorDevice.device_id).all()
        data = [{"deviceId": d[0]} for d in devices]
        return jsonify({"code": 200, "msg": "查询成功", "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：获取栖息地统计 --------------------
@app.route('/api/habitat/stat', methods=['GET'])
def habitat_stat():
    db_session = next(get_db())
    try:
        stats = db_session.query(
            HabitatInfo.ecological_type,
            db.func.count(HabitatInfo.habitat_id),
            db.func.avg(HabitatInfo.suitability_score)
        ).group_by(HabitatInfo.ecological_type).all()

        data = [{
            "type": s[0],
            "count": s[1],
            "avgScore": round(float(s[2]), 2) if s[2] else 0.0
        } for s in stats]

        return jsonify({"code": 200, "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：获取栖息地列表 --------------------
@app.route('/api/habitat', methods=['GET'])
def get_habitat():
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 10))
    page = max(page, 1)
    size = max(1, min(size, 100))

    db_session = next(get_db())
    try:
        query = db_session.query(HabitatInfo, RegionInfo.region_name).join(
            RegionInfo, HabitatInfo.region_id == RegionInfo.region_id, isouter=True
        )

        total = query.count()
        habitats = query.offset((page - 1) * size).limit(size).all()

        data = [{
            "habitatId": h.HabitatInfo.habitat_id,
            "regionName": h.region_name or "未知区域",
            "ecologicalType": h.HabitatInfo.ecological_type,
            "area": float(h.HabitatInfo.area),
            "suitabilityScore": h.HabitatInfo.suitability_score,
            "coreProtection": h.HabitatInfo.core_protection,
            "speciesCount": len(h.HabitatInfo.species_relations) if hasattr(h.HabitatInfo, 'species_relations') else 0
        } for h in habitats]

        return jsonify({
            "code": 200,
            "msg": "查询成功",
            "data": data,
            "total": total,
            "page": page,
            "size": size
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 接口：获取栖息地列表（适配图表） --------------------
@app.route('/api/habitat/list', methods=['GET'])
def get_habitat_list():
    eco_type = request.args.get('type', 'all')
    species_id = request.args.get('speciesId', '')

    db_session = next(get_db())
    try:
        query = db_session.query(HabitatInfo)

        if eco_type != 'all':
            query = query.filter(HabitatInfo.ecological_type == eco_type)
        if species_id and species_id != 'all':
            query = query.join(
                HabitatSpeciesRelation,
                HabitatInfo.habitat_id == HabitatSpeciesRelation.habitat_id
            ).filter(HabitatSpeciesRelation.species_id == species_id)

        habitat_list = query.all()

        data = [{
            "habitatId": h.habitat_id,
            "regionId": h.region_id,
            "ecologicalType": h.ecological_type,
            "area": float(h.area),
            "coreProtection": h.core_protection,
            "suitabilityScore": h.suitability_score,
            "threatLevel": "低威胁" if h.suitability_score >= 9 else "中度威胁" if h.suitability_score >= 7 else "高威胁"
        } for h in habitat_list]

        return jsonify({
            "code": 200,
            "msg": "查询成功",
            "data": data
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}", "data": []})
    finally:
        db_session.close()


# -------------------- 接口：获取栖息地生态类型列表 --------------------
@app.route('/api/habitat/types', methods=['GET'])
def get_habitat_types():
    db_session = next(get_db())
    try:
        types = db_session.query(HabitatInfo.ecological_type).distinct().all()
        data = [{"type": t[0]} for t in types]
        return jsonify({"code": 200, "msg": "查询成功", "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}", "data": []})
    finally:
        db_session.close()


# -------------------- 新增：栖息地增删改接口 --------------------
# 新增栖息地
@app.route('/api/habitat', methods=['POST'])
def add_habitat():
    data = request.json
    db_session = next(get_db())
    try:
        # 校验必填字段
        required_fields = ['regionId', 'ecologicalType', 'area', 'coreProtection', 'suitabilityScore']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"code": 400, "msg": f"字段 {field} 不能为空"})

        # 校验面积和评分
        try:
            area = float(data['area'])
            if area <= 0:
                return jsonify({"code": 400, "msg": "面积必须大于0"})

            score = int(data['suitabilityScore'])
            if score < 1 or score > 10:
                return jsonify({"code": 400, "msg": "适宜性评分必须在1-10之间"})
        except ValueError:
            return jsonify({"code": 400, "msg": "面积必须是数字，适宜性评分必须是整数"})

        # 校验区域是否存在
        region = db_session.query(RegionInfo).filter_by(region_id=data['regionId']).first()
        if not region:
            return jsonify({"code": 404, "msg": f"区域ID {data['regionId']} 不存在"})

        # 生成栖息地ID
        habitat_id = generate_habitat_id()

        # 创建栖息地
        new_habitat = HabitatInfo(
            habitat_id=habitat_id,
            region_id=data['regionId'],
            ecological_type=data['ecologicalType'],
            area=area,
            core_protection=data['coreProtection'],
            suitability_score=score
        )

        db_session.add(new_habitat)
        db_session.commit()

        return jsonify({
            "code": 200,
            "msg": "栖息地新增成功",
            "data": {"habitatId": habitat_id}
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"新增失败：{str(e)}"})
    finally:
        db_session.close()


# 编辑栖息地
@app.route('/api/habitat/<habitat_id>', methods=['PUT'])
def update_habitat(habitat_id):
    data = request.json
    db_session = next(get_db())
    try:
        # 查找栖息地
        habitat = db_session.query(HabitatInfo).filter_by(habitat_id=habitat_id).first()
        if not habitat:
            return jsonify({"code": 404, "msg": "栖息地不存在"})

        # 校验必填字段
        required_fields = ['regionId', 'ecologicalType', 'area', 'coreProtection', 'suitabilityScore']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"code": 400, "msg": f"字段 {field} 不能为空"})

        # 校验面积和评分
        try:
            area = float(data['area'])
            if area <= 0:
                return jsonify({"code": 400, "msg": "面积必须大于0"})

            score = int(data['suitabilityScore'])
            if score < 1 or score > 10:
                return jsonify({"code": 400, "msg": "适宜性评分必须在1-10之间"})
        except ValueError:
            return jsonify({"code": 400, "msg": "面积必须是数字，适宜性评分必须是整数"})

        # 校验区域是否存在
        region = db_session.query(RegionInfo).filter_by(region_id=data['regionId']).first()
        if not region:
            return jsonify({"code": 404, "msg": f"区域ID {data['regionId']} 不存在"})

        # 更新字段
        habitat.region_id = data['regionId']
        habitat.ecological_type = data['ecologicalType']
        habitat.area = area
        habitat.core_protection = data['coreProtection']
        habitat.suitability_score = score

        db_session.commit()

        return jsonify({
            "code": 200,
            "msg": "栖息地更新成功"
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"更新失败：{str(e)}"})
    finally:
        db_session.close()


# 删除栖息地
@app.route('/api/habitat/<habitat_id>', methods=['DELETE'])
def delete_habitat(habitat_id):
    db_session = next(get_db())
    try:
        # 查找栖息地
        habitat = db_session.query(HabitatInfo).filter_by(habitat_id=habitat_id).first()
        if not habitat:
            return jsonify({"code": 404, "msg": "栖息地不存在"})

        # 删除栖息地（级联删除关联的物种关系）
        db_session.delete(habitat)
        db_session.commit()

        return jsonify({
            "code": 200,
            "msg": "栖息地删除成功"
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"删除失败：{str(e)}"})
    finally:
        db_session.close()


# 获取单个栖息地详情
@app.route('/api/habitat/<habitat_id>', methods=['GET'])
def get_single_habitat(habitat_id):
    db_session = next(get_db())
    try:
        habitat = db_session.query(HabitatInfo, RegionInfo.region_name).join(
            RegionInfo, HabitatInfo.region_id == RegionInfo.region_id, isouter=True
        ).filter(HabitatInfo.habitat_id == habitat_id).first()

        if not habitat:
            return jsonify({"code": 404, "msg": "栖息地不存在"})

        data = {
            "habitatId": habitat.HabitatInfo.habitat_id,
            "regionId": habitat.HabitatInfo.region_id,
            "regionName": habitat.region_name or "未知区域",
            "ecologicalType": habitat.HabitatInfo.ecological_type,
            "area": float(habitat.HabitatInfo.area),
            "coreProtection": habitat.HabitatInfo.core_protection,
            "suitabilityScore": habitat.HabitatInfo.suitability_score,
            "threatLevel": "低威胁" if habitat.HabitatInfo.suitability_score >= 9 else "中度威胁" if habitat.HabitatInfo.suitability_score >= 7 else "高威胁"
        }

        return jsonify({
            "code": 200,
            "msg": "查询成功",
            "data": data
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"})
    finally:
        db_session.close()


# -------------------- 栖息地-物种关联接口 --------------------
@app.route('/api/habitat/species/relation', methods=['POST'])
def add_habitat_species_relation():
    data = request.json
    db_session = next(get_db())
    try:
        if not data.get('habitatId') or not data.get('speciesId'):
            return jsonify({"code": 400, "msg": "栖息地ID和物种ID不能为空"})

        habitat = db_session.query(HabitatInfo).filter_by(habitat_id=data['habitatId']).first()
        species = db_session.query(SpeciesInfo).filter_by(species_id=data['speciesId']).first()
        if not habitat:
            return jsonify({"code": 404, "msg": f"栖息地ID {data['habitatId']} 不存在"})
        if not species:
            return jsonify({"code": 404, "msg": f"物种ID {data['speciesId']} 不存在"})

        exist_relation = db_session.query(HabitatSpeciesRelation).filter_by(
            habitat_id=data['habitatId'],
            species_id=data['speciesId']
        ).first()
        if exist_relation:
            return jsonify({"code": 400, "msg": "该物种已关联至该栖息地，无需重复关联"})

        new_relation = HabitatSpeciesRelation(
            habitat_id=data['habitatId'],
            species_id=data['speciesId'],
            is_main=data.get('isMain', 1)
        )
        db_session.add(new_relation)
        db_session.commit()

        return jsonify({
            "code": 200,
            "msg": "物种关联成功",
            "data": {
                "habitatId": data['habitatId'],
                "speciesId": data['speciesId'],
                "isMain": data.get('isMain', 1)
            }
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"关联失败：{str(e)}"})
    finally:
        db_session.close()


@app.route('/api/habitat/<habitat_id>/species', methods=['GET'], endpoint='unique_habitat_species')
def get_habitat_related_species(habitat_id):
    db_session = next(get_db())
    try:
        relations = db_session.query(
            HabitatSpeciesRelation,
            SpeciesInfo.species_id,
            SpeciesInfo.chinese_name,
            SpeciesInfo.protection_level
        ).join(
            SpeciesInfo,
            HabitatSpeciesRelation.species_id == SpeciesInfo.species_id
        ).filter(
            HabitatSpeciesRelation.habitat_id == habitat_id
        ).all()

        data = [{
            "speciesId": r[1],
            "speciesName": r[2],
            "protectionLevel": r[3],
            "isMain": r[0].is_main
        } for r in relations]

        return jsonify({
            "code": 200,
            "msg": "查询成功",
            "data": data,
            "mainSpeciesCount": len([item for item in data if item['isMain'] == 1]),
            "totalSpeciesCount": len(data)
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}", "data": []})
    finally:
        db_session.close()


@app.route('/api/habitat/species/relation', methods=['PUT'])
def update_habitat_species_relation():
    data = request.json
    db_session = next(get_db())
    try:
        if not data.get('habitatId') or not data.get('speciesId') or 'isMain' not in data:
            return jsonify({"code": 400, "msg": "栖息地ID、物种ID、isMain不能为空"})

        relation = db_session.query(HabitatSpeciesRelation).filter_by(
            habitat_id=data['habitatId'],
            species_id=data['speciesId']
        ).first()
        if not relation:
            return jsonify({"code": 404, "msg": "该物种未关联至该栖息地"})

        relation.is_main = data['isMain']
        db_session.commit()

        return jsonify({
            "code": 200,
            "msg": "标记更新成功",
            "data": {"isMain": data['isMain']}
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"更新失败：{str(e)}"})
    finally:
        db_session.close()


@app.route('/api/habitat/species/relation', methods=['DELETE'])
def delete_habitat_species_relation():
    data = request.json
    db_session = next(get_db())
    try:
        if not data.get('habitatId') or not data.get('speciesId'):
            return jsonify({"code": 400, "msg": "栖息地ID和物种ID不能为空"})

        relation = db_session.query(HabitatSpeciesRelation).filter_by(
            habitat_id=data['habitatId'],
            species_id=data['speciesId']
        ).first()
        if not relation:
            return jsonify({"code": 404, "msg": "该关联关系不存在"})

        db_session.delete(relation)
        db_session.commit()

        return jsonify({"code": 200, "msg": "关联关系已解除"})
    except Exception as e:
        db_session.rollback()
        return jsonify({"code": 500, "msg": f"删除失败：{str(e)}"})
    finally:
        db_session.close()


@app.route('/api/species/<species_id>/habitat', methods=['GET'])
def get_species_related_habitat(species_id):
    db_session = next(get_db())
    try:
        relations = db_session.query(
            HabitatSpeciesRelation,
            HabitatInfo.ecological_type,
            HabitatInfo.area,
            RegionInfo.region_name
        ).join(
            HabitatInfo,
            HabitatSpeciesRelation.habitat_id == HabitatInfo.habitat_id
        ).join(
            RegionInfo,
            HabitatInfo.region_id == RegionInfo.region_id
        ).filter_by(species_id=species_id).all()

        data = [{
            "habitatId": r.HabitatSpeciesRelation.habitat_id,
            "regionName": r.region_name,
            "ecologicalType": r.ecological_type,
            "area": float(r.area),
            "isMain": r.HabitatSpeciesRelation.is_main
        } for r in relations]

        return jsonify({
            "code": 200,
            "msg": "查询成功",
            "data": data
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}", "data": []})
    finally:
        db_session.close()


# 启动应用
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)