# Copyright (C) 2026 小盒子社区
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# NOTE: 这个模块负责生成和验证邮箱验证码，使用SQLite数据库存储验证码信息

import sqlite3
import time
import secrets
import string
import os

VERIFICATION_DB = os.environ.get("SQLITE_DB", "sbox.db")
TABLE_NAME = "verification_codes"


# NOTE:初始化验证码数据库表
def init_verification_db():
    """Initialize the verification codes database"""
    conn = sqlite3.connect(VERIFICATION_DB)
    cursor = conn.cursor()

    # Create table for verification codes
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            email TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# NOTE:生成安全的随机数字验证码
def generate_verification_code(length=6):
    """Generate a cryptographically secure random verification code"""
    return "".join(secrets.choice(string.digits) for _ in range(length))


# NOTE:存储验证码并设置过期时间
def store_verification_code(email, code, expiry_minutes=10):
    """Store a verification code with expiry time"""
    conn = sqlite3.connect(VERIFICATION_DB)
    cursor = conn.cursor()

    current_time = int(time.time())
    expiry_time = current_time + (expiry_minutes * 60)  # Convert minutes to seconds

    # Insert or replace the verification code
    cursor.execute(
        f"""
        INSERT OR REPLACE INTO {TABLE_NAME} 
        (email, code, created_at, expires_at) 
        VALUES (?, ?, ?, ?)
    """,
        (email, code, current_time, expiry_time),
    )

    conn.commit()
    conn.close()


# NOTE:验证邮箱验证码是否有效
def validate_verification_code(email, code):
    """Validate a verification code for an email"""
    conn = sqlite3.connect(VERIFICATION_DB)
    cursor = conn.cursor()

    current_time = int(time.time())

    # Get the stored code for the email
    cursor.execute(
        f"""
        SELECT code, expires_at FROM {TABLE_NAME} 
        WHERE email = ?
    """,
        (email,),
    )

    result = cursor.fetchone()
    conn.close()

    if not result:
        return False  # No code found for this email

    stored_code, expiry_time = result

    # Check if code has expired
    if current_time > expiry_time:
        # Delete expired code
        delete_verification_code(email)
        return False

    # Check if code matches
    return stored_code == code


# NOTE:删除邮箱的验证码
def delete_verification_code(email):
    """Delete a verification code for an email"""
    conn = sqlite3.connect(VERIFICATION_DB)
    cursor = conn.cursor()

    cursor.execute(
        f"""
        DELETE FROM {TABLE_NAME} 
        WHERE email = ?
    """,
        (email,),
    )

    conn.commit()
    conn.close()
