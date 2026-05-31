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

# NOTE: 这个模块实现了一个用户认证系统，使用Flask和Flask-JWT-Extended来处理用户注册、登录、登出、Token刷新和获取当前用户信息等功能。用户信息存储在SQLite数据库中，密码使用Werkzeug的安全哈希函数进行加密。该模块还实现了一个简单的Token黑名单机制来处理用户登出后的Token撤销。

# NOTE: 缺少维护者
"""
用户认证 API 蓝图模块
提供基于 JWT 的统一认证功能：登录、注册、登出、Token刷新、获取用户信息
"""

import logging
from datetime import timedelta
from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from werkzeug.security import generate_password_hash, check_password_hash
import genggai
from utils.api_response import success_response, error_response

try:
    from utils.db import get_db
except ImportError:
    import sqlite3

    DATABASE = "sbox.db"

    def get_db():
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn


logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

try:
    from utils.db import get_db

    db = get_db()
    db.execute(
        "CREATE TABLE IF NOT EXISTS token_blacklist (jti TEXT PRIMARY KEY, created_at INTEGER)"
    )
    db.commit()
except Exception:
    pass

TOKEN_BLACKLIST = set()


# NOTE:从数据库加载Token黑名单到内存
def _load_blacklist_from_db():
    try:
        with get_db() as conn:
            rows = conn.execute("SELECT jti FROM token_blacklist").fetchall()
            for row in rows:
                TOKEN_BLACKLIST.add(row["jti"])
    except Exception:
        pass


_load_blacklist_from_db()

ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRES = timedelta(days=7)


# NOTE:检查JWT Token是否已被撤销（黑名单回调）
def is_token_revoked(jwt_header, jwt_payload):
    """检查 JWT token 是否已被撤销"""
    jti = jwt_payload.get("jti")
    return jti in TOKEN_BLACKLIST


# NOTE:用户注册接口，接受用户名密码邮箱，返回JWT Token
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    用户注册接口
    接受 JSON: {"username": "...", "password": "...", "email": "..."}
    返回 JWT tokens
    """
    try:
        data = request.get_json()

        if not data:
            return error_response("请求数据不能为空", 400)

        username = data.get("username", "").strip()
        password = data.get("password", "")
        email = data.get("email", "").strip()

        if not username or not password or not email:
            return error_response("用户名、密码和邮箱不能为空", 400)

        if len(username) < 3 or len(username) > 20:
            return error_response("用户名长度必须在3-20个字符之间", 400)

        if len(password) < 8:
            return error_response("密码长度必须至少为8位", 400)

        import re

        if not re.search(r"\d", password):
            return error_response("密码必须包含至少一个数字", 400)
        if not re.search(r"[a-zA-Z]", password):
            return error_response("密码必须包含至少一个字母", 400)

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return error_response("邮箱格式不正确", 400)

        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()

            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return error_response("用户名已存在", 409)

            cursor.execute("SELECT username FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return error_response("邮箱已被注册", 409)

            hashed_password = generate_password_hash(password)

            cursor.execute(
                "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                (username, hashed_password, email),
            )
            conn.commit()

            user_id = cursor.lastrowid

            access_token = create_access_token(
                identity=username, additional_claims={"user_id": user_id}
            )
            refresh_token = create_refresh_token(
                identity=username, additional_claims={"user_id": user_id}
            )

            logger.info(f"新用户注册成功: {username}")

            return success_response(
                data={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {"id": user_id, "username": username, "email": email},
                },
                message="注册成功",
                code=201,
            )

        except sqlite3.Error as e:
            logger.error(f"数据库错误: {e}")
            return error_response("数据库错误，请稍后重试", 500)
        finally:
            if conn:
                conn.close()

    except Exception as e:
        logger.error(f"注册过程发生错误: {e}")
        return error_response("服务器内部错误", 500)


# NOTE:用户登录接口，验证密码后返回JWT Access Token和Refresh Token
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    用户登录接口
    接受 JSON: {"username": "...", "password": "..."}
    返回 JWT Access Token (15分钟) 和 Refresh Token (7天)
    """
    try:
        data = request.get_json()

        if not data:
            return error_response("请求数据不能为空", 400)

        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return error_response("用户名和密码不能为空", 400)

        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, username, password, email FROM users WHERE username = ?",
                (username,),
            )
            user = cursor.fetchone()

            if not user:
                return error_response("用户名或密码错误", 401)

            user_id, db_username, db_password, db_email = user

            if not check_password_hash(db_password, password):
                return error_response("用户名或密码错误", 401)

            access_token = create_access_token(
                identity=db_username, additional_claims={"user_id": user_id}
            )
            refresh_token = create_refresh_token(
                identity=db_username, additional_claims={"user_id": user_id}
            )

            logger.info(f"用户登录成功: {username}")

            return success_response(
                data={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {"id": user_id, "username": db_username, "email": db_email},
                },
                message="登录成功",
            )

        except sqlite3.Error as e:
            logger.error(f"数据库错误: {e}")
            return error_response("数据库错误，请稍后重试", 500)
        finally:
            if conn:
                conn.close()

    except Exception as e:
        logger.error(f"登录过程发生错误: {e}")
        return error_response("服务器内部错误", 500)


# NOTE:用户登出接口，将当前JWT Token加入黑名单
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    用户登出接口
    将当前 JWT token 加入黑名单
    """
    try:
        jti = get_jwt().get("jti")
        if jti:
            TOKEN_BLACKLIST.add(jti)
            try:
                with get_db() as conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO token_blacklist (jti, created_at) VALUES (?, ?)",
                        (jti, int(__import__("time").time())),
                    )
                    conn.commit()
            except Exception:
                pass
            username = get_jwt_identity()
            logger.info(f"用户登出: {username}")
            return success_response(message="登出成功")
        else:
            return error_response("无效的 Token", 400)

    except Exception as e:
        logger.error(f"登出过程发生错误: {e}")
        return error_response("服务器内部错误", 500)


# NOTE:刷新Access Token接口，使用Refresh Token获取新Token
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    刷新 Access Token 接口
    使用 Refresh Token 获取新的 Access Token
    """
    try:
        username = get_jwt_identity()
        claims = get_jwt()
        user_id = claims.get("user_id")

        if not username:
            return error_response("无效的 Token", 401)

        new_access_token = create_access_token(
            identity=username, additional_claims={"user_id": user_id}
        )

        logger.info(f"刷新 Access Token: {username}")

        return success_response(data={"access_token": new_access_token}, message="Token 刷新成功")

    except Exception as e:
        logger.error(f"刷新 Token 发生错误: {e}")
        return error_response("服务器内部错误", 500)


# NOTE:获取当前登录用户信息，需要JWT认证
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """
    获取当前用户信息接口
    需要 JWT 认证
    返回用户信息
    """
    try:
        username = get_jwt_identity()
        claims = get_jwt()
        user_id = claims.get("user_id")

        if not username:
            return error_response("无效的 Token", 401)

        user_email = genggai.caxu(username, 4)

        return success_response(
            data={"id": user_id, "username": username, "email": user_email},
            message="获取用户信息成功",
        )

    except Exception as e:
        logger.error(f"获取用户信息发生错误: {e}")
        return error_response("服务器内部错误", 500)


# NOTE:验证JWT Token有效性接口
@auth_bp.route("/verify", methods=["GET"])
@jwt_required()
def verify_token():
    """
    验证 Token 有效性接口
    """
    try:
        username = get_jwt_identity()
        return success_response(data={"valid": True, "username": username}, message="Token 有效")
    except Exception as e:
        logger.error(f"验证 Token 发生错误: {e}")
        return error_response("Token 无效或已过期", 401)
