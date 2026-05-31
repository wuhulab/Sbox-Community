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

import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DATABASE = os.environ.get("SQLITE_DB", "sbox.db")


# NOTE:查询用户信息，number指定字段索引
def caxu(username, number):
    """查询用户信息"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user:
        result = user[number]
        conn.close()
        return result
    else:
        logger.warning("用户不存在")
        conn.close()
        return None


# NOTE:根据邮箱获取用户名
def get_username_by_email(email):
    """通过邮箱精确查询用户名"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 验证email字段存在性
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            if "email" not in columns or "username" not in columns:
                raise ValueError("表结构缺少必要字段")

            # 精确查询
            cursor.execute("SELECT username FROM users WHERE email = ? LIMIT 1", (email,))
            result = cursor.fetchone()
            return result["username"] if result else None

    except Exception as e:
        logger.error("查询错误: %s", e)
        return None


# 允许更新的字段白名单
ALLOWED_COLUMNS = {
    "password",
    "email",
    "shenfen",
    "totp_secret",
    "username",
    "avatar",
    "bio",
    "website",
    "email_verified",
    "created_at",
    "last_login",
}


# 更改数据库
# NOTE:更新用户信息，指定字段名和值
def update_user(username, number, text, ziduan):
    """更新用户信息"""
    conn = None
    try:
        if ziduan not in ALLOWED_COLUMNS:
            raise ValueError(f"不允许更新字段: {ziduan}")
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {ziduan} = ? WHERE username = ?", (text, username))
        conn.commit()
        # 确保更新
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user:
            return user[number]
        else:
            logger.warning("用户不存在")
            return None
    except Exception as e:
        logger.error("更新用户失败: %s", e)
        return None
    finally:
        # 确保关闭连接
        if conn:
            conn.close()
