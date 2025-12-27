from pro.utils.db_connection import create_db_connection, execute_query, fetch_query
import uuid
from datetime import datetime


class ProjectManager:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = create_db_connection(host, user, password, database)

    def __del__(self):
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()

    def generate_project_id(self):
        """生成唯一项目编号，格式：PROJ-YYYY-MM-XXXX"""
        date_str = datetime.now().strftime("%Y-%m")
        return f"PROJ-{date_str}-{uuid.uuid4().hex[:4].upper()}"

    def add_project(self, project_data):
        """
        新增科研项目
        project_data: 字典包含项目信息（project_name, leader_id, apply_unit等）
        """
        # 验证必填字段
        required_fields = ['project_name', 'leader_id', 'apply_unit', 'approval_time', 'research_field']
        for field in required_fields:
            if field not in project_data or not project_data[field]:
                return False, f"缺少必填字段：{field}"

        # 生成项目编号
        project_id = self.generate_project_id()

        # 构建插入SQL
        insert_sql = """
        INSERT INTO research_project (
            project_id, project_name, leader_id, apply_unit, approval_time,
            conclusion_time, project_status, research_field
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        # 处理默认值
        project_status = project_data.get('project_status', '在研')
        conclusion_time = project_data.get('conclusion_time')

        try:
            execute_query(self.connection, insert_sql, (
                project_id,
                project_data['project_name'],
                project_data['leader_id'],
                project_data['apply_unit'],
                project_data['approval_time'],
                conclusion_time,
                project_status,
                project_data['research_field']
            ))
            return True, project_id
        except Exception as e:
            return False, str(e)

    def update_project(self, project_id, update_data):
        """修改科研项目信息"""
        # 检查项目状态
        check_sql = "SELECT project_status FROM research_project WHERE project_id = %s"
        result = fetch_query(self.connection, check_sql, (project_id,))
        if not result:
            return False, "项目不存在"

        project_status = result[0]['project_status']
        if project_status == '已结题':
            # 已结题项目不可修改核心信息
            core_fields = ['project_name', 'leader_id', 'apply_unit', 'approval_time', 'research_field']
            for field in core_fields:
                if field in update_data:
                    return False, "已结题项目不可修改核心信息"

        # 构建更新SQL
        update_fields = []
        data = []
        for key, value in update_data.items():
            if key in ['project_status', 'conclusion_time'] or (
                    project_status != '已结题' and key in ['project_name', 'leader_id', 'apply_unit',
                                                           'research_field']):
                update_fields.append(f"{key} = %s")
                data.append(value)

        if not update_fields:
            return False, "没有可更新的字段"

        data.append(project_id)
        update_sql = f"UPDATE research_project SET {', '.join(update_fields)} WHERE project_id = %s"

        try:
            execute_query(self.connection, update_sql, tuple(data))
            return True, "更新成功"
        except Exception as e:
            return False, str(e)

    def query_projects(self, filters=None):
        """多条件查询项目"""
        query_sql = "SELECT * FROM research_project WHERE 1=1"
        data = []

        if filters:
            for key, value in filters.items():
                if value:
                    query_sql += f" AND {key} = %s"
                    data.append(value)

        try:
            result = fetch_query(self.connection, query_sql, tuple(data))
            return True, result
        except Exception as e:
            return False, str(e)

    def get_project_details(self, project_id):
        """查询项目及关联的采集记录和成果"""
        # 查询项目基本信息
        project_sql = "SELECT * FROM research_project WHERE project_id = %s"
        project = fetch_query(self.connection, project_sql, (project_id,))
        if not project:
            return False, "项目不存在"

        # 查询关联的采集记录
        collection_sql = "SELECT * FROM research_data_collection WHERE project_id = %s"
        collections = fetch_query(self.connection, collection_sql, (project_id,))

        # 查询关联的成果
        achievement_sql = "SELECT * FROM research_achievement WHERE project_id = %s"
        achievements = fetch_query(self.connection, achievement_sql, (project_id,))

        return True, {
            'project': project[0],
            'collections': collections,
            'achievements': achievements
        }

    def delete_project(self, project_id):
        """删除项目"""
        # 检查项目状态
        status_sql = "SELECT project_status FROM research_project WHERE project_id = %s"
        status_result = fetch_query(self.connection, status_sql, (project_id,))
        if not status_result:
            return False, "项目不存在"

        project_status = status_result[0]['project_status']

        # 检查是否为"未立项"状态
        if project_status == "未立项":
            delete_sql = "DELETE FROM research_project WHERE project_id = %s"
            execute_query(self.connection, delete_sql, (project_id,))
            return True, "项目删除成功"

        # 检查是否为"暂停"状态且无采集记录和成果
        if project_status == "暂停":
            # 检查采集记录
            coll_sql = "SELECT COUNT(*) as count FROM research_data_collection WHERE project_id = %s"
            coll_count = fetch_query(self.connection, coll_sql, (project_id,))[0]['count']
            if coll_count > 0:
                return False, "项目存在采集记录，无法删除"

            # 检查成果
            ach_sql = "SELECT COUNT(*) as count FROM research_achievement WHERE project_id = %s"
            ach_count = fetch_query(self.connection, ach_sql, (project_id,))[0]['count']
            if ach_count > 0:
                return False, "项目存在成果，无法删除"

            # 执行删除
            delete_sql = "DELETE FROM research_project WHERE project_id = %s"
            execute_query(self.connection, delete_sql, (project_id,))
            return True, "项目删除成功"

        return False, "仅允许删除'未立项'或'暂停且无采集记录/成果'的项目"


# 示例用法
if __name__ == "__main__":
    manager = ProjectManager("192.168.69.97", "qq", "515408", "sjk")

    # 示例：新增项目
    # new_project = {
    #     "project_name": "测试项目",
    #     "leader_id": "LEADER-021",
    #     "apply_unit": "测试单位",
    #     "approval_time": "2025-04-01",
    #     "research_field": "测试领域"
    # }
    # print(manager.add_project(new_project))