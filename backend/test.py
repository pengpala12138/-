import unittest
import uuid
from datetime import datetime, date
from .database import db
from .models import Tourist, Reservation, Trajectory, FlowControl


class TestDatabase(unittest.TestCase):
    """持久层测试类，覆盖所有核心操作和功能模块"""

    @classmethod
    def setUpClass(cls):
        """在所有测试开始前执行一次，确保region_info表中有数据"""
        try:
            # 检查region_info表中是否有数据
            result = db.execute_query("SELECT COUNT(*) as count FROM region_info")
            if result[0]['count'] == 0:
                raise Exception("region_info表中没有数据，请先导入数据后再运行测试")
            print("region_info表数据检查完成")
        except Exception as e:
            print(f"检查region_info表时出错: {e}")
            raise

    def setUp(self):
        """测试前的准备工作，创建测试数据"""
        # 生成唯一ID
        self.test_tourist_id = f"test_{uuid.uuid4().hex[:8]}"
        self.test_reservation_id = f"res_{uuid.uuid4().hex[:8]}"

        # 从region_info表中获取一个存在的area_id
        try:
            # 获取一个region_id用于测试
            region_result = db.execute_query(
                "SELECT region_id FROM region_info LIMIT 1"
            )
            if region_result:
                self.existing_area_id = region_result[0]['region_id']
            else:
                raise Exception("region_info表中没有数据")
        except Exception as e:
            print(f"获取region_id时出错: {e}")
            # 使用默认的测试ID
            self.existing_area_id = 'A001'

        # 创建测试游客数据
        self.test_tourist_data = {
            'tourist_id': self.test_tourist_id,
            'name': '测试游客',
            'id_card': f"110101{datetime.now().strftime('%Y%m%d')}1234",
            'phone': '13800138000',
            'entry_time': datetime.now(),
            'entry_method': 'online'
        }

        # 创建测试预约数据
        self.test_reservation_data = {
            'reservation_id': self.test_reservation_id,
            'tourist_id': self.test_tourist_id,
            'reservation_date': date.today(),
            'entry_time_slot': '09:00-10:00',
            'group_size': 2,
            'status': 'confirmed',
            'ticket_amount': 100.00,
            'payment_status': 'paid'
        }

        # 创建测试轨迹数据
        self.test_trajectory_data = {
            'tourist_id': self.test_tourist_id,
            'location_time': datetime.now(),
            'latitude': 39.9042,
            'longitude': 116.4074,
            'area_id': self.existing_area_id,  # 使用已有的area_id
            'off_route': False
        }

        # 创建测试系统日志数据
        self.test_log_data = {
            'log_type': 'info',
            'module': 'test',
            'message': '测试日志信息',
            'user_id': self.test_tourist_id,
            'ip_address': '127.0.0.1'
        }

    def tearDown(self):
        """测试后的清理工作，删除测试数据"""
        try:
            # 注意：我们只删除测试插入的数据，不删除region_info表中的数据

            # 1. 先删除可能存在的ecological_feedback记录（如果有的话）
            try:
                db.execute_update("DELETE FROM ecological_feedback WHERE area_id LIKE 'test_area_%'")
            except Exception as e:
                print(f"删除ecological_feedback时可能无此表或记录: {e}")

            # 2. 删除轨迹数据
            db.execute_update("DELETE FROM trajectories WHERE tourist_id = %s", (self.test_tourist_id,))

            # 3. 删除预约记录
            db.execute_update("DELETE FROM reservations WHERE tourist_id = %s", (self.test_tourist_id,))

            # 4. 删除系统日志
            db.execute_update("DELETE FROM system_logs WHERE user_id = %s", (self.test_tourist_id,))

            # 5. 删除游客记录
            db.execute_update("DELETE FROM tourists WHERE tourist_id = %s", (self.test_tourist_id,))

        except Exception as e:
            print(f"清理测试数据时出错: {e}")

    def test_connection(self):
        """测试数据库连接是否正常"""
        try:
            result = db.execute_query("SELECT 1")
            self.assertEqual(result[0]['1'], 1)
        except Exception as e:
            self.fail(f"数据库连接测试失败: {e}")

    # ==================== 游客表测试 ====================
    def test_tourist_operations(self):
        """测试游客表的CRUD操作"""
        # 1. 插入游客数据
        rows_affected = db.execute_update(
            "INSERT INTO tourists (tourist_id, name, id_card, phone, entry_time, entry_method) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (self.test_tourist_data['tourist_id'], self.test_tourist_data['name'],
             self.test_tourist_data['id_card'], self.test_tourist_data['phone'],
             self.test_tourist_data['entry_time'], self.test_tourist_data['entry_method'])
        )
        self.assertEqual(rows_affected, 1)

        # 2. 查询游客数据
        result = db.execute_query("SELECT * FROM tourists WHERE tourist_id = %s",
                                  (self.test_tourist_data['tourist_id'],), fetch_one=True)
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], '测试游客')

        # 3. 更新游客数据
        new_name = '更新后的游客'
        rows_affected = db.execute_update(
            "UPDATE tourists SET name = %s WHERE tourist_id = %s",
            (new_name, self.test_tourist_id)
        )
        self.assertEqual(rows_affected, 1)

        # 验证更新结果
        result = db.execute_query("SELECT * FROM tourists WHERE tourist_id = %s",
                                  (self.test_tourist_data['tourist_id'],), fetch_one=True)
        self.assertEqual(result['name'], new_name)

    # ==================== 预约表测试 ====================
    def test_reservation_operations(self):
        """测试预约表的CRUD操作"""
        # 先插入游客数据（外键依赖）
        db.execute_update(
            "INSERT INTO tourists (tourist_id, name, id_card, phone, entry_time, entry_method) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (self.test_tourist_data['tourist_id'], self.test_tourist_data['name'],
             self.test_tourist_data['id_card'], self.test_tourist_data['phone'],
             self.test_tourist_data['entry_time'], self.test_tourist_data['entry_method'])
        )

        # 1. 插入预约数据
        rows_affected = db.execute_update(
            "INSERT INTO reservations (reservation_id, tourist_id, reservation_date, entry_time_slot, "
            "group_size, status, ticket_amount, payment_status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (self.test_reservation_data['reservation_id'], self.test_reservation_data['tourist_id'],
             self.test_reservation_data['reservation_date'], self.test_reservation_data['entry_time_slot'],
             self.test_reservation_data['group_size'], self.test_reservation_data['status'],
             self.test_reservation_data['ticket_amount'], self.test_reservation_data['payment_status'])
        )
        self.assertEqual(rows_affected, 1)

        # 2. 查询预约数据
        result = db.execute_query("SELECT * FROM reservations WHERE reservation_id = %s",
                                  (self.test_reservation_data['reservation_id'],), fetch_one=True)
        self.assertIsNotNone(result)
        self.assertEqual(result['tourist_id'], self.test_tourist_id)

        # 3. 更新预约数据
        new_status = 'completed'
        rows_affected = db.execute_update(
            "UPDATE reservations SET status = %s WHERE reservation_id = %s",
            (new_status, self.test_reservation_id)
        )
        self.assertEqual(rows_affected, 1)

    # ==================== 轨迹表测试 ====================
    def test_trajectory_operations(self):
        """测试轨迹表的CRUD操作"""
        # 先插入游客数据（外键依赖）
        db.execute_update(
            "INSERT INTO tourists (tourist_id, name, id_card, phone, entry_time, entry_method) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (self.test_tourist_data['tourist_id'], self.test_tourist_data['name'],
             self.test_tourist_data['id_card'], self.test_tourist_data['phone'],
             self.test_tourist_data['entry_time'], self.test_tourist_data['entry_method'])
        )

        # 1. 插入轨迹数据
        rows_affected = db.execute_update(
            "INSERT INTO trajectories (tourist_id, location_time, latitude, longitude, area_id, off_route) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (self.test_trajectory_data['tourist_id'], self.test_trajectory_data['location_time'],
             self.test_trajectory_data['latitude'], self.test_trajectory_data['longitude'],
             self.test_trajectory_data['area_id'], self.test_trajectory_data['off_route'])
        )
        self.assertEqual(rows_affected, 1)

        # 2. 查询轨迹数据
        result = db.execute_query(
            "SELECT * FROM trajectories WHERE tourist_id = %s ORDER BY location_time DESC",
            (self.test_tourist_id,), fetch_one=True
        )
        self.assertIsNotNone(result)
        self.assertEqual(result['area_id'], self.existing_area_id)

    # ==================== 流量控制表测试 ====================
    def test_flow_control_operations(self):
        """测试流量控制表的查询和更新操作（不插入新数据）"""
        # 检查flow_control表中是否已存在数据
        existing_flow = db.execute_query(
            "SELECT * FROM flow_control WHERE area_id = %s",
            (self.existing_area_id,), fetch_one=True
        )

        if existing_flow:
            # 1. 查询流量控制数据
            result = db.execute_query("SELECT * FROM flow_control WHERE area_id = %s",
                                      (self.existing_area_id,), fetch_one=True)
            self.assertIsNotNone(result)

            # 2. 更新流量控制数据
            current_visitors = result.get('current_visitors', 0)
            new_current_visitors = current_visitors + 50
            rows_affected = db.execute_update(
                "UPDATE flow_control SET current_visitors = %s WHERE area_id = %s",
                (new_current_visitors, self.existing_area_id)
            )
            self.assertEqual(rows_affected, 1)

            # 3. 验证更新结果
            updated_result = db.execute_query("SELECT * FROM flow_control WHERE area_id = %s",
                                              (self.existing_area_id,), fetch_one=True)
            self.assertEqual(updated_result['current_visitors'], new_current_visitors)

            # 4. 恢复原始数据（可选）
            db.execute_update(
                "UPDATE flow_control SET current_visitors = %s WHERE area_id = %s",
                (current_visitors, self.existing_area_id)
            )
        else:
            # 如果flow_control表中没有该区域的数据，只测试查询
            print(f"flow_control表中没有area_id为{self.existing_area_id}的记录，跳过更新测试")
            # 可以测试插入，但需要确保area_id在region_info表中存在
            # 由于外键约束，我们不能随意插入新数据

    # ==================== 系统日志表测试 ====================
    def test_system_logs_operations(self):
        """测试系统日志表的CRUD操作"""
        # 1. 插入系统日志
        rows_affected = db.execute_update(
            "INSERT INTO system_logs (log_type, module, message, user_id, ip_address) "
            "VALUES (%s, %s, %s, %s, %s)",
            (self.test_log_data['log_type'], self.test_log_data['module'],
             self.test_log_data['message'], self.test_log_data['user_id'],
             self.test_log_data['ip_address'])
        )
        self.assertEqual(rows_affected, 1)

        # 2. 查询系统日志
        result = db.execute_query(
            "SELECT * FROM system_logs WHERE user_id = %s ORDER BY created_at DESC",
            (self.test_tourist_id,), fetch_one=True
        )
        self.assertIsNotNone(result)
        self.assertEqual(result['message'], '测试日志信息')

    # ==================== 高级功能测试 ====================
    def test_batch_insert(self):
        """测试批量插入操作"""
        # 创建多条测试数据（游客）
        batch_data = []
        self.batch_tourist_ids = []
        for i in range(3):
            tourist_id = f"batch_{uuid.uuid4().hex[:8]}"
            self.batch_tourist_ids.append(tourist_id)
            batch_data.append({
                'tourist_id': tourist_id,
                'name': f'批量测试游客{i}',
                'id_card': f"11010120000101{i:04d}",
                'phone': f'1380013800{i}',
                'entry_time': datetime.now(),
                'entry_method': 'online'
            })

        # 执行批量插入
        rows_affected = db.batch_insert('tourists', batch_data)
        self.assertEqual(rows_affected, 3)

        # 验证数据是否插入成功
        for tourist_id in self.batch_tourist_ids:
            result = db.execute_query("SELECT * FROM tourists WHERE tourist_id = %s", (tourist_id,))
            self.assertEqual(len(result), 1)

        # 清理批量插入的数据
        for tourist_id in self.batch_tourist_ids:
            db.execute_update("DELETE FROM tourists WHERE tourist_id = %s", (tourist_id,))

    def test_foreign_key_constraint(self):
        """测试外键约束"""
        # 先插入游客数据
        db.execute_update(
            "INSERT INTO tourists (tourist_id, name, id_card, phone, entry_time, entry_method) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (self.test_tourist_data['tourist_id'], self.test_tourist_data['name'],
             self.test_tourist_data['id_card'], self.test_tourist_data['phone'],
             self.test_tourist_data['entry_time'], self.test_tourist_data['entry_method'])
        )

        # 插入预约数据（带外键关联）
        rows_affected = db.execute_update(
            "INSERT INTO reservations (reservation_id, tourist_id, reservation_date, entry_time_slot, "
            "group_size, status, ticket_amount, payment_status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (self.test_reservation_data['reservation_id'], self.test_reservation_data['tourist_id'],
             self.test_reservation_data['reservation_date'], self.test_reservation_data['entry_time_slot'],
             self.test_reservation_data['group_size'], self.test_reservation_data['status'],
             self.test_reservation_data['ticket_amount'], self.test_reservation_data['payment_status'])
        )
        self.assertEqual(rows_affected, 1)

    def test_error_handling(self):
        """测试异常处理"""
        # 先清理可能存在的测试数据
        try:
            db.execute_update("DELETE FROM tourists WHERE tourist_id = %s", (self.test_tourist_id,))
        except:
            pass

        # 测试插入重复主键
        db.execute_update(
            "INSERT INTO tourists (tourist_id, name, id_card, phone, entry_time, entry_method) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (self.test_tourist_data['tourist_id'], self.test_tourist_data['name'],
             self.test_tourist_data['id_card'], self.test_tourist_data['phone'],
             self.test_tourist_data['entry_time'], self.test_tourist_data['entry_method'])
        )

        # 再次插入相同主键的数据，应该抛出异常
        with self.assertRaises(Exception):
            db.execute_update(
                "INSERT INTO tourists (tourist_id, name, id_card, phone, entry_time, entry_method) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (self.test_tourist_data['tourist_id'], '重复测试游客',
                 f"110101{datetime.now().strftime('%Y%m%d')}5678", '13900139000',
                 datetime.now(), 'online')
            )

    def test_model_conversion(self):
        """测试所有模型的转换功能"""
        # 测试Tourist模型
        tourist = Tourist(
            tourist_id=self.test_tourist_id,
            name='测试游客',
            id_card='110101199001011234',
            phone='13800138000',
            entry_time=datetime.now(),
            entry_method='online'
        )
        tourist_dict = tourist.to_dict()
        self.assertEqual(tourist_dict['tourist_id'], self.test_tourist_id)

        # 测试Reservation模型
        reservation = Reservation(
            reservation_id=self.test_reservation_id,
            tourist_id=self.test_tourist_id,
            reservation_date=date.today(),
            entry_time_slot='09:00-10:00',
            group_size=2,
            status='confirmed',
            ticket_amount=100.00,
            payment_status='paid'
        )
        reservation_dict = reservation.to_dict()
        self.assertEqual(reservation_dict['reservation_id'], self.test_reservation_id)

        # 测试Trajectory模型
        trajectory = Trajectory(
            tourist_id=self.test_tourist_id,
            location_time=datetime.now(),
            latitude=39.9042,
            longitude=116.4074,
            area_id=self.existing_area_id,  # 使用存在的area_id
            off_route=False
        )
        trajectory_dict = trajectory.to_dict()
        self.assertEqual(trajectory_dict['area_id'], self.existing_area_id)

        # 测试FlowControl模型
        # 检查flow_control表中是否有数据
        flow_result = db.execute_query(
            "SELECT * FROM flow_control WHERE area_id = %s",
            (self.existing_area_id,), fetch_one=True
        )

        if flow_result:
            flow_control = FlowControl(
                area_id=flow_result['area_id'],
                area_name=flow_result.get('area_name', '测试区域'),
                daily_capacity=flow_result.get('daily_capacity', 1000),
                current_visitors=flow_result.get('current_visitors', 500),
                warning_threshold=flow_result.get('warning_threshold', 0.8),
                status=flow_result.get('status', 'normal')
            )
            flow_control_dict = flow_control.to_dict()
            self.assertEqual(flow_control_dict['area_id'], self.existing_area_id)
        else:
            # 如果flow_control表中没有数据，使用默认值
            print("flow_control表中没有数据，跳过FlowControl模型测试")


if __name__ == '__main__':
    # 运行所有测试用例
    unittest.main(verbosity=2)