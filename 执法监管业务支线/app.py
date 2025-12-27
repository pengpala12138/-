from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,  # 静态文件托管核心函数
    redirect,
    url_for
)
from flask_cors import CORS  # 解决跨域问题
import pymysql
from datetime import datetime

app = Flask(__name__)
CORS(app)  # 允许所有跨域请求

# 健康检查端点
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"code": 200, "msg": "OK"})

# 数据库配置
DB_CONFIG = {
    'host': '172.20.10.4',
    'user': 'zyj',
    'password': '515408',
    'database': 'sjk',
    'charset': 'utf8mb4'
}


def get_db_connection():
    """创建数据库连接"""
    return pymysql.connect(**DB_CONFIG)


# -------------------------- 新增：前端页面路由 --------------------------
# 根路径跳转到非法行为记录页面
@app.route('/')
def index():
    return send_from_directory('static', 'illegal-records.html')  # 直接返回非法行为记录页面

# 移除原有的/index.html重定向路由，或者修改为指向非法行为记录页面
@app.route('/index.html')
def index_html():
    return send_from_directory('static', 'illegal-records.html')  # 也指向非法行为记录页面

# 其他前端页面的路由（匹配你的HTML文件名）
@app.route('/law-dispatches.html')
def law_dispatches_page():
    return send_from_directory('static', 'law-dispatches.html')

@app.route('/illegal-records.html')
def illegal_records_page():
    return send_from_directory('static', 'illegal-records.html')

@app.route('/law-enforcers.html')
def law_enforcers_page():
    return send_from_directory('static', 'law-enforcers.html')

@app.route('/video-monitors.html')
def video_monitors_page():
    return send_from_directory('static', 'video-monitors.html')



# -------------------------- 1. 执法人员管理接口 --------------------------
@app.route('/api/law-enforcers', methods=['GET'])
def get_enforcers():
    """查询执法人员列表"""
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM law_enforcer")
            data = cursor.fetchall()
        conn.close()
        return jsonify({"code": 200, "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/law-enforcers', methods=['POST'])
def add_enforcer():
    """新增执法人员"""
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO law_enforcer (office_id, name, department, authority_level, contact, device_no)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['office_id'], data['name'], data['department'],
                data['authority_level'], data['contact'], data['device_no']
            ))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "新增成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/law-enforcers/<string:office_id>', methods=['PUT'])
def update_enforcer(office_id):
    """修改执法人员信息"""
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            UPDATE law_enforcer SET name=%s, department=%s, authority_level=%s,
            contact=%s, device_no=%s WHERE office_id=%s
            """
            cursor.execute(sql, (
                data['name'], data['department'], data['authority_level'],
                data['contact'], data['device_no'], office_id
            ))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "更新成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/law-enforcers/<string:office_id>', methods=['DELETE'])
def delete_enforcer(office_id):
    """删除执法人员"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM law_enforcer WHERE office_id=%s", (office_id,))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "删除成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


# -------------------------- 2. 非法行为记录接口 --------------------------
@app.route('/api/illegal-records', methods=['GET'])
def get_illegal_records():
    """获取非法行为记录（支持状态筛选、分页）"""
    status = request.args.get('status', '')
    behavior_type = request.args.get('behavior_type', '')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 10))
    offset = (page - 1) * page_size
    conn = None

    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 统计总
            if status and behavior_type:
                total_sql = "SELECT COUNT(*) AS total FROM illegal_record WHERE status = %s AND behavior_type = %s"
                cursor.execute(total_sql, (status, behavior_type))
            elif status:
                total_sql = "SELECT COUNT(*) AS total FROM illegal_record WHERE status = %s"
                cursor.execute(total_sql, (status,))
            elif behavior_type:
                total_sql = "SELECT COUNT(*) AS total FROM illegal_record WHERE behavior_type = %s"
                cursor.execute(total_sql, (behavior_type,))
            else:
                total_sql = "SELECT COUNT(*) AS total FROM illegal_record"
                cursor.execute(total_sql)
            total = cursor.fetchone()['total']

            # 查询分页数据
            query_sql = """
            SELECT ir.*, ri.region_name, GROUP_CONCAT(vm.monitor_id) AS monitor_ids
            FROM illegal_record ir
            LEFT JOIN region_info ri ON ir.region_id = ri.region_id
            LEFT JOIN illegal_monitor_rel rel ON ir.record_id = rel.illegal_behavior_record_id
            LEFT JOIN video_monitor vm ON rel.monitor_id = vm.monitor_id
            """
            params = []
            where_clause = []
            if status:
                where_clause.append("ir.status = %s")
                params.append(status)
            if behavior_type:
                where_clause.append("ir.behavior_type = %s")
                params.append(behavior_type)
            if where_clause:
                query_sql += " WHERE " + " AND ".join(where_clause)
            query_sql += " GROUP BY ir.record_id ORDER BY ir.occurrence_time DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])
            cursor.execute(query_sql, params)
            records = cursor.fetchall()

        return jsonify({
            "code": 200,
            "data": {
                "records": records,
                "total": total,
                "page": page,
                "pageSize": page_size
            },
            "msg": "查询成功"
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"})
    finally:
        if conn:
            conn.close()


@app.route('/api/illegal-records', methods=['POST'])
def add_illegal_record():
    """新增非法行为记录"""
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO illegal_record (record_id, behavior_type, region_id, occurrence_time, 
                                       evidence_path, status, result, basis)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['record_id'], data['behavior_type'], data['region_id'],
                data['occurrence_time'], data['evidence_path'], '未处理',
                '', ''
            ))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "新增成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/illegal-records/<string:record_id>', methods=['PUT'])
def update_illegal_record(record_id):
    """更新非法行为记录"""
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            UPDATE illegal_record SET behavior_type=%s, region_id=%s, 
            occurrence_time=%s, evidence_path=%s WHERE record_id=%s
            """
            cursor.execute(sql, (
                data['behavior_type'], data['region_id'], data['occurrence_time'],
                data['evidence_path'], record_id
            ))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "更新成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/illegal-records/handle', methods=['POST'])
def handle_illegal_record():
    """处理非法行为记录（更新状态、处理结果）"""
    data = request.form
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            UPDATE illegal_record 
            SET status = %s, result = %s, basis = %s, officer_id = %s
            WHERE record_id = %s
            """
            cursor.execute(sql, (
                data['status'], data['result'], data['basis'],
                data['officer_id'], data['record_id']
            ))
        conn.commit()
        return jsonify({"code": 200, "msg": "处理成功"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"code": 500, "msg": f"处理失败：{str(e)}"})
    finally:
        if conn:
            conn.close()


@app.route('/api/illegal-records/<string:record_id>', methods=['DELETE'])
def delete_illegal_record(record_id):
    """删除非法行为记录"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM illegal_record WHERE record_id=%s", (record_id,))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "删除成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


# -------------------------- 3. 视频监控点接口 --------------------------
@app.route('/api/video-monitors', methods=['GET'])
def get_video_monitors():
    """获取视频监控点列表"""
    monitor_id = request.args.get('monitor_id', '').strip()  # 清除输入空格
    status = request.args.get('status', '')
    region_id = request.args.get('region_id', '').strip()    # 清除输入空格

    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            query_sql = "SELECT * FROM video_monitor WHERE 1=1"
            params = []
            if monitor_id:
                # 由模糊匹配改为精确匹配，并处理空格
                query_sql += " AND monitor_id = %s"
                params.append(monitor_id)
            if status:
                query_sql += " AND status = %s"
                params.append(status)
            if region_id:
                # 区域ID同样改为精确匹配
                query_sql += " AND region_id = %s"
                params.append(region_id)

            cursor.execute(query_sql, params)
            data = cursor.fetchall()
        conn.close()
        return jsonify({"code": 200, "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})

@app.route('/api/video-monitors', methods=['POST'])
def add_video_monitor():
    """新增视频监控点"""
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO video_monitor (monitor_id, region_id, location, coverage, 
                                      status, storage_period)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['monitor_id'], data['region_id'], data['location'],
                data['coverage'], data['status'], data['storage_period']
            ))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "新增成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/video-monitors/<string:monitor_id>', methods=['PUT'])
def update_video_monitor(monitor_id):
    """更新视频监控点"""
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            UPDATE video_monitor SET region_id=%s, location=%s, coverage=%s,
            status=%s, storage_period=%s WHERE monitor_id=%s
            """
            cursor.execute(sql, (
                data['region_id'], data['location'], data['coverage'],
                data['status'], data['storage_period'], monitor_id
            ))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "更新成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/video-monitors/<string:monitor_id>', methods=['DELETE'])
def delete_video_monitor(monitor_id):
    """删除视频监控点"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM video_monitor WHERE monitor_id=%s", (monitor_id,))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "删除成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


# -------------------------- 4. 执法调度接口 --------------------------
@app.route('/api/law-dispatches', methods=['GET'])
def get_law_dispatches():
    """获取执法调度记录"""
    status = request.args.get('status', '')
    officer_name = request.args.get('officer_name', '')
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            query_sql = """
            SELECT 
                ld.*,
                le.name AS officer_name,
                le.department AS department,
                ir.behavior_type AS behavior_type
            FROM law_dispatch ld
            LEFT JOIN law_enforcer le ON ld.officer_id = le.office_id
            LEFT JOIN illegal_record ir ON ld.illegal_behavior_record_id = ir.record_id
            WHERE 1=1
            """
            params = []
            if status:
                query_sql += " AND ld.status = %s"
                params.append(status)
            if officer_name:
                # 问题可能原因：数据库中姓名存在空格/特殊字符，或参数传递时有空格
                # 解决方案：去除两端空格后精确匹配
                clean_name = officer_name.strip()  # 新增：清除输入的空格
                query_sql += " AND le.name = %s"   # 改为精确匹配
                params.append(clean_name)          # 使用清洗后的值

            cursor.execute(query_sql, params)
            data = cursor.fetchall()
        conn.close()
        return jsonify({"code": 200, "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})

@app.route('/api/law-dispatches', methods=['POST'])
def add_law_dispatch():
    """新增执法调度"""
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO law_dispatch (dispatch_id, illegal_behavior_record_id, officer_id,
                                     dispatch_time, status)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['dispatch_id'], data['illegal_behavior_record_id'],
                data['officer_id'], datetime.now(), "待响应"
            ))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "调度成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/law-dispatches/<string:dispatch_id>', methods=['PUT'])
def update_law_dispatch(dispatch_id):
    """更新执法调度状态"""
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "UPDATE law_dispatch SET status=%s"
            params = [data['status']]

            if data['status'] == "已派单":
                sql += ", response_time=%s"
                params.append(datetime.now())
            elif data['status'] == "已完成":
                sql += ", complete_time=%s"
                params.append(datetime.now())

            sql += " WHERE dispatch_id=%s"
            params.append(dispatch_id)

            cursor.execute(sql, params)
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "更新成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/law-dispatches/<string:dispatch_id>', methods=['DELETE'])
def delete_law_dispatch(dispatch_id):
    """删除执法调度记录"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM law_dispatch WHERE dispatch_id=%s", (dispatch_id,))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "删除成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"code": 500, "msg": str(e)})


# -------------------------- 5. 统计接口 --------------------------
@app.route('/api/statistics/officer-workload', methods=['GET'])
def stat_officer_workload():
    """统计执法人员工作量（近90天）"""
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
            SELECT 
                le.office_id, le.name, le.department,
                COUNT(ld.dispatch_id) AS handle_count,
                IFNULL(AVG(TIMESTAMPDIFF(HOUR, ld.dispatch_time, ld.complete_time)), 0) AS avg_handle_hours
            FROM 
                law_enforcers le
            LEFT JOIN 
                law_dispatch ld ON le.office_id = ld.officer_id
            WHERE 
                ld.complete_time IS NOT NULL
                AND ld.dispatch_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            GROUP BY 
                le.office_id, le.name, le.department
            ORDER BY 
                handle_count DESC
            """)
            result = cursor.fetchall()
        conn.close()
        return jsonify({"code": 200, "data": result, "msg": "统计成功"})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"统计失败：{str(e)}"})


# @app.route('/')
# def index():
#     return "Hello from Flask!"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)