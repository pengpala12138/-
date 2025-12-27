from pro.utils.db_connection import create_db_connection, execute_query, fetch_query
import uuid
from datetime import datetime
import os


class AchievementManager:
    def __init__(self, host, user, password, database, file_storage_path):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.file_storage_path = file_storage_path
        self.connection = create_db_connection(host, user, password, database)

        # 确保文件存储目录存在
        os.makedirs(file_storage_path, exist_ok=True)

    def __del__(self):
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()

    def generate_achievement_id(self):
        """生成唯一成果编号"""
        date_str = datetime.now().strftime("%Y-%m")
        return f"ACH-{date_str}-{uuid.uuid4().hex[:4].upper()}"

    def save_file(self, file):
        """保存上传的成果文件"""
        try:
            file_ext = os.path.splitext(file.filename)[1]
            file_name = f"{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(self.file_storage_path, file_name)

            # 保存文件（这里假设file是Flask的FileStorage对象）
            file.save(file_path)
            return True, f"/data/ach/{file_name}"  # 返回数据库存储的路径
        except Exception as e:
            return False, str(e)

    def add_achievement(self, achievement_data, file=None):
        """新增科研成果"""
        # 验证必填字段
        required_fields = ['project_id', 'achievement_type', 'achievement_name', 'publish_time', 'share_permission']
        for field in required_fields:
            if field not in achievement_data or not achievement_data[field]:
                return False, f"缺少必填字段：{field}"

        # 验证项目是否存在
        project_sql = "SELECT project_status FROM research_project WHERE project_id = %s"
        project = fetch_query(self.connection, project_sql, (achievement_data['project_id'],))
        if not project:
            return False, "关联项目不存在"

        # 验证成果类型
        if achievement_data['achievement_type'] not in ['论文', '报告', '专利']:
            return False, "成果类型必须是'论文'、'报告'或'专利'"

        # 验证共享权限
        if achievement_data['share_permission'] not in ['公开', '内部共享', '保密']:
            return False, "共享权限必须是'公开'、'内部共享'或'保密'"

        # 处理文件上传
        file_path = None
        if file:
            save_result, file_info = self.save_file(file)
            if not save_result:
                return False, f"文件保存失败：{file_info}"
            file_path = file_info

        # 生成成果ID
        achievement_id = self.generate_achievement_id()

        # 插入记录
        insert_sql = """
        INSERT INTO research_achievement (
            achievement_id, project_id, achievement_type, achievement_name,
            publish_time, share_permission, file_path
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        try:
            execute_query(self.connection, insert_sql, (
                achievement_id,
                achievement_data['project_id'],
                achievement_data['achievement_type'],
                achievement_data['achievement_name'],
                achievement_data['publish_time'],
                achievement_data['share_permission'],
                file_path
            ))
            return True, achievement_id
        except Exception as e:
            # 若数据库插入失败，删除已保存的文件
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            return False, str(e)

    def update_achievement(self, achievement_id, update_data):
        """修改科研成果"""
        # 检查成果是否存在
        check_sql = "SELECT * FROM research_achievement WHERE achievement_id = %s"
        result = fetch_query(self.connection, check_sql, (achievement_id,))
        if not result:
            return False, "成果不存在"

        current_achievement = result[0]
        update_fields = []
        data = []

        # 处理共享权限更新限制
        if 'share_permission' in update_data:
            if current_achievement['share_permission'] == '公开' and update_data['share_permission'] == '保密':
                return False, "公开成果不可改为保密"
            update_fields.append("share_permission = %s")
            data.append(update_data['share_permission'])

        # 处理成果名称更新
        if 'achievement_name' in update_data and update_data['achievement_name']:
            update_fields.append("achievement_name = %s")
            data.append(update_data['achievement_name'])

        if not update_fields:
            return False, "没有可更新的字段"

        data.append(achievement_id)
        update_sql = f"UPDATE research_achievement SET {', '.join(update_fields)} WHERE achievement_id = %s"

        try:
            execute_query(self.connection, update_sql, tuple(data))
            return True, "成果更新成功"
        except Exception as e:
            return False, str(e)

    def query_achievements(self, filters=None, user_role=None, user_id=None):
        """查询科研成果（带权限控制）"""
        query_sql = "SELECT * FROM research_achievement WHERE 1=1"
        data = []

        # 权限过滤：保密成果仅负责人与授权人员可查
        if user_role != 'admin':  # 非管理员
            # 获取用户有权限的项目
            auth_sql = """
            SELECT DISTINCT project_id FROM research_project WHERE leader_id = %s
            UNION
            SELECT DISTINCT project_id FROM project_achievement_share WHERE authorizer_id = %s
            """
            auth_projects = fetch_query(self.connection, auth_sql, (user_id, user_id))
            auth_project_ids = [p['project_id'] for p in auth_projects]

            if auth_project_ids:
                query_sql += " AND (share_permission != '保密' OR project_id IN ({})".format(
                    ', '.join(['%s'] * len(auth_project_ids))
                )
                data.extend(auth_project_ids)
                query_sql += ")"
            else:
                query_sql += " AND share_permission != '保密'"

        # 应用其他筛选条件
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

    def delete_achievement(self, achievement_id, user_role, user_id):
        """删除科研成果（需权限验证）"""
        # 权限验证：系统管理员或项目负责人
        if user_role != 'admin':
            # 获取项目负责人ID
            proj_sql = """
            SELECT rp.leader_id 
            FROM research_achievement ra
            JOIN research_project rp ON ra.project_id = rp.project_id
            WHERE ra.achievement_id = %s
            """
            leader = fetch_query(self.connection, proj_sql, (achievement_id,))
            if not leader or leader[0]['leader_id'] != user_id:
                return False, "权限不足，仅系统管理员或项目负责人可删除"

        # 检查是否有外部引用
        ref_sql = "SELECT COUNT(*) as count FROM project_achievement_share WHERE achievement_id = %s"
        ref_count = fetch_query(self.connection, ref_sql, (achievement_id,))[0]['count']
        if ref_count > 0:
            return False, "存在外部引用，无法删除"

        # 获取文件路径并删除文件
        file_sql = "SELECT file_path FROM research_achievement WHERE achievement_id = %s"
        file_path = fetch_query(self.connection, file_sql, (achievement_id,))[0]['file_path']
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                return False, f"文件删除失败：{str(e)}"

        # 执行删除
        delete_sql = "DELETE FROM research_achievement WHERE achievement_id = %s"
        try:
            execute_query(self.connection, delete_sql, (achievement_id,))
            return True, "成果删除成功"
        except Exception as e:
            return False, str(e)


# 示例用法
if __name__ == "__main__":
    FILE_STORAGE = "/data/ach"  # 实际部署时修改为真实路径
    manager = AchievementManager("192.168.69.97", "qq", "515408", "sjk", FILE_STORAGE)

    # 示例：新增成果
    # new_achievement = {
    #     "project_id": "PROJ-2025-001",
    #     "achievement_type": "论文",
    #     "achievement_name": "测试论文",
    #     "publish_time": "2025-04-10",
    #     "share_permission": "内部共享"
    # }
    # print(manager.add_achievement(new_achievement))  # 实际使用时传入file参数