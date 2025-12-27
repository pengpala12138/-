from pro.utils.db_connection import create_db_connection, execute_query, fetch_query
import uuid
from datetime import datetime


class CollectionManager:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = create_db_connection(host, user, password, database)

    def __del__(self):
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()

    def generate_collection_id(self):
        """生成唯一采集记录编号"""
        date_str = datetime.now().strftime("%Y-%m")
        return f"COLL-{date_str}-{uuid.uuid4().hex[:4].upper()}"

    def add_collection(self, collection_data):
        """新增采集记录"""
        # 验证必填字段
        required_fields = ['project_id', 'collector_id', 'collection_time', 'collection_content', 'data_source']
        for field in required_fields:
            if field not in collection_data or not collection_data[field]:
                return False, f"缺少必填字段：{field}"

        # 验证项目是否存在且已立项
        project_sql = "SELECT project_status FROM research_project WHERE project_id = %s"
        project = fetch_query(self.connection, project_sql, (collection_data['project_id'],))
        if not project:
            return False, "关联项目不存在"
        if project[0]['project_status'] in ['未立项', '已结题']:
            return False, "仅可对在研或暂停的项目添加采集记录"

        # 验证数据来源
        if collection_data['data_source'] not in ['实地采集', '系统调用']:
            return False, "数据来源必须是'实地采集'或'系统调用'"

        # 生成采集ID
        collection_id = self.generate_collection_id()

        # 插入记录
        insert_sql = """
        INSERT INTO research_data_collection (
            collection_id, project_id, collector_id, collection_time,
            collection_content, data_source
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """

        try:
            execute_query(self.connection, insert_sql, (
                collection_id,
                collection_data['project_id'],
                collection_data['collector_id'],
                collection_data['collection_time'],
                collection_data['collection_content'],
                collection_data['data_source']
            ))
            return True, collection_id
        except Exception as e:
            return False, str(e)

    def update_collection(self, collection_id, update_data):
        """修改采集记录（仅允许补充备注信息）"""
        # 检查采集记录是否存在
        check_sql = "SELECT * FROM research_data_collection WHERE collection_id = %s"
        if not fetch_query(self.connection, check_sql, (collection_id,)):
            return False, "采集记录不存在"

        # 仅允许更新备注信息（假设表中有remark字段，若没有可调整）
        if 'remark' not in update_data:
            return False, "仅允许补充备注信息"

        update_sql = "UPDATE research_data_collection SET remark = %s WHERE collection_id = %s"
        try:
            execute_query(self.connection, update_sql, (update_data['remark'], collection_id))
            return True, "备注信息更新成功"
        except Exception as e:
            return False, str(e)

    def query_collections(self, filters=None):
        """查询采集记录"""
        query_sql = "SELECT * FROM research_data_collection WHERE 1=1"
        data = []

        if filters:
            # 处理时间范围
            if 'start_time' in filters and 'end_time' in filters:
                query_sql += " AND collection_time BETWEEN %s AND %s"
                data.extend([filters['start_time'], filters['end_time']])
                del filters['start_time'], filters['end_time']

            # 处理其他条件
            for key, value in filters.items():
                if value:
                    query_sql += f" AND {key} = %s"
                    data.append(value)

        try:
            result = fetch_query(self.connection, query_sql, tuple(data))
            return True, result
        except Exception as e:
            return False, str(e)

    def get_collection_count(self, project_id):
        """统计项目下的采集记录总数"""
        count_sql = "SELECT COUNT(*) as count FROM research_data_collection WHERE project_id = %s"
        try:
            result = fetch_query(self.connection, count_sql, (project_id,))
            return True, result[0]['count']
        except Exception as e:
            return False, str(e)

    def delete_collection(self, collection_id, user_role, user_id):
        """删除采集记录（需权限验证）"""
        # 权限验证：系统管理员或项目负责人
        if user_role != 'admin':
            # 获取项目负责人ID
            proj_sql = """
            SELECT rp.leader_id 
            FROM research_data_collection rdc
            JOIN research_project rp ON rdc.project_id = rp.project_id
            WHERE rdc.collection_id = %s
            """
            leader = fetch_query(self.connection, proj_sql, (collection_id,))
            if not leader or leader[0]['leader_id'] != user_id:
                return False, "权限不足，仅系统管理员或项目负责人可删除"

        # 检查是否有成果引用该采集记录
        ref_sql = """
        SELECT COUNT(*) as count 
        FROM collection_monitor_data_rel 
        WHERE collection_id = %s
        """
        ref_count = fetch_query(self.connection, ref_sql, (collection_id,))[0]['count']
        if ref_count > 0:
            return False, "存在成果引用该采集记录，无法删除"

        # 执行删除
        delete_sql = "DELETE FROM research_data_collection WHERE collection_id = %s"
        try:
            execute_query(self.connection, delete_sql, (collection_id,))
            return True, "采集记录删除成功"
        except Exception as e:
            return False, str(e)


# 示例用法
if __name__ == "__main__":
    manager = CollectionManager("192.168.69.97", "qq", "515408", "sjk")

    # 示例：新增采集记录
    # new_collection = {
    #     "project_id": "PROJ-2025-001",
    #     "collector_id": "COLL-021",
    #     "collection_time": "2025-04-10 10:00:00",
    #     "collection_content": "测试采集内容",
    #     "data_source": "实地采集"
    # }
    # print(manager.add_collection(new_collection))