# -*- coding: utf-8 -*-
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

"""
用户信息 API V1 版本蓝图模块
提供用户信息的查看、修改、作品列表、收藏列表等功能接口
"""

import logging
import ast
import markdown
import bleach
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import sdb
import genggai
from utils.api_response import success_response, error_response
from werkzeug.security import generate_password_hash, check_password_hash
from utils.helpers import check_password_strength

try:
    from utils.database import get_db
except ImportError:
    import sqlite3

    DATABASE = "sbox.db"

    def get_db():
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn


logger = logging.getLogger(__name__)

user_bp = Blueprint("user", __name__, url_prefix="/api/v1/user")


# NOTE:根据用户名获取用户ID
def _get_current_user_id(username):
    """
    根据用户名获取用户ID
    :param username: 用户名
    :return: 用户ID 或 None
    """
    try:
        user_id = genggai.caxu(username, 0)
        return int(user_id) if user_id else None
    except:
        return None


# NOTE:检查用户是否为管理员
def _is_admin(username):
    """
    检查用户是否为管理员
    :param username: 用户名
    :return: True/False
    """
    try:
        user_shenfen = genggai.caxu(username, 3)
        return user_shenfen in ["站长", "高级管理员"]
    except:
        return False


# NOTE:清洗Markdown内容，防止XSS攻击
def _sanitize_markdown(content):
    """
    清洗 Markdown 内容，防止 XSS 攻击
    :param content: 原始内容
    :return: 清洗后的 HTML 内容
    """
    if not content:
        return ""
    try:
        html_content = markdown.markdown(content, extensions=["extra"])
        clean_html = bleach.clean(
            html_content,
            tags=[
                "p",
                "br",
                "strong",
                "em",
                "u",
                "strike",
                "code",
                "pre",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "ul",
                "ol",
                "li",
                "blockquote",
                "hr",
                "a",
                "img",
                "table",
                "thead",
                "tbody",
                "tr",
                "th",
                "td",
            ],
            attributes={
                "a": ["href", "title", "target"],
                "img": ["src", "alt", "title"],
                "table": ["border", "cellpadding", "cellspacing"],
            },
            protocols=["http", "https", "mailto"],
            strip=True,
        )
        return clean_html
    except:
        return content


# NOTE:获取用户信息
@user_bp.route("/<username>", methods=["GET"])
def get_user(username):
    """
    获取用户信息接口
    :param username: 用户名
    :return: 用户详细信息
    """
    user_id = _get_current_user_id(username)
    if not user_id:
        return error_response("用户不存在", 404)

    email = genggai.caxu(username, 4)
    shengfen = genggai.caxu(username, 3) or ""

    try:
        user_grade = int(sdb.up("user.sdb", "id_Grade_" + str(user_id)) or 0)
    except:
        user_grade = 0

    raw_jianjie = sdb.up("user.sdb", "id_简介_" + str(user_id)) or ""
    clean_jianjie = _sanitize_markdown(raw_jianjie)

    grby = sdb.up("user.sdb", "id_个性_" + str(user_id)) or ""

    try:
        user_works_ids = ast.literal_eval(
            sdb.up("zhuopin.sdb", "用户所有作品_id_" + str(user_id)) or "[]"
        )
    except:
        user_works_ids = []

    user_stars_str = sdb.up("zhuopin.sdb", "用户收藏_id_" + str(user_id)) or ""
    if user_stars_str:
        user_stars_ids = [x for x in user_stars_str.split(",") if x.strip()]
    else:
        user_stars_ids = []

    money = sdb.up("zhuopin.sdb", "作者金币_id_" + str(user_id)) or "0"
    try:
        money = float(money)
    except:
        money = 0.0

    show_stars = sdb.up("user.sdb", "id_收藏展示_" + str(user_id)) != "n"

    version = sdb.up("user.sdb", "id_社区版本_" + str(user_id)) or "社区版"

    avatar_url = f"/avaphoto={user_id}"

    return success_response(
        data={
            "id": user_id,
            "username": username,
            "email": email,
            "shengfen": shengfen,
            "grade": user_grade,
            "jianjie": clean_jianjie,
            "raw_jianjie": raw_jianjie,
            "gexing": grby,
            "avatar_url": avatar_url,
            "works_count": len(user_works_ids),
            "stars_count": len(user_stars_ids),
            "show_stars": show_stars,
            "money": money,
            "version": version,
        },
        message="获取用户信息成功",
    )


# NOTE:更新用户信息（修改个性签名和简介）
@user_bp.route("/<username>", methods=["PUT"])
@jwt_required()
def update_user(username):
    """
    更新用户信息接口
    需要 JWT 认证
    仅用户本人可操作
    接受 JSON: {"gexing": "...", "jianjie": "..."}
    :param username: 用户名
    :return: 更新结果
    """
    current_username = get_jwt_identity()
    claims = get_jwt()
    current_user_id = claims.get("user_id")

    if current_username != username:
        return error_response("权限不足，仅用户本人可修改信息", 403)

    data = request.get_json()
    if not data:
        return error_response("请求数据不能为空", 400)

    gexing = data.get("gexing", "").strip()
    jianjie = data.get("jianjie", "").strip()

    user_id = _get_current_user_id(username)
    if not user_id:
        return error_response("用户不存在", 404)

    try:
        if gexing:
            if len(gexing) > 100:
                return error_response("个性签名过长", 400)
            sdb.down("user.sdb", "id_个性_" + str(user_id), gexing)

        if jianjie:
            if len(jianjie) > 500:
                return error_response("个人简介过长", 400)
            sdb.down("user.sdb", "id_简介_" + str(user_id), jianjie)

        logger.info(f"用户 {username} 更新了个人信息")

        return success_response(
            data={"username": username, "gexing": gexing, "jianjie": jianjie},
            message="用户信息更新成功",
        )

    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        return error_response("更新用户信息失败", 500)


# NOTE:修改用户密码（需要JWT认证）
@user_bp.route("/<username>/password", methods=["PUT"])
@jwt_required()
def update_password(username):
    """
    修改用户密码接口
    需要 JWT 认证
    仅用户本人可操作
    接受 JSON: {"current_password": "...", "new_password": "..."}
    :param username: 用户名
    :return: 修改结果
    """
    current_username = get_jwt_identity()

    if current_username != username:
        return error_response("权限不足，仅用户本人可修改密码", 403)

    data = request.get_json()
    if not data:
        return error_response("请求数据不能为空", 400)

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return error_response("当前密码和新密码不能为空", 400)

    if not check_password_strength(new_password):
        return error_response("新密码强度不足，需要至少8位包含数字、大小写字母和特殊字符", 400)

    try:
        from utils.database import get_db
    except ImportError:
        DATABASE = "sbox.db"

        def get_db():
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            return conn

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return error_response("用户不存在", 404)

        user_id, db_password = user

        if not check_password_hash(db_password, current_password):
            conn.close()
            return error_response("当前密码错误", 401)

        hashed_password = generate_password_hash(new_password)
        cursor.execute(
            "UPDATE users SET password = ? WHERE username = ?", (hashed_password, username)
        )
        conn.commit()
        conn.close()

        logger.info(f"用户 {username} 修改了密码")

        return success_response(data={"username": username}, message="密码修改成功")
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return error_response("修改密码失败", 500)


# NOTE:获取用户作品列表（支持按类型筛选）
@user_bp.route("/<username>/works", methods=["GET"])
def get_user_works(username):
    """
    获取用户作品列表接口
    :param username: 用户名
    :param page: 页码，默认1
    :param per_page: 每页数量，默认20
    :param type: 作品类型，可选值：scratch，默认为 all
    :return: 用户作品列表
    """
    user_id = _get_current_user_id(username)
    if not user_id:
        return error_response("用户不存在", 404)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    work_type = request.args.get("type", "all")

    all_works = []

    if work_type in ["all", "scratch"]:
        try:
            scratch_works = ast.literal_eval(
                sdb.up("zhuopin.sdb", "用户所有作品_id_" + str(user_id)) or "[]"
            )
        except:
            scratch_works = []

        for work_id in scratch_works:
            title = sdb.up("zhuopin.sdb", "作品名称_id_" + str(work_id))
            if not title:
                continue
            all_works.append(
                {
                    "id": work_id,
                    "type": "scratch",
                    "title": title,
                    "author": username,
                    "views": int(sdb.up("zhuopin.sdb", "作品观看数量_id_" + str(work_id)) or 0),
                    "likes": int(sdb.up("zhuopin.sdb", "作品点赞_id_" + str(work_id)) or 0),
                    "stars": int(sdb.up("zhuopin.sdb", "作品收藏_id_" + str(work_id)) or 0),
                    "cover_url": f"/scratchphoto/{work_id}",
                    "license": sdb.up("zhuopin.sdb", "作品_id_协议_" + str(work_id)),
                    "editor": sdb.up("zhuopin.sdb", "作品_id_编辑器_" + str(work_id)),
                }
            )

    total = len(all_works)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_works = all_works[start_idx:end_idx]

    return success_response(
        data={
            "works": paginated_works,
            "total": total,
            "page": page,
            "per_page": per_page,
            "type": work_type,
        },
        message="获取用户作品列表成功",
    )


# NOTE:获取用户收藏列表
@user_bp.route("/<username>/stars", methods=["GET"])
def get_user_stars(username):
    """
    获取用户收藏列表接口
    :param username: 用户名
    :param page: 页码，默认1
    :param per_page: 每页数量，默认20
    :return: 用户收藏列表
    """
    user_id = _get_current_user_id(username)
    if not user_id:
        return error_response("用户不存在", 404)

    show_stars = sdb.up("user.sdb", "id_收藏展示_" + str(user_id)) != "n"
    if not show_stars:
        return error_response("该用户设置了收藏私密", 403)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    user_stars_str = sdb.up("zhuopin.sdb", "用户收藏_id_" + str(user_id)) or ""
    if user_stars_str:
        star_ids = [x for x in user_stars_str.split(",") if x.strip()]
    else:
        star_ids = []

    stars = []
    for work_id in star_ids:
        try:
            work_id = int(work_id)
        except:
            continue

        title = sdb.up("zhuopin.sdb", "作品名称_id_" + str(work_id))
        if not title:
            continue

        author = sdb.up("zhuopin.sdb", "作品作者_id_" + str(work_id))
        stars.append(
            {
                "id": work_id,
                "type": "scratch",
                "title": title,
                "author": author,
                "views": int(sdb.up("zhuopin.sdb", "作品观看数量_id_" + str(work_id)) or 0),
                "likes": int(sdb.up("zhuopin.sdb", "作品点赞_id_" + str(work_id)) or 0),
                "stars": int(sdb.up("zhuopin.sdb", "作品收藏_id_" + str(work_id)) or 0),
                "cover_url": f"/scratchphoto/{work_id}",
                "license": sdb.up("zhuopin.sdb", "作品_id_协议_" + str(work_id)),
                "editor": sdb.up("zhuopin.sdb", "作品_id_编辑器_" + str(work_id)),
            }
        )

    total = len(stars)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_stars = stars[start_idx:end_idx]

    return success_response(
        data={"stars": paginated_stars, "total": total, "page": page, "per_page": per_page},
        message="获取用户收藏列表成功",
    )


# NOTE:搜索用户
@user_bp.route("/search", methods=["GET"])
def search_users():
    """
    搜索用户接口
    :param q: 搜索关键词
    :param page: 页码，默认1
    :param per_page: 每页数量，默认20
    :return: 用户搜索结果
    """
    keyword = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    if not keyword:
        return error_response("搜索关键词不能为空", 400)

    if len(keyword) < 2:
        return error_response("搜索关键词至少需要2个字符", 400)

    try:
        from utils.database import get_db
    except ImportError:
        DATABASE = "sbox.db"

        def get_db():
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            return conn

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username LIKE ?", (f"%{keyword}%",))
        results = cursor.fetchall()
        conn.close()

        users = []
        for row in results:
            username = row[0]
            user_id = _get_current_user_id(username)
            if not user_id:
                continue

            users.append(
                {
                    "id": user_id,
                    "username": username,
                    "shengfen": genggai.caxu(username, 3) or "",
                    "grade": int(sdb.up("user.sdb", "id_Grade_" + str(user_id)) or 0),
                    "avatar_url": f"/avaphoto={user_id}",
                }
            )

        total = len(users)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_users = users[start_idx:end_idx]

        return success_response(
            data={
                "users": paginated_users,
                "total": total,
                "page": page,
                "per_page": per_page,
                "keyword": keyword,
            },
            message="搜索用户成功",
        )
    except Exception as e:
        logger.error(f"搜索用户失败: {e}")
        return error_response("搜索用户失败", 500)


# NOTE:获取当前登录用户信息（需要JWT认证）
@user_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """
    获取当前登录用户信息接口
    需要 JWT 认证
    :return: 当前用户详细信息
    """
    username = get_jwt_identity()
    claims = get_jwt()
    user_id = claims.get("user_id")

    if not username:
        return error_response("无效的 Token", 401)

    user_id = _get_current_user_id(username)
    if not user_id:
        return error_response("用户不存在", 404)

    email = genggai.caxu(username, 4)
    shengfen = genggai.caxu(username, 3) or ""

    try:
        user_grade = int(sdb.up("user.sdb", "id_Grade_" + str(user_id)) or 0)
    except:
        user_grade = 0

    raw_jianjie = sdb.up("user.sdb", "id_简介_" + str(user_id)) or ""
    clean_jianjie = _sanitize_markdown(raw_jianjie)

    grby = sdb.up("user.sdb", "id_个性_" + str(user_id)) or ""

    try:
        user_works_ids = ast.literal_eval(
            sdb.up("zhuopin.sdb", "用户所有作品_id_" + str(user_id)) or "[]"
        )
    except:
        user_works_ids = []

    user_stars_str = sdb.up("zhuopin.sdb", "用户收藏_id_" + str(user_id)) or ""
    if user_stars_str:
        user_stars_ids = [x for x in user_stars_str.split(",") if x.strip()]
    else:
        user_stars_ids = []

    money = sdb.up("zhuopin.sdb", "作者金币_id_" + str(user_id)) or "0"
    try:
        money = float(money)
    except:
        money = 0.0

    version = sdb.up("user.sdb", "id_社区版本_" + str(user_id)) or "社区版"

    ai_api_key = sdb.up("user.sdb", "ai_api_key_" + username) or ""

    return success_response(
        data={
            "id": user_id,
            "username": username,
            "email": email,
            "shengfen": shengfen,
            "grade": user_grade,
            "jianjie": clean_jianjie,
            "raw_jianjie": raw_jianjie,
            "gexing": grby,
            "avatar_url": f"/avaphoto={user_id}",
            "works_count": len(user_works_ids),
            "stars_count": len(user_stars_ids),
            "money": money,
            "version": version,
            "ai_api_key": ai_api_key if ai_api_key else None,
            "is_admin": _is_admin(username),
        },
        message="获取当前用户信息成功",
    )
