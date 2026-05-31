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

import os
from contextlib import contextmanager

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "sqlite")

if DATABASE_TYPE == "postgresql":
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
    import psycopg2.extras

    DB_CONFIG = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", 5432)),
        "database": os.environ.get("DB_NAME", "sbox"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
    }

    connection_pool = None

    def init_connection_pool():
        global connection_pool
        if connection_pool is None:
            min_conn = 1
            max_conn = int(os.environ.get("DB_MAX_CONN", 10))
            connection_pool = ThreadedConnectionPool(min_conn, max_conn, **DB_CONFIG)

    def get_connection():
        if connection_pool is None:
            init_connection_pool()
        return connection_pool.getconn()

    def release_connection(conn):
        if connection_pool:
            connection_pool.putconn(conn)

    @contextmanager
    def get_db():
        conn = get_connection()
        conn.autocommit = True
        try:
            yield conn
        finally:
            release_connection(conn)

    def query_all(query, params=None):
        if connection_pool is None:
            init_connection_pool()
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        finally:
            release_connection(conn)

    def query_one(query, params=None):
        results = query_all(query, params)
        return results[0] if results else None

    def execute(query, params=None):
        if connection_pool is None:
            init_connection_pool()
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                conn.commit()
        finally:
            release_connection(conn)

    def init_db():
        if connection_pool is None:
            init_connection_pool()
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cloud_vars (
                        project_id TEXT NOT NULL,
                        var_name TEXT NOT NULL,
                        var_value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (project_id, var_name)
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        shenfen TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        totp_secret TEXT,
                        zerocat_openid TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS classtap_data (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title TEXT NOT NULL,
                        cards_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS update_classtap_updated_at
                    AFTER UPDATE ON classtap_data
                    FOR EACH ROW
                    BEGIN
                        UPDATE classtap_data SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                    END
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS oauth_clients (
                        id SERIAL PRIMARY KEY,
                        client_id TEXT UNIQUE NOT NULL,
                        client_secret TEXT NOT NULL,
                        redirect_uri TEXT NOT NULL
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auth_codes (
                        id SERIAL PRIMARY KEY,
                        code TEXT UNIQUE NOT NULL,
                        client_id TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        redirect_uri TEXT NOT NULL,
                        scope TEXT,
                        expires_at INTEGER NOT NULL
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS access_tokens (
                        token TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        client_id TEXT NOT NULL,
                        scope TEXT,
                        expires_at INTEGER NOT NULL
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS refresh_tokens (
                        token TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        client_id TEXT NOT NULL,
                        scope TEXT,
                        expires_at INTEGER NOT NULL
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS kv_store (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        source TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS verification_codes (
                        email TEXT PRIMARY KEY,
                        code TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        expires_at INTEGER NOT NULL
                    )
                """)

                conn.commit()
        finally:
            release_connection(conn)

else:
    import sqlite3

    DATABASE = os.environ.get("SQLITE_DB", "sbox.db")

    # NOTE:获取SQLite数据库连接
    def get_db():
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn

    # NOTE:查询所有匹配的记录
    def query_all(query, params=None):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchall()

    # NOTE:查询单条记录
    def query_one(query, params=None):
        results = query_all(query, params)
        return results[0] if results else None

    # NOTE:执行SQL写入操作（INSERT/UPDATE/DELETE）
    def execute(query, params=None):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()

    # NOTE:初始化数据库，创建所有必要的表
    def init_db():
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cloud_vars (
                    project_id TEXT NOT NULL,
                    var_name TEXT NOT NULL,
                    var_value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (project_id, var_name)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    shenfen TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    totp_secret TEXT,
                    zerocat_openid TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS classtap_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    cards_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_classtap_updated_at
                AFTER UPDATE ON classtap_data
                FOR EACH ROW
                BEGIN
                    UPDATE classtap_data SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT UNIQUE NOT NULL,
                    client_secret TEXT NOT NULL,
                    redirect_uri TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auth_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    client_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    redirect_uri TEXT NOT NULL,
                    scope TEXT,
                    expires_at INTEGER NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS access_tokens (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    client_id TEXT NOT NULL,
                    scope TEXT,
                    expires_at INTEGER NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    client_id TEXT NOT NULL,
                    scope TEXT,
                    expires_at INTEGER NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS verification_codes (
                    email TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                )
            """)

            conn.commit()

    # NOTE:备份SQLite数据库文件
    def backup_database(backup_path):
        import shutil

        shutil.copy2(DATABASE, backup_path)
