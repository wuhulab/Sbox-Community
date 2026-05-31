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
Scratch 作品 API V1 版本蓝图模块
提供作品的 CRUD、点赞、收藏、Issue 等功能接口
"""

import os
import ast
import logging
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import sdb
import genggai
from utils.helpers import allowed_file, svg_to_png
from utils.api_response import success_response, error_response

logger = logging.getLogger(__name__)

scratch_bp = Blueprint("scratch", __name__, url_prefix="/api/v1/scratch")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "html", "sb3", "sb2"}


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


# NOTE:检查用户对作品的权限
def _check_work_permission(work_id, username):
    """
    检查用户对作品的权限
    :param work_id: 作品ID
    :param username: 用户名
    :return: (is_author, is_admin, work_exists)
    """
    work_author = sdb.up("zhuopin.sdb", f"作品作者_id_{work_id}")
    if not work_author:
        return False, False, False
    is_author = username == work_author
    is_admin = _is_admin(username)
    return is_author, is_admin, True


# NOTE:获取作品列表（分页）
@scratch_bp.route("/list", methods=["GET"])
def list_scratch():
    """
    获取作品列表接口
    :param page: 页码，默认1
    :param per_page: 每页数量，默认20
    :return: 作品列表数据
    """
    try:
        zhuopin_max_id = int(sdb.up("zhuopin.sdb", "作品最大id")) - 1
        if zhuopin_max_id < 1:
            zhuopin_max_id = 1
    except:
        zhuopin_max_id = 1

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    start_id = zhuopin_max_id - (page - 1) * per_page
    end_id = max(0, start_id - per_page)

    works = []
    for i in range(start_id, end_id, -1):
        if i < 1:
            break
        title = sdb.up("zhuopin.sdb", f"作品名称_id_{i}")
        if not title:
            continue

        works.append(
            {
                "id": i,
                "title": title,
                "author": sdb.up("zhuopin.sdb", f"作品作者_id_{i}"),
                "cover": f"/scratchphoto/{i}",
                "views": int(sdb.up("zhuopin.sdb", f"作品观看数量_id_{i}") or 0),
                "likes": int(sdb.up("zhuopin.sdb", f"作品点赞_id_{i}") or 0),
            }
        )

    return success_response(
        data={
            "works": works,
            "total": zhuopin_max_id,
            "page": page,
            "per_page": per_page,
        },
        message="获取作品列表成功",
    )


# NOTE:获取作品详情
@scratch_bp.route("/<int:work_id>", methods=["GET"])
def get_scratch(work_id):
    """
    获取作品详情接口
    :param work_id: 作品ID
    :return: 作品详细信息
    """
    title = sdb.up("zhuopin.sdb", f"作品名称_id_{work_id}")
    if not title:
        return error_response("作品不存在", 404)

    try:
        views = int(sdb.up("zhuopin.sdb", f"作品观看数量_id_{work_id}") or 0) + 1
        sdb.down("zhuopin.sdb", f"作品观看数量_id_{work_id}", views)
    except:
        views = 1

    raw_jianjie = sdb.up("zhuopin.sdb", f"作品_id_简介_{work_id}")
    try:
        import markdown
        import bleach

        clean_html = bleach.clean(markdown.markdown(raw_jianjie or ""), strip=True)
    except:
        clean_html = raw_jianjie or ""

    username = get_jwt_identity() if request.headers.get("Authorization") else None
    is_author = False
    if username:
        is_author = username == sdb.up("zhuopin.sdb", f"作品作者_id_{work_id}")

    return success_response(
        data={
            "id": work_id,
            "title": title,
            "author": sdb.up("zhuopin.sdb", f"作品作者_id_{work_id}"),
            "description": clean_html,
            "raw_description": raw_jianjie,
            "stats": {
                "views": views,
                "likes": int(sdb.up("zhuopin.sdb", f"作品点赞_id_{work_id}") or 0),
                "stars": int(sdb.up("zhuopin.sdb", f"作品收藏_id_{work_id}") or 0),
                "downloads": int(sdb.up("zhuopin.sdb", f"作品下载_id_{work_id}") or 0),
            },
            "license": sdb.up("zhuopin.sdb", f"作品_id_协议_{work_id}"),
            "editor": sdb.up("zhuopin.sdb", f"作品_id_编辑器_{work_id}"),
            "is_author": is_author,
            "file_url": f"/works/{work_id}",
            "cover_url": f"/scratchphoto/{work_id}",
        },
        message="获取作品详情成功",
    )


# NOTE:上传作品（需要JWT认证）
@scratch_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_scratch():
    """
    上传作品接口
    需要 JWT 认证
    :return: 上传结果
    """
    username = get_jwt_identity()

    if not genggai.caxu(username, 4):
        return error_response("请先验证邮箱后再上传作品", 403)

    name = request.form.get("name")
    jianjie = request.form.get("jianjie")
    license_type = request.form.get("license", "mit")
    sbox = request.form.get("sbox", "sbox-scratch")
    file = request.files.get("file")

    if not file or not allowed_file(file.filename, ALLOWED_EXTENSIONS):
        return error_response("无效的文件格式", 400)

    _, ext = os.path.splitext(file.filename)
    if ext.lower() == ".html":
        if not _is_admin(username):
            return error_response("HTML 文件上传权限不足", 403)

    try:
        zhuopin_max_id = int(sdb.up("zhuopin.sdb", "作品最大id"))
    except:
        zhuopin_max_id = 1

    new_filename = f"scratch2/{zhuopin_max_id}{ext}"
    if not os.path.exists("scratch2"):
        os.makedirs("scratch2")
    file.save(new_filename)

    sdb.down("zhuopin.sdb", "作品最大id", zhuopin_max_id + 1)
    sdb.down("zhuopin.sdb", f"作品_id_协议_{zhuopin_max_id}", license_type)
    sdb.down("zhuopin.sdb", f"作品_id_编辑器_{zhuopin_max_id}", sbox)
    sdb.down("zhuopin.sdb", f"作品_id_简介_{zhuopin_max_id}", jianjie)
    sdb.down("zhuopin.sdb", f"作品名称_id_{zhuopin_max_id}", name)
    sdb.down("zhuopin.sdb", f"作品作者_id_{zhuopin_max_id}", username)

    user_key = f"用户所有作品_id_{genggai.caxu(username, 0)}"
    try:
        user_works = ast.literal_eval(sdb.up("zhuopin.sdb", user_key) or "[]")
    except:
        user_works = []
    user_works.append(zhuopin_max_id)
    sdb.down("zhuopin.sdb", user_key, user_works)

    logger.info(f"用户 {username} 上传了新作品: id={zhuopin_max_id}, name={name}")

    return success_response(data={"id": zhuopin_max_id}, message="作品上传成功")


# NOTE:更新作品信息（需要JWT认证，作者或管理员）
@scratch_bp.route("/<int:work_id>", methods=["PUT"])
@jwt_required()
def update_scratch(work_id):
    """
    更新作品接口
    需要 JWT 认证
    仅作者或管理员可操作
    :param work_id: 作品ID
    :return: 更新结果
    """
    username = get_jwt_identity()
    is_author, is_admin, work_exists = _check_work_permission(work_id, username)

    if not work_exists:
        return error_response("作品不存在", 404)

    if not is_author and not is_admin:
        return error_response("权限不足，仅作者或管理员可操作", 403)

    name = request.form.get("name")
    jianjie = request.form.get("jianjie")

    if name:
        sdb.down("zhuopin.sdb", f"作品名称_id_{work_id}", name)
    if jianjie:
        sdb.down("zhuopin.sdb", f"作品_id_简介_{work_id}", jianjie)

    cover = request.files.get("cover")
    if cover:
        if not os.path.exists("scratchphoto"):
            os.makedirs("scratchphoto")
        cover_filename = f"{work_id}.png"
        if cover.filename.lower().endswith(".svg"):
            temp = f"scratchphoto/{work_id}_temp.svg"
            cover.save(temp)
            svg_to_png(temp, f"scratchphoto/{cover_filename}")
            if os.path.exists(temp):
                os.remove(temp)
        else:
            cover.save(f"scratchphoto/{cover_filename}")

    logger.info(f"用户 {username} 更新了作品: id={work_id}")

    return success_response(data={"id": work_id}, message="作品更新成功")


# NOTE:点赞作品（需要JWT认证）
@scratch_bp.route("/like/<int:work_id>", methods=["POST"])
@jwt_required()
def like_scratch(work_id):
    """
    点赞作品接口
    需要 JWT 认证
    :param work_id: 作品ID
    :return: 点赞结果
    """
    username = get_jwt_identity()
    user_id = _get_current_user_id(username)

    if not user_id:
        return error_response("无法获取用户信息", 400)

    title = sdb.up("zhuopin.sdb", f"作品名称_id_{work_id}")
    if not title:
        return error_response("作品不存在", 404)

    likes_str = sdb.up("zhuopin.sdb", f"作品点赞用户_id_{work_id}")
    likes_list = likes_str.split(",") if likes_str else []
    likes_list = [x for x in likes_list if x.strip()]

    if str(user_id) in likes_list:
        return success_response(data={"liked": True, "count": len(likes_list)}, message="已点赞")

    likes_list.append(str(user_id))
    sdb.down("zhuopin.sdb", f"作品点赞用户_id_{work_id}", ",".join(likes_list))

    count = len(likes_list)
    sdb.down("zhuopin.sdb", f"作品点赞_id_{work_id}", count)

    logger.info(f"用户 {username} 点赞了作品: id={work_id}")

    return success_response(data={"liked": True, "count": count}, message="点赞成功")


# NOTE:收藏/取消收藏作品（需要JWT认证）
@scratch_bp.route("/star/<int:work_id>", methods=["POST"])
@jwt_required()
def star_scratch(work_id):
    """
    收藏作品接口
    需要 JWT 认证
    :param work_id: 作品ID
    :return: 收藏结果
    """
    username = get_jwt_identity()
    user_id = _get_current_user_id(username)

    if not user_id:
        return error_response("无法获取用户信息", 400)

    title = sdb.up("zhuopin.sdb", f"作品名称_id_{work_id}")
    if not title:
        return error_response("作品不存在", 404)

    user_stars_str = sdb.up("zhuopin.sdb", f"用户收藏_id_{user_id}")
    user_stars = user_stars_str.split(",") if user_stars_str else []

    starred = False
    if str(work_id) in user_stars:
        user_stars.remove(str(work_id))
        starred = False
    else:
        user_stars.append(str(work_id))
        starred = True

    sdb.down("zhuopin.sdb", f"用户收藏_id_{user_id}", ",".join(user_stars))

    try:
        current_stars = int(sdb.up("zhuopin.sdb", f"作品收藏_id_{work_id}") or 0)
    except:
        current_stars = 0

    new_stars = current_stars + 1 if starred else max(0, current_stars - 1)
    sdb.down("zhuopin.sdb", f"作品收藏_id_{work_id}", new_stars)

    logger.info(f"用户 {username} {'收藏' if starred else '取消收藏'}了作品: id={work_id}")

    return success_response(
        data={"starred": starred, "count": new_stars},
        message="收藏成功" if starred else "取消收藏成功",
    )


# NOTE:获取作品Issues列表
@scratch_bp.route("/<int:work_id>/issues", methods=["GET"])
def get_issues(work_id):
    """
    获取作品 Issues 接口
    :param work_id: 作品ID
    :return: Issues 列表
    """
    title = sdb.up("zhuopin.sdb", f"作品名称_id_{work_id}")
    if not title:
        return error_response("作品不存在", 404)

    try:
        issues = ast.literal_eval(sdb.up("Issues.sdb", f"Issues_id_{work_id}") or "[]")
    except:
        issues = []

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    total = len(issues)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_issues = issues[start_idx:end_idx]

    return success_response(
        data={
            "issues": paginated_issues,
            "total": total,
            "page": page,
            "per_page": per_page,
        },
        message="获取 Issues 成功",
    )


# NOTE:添加作品Issue（需要JWT认证）
@scratch_bp.route("/<int:work_id>/issues", methods=["POST"])
@jwt_required()
def add_issue(work_id):
    """
    添加作品 Issue 接口
    需要 JWT 认证
    :param work_id: 作品ID
    :return: 添加结果
    """
    username = get_jwt_identity()

    title = sdb.up("zhuopin.sdb", f"作品名称_id_{work_id}")
    if not title:
        return error_response("作品不存在", 404)

    data = request.get_json()
    if not data:
        return error_response("请求数据不能为空", 400)

    content = data.get("content")
    issue_type = data.get("type", "general")

    if not content:
        return error_response("Issue 内容不能为空", 400)

    try:
        issues = ast.literal_eval(sdb.up("Issues.sdb", f"Issues_id_{work_id}") or "[]")
    except:
        issues = []

    entry = f"{username} [{issue_type.upper()}]: {content}"
    issues.insert(0, entry)
    sdb.down("Issues.sdb", f"Issues_id_{work_id}", issues)

    logger.info(f"用户 {username} 为作品 {work_id} 添加了 Issue: {issue_type}")

    return success_response(data={"entry": entry}, message="Issue 添加成功")
