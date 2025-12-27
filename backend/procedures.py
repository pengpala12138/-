from database import db
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DatabaseProcedures:
    """存储过程调用类"""

    @staticmethod
    def update_flow_status():
        """更新流量控制状态（核心方法）"""
        try:
            # 查询所有区域并更新状态
            query = """
                    SELECT area_id, daily_capacity, current_visitors, warning_threshold
                    FROM flow_control \
                    """
            areas = db.execute_query(query)

            for area in areas:
                area_id = area['area_id']
                capacity = area['daily_capacity']
                current = area['current_visitors']
                warning_threshold = area['warning_threshold'] or 0.8

                # 计算占用率
                occupancy_rate = current / capacity if capacity > 0 else 0
                new_status = 'normal'

                # 更新状态规则
                if occupancy_rate >= 1.0:
                    new_status = 'restricted'  # 超限
                elif occupancy_rate >= warning_threshold:
                    new_status = 'warning'  # 预警
                else:
                    new_status = 'normal'  # 正常

                # 更新数据库
                update_query = """
                               UPDATE flow_control
                               SET status       = %s, \
                                   last_updated = %s
                               WHERE area_id = %s \
                               """
                db.execute_update(update_query, (new_status, datetime.now(), area_id))

                logger.info(f"区域 {area_id} 状态更新为: {new_status} (占用率: {occupancy_rate:.2f})")

            return {
                'updated_areas': len(areas),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"更新流量状态失败: {str(e)}")
            raise  # 抛出异常让API层捕获

    @staticmethod
    def generate_daily_report(report_date: str = None):
        """生成每日统计报告"""
        if not report_date:
            report_date = datetime.now().strftime('%Y-%m-%d')

        try:
            result = db.call_procedure('sp_generate_daily_report', [report_date])
            logger.info(f"每日报告生成完成: {report_date}")
            return result
        except Exception as e:
            logger.error(f"生成报告失败: {str(e)}")
            return None

    @staticmethod
    def process_expired_reservations():
        """处理过期预约"""
        try:
            result = db.call_procedure('sp_process_expired_reservations')
            processed = result[0]['processed_count'] if result else 0
            logger.info(f"处理过期预约完成，处理数量: {processed}")
            return processed
        except Exception as e:
            logger.error(f"处理过期预约失败: {str(e)}")
            return 0

    @staticmethod
    def simulate_trajectory_data(minutes: int = 60):
        """模拟轨迹数据"""
        try:
            # 获取在园游客
            query = """
                    SELECT tourist_id, name \
                    FROM tourists
                    WHERE entry_time IS NOT NULL \
                      AND exit_time IS NULL
                    LIMIT 10 \
                    """

            tourists = db.execute_query(query)
            if not tourists:
                return 0

            # 定义区域坐标
            areas = [
                {'id': 'A001', 'name': '主入口广场', 'lat_min': 39.9, 'lat_max': 39.91, 'lng_min': 116.4,
                 'lng_max': 116.41},
                {'id': 'A002', 'name': '园林区', 'lat_min': 39.91, 'lat_max': 39.92, 'lng_min': 116.41,
                 'lng_max': 116.42},
                {'id': 'A003', 'name': '休闲区', 'lat_min': 39.89, 'lat_max': 39.9, 'lng_min': 116.39,
                 'lng_max': 116.4},
                {'id': 'A004', 'name': '观景区', 'lat_min': 39.92, 'lat_max': 39.93, 'lng_min': 116.42,
                 'lng_max': 116.43}
            ]

            import random
            from datetime import datetime

            trajectories = []
            current_time = datetime.now()

            for i in range(minutes):
                for tourist in tourists:
                    area = random.choice(areas)

                    # 随机位置（在区域内）
                    latitude = random.uniform(area['lat_min'], area['lat_max'])
                    longitude = random.uniform(area['lng_min'], area['lng_max'])

                    # 小概率超出路线
                    off_route = random.random() < 0.02

                    trajectory = {
                        'tourist_id': tourist['tourist_id'],
                        'location_time': (current_time - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S'),
                        'latitude': latitude,
                        'longitude': longitude,
                        'area_id': area['id'],
                        'off_route': off_route
                    }

                    trajectories.append(trajectory)

            # 批量插入
            inserted = db.batch_insert('trajectories', trajectories)
            logger.info(f"模拟轨迹数据完成，插入 {inserted} 条记录")

            # 更新流量状态
            DatabaseProcedures.update_flow_status()

            return inserted

        except Exception as e:
            logger.error(f"模拟轨迹数据失败: {str(e)}")
            return 0

    @staticmethod
    def backup_database(backup_type: str = 'incremental'):
        """执行数据库备份"""
        try:
            # 记录备份开始
            query = """
                    INSERT INTO backup_logs
                        (backup_type, backup_path, status, start_time, message)
                    VALUES (%s, '手动备份', 'success', %s, '手动备份开始') \
                    """

            db.execute_update(query, (backup_type, datetime.now()))

            # 这里实际应该调用外部备份脚本
            # 为了演示，我们只记录日志
            logger.info(f"手动{backup_type}备份开始")

            return True
        except Exception as e:
            logger.error(f"备份失败: {str(e)}")
            return False