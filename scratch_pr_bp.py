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

# NOTE: 这个模块实现了一个简单的PR系统，允许用户提交PR文件（.sb3格式）到指定的Scratch项目，并且项目作者可以审核这些PR（接受或拒绝）。PR信息存储在SQLite数据库中，包括提交者、文件路径、描述、状态等。用户可以查看PR详情和下载PR文件。

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
)
import os
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime
import genggai
import sdb

DATABASE = os.environ.get("SQLITE_DB", "sbox.db")

scratch_pr_bp = Blueprint("scratch_pr", __name__, url_prefix="/scratch_pr")

PR_FOLDER = "pr"
if not os.path.exists(PR_FOLDER):
    os.makedirs(PR_FOLDER)

ALLOWED_EXTENSIONS = {"sb3"}


# NOTE:检查上传文件是否为.sb3格式
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# NOTE:检查用户是否已登录
def check_login():
    return "username" in session


# NOTE:初始化PR数据库表
def init_pr_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        # 创建PR表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scratch_prs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                submitter_id INTEGER NOT NULL,
                submitter_username TEXT NOT NULL,
                file_path TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'pending',  -- pending, accepted, rejected
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewer_id INTEGER,
                review_comment TEXT,
                review_at TIMESTAMP
            )
        """)

        # 创建触发器，自动更新 updated_at 时间戳
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_pr_updated_at
            AFTER UPDATE ON scratch_prs
            FOR EACH ROW
            BEGIN
                UPDATE scratch_prs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)

        conn.commit()


# NOTE:提交PR到指定Scratch项目
@scratch_pr_bp.route("/submit/<int:project_id>", methods=["GET", "POST"])
def submit_pr(project_id):
    """提交PR到指定项目"""
    if not check_login():
        return redirect(url_for("main.login"))

    a = ""
    if session.get("username") == sdb.up("zhuopin.sdb", "作品作者_id_" + str(project_id)):
        a = f'<a href="/scratch/{project_id}?page=Management">管理</a>'
    # 检查项目是否存在
    project_name = sdb.up("zhuopin.sdb", f"作品名称_id_{project_id}")
    if not project_name:
        flash("项目不存在", "error")
        return redirect(url_for("scratch_word2", id=project_id))

    # 检查项目是否为开源项目（协议不是closed或不开源）
    license = sdb.up("zhuopin.sdb", f"作品_id_协议_{project_id}")
    if license in ["closed", "不开源"]:
        flash("该项目不是开源项目，无法提交PR", "error")
        return redirect(url_for("scratch_word2", id=project_id))

    if request.method == "POST":
        file = request.files.get("file")
        description = request.form.get("description", "").strip()

        if not file or not file.filename:
            flash("请选择要上传的.sb3文件", "error")
            return render_template(
                "scratch_pr/submit_pr.html",
                project_id=project_id,
                project_name=project_name,
                a=a,
            )

        if not description:
            flash("请填写PR说明", "error")
            return render_template(
                "scratch_pr/submit_pr.html",
                project_id=project_id,
                project_name=project_name,
                a=a,
            )

        if not allowed_file(file.filename):
            flash("文件格式不支持，仅支持.sb3文件", "error")
            return render_template(
                "scratch_pr/submit_pr.html",
                project_id=project_id,
                project_name=project_name,
                a=a,
            )

        # 保存文件
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"pr_{project_id}_{session['username']}_{timestamp}_{filename}"
        file_path = os.path.join(PR_FOLDER, unique_filename)

        file.save(file_path)

        # 获取提交者ID
        submitter_id = genggai.caxu(session["username"], 0)

        # 保存PR信息到数据库
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO scratch_prs (project_id, submitter_id, submitter_username, file_path, description)
                VALUES (?, ?, ?, ?, ?)
            """,
                (project_id, submitter_id, session["username"], file_path, description),
            )
            pr_id = cursor.lastrowid
            conn.commit()

        flash("PR提交成功", "success")
        return redirect(url_for("scratch_pr.view_pr", pr_id=pr_id))

    return render_template(
        "scratch_pr/submit_pr.html",
        project_id=project_id,
        project_name=project_name,
        a=a,
    )


# NOTE:查看项目的所有PR列表
@scratch_pr_bp.route("/project/<int:project_id>/prs")
def list_project_prs(project_id):
    """查看项目的所有PR"""
    if not check_login():
        return redirect(url_for("main.login"))
    a = ""
    if session.get("username") == sdb.up("zhuopin.sdb", "作品作者_id_" + str(project_id)):
        a = f'<a href="/scratch/{project_id}?page=Management">管理</a>'

    # 检查项目是否存在
    project_name = sdb.up("zhuopin.sdb", f"作品名称_id_{project_id}")
    if not project_name:
        flash("项目不存在", "error")
        return redirect(url_for("main.index"))

    # 检查当前用户是否是项目作者
    project_author = sdb.up("zhuopin.sdb", f"作品作者_id_{project_id}")
    is_author = session["username"] == project_author

    # 获取项目的所有PR
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if is_author:
            # 作者可以看到所有PR
            cursor.execute(
                """
                SELECT * FROM scratch_prs 
                WHERE project_id = ? 
                ORDER BY created_at DESC
            """,
                (project_id,),
            )
        else:
            # 其他用户只能看到已接受的PR
            cursor.execute(
                """
                SELECT * FROM scratch_prs 
                WHERE project_id = ? AND status = 'accepted'
                ORDER BY created_at DESC
            """,
                (project_id,),
            )

        prs = cursor.fetchall()

    return render_template(
        "scratch_pr/list_project_prs.html",
        project_id=project_id,
        project_name=project_name,
        prs=prs,
        a=a,
        is_author=is_author,
    )


# NOTE:查看单个PR详情
@scratch_pr_bp.route("/pr/<int:pr_id>")
def view_pr(pr_id):
    """查看单个PR详情"""
    if not check_login():
        return redirect(url_for("main.login"))

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scratch_prs WHERE id = ?", (pr_id,))
        pr = cursor.fetchone()

    if not pr:
        flash("PR不存在", "error")
        return redirect(url_for("main.index"))

    # 检查当前用户是否是项目作者或PR提交者
    project_author = sdb.up("zhuopin.sdb", f"作品作者_id_{pr['project_id']}")
    is_author = session["username"] == project_author
    is_submitter = session["username"] == pr["submitter_username"]
    id = code = request.args.get("id")

    if not (is_author or is_submitter):
        flash("您没有权限查看此PR", "error")
        return redirect(url_for("main.index"))
    else:
        if id:
            a = f'<a href="/scratch/{id}?page=Management">管理</a>'
        else:
            a = ""  # 如果没有提供id参数，则不显示管理链接

    # 获取项目信息
    project_name = sdb.up("zhuopin.sdb", f"作品名称_id_{pr['project_id']}")

    return render_template(
        "scratch_pr/view_pr.html",
        pr=pr,
        a=a,
        project_name=project_name,
        is_author=is_author,
    )


# NOTE:下载PR文件
@scratch_pr_bp.route("/pr/<int:pr_id>/download")
def download_pr(pr_id):
    """下载PR文件"""
    if not check_login():
        return redirect(url_for("main.login"))

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scratch_prs WHERE id = ?", (pr_id,))
        pr = cursor.fetchone()

    if not pr:
        flash("PR不存在", "error")
        return redirect(url_for("main.index"))

    # 检查当前用户是否是项目作者或PR提交者
    project_author = sdb.up("zhuopin.sdb", f"作品作者_id_{pr['project_id']}")
    is_author = session["username"] == project_author
    is_submitter = session["username"] == pr["submitter_username"]

    if not (is_author or is_submitter):
        flash("您没有权限下载此PR文件", "error")
        return redirect(url_for("main.index"))

    # 检查文件是否存在
    if not os.path.exists(pr["file_path"]):
        flash("PR文件不存在", "error")
        return redirect(url_for("scratch_pr.view_pr", pr_id=pr_id))

    directory = os.path.dirname(pr["file_path"])
    filename = os.path.basename(pr["file_path"])

    return send_from_directory(directory, filename, as_attachment=True)


# NOTE:审核PR，接受或拒绝PR请求
@scratch_pr_bp.route("/pr/<int:pr_id>/review", methods=["POST"])
def review_pr(pr_id):
    """审核PR（接受或拒绝）"""
    if not check_login():
        return redirect(url_for("main.login"))
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scratch_prs WHERE id = ?", (pr_id,))
        pr = cursor.fetchone()

    if not pr:
        flash("PR不存在", "error")
        return redirect(url_for("main.index"))

    # 检查当前用户是否是项目作者
    project_author = sdb.up("zhuopin.sdb", f"作品作者_id_{pr['project_id']}")
    if session["username"] != project_author:
        flash("您没有权限审核此PR", "error")
        return redirect(url_for("scratch_pr.view_pr", pr_id=pr_id))

    action = request.form.get("action")
    comment = request.form.get("comment", "").strip()

    if action not in ["accept", "reject"]:
        flash("无效的操作", "error")
        return redirect(url_for("scratch_pr.view_pr", pr_id=pr_id))

    # 更新PR状态
    reviewer_id = genggai.caxu(session["username"], 0)
    status = "accepted" if action == "accept" else "rejected"

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE scratch_prs 
            SET status = ?, reviewer_id = ?, review_comment = ?, review_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (status, reviewer_id, comment, pr_id),
        )
        conn.commit()

    flash(f"PR已{'接受' if action == 'accept' else '拒绝'}", "success")
    return redirect(url_for("scratch_pr.view_pr", pr_id=pr_id))


# 初始化数据库
init_pr_db()
