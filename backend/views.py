from database import db, logger
from datetime import datetime, timedelta
import json
from typing import List, Dict, Any


class DataViews:
    """数据视图查询类"""

    # @staticmethod
    # def get_customer_service_view(search_term: str = None, page: int = 1, page_size: int = 20):
    #     """客服人员视图：游客基本信息查询"""
    #     offset = (page - 1) * page_size
    #
    #     query = """
    #             SELECT *
    #             FROM vw_tourist_info_for_customer_service
    #             """
    #
    #     params = []
    #     if search_term:
    #         query += " WHERE name LIKE %s OR id_card LIKE %s OR tourist_id LIKE %s"
    #         params = [f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"]
    #
    #     query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    #     params.extend([page_size, offset])
    #
    #     return db.execute_query(query, params)

    @staticmethod
    def get_security_realtime_view(show_warnings_only=False):
        """获取实时安全监控视图"""
        try:
            query = """
                    SELECT t.trajectory_id, \
                           t.tourist_id, \
                           tr.name, \
                           tr.phone, \
                           t.latitude, \
                           t.longitude, \
                           t.area_id, \
                           t.off_route, \
                           fc.status                                     as area_status, \
                           t.location_time, \
                           TIMESTAMPDIFF(MINUTE, t.location_time, NOW()) as minutes_ago
                    FROM trajectories t
                             LEFT JOIN tourists tr ON t.tourist_id = tr.tourist_id
                             LEFT JOIN flow_control fc ON t.area_id = fc.area_id
                    WHERE t.location_time >= DATE_SUB(NOW(), INTERVAL 30 MINUTE)
                    ORDER BY t.location_time DESC
                    LIMIT 100 \
                    """

            result = db.execute_query(query)
            logger.info(f"安全监控视图查询结果: {len(result)} 条记录")
            return result
        except Exception as e:
            logger.error(f"获取安全监控视图失败: {str(e)}")
            return []

    @staticmethod
    def get_customer_service_view(search_term=None, page=1, page_size=20):
        """获取客户服务视图"""
        try:
            offset = (page - 1) * page_size

            query = """
                    SELECT tourist_id, \
                           name, \
                           id_card, \
                           phone, \
                           entry_method, \
                           entry_time, \
                           exit_time, \
                           created_at
                    FROM tourists \
                    """
            params = []

            if search_term:
                query += " WHERE name LIKE %s OR id_card LIKE %s OR tourist_id LIKE %s"
                params = [f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"]

            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])

            result = db.execute_query(query, params)
            logger.info(f"客户服务视图查询结果: {len(result)} 条记录")
            return result
        except Exception as e:
            logger.error(f"获取客户服务视图失败: {str(e)}")
            return []
    @staticmethod
    def get_management_dashboard_view(start_date: str = None, end_date: str = None):
        """管理人员视图：综合统计报表"""
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # 使用修正后的视图
        query = """
                SELECT *
                FROM vw_management_dashboard
                WHERE visit_date BETWEEN %s AND %s
                ORDER BY visit_date DESC
                """

        return db.execute_query(query, (start_date, end_date))

    @staticmethod
    def get_ticket_analysis_view(start_date: str = None, end_date: str = None):
        """票务人员视图：预约与入园统计"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        query = """
                SELECT * 
                FROM vw_ticket_sales_analysis
                WHERE reservation_date BETWEEN %s AND %s
                ORDER BY reservation_date DESC 
                """

        return db.execute_query(query, (start_date, end_date))

    @staticmethod
    def get_flow_monitoring_view():
        """监控人员视图：区域流量监控"""
        query = """
                SELECT * 
                FROM vw_area_flow_monitoring
                ORDER BY capacity_percentage DESC 
                """

        return db.execute_query(query)

    @staticmethod
    def get_behavior_analysis_view(tourist_id: str = None):
        """数据分析视图：游客行为分析"""
        query = """
                SELECT * 
                FROM vw_tourist_behavior_analysis 
                """

        if tourist_id:
            query += " WHERE tourist_id = %s"
            return db.execute_query(query, (tourist_id,))

        query += " ORDER BY total_duration_minutes DESC LIMIT 100"
        return db.execute_query(query)

    @staticmethod
    def get_real_time_alerts(limit: int = 20):
        """实时预警视图"""
        query = """
                SELECT sl.log_id, 
                       sl.log_type, 
                       sl.module, 
                       sl.message, 
                       sl.user_id, 
                       t.name as tourist_name, 
                       sl.created_at, 
                       TIMESTAMPDIFF(MINUTE, sl.created_at, NOW()) as minutes_ago
                FROM system_logs sl
                LEFT JOIN tourists t ON sl.user_id = t.tourist_id
                WHERE sl.log_type IN ('warning', 'error', 'security')
                ORDER BY sl.created_at DESC
                LIMIT %s 
                """

        return db.execute_query(query, (limit,))

    @staticmethod
    def get_tourist_history(tourist_id: str):
        """游客历史轨迹视图"""
        query = """
                SELECT t.tourist_id, 
                       t.name, 
                       t.entry_method, 
                       t.entry_time, 
                       t.exit_time, 
                       COUNT(DISTINCT tr.area_id) as areas_visited, 
                       COUNT(DISTINCT tr.trajectory_id) as location_points, 
                       MIN(tr.location_time) as first_location, 
                       MAX(tr.location_time) as last_location, 
                       COUNT(CASE WHEN tr.off_route = TRUE THEN 1 END) as off_route_count, 
                       GROUP_CONCAT(DISTINCT tr.area_id ORDER BY tr.location_time) as visit_sequence, 
                       r.group_size, 
                       r.ticket_amount, 
                       r.payment_status
                FROM tourists t
                LEFT JOIN trajectories tr ON t.tourist_id = tr.tourist_id
                LEFT JOIN reservations r ON t.tourist_id = r.tourist_id
                WHERE t.tourist_id = %s
                GROUP BY t.tourist_id, t.name, t.entry_method, t.entry_time,
                         t.exit_time, r.group_size, r.ticket_amount, r.payment_status 
                """

        return db.execute_query(query, (tourist_id,))

    @staticmethod
    def get_daily_summary():
        """每日摘要视图"""
        today = datetime.now().strftime('%Y-%m-%d')

        # 获取今日数据
        query = """
                SELECT COUNT(DISTINCT t.tourist_id) as total_visitors_today, 
                       SUM(CASE WHEN t.entry_method = 'online' THEN 1 ELSE 0 END) as online_today, 
                       SUM(CASE WHEN t.entry_method = 'onsite' THEN 1 ELSE 0 END) as onsite_today, 
                       COUNT(DISTINCT CASE WHEN t.exit_time IS NULL THEN t.tourist_id END) as in_park_now, 
                       COUNT(DISTINCT r.reservation_id) as reservations_today, 
                       SUM(r.ticket_amount) as revenue_today, 
                       COUNT(DISTINCT CASE WHEN tr.off_route = TRUE THEN t.tourist_id END) as off_route_today, 
                       COUNT(DISTINCT CASE WHEN fc.status IN ('warning', 'restricted') THEN fc.area_id END) as warning_areas
                FROM tourists t
                LEFT JOIN reservations r ON t.tourist_id = r.tourist_id
                    AND DATE(r.reservation_date) = %s
                LEFT JOIN trajectories tr ON t.tourist_id = tr.tourist_id
                    AND DATE(tr.location_time) = %s
                    AND tr.off_route = TRUE
                LEFT JOIN flow_control fc ON fc.status IN ('warning', 'restricted')
                WHERE DATE(t.entry_time) = %s 
                """

        result = db.execute_query(query, (today, today, today), fetch_one=True)

        # 获取系统状态
        status_query = """
                SELECT (SELECT COUNT(*) FROM tourists) as total_tourists, 
                       (SELECT COUNT(*) FROM reservations) as total_reservations, 
                       (SELECT COUNT(*) FROM trajectories WHERE DATE(created_at) = %s) as trajectories_today, 
                       (SELECT COUNT(*) FROM system_logs WHERE DATE(created_at) = %s AND log_type = 'warning') as warnings_today 
                """

        status = db.execute_query(status_query, (today, today), fetch_one=True)

        return {**result, **status} if result and status else {}