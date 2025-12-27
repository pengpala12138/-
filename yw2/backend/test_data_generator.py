# backend/test_data_generator.py
import random
import decimal
from datetime import datetime, timedelta
from app import db, RegionInfo, MonitorIndicator, MonitorDevice, EnvironmentData


def generate_test_data():
    """生成完整的测试数据，不影响现有数据"""

    # 生成测试数据的唯一标识前缀，确保ID不超过20个字符
    timestamp = datetime.now().strftime('%y%m%d%H%M%S')
    random_suffix = random.randint(100, 999)
    test_prefix = f"T{timestamp}_{random_suffix}"
    print(f"测试前缀: {test_prefix}")

    # 检查region_info表中是否有数据
    regions = RegionInfo.query.all()
    if not regions:
        print("region_info表中没有区域数据，请先插入区域数据")
        return

    # 1. 生成监测指标
    indicators_data = [
        {'name': '空气质量PM2.5', 'unit': 'μg/m³', 'upper': 35.0, 'lower': 0.0, 'freq': '小时'},
        {'name': '水质PH值', 'unit': 'pH', 'upper': 8.5, 'lower': 6.5, 'freq': '日'},
        {'name': '土壤湿度', 'unit': '%', 'upper': 80.0, 'lower': 20.0, 'freq': '日'},
        {'name': '温度', 'unit': '°C', 'upper': 35.0, 'lower': -10.0, 'freq': '小时'},
        {'name': '湿度', 'unit': '%', 'upper': 90.0, 'lower': 20.0, 'freq': '小时'},
        {'name': '噪音', 'unit': 'dB', 'upper': 60.0, 'lower': 20.0, 'freq': '小时'},
        {'name': '水质溶解氧', 'unit': 'mg/L', 'upper': 10.0, 'lower': 5.0, 'freq': '日'},
        {'name': '土壤温度', 'unit': '°C', 'upper': 30.0, 'lower': 5.0, 'freq': '日'},
        {'name': '风速', 'unit': 'm/s', 'upper': 15.0, 'lower': 0.0, 'freq': '小时'},
        {'name': '降雨量', 'unit': 'mm', 'upper': 50.0, 'lower': 0.0, 'freq': '日'}
    ]

    indicators = []
    for i, data in enumerate(indicators_data, 1):
        indicator = MonitorIndicator(
            indicator_id=f'{test_prefix}I{i:02d}',
            indicator_name=f'{test_prefix}_{data['name']}',
            unit=data['unit'],
            standard_upper=data['upper'],
            standard_lower=data['lower'],
            monitor_freq=data['freq']
        )
        indicators.append(indicator)

    db.session.add_all(indicators)
    db.session.commit()
    print(f"已生成 {len(indicators)} 个监测指标")

    # 2. 生成监测设备
    device_types = ['空气质量传感器', '水质监测仪', '土壤传感器', '温湿度传感器',
                    '噪音监测仪', '气象站', '水质多参数仪', '土壤多参数仪']

    devices = []
    for i in range(1, 21):
        device = MonitorDevice(
            device_id=f'{test_prefix}D{i:02d}',
            device_type=random.choice(device_types),
            region_id=random.choice(regions).region_id,
            install_time=datetime.now().date() - timedelta(days=random.randint(0, 365)),
            calibration_cycle=f'{random.choice([30, 60, 90])}天',
            operation_status=random.choice(['正常', '正常', '正常', '故障', '离线']),
            comm_proto=random.choice(['MQTT', 'HTTP', 'LoRa', 'NB-IoT'])
        )
        devices.append(device)

    db.session.add_all(devices)
    db.session.commit()
    print(f"已生成 {len(devices)} 个监测设备")

    # 3. 生成环境监测数据
    env_data_list = []
    base_time = datetime.now() - timedelta(days=30)

    for i in range(1, 501):  # 生成500条测试数据
        device = random.choice(devices)
        indicator = random.choice(indicators)

        # 根据指标类型生成合理的监测值（20%的数据会超出阈值）
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
                monitor_value = indicator.standard_upper + decimal.Decimal(str(random.uniform(1, 20)))
            else:
                monitor_value = indicator.standard_upper + decimal.Decimal(str(random.uniform(1, 20)))
        else:
            monitor_value = base_value

        # 数据质量
        data_quality = random.choice(['优', '良', '中', '差'])

        # 检查是否异常
        is_abnormal = (monitor_value > indicator.standard_upper or
                       monitor_value < indicator.standard_lower)

        abnormal_reason = None
        if is_abnormal:
            if monitor_value > indicator.standard_upper:
                abnormal_reason = f"超出上限阈值 {indicator.standard_upper}"
            else:
                abnormal_reason = f"低于下限阈值 {indicator.standard_lower}"

        # 生成data_id，确保不超过20个字符
        data_id = f'{test_prefix}ED{i:05d}'[:20]
        env_data = EnvironmentData(
            data_id=data_id,
            indicator_id=indicator.indicator_id,
            device_id=device.device_id,
            region_id=device.region_id,
            collection_time=base_time + timedelta(hours=i),
            monitor_value=float(monitor_value),
            data_quality=data_quality,
            is_abnormal=is_abnormal,
            abnormal_reason=abnormal_reason
        )
        env_data_list.append(env_data)

        # 每100条提交一次，避免内存溢出
        if i % 100 == 0:
            db.session.add_all(env_data_list)
            db.session.commit()
            env_data_list = []
            print(f"已生成 {i} 条环境监测数据")

    # 提交剩余数据
    if env_data_list:
        db.session.add_all(env_data_list)
        db.session.commit()

    print(f"已生成总计 500 条环境监测数据")
    print("测试数据生成完成！")


if __name__ == '__main__':
    from app import app

    with app.app_context():
        generate_test_data()