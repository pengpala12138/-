# backend/app.py
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
from sqlalchemy import text
import logging
import random
import socket
import threading
import time
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://share_user:515408@192.168.69.97:3306/sjk'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

db = SQLAlchemy(app)

# 全局变量存储设备状态提醒
device_alerts = defaultdict(list)


# ============ 数据模型定义（使用已有region_info表）============
class RegionInfo(db.Model):
    """已有区域信息表"""
    __tablename__ = 'region_info'

    region_id = db.Column(db.String(20), primary_key=True)
    region_name = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            'region_id': self.region_id,
            'region_name': self.region_name
        }


class MonitorIndicator(db.Model):
    """监测指标信息表"""
    __tablename__ = 'monitor_indicator'

    indicator_id = db.Column(db.String(20), primary_key=True)
    indicator_name = db.Column(db.String(50), nullable=False)
    unit = db.Column(db.String(20))
    standard_upper = db.Column(db.Numeric(10, 4), nullable=False)
    standard_lower = db.Column(db.Numeric(10, 4), nullable=False)
    monitor_freq = db.Column(db.String(10))

    # 关系
    env_data = db.relationship('EnvironmentData', backref='indicator', lazy=True)

    def to_dict(self):
        return {
            'indicator_id': self.indicator_id,
            'indicator_name': self.indicator_name,
            'unit': self.unit,
            'standard_upper': float(self.standard_upper),
            'standard_lower': float(self.standard_lower),
            'monitor_freq': self.monitor_freq
        }


class MonitorDevice(db.Model):
    """监测设备信息表"""
    __tablename__ = 'monitor_device'

    device_id = db.Column(db.String(20), primary_key=True)
    device_type = db.Column(db.String(50), nullable=False)
    region_id = db.Column(db.String(20), db.ForeignKey('region_info.region_id'), nullable=False)
    install_time = db.Column(db.Date)
    calibration_cycle = db.Column(db.String(8))
    operation_status = db.Column(db.String(10), nullable=False, default='正常')
    comm_proto = db.Column(db.String(50))
    status_update_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # 移除 last_maintenance 字段

    # 关系
    env_data = db.relationship('EnvironmentData', backref='device', lazy=True)
    region = db.relationship('RegionInfo', backref='devices', lazy=True)

    def to_dict(self):
        return {
            'device_id': self.device_id,
            'device_type': self.device_type,
            'region_id': self.region_id,
            'install_time': self.install_time.isoformat() if self.install_time else None,
            'calibration_cycle': self.calibration_cycle,
            'operation_status': self.operation_status,
            'comm_proto': self.comm_proto,
            'status_update_time': self.status_update_time.isoformat() if self.status_update_time else None,
            'region_name': self.region.region_name if self.region else None
        }


class EnvironmentData(db.Model):
    """环境监测数据表"""
    __tablename__ = 'environment_data'

    data_id = db.Column(db.String(20), primary_key=True)
    indicator_id = db.Column(db.String(20), db.ForeignKey('monitor_indicator.indicator_id'), nullable=False)
    device_id = db.Column(db.String(20), db.ForeignKey('monitor_device.device_id'), nullable=False)
    collection_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    monitor_value = db.Column(db.Numeric(10, 4))
    region_id = db.Column(db.String(20), db.ForeignKey('region_info.region_id'), nullable=False)
    data_quality = db.Column(db.String(2), nullable=False, default='中')
    is_abnormal = db.Column(db.Boolean, default=False)
    abnormal_reason = db.Column(db.String(200))

    # 关系
    region = db.relationship('RegionInfo', backref='env_data', lazy=True)

    def to_dict(self):
        return {
            'data_id': self.data_id,
            'indicator_id': self.indicator_id,
            'device_id': self.device_id,
            'collection_time': self.collection_time.isoformat() if self.collection_time else None,
            'monitor_value': float(self.monitor_value) if self.monitor_value else None,
            'region_id': self.region_id,
            'data_quality': self.data_quality,
            'is_abnormal': self.is_abnormal,
            'abnormal_reason': self.abnormal_reason,
            'indicator_name': self.indicator.indicator_name if self.indicator else None,
            'device_type': self.device.device_type if self.device else None,
            'region_name': self.region.region_name if self.region else None
        }


# ============ 辅助函数 ============
def should_create_alert(device_id, indicator_id, alert_type, data_id=None):
    """检查是否应该创建新警报"""
    alert_key = f"{alert_type}_{device_id}_{indicator_id if indicator_id else ''}".rstrip('_')

    if alert_key in device_alerts:
        # 检查最近是否有未处理的相同警报
        recent_time = datetime.now() - timedelta(minutes=30)  # 30分钟内
        recent_alerts = [
            alert for alert in device_alerts[alert_key]
            if datetime.fromisoformat(alert['time']) > recent_time
               and not alert.get('handled', False)
        ]
        return len(recent_alerts) == 0  # 如果没有未处理的最近警报，则创建

    return True  # 没有历史警报，可以创建


# ============ 业务服务类 ============
class EnvironmentMonitorService:

    @staticmethod
    def upload_environment_data(data_dict):
        """物联网设备上传环境数据"""
        try:
            # 生成数据ID
            max_id_result = db.session.query(
                db.func.max(EnvironmentData.data_id)
            ).scalar()

            if max_id_result and max_id_result.startswith('ED'):
                try:
                    # 提取数字部分并递增
                    current_num = int(max_id_result[2:])
                    new_num = current_num + 1
                    data_id = f"ED{new_num:06d}"  # 保持6位数字
                except ValueError:
                    # 如果解析失败，使用当前时间戳
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    random_str = str(random.randint(10000, 99999))
                    data_id = f"ED{timestamp[-10:]}{random_str}"[:20]
            else:
                # 如果没有数据，从000001开始
                data_id = "ED000001"
            # 检查设备是否存在
            device = MonitorDevice.query.get(data_dict.get('device_id'))
            if not device:
                return {'success': False, 'error': '设备不存在'}

            # 检查指标是否存在
            indicator = MonitorIndicator.query.get(data_dict.get('indicator_id'))
            if not indicator:
                return {'success': False, 'error': '监测指标不存在'}

            # 检查阈值是否异常
            monitor_value = float(data_dict.get('monitor_value', 0))
            is_abnormal = False
            abnormal_reason = None

            if monitor_value > float(indicator.standard_upper) or monitor_value < float(indicator.standard_lower):
                is_abnormal = True
                abnormal_reason = f"监测值 {monitor_value} {'>' if monitor_value > indicator.standard_upper else '<'} 阈值范围 [{indicator.standard_lower}, {indicator.standard_upper}]"

                # 只有设备状态正常时才记录异常预警
                if device.operation_status == '正常':
                    # 检查是否需要创建新警报
                    if should_create_alert(device.device_id, indicator.indicator_id, 'data_abnormal', data_id=data_id):
                        alert_key = f"data_abnormal_{device.device_id}_{indicator.indicator_id}"
                        alert_message = f"设备 {device.device_id} 监测指标 {indicator.indicator_name} 异常：{abnormal_reason}"
                        device_alerts[alert_key].append({
                            'time': datetime.now().isoformat(),
                            'message': alert_message,
                            'device_id': device.device_id,
                            'data_id': data_id,
                            'indicator_id': indicator.indicator_id,
                            'value': monitor_value,
                            'threshold': f"[{indicator.standard_lower}, {indicator.standard_upper}]",
                            'alert_type': 'data_abnormal'
                        })

            # 创建监测数据
            env_data = EnvironmentData(
                data_id=data_id,
                indicator_id=data_dict.get('indicator_id'),
                device_id=data_dict.get('device_id'),
                region_id=device.region_id,
                collection_time=datetime.strptime(data_dict.get('collection_time'),
                                                  '%Y-%m-%d %H:%M:%S') if data_dict.get(
                    'collection_time') else datetime.utcnow(),
                monitor_value=monitor_value,
                data_quality=data_dict.get('data_quality', '中'),
                is_abnormal=is_abnormal,
                abnormal_reason=abnormal_reason
            )

            db.session.add(env_data)

            # 更新设备状态时间
            device.status_update_time = datetime.utcnow()

            db.session.commit()

            logger.info(f"环境数据上传成功: {data_id}")
            return {'success': True, 'data_id': data_id, 'is_abnormal': is_abnormal}

        except Exception as e:
            db.session.rollback()
            logger.error(f"环境数据上传失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_device_calibration(device_id, calibration_result, calibration_date=None):
        """更新设备校准状态"""
        try:
            device = MonitorDevice.query.get(device_id)
            if not device:
                return {'success': False, 'error': '设备不存在'}

            # 更新安装时间（表示校准时间）
            if calibration_date:
                # 使用指定的校准日期
                device.install_time = datetime.strptime(calibration_date, '%Y-%m-%d').date()
            else:
                # 使用当前日期
                device.install_time = datetime.utcnow().date()

            # 更新设备状态为正常（如果校准合格）
            if calibration_result == '合格':
                device.operation_status = '正常'
                # 清除该设备的故障警报
                alert_key = f"device_fault_{device_id}"
                if alert_key in device_alerts:
                    for alert in device_alerts[alert_key]:
                        alert['handled'] = True
            elif calibration_result == '不合格':
                device.operation_status = '故障'

            device.status_update_time = datetime.utcnow()
            db.session.commit()

            logger.info(f"设备校准更新: {device_id}, 校准结果: {calibration_result}, 校准时间: {device.install_time}")
            return {'success': True, 'device_id': device_id, 'calibration_result': calibration_result}

        except Exception as e:
            db.session.rollback()
            logger.error(f"设备校准更新失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_device_status(device_id, status, calibration_data=None):
        """更新设备状态"""
        try:
            device = MonitorDevice.query.get(device_id)
            if not device:
                return {'success': False, 'error': '设备不存在'}

            # 验证状态是否有效
            valid_statuses = ['正常', '故障', '离线']
            if status not in valid_statuses:
                return {'success': False, 'error': f'无效的状态: {status}'}

            old_status = device.operation_status
            device.operation_status = status

            # 如果是故障状态，记录提醒
            if status == '故障' and old_status != '故障':
                if should_create_alert(device_id, None, 'device_fault'):
                    alert_key = f"device_fault_{device_id}"
                    alert_message = f"设备 {device_id} ({device.device_type}) 发生故障！请及时检查维修。"
                    device_alerts[alert_key].append({
                        'time': datetime.now().isoformat(),
                        'message': alert_message,
                        'device_id': device_id,
                        'device_type': device.device_type,
                        'region': device.region.region_name if device.region else '未知',
                        'alert_type': 'device_fault'
                    })
            # 如果是从故障状态变为正常状态，清除该设备的故障提醒
            elif old_status == '故障' and status == '正常':
                alert_key = f"device_fault_{device_id}"
                if alert_key in device_alerts:
                    for alert in device_alerts[alert_key]:
                        alert['handled'] = True

            # 如果是校准，更新校准信息
            if calibration_data:
                if calibration_data.get('calibration_result') == '合格':
                    device.operation_status = '正常'
                device.calibration_cycle = calibration_data.get('calibration_cycle', device.calibration_cycle)

            device.status_update_time = datetime.utcnow()
            db.session.commit()

            logger.info(f"设备状态更新: {device_id} {old_status} -> {status}")
            return {'success': True, 'old_status': old_status, 'new_status': status, 'device_id': device_id}

        except Exception as e:
            db.session.rollback()
            logger.error(f"设备状态更新失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_all_devices():
        """获取所有设备信息"""
        try:
            devices = MonitorDevice.query.order_by(MonitorDevice.device_id).all()
            result = []
            for device in devices:
                device_dict = device.to_dict()
                # 添加校准状态信息
                sql = text("CALL sp_get_devices_need_calibration()")
                calibration_result = db.session.execute(sql)
                calibration_found = False
                for row in calibration_result:
                    cal_device = dict(row._mapping)
                    if cal_device['device_id'] == device.device_id:
                        device_dict['calibration_status'] = cal_device['calibration_status']
                        calibration_found = True
                        break

                if not calibration_found:
                    device_dict['calibration_status'] = '正常'

                result.append(device_dict)

            return {'success': True, 'devices': result}

        except Exception as e:
            logger.error(f"获取所有设备失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_device_management_data():
        """获取设备管理数据（包括校准状态）"""
        try:
            # 获取所有设备
            devices = MonitorDevice.query.order_by(MonitorDevice.device_id).all()

            # 获取校准状态
            sql = text("CALL sp_get_devices_need_calibration()")
            calibration_result = db.session.execute(sql)
            calibration_map = {}
            for row in calibration_result:
                device_data = dict(row._mapping)
                calibration_map[device_data['device_id']] = device_data['calibration_status']

            result = []
            for device in devices:
                device_dict = device.to_dict()
                device_dict['calibration_status'] = calibration_map.get(device.device_id, '正常')
                result.append(device_dict)

            return {'success': True, 'devices': result}

        except Exception as e:
            logger.error(f"获取设备管理数据失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_abnormal_data(start_date=None, end_date=None):
        """获取异常数据"""
        try:
            query = EnvironmentData.query.filter_by(is_abnormal=True)

            if start_date:
                query = query.filter(EnvironmentData.collection_time >= start_date)
            if end_date:
                query = query.filter(EnvironmentData.collection_time <= end_date)

            abnormal_data = query.order_by(EnvironmentData.collection_time.desc()).all()

            result = []
            for data in abnormal_data:
                result.append(data.to_dict())

            return {'success': True, 'data': result, 'count': len(result)}

        except Exception as e:
            logger.error(f"获取异常数据失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_core_protection_data():
        """获取核心保护区数据"""
        try:
            sql = text(""" 
                SELECT 
                    ri.region_name,
                    mi.indicator_name,
                    mi.unit,
                    ed.collection_time,
                    ed.monitor_value,
                    mi.standard_upper,
                    mi.standard_lower,
                    CASE
                        WHEN ed.monitor_value > mi.standard_upper THEN '超出上限'
                        WHEN ed.monitor_value < mi.standard_lower THEN '低于下限'
                        ELSE '正常'
                    END as threshold_status,
                    ed.data_quality,
                    ed.is_abnormal,
                    ed.abnormal_reason,
                    md.device_type,
                    md.operation_status as device_status
                FROM environment_data ed
                JOIN region_info ri ON ed.region_id = ri.region_id
                JOIN monitor_indicator mi ON ed.indicator_id = mi.indicator_id
                JOIN monitor_device md ON ed.device_id = md.device_id
                ORDER BY ed.collection_time DESC
                LIMIT 100
            """)

            result = db.session.execute(sql)

            data = []
            for row in result:
                data.append(dict(row._mapping))

            return {'success': True, 'data': data}

        except Exception as e:
            logger.error(f"获取核心保护区数据失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_device_status_summary():
        """获取设备状态统计"""
        try:
            sql = text("SELECT * FROM v_device_status_summary")
            result = db.session.execute(sql)

            summary = []
            for row in result:
                summary.append(dict(row._mapping))

            return {'success': True, 'summary': summary}

        except Exception as e:
            logger.error(f"获取设备状态统计失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def generate_monitor_report(start_date, end_date):
        """生成监测报告"""
        try:
            sql = text(""" 
                CALL sp_generate_env_monitor_report(:start_date, :end_date)
            """)

            result = db.session.execute(sql, {
                'start_date': start_date,
                'end_date': end_date
            })

            report = []
            for row in result:
                report.append(dict(row._mapping))

            return {'success': True, 'report': report}

        except Exception as e:
            logger.error(f"生成监测报告失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_devices_need_calibration():
        """获取需要校准的设备"""
        try:
            sql = text("CALL sp_get_devices_need_calibration()")
            result = db.session.execute(sql)

            devices = []
            for row in result:
                devices.append(dict(row._mapping))

            return {'success': True, 'devices': devices}

        except Exception as e:
            logger.error(f"获取需要校准的设备失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_available_regions():
        """获取所有可用的区域"""
        try:
            regions = RegionInfo.query.order_by(RegionInfo.region_name).all()
            return {'success': True, 'regions': [r.to_dict() for r in regions]}
        except Exception as e:
            logger.error(f"获取区域列表失败: {str(e)}")
            return {'success': False, 'error': str(e)}


# ============ 设备状态自动更新线程 ============
def device_status_auto_update():
    """每小时自动更新设备状态"""
    while True:
        try:
            with app.app_context():
                devices = MonitorDevice.query.all()
                for device in devices:
                    # 随机模拟设备状态变化
                    if random.random() < 0.05:  # 5%的概率状态会变化
                        old_status = device.operation_status
                        new_status = random.choice(['正常', '故障', '离线'])

                        if old_status != new_status:
                            device.operation_status = new_status
                            device.status_update_time = datetime.utcnow()

                            # 如果是新故障，记录提醒
                            if new_status == '故障' and old_status != '故障':
                                if should_create_alert(device.device_id, None, 'device_fault'):
                                    alert_key = f"auto_fault_{device.device_id}"
                                    alert_message = f"设备 {device.device_id} ({device.device_type}) 自动检测到故障！"
                                    device_alerts[alert_key].append({
                                        'time': datetime.now().isoformat(),
                                        'message': alert_message,
                                        'device_id': device.device_id,
                                        'device_type': device.device_type,
                                        'alert_type': 'device_fault'
                                    })

                            logger.info(f"设备状态自动更新: {device.device_id} {old_status} -> {new_status}")

                db.session.commit()
                logger.info(f"设备状态自动更新完成，处理了 {len(devices)} 个设备")
        except Exception as e:
            logger.error(f"设备状态自动更新失败: {str(e)}")

        # 每小时运行一次
        time.sleep(3600)


# ============ API接口 ============
@app.route('/')
def index():
    return ''' 
    <html>
        <head><title>生态环境监测系统API</title></head>
        <body>
            <h1>🌲 国家公园生态环境监测系统API</h1>
            <p>后端服务运行正常！</p>
            <p>API文档：</p>
            <ul>
                <li><a href="/api/health">健康检查</a></li>
                <li><a href="/api/regions">区域列表</a></li>
                <li><a href="/api/environment/data/recent">最近数据</a></li>
                <li><a href="/api/environment/data/abnormal">异常数据</a></li>
            </ul>
            <p>前端地址：<a href="http://localhost:3001">http://localhost:3001</a></p>
        </body>
    </html>
    '''


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})


@app.route('/api/regions', methods=['GET'])
def get_regions():
    """获取所有区域"""
    result = EnvironmentMonitorService.get_available_regions()
    return jsonify(result)


@app.route('/api/environment/data/upload', methods=['POST'])
def upload_environment_data():
    """上传环境监测数据"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        required_fields = ['indicator_id', 'device_id', 'monitor_value']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400

        result = EnvironmentMonitorService.upload_environment_data(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"API错误 - 上传环境数据: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/abnormal', methods=['GET'])
def get_abnormal_data():
    """获取异常数据"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        result = EnvironmentMonitorService.get_abnormal_data(start_date, end_date)
        return jsonify(result)

    except Exception as e:
        logger.error(f"API错误 - 获取异常数据: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/<device_id>/calibration', methods=['PUT'])
def update_device_calibration(device_id):
    """更新设备校准状态"""
    try:
        data = request.get_json()
        if not data or 'calibration_result' not in data:
            return jsonify({'success': False, 'error': '缺少校准结果信息'}), 400

        result = EnvironmentMonitorService.update_device_calibration(
            device_id,
            data['calibration_result'],
            data.get('calibration_date')
        )
        return jsonify(result)

    except Exception as e:
        logger.error(f"API错误 - 更新设备校准: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/<device_id>/status', methods=['PUT'])
def update_device_status(device_id):
    """更新设备状态"""
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': '缺少状态信息'}), 400

        # 保持 calibration_data 参数可选
        calibration_data = data.get('calibration_data')
        result = EnvironmentMonitorService.update_device_status(
            device_id,
            data['status'],
            calibration_data
        )
        return jsonify(result)

    except Exception as e:
        logger.error(f"API错误 - 更新设备状态: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/all', methods=['GET'])
def get_all_devices():
    """获取所有设备信息"""
    try:
        result = EnvironmentMonitorService.get_all_devices()
        return jsonify(result)
    except Exception as e:
        logger.error(f"API错误 - 获取所有设备: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/management', methods=['GET'])
def get_device_management_data():
    """获取设备管理数据"""
    try:
        result = EnvironmentMonitorService.get_device_management_data()
        return jsonify(result)
    except Exception as e:
        logger.error(f"API错误 - 获取设备管理数据: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/status-summary', methods=['GET'])
def get_device_status_summary():
    """获取设备状态统计"""
    try:
        result = EnvironmentMonitorService.get_device_status_summary()
        return jsonify(result)

    except Exception as e:
        logger.error(f"API错误 - 获取设备状态统计: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/need-calibration', methods=['GET'])
def get_devices_need_calibration():
    """获取需要校准的设备"""
    try:
        result = EnvironmentMonitorService.get_devices_need_calibration()
        return jsonify(result)

    except Exception as e:
        logger.error(f"API错误 - 获取需要校准的设备: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats/dashboard', methods=['GET'])
def get_dashboard_stats():
    try:
        # 设备总数
        total_devices = MonitorDevice.query.count()

        # 正常设备数量
        normal_devices = MonitorDevice.query.filter_by(operation_status='正常').count()

        # 数据总数
        total_data_count = EnvironmentData.query.count()

        # 异常数据总数（历史所有）
        total_abnormal_data = EnvironmentData.query.filter_by(is_abnormal=True).count()

        # 最近30天异常数据
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_abnormal_data = EnvironmentData.query.filter(
            EnvironmentData.is_abnormal == True,
            EnvironmentData.collection_time >= thirty_days_ago
        ).count()

        # 需要校准的设备数量
        sql = text("CALL sp_get_devices_need_calibration()")
        result = db.session.execute(sql)
        need_calibration = 0
        devices_list = []
        for row in result:
            device_dict = dict(row._mapping)
            devices_list.append(device_dict)
            if device_dict['calibration_status'] in ['逾期未校准', '即将到期']:
                need_calibration += 1

        return jsonify({
            'success': True,
            'stats': {
                'total_devices': total_devices,
                'normal_devices': normal_devices,
                'total_data_count': total_data_count,  # 新增：数据总数
                'total_abnormal_count': total_abnormal_data,  # 新增：异常数据总数
                'recent_abnormal_count': recent_abnormal_data,  # 新增：近期异常数据
                'need_calibration': need_calibration
            }
        })
    except Exception as e:
        logger.error(f"获取仪表盘统计失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/report', methods=['GET'])
def generate_report():
    """生成监测报告"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date or not end_date:
            return jsonify({'success': False, 'error': '需要指定开始日期和结束日期'}), 400

        result = EnvironmentMonitorService.generate_monitor_report(start_date, end_date)
        return jsonify(result)

    except Exception as e:
        logger.error(f"API错误 - 生成监测报告: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/recent', methods=['GET'])
def get_recent_data():
    """获取最近的环境数据"""
    try:
        days = request.args.get('days', 30, type=int)  # 默认30天
        region_id = request.args.get('region_id')
        indicator_id = request.args.get('indicator_id')

        query = EnvironmentData.query

        # 时间过滤
        time_threshold = datetime.utcnow() - timedelta(days=days)
        query = query.filter(EnvironmentData.collection_time >= time_threshold)

        # 区域过滤
        if region_id:
            query = query.filter_by(region_id=region_id)

        # 指标过滤
        if indicator_id:
            query = query.filter_by(indicator_id=indicator_id)

        # 排序和限制
        data = query.order_by(EnvironmentData.collection_time.desc()).limit(200).all()

        result = []
        for d in data:
            result.append(d.to_dict())

        return jsonify({'success': True, 'data': result, 'query_days': days})

    except Exception as e:
        logger.error(f"API错误 - 获取最近数据: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 新增的 API 接口 ============

@app.route('/api/indicators', methods=['GET'])
def get_all_indicators():
    """获取所有监测指标"""
    try:
        indicators = MonitorIndicator.query.order_by(MonitorIndicator.indicator_id).all()
        result = [indicator.to_dict() for indicator in indicators]
        return jsonify({'success': True, 'indicators': result})
    except Exception as e:
        logger.error(f"获取监测指标失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/indicators/<indicator_id>', methods=['GET'])
def get_indicator_by_id(indicator_id):
    """根据ID获取监测指标"""
    try:
        indicator = MonitorIndicator.query.get(indicator_id)
        if not indicator:
            return jsonify({'success': False, 'error': '监测指标不存在'}), 404
        return jsonify({'success': True, 'indicator': indicator.to_dict()})
    except Exception as e:
        logger.error(f"获取监测指标失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/indicators/add', methods=['POST'])
def add_indicator():
    """新增监测指标"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        # 检查必要字段
        required_fields = ['indicator_id', 'indicator_name', 'standard_upper', 'standard_lower']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400

        # 检查指标ID是否已存在
        if MonitorIndicator.query.get(data['indicator_id']):
            return jsonify({'success': False, 'error': '指标编号已存在'}), 400

        # 创建新指标
        indicator = MonitorIndicator(
            indicator_id=data['indicator_id'],
            indicator_name=data['indicator_name'],
            unit=data.get('unit', ''),
            standard_upper=data['standard_upper'],
            standard_lower=data['standard_lower'],
            monitor_freq=data.get('monitor_freq', '日')
        )

        db.session.add(indicator)
        db.session.commit()

        logger.info(f"新增监测指标成功: {data['indicator_id']}")
        return jsonify({'success': True, 'indicator': indicator.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"新增监测指标失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/indicators/<indicator_id>/update', methods=['PUT'])
def update_indicator(indicator_id):
    """更新监测指标"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        indicator = MonitorIndicator.query.get(indicator_id)
        if not indicator:
            return jsonify({'success': False, 'error': '监测指标不存在'}), 404

        # 更新字段
        if 'indicator_name' in data:
            indicator.indicator_name = data['indicator_name']
        if 'unit' in data:
            indicator.unit = data['unit']
        if 'standard_upper' in data:
            indicator.standard_upper = data['standard_upper']
        if 'standard_lower' in data:
            indicator.standard_lower = data['standard_lower']
        if 'monitor_freq' in data:
            indicator.monitor_freq = data['monitor_freq']

        db.session.commit()

        logger.info(f"更新监测指标成功: {indicator_id}")
        return jsonify({'success': True, 'indicator': indicator.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"更新监测指标失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/indicators/<indicator_id>/delete', methods=['DELETE'])
def delete_indicator(indicator_id):
    """删除监测指标"""
    try:
        indicator = MonitorIndicator.query.get(indicator_id)
        if not indicator:
            return jsonify({'success': False, 'error': '监测指标不存在'}), 404

        # 检查是否有环境数据关联该指标
        related_data = EnvironmentData.query.filter_by(indicator_id=indicator_id).first()
        if related_data:
            return jsonify({
                'success': False,
                'error': '该指标已关联环境监测数据，无法删除'
            }), 400

        db.session.delete(indicator)
        db.session.commit()

        logger.info(f"删除监测指标成功: {indicator_id}")
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        logger.error(f"删除监测指标失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/all', methods=['GET'])
def get_all_environment_data():
    """获取所有环境监测数据"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        region_id = request.args.get('region_id')
        indicator_id = request.args.get('indicator_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        query = EnvironmentData.query

        # 应用过滤条件
        if region_id:
            query = query.filter_by(region_id=region_id)
        if indicator_id:
            query = query.filter_by(indicator_id=indicator_id)
        if start_date:
            query = query.filter(EnvironmentData.collection_time >= start_date)
        if end_date:
            query = query.filter(EnvironmentData.collection_time <= end_date)

        # 分页查询
        pagination = query.order_by(EnvironmentData.collection_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        data_list = [d.to_dict() for d in pagination.items]

        return jsonify({
            'success': True,
            'data': data_list,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        })

    except Exception as e:
        logger.error(f"获取环境监测数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/<data_id>', methods=['GET'])
def get_environment_data_by_id(data_id):
    """根据ID获取环境监测数据"""
    try:
        env_data = EnvironmentData.query.get(data_id)
        if not env_data:
            return jsonify({'success': False, 'error': '环境监测数据不存在'}), 404

        return jsonify({'success': True, 'data': env_data.to_dict()})

    except Exception as e:
        logger.error(f"获取环境监测数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/add', methods=['POST'])
def add_environment_data():
    """新增环境监测数据"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        # 检查必要字段
        required_fields = ['indicator_id', 'device_id', 'monitor_value', 'region_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400

        # 检查指标是否存在
        indicator = MonitorIndicator.query.get(data['indicator_id'])
        if not indicator:
            return jsonify({'success': False, 'error': '监测指标不存在'}), 400

        # 检查设备是否存在
        device = MonitorDevice.query.get(data['device_id'])
        if not device:
            return jsonify({'success': False, 'error': '监测设备不存在'}), 400

        # 检查区域是否存在
        region = RegionInfo.query.get(data['region_id'])
        if not region:
            return jsonify({'success': False, 'error': '区域不存在'}), 400

        # ========== 修复：生成短格式ID ==========
        # 查询当前最大的数据ID
        max_id = EnvironmentData.query.with_entities(
            db.func.max(EnvironmentData.data_id)
        ).scalar()

        if max_id and max_id.startswith('ED'):
            try:
                # 提取数字部分并递增
                current_num = int(max_id[2:])
                new_num = current_num + 1
                data_id = f"ED{new_num:06d}"  # 保持6位数字
            except ValueError:
                # 如果解析失败，从1开始
                data_id = "ED000001"
        else:
            # 如果没有数据，从000001开始
            data_id = "ED000001"
        # ========== 修复结束 ==========

        # 检查阈值是否异常
        monitor_value = float(data.get('monitor_value', 0))
        is_abnormal = False
        abnormal_reason = None

        if monitor_value > float(indicator.standard_upper) or monitor_value < float(indicator.standard_lower):
            is_abnormal = True
            abnormal_reason = f"监测值 {monitor_value} {'>' if monitor_value > indicator.standard_upper else '<'} 阈值范围 [{indicator.standard_lower}, {indicator.standard_upper}]"

            # 只有设备状态正常时才记录异常预警
            if device.operation_status == '正常':
                # 检查是否需要创建新警报
                if should_create_alert(device.device_id, indicator.indicator_id, 'data_abnormal', data_id=data_id):
                    alert_key = f"data_abnormal_{device.device_id}_{indicator.indicator_id}"
                    alert_message = f"设备 {device.device_id} 监测指标 {indicator.indicator_name} 异常：{abnormal_reason}"
                    device_alerts[alert_key].append({
                        'time': datetime.now().isoformat(),
                        'message': alert_message,
                        'device_id': device.device_id,
                        'data_id': data_id,
                        'indicator_id': indicator.indicator_id,
                        'value': monitor_value,
                        'threshold': f"[{indicator.standard_lower}, {indicator.standard_upper}]",
                        'alert_type': 'data_abnormal'
                    })

        # 创建环境监测数据
        env_data = EnvironmentData(
            data_id=data_id,
            indicator_id=data['indicator_id'],
            device_id=data['device_id'],
            region_id=data['region_id'],
            collection_time=datetime.strptime(data.get('collection_time'), '%Y-%m-%d %H:%M:%S')
            if data.get('collection_time') else datetime.utcnow(),
            monitor_value=monitor_value,
            data_quality=data.get('data_quality', '中'),
            is_abnormal=is_abnormal,
            abnormal_reason=abnormal_reason
        )

        db.session.add(env_data)
        db.session.commit()

        logger.info(f"新增环境监测数据成功: {data_id}")
        return jsonify({'success': True, 'data': env_data.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"新增环境监测数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/<data_id>/update', methods=['PUT'])
def update_environment_data(data_id):
    """更新环境监测数据"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        env_data = EnvironmentData.query.get(data_id)
        if not env_data:
            return jsonify({'success': False, 'error': '环境监测数据不存在'}), 404

        # 获取相关指标信息
        indicator = MonitorIndicator.query.get(env_data.indicator_id)
        if not indicator:
            return jsonify({'success': False, 'error': '关联的监测指标不存在'}), 400

        # 更新字段
        if 'monitor_value' in data:
            monitor_value = float(data['monitor_value'])
            env_data.monitor_value = monitor_value

            # 重新检查阈值
            if monitor_value > float(indicator.standard_upper) or monitor_value < float(indicator.standard_lower):
                env_data.is_abnormal = True
                env_data.abnormal_reason = f"监测值 {monitor_value} {'>' if monitor_value > indicator.standard_upper else '<'} 阈值范围 [{indicator.standard_lower}, {indicator.standard_upper}]"

                # 检查是否需要创建新警报
                device = MonitorDevice.query.get(env_data.device_id)
                if device and device.operation_status == '正常':
                    if should_create_alert(device.device_id, indicator.indicator_id, 'data_abnormal', data_id=env_data.data_id):
                        alert_key = f"data_abnormal_{device.device_id}_{indicator.indicator_id}"
                        alert_message = f"设备 {device.device_id} 监测指标 {indicator.indicator_name} 异常：{env_data.abnormal_reason}"
                        device_alerts[alert_key].append({
                            'time': datetime.now().isoformat(),
                            'message': alert_message,
                            'device_id': device.device_id,
                            'data_id': env_data.data_id,
                            'indicator_id': indicator.indicator_id,
                            'value': monitor_value,
                            'threshold': f"[{indicator.standard_lower}, {indicator.standard_upper}]",
                            'alert_type': 'data_abnormal'
                        })
            else:
                env_data.is_abnormal = False
                env_data.abnormal_reason = None

        if 'data_quality' in data:
            env_data.data_quality = data['data_quality']

        if 'collection_time' in data:
            env_data.collection_time = datetime.strptime(data['collection_time'], '%Y-%m-%d %H:%M:%S')

        db.session.commit()

        logger.info(f"更新环境监测数据成功: {data_id}")
        return jsonify({'success': True, 'data': env_data.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"更新环境监测数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/<data_id>/delete', methods=['DELETE'])
def delete_environment_data(data_id):
    """删除环境监测数据"""
    try:
        env_data = EnvironmentData.query.get(data_id)
        if not env_data:
            return jsonify({'success': False, 'error': '环境监测数据不存在'}), 404

        db.session.delete(env_data)
        db.session.commit()

        logger.info(f"删除环境监测数据成功: {data_id}")
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        logger.error(f"删除环境监测数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/add', methods=['POST'])
def add_device():
    """新增监测设备"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        # 检查必要字段
        required_fields = ['device_id', 'device_type', 'region_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400

        # 检查设备ID是否已存在
        if MonitorDevice.query.get(data['device_id']):
            return jsonify({'success': False, 'error': '设备编号已存在'}), 400

        # 检查区域是否存在
        region = RegionInfo.query.get(data['region_id'])
        if not region:
            return jsonify({'success': False, 'error': '区域不存在'}), 400

        # 创建新设备
        device = MonitorDevice(
            device_id=data['device_id'],
            device_type=data['device_type'],
            region_id=data['region_id'],
            install_time=datetime.strptime(data.get('install_time'), '%Y-%m-%d').date()
            if data.get('install_time') else datetime.utcnow().date(),
            calibration_cycle=data.get('calibration_cycle'),
            operation_status=data.get('operation_status', '正常'),
            comm_proto=data.get('comm_proto', 'HTTP')
        )

        db.session.add(device)
        db.session.commit()

        logger.info(f"新增监测设备成功: {data['device_id']}")
        return jsonify({'success': True, 'device': device.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"新增监测设备失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/<device_id>/update', methods=['PUT'])
def update_device(device_id):
    """更新监测设备信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400

        device = MonitorDevice.query.get(device_id)
        if not device:
            return jsonify({'success': False, 'error': '监测设备不存在'}), 404

        # 更新字段
        if 'device_type' in data:
            device.device_type = data['device_type']
        if 'region_id' in data:
            # 检查区域是否存在
            region = RegionInfo.query.get(data['region_id'])
            if not region:
                return jsonify({'success': False, 'error': '区域不存在'}), 400
            device.region_id = data['region_id']
        if 'install_time' in data:
            device.install_time = datetime.strptime(data['install_time'], '%Y-%m-%d').date()
        if 'calibration_cycle' in data:
            device.calibration_cycle = data['calibration_cycle']
        if 'operation_status' in data:
            device.operation_status = data['operation_status']
        if 'comm_proto' in data:
            device.comm_proto = data['comm_proto']

        device.status_update_time = datetime.utcnow()
        db.session.commit()

        logger.info(f"更新监测设备成功: {device_id}")
        return jsonify({'success': True, 'device': device.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"更新监测设备失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/<device_id>/delete', methods=['DELETE'])
def delete_device(device_id):
    """删除监测设备"""
    try:
        device = MonitorDevice.query.get(device_id)
        if not device:
            return jsonify({'success': False, 'error': '监测设备不存在'}), 404

        # 检查是否有环境数据关联该设备
        related_data = EnvironmentData.query.filter_by(device_id=device_id).first()
        if related_data:
            return jsonify({
                'success': False,
                'error': '该设备已关联环境监测数据，无法删除'
            }), 400

        db.session.delete(device)
        db.session.commit()

        logger.info(f"删除监测设备成功: {device_id}")
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        logger.error(f"删除监测设备失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/types', methods=['GET'])
def get_device_types():
    """获取所有设备类型"""
    try:
        # 从现有设备中获取唯一的设备类型
        device_types = db.session.query(MonitorDevice.device_type).distinct().all()
        types = [dt[0] for dt in device_types if dt[0]]

        # 如果没有设备，返回默认的设备类型列表
        if not types:
            types = ['空气质量传感器', '水质监测仪', '土壤传感器',
                     '温湿度传感器', '噪音监测仪', '气象站',
                     '土壤多参数仪', '水质监测传感器']

        return jsonify({'success': True, 'device_types': types})

    except Exception as e:
        logger.error(f"获取设备类型失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/recalculate-abnormal-by-indicator', methods=['POST'])
def recalculate_abnormal_by_indicator():
    """根据指标ID重新计算异常数据"""
    try:
        data = request.get_json()
        if not data or 'indicator_id' not in data:
            return jsonify({'success': False, 'error': '缺少指标ID'}), 400

        indicator_id = data['indicator_id']

        # 获取指标信息
        indicator = MonitorIndicator.query.get(indicator_id)
        if not indicator:
            return jsonify({'success': False, 'error': '监测指标不存在'}), 404

        # 重新计算该指标的所有数据
        affected_count = 0
        env_data_list = EnvironmentData.query.filter_by(indicator_id=indicator_id).all()

        for env_data in env_data_list:
            # 重新检查阈值
            monitor_value = float(env_data.monitor_value) if env_data.monitor_value else 0

            old_status = env_data.is_abnormal
            old_reason = env_data.abnormal_reason

            if monitor_value > float(indicator.standard_upper) or monitor_value < float(indicator.standard_lower):
                env_data.is_abnormal = True
                env_data.abnormal_reason = f"监测值 {monitor_value} {'>' if monitor_value > indicator.standard_upper else '<'} 阈值范围 [{indicator.standard_lower}, {indicator.standard_upper}]"
                affected_count += 1
                device = MonitorDevice.query.get(env_data.device_id)
                if device and device.operation_status == '正常':
                    if should_create_alert(device.device_id, indicator.indicator_id, 'data_abnormal', data_id=env_data.data_id):
                        alert_key = f"data_abnormal_{device.device_id}_{indicator.indicator_id}"
                        alert_message = f"设备 {device.device_id} 监测指标 {indicator.indicator_name} 异常：{env_data.abnormal_reason}"
                        device_alerts[alert_key].append({
                            'time': datetime.now().isoformat(),
                            'message': alert_message,
                            'device_id': device.device_id,
                            'data_id': env_data.data_id,
                            'indicator_id': indicator.indicator_id,
                            'value': monitor_value,
                            'threshold': f"[{indicator.standard_lower}, {indicator.standard_upper}]",
                            'alert_type': 'data_abnormal'
                        })
            else:
                env_data.is_abnormal = False
                env_data.abnormal_reason = None
                if old_status:
                    affected_count += 1

            # 记录变更（可选）
            if old_status != env_data.is_abnormal:
                logger.info(f"数据 {env_data.data_id} 异常状态变更: {old_status} -> {env_data.is_abnormal}")

        db.session.commit()

        logger.info(f"重新计算异常数据完成，指标: {indicator_id}, 影响数据: {affected_count} 条")
        return jsonify({
            'success': True,
            'message': f'重新计算完成',
            'affected': affected_count,
            'indicator_id': indicator_id
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"重新计算异常数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/recalculate-abnormal', methods=['POST'])
def recalculate_all_abnormal():
    """重新计算所有数据的异常状态"""
    try:
        # 获取所有指标
        indicators = MonitorIndicator.query.all()
        indicator_map = {ind.indicator_id: ind for ind in indicators}

        # 获取所有环境数据
        env_data_list = EnvironmentData.query.all()

        affected_count = 0

        for env_data in env_data_list:
            indicator = indicator_map.get(env_data.indicator_id)
            if not indicator:
                continue

            monitor_value = float(env_data.monitor_value) if env_data.monitor_value else 0

            old_status = env_data.is_abnormal

            # 重新检查阈值
            if monitor_value > float(indicator.standard_upper) or monitor_value < float(indicator.standard_lower):
                env_data.is_abnormal = True
                env_data.abnormal_reason = f"监测值 {monitor_value} {'>' if monitor_value > indicator.standard_upper else '<'} 阈值范围 [{indicator.standard_lower}, {indicator.standard_upper}]"
                affected_count += 1
                device = MonitorDevice.query.get(env_data.device_id)
                if device and device.operation_status == '正常':
                    if should_create_alert(device.device_id, indicator.indicator_id, 'data_abnormal', data_id=env_data.data_id):
                        alert_key = f"data_abnormal_{device.device_id}_{indicator.indicator_id}"
                        alert_message = f"设备 {device.device_id} 监测指标 {indicator.indicator_name} 异常：{env_data.abnormal_reason}"
                        device_alerts[alert_key].append({
                            'time': datetime.now().isoformat(),
                            'message': alert_message,
                            'device_id': device.device_id,
                            'data_id': env_data.data_id,
                            'indicator_id': indicator.indicator_id,
                            'value': monitor_value,
                            'threshold': f"[{indicator.standard_lower}, {indicator.standard_upper}]",
                            'alert_type': 'data_abnormal'
                        })
            else:
                env_data.is_abnormal = False
                env_data.abnormal_reason = None
                if old_status:
                    affected_count += 1

        db.session.commit()

        logger.info(f"重新计算所有异常数据完成，影响数据: {affected_count} 条")
        return jsonify({
            'success': True,
            'message': f'重新计算所有异常数据完成',
            'affected': affected_count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"重新计算所有异常数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/batch-upload', methods=['POST'])
def batch_upload_environment_data():
    """批量上传环境监测数据"""
    try:
        data_list = request.get_json()
        if not isinstance(data_list, list) or len(data_list) == 0:
            return jsonify({'success': False, 'error': '请求数据应为非空数组'}), 400

        results = []
        errors = []

        # ========== 修复：先获取起始ID ==========
        max_id = EnvironmentData.query.with_entities(
            db.func.max(EnvironmentData.data_id)
        ).scalar()

        if max_id and max_id.startswith('ED'):
            try:
                start_num = int(max_id[2:]) + 1
            except ValueError:
                start_num = 1
        else:
            start_num = 1
        # ========== 修复结束 ==========

        for i, data in enumerate(data_list):
            try:
                # 检查必要字段
                required_fields = ['indicator_id', 'device_id', 'monitor_value', 'region_id']
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    errors.append(f"第{i + 1}条数据缺少字段: {', '.join(missing_fields)}")
                    continue

                # 检查指标是否存在
                indicator = MonitorIndicator.query.get(data['indicator_id'])
                if not indicator:
                    errors.append(f"第{i + 1}条数据的监测指标不存在: {data['indicator_id']}")
                    continue

                # 检查设备是否存在
                device = MonitorDevice.query.get(data['device_id'])
                if not device:
                    errors.append(f"第{i + 1}条数据的监测设备不存在: {data['device_id']}")
                    continue

                # 检查区域是否存在
                region = RegionInfo.query.get(data['region_id'])
                if not region:
                    errors.append(f"第{i + 1}条数据的区域不存在: {data['region_id']}")
                    continue

                # ========== 修复：生成短格式ID ==========
                data_id = f"ED{start_num + i:06d}"
                # ========== 修复结束 ==========

                # 检查阈值是否异常
                monitor_value = float(data.get('monitor_value', 0))
                is_abnormal = False
                abnormal_reason = None

                if monitor_value > float(indicator.standard_upper) or monitor_value < float(indicator.standard_lower):
                    is_abnormal = True
                    abnormal_reason = f"监测值 {monitor_value} {'>' if monitor_value > indicator.standard_upper else '<'} 阈值范围 [{indicator.standard_lower}, {indicator.standard_upper}]"

                # 创建环境监测数据
                env_data = EnvironmentData(
                    data_id=data_id,
                    indicator_id=data['indicator_id'],
                    device_id=data['device_id'],
                    region_id=data['region_id'],
                    collection_time=datetime.strptime(data.get('collection_time'), '%Y-%m-%d %H:%M:%S')
                    if data.get('collection_time') else datetime.utcnow(),
                    monitor_value=monitor_value,
                    data_quality=data.get('data_quality', '中'),
                    is_abnormal=is_abnormal,
                    abnormal_reason=abnormal_reason
                )

                db.session.add(env_data)
                results.append(data_id)

            except Exception as e:
                errors.append(f"第{i + 1}条数据处理失败: {str(e)}")

        if errors:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'部分数据处理失败，已回滚所有操作',
                'errors': errors
            }), 400
        else:
            db.session.commit()
            logger.info(f"批量上传环境监测数据成功，共{len(results)}条")
            return jsonify({
                'success': True,
                'message': f'成功上传{len(results)}条数据',
                'data_ids': results
            })

    except Exception as e:
        db.session.rollback()
        logger.error(f"批量上传环境监测数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 新增的数据统计API ============
@app.route('/api/environment/data/count', methods=['GET'])
def get_data_count():
    """获取环境监测数据总数"""
    try:
        count = EnvironmentData.query.count()
        return jsonify({
            'success': True,
            'count': count
        })
    except Exception as e:
        logger.error(f"获取数据总数失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/abnormal-count', methods=['GET'])
def get_abnormal_data_count():
    """获取异常数据总数"""
    try:
        count = EnvironmentData.query.filter_by(is_abnormal=True).count()
        return jsonify({
            'success': True,
            'count': count
        })
    except Exception as e:
        logger.error(f"获取异常数据总数失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 新增的提醒相关API ============
@app.route('/api/alerts/device', methods=['GET'])
def get_device_alerts():
    """获取设备相关警报"""
    try:
        device_id = request.args.get('device_id')
        alert_type = request.args.get('alert_type')

        recent_alerts = []
        for key, alerts in device_alerts.items():
            # 如果指定了设备ID，只返回该设备的警报
            if device_id and device_id not in key:
                continue

            # 如果指定了警报类型，只返回该类型的警报
            if alert_type and not key.startswith(alert_type):
                continue

            for alert in alerts[-5:]:  # 每个设备最多返回最近5条
                alert_time = datetime.fromisoformat(alert['time'])

                # 基本过滤条件
                is_recent = datetime.now() - alert_time < timedelta(hours=24)
                is_not_handled = not alert.get('handled', False)

                # 额外的过滤条件：如果设备处于故障状态，不显示数据异常警报
                device_id_from_alert = alert.get('device_id')
                if device_id_from_alert and alert.get('alert_type') == 'data_abnormal':
                    device = MonitorDevice.query.get(device_id_from_alert)
                    if device and device.operation_status != '正常':
                        continue  # 跳过故障设备的数据异常警报

                if is_recent and is_not_handled:
                    # 为数据异常警报添加更多信息
                    if alert.get('alert_type') == 'data_abnormal':
                        # 获取阈值信息
                        indicator = MonitorIndicator.query.get(alert.get('indicator_id'))
                        if indicator:
                            alert['threshold_upper'] = float(indicator.standard_upper)
                            alert['threshold_lower'] = float(indicator.standard_lower)
                            alert['unit'] = indicator.unit
                            alert['indicator_name'] = indicator.indicator_name

                    recent_alerts.append(alert)

        # 按时间倒序排序
        recent_alerts.sort(key=lambda x: x['time'], reverse=True)

        return jsonify({
            'success': True,
            'alerts': recent_alerts[:50],  # 最多返回50条
            'count': len(recent_alerts)
        })
    except Exception as e:
        logger.error(f"获取设备提醒失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/alerts/clear', methods=['POST'])
def clear_alerts():
    """清除提醒并将相关设备状态设置为正常"""
    try:
        data = request.get_json()
        alert_key = data.get('alert_key')

        if alert_key:
            # 提取设备ID（如果alert_key格式为 device_fault_D001）
            if alert_key.startswith('device_fault_'):
                device_id = alert_key.replace('device_fault_', '')
                # 将设备状态设置为正常
                device = MonitorDevice.query.get(device_id)
                if device:
                    device.operation_status = '正常'
                    device.status_update_time = datetime.utcnow()
                    db.session.commit()
                    logger.info(f"清除警报并设置设备 {device_id} 状态为正常")

            if alert_key in device_alerts:
                # 标记所有相关警报为已处理
                for alert in device_alerts[alert_key]:
                    alert['handled'] = True
                return jsonify({'success': True, 'message': '提醒已清除，设备状态已更新为正常'})
            else:
                return jsonify({'success': False, 'error': '提醒不存在'}), 404
        else:
            # 清除所有提醒但不改变设备状态
            device_alerts.clear()
            return jsonify({'success': True, 'message': '所有提醒已清除'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"清除提醒失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 新增：根据警报获取关联数据API ============
@app.route('/api/environment/data/by-alert', methods=['GET'])
def get_environment_data_by_alert():
    """根据警报信息获取关联的环境数据"""
    try:
        device_id = request.args.get('device_id')
        indicator_id = request.args.get('indicator_id')
        start_time = request.args.get('start_time')  # 警报时间

        if not device_id or not indicator_id:
            return jsonify({'success': False, 'error': '需要设备ID和指标ID'}), 400

        # 获取指标信息（用于阈值）
        indicator = MonitorIndicator.query.get(indicator_id)
        if not indicator:
            return jsonify({'success': False, 'error': '监测指标不存在'}), 404

        threshold_info = {
            'standard_lower': float(indicator.standard_lower),
            'standard_upper': float(indicator.standard_upper),
            'unit': indicator.unit,
            'indicator_name': indicator.indicator_name
        }

        query = EnvironmentData.query.filter_by(
            device_id=device_id,
            indicator_id=indicator_id,
            is_abnormal=True
        )

        if start_time:
            # 查找警报时间附近的异常数据
            try:
                alert_time = datetime.fromisoformat(start_time)
                time_from = alert_time - timedelta(hours=1)  # 扩展时间范围到1小时
                time_to = alert_time + timedelta(hours=1)
                query = query.filter(
                    EnvironmentData.collection_time >= time_from,
                    EnvironmentData.collection_time <= time_to
                )
            except ValueError:
                logger.warning(f"无效的时间格式: {start_time}")

        # 获取最近的异常数据
        data_list = query.order_by(EnvironmentData.collection_time.desc()).limit(10).all()

        result = []
        for data in data_list:
            data_dict = data.to_dict()
            # 添加指标阈值信息
            data_dict['threshold_info'] = threshold_info
            result.append(data_dict)

        # 如果没有找到关联数据，返回阈值信息和空数据
        if not result:
            return jsonify({
                'success': True,
                'data': [],
                'threshold_info': threshold_info
            })

        return jsonify({'success': True, 'data': result})

    except Exception as e:
        logger.error(f"获取警报关联数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/environment/data/<data_id>/adjust', methods=['PUT'])
def adjust_environment_data(data_id):
    """调整监测值并重新检查异常状态"""
    try:
        data = request.get_json()
        if not data or 'monitor_value' not in data:
            return jsonify({'success': False, 'error': '缺少监测值'}), 400

        env_data = EnvironmentData.query.get(data_id)
        if not env_data:
            return jsonify({'success': False, 'error': '环境监测数据不存在'}), 404

        # 获取相关指标信息
        indicator = MonitorIndicator.query.get(env_data.indicator_id)
        if not indicator:
            return jsonify({'success': False, 'error': '关联的监测指标不存在'}), 400

        old_value = env_data.monitor_value
        new_value = float(data['monitor_value'])

        # 检查新值是否在阈值范围内
        threshold_lower = float(indicator.standard_lower)
        threshold_upper = float(indicator.standard_upper)

        # 更新监测值
        env_data.monitor_value = new_value

        # 重要：重新检查阈值是否异常
        old_abnormal = env_data.is_abnormal

        # 如果新值在阈值范围内，则设置为正常；否则为异常
        if threshold_lower <= new_value <= threshold_upper:
            env_data.is_abnormal = False
            env_data.abnormal_reason = None
        else:
            env_data.is_abnormal = True
            env_data.abnormal_reason = f"监测值 {new_value} {'>' if new_value > threshold_upper else '<'} 阈值范围 [{threshold_lower}, {threshold_upper}]"

        # 如果数据从不正常变为正常，清除相关警报
        if old_abnormal and not env_data.is_abnormal:
            alert_key = f"data_abnormal_{env_data.device_id}_{indicator.indicator_id}"
            if alert_key in device_alerts:
                for alert in device_alerts[alert_key]:
                    alert['handled'] = True

        # 更新数据质量（可选，如果修改了值，可以设为"中"）
        env_data.data_quality = data.get('data_quality', env_data.data_quality)

        # 更新时间戳
        env_data.collection_time = env_data.collection_time  # 保持原时间，或可以更新

        db.session.commit()

        logger.info(
            f"调整监测值成功: {data_id}, 旧值: {old_value}, 新值: {new_value}, 异常状态: {old_abnormal} -> {env_data.is_abnormal}")

        # 重新获取数据以确保返回最新的
        db.session.refresh(env_data)

        return jsonify({
            'success': True,
            'data': env_data.to_dict(),
            'old_value': float(old_value) if old_value else None,
            'new_value': new_value,
            'is_abnormal': env_data.is_abnormal,
            'threshold_lower': threshold_lower,
            'threshold_upper': threshold_upper,
            'unit': indicator.unit
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"调整监测值失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ 新增：更新监测值API（用于警报处理） ============
@app.route('/api/environment/data/<data_id>/update-value', methods=['PUT'])
def update_environment_data_value(data_id):
    """更新环境监测数据值（用于警报处理）"""
    try:
        data = request.get_json()
        if not data or 'monitor_value' not in data:
            return jsonify({'success': False, 'error': '缺少监测值'}), 400

        env_data = EnvironmentData.query.get(data_id)
        if not env_data:
            return jsonify({'success': False, 'error': '环境监测数据不存在'}), 404

        # 获取相关指标信息
        indicator = MonitorIndicator.query.get(env_data.indicator_id)
        if not indicator:
            return jsonify({'success': False, 'error': '关联的监测指标不存在'}), 400

        # 更新监测值
        old_value = env_data.monitor_value
        new_value = float(data['monitor_value'])
        env_data.monitor_value = new_value

        # 重新检查阈值是否异常
        old_abnormal = env_data.is_abnormal
        if new_value > float(indicator.standard_upper) or new_value < float(indicator.standard_lower):
            env_data.is_abnormal = True
            env_data.abnormal_reason = f"监测值 {new_value} {'>' if new_value > indicator.standard_upper else '<'} 阈值范围 [{indicator.standard_lower}, {indicator.standard_upper}]"
        else:
            env_data.is_abnormal = False
            env_data.abnormal_reason = None

            # 如果数据从不正常变为正常，清除相关警报
            if old_abnormal:
                alert_key = f"data_abnormal_{env_data.device_id}_{indicator.indicator_id}"
                if alert_key in device_alerts:
                    for alert in device_alerts[alert_key]:
                        alert['handled'] = True

        db.session.commit()

        logger.info(
            f"更新监测值成功: {data_id}, 旧值: {old_value}, 新值: {new_value}, 异常状态: {old_abnormal} -> {env_data.is_abnormal}")

        return jsonify({
            'success': True,
            'data': env_data.to_dict(),
            'old_value': float(old_value) if old_value else None,
            'new_value': new_value,
            'is_abnormal': env_data.is_abnormal
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"更新监测值失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 初始化数据库 ============
def init_database():
    """初始化数据库"""
    with app.app_context():
        try:
            # 只创建本业务线的表
            db.create_all()
            logger.info("数据库表创建成功")

            # 插入本业务线的测试数据
            insert_test_data()

            # 启动设备状态自动更新线程
            update_thread = threading.Thread(target=device_status_auto_update, daemon=True)
            update_thread.start()
            logger.info("设备状态自动更新线程已启动")

        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")


def insert_test_data():
    """插入测试数据"""
    try:
        # 检查是否已有数据
        if MonitorIndicator.query.count() > 0:
            logger.info("数据库已有数据，跳过测试数据插入")
            return

        # 插入监测指标
        indicators = [
            MonitorIndicator(
                indicator_id='I001',
                indicator_name='空气质量PM2.5',
                unit='μg/m³',
                standard_upper=35.0,
                standard_lower=0.0,
                monitor_freq='小时'
            ),
            MonitorIndicator(
                indicator_id='I002',
                indicator_name='水质PH值',
                unit='pH',
                standard_upper=8.5,
                standard_lower=6.5,
                monitor_freq='日'
            ),
            MonitorIndicator(
                indicator_id='I003',
                indicator_name='土壤湿度',
                unit='%',
                standard_upper=80.0,
                standard_lower=20.0,
                monitor_freq='日'
            ),
            MonitorIndicator(
                indicator_id='I004',
                indicator_name='温度',
                unit='°C',
                standard_upper=35.0,
                standard_lower=-10.0,
                monitor_freq='小时'
            ),
            MonitorIndicator(
                indicator_id='I005',
                indicator_name='噪音',
                unit='dB',
                standard_upper=60.0,
                standard_lower=20.0,
                monitor_freq='小时'
            )
        ]

        db.session.add_all(indicators)

        # 检查region_info表中是否有数据
        regions = RegionInfo.query.all()
        if not regions:
            logger.warning("region_info表中没有区域数据，将跳过设备插入")
            db.session.commit()
            return

        # 插入监测设备（确保有20个设备）
        device_types = ['空气质量传感器', '水质监测仪', '土壤传感器', '温湿度传感器', '噪音监测仪']

        # 清空现有设备数据
        MonitorDevice.query.delete()
        db.session.commit()

        devices = []
        for i in range(1, 21):  # 确保生成20个设备
            region = regions[(i - 1) % len(regions)]  # 循环使用区域
            # 随机生成校准周期，部分设备不设置校准周期
            calibration_options = ['30天', '60天', '90天', None, None]
            calibration_cycle = random.choice(calibration_options)

            device = MonitorDevice(
                device_id=f'D{i:03d}',
                device_type=device_types[(i - 1) % len(device_types)],
                region_id=region.region_id,
                install_time=datetime.now().date() - timedelta(days=random.randint(0, 365)),
                calibration_cycle=calibration_cycle,
                operation_status=random.choice(['正常', '正常', '正常', '故障', '离线']),
                comm_proto=random.choice(['MQTT', 'HTTP', 'LoRa', 'NB-IoT'])
            )
            devices.append(device)
            db.session.add(device)

        db.session.commit()
        logger.info(f"成功插入 {len(devices)} 个设备")

        # 插入环境监测数据
        base_time = datetime.utcnow() - timedelta(days=30)

        for i in range(1, 201):  # 生成200条测试数据
            device = devices[(i - 1) % len(devices)]
            indicator = indicators[(i - 1) % len(indicators)]

            # 根据指标类型生成合理的监测值
            if indicator.indicator_name == '空气质量PM2.5':
                base_value = random.uniform(0, 50)
            elif indicator.indicator_name == '水质PH值':
                base_value = random.uniform(6.0, 9.0)
            elif indicator.indicator_name == '土壤湿度':
                base_value = random.uniform(10, 90)
            elif indicator.indicator_name == '温度':
                base_value = random.uniform(-5, 40)
            else:
                base_value = random.uniform(0, 100)

            # 20%的数据超出阈值
            if random.random() < 0.2:
                if random.choice([True, False]):
                    monitor_value = float(indicator.standard_upper) + random.uniform(1, 20)
                else:
                    monitor_value = float(indicator.standard_lower) - random.uniform(1, 20)
            else:
                monitor_value = base_value

            env_data = EnvironmentData(
                data_id=f'ED{i:06d}',
                indicator_id=indicator.indicator_id,
                device_id=device.device_id,
                region_id=device.region_id,
                collection_time=base_time + timedelta(hours=i),
                monitor_value=float(monitor_value),
                data_quality=random.choice(['优', '良', '中', '差'])
            )
            db.session.add(env_data)

        db.session.commit()

        logger.info(f"测试数据插入成功，生成{len(devices)}个设备，200条环境数据")

    except Exception as e:
        db.session.rollback()
        logger.error(f"插入测试数据失败: {str(e)}")


# 检查端口是否被占用
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


if __name__ == '__main__':
    if is_port_in_use(5001):
        print("⚠️  端口 5001 已被占用")
    else:
        print("✅ 端口 5001 可用")

    init_database()
    app.run(host='0.0.0.0', port=5001, debug=True)
