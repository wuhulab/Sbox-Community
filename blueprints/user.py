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

# NOTE: 这个模块实现了用户相关的功能，包括个人中心、用户信息管理、文件上传和头像处理等。它使用Flask框架来处理HTTP请求，使用SQLite数据库来存储用户数据，并且使用Bleach来防止XSS攻击。该模块还提供了一些辅助函数来检查文件类型和提供用户头像等功能。

import logging

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_from_directory,
    flash,
)
import os
import re
import ast
import markdown
import bleach
from werkzeug.utils import secure_filename
import genggai
import sdb
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from utils.helpers import check_password_strength

logger = logging.getLogger(__name__)

try:
    from utils.database import get_db
except ImportError:
    import sqlite3

    DATABASE = "sbox.db"

    def get_db():
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn


user_bp = Blueprint("user", __name__)

# 导航栏配置
nav = """
            <div class="toolbox">
                <div class="dropdown" onclick="toggleDropdown()">
                    ☰
                    <div class="dropdown-content">
                        <a href="/">首页</a>
                        <a href="/scratch">scratch</a>
                        <a href="/ai">AI模型</a>
                        <a href="/search">作品搜索</a>
                        <a href="/user/">个人中心</a>
                        <a href="/tougaoscratch">投稿作品</a>
                        <a href="/users">用户更改</a>
                        <a href="/message">信息</a>
                        <a href="/logout">登出</a>
                    </div>
                </div>
                <button class="theme-toggle" onclick="toggleTheme()">&#9788;</button>
            </div>
        </div>
"""

# 页脚配置
footer = """
        <p>2025 小盒子社区</p>
        开源文件 <a href="https://gitee.com/wujiajiouwei/small-box-community">gitee</a> | <a href="https://gitee.com/wujiajiouwei/scratch-git">ScratchGit</a> | <a href="https://gitee.com/wujiajiouwei/sbox-api">Sboxapi</a><br>
        网站相关 <a href = "/required">使用小盒子必读</a> | <a href="/download">下载相关软件</a> | <a href="/thanks">特别鸣谢</a><br>
"""


# NOTE:个人中心首页，重定向到用户详情页
@user_bp.route("/user/")
def user_center():
    if "username" not in session:
        return redirect(url_for("main.login"))
    username = session["username"]
    return redirect(url_for("user.user", s=username))


# NOTE:个人中心详情页，支持密码修改和头像上传
@user_bp.route("/user/<s>", methods=["GET", "POST"])
def user(s):
    if "username" not in session:
        return redirect(url_for("main.login"))

    # 处理POST请求（密码修改、头像上传）
    if request.method == "POST":
        if "new_password" in request.form:
            new_password = request.form["new_password"]
            # 检查密码强度
            if len(new_password) < 8:
                return "密码长度必须至少为8位", 400
            if not re.search(r"\d", new_password):
                return "密码必须包含至少一个数字", 400
            if not re.search(r"[a-z]", new_password):
                return "密码必须包含至少一个小写字母", 400
            if not re.search(r"[A-Z]", new_password):
                return "密码必须包含至少一个大写字母", 400
            if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
                return "密码必须包含至少一个特殊字符", 400
            # 加密密码
            hashed_password = generate_password_hash(new_password)
            # 更新密码
            user_data = sdb.up("users.sdb", s)
            if user_data:
                user_info = ast.literal_eval(user_data)
                user_info["password"] = hashed_password
                sdb.down("users.sdb", s, str(user_info))
                return "密码修改成功！", 200
            else:
                return "用户不存在", 404
        elif "profile_image" in request.files:
            file = request.files["profile_image"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # 确保用户文件夹存在
                user_folder = os.path.join("uploads", s)
                os.makedirs(user_folder, exist_ok=True)
                # 保存文件
                file_path = os.path.join(user_folder, filename)
                file.save(file_path)
                # 更新用户信息
                user_data = sdb.up("users.sdb", s)
                if user_data:
                    user_info = ast.literal_eval(user_data)
                    user_info["profile_image"] = filename
                    sdb.down("users.sdb", s, str(user_info))
                    return "头像上传成功！", 200
                else:
                    return "用户不存在", 404
            else:
                return "无效的文件类型", 400

    # 处理GET请求 - 渲染用户页面
    # === XSS 防护：转义 URL 参数 s（用户名） ===
    username = bleach.clean(s)  # 防止恶意用户名执行脚本

    # 获取id和email
    id = genggai.caxu(s, 0)
    email = genggai.caxu(s, 4)

    # 如果 id 无效，避免继续执行
    if str(id) == "None":
        return render_template("information.html", Information="没有该用户")

    logger.debug("访问用户页面: %s", username)

    # 获取用户文件夹路径
    user_folder = os.path.join("uploads", s)
    shengfen = genggai.caxu(s, 3)

    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    files = os.listdir(user_folder)

    try:
        zhuopinsc = ast.literal_eval(sdb.up("zhuopin.sdb", "用户所有作品_id_" + str(id)))
    except (SyntaxError, ValueError) as e:
        logger.error("解析用户 %s 作品数据失败: %s", id, e)
        zhuopinsc = []

    zhuopinstar = sdb.up("zhuopin.sdb", "用户收藏_id_" + str(id))
    if zhuopinstar:
        zhuopinstar = zhuopinstar.split(",")
        if zhuopinstar and zhuopinstar[0] == "":
            del zhuopinstar[0]
    else:
        zhuopinstar = []

    Grade = sdb.up("user.sdb", "id_Grade_" + str(id))
    if Grade == "":
        Grade = 0
        sdb.down("user.sdb", "id_Grade_" + str(id), Grade)

    # === XSS 防护：转义数据库中读取的用户可控字段 ===
    grby = bleach.clean(sdb.up("user.sdb", "id_个性_" + str(id)) or "")
    jianjie = bleach.clean(sdb.up("user.sdb", "id_简介_" + str(id)) or "")
    jianjie = markdown.markdown(jianjie, extensions=["extra"])

    # Step 2: 使用 bleach 清洗 HTML，防止 XSS
    clean_jianjie = bleach.clean(
        jianjie,
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
        protocols=["http", "https", "mailto"],  # 允许的协议，阻止 javascript:
        strip=True,  # 自动移除非法标签，而不是转义
    )

    zhuopinsc1 = []
    for item in zhuopinsc:
        title = sdb.up("zhuopin.sdb", f"作品名称_id_{item}")
        zhuopinsc1.append({"id": item, "title": bleach.clean(title)})

    zhuopinsc2 = []
    for item in zhuopinstar:
        title = sdb.up("zhuopin.sdb", f"作品名称_id_{item}")
        zhuopinsc2.append({"id": item, "title": bleach.clean(title)})
    semail = ""
    qiandao = ""
    if (email == "no" or email == "" or email is None) and (session.get("username") == s):
        semail = """
        你的邮箱没有验证  <a href="/register3">来此补签邮箱</a>
        """
    if session.get("username") == s:
        qiandao = """
        """

    money = sdb.up("zhuopin.sdb", f"作者金币_id_{id}")
    if money == "":
        money = 0

    if sdb.up("user.sdb", f"id_收藏展示_{id}") == "n":
        zhuopinsc2 = ""

    # === 最终渲染前确保所有用户内容已转义 ===
    return render_template(
        "user2.html",
        nav=nav,
        Grade=Grade,
        qiandao=qiandao,
        money=money,
        email=semail,
        id=str(id),
        jianjie=clean_jianjie,  # 已转义
        grby=grby,  # 已转义
        zhuopinsc2=zhuopinsc2,  # 列表中的 title 已转义
        zhuopinsc1=zhuopinsc1,  # 列表中的 title 已转义
        files=[bleach.clean(f) for f in files],  # 转义文件名（防止恶意文件名XSS）
        shengfen=bleach.clean(shengfen),
        username=username,  # 已转义
    )


# NOTE:用户设置页面，修改个性签名、简介、密码、头像等
@user_bp.route("/users", methods=["GET", "POST"])
def users():
    if "username" not in session:
        return redirect(url_for("main.login"))

    username = session["username"]
    id = genggai.caxu(username, 0)

    if request.method == "POST":
        # 获取表单中的个性、简介、收藏展示
        gexing = request.form["geixing"]
        jianjie = request.form["jianjie"]
        shoucang = request.form["shoucang"]
        version = request.form["version"]

        # 获取第三方登录验证设置
        third_party_auth = request.form.get(
            "third_party_auth", "2"
        )  # 默认值为2（信任第三方授权登录验证）

        # 获取默认使用Turbowarp设置
        use_turbowarp = request.form.get("use_turbowarp", "false")

        # 检查内容合法性
        try:
            # 导入main函数进行内容检查
            from app import main

            if (
                not main(
                    "检查是否合法，可以水文字，合法返回True，否则返回False:"
                    + gexing
                    + ","
                    + jianjie
                )
                == "True"
            ):
                return "简介不合法"
        except:
            # 如果检查失败，继续执行
            pass

        # 将个性、简介、收藏展示保存到数据库中
        sdb.down("user.sdb", f"id_个性_{id}", gexing)
        sdb.down("user.sdb", f"id_简介_{id}", jianjie)
        sdb.down("user.sdb", f"id_收藏展示_{id}", shoucang)
        if version in ["教育版", "社区版"]:
            sdb.down("user.sdb", f"id_社区版本_{id}", version)
        else:
            return "不存在的社区版本"

        # 保存第三方登录验证设置
        sdb.down("user.sdb", f"id_第三方登录验证_{id}", third_party_auth)

        # 保存默认使用Turbowarp设置
        sdb.down("user.sdb", f"个人默认_turbowarp_{username}", use_turbowarp)

        # 处理密码修改
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if current_password and new_password and confirm_password:
            try:
                from utils.database import get_db
            except ImportError:
                DATABASE = "sbox.db"

                def get_db():
                    conn = sqlite3.connect(DATABASE)
                    conn.row_factory = sqlite3.Row
                    return conn

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()

            if result:
                current_hash = result[0]
                # 验证当前密码
                if check_password_hash(current_hash, current_password):
                    # 检查新密码强度
                    if check_password_strength(new_password):
                        # 检查两次输入的新密码是否一致
                        if new_password == confirm_password:
                            # 更新密码
                            hashed_password = generate_password_hash(new_password)
                            genggai.update_user(username, 2, hashed_password, "password")
                        else:
                            return render_template(
                                "information.html", Information="两次输入的新密码不一致"
                            )
                    else:
                        return render_template(
                            "information.html",
                            Information="新密码强度不足，请使用至少8位包含数字、大小写字母和特殊字符的密码",
                        )
                else:
                    return render_template("information.html", Information="当前密码错误")

        # 处理头像上传
        if "cover" in request.files:
            file = request.files["cover"]
            # 如果文件存在且文件名不为空
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_ext = os.path.splitext(filename)[1].lower()

                AVATAR_FOLDER = "avatar"
                if not os.path.exists(AVATAR_FOLDER):
                    os.makedirs(AVATAR_FOLDER)

                if file_ext == ".svg":
                    # Handle SVG file - convert to PNG
                    temp_svg_path = os.path.join(AVATAR_FOLDER, f"{id}_temp.svg")
                    final_png_path = os.path.join(AVATAR_FOLDER, f"{id}.png")

                    # Save the uploaded SVG file temporarily
                    file.save(temp_svg_path)

                    # Convert SVG to PNG
                    try:
                        from utils.helpers import svg_to_png

                        if svg_to_png(temp_svg_path, final_png_path):
                            # Remove the temporary SVG file
                            os.remove(temp_svg_path)
                            flash("头像上传成功")
                        else:
                            # If conversion fails, remove the temp file and show error
                            if os.path.exists(temp_svg_path):
                                os.remove(temp_svg_path)
                            flash("SVG to PNG conversion failed")
                    except:
                        flash("头像处理失败")
                else:
                    # Handle regular image files - save as PNG
                    filename = secure_filename(f"{id}.png")
                    # 尝试保存文件
                    try:
                        file.save(os.path.join(AVATAR_FOLDER, filename))
                        flash("头像上传成功")
                    except Exception as e:
                        flash(f"头像保存失败：{str(e)}")

        # 返回更改后的个性、简介、收藏展示
        return redirect(url_for("user.users"))

    # 从数据库中获取个性、简介、收藏展示
    gexing1 = sdb.up("user.sdb", f"id_个性_{id}")
    jianjie1 = sdb.up("user.sdb", f"id_简介_{id}")
    shoucang1 = sdb.up("user.sdb", f"id_收藏展示_{id}")
    version = sdb.up("user.sdb", f"id_社区版本_{id}")

    # 获取第三方登录验证设置，如果没有设置则默认为2（信任第三方授权登录验证）
    third_party_auth = sdb.up("user.sdb", f"id_第三方登录验证_{id}")
    if third_party_auth == "":
        third_party_auth = "2"
        sdb.down("user.sdb", f"id_第三方登录验证_{id}", third_party_auth)

    # 获取默认使用Turbowarp设置，如果没有设置则默认为false
    use_turbowarp = sdb.up("user.sdb", f"个人默认_turbowarp_{username}")
    if use_turbowarp == "":
        use_turbowarp = "false"
        sdb.down("user.sdb", f"个人默认_turbowarp_{username}", use_turbowarp)

    if version == "":
        version = "社区版"
        sdb.down("user.sdb", f"id_社区版本_{id}", version)

    # 渲染users2.html页面
    return render_template(
        "users2.html",
        version=version,
        gexing1=gexing1,
        jianjie1=jianjie1,
        shoucang1=shoucang1,
        nav=nav,
        footer=footer,
        third_party_auth=third_party_auth,
        use_turbowarp=use_turbowarp,
    )


# NOTE:提供用户上传文件的访问
@user_bp.route("/uploads/<username>/<filename>")
def uploaded_file(username, filename):
    if "username" not in session or session["username"] != username:
        if not filename.startswith("public_"):
            return "权限不足", 403
    return send_from_directory(os.path.join("uploads", username), filename)


# NOTE:在iframe中查看用户上传的文件
@user_bp.route("/view_file_in_iframe/<username>/<filename>")
def view_file_in_iframe(username, filename):
    file_path = os.path.join("uploads", username, filename)
    if not os.path.exists(file_path):
        return "文件不存在", 404
    return render_template("view_file.html", username=username, filename=filename)


# NOTE:删除用户的指定文件
@user_bp.route("/delete_file/<username>/<filename>", methods=["GET"])
def delete_file(username, filename):
    if "username" not in session or session["username"] != username:
        return "权限不足", 403
    file_path = os.path.join("uploads", username, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return "文件删除成功！", 200
    else:
        return "文件不存在", 404


# NOTE:获取平台注册用户总数
@user_bp.route("/number_of_users")
def number_of_users():
    count = 0
    try:
        with open("users.sdb", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    count += 1
    except:
        pass
    return str(count)


# NOTE:用户信息API，返回当前登录用户的JSON数据
@user_bp.route("/api/user/ue")
def user_api():
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401
    username = session["username"]
    user_data = sdb.up("users.sdb", username)
    if user_data:
        try:
            user_info = ast.literal_eval(user_data)
            return jsonify(user_info)
        except:
            return jsonify({"error": "Invalid user data"}), 500
    else:
        return jsonify({"error": "User not found"}), 404


# NOTE:检查上传文件类型是否在允许列表中
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "svg"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# NOTE:提供用户头像图片，不存在则生成默认头像
@user_bp.route("/avaphoto=<id>")
def serve_avatar(id):
    logger.debug("头像请求: %s", id)
    try:
        AVATAR_FOLDER = "avatar"
        filename = f"{id}.png"
        file_path = os.path.join(AVATAR_FOLDER, filename)

        # 如果文件存在，返回文件
        if os.path.exists(file_path):
            return send_from_directory(AVATAR_FOLDER, filename)
        else:
            # 确保avatar目录存在
            if not os.path.exists(AVATAR_FOLDER):
                os.makedirs(AVATAR_FOLDER)
            # 如果文件不存在，返回默认头像
            filename = "1.png"
            file_path = os.path.join(AVATAR_FOLDER, filename)
            # 如果默认头像也不存在，创建一个简单的默认头像
            if not os.path.exists(file_path):
                from PIL import Image, ImageDraw, ImageFont

                img = Image.new("RGB", (128, 128), color=(73, 109, 137))
                d = ImageDraw.Draw(img)
                try:
                    fnt = ImageFont.truetype("arial.ttf", 60)
                except:
                    fnt = ImageFont.load_default()
                d.text((30, 30), str(id)[-2:], font=fnt, fill=(255, 255, 0))
                img.save(file_path)
            return send_from_directory(AVATAR_FOLDER, filename)
    except Exception as e:
        return "发生错误", 500
