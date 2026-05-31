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

# NOTE: 这个模块实现了Scratch作品的相关API接口，包括作品列表、作品详情、作品上传、作品更新、生成简介、点赞、收藏、问题反馈等功能。它使用Flask框架来处理HTTP请求，使用SQLite数据库来存储作品数据，并且集成了一个AI接口来生成作品简介。该模块还实现了一些权限检查和异常处理，以确保只有授权用户才能进行特定操作。

from flask import Blueprint, request, jsonify, session
import os
import ast
import markdown
import bleach
import sdb
import genggai
import requests
import time
import config
import logging
from utils.helpers import allowed_file, svg_to_png

try:
    from utils.db import get_db
except ImportError:
    from utils.database import get_db

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)

scratch_api_bp = Blueprint("scratch_api", __name__)

UPLOAD_FOLDER = "scratch"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "html", "sb3", "sb2"}
DATABASE = "sbox.db"

# AI Configuration
try:
    API_KEY = config.AI_API_KEY_A
    AI_URL = "https://api.siliconflow.cn/v1/chat/completions"
    AI_HEADERS = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
except:
    API_KEY = None


# NOTE:调用AI接口生成文本，用于作品简介生成
def ai_main(m):
    if not API_KEY:
        return "AI Service Unavailable"

    data = {
        "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "messages": [{"role": "user", "content": m}],
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
        "stream": False,
    }

    try:
        response = requests.post(AI_URL, headers=AI_HEADERS, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        return "AI Error: " + str(response.status_code)
    except Exception as e:
        return "AI Error: " + str(e)


# NOTE:获取Scratch作品列表（分页）
@scratch_api_bp.route("/api/scratch/list", methods=["GET"])
def list_scratch():
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
                "views": sdb.up("zhuopin.sdb", f"作品观看数量_id_{i}") or 0,
                "likes": sdb.up("zhuopin.sdb", f"作品点赞_id_{i}") or 0,
            }
        )

    return jsonify({"works": works, "total": zhuopin_max_id, "page": page, "per_page": per_page})


# NOTE:获取单个Scratch作品详情
@scratch_api_bp.route("/api/scratch/<id>", methods=["GET"])
def get_scratch(id):
    title = sdb.up("zhuopin.sdb", f"作品名称_id_{id}")
    if not title:
        return jsonify({"error": "Work not found"}), 404

    # Increment view count
    try:
        gk = int(sdb.up("zhuopin.sdb", f"作品观看数量_id_{id}") or 0) + 1
        sdb.down("zhuopin.sdb", f"作品观看数量_id_{id}", gk)
    except:
        gk = 1

    raw_jianjie = sdb.up("zhuopin.sdb", f"作品_id_简介_{id}")
    clean_html = bleach.clean(markdown.markdown(raw_jianjie or ""), strip=True)

    # Check if user is author
    is_author = False
    if session.get("username") and session.get("username") == sdb.up(
        "zhuopin.sdb", f"作品作者_id_{id}"
    ):
        is_author = True

    return jsonify(
        {
            "id": id,
            "title": title,
            "author": sdb.up("zhuopin.sdb", f"作品作者_id_{id}"),
            "description": clean_html,
            "raw_description": raw_jianjie,
            "stats": {
                "views": gk,
                "likes": sdb.up("zhuopin.sdb", f"作品点赞_id_{id}") or 0,
                "stars": sdb.up("zhuopin.sdb", f"作品收藏_id_{id}") or 0,
                "downloads": sdb.up("zhuopin.sdb", f"作品下载_id_{id}") or 0,
            },
            "license": sdb.up("zhuopin.sdb", f"作品_id_协议_{id}"),
            "editor": sdb.up("zhuopin.sdb", f"作品_id_编辑器_{id}"),
            "is_author": is_author,
            "file_url": f"/works/{id}",
            "cover_url": f"/scratchphoto/{id}",
        }
    )


# NOTE:上传Scratch作品文件
@scratch_api_bp.route("/api/scratch/upload", methods=["POST"])
def upload_scratch():
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401

    # Check email verification
    if not genggai.caxu(session.get("username"), 4):
        return jsonify({"error": "Email verification required"}), 403

    name = request.form.get("name")
    jianjie = request.form.get("jianjie")
    license = request.form.get("license", "mit")
    sbox = request.form.get("sbox", "sbox-scratch")
    file = request.files.get("file")

    if not file or not allowed_file(file.filename, ALLOWED_EXTENSIONS):
        return jsonify({"error": "Invalid file"}), 400

    _, ext = os.path.splitext(file.filename)
    if ext.lower() == ".html":
        if genggai.caxu(session.get("username"), 3) not in ["站长", "高级管理员"]:
            return jsonify({"error": "HTML upload permission denied"}), 403

    try:
        zhuopin_max_id = int(sdb.up("zhuopin.sdb", "作品最大id"))
    except:
        zhuopin_max_id = 1

    new_filename = f"scratch2/{zhuopin_max_id}{ext}"
    if not os.path.exists("scratch2"):
        os.makedirs("scratch2")
    file.save(new_filename)

    sdb.down("zhuopin.sdb", "作品最大id", zhuopin_max_id + 1)
    sdb.down("zhuopin.sdb", f"作品_id_协议_{zhuopin_max_id}", license)
    sdb.down("zhuopin.sdb", f"作品_id_编辑器_{zhuopin_max_id}", sbox)
    sdb.down("zhuopin.sdb", f"作品_id_简介_{zhuopin_max_id}", jianjie)
    sdb.down("zhuopin.sdb", f"作品名称_id_{zhuopin_max_id}", name)
    sdb.down("zhuopin.sdb", f"作品作者_id_{zhuopin_max_id}", session.get("username"))

    # Update user works
    user_key = f"用户所有作品_id_{genggai.caxu(session.get('username'), 0)}"
    try:
        user_works = ast.literal_eval(sdb.up("zhuopin.sdb", user_key) or "[]")
    except:
        user_works = []
    user_works.append(zhuopin_max_id)
    sdb.down("zhuopin.sdb", user_key, user_works)

    return jsonify({"success": True, "id": zhuopin_max_id})


# NOTE:更新Scratch作品信息（名称、简介、封面）
@scratch_api_bp.route("/api/scratch/<id>/update", methods=["POST"])
def update_scratch(id):
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401

    author = sdb.up("zhuopin.sdb", f"作品作者_id_{id}")
    if session.get("username") != author:
        return jsonify({"error": "Permission denied"}), 403

    name = request.form.get("name")
    jianjie = request.form.get("jianjie")

    if name:
        sdb.down("zhuopin.sdb", f"作品名称_id_{id}", name)
    if jianjie:
        sdb.down("zhuopin.sdb", f"作品_id_简介_{id}", jianjie)

    # Handle cover
    cover = request.files.get("cover")
    if cover:
        if not os.path.exists("scratchphoto"):
            os.makedirs("scratchphoto")
        cover_filename = f"{id}.png"
        if cover.filename.lower().endswith(".svg"):
            temp = f"scratchphoto/{id}_temp.svg"
            cover.save(temp)
            svg_to_png(temp, f"scratchphoto/{cover_filename}")
            if os.path.exists(temp):
                os.remove(temp)
        else:
            cover.save(f"scratchphoto/{cover_filename}")

    return jsonify({"success": True})


# NOTE:AI生成Scratch作品简介
@scratch_api_bp.route("/api/scratch/<id>/summary", methods=["POST"])
def generate_summary(id):
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401

    author = sdb.up("zhuopin.sdb", f"作品作者_id_{id}")
    if session.get("username") != author:
        return jsonify({"error": "Permission denied"}), 403

    title = sdb.up("zhuopin.sdb", f"作品名称_id_{id}")
    jianjie = sdb.up("zhuopin.sdb", f"作品_id_简介_{id}")

    prompt = (
        f"为一个名为《{title}》的Scratch互动作品写一段生动有趣的简介,原简介{jianjie}，不少于200字。"
    )
    summary = ai_main(prompt)

    return jsonify({"success": True, "summary": jianjie + "\n\nAI Summary:\n" + summary})


# NOTE:点赞Scratch作品
@scratch_api_bp.route("/api/scratch/like/<id>", methods=["POST"])
def like_scratch(id):
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401

    user_id = genggai.caxu(session.get("username"), 0)
    likes_str = sdb.up("zhuopin.sdb", f"作品点赞用户_id_{id}")
    likes_list = likes_str.split(",") if likes_str else []
    likes_list = [x for x in likes_list if x.strip()]

    if str(user_id) in likes_list:
        return jsonify({"success": True, "liked": True, "count": len(likes_list)})

    likes_list.append(str(user_id))
    sdb.down("zhuopin.sdb", f"作品点赞用户_id_{id}", ",".join(likes_list))

    count = len(likes_list)
    sdb.down("zhuopin.sdb", f"作品点赞_id_{id}", count)

    return jsonify({"success": True, "liked": True, "count": count})


# NOTE:收藏/取消收藏Scratch作品
@scratch_api_bp.route("/api/scratch/star/<id>", methods=["POST"])
def star_scratch(id):
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401

    user_id = genggai.caxu(session.get("username"), 0)
    user_stars_str = sdb.up("zhuopin.sdb", f"用户收藏_id_{user_id}")
    user_stars = user_stars_str.split(",") if user_stars_str else []

    starred = False
    if str(id) in user_stars:
        user_stars.remove(str(id))
        starred = False
    else:
        user_stars.append(str(id))
        starred = True

    sdb.down("zhuopin.sdb", f"用户收藏_id_{user_id}", ",".join(user_stars))

    # Update work star count
    try:
        current_stars = int(sdb.up("zhuopin.sdb", f"作品收藏_id_{id}") or 0)
    except:
        current_stars = 0

    new_stars = current_stars + 1 if starred else max(0, current_stars - 1)
    sdb.down("zhuopin.sdb", f"作品收藏_id_{id}", new_stars)

    return jsonify({"success": True, "starred": starred, "count": new_stars})


# NOTE:获取作品的问题反馈列表
@scratch_api_bp.route("/api/scratch/<id>/issues", methods=["GET"])
def get_issues(id):
    try:
        issues = ast.literal_eval(sdb.up("Issues.sdb", f"Issues_id_{id}") or "[]")
    except:
        issues = []
    return jsonify({"issues": issues})


# NOTE:提交作品问题反馈
@scratch_api_bp.route("/api/scratch/<id>/issues", methods=["POST"])
def add_issue(id):
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401

    content = request.json.get("content")
    type_ = request.json.get("type", "general")

    if not content:
        return jsonify({"error": "Content required"}), 400

    try:
        issues = ast.literal_eval(sdb.up("Issues.sdb", f"Issues_id_{id}") or "[]")
    except:
        issues = []

    entry = f"{session.get('username')} [{type_.upper()}]: {content}"
    issues.insert(0, entry)
    sdb.down("Issues.sdb", f"Issues_id_{id}", issues)

    return jsonify({"success": True, "entry": entry})


# NOTE:从请求中获取当前用户ID（支持OAuth Token和Session两种认证）
def _get_current_user_id():
    """
    从请求中获取当前用户ID
    支持两种认证方式：
    1. OAuth Bearer Token (Authorization header)
    2. Session认证 (兼容现有系统)

    :return: (user_id, username) 或 (None, None) 如果认证失败
    """
    # 方式1: OAuth Bearer Token认证
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT user_id FROM access_tokens WHERE token = ? AND expires_at > ?",
                    (token, int(time.time())),
                ).fetchone()
                if row:
                    # 通过user_id获取username
                    user_row = conn.execute(
                        "SELECT id, username FROM users WHERE id = ?", (row["user_id"],)
                    ).fetchone()
                    if user_row:
                        logger.info(
                            f"OAuth认证成功: user_id={user_row['id']}, username={user_row['username']}"
                        )
                        return user_row["id"], user_row["username"]
        except Exception as e:
            logger.error(f"OAuth Token验证失败: {e}")
            return None, None

    # 方式2: Session认证
    username = session.get("username")
    if username:
        try:
            user_id = genggai.caxu(username, 0)  # 0 表示获取用户ID
            if user_id:
                logger.info(f"Session认证成功: user_id={user_id}, username={username}")
                return int(user_id), username
        except Exception as e:
            logger.error(f"Session认证失败: {e}")
            return None, None

    return None, None


# NOTE:检查用户对指定作品的操作权限（作者/管理员）
@scratch_api_bp.route("/api/scratch/<int:work_id>/check-permission", methods=["GET", "POST"])
def check_work_permission(work_id):
    """
    检查用户是否拥有指定作品的权限

    接受两种认证方式：
    1. OAuth Bearer Token (Authorization: Bearer <token>)
    2. Session认证 (已登录用户)

    参数：
    - work_id: 作品ID (URL路径参数)

    返回：
    {
        "has_permission": true/false,
        "is_author": true/false,
        "is_admin": true/false,
        "work_exists": true/false,
        "user_id": <user_id> or null,
        "username": "<username>" or null,
        "work_info": {
            "id": <work_id>,
            "title": "<作品名称>",
            "author": "<作者用户名>"
        }
    }
    """
    start_time = time.time()
    logger.info(f"开始检查作品权限: work_id={work_id}")

    result = {
        "has_permission": False,
        "is_author": False,
        "is_admin": False,
        "work_exists": False,
        "user_id": None,
        "username": None,
        "work_info": None,
    }

    try:
        # 1. 检查作品是否存在
        work_title = sdb.up("zhuopin.sdb", f"作品名称_id_{work_id}")
        if not work_title:
            logger.warning(f"作品不存在: work_id={work_id}")
            result["work_exists"] = False
            return jsonify(result), 404

        result["work_exists"] = True
        work_author = sdb.up("zhuopin.sdb", f"作品作者_id_{work_id}")
        result["work_info"] = {
            "id": work_id,
            "title": work_title,
            "author": work_author,
        }
        logger.info(f"作品信息: id={work_id}, title={work_title}, author={work_author}")

        # 2. 获取当前用户信息
        user_id, username = _get_current_user_id()

        if not user_id or not username:
            logger.warning(f"用户未认证: work_id={work_id}")
            return jsonify(result), 401

        result["user_id"] = user_id
        result["username"] = username

        # 3. 检查是否是作者
        if username == work_author:
            result["is_author"] = True
            result["has_permission"] = True
            logger.info(f"用户是作品作者: username={username}, work_id={work_id}")

        # 4. 检查是否是管理员
        try:
            user_shenfen = genggai.caxu(username, 3)  # 3 表示获取用户身份
            logger.info(f"用户身份: username={username}, shenfen={user_shenfen}")

            if user_shenfen in ["站长", "高级管理员"]:
                result["is_admin"] = True
                result["has_permission"] = True
                logger.info(f"用户是管理员: username={username}, shenfen={user_shenfen}")
        except Exception as e:
            logger.error(f"获取用户身份失败: {e}")

        elapsed_time = (time.time() - start_time) * 1000
        logger.info(
            f"权限检查完成: work_id={work_id}, has_permission={result['has_permission']}, 耗时={elapsed_time:.2f}ms"
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"检查作品权限时发生错误: work_id={work_id}, error={e}")
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


# NOTE:批量检查用户对多个作品的权限
@scratch_api_bp.route("/api/scratch/check-permissions", methods=["POST"])
def check_multiple_work_permissions():
    """
    批量检查用户对多个作品的权限

    请求体：
    {
        "work_ids": [1, 2, 3, ...]
    }

    返回：
    {
        "user_id": <user_id> or null,
        "username": "<username>" or null,
        "results": {
            "1": {"has_permission": true, "is_author": true, "is_admin": false},
            "2": {"has_permission": false, "is_author": false, "is_admin": false},
            ...
        }
    }
    """
    start_time = time.time()
    logger.info("开始批量检查作品权限")

    # 获取当前用户信息
    user_id, username = _get_current_user_id()

    if not user_id or not username:
        logger.warning("用户未认证")
        return jsonify({"user_id": None, "username": None, "results": {}}), 401

    # 获取用户身份
    user_shenfen = None
    try:
        user_shenfen = genggai.caxu(username, 3)
    except Exception as e:
        logger.error(f"获取用户身份失败: {e}")

    is_admin = user_shenfen in ["站长", "高级管理员"] if user_shenfen else False

    # 获取要检查的作品ID列表
    data = request.get_json()
    if not data or "work_ids" not in data:
        return jsonify({"error": "work_ids is required"}), 400

    work_ids = data["work_ids"]
    if not isinstance(work_ids, list):
        return jsonify({"error": "work_ids must be a list"}), 400

    results = {}

    for work_id in work_ids:
        work_id_str = str(work_id)
        result = {"has_permission": False, "is_author": False, "is_admin": is_admin}

        try:
            work_author = sdb.up("zhuopin.sdb", f"作品作者_id_{work_id}")

            if work_author:
                if username == work_author:
                    result["is_author"] = True
                    result["has_permission"] = True
                elif is_admin:
                    result["has_permission"] = True
        except Exception as e:
            logger.error(f"检查作品权限失败: work_id={work_id}, error={e}")

        results[work_id_str] = result

    elapsed_time = (time.time() - start_time) * 1000
    logger.info(f"批量权限检查完成: 检查了{len(work_ids)}个作品, 耗时={elapsed_time:.2f}ms")

    return jsonify(
        {
            "user_id": user_id,
            "username": username,
            "is_admin": is_admin,
            "results": results,
        }
    )


# NOTE:简单的作者权限检查接口
@scratch_api_bp.route("/api/scratch/check-author", methods=["GET"])
def check_author():
    """
    简单的作者权限检查接口

    参数：
    - name: 用户名
    - workid: 作品ID

    返回：
    - "yes" 如果是该作品的作者
    - "false" 如果不是作者或作品不存在
    """
    username = request.args.get("name")
    work_id = request.args.get("workid")

    # 参数验证
    if not username or not work_id:
        logger.warning(f"参数缺失: name={username}, workid={work_id}")
        return "false", 200

    try:
        # 获取作品作者
        work_author = sdb.up("zhuopin.sdb", f"作品作者_id_{work_id}")

        # 检查是否是作者
        if work_author and work_author == username:
            logger.info(f"作者验证成功: username={username}, work_id={work_id}")
            return "yes", 200
        else:
            logger.info(
                f"作者验证失败: username={username}, work_id={work_id}, author={work_author}"
            )
            return "false", 200

    except Exception as e:
        logger.error(f"检查作者权限时发生错误: username={username}, work_id={work_id}, error={e}")
        return "false", 200
