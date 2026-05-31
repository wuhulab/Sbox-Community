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

# NOTE: 这个模块实现了Scratch作品的上传、展示、管理和下载功能。用户可以通过表单上传Scratch项目文件（如.sb3或.html），并为作品添加名称、简介和许可证信息。作品会被保存到服务器，并在数据库中记录相关信息。用户可以查看作品详情，包括简介、协议、作者信息等，还可以进行管理操作，如修改作品信息、上传新版本等。此外，用户还可以下载作品文件，前提是作品的许可证允许下载。该模块还处理了一些权限检查和异常情况，如作者状态异常、作品状态异常等。

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
    Response,
    make_response,
    current_app,
)
import os
import re
import ast
import markdown
import bleach
import shutil
from datetime import datetime, timedelta
import sdb
import genggai
import email_send
import config
from utils.helpers import allowed_file, svg_to_png

logger = logging.getLogger(__name__)

scratch_bp = Blueprint("scratch", __name__)

# NOTE:导航栏配置
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

# NOTE:优秀作品列表
Excellent_scratch = [10, 12, 36]

# NOTE:配置上传文件保存路径，确认正常文件
UPLOAD_FOLDER = "scratch"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "html", "sb3", "sb2"}

# 确保上传目录存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# NOTE:投稿Scratch（重定向到/scratch/up）
@scratch_bp.route("/tougaoscratch", methods=["GET", "POST"])
def scratch_tougao2():
    return redirect(url_for("scratch.scratch_tougao"))


# NOTE:Scratch作品上传页面
@scratch_bp.route("/scratch/up", methods=["GET", "POST"])
def scratch_tougao():
    if session.get("username") == None:
        return redirect(url_for("main.login"))

    id = genggai.caxu(session.get("username"), 0)

    zhuozhe = sdb.up(
        "zhuopin.sdb",
        "作者状态内容_id_" + str(genggai.caxu(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)), 0)),
    )
    if not zhuozhe == "":
        return render_template("information.html", Information=f"作者状态异常，详情：{zhuozhe}")

    if (
        genggai.caxu(session.get("username"), 4) == None
        or genggai.caxu(session.get("username"), 4) == ""
    ):
        return render_template("information.html", Information="上传作品需要验证邮箱")

    if request.method == "POST":
        name = request.form["name"]
        jianjie = request.form["jianjie"]
        license = request.form.get("license", "mit")  # 默认mit
        sbox = request.form.get("sbox", "sbox-scratch")
        file = request.files["file"]

        logger.debug("上传文件: %s", file.filename)

        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
            _, file_extension = os.path.splitext(file.filename)

            # 对HTML文件进行额外的安全检查 - 只有特定身份的用户才能上传HTML文件
            if file_extension.lower() == ".html":
                user_shenfen = genggai.caxu(session.get("username"), 3)  # 获取用户身份
                if user_shenfen not in ["站长", "高级管理员"]:
                    return render_template(
                        "information.html",
                        Information="HTML文件上传权限不足！请联系管理员。",
                    )

            zhuopin_max_id = sdb.up("zhuopin.sdb", "作品最大id")

            new_filename = "scratch2/" + str(zhuopin_max_id) + file_extension
            sdb.down("zhuopin.sdb", "作品最大id", int(zhuopin_max_id) + 1)
            filename = os.path.join(UPLOAD_FOLDER, new_filename)

            file.save(new_filename)
            sdb.down("zhuopin.sdb", "作品_id_协议_" + str(zhuopin_max_id), license)
            sdb.down("zhuopin.sdb", "作品_id_编辑器_" + str(zhuopin_max_id), sbox)
            sdb.down("zhuopin.sdb", "作品_id_简介_" + str(zhuopin_max_id), jianjie)
            sdb.down("zhuopin.sdb", "作品名称_id_" + str(zhuopin_max_id), name)
            sdb.down(
                "zhuopin.sdb",
                "作品作者_id_" + str(zhuopin_max_id),
                session.get("username"),
            )

            user_key_suffix = genggai.caxu(session.get("username"), 0)
            if not user_key_suffix:
                return render_template(
                    "information.html", Information="用户名无效，请确认用户名是否正确"
                )

            user_key = f"用户所有作品_id_{user_key_suffix}"

            if not sdb.up("zhuopin.sdb", user_key) == "":
                user_works = ast.literal_eval(sdb.up("zhuopin.sdb", user_key))
            else:
                user_works = []

            if user_works is None:
                user_works = []

            user_works.append(zhuopin_max_id)

            sdb.down("zhuopin.sdb", f"用户所有作品_id_{user_key_suffix}", user_works)

            username = session.get("username")

            # TODO:之后改成中文
            con = f"""
hey {username}!<br>
<br>
Thank you for submitting your works to the repository!<br>
Your repository name is {name}, and the profile is {jianjie}. <br>
<br>
The file has been uploaded.<br>
<br>
Can visit {config.SITE_URL}/scratch/    {zhuopin_max_id}<br>
<br>
If you encounter any problems, you can visit {config.SITE_URL} or send mail to {config.EMAIL_SENDER or "the administrator"} for support<br>
<br>
Thank you,<br>
The Sbox Team
            """
            email_send.email(
                genggai.caxu(session.get("username"), 4),
                con,
                "[Sbox]You uploaded a repository of works",
            )
            return render_template(
                "information.html",
                Information=f"感谢提交！你的作品名是 {name}，简介是 {jianjie}，文件已上传：{new_filename}",
            )
        else:
            return render_template("information.html", Information="文件格式不支持！")

    return render_template("tougao.html", nav=nav)


# NOTE:%1% scratch作品展示 XXX: 需要重构，避免代码重复和冗余
@scratch_bp.route("/scratch/<id>", methods=["GET", "POST"])
def scratch_word2(id):
    page = request.args.get("page")

    if page == "wikis":
        if (
            sdb.up(
                "user.sdb",
                "id_社区版本_" + str(genggai.caxu(session.get("username"), 0)),
            )
            == "教育版"
        ):
            return redirect(url_for("scratch.scratch_word2", id=id))
        if session.get("username") == None:
            return redirect(url_for("main.login"))

        a = ""
        author = sdb.up("zhuopin.sdb", "作品作者_id_" + str(id))
        if session.get("username") == author:
            a = f'<a href="/scratch/{id}?page=Management">管理</a>'

        # 获取原始简介内容
        raw_jianjie = sdb.up("zhuopin.sdb", "作品_id_简介_" + str(id))

        # 转换为 HTML
        html = markdown.markdown(raw_jianjie, extensions=["extra"])

        # 白名单过滤 HTML 标签和属性
        clean_html = bleach.clean(
            html,
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
                "img": ["src", "alt", "title", "width", "height"],
                "table": ["border", "cellpadding", "cellspacing"],
            },
            protocols=["http", "https", "mailto"],
            strip=True,
        )

        return render_template(
            "work_wiki.html",
            nav=nav,
            license=sdb.up("zhuopin.sdb", "作品_id_协议_" + str(id)),
            a=a,
            id=id,
            filename=sdb.up("zhuopin.sdb", "作品名称_id_" + str(id)),
            username=author,
            jianjie=clean_html,
        )
    elif page == "Management":
        if session.get("username") is None:
            return redirect(url_for("main.login"))

        user_key_suffix = genggai.caxu(session.get("username"), 0)
        if not user_key_suffix:
            return render_template(
                "information.html", Information="用户名无效，请确认用户名是否正确"
            )

        if not sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)) == session.get("username"):
            return render_template("information.html", Information="权限错误")

        user_key = f"用户所有作品_id_{user_key_suffix}"

        user_works = sdb.up("zhuopin.sdb", user_key)

        if not (int(id) in ast.literal_eval(user_works) or str(id) in ast.literal_eval(user_works)):
            wenz = [
                "喵~主人，是不是又做了什么让人心动的事情？我都快忍不住想要扑过来了~",
                "喵~ 主人今天看起来真是魅力四射呀，简直让人无法抗拒呢~",
            ]
            return render_template("520.html", wenz=wenz[0]), 520

        if request.method == "POST":
            # 获取表单数据
            gexing = request.form["geixing"]
            jianjie = request.form["jianjie"]

            sdb.down("zhuopin.sdb", f"作品名称_id_{id}", gexing)
            sdb.down("zhuopin.sdb", f"作品_id_简介_{id}", jianjie)

            if "cover" in request.files:
                file = request.files["cover"]
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_ext = os.path.splitext(filename)[1].lower()

                    if file_ext == ".svg":
                        # Handle SVG file - convert to PNG
                        temp_svg_path = os.path.join(UPLOAD_FOLDER, f"{id}_temp.svg")
                        final_png_path = os.path.join(UPLOAD_FOLDER, f"{id}.png")

                        # Save the uploaded SVG file temporarily
                        file.save(temp_svg_path)

                        # Convert SVG to PNG
                        if svg_to_png(temp_svg_path, final_png_path):
                            # Remove the temporary SVG file
                            os.remove(temp_svg_path)
                        else:
                            # If conversion fails, remove the temp file and return error
                            if os.path.exists(temp_svg_path):
                                os.remove(temp_svg_path)
                            return "SVG to PNG conversion failed"
                    elif allowed_file(file.filename, ALLOWED_EXTENSIONS):
                        # Handle regular image files - save as PNG
                        filename = f"{id}.png"  # Save as <id>.png
                        file.save(os.path.join(UPLOAD_FOLDER, filename))

            if "new_version" in request.files:
                html_file = request.files["new_version"]
                if html_file and (
                    html_file.filename.endswith(".sb3") or html_file.filename.endswith(".html")
                ):
                    # 根据文件类型确定备份和保存的文件名
                    file_ext = ".sb3" if html_file.filename.endswith(".sb3") else ".html"
                    old_file_path = os.path.join(
                        current_app.config["SCRATCH_FOLDER"], f"{id}{file_ext}"
                    )
                    backup_folder = current_app.config.get(
                        "SCRATCH_OLD_FOLDER", "scratch_old"
                    )  # 默认为 scratch_old

                    # 确保备份目录存在
                    os.makedirs(backup_folder, exist_ok=True)

                    # 如果旧文件存在，则备份
                    if os.path.exists(old_file_path):
                        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                        backup_filename = f"{id}-{timestamp}{file_ext}"
                        backup_path = os.path.join(backup_folder, backup_filename)
                        shutil.copy(old_file_path, backup_path)  # 复制旧文件到备份目录

                html_file = request.files["new_version"]
                if html_file and (
                    html_file.filename.endswith(".sb3") or html_file.filename.endswith(".html")
                ):
                    # 根据上传的文件类型确定保存的文件名
                    file_ext = ".sb3" if html_file.filename.endswith(".sb3") else ".html"
                    html_filename = f"{id}{file_ext}"
                    html_file.save(
                        os.path.join(current_app.config["SCRATCH_FOLDER"], html_filename)
                    )  # 保存到 scratch 文件夹

            # 更新后重新获取个性和简介数据
            gexing1 = sdb.up("zhuopin.sdb", f"作品名称_id_{id}")
            jianjie1 = sdb.up("zhuopin.sdb", f"作品_id_简介_{id}")

            return redirect(url_for("scratch.scratch_word2", id=id))  # 返回成功提示

        gexing1 = sdb.up("zhuopin.sdb", f"作品名称_id_{id}")  # 获取个性数据
        jianjie1 = sdb.up("zhuopin.sdb", f"作品_id_简介_{id}")  # 获取简介数据
        a = ""
        author = sdb.up("zhuopin.sdb", "作品作者_id_" + str(id))
        if session.get("username") == author:
            a = f'<a href="/scratch/{id}?page=Management">管理</a>'
        return render_template(
            "work_Management.html",
            a=a,
            license=sdb.up("zhuopin.sdb", "作品_id_协议_" + str(id)),
            filename=sdb.up("zhuopin.sdb", "作品名称_id_" + str(id)),
            username=sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)),
            nav=nav,
            id=id,
            gexing1=gexing1,
            jianjie1=jianjie1,
        )
    elif page == "license":
        # 检查用户是否登录
        if session.get("username") is None:
            return redirect(url_for("main.login"))
        if (
            sdb.up(
                "user.sdb",
                "id_社区版本_" + str(genggai.caxu(session.get("username"), 0)),
            )
            == "教育版"
        ):
            return redirect(url_for("scratch.scratch_word2", id=id))
        a = ""
        # 从数据库中获取作品协议
        license = sdb.up("zhuopin.sdb", "作品_id_协议_" + str(id))
        # 白名单：只允许已知的协议文件名
        ALLOWED_LICENSES = {
            "mit",
            "apache-2.0",
            "gpl-3.0",
            "lgpl-3.0",
            "bsd-2-clause",
            "bsd-3-clause",
            "mpl-2.0",
            "cc-by-4.0",
            "cc-by-sa-4.0",
            "cc0-1.0",
            "unlicense",
            "agpl-3.0",
        }
        license_clean = license.strip().lower()
        if license_clean not in ALLOWED_LICENSES:
            license_clean = "mit"
        license_file = f"license/{license_clean}.txt"

        # 读取协议内容
        licenses = ""
        # 检查协议文件是否存在
        if os.path.exists(license_file):
            # 读取协议文件内容
            with open(license_file, "r", encoding="utf-8") as f:
                licenses = f.read()

        # 检查是否为作者
        if session.get("username") == sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)):
            a = f'<a href="/scratch/{id}?page=Management">管理</a>'

        return render_template(
            "work_license.html",
            license=sdb.up("zhuopin.sdb", "作品_id_协议_" + str(id)),
            a=a,
            nav=nav,
            id=id,
            filename=sdb.up("zhuopin.sdb", "作品名称_id_" + str(id)),
            username=sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)),
            licenses=licenses,
        )
    elif page == "master":
        a = ""
        if session.get("username") == sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)):
            a = f'<a href="/scratch/{id}?page=Management">管理</a>'
        if (
            sdb.up(
                "user.sdb",
                "id_社区版本_" + str(genggai.caxu(session.get("username"), 0)),
            )
            == "教育版"
        ):
            return redirect(url_for("scratch.scratch_word2", id=id))
        gk = sdb.up("zhuopin.sdb", "作品观看数量_id_" + id)
        if gk == "" or gk == None:
            gk = 0
        gk = int(gk) + 1
        sdb.down("zhuopin.sdb", "作品观看数量_id_" + id, gk)
        good = sdb.up("zhuopin.sdb", "作品点赞_id_" + str(id))
        star = sdb.up("zhuopin.sdb", "作品收藏_id_" + str(id))
        Download = sdb.up("zhuopin.sdb", "作品下载_id_" + str(id))
        if good == None:
            good = "0"
        return render_template(
            "work_master.html",
            Download=Download,
            license=sdb.up("zhuopin.sdb", "作品_id_协议_" + str(id)),
            nav=nav,
            a=a,
            gk=gk,
            star=star,
            good=good,
            id=id,
            filename=sdb.up("zhuopin.sdb", "作品名称_id_" + str(id)),
            username=sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)),
            jianjie=bleach.clean(
                markdown.markdown(sdb.up("zhuopin.sdb", "作品_id_简介_" + str(id))),
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
                    "img": ["src", "alt", "title", "width", "height"],
                },
                protocols=["http", "https", "mailto"],
                strip=True,
            ),
        )
    elif page == "Issues":
        try:
            if session.get("username") == None:
                return redirect(url_for("main.login"))
            a = ""
            if (
                sdb.up(
                    "user.sdb",
                    "id_社区版本_" + str(genggai.caxu(session.get("username"), 0)),
                )
                == "教育版"
            ):
                return redirect(url_for("scratch.scratch_word2", id=id))
            if session.get("username") == sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)):
                a = f'<a href="/scratch/{id}?page=Management">管理</a>'
            if "" == sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)):
                return render_template("work_Issues.html", id=id, issues="不存在的作品")

            user = session.get("username")
            Issues = ast.literal_eval(sdb.up("Issues.sdb", "Issues_id_" + str(id)))
            if Issues == "":
                Issues = []
            if request.method == "POST":
                if "" == sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)):
                    return render_template("work_Issues.html", id=id, issues="不存在的作品")
                issue_content = request.form.get("issue_content")
                issue_type = request.form.get(
                    "issue_type", "general"
                )  # Default to 'general' if not provided
                if issue_content:
                    # Add issue type prefix if it's a bug
                    if issue_type == "bug":
                        tall = user + " [BUG]：" + issue_content
                    else:
                        tall = user + "：" + issue_content

                    Issues.insert(0, tall)  # 在索引0位置插入元素

                    sdb.down("Issues.sdb", "Issues_id_" + str(id), Issues)
                    message = sdb.up(
                        "zhuopin.sdb",
                        "作者消息_id_"
                        + str(genggai.caxu(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)), 0)),
                    )

                    if not isinstance(message, list):  # 确保是列表类型
                        message = []
                    if not message:
                        message = []
                    filename = sdb.up("zhuopin.sdb", "作品名称_id_" + str(id))
                    message.insert(
                        0,
                        session.get("username")
                        + " 给你作品"
                        + filename
                        + "提交 <strong>Issues</strong> 啦！",
                    )
                    sdb.down(
                        "zhuopin.sdb",
                        "作者消息_id_"
                        + str(genggai.caxu(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)), 0)),
                        message,
                    )

                    # Send email notification to the writer if it's a bug report
                    if issue_type == "bug":
                        try:
                            # Get the author's email
                            author_username = sdb.up("zhuopin.sdb", "作品作者_id_" + str(id))
                            author_email = genggai.caxu(
                                author_username, 4
                            )  # Assuming email is at index 4

                            # Prepare email content
                            email_subject = f"[Sbox] 作品 {filename} 收到新的 Bug 报告"
                            email_content = f"""
                            <p>你好 {author_username}，</p>
                            <p>你的作品 <strong>{filename}</strong> (ID: {id}) 收到了一个新的 Bug 报告：</p>
                            <p><strong>报告者：</strong>{user}</p>
                            <p><strong>问题描述：</strong>{issue_content}</p>
                            <p>请尽快查看并处理此 Bug 报告。</p>
                            <p>你可以通过以下链接访问问题页面：<a href="{config.SITE_URL}/scratch/{id}?page=Issues">查看 Issues</a></p>
                            <br>
                            <p>谢谢，</p>
                            <p>小盒子团队</p>
                            """

                            # Send email
                            email_send.email(author_email, email_content, email_subject)
                        except Exception as e:
                            logger.warning("发送邮件通知失败: %s", e)
                            # Continue without failing the issue submission
                return redirect(url_for("scratch.scratch_word2", id=id, page="Issues"))

            # 分页参数
            page_num = request.args.get("p", 1, type=int)
            per_page = 10  # 每页显示10条

            # 计算总页数
            total_issues = len(Issues)
            total_pages = (total_issues + per_page - 1) // per_page if total_issues > 0 else 1

            # 确保页码在有效范围内
            if page_num < 1:
                page_num = 1
            elif page_num > total_pages:
                page_num = total_pages

            # 获取当前页的 Issues
            start_idx = (page_num - 1) * per_page
            end_idx = start_idx + per_page
            paginated_issues = Issues[start_idx:end_idx]

            return render_template(
                "work_Issues.html",
                nav=nav,
                license=sdb.up("zhuopin.sdb", "作品_id_协议_" + str(id)),
                a=a,
                id=id,
                filename=sdb.up("zhuopin.sdb", "作品名称_id_" + str(id)),
                username=sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)),
                issues=paginated_issues,
                current_page=page_num,
                total_pages=total_pages,
                total_issues=total_issues,
            )
        except:
            Issues = []
            tall = "由于系统问题，已自动清除格式错误的评论，而并非删除评论"

            Issues.insert(0, tall)
            sdb.down("Issues.sdb", "Issues_id_" + str(id), Issues)
            return redirect(url_for("scratch.scratch_word2", id=id, page="Issues"))

    # Ajax 分页 API 端点
    elif page == "Issues_api":
        try:
            Issues = ast.literal_eval(sdb.up("Issues.sdb", "Issues_id_" + str(id)))
            if Issues == "" or Issues is None:
                Issues = []

            # 分页参数
            page_num = request.args.get("p", 1, type=int)
            per_page = 10  # 每页显示10条

            # 计算总页数
            total_issues = len(Issues)
            total_pages = (total_issues + per_page - 1) // per_page if total_issues > 0 else 1

            # 确保页码在有效范围内
            if page_num < 1:
                page_num = 1
            elif page_num > total_pages:
                page_num = total_pages

            # 获取当前页的 Issues
            start_idx = (page_num - 1) * per_page
            end_idx = start_idx + per_page
            paginated_issues = Issues[start_idx:end_idx]

            return jsonify(
                {
                    "issues": paginated_issues,
                    "current_page": page_num,
                    "total_pages": total_pages,
                    "total_issues": total_issues,
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    elif page == "Download":
        # 检查用户是否已登录
        if session.get("username") == None:
            return redirect(url_for("main.login"))
        if (
            sdb.up(
                "user.sdb",
                "id_社区版本_" + str(genggai.caxu(session.get("username"), 0)),
            )
            == "教育版"
        ):
            return redirect(url_for("scratch.scratch_word2", id=id))
        try:
            # 获取作品id
            filename = f"{id}.html"
            # 获取作品所在文件夹
            directory = current_app.config["SCRATCH2_FOLDER"]
            # 发送作品文件
            num = sdb.up("zhuopin.sdb", "作品下载_id_" + str(id))
            if num == "":
                num = 0
            sdb.down("zhuopin.sdb", "作品下载_id_" + str(id), int(num) + 1)
            return send_from_directory(
                directory=directory,
                path=filename,
                as_attachment=True,
                download_name=filename,
            )
        except:
            # 如果作品文件不存在，则查询作品协议
            license = sdb.up("zhuopin.sdb", "作品_id_协议_" + str(id))
            # 如果作品协议为closed或不开源，则返回不可拷贝
            if license == "closed" or license == "不开源":
                return "不可拷贝！", 520
            # 否则，发送作品文件
            else:
                filename = f"{id}.sb3"
                directory = current_app.config["SCRATCH2_FOLDER"]
                num = sdb.up("zhuopin.sdb", "作品下载_id_" + str(id))
                if num == "":
                    num = 0
                sdb.down("zhuopin.sdb", "作品下载_id_" + str(id), int(num) + 1)
                return send_from_directory(
                    directory=directory,
                    path=filename,
                    as_attachment=True,
                    download_name="sbox-scratch.sb3",
                )

    status = sdb.up("zhuopin.sdb", "作品状态_id_" + id)
    if not status == "":
        status_next = sdb.up("zhuopin.sdb", "作品状态内容_id_" + id)
        return f"作品状态异常，详情：{status_next}"

    zhuozhe = sdb.up(
        "zhuopin.sdb",
        "作者状态内容_id_" + str(genggai.caxu(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)), 0)),
    )
    if not zhuozhe == "":
        return f"作者状态异常，详情：{zhuozhe}"

    gk = sdb.up("zhuopin.sdb", "作品观看数量_id_" + id)
    if gk == "" or gk == None:
        gk = 0
    gk = int(gk) + 1
    sdb.down("zhuopin.sdb", "作品观看数量_id_" + id, gk)

    good = sdb.up("zhuopin.sdb", "作品点赞_id_" + str(id))
    star = sdb.up("zhuopin.sdb", "作品收藏_id_" + str(id))

    if good == None:
        good = "0"
    a = ""
    license = sdb.up("zhuopin.sdb", "作品_id_协议_" + str(id))

    if session.get("username") == sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)):
        a = f'<a href="/scratch/{id}?page=Management">管理</a>'

    sbox = sdb.up("zhuopin.sdb", "作品_id_编辑器_" + str(id))

    caz = "/works/" + id

    if (
        sdb.up("user.sdb", "id_社区版本_" + str(genggai.caxu(session.get("username"), 0)))
        == "社区版"
    ):
        return render_template(
            "work_detail.html",
            nav=nav,
            license=license,
            star=star,
            good=good,
            id=id,
            gk=gk,
            a=a,
            raw_jianjie=sdb.up("zhuopin.sdb", "作品_id_简介_" + str(id)),
            caz=caz,  # 拼接路径，确保正确的文件扩展名
            filename=sdb.up("zhuopin.sdb", "作品名称_id_" + str(id)),  # 获取不带扩展名的文件名
            username=sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)),  # 假设用户名是 ID
            jianjie=bleach.clean(
                markdown.markdown(sdb.up("zhuopin.sdb", "作品_id_简介_" + str(id))),
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
                    "img": ["src", "alt", "title", "width", "height"],
                },
                protocols=["http", "https", "mailto"],
                strip=True,
            ),
            url="/user/{}".format(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id))),
        )
    elif (
        sdb.up("user.sdb", "id_社区版本_" + str(genggai.caxu(session.get("username"), 0)))
        == "专业版"
    ):
        return render_template(
            "scratch_NEXT.html",
            nav=nav,
            license=license,
            star=star,
            good=good,
            id=id,
            gk=gk,
            a=a,
            caz=caz,  # 拼接路径，确保正确的文件扩展名
            filename=sdb.up("zhuopin.sdb", "作品名称_id_" + str(id)),  # 获取不带扩展名的文件名
            username=sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)),  # 假设用户名是 ID
            jianjie=bleach.clean(
                markdown.markdown(sdb.up("zhuopin.sdb", "作品_id_简介_" + str(id))),
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
                    "img": ["src", "alt", "title", "width", "height"],
                },
                protocols=["http", "https", "mailto"],
                strip=True,
            ),
            url="/user/{}".format(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id))),
        )
    else:
        return render_template(
            "scratch_edu.html",
            nav=nav,
            license=license,
            star=star,
            good=good,
            id=id,
            gk=gk,
            a=a,
            caz=caz,  # 拼接路径，确保正确的文件扩展名
            filename=sdb.up("zhuopin.sdb", "作品名称_id_" + str(id)),  # 获取不带扩展名的文件名
            username=sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)),  # 假设用户名是 ID
            jianjie=bleach.clean(
                markdown.markdown(sdb.up("zhuopin.sdb", "作品_id_简介_" + str(id))),
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
                    "img": ["src", "alt", "title", "width", "height"],
                },
                protocols=["http", "https", "mailto"],
                strip=True,
            ),
            url="/user/{}".format(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id))),
        )


# NOTE:丢到上面/scratch/<id>
@scratch_bp.route("/scratch/<id>/")
def scratch_word3(id):
    return redirect(url_for("scratch.scratch_word2", id=id))


# NOTE: 下面是/scratch的主页路由，展示推荐作品和随机作品等内容 XXX: 需要重构，避免代码重复和冗余
@scratch_bp.route("/scratch")
def scratch_index():
    zhueixinxinwen = sdb.up("xinwen.sdb", "新闻模块_新闻最大编号")
    # Get zhuopin max ID with error handling
    try:
        zhuopin_max_id = int(sdb.up("zhuopin.sdb", "作品最大id")) - 1
        if zhuopin_max_id < 1:
            zhuopin_max_id = 1
    except (ValueError, TypeError):
        zhuopin_max_id = 1
    if not session.get("username") == None:
        sdb.down("user.sdb", "个人默认首页_name_" + session.get("username"), "scratch")

    # 随机选择6个优秀scratch作品
    Excellent_scratch_1 = Excellent_scratch[0]
    Excellent_scratch_work_1 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_1))
    Excellent_scratch_2 = Excellent_scratch[1]
    Excellent_scratch_work_2 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_2))
    Excellent_scratch_3 = Excellent_scratch[2]
    Excellent_scratch_work_3 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_3))
    Excellent_scratch_4 = Excellent_scratch[0]
    Excellent_scratch_work_4 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_4))
    Excellent_scratch_5 = Excellent_scratch[1]
    Excellent_scratch_work_5 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_5))
    Excellent_scratch_6 = Excellent_scratch[2]
    Excellent_scratch_work_6 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_6))

    # 随机选择6个scratch作品
    import random

    scid1 = random.randint(1, zhuopin_max_id)
    zhuopin1 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid1))
    scid2 = random.randint(1, zhuopin_max_id)
    zhuopin2 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid2))
    scid3 = random.randint(1, zhuopin_max_id)
    zhuopin3 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid3))
    scid4 = random.randint(1, zhuopin_max_id)
    zhuopin4 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid4))
    scid5 = random.randint(1, zhuopin_max_id)
    zhuopin5 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid5))
    scid6 = random.randint(1, zhuopin_max_id)
    zhuopin6 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid6))

    scratch_tueijian = [30, 28, 32]
    Excellent_scratch_7 = scratch_tueijian[0]
    Excellent_scratch_work_7 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_7))
    Excellent_scratch_8 = scratch_tueijian[1]
    Excellent_scratch_work_8 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_8))
    Excellent_scratch_9 = scratch_tueijian[2]
    Excellent_scratch_work_9 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_9))
    Excellent_scratch_10 = scratch_tueijian[0]
    Excellent_scratch_work_10 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_10))
    Excellent_scratch_11 = scratch_tueijian[1]
    Excellent_scratch_work_11 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_11))
    Excellent_scratch_12 = scratch_tueijian[2]
    Excellent_scratch_work_12 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_12))

    # 选择最后6个scratch作品
    scid7 = zhuopin_max_id
    zhuopin7 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid7))
    scid8 = zhuopin_max_id - 1
    zhuopin8 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid8))
    scid9 = zhuopin_max_id - 2
    zhuopin9 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid9))
    scid10 = zhuopin_max_id - 3
    zhuopin10 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid10))
    scid11 = zhuopin_max_id - 4
    zhuopin11 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid11))
    scid12 = zhuopin_max_id - 5
    zhuopin12 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid12))

    hhh = count_files_recursively("uploads")
    yh = count_subdirectories("uploads")
    return render_template(
        "index3.html",
        nav=nav,
        Excellent_scratch_1=Excellent_scratch_1,
        Excellent_scratch_2=Excellent_scratch_2,
        Excellent_scratch_3=Excellent_scratch_3,
        Excellent_scratch_4=Excellent_scratch_4,
        Excellent_scratch_5=Excellent_scratch_5,
        Excellent_scratch_6=Excellent_scratch_6,
        Excellent_scratch_7=Excellent_scratch_7,
        Excellent_scratch_8=Excellent_scratch_8,
        Excellent_scratch_9=Excellent_scratch_9,
        Excellent_scratch_10=Excellent_scratch_10,
        Excellent_scratch_11=Excellent_scratch_11,
        Excellent_scratch_12=Excellent_scratch_12,
        Excellent_scratch_work_1=Excellent_scratch_work_1,
        Excellent_scratch_work_2=Excellent_scratch_work_2,
        Excellent_scratch_work_3=Excellent_scratch_work_3,
        Excellent_scratch_work_4=Excellent_scratch_work_4,
        Excellent_scratch_work_5=Excellent_scratch_work_5,
        Excellent_scratch_work_6=Excellent_scratch_work_6,
        Excellent_scratch_work_7=Excellent_scratch_work_7,
        Excellent_scratch_work_8=Excellent_scratch_work_8,
        Excellent_scratch_work_9=Excellent_scratch_work_9,
        Excellent_scratch_work_10=Excellent_scratch_work_10,
        Excellent_scratch_work_11=Excellent_scratch_work_11,
        Excellent_scratch_work_12=Excellent_scratch_work_12,
        scid12=scid12,
        scid11=scid11,
        scid10=scid10,
        scid9=scid9,
        scid8=scid8,
        scid7=scid7,
        scid6=scid6,
        scid4=scid4,
        scid5=scid5,
        scid2=scid2,
        scid3=scid3,
        scid1=scid1,
        zhuopin12=zhuopin12,
        zhuopin11=zhuopin11,
        zhuopin10=zhuopin10,
        zhuopin9=zhuopin9,
        zhuopin8=zhuopin8,
        zhuopin6=zhuopin6,
        zhuopin7=zhuopin7,
        zhuopin5=zhuopin5,
        zhuopin4=zhuopin4,
        zhuopin2=zhuopin2,
        zhuopin3=zhuopin3,
        zhuopin1=zhuopin1,
        shenfen=genggai.caxu(session.get("username"), 3),
    )


# NOTE:scratch点赞功能，增加作者金币和消息通知
@scratch_bp.route("/scratchlike=<id>", methods=["GET", "POST"])
def scratch_good(id):
    # 判断用户是否登录
    if session.get("username") == None:
        return redirect(url_for("main.login"))

    # 获取当前用户信息
    user = genggai.caxu(session.get("username"), 0)

    # 判断用户是否已经验证邮箱
    if genggai.caxu(session.get("username"), 4) == None:
        return render_template(
            "information.html", Information="用户应该要身份凭证完整（你没有验证邮箱）"
        )

    # 获取作品最大id
    # Get zhuopin max ID with error handling
    try:
        zhuopin_max_id = int(sdb.up("zhuopin.sdb", "作品最大id")) - 1
        if zhuopin_max_id < 1:
            zhuopin_max_id = 1
    except (ValueError, TypeError):
        zhuopin_max_id = 1
    # 判断作品id是否合法
    if zhuopin_max_id < int(id):
        return render_template("information.html", Information="权限未知")

    # 获取作品点赞用户列表
    gooduser = sdb.up("zhuopin.sdb", "作品点赞用户_id_" + str(id))

    # 如果gooduser为None，则初始化为空列表
    if gooduser == None:
        gooduser = []  # 如果gooduser为None，则初始化为空列表

    # 如果gooduser是字符串，将其转换为列表
    if isinstance(gooduser, str):
        gooduser = gooduser.split(",")  # 将字符串分割为列表

    # 过滤掉空字符串
    gooduser = [g for g in gooduser if g.strip()]

    # 将gooduser中的元素转换为整数并进行比较
    if user in map(int, gooduser):  # 将gooduser中的元素转换为整数并进行比较
        good = sdb.up("zhuopin.sdb", "作品点赞_id_" + str(id))
        return jsonify({"like": good})
    else:
        gooduser.append(str(user))  # 如果user是整数，将其转换为字符串存储
        sdb.down(
            "zhuopin.sdb", "作品点赞用户_id_" + str(id), ",".join(gooduser)
        )  # 更新点赞用户列表
        good = sdb.up("zhuopin.sdb", "作品点赞_id_" + str(id))  # 获取当前点赞数

        # 确保good是整数类型，然后执行加法操作
        try:
            good = int(good)  # 尝试将good转换为整数
        except (ValueError, TypeError):  # 如果转换失败，默认设置为0
            good = 0

        good = good + 1

        sdb.down("zhuopin.sdb", "作品点赞_id_" + str(id), good)  # 更新点赞数

        # 获取作者金币
        money = sdb.up(
            "zhuopin.sdb",
            "作者金币_id_" + str(genggai.caxu(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)), 0)),
        )
        # 如果作者金币为空，则设置为0
        if money == "" or money == None:
            money = 0
        # 作者金币加1
        money = int(money) + 1
        # 更新作者金币
        sdb.down(
            "zhuopin.sdb",
            "作者金币_id_" + str(genggai.caxu(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)), 0)),
            money,
        )

        message = sdb.up(
            "zhuopin.sdb",
            "作者消息_id_" + str(genggai.caxu(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)), 0)),
        )
        if not isinstance(message, list):  # 确保是列表类型
            message = []
        if not message:
            message = []
        filename = sdb.up("zhuopin.sdb", "作品名称_id_" + str(id))
        message.insert(0, session.get("username") + " 给你作品" + filename + "点赞啦！")
        sdb.down(
            "zhuopin.sdb",
            "作者消息_id_" + str(genggai.caxu(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)), 0)),
            message,
        )

        return jsonify({"like": good})


# NOTE: 收藏功能和点赞功能分开，收藏功能不增加作者金币，点赞功能增加作者金币
@scratch_bp.route("/scratchstar=<id>", methods=["GET", "POST"])
def scratch_star(id):
    # 检查用户是否已登录，如果未登录则跳转到登录页面
    if session.get("username") is None:
        return redirect(url_for("main.login"))

    # 检查用户是否已验证邮箱，如果未验证则跳转到提示页面
    if genggai.caxu(session.get("username"), 4) == None:
        return render_template(
            "information.html", Information="用户应该要身份凭证完整（你没有验证邮箱）"
        )

    # 获取数据库中作品最大id
    # Get zhuopin max ID with error handling
    try:
        zhuopin_max_id = int(sdb.up("zhuopin.sdb", "作品最大id")) - 1
        if zhuopin_max_id < 1:
            zhuopin_max_id = 1
    except (ValueError, TypeError):
        zhuopin_max_id = 1
    # 如果传入的id大于作品最大id，则跳转到提示页面
    if zhuopin_max_id < int(id):
        return render_template("information.html", Information="权限未知")

    # 获取用户信息
    user = genggai.caxu(session.get("username"), 0)
    # 获取用户收藏的作品id列表
    gooduser = sdb.up("zhuopin.sdb", "用户收藏_id_" + str(user))

    # 如果 gooduser 是字符串，尝试将其转换为列表
    if isinstance(gooduser, str):
        gooduser = gooduser.split(",")  # 假设数据库中的字符串是以逗号分隔的id列表
    elif gooduser is None:
        gooduser = []  # 如果 gooduser 为 None，则初始化为空列表

    # 确保 id 是字符串类型，避免类型错误
    if str(id) in gooduser:
        # 如果 id 在用户收藏列表中，则将其移除，并更新数据库
        gooduser.remove(str(id))
        sdb.down(
            "zhuopin.sdb", "用户收藏_id_" + str(user), ",".join(gooduser)
        )  # 使用逗号连接成字符串存储
        good = sdb.up("zhuopin.sdb", "作品收藏_id_" + str(id))
        good = good - 1
        sdb.down("zhuopin.sdb", "作品收藏_id_" + str(id), good)
        return jsonify({"star": good})
    else:
        # 如果 id 不在用户收藏列表中，则将其添加，并更新数据库
        gooduser.append(str(id))  # 将 id 添加到 gooduser 列表中
        sdb.down(
            "zhuopin.sdb", "用户收藏_id_" + str(user), ",".join(gooduser)
        )  # 使用逗号连接成字符串存储
        good = sdb.up("zhuopin.sdb", "作品收藏_id_" + str(id))

        try:
            good = int(good)
        except (ValueError, TypeError):
            good = 0

        good = good + 1
        sdb.down("zhuopin.sdb", "作品收藏_id_" + str(id), good)

        message = sdb.up(
            "zhuopin.sdb",
            "作者消息_id_" + str(genggai.caxu(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)), 0)),
        )

        if not isinstance(message, list):  # 确保是列表类型
            message = []
        if not message:
            message = []
        filename = sdb.up("zhuopin.sdb", "作品名称_id_" + str(id))
        message.insert(0, session.get("username") + " 给你作品" + filename + "点star啦！")
        sdb.down(
            "zhuopin.sdb",
            "作者消息_id_" + str(genggai.caxu(sdb.up("zhuopin.sdb", "作品作者_id_" + str(id)), 0)),
            message,
        )

        return jsonify({"star": good})


# NOTE: 加载大型作品时，游客限制30MB，登录用户限制35MB，超过限制需要确认才能加载
@scratch_bp.route("/works/<id>")
def serve_large_html_file(id):
    if not re.match(r"^[a-zA-Z0-9_-]+$", id):
        return None, "Invalid ID format"
    # 根据传入的id获取文件名
    filename = id + ".sb3"
    # 获取文件路径
    file_path = os.path.join(current_app.config["SCRATCH2_FOLDER"], filename)
    UPLOAD_FOLDER = "scratch2"  # 项目文件存放目录
    MAX_SIZE = 35 * 1024 * 1024
    MAX_Tourist_SIZE = 30 * 1024 * 1024

    project_path = os.path.join(UPLOAD_FOLDER, f"{id}.sb3")
    if not os.path.exists(project_path):
        project_path = os.path.join(UPLOAD_FOLDER, f"{id}.html")
    try:
        file_size = os.path.getsize(project_path)
    except:
        return redirect(url_for("loveyou"))

    confirm = request.args.get("confirm", "false")
    if file_size > MAX_Tourist_SIZE and confirm != "true" and session.get("username") == None:
        size_mb = round(file_size / (1024 * 1024), 2)
        return """
        游客不可加载比较大作品，快去登录吧喵~
        """
    elif file_size > MAX_SIZE and confirm != "true":
        size_mb = round(file_size / (1024 * 1024), 2)
        return render_template("confirm_load.html", size=size_mb, id=id)

    # 检查用户是否设置了默认使用Turbowarp加载.sb3文件
    use_turbowarp_default = False
    if session.get("username") != None:
        turbowarp_setting = sdb.up("user.sdb", "个人默认_turbowarp_" + session.get("username"))
        if turbowarp_setting == "true" and project_path.endswith(".sb3"):
            use_turbowarp_default = True

    # 如果用户设置了默认使用Turbowarp，直接使用Turbowarp加载
    if use_turbowarp_default:
        caz = (
            config.TURBOWARP_ORIGIN
            + "/embed?project_url="
            + config.SITE_URL
            + "/scratchwork/"
            + id
            + ".sb3&autoplay&hqpen&allow_unsigned_extensions=1&disable_embedded_extensions=1&disable_embedded_extensions=1&extension_url_shangcloud="
            + config.SCRATCH_EXTENSION_URL
        )
        return redirect(caz)

    # 检查作品是否设置了使用Turbowarp
    sbox = sdb.up("zhuopin.sdb", "作品_id_编辑器_" + str(id))
    if sbox == "turbowarp":
        caz = (
            config.TURBOWARP_ORIGIN
            + "/embed?project_url="
            + config.SITE_URL
            + "/scratchwork/"
            + id
            + ".sb3&autoplay&hqpen&allow_unsigned_extensions=1&disable_embedded_extensions=1&disable_embedded_extensions=1&extension_url_shangcloud="
            + config.SCRATCH_EXTENSION_URL
        )
        return redirect(caz)
    # 如果文件存在且以.sb3结尾，则重定向到/player.html页面
    if os.path.isfile(file_path) and file_path.endswith(".sb3"):
        return redirect(f"/player.html?aid={id}")

    try:
        # 如果文件不存在，则获取.html文件
        filename = id + ".html"
        file_path = os.path.join(current_app.config["SCRATCH2_FOLDER"], filename)

        # 安全检查：确保文件路径在允许的目录内
        if (
            not os.path.commonprefix([file_path, current_app.config["SCRATCH2_FOLDER"]])
            == current_app.config["SCRATCH2_FOLDER"]
        ):
            return None, 403

        # 检查文件是否存在
        if os.path.exists(file_path):
            # 获取文件的最后修改时间
            file_mtime = os.path.getmtime(file_path)
            file_mtime_dt = datetime.fromtimestamp(file_mtime)
            file_mtime_str = file_mtime_dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

            # 创建响应对象
            response = Response()

            # 设置缓存控制头部
            response.headers["Last-Modified"] = file_mtime_str
            response.headers["Cache-Control"] = "public, max-age=86400"

            # 检查浏览器的 If-Modified-Since 头部
            if request.if_modified_since:
                try:
                    # 判断 if_modified_since 是否为 datetime 对象
                    if isinstance(request.if_modified_since, str):
                        # 如果是字符串，使用 strptime 解析为 datetime 对象
                        if_modified_since_dt = datetime.strptime(
                            request.if_modified_since, "%a, %d %b %Y %H:%M:%S GMT"
                        )
                    elif isinstance(request.if_modified_since, datetime):
                        # 如果已经是 datetime 对象，则直接使用
                        if_modified_since_dt = request.if_modified_since

                    # 比较文件的修改时间与 If-Modified-Since 的时间
                    if if_modified_since_dt >= file_mtime_dt:
                        return "", 304
                except ValueError:
                    pass

            # 获取文件大小并决定是否强制缓存（小于10MB的文件）
            file_size = os.path.getsize(file_path)
            if file_size < 10 * 1024 * 1024:  # 小于10MB
                # 读取整个文件并缓存
                with open(file_path, "rb") as f:
                    file_data = f.read()

                # 设置响应头
                response.data = file_data
                response.headers["Content-Length"] = len(file_data)
                return response

            # 获取 Range 请求头，判断是否需要返回部分内容
            range_header = request.headers.get("Range", None)
            if range_header:
                # 解析 Range 头部
                byte1, byte2 = range_header.strip().replace("bytes=", "").split("-")
                byte1 = int(byte1)
                byte2 = int(byte2) if byte2 else None  # 如果没有 byte2，读取到文件末尾

                if byte2 is None or byte2 > file_size - 1:
                    byte2 = file_size - 1

                # 检查 Range 是否有效
                if byte1 > byte2 or byte1 >= file_size:
                    return render_template("information.html", Information="Range not satisfiable")
                # 打开文件并返回指定部分
                with open(file_path, "rb") as f:
                    f.seek(byte1)
                    data = f.read(byte2 - byte1 + 1)

                # 设置响应头
                response = Response(data, status=206)
                response.headers["Content-Range"] = f"bytes {byte1}-{byte2}/{file_size}"
                response.headers["Content-Length"] = len(data)
                return response
            else:
                # NOTE:如果没有 Range 请求头，返回完整文件
                def generate():
                    with open(file_path, "rb") as f:
                        while chunk := f.read(1024 * 64):  # 每次读取 64KB
                            yield chunk

                # 使用 StreamingResponse 流式返回
                return Response(generate())

        else:
            wenz = [
                "喵~主人，是不是又做了什么让人心动的事情？我都快忍不住想要扑过来了~",
                "喵~ 主人今天看起来真是魅力四射呀，简直让人无法抗拒呢~",
            ]
            return render_template("520.html", wenz=wenz[0]), 520

    except Exception as e:
        return "发生错误: 请尝试刷新再试", 500


# NOTE:定义serve_html_photo函数，根据id参数返回对应图片
@scratch_bp.route("/scratchphoto/<string:id>")
def serve_html_photo(id):
    try:
        # 根据id参数生成文件名
        filename = f"{id}.png"
        # 拼接文件路径
        file_path = os.path.join(current_app.config["SCRATCH2_PHOTO"], filename)

        # 判断文件是否存在
        if not os.path.exists(file_path):
            # 如果文件不存在，则使用默认图片
            filename = "scratch.png"

        # 从指定目录发送文件
        response = make_response(
            send_from_directory(current_app.config["SCRATCH2_PHOTO"], filename)
        )
        response.headers["Cache-Control"] = "public, max-age=1209600"  # 缓存2周
        response.headers["Expires"] = (datetime.now() + timedelta(seconds=1209600)).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
        return response
    except Exception as e:
        return "Server Error", 500


# NOTE:提供Scratch作品文件下载（.sb3格式）
@scratch_bp.route("/scratchwork/<id>.sb3")
def scratch_vm_viewer2(id):
    # 发送文件
    response = send_from_directory(
        current_app.config["SCRATCH_FOLDER"],
        f"{id}.sb3",
        mimetype="application/x-scratch-project",
        as_attachment=False,
    )

    # 关键CORS头设置
    response.headers["Access-Control-Allow-Origin"] = config.TURBOWARP_ORIGIN
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"

    # 新增缓存控制头
    response.headers["Cache-Control"] = "public, max-age=3600"

    return response


# NOTE:处理OPTIONS预检请求,与/scratchwork/<id>.sb3连用
@scratch_bp.route("/scratchwork/<id>.sb3", methods=["OPTIONS"])
def handle_options():
    return "", 204


# 导入必要的模块
from werkzeug.utils import secure_filename


# NOTE:递归统计目录文件数量
def count_files_recursively(directory):
    if not os.path.isdir(directory):
        return 0
    file_count = 0
    for root, dirs, files in os.walk(directory):
        file_count += len(files)
    return file_count


# NOTE:统计目录中子文件夹数量
def count_subdirectories(directory):
    if not os.path.isdir(directory):
        return 0
    entries = os.listdir(directory)
    subdirs = [entry for entry in entries if os.path.isdir(os.path.join(directory, entry))]
    return len(subdirs)
