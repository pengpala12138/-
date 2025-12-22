from flask import Flask, jsonify, request, render_template, send_file
from flask_cors import CORS
import logging
from datetime import datetime, timedelta
import os
import json

from database import db
from views import DataViews
from procedures import DatabaseProcedures

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# 简化的CORS配置
CORS(app, origins=["http://172.20.10.7:3000"],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "Accept"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# 配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['JSON_AS_ASCII'] = False


@app.route('/')
def index():
    """主页"""
    return jsonify({
        'message': '游客智能管理系统 API',
        'version': '2.1.3',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            '系统状态': '/api/status',
            '游客管理': '/api/tourists',
            '预约管理': '/api/reservations',
            '轨迹管理': '/api/trajectories',
            '流量控制': '/api/flow-control',
            '数据视图': '/api/views/*',
            '存储过程': '/api/procedures/*',
            '入园核验': '/api/check-in',
            '实时监控': '/api/realtime-monitor',
            '数据统计': '/api/stats',
            '系统日志': '/api/logs'
        }
    })


@app.route('/api/status', methods=['GET'])
def system_status():
    """系统状态检查"""
    try:
        # 检查数据库连接
        db.execute_query("SELECT 1 as status")

        # 获取基本统计
        stats_query = """
                      SELECT (SELECT COUNT(*) FROM tourists)                              as total_tourists,
                             (SELECT COUNT(*) FROM reservations)                          as total_reservations,
                             (SELECT COUNT(*) FROM trajectories)                          as total_trajectories,
                             (SELECT COUNT(*) FROM flow_control WHERE status != 'normal') as warning_areas,
                             (SELECT COUNT(*) \
                              FROM system_logs
                              WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                                AND log_type = 'warning')                                 as recent_warnings \
                      """

        stats = db.execute_query(stats_query, fetch_one=True)

        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat(),
            'uptime': get_uptime(),
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"系统状态检查失败: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


def get_uptime():
    """获取系统运行时间（示例）"""
    return "24小时"


# 游客管理API
@app.route('/api/tourists', methods=['GET', 'POST', 'OPTIONS'])
def manage_tourists():
    if request.method == 'OPTIONS':
        return '', 200
    elif request.method == 'GET':
        # 获取游客列表
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        search = request.args.get('search', '')

        offset = (page - 1) * page_size

        query = "SELECT * FROM tourists"
        params = []

        if search:
            query += " WHERE name LIKE %s OR id_card LIKE %s OR tourist_id LIKE %s"
            params = [f"%{search}%", f"%{search}%", f"%{search}%"]

        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])

        tourists = db.execute_query(query, params)
        return jsonify(tourists)

    elif request.method == 'POST':
        # 创建新游客
        data = request.json

        required_fields = ['tourist_id', 'name', 'id_card']
        if not all(field in data for field in required_fields):
            return jsonify({'error': '缺少必填字段'}), 400

        # 检查ID是否重复
        check_query = "SELECT COUNT(*) as count FROM tourists WHERE tourist_id = %s OR id_card = %s"
        result = db.execute_query(check_query, (data['tourist_id'], data['id_card']), fetch_one=True)

        if result['count'] > 0:
            return jsonify({'error': '游客ID或身份证号已存在'}), 400

        # 插入新游客
        insert_query = """
                       INSERT INTO tourists (tourist_id, name, id_card, phone, entry_method, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s) \
                       """

        try:
            db.execute_update(insert_query, (
                data['tourist_id'],
                data['name'],
                data['id_card'],
                data.get('phone'),
                data.get('entry_method', 'online'),
                datetime.now()
            ))

            # 记录日志 - 使用英文避免字符集问题
            log_query = """
                        INSERT INTO system_logs (log_type, module, message, user_id, created_at)
                        VALUES ('info', 'tourist', 'Create new tourist', %s, %s) \
                        """
            db.execute_update(log_query, (data['tourist_id'], datetime.now()))

            return jsonify({'message': '游客创建成功', 'tourist_id': data['tourist_id']}), 201

        except Exception as e:
            logger.error(f"创建游客失败: {str(e)}")
            return jsonify({'error': str(e)}), 500


@app.route('/api/tourists/<tourist_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def manage_tourist(tourist_id):
    if request.method == 'OPTIONS':
        return '', 200
    elif request.method == 'GET':
        # 获取单个游客信息
        query = "SELECT * FROM tourists WHERE tourist_id = %s"
        tourist = db.execute_query(query, (tourist_id,), fetch_one=True)

        if not tourist:
            return jsonify({'error': '游客不存在'}), 404

        return jsonify(tourist)

    elif request.method == 'PUT':
        # 更新游客信息
        data = request.json
        check_query = "SELECT * FROM tourists WHERE tourist_id = %s"
        existing_tourist = db.execute_query(check_query, (tourist_id,), fetch_one=True)

        if not existing_tourist:
            return jsonify({'error': '游客不存在'}), 404

        # 构建更新语句
        updates = []
        params = []
        # 扩展可更新字段，包含日期字段
        allowed_fields = ['name', 'phone', 'entry_method', 'id_card', 'entry_time', 'exit_time']

        for field in allowed_fields:
            if field in data and data[field] is not None:
                # 处理日期字段转换
                field_value = data[field]
                if field in ['entry_time', 'exit_time'] and field_value:
                    try:
                        # 将前端ISO字符串转为datetime
                        field_value = datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                    except ValueError:
                        return jsonify({'error': f'{field} 日期格式错误'}), 400

                # 检查数据是否真的改变
                current_value = existing_tourist.get(field, '')
                # 统一转字符串比较（兼容datetime和普通字段）
                if str(field_value) != str(current_value):
                    updates.append(f"{field} = %s")
                    params.append(field_value)

        if not updates:
            return jsonify({'error': '没有可更新的字段'}), 400

        # 修正参数顺序：先加updated_at，再加tourist_id
        updates.append("updated_at = %s")
        params.append(datetime.now())
        params.append(tourist_id)

        # 构建最终SQL
        query = f"UPDATE tourists SET {', '.join(updates)} WHERE tourist_id = %s"

        try:
            affected = db.execute_update(query, params)

            if affected == 0:
                return jsonify({'error': '游客不存在或数据未更改'}), 404

            # 记录日志 - 使用英文
            log_query = """
                        INSERT INTO system_logs (log_type, module, message, user_id, created_at)
                        VALUES ('info', 'tourist', 'Update tourist info', %s, %s) \
                        """
            db.execute_update(log_query, (tourist_id, datetime.now()))

            return jsonify({'message': '游客信息更新成功'})

        except Exception as e:
            logger.error(f"更新游客失败: {str(e)}")
            return jsonify({'error': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            # 先检查是否有相关数据
            # 1. 先删除关联的轨迹数据
            db.execute_update("DELETE FROM trajectories WHERE tourist_id = %s", (tourist_id,))
            # 2. 再删除关联的预约数据
            db.execute_update("DELETE FROM reservations WHERE tourist_id = %s", (tourist_id,))

            # 3. 最后删除游客本人
            delete_query = "DELETE FROM tourists WHERE tourist_id = %s"
            affected = db.execute_update(delete_query, (tourist_id,))
            if affected == 0:
                return jsonify({'error': '游客不存在'}), 404

            # 记录日志 - 使用英文
            log_query = """
                        INSERT INTO system_logs (log_type, module, message, user_id, created_at)
                        VALUES ('warning', 'tourist', 'Delete tourist', %s, %s) \
                        """
            db.execute_update(log_query, (tourist_id, datetime.now()))

            return jsonify({'message': '游客删除成功'})

        except Exception as e:
            logger.error(f"删除游客失败: {str(e)}")
            return jsonify({'error': str(e)}), 500


# 预约管理API
@app.route('/api/reservations', methods=['GET', 'POST', 'OPTIONS'])
def manage_reservations():
    if request.method == 'OPTIONS':
        return '', 200
    elif request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        status = request.args.get('status', '')
        date = request.args.get('date', '')

        offset = (page - 1) * page_size

        query = "SELECT * FROM reservations"
        params = []
        conditions = []

        if status:
            conditions.append("status = %s")
            params.append(status)

        if date:
            conditions.append("reservation_date = %s")
            params.append(date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY reservation_date DESC, created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])

        reservations = db.execute_query(query, params)
        return jsonify(reservations)

    elif request.method == 'POST':
        data = request.json

        required_fields = ['reservation_id', 'tourist_id', 'reservation_date', 'entry_time_slot']
        if not all(field in data for field in required_fields):
            return jsonify({'error': '缺少必填字段'}), 400

        # 检查游客是否存在
        tourist_check = "SELECT COUNT(*) as count FROM tourists WHERE tourist_id = %s"
        result = db.execute_query(tourist_check, (data['tourist_id'],), fetch_one=True)

        if result['count'] == 0:
            return jsonify({'error': '游客不存在'}), 400

        # 插入预约
        insert_query = """
                       INSERT INTO reservations
                       (reservation_id, tourist_id, reservation_date, entry_time_slot,
                        group_size, status, ticket_amount, payment_status, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) \
                       """

        try:
            db.execute_update(insert_query, (
                data['reservation_id'],
                data['tourist_id'],
                data['reservation_date'],
                data['entry_time_slot'],
                data.get('group_size', 1),
                data.get('status', 'confirmed'),
                data.get('ticket_amount', 0.0),
                data.get('payment_status', 'pending'),
                datetime.now()
            ))

            # 记录日志 - 使用英文
            log_query = """
                        INSERT INTO system_logs (log_type, module, message, user_id, created_at)
                        VALUES ('info', 'reservation', 'Create new reservation', %s, %s) \
                        """
            db.execute_update(log_query, (data['tourist_id'], datetime.now()))

            return jsonify({'message': '预约创建成功', 'reservation_id': data['reservation_id']}), 201

        except Exception as e:
            logger.error(f"创建预约失败: {str(e)}")
            return jsonify({'error': str(e)}), 500


# 在 app.py 中 manage_reservations 函数下方添加
@app.route('/api/reservations/<reservation_id>', methods=['PUT', 'OPTIONS'])
def update_reservation(reservation_id):
    if request.method == 'OPTIONS':
        return '', 200

    data = request.json
    # 构建更新字段（这里允许更新状态和支付状态）
    updates = []
    params = []
    allowed_fields = ['status', 'payment_status', 'ticket_amount']

    for field in allowed_fields:
        if field in data:
            updates.append(f"{field} = %s")
            params.append(data[field])

    if not updates:
        return jsonify({'error': '无有效更新字段'}), 400

    params.append(reservation_id)
    query = f"UPDATE reservations SET {', '.join(updates)} WHERE reservation_id = %s"

    try:
        db.execute_update(query, params)
        return jsonify({'message': '预约信息更新成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# 入园核验API - 简化的版本
@app.route('/api/check-in', methods=['POST', 'OPTIONS'])
def check_in_tourist():
    """入园核验 - 修复字符集编码问题"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json(force=True)  # 使用 force=True 避免编码问题
        logger.info(f"收到入园核验请求: {data}")

        # 验证必填字段
        if not data or 'tourist_id' not in data or 'id_card' not in data:
            return jsonify({'success': False, 'message': '缺少必填字段'}), 400

        tourist_id = str(data['tourist_id']).strip()
        id_card = str(data['id_card']).strip()

        logger.info(f"查询游客: tourist_id={tourist_id}, id_card={id_card}")

        # 验证游客 - 移除 COLLATE 子句，让连接字符集处理
        query = """
                SELECT *
                FROM tourists
                WHERE tourist_id = %s
                  AND id_card = %s
                """
        tourist = db.execute_query(query, (tourist_id, id_card), fetch_one=True)

        if not tourist:
            return jsonify({'success': False, 'message': '游客信息不匹配'}), 400

        # 检查是否已入园
        if tourist.get('entry_time'):
            return jsonify({'success': False, 'message': '游客已入园'}), 400

        # 更新入园时间
        update_query = "UPDATE tourists SET entry_time = NOW() WHERE tourist_id = %s"

        # 确保参数是纯净的字符串，不带隐藏字符
        safe_tourist_id = str(tourist_id).encode('utf-8').decode('utf-8')
        logger.info(f"更新游客入园时间: {update_query} with ({safe_tourist_id})")

        try:
            db.execute_update(update_query, (safe_tourist_id,))
        except Exception as e:
            # 如果依然报错，可能是触发器问题，打印更详细的错误
            logger.error(f"数据库执行物理错误: {str(e)}")
            raise e

        # 记录轨迹
        area_id = str(data.get('area_id', 'A001')).strip()

        # 确保经纬度是数值
        try:
            latitude = float(data.get('latitude', 39.90))
            longitude = float(data.get('longitude', 116.40))
        except (ValueError, TypeError):
            latitude = 39.90
            longitude = 116.40

        # 插入轨迹记录
        trajectory_query = """
                           INSERT INTO trajectories (tourist_id, latitude, longitude, area_id, off_route, location_time)
                           VALUES (%s, %s, %s, %s, %s, NOW())
                           """

        logger.info(f"插入轨迹: {trajectory_query} with ({tourist_id}, {latitude}, {longitude}, {area_id}, False)")
        db.execute_update(trajectory_query, (
            tourist_id,
            latitude,
            longitude,
            area_id,
            False
        ))

        # 更新区域人数
        update_area_query = """
                            UPDATE flow_control
                            SET current_visitors = current_visitors + 1,
                                last_updated     = NOW()
                            WHERE area_id = %s
                            """
        logger.info(f"更新区域人数: {update_area_query} with ({area_id})")
        db.execute_update(update_area_query, (area_id,))

        # 获取更新后的游客信息
        updated_query = "SELECT tourist_id, name, entry_time FROM tourists WHERE tourist_id = %s"
        updated_tourist = db.execute_query(updated_query, (tourist_id,), fetch_one=True)

        return jsonify({
            'success': True,
            'message': '入园核验成功',
            'tourist': updated_tourist
        })

    except Exception as e:
        logger.error(f"入园核验失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'入园核验失败: {str(e)[:100]}'
        }), 500

# 实时监控API
@app.route('/api/realtime-monitor', methods=['GET', 'OPTIONS'])
def realtime_monitor():
    """实时监控数据"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        # 获取最新轨迹
        trajectory_query = """
    SELECT t.name, t.tourist_id, tr.trajectory_id, tr.area_id, tr.off_route, tr.location_time, fc.status as area_status
    FROM trajectories tr
    JOIN tourists t ON tr.tourist_id = t.tourist_id
    LEFT JOIN flow_control fc ON tr.area_id = fc.area_id
    ORDER BY tr.location_time DESC
    LIMIT 10 
"""

        trajectories = db.execute_query(trajectory_query)

        # 获取流量信息
        flow_query = "SELECT * FROM flow_control ORDER BY current_visitors DESC"
        flow_control = db.execute_query(flow_query)

        # 获取预警信息
        alert_query = """
                      SELECT * \
                      FROM system_logs
                      WHERE log_type IN ('warning', 'error', 'security')
                        AND created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                      ORDER BY created_at DESC
                      LIMIT 10 \
                      """

        alerts = db.execute_query(alert_query)

        # 获取统计数据
        stats_query = """
                      SELECT (SELECT COUNT(*) \
                              FROM tourists
                              WHERE entry_time IS NOT NULL \
                                AND exit_time IS NULL)                   as in_park_count,
                             (SELECT COUNT(*) \
                              FROM trajectories
                              WHERE location_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                                AND off_route = TRUE)                    as off_route_count,
                             (SELECT COUNT(*) \
                              FROM flow_control
                              WHERE status IN ('warning', 'restricted')) as warning_areas,
                             (SELECT COUNT(*) \
                              FROM reservations
                              WHERE status = 'confirmed'
                                AND reservation_date = CURDATE())        as today_reservations \
                      """

        stats = db.execute_query(stats_query, fetch_one=True)

        return jsonify({
            'trajectories': trajectories,
            'flow_control': flow_control,
            'alerts': alerts,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"获取实时监控数据失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


# 数据视图API
@app.route('/api/views/<view_name>', methods=['GET', 'OPTIONS'])
def get_data_view(view_name):
    """获取数据视图"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        view_methods = {
            'customer-service': DataViews.get_customer_service_view,
            'security': DataViews.get_security_realtime_view,
            'management': DataViews.get_management_dashboard_view,
            'ticket-analysis': DataViews.get_ticket_analysis_view,
            'flow-monitoring': DataViews.get_flow_monitoring_view,
            'behavior-analysis': DataViews.get_behavior_analysis_view,
            'real-time-alerts': DataViews.get_real_time_alerts,
            'daily-summary': DataViews.get_daily_summary
        }

        if view_name not in view_methods:
            return jsonify({'error': '视图不存在'}), 404

        # 获取查询参数
        args = request.args.to_dict()

        # 调用对应的视图方法
        if view_name == 'customer-service':
            result = view_methods[view_name](
                search_term=args.get('search'),
                page=int(args.get('page', 1)),
                page_size=int(args.get('page_size', 20))
            )
        elif view_name == 'security':
            result = view_methods[view_name](
                show_warnings_only=args.get('warnings_only', 'false').lower() == 'true'
            )
        elif view_name in ['management', 'ticket-analysis']:
            result = view_methods[view_name](
                start_date=args.get('start_date'),
                end_date=args.get('end_date')
            )
        elif view_name == 'behavior-analysis':
            result = view_methods[view_name](
                tourist_id=args.get('tourist_id')
            )
        elif view_name == 'real-time-alerts':
            result = view_methods[view_name](
                limit=int(args.get('limit', 20))
            )
        else:
            result = view_methods[view_name]()

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取视图失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


# 存储过程API
@app.route('/api/procedures/<proc_name>', methods=['POST', 'OPTIONS'])
def execute_procedure(proc_name):
    """执行存储过程"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        procedures = {
            'update-flow-status': DatabaseProcedures.update_flow_status,
            'generate-daily-report': DatabaseProcedures.generate_daily_report,
            'process-expired-reservations': DatabaseProcedures.process_expired_reservations,
            'simulate-trajectory-data': DatabaseProcedures.simulate_trajectory_data,
            'backup-database': DatabaseProcedures.backup_database
        }

        if proc_name not in procedures:
            return jsonify({'error': '存储过程不存在'}), 404

        # 获取参数
        data = request.json or {}

        # 调用对应的存储过程
        if proc_name == 'generate-daily-report':
            result = procedures[proc_name](data.get('report_date'))
        elif proc_name == 'simulate-trajectory-data':
            result = procedures[proc_name](data.get('minutes', 60))
        elif proc_name == 'backup-database':
            result = procedures[proc_name](data.get('backup_type', 'incremental'))
        else:
            result = procedures[proc_name]()

        return jsonify({
            'success': True,
            'message': f'存储过程 {proc_name} 执行成功',
            'result': result
        })

    except Exception as e:
        logger.error(f"执行存储过程失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


# 数据统计API
@app.route('/api/stats', methods=['GET', 'OPTIONS'])
def get_statistics():
    """获取统计数据"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        # 今日统计
        today = datetime.now().strftime('%Y-%m-%d')
        recent_query = """
                       SELECT t.name, \
                              t.tourist_id, \
                              DATE_FORMAT(t.entry_time, '%%H:%%i:%%s') as time, \
                              tr.area_id                               as area
                       FROM tourists t
                                LEFT JOIN (
                           -- 关联轨迹表获取最新的入园区域
                           SELECT tourist_id, area_id
                           FROM trajectories
                           WHERE (tourist_id, location_time) IN (SELECT tourist_id, MIN(location_time) \
                                                                 FROM trajectories \
                                                                 GROUP BY tourist_id)) tr \
                                          ON t.tourist_id = tr.tourist_id
                       WHERE t.entry_time IS NOT NULL
                       ORDER BY t.entry_time DESC
                       LIMIT 5
                       """
        recent_records = db.execute_query(recent_query)
        stats_query = """
                      SELECT
                          -- 游客统计
                          (SELECT COUNT(*) FROM tourists WHERE DATE(entry_time) = %s)               as visitors_today,
                          (SELECT COUNT(*) \
                           FROM tourists
                           WHERE entry_time IS NOT NULL \
                             AND exit_time IS NULL)                                                 as visitors_in_park,
                          (SELECT COUNT(*) FROM tourists)                                           as total_visitors,

                          -- 预约统计
                          (SELECT COUNT(*) FROM reservations WHERE reservation_date = %s)           as reservations_today,
                          (SELECT COUNT(*) \
                           FROM reservations
                           WHERE status = 'confirmed' \
                             AND reservation_date = %s)                                             as confirmed_today,
                          (SELECT COUNT(*) FROM reservations)                                       as total_reservations,

                          -- 财务统计
                          (SELECT SUM(ticket_amount) FROM reservations WHERE reservation_date = %s) as revenue_today,
                          (SELECT SUM(ticket_amount) FROM reservations)                             as total_revenue,

                          -- 轨迹统计
                          (SELECT COUNT(*) FROM trajectories WHERE DATE(location_time) = %s)        as trajectories_today,
                          (SELECT COUNT(*) \
                           FROM trajectories
                           WHERE off_route = TRUE \
                             AND DATE(location_time) = %s)                                          as off_route_today,
                          (SELECT COUNT(*) FROM trajectories)                                       as total_trajectories,

                          -- 区域统计
                          (SELECT COUNT(*) FROM flow_control)                                       as total_areas,
                          (SELECT COUNT(*) FROM flow_control WHERE status = 'warning')              as warning_areas,
                          (SELECT COUNT(*) FROM flow_control WHERE status = 'restricted')           as restricted_areas,

                          -- 预警统计
                          (SELECT COUNT(*) \
                           FROM system_logs
                           WHERE DATE(created_at) = %s \
                             AND log_type = 'warning')                                              as warnings_today,
                          (SELECT COUNT(*) \
                           FROM system_logs
                           WHERE DATE(created_at) = %s \
                             AND log_type = 'security')                                             as security_alerts_today \
                      """

        stats = db.execute_query(stats_query, (
            today, today, today, today, today, today, today, today
        ), fetch_one=True)

        # 最近7天趋势
        trend_query = """
                      SELECT DATE(t.entry_time)                                                  as date,
                             COUNT(DISTINCT t.tourist_id)                                        as visitors,
                             SUM(r.ticket_amount)                                                as revenue,
                             COUNT(DISTINCT CASE WHEN tr.off_route = TRUE THEN t.tourist_id END) as off_route_count
                      FROM tourists t
                               LEFT JOIN reservations r ON t.tourist_id = r.tourist_id
                               LEFT JOIN trajectories tr \
                                         ON t.tourist_id = tr.tourist_id AND DATE(tr.location_time) = DATE(t.entry_time)
                      WHERE t.entry_time >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                      GROUP BY DATE(t.entry_time)
                      ORDER BY date \
                      """

        trends = db.execute_query(trend_query)

        return jsonify({
            'stats': stats,
            'recent_records': recent_records, # 新增：最近记录
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"获取统计数据失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trajectories', methods=['GET', 'POST', 'OPTIONS'])
def manage_trajectories():
    if request.method == 'OPTIONS':
        return '', 200
    elif request.method == 'GET':
        # 获取轨迹列表
        try:
            page = request.args.get('page', 1, type=int)
            page_size = request.args.get('page_size', 20, type=int)
            tourist_id = request.args.get('tourist_id', '')
            area_id = request.args.get('area_id', '')

            offset = (page - 1) * page_size

            query = """
                    SELECT t.*, tr.name, tr.phone, fc.status as area_status
                    FROM trajectories t
                             LEFT JOIN tourists tr ON t.tourist_id = tr.tourist_id
                             LEFT JOIN flow_control fc ON t.area_id = fc.area_id \
                    """
            params = []
            conditions = []

            if tourist_id:
                conditions.append("t.tourist_id = %s")
                params.append(tourist_id)

            if area_id:
                conditions.append("t.area_id = %s")
                params.append(area_id)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY t.location_time DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])

            trajectories = db.execute_query(query, params)

            # 获取总数
            count_query = "SELECT COUNT(*) as total FROM trajectories"
            if conditions:
                count_query += " WHERE " + " AND ".join(conditions)

            total_result = db.execute_query(count_query, params[:-2] if conditions else [], fetch_one=True)

            return jsonify({
                'trajectories': trajectories,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total_result['total'] if total_result else 0
                }
            })

        except Exception as e:
            logger.error(f"获取轨迹数据失败: {str(e)}")
            return jsonify({'error': str(e)}), 500

    elif request.method == 'POST':
        # 创建新轨迹（用于测试）
        data = request.json

        required_fields = ['tourist_id', 'latitude', 'longitude']
        if not all(field in data for field in required_fields):
            return jsonify({'error': '缺少必填字段'}), 400

        # 检查游客是否存在
        check_query = "SELECT COUNT(*) as count FROM tourists WHERE tourist_id = %s"
        result = db.execute_query(check_query, (data['tourist_id'],), fetch_one=True)

        if result['count'] == 0:
            return jsonify({'error': '游客不存在'}), 400

        # 插入新轨迹
        insert_query = """
                       INSERT INTO trajectories (tourist_id, latitude, longitude, area_id, off_route, location_time)
                       VALUES (%s, %s, %s, %s, %s, %s) \
                       """

        try:
            db.execute_update(insert_query, (
                data['tourist_id'],
                data['latitude'],
                data['longitude'],
                data.get('area_id', 'A001'),
                data.get('off_route', False),
                datetime.now()
            ))

            # 记录日志 - 使用英文
            log_query = """
                        INSERT INTO system_logs (log_type, module, message, user_id, created_at)
                        VALUES ('info', 'trajectory', 'Create trajectory record', %s, %s) \
                        """
            db.execute_update(log_query, (data['tourist_id'], datetime.now()))

            return jsonify({'message': '轨迹记录创建成功'}), 201

        except Exception as e:
            logger.error(f"创建轨迹失败: {str(e)}")
            return jsonify({'error': str(e)}), 500


@app.route('/api/trajectories/test-data', methods=['POST', 'OPTIONS'])
def create_test_trajectories():
    """创建测试轨迹数据"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        # 先检查是否有游客
        tourists_query = "SELECT tourist_id FROM tourists LIMIT 5"
        tourists = db.execute_query(tourists_query)

        if not tourists:
            return jsonify({'error': '没有游客数据，请先创建游客'}), 400

        # 创建测试轨迹数据
        test_trajectories = []
        for i, tourist in enumerate(tourists[:3]):  # 只取前3个游客
            for j in range(3):  # 每个游客创建3条轨迹
                trajectory_data = {
                    'tourist_id': tourist['tourist_id'],
                    'latitude': 39.9042 + (j * 0.001),
                    'longitude': 116.4074 + (i * 0.001),
                    'area_id': f'A00{j + 1}',
                    'off_route': (j == 2),  # 第三条轨迹设为异常
                    'location_time': (datetime.now() - timedelta(minutes=j * 10)).isoformat()
                }

                insert_query = """
                               INSERT INTO trajectories (tourist_id, latitude, longitude, area_id, off_route, location_time)
                               VALUES (%s, %s, %s, %s, %s, %s) \
                               """

                db.execute_update(insert_query, (
                    trajectory_data['tourist_id'],
                    trajectory_data['latitude'],
                    trajectory_data['longitude'],
                    trajectory_data['area_id'],
                    trajectory_data['off_route'],
                    datetime.now() - timedelta(minutes=j * 10)
                ))

                test_trajectories.append(trajectory_data)

        logger.info(f"创建了 {len(test_trajectories)} 条测试轨迹数据")

        return jsonify({
            'message': f'成功创建 {len(test_trajectories)} 条测试轨迹数据',
            'trajectories': test_trajectories
        })

    except Exception as e:
        logger.error(f"创建测试轨迹数据失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


# 系统日志API
@app.route('/api/logs', methods=['GET', 'OPTIONS'])
def get_system_logs():
    """获取系统日志"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        log_type = request.args.get('type', '')
        module = request.args.get('module', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')

        offset = (page - 1) * page_size

        query = "SELECT * FROM system_logs"
        params = []
        conditions = []

        if log_type:
            conditions.append("log_type = %s")
            params.append(log_type)

        if module:
            conditions.append("module = %s")
            params.append(module)

        if start_date:
            conditions.append("DATE(created_at) >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("DATE(created_at) <= %s")
            params.append(end_date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])

        logs = db.execute_query(query, params)

        # 获取总数
        count_query = "SELECT COUNT(*) as total FROM system_logs"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions)

        total_result = db.execute_query(count_query, params[:-2] if conditions else [], fetch_one=True)

        return jsonify({
            'logs': logs,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total_result['total'] if total_result else 0
            }
        })

    except Exception as e:
        logger.error(f"获取系统日志失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/flow-control', methods=['GET', 'OPTIONS'])
def get_flow_control():
    """获取所有流量管控数据"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        query = "SELECT * FROM flow_control ORDER BY area_id"
        flow_data = db.execute_query(query)
        return jsonify(flow_data)
    except Exception as e:
        logger.error(f"获取流量管控数据失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/flow-control/<area_id>', methods=['PUT', 'OPTIONS'])
def update_flow_control(area_id):
    """更新单个区域的流量管控配置"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.json
        # 验证必填字段
        if not data:
            return jsonify({'error': '无更新数据'}), 400

        # 构建更新语句
        updates = []
        params = []
        allowed_fields = ['daily_capacity', 'warning_threshold', 'current_visitors']

        for field in allowed_fields:
            if field in data and data[field] is not None:
                updates.append(f"{field} = %s")
                params.append(data[field])

        if not updates:
            return jsonify({'error': '无有效更新字段'}), 400

        # 添加更新时间和区域ID
        updates.append("last_updated = %s")
        params.append(datetime.now())
        params.append(area_id)

        # 执行更新
        query = f"UPDATE flow_control SET {', '.join(updates)} WHERE area_id = %s"
        affected = db.execute_update(query, params)

        if affected == 0:
            return jsonify({'error': '区域不存在'}), 404

        # 触发流量状态更新
        DatabaseProcedures.update_flow_status()

        # 返回更新后的完整数据
        get_query = "SELECT * FROM flow_control WHERE area_id = %s"
        updated_area = db.execute_query(get_query, (area_id,), fetch_one=True)

        return jsonify({
            'message': f'区域 {area_id} 更新成功',
            'data': updated_area
        })
    except Exception as e:
        logger.error(f"更新流量管控失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ecological-feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    try:
        query = """
                INSERT INTO ecological_feedback (tourist_id, area_id, feedback_type, content)
                VALUES (%s, %s, %s, %s)
                """
        db.execute_update(query, (
            data['tourist_id'],
            data['area_id'],
            data['feedback_type'],
            data['content']
        ))
        return jsonify({'success': True, 'message': '反馈提交成功，感谢您参与生态保护！'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/eco-stats/<role>', methods=['GET'])
def get_eco_stats(role):
    try:
        if role == 'manager':
            # 管理层从区域汇总视图查询数据
            result = db.execute_query("SELECT * FROM view_area_eco_summary")
        elif role == 'officer':
            # 监管员从明细视图查询待处理的数据
            result = db.execute_query("SELECT * FROM view_eco_feedback_details WHERE status = '待处理'")
        else:
            return jsonify({'error': '未授权角色'}), 403

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '资源不存在'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"服务器内部错误: {str(error)}")
    return jsonify({'error': '服务器内部错误'}), 500


if __name__ == '__main__':
    # 初始化数据库（如果不存在）
    try:
        # 创建必要的表 - 使用utf8mb4字符集
        init_queries = [
            """
            CREATE TABLE IF NOT EXISTS flow_control
            (
                area_id           VARCHAR(50) PRIMARY KEY,
                daily_capacity    INT NOT NULL,
                current_visitors  INT                                      DEFAULT 0,
                warning_threshold DECIMAL(5, 2)                            DEFAULT 0.80,
                status            ENUM ('normal', 'warning', 'restricted') DEFAULT 'normal',
                last_updated      TIMESTAMP                                DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_status (status)
            ) CHARACTER SET utf8mb4
              COLLATE utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS system_logs
            (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                log_type   VARCHAR(20),
                module     VARCHAR(50),
                message    TEXT,
                user_id    VARCHAR(50),
                ip_address VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_log_type (log_type),
                INDEX idx_created_at (created_at)
            ) CHARACTER SET utf8mb4
              COLLATE utf8mb4_unicode_ci
            """,
            """
            INSERT IGNORE INTO flow_control (area_id, daily_capacity)
            VALUES ('A001', 1000),
                   ('A002', 800),
                   ('A003', 500),
                   ('A004', 1200)
            """
        ]

        for query in init_queries:
            try:
                db.execute_update(query)
            except Exception as e:
                logger.warning(f"执行初始化查询时出错: {str(e)}")
                # 继续执行其他查询

        logger.info("数据库初始化完成")

    except Exception as e:
        logger.warning(f"数据库初始化失败: {str(e)}")

    # 启动应用
    app.run(host='0.0.0.0', port=5000, debug=True)