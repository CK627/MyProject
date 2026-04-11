"""
数据库迁移脚本 - 为 users 表添加 OAuth 和密码重置相关字段

在已有数据库上运行此脚本以添加新字段，而无需删除表重建。
使用方法: python -m backend.add_auth_columns
或者: cd backend && python add_auth_columns.py
"""

import pymysql
from app.config import settings


def migrate():
    conn = pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        charset="utf8mb4",
    )

    cursor = conn.cursor()

    # 查询 users 表现有列
    cursor.execute("SHOW COLUMNS FROM users")
    existing_columns = {row[0] for row in cursor.fetchall()}

    migrations = []

    if "github_id" not in existing_columns:
        migrations.append(
            "ALTER TABLE users ADD COLUMN github_id VARCHAR(100) NULL UNIQUE"
        )
        migrations.append(
            "CREATE INDEX idx_users_github_id ON users(github_id)"
        )

    if "password_reset_token" not in existing_columns:
        migrations.append(
            "ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(255) NULL"
        )

    if "password_reset_expires" not in existing_columns:
        migrations.append(
            "ALTER TABLE users ADD COLUMN password_reset_expires DATETIME NULL"
        )

    # 将 password_hash 改为可空（OAuth 用户无密码）
    cursor.execute(
        "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'password_hash'",
        (settings.DB_NAME,),
    )
    row = cursor.fetchone()
    if row and row[0] == "NO":
        migrations.append(
            "ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255) NULL"
        )

    if not migrations:
        print("数据库已是最新状态，无需迁移。")
    else:
        for sql in migrations:
            print(f"执行: {sql}")
            cursor.execute(sql)
        conn.commit()
        print(f"迁移完成，共执行 {len(migrations)} 条语句。")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    migrate()
