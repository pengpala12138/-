# config.py - 修复版本
import os

# 方法1：使用 DB_CONFIG 字典
DB_CONFIG = {
    'host': '170.20.10.4',
    'port': 3306,
    'user': 'qq',
    'password': '515408',
    'database': 'sjk',
    'charset': 'utf8mb4'
}

# 从 DB_CONFIG 构建 SQLAlchemy 连接字符串
# SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}&auth_plugin=mysql_native_password"
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"

# 完整的 Flask 配置
FLASK_CONFIG = {
    'SQLALCHEMY_DATABASE_URI': SQLALCHEMY_DATABASE_URI,
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SQLALCHEMY_ENGINE_OPTIONS': {
        'connect_args': {
            'auth_plugin': 'mysql_native_password'
        }
    },
    'SECRET_KEY': 'your-secret-key-123456',
    'DEBUG': True
}