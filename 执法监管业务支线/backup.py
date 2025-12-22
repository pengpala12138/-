# -*- coding: utf-8 -*-
"""
执法监管业务线自动备份脚本（最终稳定版）
修复：指定 mysqldump 绝对路径、移除冗余表名、添加错误日志、适配数据库设计文档
"""
import subprocess
import os
import time
import shutil
from datetime import datetime, timedelta

# 数据库配置（与数据库设计文档、app.py一致）
DB_CONFIG = {
    "host": "10.152.230.97",
    "user": "zyj",
    "password": "515408",
    "database": "sjk",
    "port": 3306
}

# 备份路径配置（自动适配脚本所在目录）
script_dir = os.path.dirname(os.path.abspath(__file__))
BACKUP_CONFIG = {
    "local_backup": os.path.join(script_dir, "backup"),  # 备份根目录
    "remote_path": r"\\192.168.43.100\backup\law_enforcement",  # 异地存储（可选）
    "retention_days": 30,  # 备份保留天数
    "log_file": os.path.join(script_dir, "backup.log")  # 错误日志文件
}

# 需备份的核心表（仅保留数据库设计文档中明确的执法监管业务线表，避免冗余）
BACKUP_TABLES = [
    "law_enforcer",  # app.py中引用的执法人员表
    "illegal_record", "illegal_monitor_rel",  # app.py中引用的非法行为相关表
    "law_dispatch", "video_monitor", "region_info"  # app.py中核心表
]


def init_backup_env():
    """初始化备份环境：创建目录、日志文件"""
    # 创建备份目录
    if not os.path.exists(BACKUP_CONFIG["local_backup"]):
        os.makedirs(BACKUP_CONFIG["local_backup"])
        print(f"✅ 创建备份目录：{BACKUP_CONFIG['local_backup']}")

    # 创建日志文件
    if not os.path.exists(BACKUP_CONFIG["log_file"]):
        with open(BACKUP_CONFIG["log_file"], "w", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 备份日志初始化\n")
        print(f"✅ 创建日志文件：{BACKUP_CONFIG['log_file']}")


def write_log(content):
    """写入日志（含时间戳）"""
    log_content = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {content}\n"
    with open(BACKUP_CONFIG["log_file"], "a", encoding="utf-8") as f:
        f.write(log_content)
    print(log_content.strip())


def get_mysqldump_path():
    """获取 mysqldump 绝对路径（适配 Windows 常见安装路径）"""
    # 常见 MySQL 安装路径（可根据实际情况修改）
    common_paths = [
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 5.7\bin\mysqldump.exe",
        r"D:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        r"C:\ProgramData\MySQL\MySQL Server 8.0\bin\mysqldump.exe"
    ]

    # 优先使用系统环境变量中的 mysqldump
    for path in common_paths:
        if os.path.exists(path):
            write_log(f"找到 mysqldump 路径：{path}")
            return path

    # 若未找到，提示用户手动配置
    write_log("⚠️  未自动找到 mysqldump.exe，请手动配置路径")
    return input(
        "请输入 mysqldump.exe 的绝对路径（如 C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\mysqldump.exe）：").strip()


def execute_full_backup():
    """执行全量备份（含错误捕获与日志）"""
    # 生成备份文件名
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_CONFIG["local_backup"], f"{date_str}_full.sql")

    # 获取 mysqldump 路径
    mysqldump_path = get_mysqldump_path()
    if not os.path.exists(mysqldump_path):
        write_log(f"❌ mysqldump 路径不存在：{mysqldump_path}")
        return None

    # 构造备份命令（简化参数，避免语法错误）
    cmd = [
        f'"{mysqldump_path}"',  # 路径含空格，需加引号
        f"-h{DB_CONFIG['host']}",
        f"-u{DB_CONFIG['user']}",
        f"-p{DB_CONFIG['password']}",
        f"-P{DB_CONFIG['port']}",
        DB_CONFIG["database"],
        "--tables", *BACKUP_TABLES,
        "--lock-tables=false",
        "--default-character-set=utf8mb4",
        "--skip-triggers",
        ">",
        f'"{backup_file}"'  # 输出文件路径含空格，加引号
    ]

    cmd_str = " ".join(cmd)
    write_log(f"执行备份命令：{cmd_str}")

    try:
        # 执行命令，捕获输出日志
        result = subprocess.run(
            cmd_str, shell=True, check=True,
            capture_output=True, text=True, encoding="gbk"  # Windows 用 gbk 编码
        )
        write_log(f"✅ 全量备份完成：{os.path.basename(backup_file)}")

        # 验证备份文件有效性
        if os.path.getsize(backup_file) > 100:  # 大于100字节视为有效
            # 同步到异地存储（可选）
            sync_to_remote(backup_file)
            return backup_file
        else:
            os.remove(backup_file)
            write_log(f"❌ 备份文件无效（为空或过小），已删除：{os.path.basename(backup_file)}")
            return None
    except subprocess.CalledProcessError as e:
        # 捕获命令执行错误
        error_msg = f"备份命令执行失败：返回码 {e.returncode}，错误信息：{e.stderr}"
        write_log(f"❌ {error_msg}")
        # 清理无效文件
        if os.path.exists(backup_file):
            os.remove(backup_file)
        return None
    except Exception as e:
        write_log(f"❌ 备份异常：{str(e)}")
        if os.path.exists(backup_file):
            os.remove(backup_file)
        return None


def sync_to_remote(local_file):
    """同步到异地存储（可选）"""
    if not os.path.exists(BACKUP_CONFIG["remote_path"]):
        write_log(f"⚠️  异地存储路径不存在：{BACKUP_CONFIG['remote_path']}")
        return

    try:
        shutil.copy2(local_file, BACKUP_CONFIG["remote_path"])
        write_log(f"✅ 同步到异地存储：{os.path.basename(local_file)}")
    except Exception as e:
        write_log(f"⚠️  异地同步失败：{str(e)}")


def clean_expired_backup():
    """清理超期备份文件"""
    backup_dir = BACKUP_CONFIG["local_backup"]
    for file in os.listdir(backup_dir):
        file_path = os.path.join(backup_dir, file)
        if os.path.isfile(file_path) and file.endswith("_full.sql"):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if datetime.now() - file_mtime > timedelta(days=BACKUP_CONFIG["retention_days"]):
                os.remove(file_path)
                write_log(f"🗑️ 删除超期备份：{file}")


def main():
    """执行入口"""
    print("=" * 60)
    print("开始执法监管业务线数据备份任务...")
    print("=" * 60)

    # 初始化环境
    init_backup_env()

    # 执行备份
    execute_full_backup()

    # 清理超期文件
    clean_expired_backup()

    print("\n🎉 备份任务执行完成！")
    print(f"📁 备份文件存储路径：{BACKUP_CONFIG['local_backup']}")
    print(f"📜 日志文件路径：{BACKUP_CONFIG['log_file']}")
    print(f"💾 已保留最近{BACKUP_CONFIG['retention_days']}天备份")


if __name__ == "__main__":
    main()