#!/usr/bin/env python3
"""
数据备份脚本
每日增量备份，每周全量备份
"""

import os
import sys
import datetime
import subprocess
import logging
import gzip
import shutil
from pathlib import Path

# 配置
CONFIG = {
    'mysql_host': '172.20.10.4',
    'mysql_port': 3306,
    'mysql_user': 'fxt',
    'mysql_password': '515408',
    'database': 'sjk',
    'backup_dir': '/backup/mysql',  # 备份存储路径
    'keep_days': 30,  # 保留天数
    'log_file': '/var/log/mysql_backup.log'
}

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG['log_file']),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def ensure_backup_dir():
    """确保备份目录存在"""
    backup_dir = Path(CONFIG['backup_dir'])
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建备份目录: {backup_dir}")

    # 创建子目录
    full_backup_dir = backup_dir / 'full'
    incremental_backup_dir = backup_dir / 'incremental'
    full_backup_dir.mkdir(exist_ok=True)
    incremental_backup_dir.mkdir(exist_ok=True)

    return full_backup_dir, incremental_backup_dir


def execute_sql(sql):
    """执行SQL语句"""
    cmd = [
        'mysql',
        f'-h{CONFIG["mysql_host"]}',
        f'-P{CONFIG["mysql_port"]}',
        f'-u{CONFIG["mysql_user"]}',
        f'-p{CONFIG["mysql_password"]}',
        CONFIG['database'],
        '-e', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"SQL执行失败: {e.stderr}")
        return None


def full_backup():
    """执行全量备份"""
    logger.info("开始全量备份...")

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"{CONFIG['backup_dir']}/full/full_backup_{timestamp}.sql.gz"

    # 执行mysqldump
    cmd = [
        'mysqldump',
        f'-h{CONFIG["mysql_host"]}',
        f'-P{CONFIG["mysql_port"]}',
        f'-u{CONFIG["mysql_user"]}',
        f'-p{CONFIG["mysql_password"]}',
        '--single-transaction',
        '--routines',
        '--triggers',
        '--events',
        CONFIG['database']
    ]

    try:
        # 压缩备份
        with gzip.open(backup_file, 'wb') as f:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

            while True:
                chunk = process.stdout.read(1024)
                if not chunk:
                    break
                f.write(chunk)

            process.wait()

        if process.returncode == 0:
            file_size = os.path.getsize(backup_file) / (1024 * 1024)  # MB
            logger.info(f"全量备份完成: {backup_file} ({file_size:.2f} MB)")

            # 记录备份日志到数据库
            log_sql = f"""
            INSERT INTO backup_logs 
            (backup_type, backup_path, file_size, status, start_time, end_time, message)
            VALUES ('full', '{backup_file}', {file_size}, 'success', 
                    '{datetime.datetime.now()}', '{datetime.datetime.now()}', 
                    '全量备份成功');
            """
            execute_sql(log_sql)

            return backup_file
        else:
            logger.error("全量备份失败")
            return None

    except Exception as e:
        logger.error(f"全量备份异常: {str(e)}")
        return None


def incremental_backup():
    """执行增量备份"""
    logger.info("开始增量备份...")

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"{CONFIG['backup_dir']}/incremental/inc_backup_{timestamp}.sql.gz"

    # 获取上次备份后的binlog位置（如果有）
    last_backup_sql = """
                      SELECT MAX(end_time) \
                      FROM backup_logs
                      WHERE backup_type = 'incremental' \
                        AND status = 'success'; \
                      """

    result = execute_sql(last_backup_sql)
    last_backup_time = None
    if result:
        lines = result.strip().split('\n')
        if len(lines) > 1:
            last_backup_time = lines[1]

    # 执行增量备份
    cmd = [
        'mysqldump',
        f'-h{CONFIG["mysql_host"]}',
        f'-P{CONFIG["mysql_port"]}',
        f'-u{CONFIG["mysql_user"]}',
        f'-p{CONFIG["mysql_password"]}',
        '--single-transaction',
        '--where=updated_at>="' + (last_backup_time or '2000-01-01') + '"' if last_backup_time else '',
        CONFIG['database']
    ]

    try:
        # 压缩备份
        with gzip.open(backup_file, 'wb') as f:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

            while True:
                chunk = process.stdout.read(1024)
                if not chunk:
                    break
                f.write(chunk)

            process.wait()

        if process.returncode == 0:
            file_size = os.path.getsize(backup_file) / (1024 * 1024)  # MB
            logger.info(f"增量备份完成: {backup_file} ({file_size:.2f} MB)")

            # 记录备份日志到数据库
            log_sql = f"""
            INSERT INTO backup_logs 
            (backup_type, backup_path, file_size, status, start_time, end_time, message)
            VALUES ('incremental', '{backup_file}', {file_size}, 'success', 
                    '{datetime.datetime.now()}', '{datetime.datetime.now()}', 
                    '增量备份成功');
            """
            execute_sql(log_sql)

            return backup_file
        else:
            logger.error("增量备份失败")
            return None

    except Exception as e:
        logger.error(f"增量备份异常: {str(e)}")
        return None


def cleanup_old_backups():
    """清理旧备份文件"""
    logger.info("清理旧备份文件...")

    backup_dir = Path(CONFIG['backup_dir'])
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=CONFIG['keep_days'])

    deleted_count = 0
    for backup_type in ['full', 'incremental']:
        type_dir = backup_dir / backup_type
        if type_dir.exists():
            for file_path in type_dir.glob('*.sql.gz'):
                file_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"删除旧备份: {file_path}")
                    except Exception as e:
                        logger.error(f"删除失败 {file_path}: {str(e)}")

    logger.info(f"清理完成，删除 {deleted_count} 个旧备份文件")


def restore_database(backup_file, is_incremental=False):
    """
    恢复数据库
    """
    logger.info(f"开始恢复数据库: {backup_file}")

    # 解压并恢复
    try:
        # 解压备份文件
        temp_file = '/tmp/temp_restore.sql'
        with gzip.open(backup_file, 'rb') as f_in:
            with open(temp_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # 如果是增量恢复，先恢复最近的全量备份
        if is_incremental:
            # 查找最新的全量备份
            full_backup_dir = Path(CONFIG['backup_dir']) / 'full'
            full_backups = list(full_backup_dir.glob('*.sql.gz'))
            if full_backups:
                latest_full = max(full_backups, key=lambda x: x.stat().st_mtime)
                logger.info(f"先恢复全量备份: {latest_full}")
                restore_database(str(latest_full), is_incremental=False)

        # 执行恢复
        cmd = [
            'mysql',
            f'-h{CONFIG["mysql_host"]}',
            f'-P{CONFIG["mysql_port"]}',
            f'-u{CONFIG["mysql_user"]}',
            f'-p{CONFIG["mysql_password"]}',
            CONFIG['database']
        ]

        with open(temp_file, 'r') as f:
            process = subprocess.Popen(cmd, stdin=f)
            process.wait()

        if process.returncode == 0:
            logger.info("数据库恢复成功")

            # 清理临时文件
            os.remove(temp_file)

            # 记录恢复日志
            log_sql = f"""
            INSERT INTO system_logs 
            (log_type, module, message, created_at)
            VALUES ('info', 'backup', 
                    '数据库恢复成功，文件: {backup_file}', 
                    '{datetime.datetime.now()}');
            """
            execute_sql(log_sql)

            return True
        else:
            logger.error("数据库恢复失败")
            return False

    except Exception as e:
        logger.error(f"恢复异常: {str(e)}")
        return False


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始数据备份任务")

    # 确保备份目录存在
    ensure_backup_dir()

    today = datetime.datetime.now()

    try:
        # 每周日执行全量备份
        if today.weekday() == 6:  # 6代表周日
            logger.info("周日执行全量备份")
            backup_file = full_backup()
            if backup_file:
                logger.info("全量备份成功")
            else:
                logger.error("全量备份失败")
        else:
            # 其他日期执行增量备份
            logger.info("执行增量备份")
            backup_file = incremental_backup()
            if backup_file:
                logger.info("增量备份成功")
            else:
                logger.error("增量备份失败")

        # 清理旧备份
        cleanup_old_backups()

        logger.info("备份任务完成")

    except Exception as e:
        logger.error(f"备份任务异常: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    # 示例恢复使用（需要时取消注释）
    # restore_database('/backup/mysql/full/full_backup_20231201_120000.sql.gz', is_incremental=False)

    # 正常执行备份
    main()