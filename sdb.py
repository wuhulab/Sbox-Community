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

# NOTE: 这个模块负责提供一个简单的键值存储接口，使用SQLite数据库来存储数据。它提供了基本的增删改查功能，并且支持通过正则表达式搜索内容。

import sqlite3
import os
import re
import logging

logger = logging.getLogger(__name__)

SQLITE_DB = os.environ.get("SQLITE_DB", "production.db")
TABLE_NAME = "kv_store"


# ========================
# 工具函数：连接数据库
# ========================
# NOTE:获取SQLite数据库连接
def _get_sqlite_connection():
    try:
        return sqlite3.connect(SQLITE_DB)
    except Exception as e:
        logger.error("连接数据库失败: %s", e)
        return None


# NOTE:从文件名提取source标签（去掉.sdb后缀）
def _sdb_to_source(sdb_file):
    """提取 sdb 文件名作为 source 标签（去掉 .sdb）"""
    if sdb_file.endswith(".sdb"):
        return os.path.splitext(os.path.basename(sdb_file))[0]
    return os.path.basename(sdb_file)


# ========================
# up(sdb_file, var_name) → 改为从 SQLite 查询
# ========================
# NOTE:获取变量值（从SQLite读取）
def up(sdb_file, var_name):
    """
    获取变量名的值（从 SQLite 中读取）

    :param sdb_file: 数据库文件名 (例如 xx.sdb)，用于确定 source
    :param var_name: 变量名
    :return: 变量值，如果找不到则返回 ""
    """
    source = _sdb_to_source(sdb_file)

    conn = _get_sqlite_connection()
    if not conn:
        logger.warning("文件 %s 不存在（SQLite 连接失败）", sdb_file)
        return ""

    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT value FROM {TABLE_NAME} WHERE source = ? AND key = ?",
            (source, var_name),
        )
        row = cursor.fetchone()
        conn.close()

        value = row[0] if row else ""
        return value

    except Exception as e:
        logger.error("查询数据库出错: %s", e)
        conn.close()
        return ""


# ========================
# down(sdb_file, var_name, value) → 写入 SQLite
# ========================
# NOTE:存储变量值到SQLite
def down(sdb_file, var_name, value):
    """
    上传变量名的数据到 SQLite

    :param sdb_file: 数据库文件名
    :param var_name: 变量名
    :param value: 需要上传的值
    """
    source = _sdb_to_source(sdb_file)

    conn = _get_sqlite_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        # 创建表（以防万一）
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                source TEXT NOT NULL
            )
        """)
        # 插入或替换
        cursor.execute(
            f"""
            INSERT OR REPLACE INTO {TABLE_NAME} (key, value, source)
            VALUES (?, ?, ?)
        """,
            (var_name, str(value), source),
        )
        conn.commit()
        conn.close()
        logger.debug("变量 %s 已上传", var_name)
    except Exception as e:
        logger.error("写入数据库失败: %s", e)
        conn.close()


# ========================
# search(sdb_file, search_str) → 搜索 key 包含字符串（忽略 _）
# ========================
# NOTE:搜索变量名（跳过带下划线的变量）
def search(sdb_file, search_str):
    """
    搜索所有变量名，输出包含指定字符串的变量名（跳过带有 '_' 的变量）
    """
    source = _sdb_to_source(sdb_file)

    conn = _get_sqlite_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT key FROM {TABLE_NAME} WHERE source = ?", (source,))
        rows = cursor.fetchall()
        conn.close()

        result = []
        for (var_name,) in rows:
            if search_str in var_name and "_" not in var_name:
                result.append(var_name)
        return result

    except Exception as e:
        logger.error("搜索出错: %s", e)
        conn.close()
        return []


# ========================
# delete(sdb_file, var_name) → 删除某 key
# ========================
# NOTE:删除指定变量
def delete(sdb_file, var_name):
    """
    删除指定的变量名
    """
    source = _sdb_to_source(sdb_file)

    conn = _get_sqlite_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE source = ? AND key = ?", (source, var_name))
        if cursor.rowcount == 0:
            logger.warning("变量 %s 不存在，删除失败", var_name)
        else:
            conn.commit()
            logger.debug("变量 %s 已删除", var_name)
        conn.close()
    except Exception as e:
        logger.error("删除失败: %s", e)
        conn.close()


# ========================
# search_by_content_and_filter(sdb_file, pattern, filter_str)
# 只返回变量名包含 "作品名称_id_" 的内容，并提取 id
# ========================
# NOTE:安全编译正则表达式，失败则转义
def _safe_regex(pattern):
    try:
        return re.compile(pattern, re.DOTALL)
    except re.error:
        return re.compile(re.escape(pattern))


# NOTE:按内容搜索，只返回作品名称_id_的变量
def search_by_content_and_filter(sdb_file, pattern, filter_str="666"):
    source = _sdb_to_source(sdb_file)

    conn = _get_sqlite_connection()
    if not conn:
        return []

    try:
        regex = _safe_regex(pattern)
        cursor = conn.cursor()
        cursor.execute(f"SELECT key, value FROM {TABLE_NAME} WHERE source = ?", (source,))
        rows = cursor.fetchall()
        conn.close()

        result = []
        for var_name, content in rows:
            if not isinstance(content, str):
                continue
            if regex.search(content) and filter_str in content and "作品名称_id_" in var_name:
                match = re.search(r"作品名称_id_(\d+)", var_name)
                if match:
                    result.append((var_name, content, match.group(1)))
        return result

    except Exception as e:
        logger.error("搜索内容出错: %s", e)
        return []


# ========================
# search_by_content(sdb_file, pattern, filter_str)
# 搜索内容匹配正则且包含 filter_str 的项
# ========================
# NOTE:按内容搜索，匹配正则和过滤字符串
def search_by_content(sdb_file, pattern, filter_str="666"):
    source = _sdb_to_source(sdb_file)

    conn = _get_sqlite_connection()
    if not conn:
        return []

    try:
        regex = _safe_regex(pattern)
        cursor = conn.cursor()
        cursor.execute(f"SELECT key, value FROM {TABLE_NAME} WHERE source = ?", (source,))
        rows = cursor.fetchall()
        conn.close()

        result = []
        for var_name, content in rows:
            if isinstance(content, str) and regex.search(content) and filter_str in content:
                result.append((var_name, content, var_name))
        return result

    except Exception as e:
        logger.error("发生错误: %s", e)
        return []
