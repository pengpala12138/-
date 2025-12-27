import os
import sys
import warnings
# 设置环境变量禁用所有警告
os.environ['PYTHONWARNINGS'] = 'ignore'
def warn(*args, **kwargs):
    pass
warnings.warn = warn
if not sys.warnoptions:
    warnings.simplefilter("ignore")
    # 强制禁用所有警告
    warnings.filterwarnings("ignore", category=Warning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)

# 专门过滤SQLAlchemy相关警告
from sqlalchemy import exc
warnings.filterwarnings("ignore", category=exc.LegacyAPIWarning)
from sqlalchemy.exc import SAWarning
warnings.filterwarnings("ignore", category=SAWarning)

# 再次确保所有警告都被忽略
warnings.filterwarnings("ignore", message=".*utcnow.*")
warnings.filterwarnings("ignore", message=".*Query.get.*")

# 导入所需模块
import unittest
import time
from unittest.mock import MagicMock
from datetime import datetime, timedelta
import decimal
import random
from app import db, app, RegionInfo, MonitorIndicator, MonitorDevice, EnvironmentData, EnvironmentMonitorService


class PersistenceTest(unittest.TestCase):
    """持久化测试类，确保所有操作都使用新增的数据，不影响现有数据"""

    def setUp(self):
        """测试前的准备工作"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # 生成测试数据的唯一标识前缀，确保ID不超过20个字符
        timestamp = datetime.now().strftime('%y%m%d%H%M%S')
        random_suffix = random.randint(10, 99)
        self.test_prefix = f"T{timestamp}{random_suffix}"
        
        # 验证region_info表中有数据
        self.regions = RegionInfo.query.all()
        self.assertGreater(len(self.regions), 0, "region_info表中没有区域数据，请先插入区域数据")
        
        # 记录初始数据数量
        self.initial_indicator_count = MonitorIndicator.query.count()
        self.initial_device_count = MonitorDevice.query.count()
        self.initial_data_count = EnvironmentData.query.count()
        
        print(f"\n=== 测试前缀: {self.test_prefix} ===")
        print(f"初始数据数量 - 指标: {self.initial_indicator_count}, 设备: {self.initial_device_count}, 数据: {self.initial_data_count}")

    def tearDown(self):
        """测试后的清理工作"""
        # 只删除测试数据
        self.delete_test_data()
        
        # 验证没有影响现有数据
        final_indicator_count = MonitorIndicator.query.count()
        final_device_count = MonitorDevice.query.count()
        final_data_count = EnvironmentData.query.count()
        
        self.assertEqual(final_indicator_count, self.initial_indicator_count, "测试影响了现有指标数据")
        self.assertEqual(final_device_count, self.initial_device_count, "测试影响了现有设备数据")
        self.assertEqual(final_data_count, self.initial_data_count, "测试影响了现有环境数据")
        
        print(f"清理后数据数量 - 指标: {final_indicator_count}, 设备: {final_device_count}, 数据: {final_data_count}")
        print("=== 测试清理完成 ===\n")
        
        self.app_context.pop()

    def delete_test_data(self):
        """删除测试数据"""
        try:
            # 检查会话状态，确保没有挂起的事务
            if db.session.is_active and (db.session.dirty or db.session.deleted or db.session.new):
                db.session.rollback()
            # 删除测试环境数据
            env_data_count = EnvironmentData.query.filter(EnvironmentData.data_id.like(f"{self.test_prefix}%")).delete(synchronize_session=False)
            # 删除测试设备
            device_count = MonitorDevice.query.filter(MonitorDevice.device_id.like(f"{self.test_prefix}%")).delete(synchronize_session=False)
            # 删除测试指标
            indicator_count = MonitorIndicator.query.filter(MonitorIndicator.indicator_id.like(f"{self.test_prefix}%")).delete(synchronize_session=False)
            db.session.commit()
            print(f"  删除测试数据：环境数据 {env_data_count} 条，设备 {device_count} 台，指标 {indicator_count} 个")
        except Exception as e:
            db.session.rollback()
            print(f"  删除测试数据时出错：{str(e)}")
            raise

    def generate_test_indicator(self):
        """生成测试监测指标"""
        indicator_id = f"{self.test_prefix}I1"
        indicator = MonitorIndicator(
            indicator_id=indicator_id,
            indicator_name=f"测试指标_{self.test_prefix}",
            unit="mg/L",
            standard_upper=10.0,
            standard_lower=5.0,
            monitor_freq="小时"
        )
        db.session.add(indicator)
        return indicator

    def generate_test_device(self):
        """生成测试设备"""
        region = random.choice(self.regions)
        device_id = f"{self.test_prefix}D1"
        device = MonitorDevice(
            device_id=device_id,
            device_type="测试传感器",
            region_id=region.region_id,
            install_time=datetime.now().date() - timedelta(days=30),
            calibration_cycle="90天",
            operation_status="正常",
            comm_proto="MQTT"
        )
        db.session.add(device)
        return device

    def generate_test_env_data(self, indicator, device, monitor_value, collection_time=None):
        """生成测试环境数据，确保使用测试前缀"""
        if collection_time is None:
            collection_time = datetime.now()
        
        # 生成带测试前缀的data_id
        data_id = f"{self.test_prefix}ED{random.randint(1, 999):03d}"
        
        # 检查是否异常
        is_abnormal = monitor_value > indicator.standard_upper or monitor_value < indicator.standard_lower
        abnormal_reason = None
        if is_abnormal:
            if monitor_value > indicator.standard_upper:
                abnormal_reason = f"超出上限阈值 {indicator.standard_upper}"
            else:
                abnormal_reason = f"低于下限阈值 {indicator.standard_lower}"
        
        env_data = EnvironmentData(
            data_id=data_id,
            indicator_id=indicator.indicator_id,
            device_id=device.device_id,
            region_id=device.region_id,
            collection_time=collection_time,
            monitor_value=monitor_value,
            data_quality='优',
            is_abnormal=is_abnormal,
            abnormal_reason=abnormal_reason
        )
        
        db.session.add(env_data)
        return env_data

    def test_complete_crud_flow(self):
        """测试完整的增-改-查-删流程"""
        print("\n--- 测试完整的增-改-查-删流程 ---")
        
        # 记录初始数据数量
        initial_indicator_count = MonitorIndicator.query.count()
        initial_device_count = MonitorDevice.query.count()
        initial_data_count = EnvironmentData.query.count()
        print(f"初始数据 - 指标: {initial_indicator_count}, 设备: {initial_device_count}, 数据: {initial_data_count}")
        
        # 1. 测试数据新增（增加测试数据）
        print("\n1. 开始新增测试数据：")
        
        # 创建测试指标
        indicator = self.generate_test_indicator()
        self.assertIsNotNone(indicator)
        print(f"   - 指标创建成功: {indicator.indicator_id}")
        
        # 创建测试设备
        device = self.generate_test_device()
        self.assertIsNotNone(device)
        print(f"   - 设备创建成功: {device.device_id}")
        
        # 创建测试环境数据
        normal_value = 7.5  # 正常范围值
        env_data = self.generate_test_env_data(indicator, device, normal_value)
        self.assertIsNotNone(env_data)
        print(f"   - 环境数据创建成功: {env_data.data_id}")
        
        # 提交新增数据
        db.session.commit()
        
        # 验证数据已新增
        after_insert_indicator_count = MonitorIndicator.query.count()
        after_insert_device_count = MonitorDevice.query.count()
        after_insert_data_count = EnvironmentData.query.count()
        
        self.assertEqual(after_insert_indicator_count, initial_indicator_count + 1, "指标数据未正确新增")
        self.assertEqual(after_insert_device_count, initial_device_count + 1, "设备数据未正确新增")
        self.assertEqual(after_insert_data_count, initial_data_count + 1, "环境数据未正确新增")
        
        print(f"   ✓ 数据新增验证成功 - 指标: {after_insert_indicator_count}, 设备: {after_insert_device_count}, 数据: {after_insert_data_count}")
        
        # 2. 测试数据查询（查找测试数据）
        print("\n2. 开始查询测试数据：")
        
        # 查询刚创建的指标
        queried_indicator = MonitorIndicator.query.get(indicator.indicator_id)
        self.assertIsNotNone(queried_indicator)
        self.assertEqual(queried_indicator.indicator_id, indicator.indicator_id)
        print(f"   - 指标查询成功: {queried_indicator.indicator_id}")
        
        # 查询刚创建的设备
        queried_device = MonitorDevice.query.get(device.device_id)
        self.assertIsNotNone(queried_device)
        self.assertEqual(queried_device.device_id, device.device_id)
        print(f"   - 设备查询成功: {queried_device.device_id}")
        
        # 查询刚创建的环境数据
        queried_data = EnvironmentData.query.get(env_data.data_id)
        self.assertIsNotNone(queried_data)
        self.assertEqual(queried_data.data_id, env_data.data_id)
        self.assertEqual(queried_data.monitor_value, normal_value)
        self.assertEqual(queried_data.is_abnormal, False)
        print(f"   - 环境数据查询成功: {queried_data.data_id}, 值: {queried_data.monitor_value}")
        
        # 3. 测试数据修改
        print("\n3. 开始修改测试数据：")
        
        # 修改设备状态
        result = EnvironmentMonitorService.update_device_status(device.device_id, '故障')
        self.assertTrue(result['success'])
        
        # 验证设备状态已修改
        updated_device = MonitorDevice.query.get(device.device_id)
        self.assertEqual(updated_device.operation_status, '故障')
        print(f"   - 设备状态修改成功: 正常 -> 故障")
        
        # 修改环境数据的异常状态
        queried_data.is_abnormal = True
        queried_data.abnormal_reason = "测试修改异常状态"
        db.session.commit()
        
        # 验证环境数据已修改
        updated_data = EnvironmentData.query.get(env_data.data_id)
        self.assertEqual(updated_data.is_abnormal, True)
        self.assertEqual(updated_data.abnormal_reason, "测试修改异常状态")
        print(f"   - 环境数据异常状态修改成功")
        
        # 4. 再次查询验证修改结果
        print("\n4. 验证修改后的数据：")
        
        # 查询修改后的设备
        final_device = MonitorDevice.query.get(device.device_id)
        self.assertEqual(final_device.operation_status, '故障')
        print(f"   - 设备状态: {final_device.operation_status}")
        
        # 查询修改后的环境数据
        final_data = EnvironmentData.query.get(env_data.data_id)
        self.assertEqual(final_data.is_abnormal, True)
        print(f"   - 环境数据异常状态: {final_data.is_abnormal}")
        
        # 5. 测试数据删除
        print("\n5. 开始删除测试数据：")
        
        # 先删除环境数据
        db.session.delete(final_data)
        
        # 删除设备
        db.session.delete(final_device)
        
        # 删除指标
        db.session.delete(queried_indicator)
        
        # 提交删除操作
        db.session.commit()
        
        # 验证数据已删除
        final_indicator_count = MonitorIndicator.query.count()
        final_device_count = MonitorDevice.query.count()
        final_data_count = EnvironmentData.query.count()
        
        self.assertEqual(final_indicator_count, initial_indicator_count, "指标数据未正确删除")
        self.assertEqual(final_device_count, initial_device_count, "设备数据未正确删除")
        self.assertEqual(final_data_count, initial_data_count, "环境数据未正确删除")
        
        print(f"   ✓ 数据删除验证成功 - 指标: {final_indicator_count}, 设备: {final_device_count}, 数据: {final_data_count}")
        
        # 最终验证
        self.assertEqual(final_indicator_count, initial_indicator_count, "测试影响了现有指标数据")
        self.assertEqual(final_device_count, initial_device_count, "测试影响了现有设备数据")
        self.assertEqual(final_data_count, initial_data_count, "测试影响了现有环境数据")
        
        print("\n✅ 完整的增-改-查-删流程测试成功！")


if __name__ == '__main__':
    import time
    print("开始持久化测试...")
    start_time = time.time()
    
    # 运行测试
    unittest.main(verbosity=2)
    
    end_time = time.time()
    print(f"\n测试完成，总共耗时: {end_time - start_time:.2f}秒")
