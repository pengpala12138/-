# backend/config.py
import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ========== 你的数据库信息（必须填对） ==========
DB_CONFIG = {
    "host": "127.0.0.1",    # 你的数据库IP
    "user": "root",              # 你的数据库用户名
    "password": "Aa20051004",       # 你的数据库密码
    "db": "sjk",                # 你的数据库名
    "port": 3306,               # MySQL默认端口，不用改
    "charset": "utf8mb4"        # 支持中文，必填
}

'''
DB_CONFIG = {
    "host": "172.20.10.4",    # 你的数据库IP
    "user": "sjy",              # 你的数据库用户名
    "password": "515408",       # 你的数据库密码
    "db": "sjk",                # 你的数据库名
    "port": 3306,               # MySQL默认端口，不用改
    "charset": "utf8mb4"        # 支持中文，必填
} '''

# 1. 创建SQLAlchemy引擎（连接MySQL）
engine = create_engine(
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['db']}?charset={DB_CONFIG['charset']}",
    echo=False,  # 调试时可设为True，打印SQL语句
    pool_pre_ping=True
)

# 2. 创建数据库会话（执行CRUD用）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. 模型基类
Base = declarative_base()

# 4. 获取数据库连接（供接口调用）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()