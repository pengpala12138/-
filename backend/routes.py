# backend/routes.py
from flask import jsonify, request, Blueprint
from .config import get_db
from .models import SpeciesInfo, MonitorRecord, SysUser
from .utils import execute_sql_script

# 创建蓝图
api = Blueprint("api", __name__)

# 接口1：初始化数据库（执行create和insert脚本）
@api.route("/api/init-db", methods=["POST"])
def init_db():
    try:
        execute_sql_script("create_tables.sql")
        execute_sql_script("insert_test_data.sql")
        return jsonify({"code": 200, "msg": "数据库初始化成功"})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"失败：{str(e)}"}), 500

# 接口2：获取所有物种
@api.route("/api/species", methods=["GET"])
def get_species():
    db = next(get_db())
    try:
        species = db.query(SpeciesInfo).all()
        result = [{
            "species_id": s.species_id,
            "chinese_name": s.chinese_name,
            "latin_name": s.latin_name,
            "protection_level": s.protection_level
        } for s in species]
        return jsonify({"code": 200, "data": result})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"}), 500
    finally:
        db.close()

# 接口3：获取待核实监测记录
@api.route("/api/monitor/pending", methods=["GET"])
def get_pending():
    db = next(get_db())
    try:
        records = db.query(MonitorRecord, SpeciesInfo, SysUser).\
            join(SpeciesInfo, MonitorRecord.species_id == SpeciesInfo.species_id).\
            join(SysUser, MonitorRecord.recorder_id == SysUser.user_id).\
            filter(MonitorRecord.data_status == "待核实").all()
        result = [{
            "record_id": r[0].record_id,
            "species_name": r[1].chinese_name,
            "monitor_time": r[0].monitor_time.strftime("%Y-%m-%d %H:%M"),
            "monitor_method": r[0].monitor_method,
            "recorder_name": r[2].user_name
        } for r in records]
        return jsonify({"code": 200, "data": result})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"}), 500
    finally:
        db.close()

# 接口4：审核监测记录
@api.route("/api/monitor/audit/<record_id>", methods=["PUT"])
def audit(record_id):
    db = next(get_db())
    try:
        data = request.json
        record = db.query(MonitorRecord).filter(MonitorRecord.record_id == record_id).first()
        if not record:
            return jsonify({"code": 404, "msg": "记录不存在"}), 404
        record.data_status = data.get("status")
        record.analysis_conclusion = data.get("conclusion")
        record.verify_time = data.get("verify_time")
        db.commit()
        return jsonify({"code": 200, "msg": "审核成功"})
    except Exception as e:
        db.rollback()
        return jsonify({"code": 500, "msg": f"审核失败：{str(e)}"}), 500
    finally:
        db.close()

# 注册路由的函数
def register_routes(app):
    app.register_blueprint(api)