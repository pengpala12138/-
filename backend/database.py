import sys
import os

# 添加 DBUtils 的安装路径
dbutils_path = r"C:\Users\付欣婷\AppData\Roaming\Python\Python312\site-packages"
if dbutils_path not in sys.path:
    sys.path.append(dbutils_path)

try:
    from dbutils.pooled_db import PooledDB
    print("成功导入 DBUtils")
except ImportError as e:
    print(f"导入 DBUtils 失败: {e}")
    print(f"当前 sys.path: {sys.path}")
    exit(1)
import pymysql
import threading
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_pool()
        return cls._instance

    def _init_pool(self):
        """初始化数据库连接池"""
        self.pool = PooledDB(
            creator=pymysql,
            maxconnections=10,
            mincached=2,
            maxcached=5,
            blocking=True,
            host='172.20.10.4',
            port=3306,
            user='fxt',
            password='515408',
            database='sjk',
            charset='utf8mb4',
            use_unicode=True,
            # 核心修改：强制会话级别所有编码为 utf8mb4，防止服务器默认 gbk 干扰
            init_command=
                "SET NAMES utf8mb4; "

            ,
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor
        )
        logger.info("数据库连接池初始化完成")

    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = None
        try:
            conn = self.pool.connection()
            yield conn
        except pymysql.Error as err:
            logger.error(f"数据库连接错误: {err}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(self, query, params=None, fetch_one=False):
        """执行查询"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SET NAMES utf8mb4")
                cursor.execute("SET CHARACTER SET utf8mb4")
                cursor.execute(query, params or ())
                if fetch_one:
                    result = cursor.fetchone()
                else:
                    result = cursor.fetchall()
                return result
            except pymysql.Error as err:
                logger.error(f"查询执行错误: {err}")
                raise
            finally:
                cursor.close()

    def execute_update(self, query, params=None):
        """执行更新/插入/删除"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SET NAMES utf8mb4")
                cursor.execute("SET CHARACTER SET utf8mb4")
                cursor.execute(query, params or ())

                affected_rows = cursor.rowcount
                # 注意：pymysql中autocommit=True时不需要显式commit
                return affected_rows
            except pymysql.Error as err:
                logger.error(f"更新执行错误: {err}")
                raise
            finally:
                cursor.close()

    def call_procedure(self, proc_name, args=None):
        """调用存储过程"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if args:
                    cursor.callproc(proc_name, args)
                else:
                    cursor.callproc(proc_name)

                # 获取所有结果集
                results = []
                cursor.nextset()  # 移动到第一个结果集
                while True:
                    try:
                        results.extend(cursor.fetchall())
                        if not cursor.nextset():
                            break
                    except pymysql.Error:
                        break

                return results
            except pymysql.Error as err:
                logger.error(f"存储过程调用错误: {err}")
                raise
            finally:
                cursor.close()

    def batch_insert(self, table, data_list):
        """批量插入数据"""
        if not data_list:
            return 0

        columns = ', '.join(data_list[0].keys())
        placeholders = ', '.join(['%s'] * len(data_list[0]))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        values = [tuple(item.values()) for item in data_list]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, values)
                affected_rows = cursor.rowcount
                return affected_rows
            except pymysql.Error as err:
                logger.error(f"批量插入错误: {err}")
                raise
            finally:
                cursor.close()


# 全局数据库实例
db = Database()