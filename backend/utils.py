# backend/utils.py
import os
import pymysql
from .config import DB_CONFIG

# 获取database文件夹下的SQL文件路径（适配你的目录结构）
def get_sql_file_path(filename):
    # 拼接路径：项目根目录/database/xxx.sql
    # ../../ 表示从backend/回退到项目根目录，再进入database/
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", filename)

# 执行SQL脚本（创建表+插入测试数据）
def execute_sql_script(filename):
    # 1. 连接MySQL
    conn = pymysql.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        db=DB_CONFIG["db"],
        port=DB_CONFIG["port"],
        charset=DB_CONFIG["charset"]
    )
    cursor = conn.cursor()

    # 2. 读取SQL文件
    sql_path = get_sql_file_path(filename)
    with open(sql_path, "r", encoding="utf8") as f:
        sql_scripts = f.read().split(";")  # 按分号分割SQL

    # 3. 执行SQL（跳过注释和空行）
    for sql in sql_scripts:
        sql = sql.strip()
        if sql and not sql.startswith("--"):
            try:
                cursor.execute(sql)
                conn.commit()
                print(f"执行成功：{sql[:50]}...")
            except Exception as e:
                conn.rollback()
                print(f"执行失败：{e} | {sql[:50]}...")

    # 4. 关闭连接
    cursor.close()
    conn.close()
    print(f"脚本 {filename} 执行完成！")