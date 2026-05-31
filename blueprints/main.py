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

# NOTE: 这个模块实现了主页面的功能，包括首页展示、GitHub登录、ZeroCat登录等。它使用Flask框架来处理HTTP请求，使用SQLite数据库来存储数据，并且集成了一些第三方服务的OAuth登录功能。首页会随机展示一些优秀的Scratch作品，并提供导航栏和页脚。GitHub登录和ZeroCat登录功能允许用户通过第三方账号进行授权登录，并且在登录成功后发送邮件通知用户。

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
import os
import json
import secrets
import logging
import requests
import urllib.parse
from urllib.parse import urlencode
import sdb
import genggai
import email_send
from utils.helpers import (
    check_email_registered,
    generate_pkce_pair,
    check_password_strength,
)
import config

logger = logging.getLogger(__name__)

try:
    from utils.db import get_db, DATABASE
except ImportError:
    from utils.database import DATABASE
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import pyotp
import qrcode
import io
import base64

DATABASE = os.environ.get("SQLITE_DB", "sbox.db")

# 配置限流器
limiter = Limiter(get_remote_address)

main_bp = Blueprint("main", __name__)

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
footer3 = """
        <p>2025 小盒子社区</p>
        开源文件 <a href="https://gitee.com/wujiajiouwei/small-box-community">gitee</a> | <a href="https://gitee.com/wujiajiouwei/scratch-git">ScratchGit</a> | <a href="https://gitee.com/wujiajiouwei/sbox-api">Sboxapi</a><br>
        网站相关 <a href = "/required">使用小盒子必读</a> | <a href="/download">下载相关软件</a> | <a href="/thanks">特别鸣谢</a><br>
"""

# 优秀作品列表
Excellent_scratch = [10, 12, 36]

# 40code配置
CLIENT_ID_40code = config.CLIENT_ID_40CODE
CLIENT_SECRET_40code = config.CLIENT_SECRET_40CODE
REDIRECT_URI_40code = config.SITE_URL + "/callback/40code"
SCOPE_40code = "basic"
AUTH_URL_40code = "https://www.40code.com/#page=oauth_authorize"
TOKEN_URL_40code = "https://api.abc.520gxx.com/oauth/token"
USER_INFO_URL_40code = "https://api.abc.520gxx.com/oauth/user"

# GitHub OAuth配置
try:
    GITHUB_CLIENT_ID = config.GITHUB_CLIENT_ID
    GITHUB_CLIENT_SECRET = config.GITHUB_CLIENT_SECRET
    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_API_URL = "https://api.github.com/user"
    GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

    REDIRECT_URI = config.SITE_URL + "/github/callback"
except:
    pass

# ZeroCat OAuth配置
CLIENT_ID_zerocat = config.ZEROCAT_CLIENT_ID
try:
    CLIENT_SECRET_zerocat = config.ZEROCAT_CLIENT_ID
except:
    pass
REDIRECT_URI_zerocat = config.SITE_URL + "/zerocat"
AUTHORIZE_URL_zerocat = "https://zerocat-api.houlangs.com/oauth/authorize"
TOKEN_URL_zerocat = "https://zerocat-api.houlangs.com/oauth/token"
USERINFO_URL_zerocat = "https://zerocat-api.houlangs.com/oauth/userinfo"


# NOTE:首页，展示推荐作品和随机作品
@main_bp.route("/")
def index():
    if not session.get("username") == None:
        moren = sdb.up("user.sdb", "个人默认首页_name_" + session.get("username"))
        if moren == "scratch":
            return redirect(url_for("scratch.scratch_index"))

    try:
        zhuopin_max_id = int(sdb.up("zhuopin.sdb", "作品最大id")) - 1
        if zhuopin_max_id < 1:
            zhuopin_max_id = 1
    except (ValueError, TypeError):
        sdb.down("zhuopin.sdb", "作品最大id", 3)
        zhuopin_max_id = 2  # 3 - 1
    # 随机选择6个优秀scratch作品
    Excellent_scratch_1 = Excellent_scratch[secrets.randbelow(len(Excellent_scratch))]
    Excellent_scratch_work_1 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_1))
    Excellent_scratch_2 = Excellent_scratch[secrets.randbelow(len(Excellent_scratch))]
    Excellent_scratch_work_2 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_2))
    Excellent_scratch_3 = Excellent_scratch[secrets.randbelow(len(Excellent_scratch))]
    Excellent_scratch_work_3 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_3))
    Excellent_scratch_4 = Excellent_scratch[secrets.randbelow(len(Excellent_scratch))]
    Excellent_scratch_work_4 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_4))
    Excellent_scratch_5 = Excellent_scratch[secrets.randbelow(len(Excellent_scratch))]
    Excellent_scratch_work_5 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_5))
    Excellent_scratch_6 = Excellent_scratch[secrets.randbelow(len(Excellent_scratch))]
    Excellent_scratch_work_6 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_6))

    # 随机选择6个scratch作品
    scid1 = secrets.randbelow(zhuopin_max_id) + 1
    zhuopin1 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid1))
    scid2 = secrets.randbelow(zhuopin_max_id) + 1
    zhuopin2 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid2))
    scid3 = secrets.randbelow(zhuopin_max_id) + 1
    zhuopin3 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid3))
    scid4 = secrets.randbelow(zhuopin_max_id) + 1
    zhuopin4 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid4))
    scid5 = secrets.randbelow(zhuopin_max_id) + 1
    zhuopin5 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid5))
    scid6 = secrets.randbelow(zhuopin_max_id) + 1
    zhuopin6 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(scid6))

    scratch_tueijian = [30, 28, 32]
    Excellent_scratch_7 = scratch_tueijian[secrets.randbelow(len(scratch_tueijian))]
    Excellent_scratch_work_7 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_7))
    Excellent_scratch_8 = scratch_tueijian[secrets.randbelow(len(scratch_tueijian))]
    Excellent_scratch_work_8 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_8))
    Excellent_scratch_9 = scratch_tueijian[secrets.randbelow(len(scratch_tueijian))]
    Excellent_scratch_work_9 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_9))
    Excellent_scratch_10 = scratch_tueijian[secrets.randbelow(len(scratch_tueijian))]
    Excellent_scratch_work_10 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_10))
    Excellent_scratch_11 = scratch_tueijian[secrets.randbelow(len(scratch_tueijian))]
    Excellent_scratch_work_11 = sdb.up("zhuopin.sdb", "作品名称_id_" + str(Excellent_scratch_11))
    Excellent_scratch_12 = scratch_tueijian[secrets.randbelow(len(scratch_tueijian))]
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

    return render_template(
        "index3.html",
        nav=nav,
        footer=footer3,
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


# NOTE:GitHub OAuth登录跳转
@main_bp.route("/githublogin")
def github_login():
    state = os.urandom(16).hex()
    session["oauth_state"] = state

    auth_params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "user:email",
        "state": state,
    }
    auth_url = GITHUB_AUTH_URL + "?" + urlencode(auth_params)
    return redirect(auth_url)


# NOTE:GitHub OAuth回调处理，获取用户信息并登录
@main_bp.route("/github/callback")
def github_callback():
    # 验证 state 防止 CSRF
    if request.args.get("state") != session.get("oauth_state"):
        return "State mismatch! Possible CSRF attack.", 400

    code = request.args.get("code")
    if not code:
        return "Authorization code not found.", 400

    # Step 1: 请求 access_token
    token_data = urlencode(
        {
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
    ).encode("utf-8")

    token_req = urllib.request.Request(GITHUB_TOKEN_URL, data=token_data)
    token_req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(token_req) as response:
            token_response = response.read().decode("utf-8")
            token_json = json.loads(token_response)
    except Exception as e:
        return "Failed to get access token", 500

    if "access_token" not in token_json:
        return "Access token not returned", 500

    access_token = token_json["access_token"]

    # Step 2: 获取用户基本信息
    user_req = urllib.request.Request(GITHUB_API_URL)
    user_req.add_header("Authorization", f"token {access_token}")
    user_req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(user_req) as response:
            user_data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return "Failed to get user info", 500

    # Step 3: 获取邮箱（primary + verified）
    email = user_data.get("email")
    if not email:
        try:
            emails_req = urllib.request.Request(GITHUB_EMAILS_URL)
            emails_req.add_header("Authorization", f"token {access_token}")
            emails_req.add_header("Accept", "application/json")
            with urllib.request.urlopen(emails_req) as response:
                emails_data = json.loads(response.read().decode("utf-8"))
                for em in emails_data:
                    if em.get("primary") and em.get("verified"):
                        email = em["email"]
                        break
        except:
            email = None

    username = user_data.get("login")
    email = email
    shenfen = "用户"  # 默认用户身份
    if check_email_registered(email):
        username = genggai.get_username_by_email(email)
        con = f"""
hey {username}!<br>
<br>
You log in through the authorization of Github.<br>
Please confirm that you are the one operating to ensure security.<br>
<br>
If you encounter any problems, you can visit <a href="{config.SITE_URL}">{config.SITE_URL}</a> or send mail to {config.EMAIL_SENDER or "the administrator"} for support<br>
<br>
Thank you,<br>
The Sbox Team
            """
        email_send.email(
            genggai.caxu(session.get("username"), 4),
            con,
            "[Sbox]You log in through the authorization GitHub.",
        )
        session.clear()
        session["username"] = username
        return "成功"


# NOTE:ZeroCat OAuth登录跳转（使用PKCE）
@main_bp.route("/zerocatlogin")
def zerocat_login():
    # 生成 PKCE 和 state
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    # 存入 session（用于后续验证）
    session["code_verifier"] = code_verifier
    session["oauth_state"] = state

    # 构建授权 URL
    params = {
        "client_id": CLIENT_ID_zerocat,
        "redirect_uri": REDIRECT_URI_zerocat,
        "response_type": "code",
        "scope": "user:basic user:email",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = AUTHORIZE_URL_zerocat + "?" + urllib.parse.urlencode(params)
    return redirect(auth_url)


# NOTE:ZeroCat OAuth回调处理，关联或登录用户
@main_bp.route("/zerocat")
def zerocat_oauth_callback():
    # 1. 验证 state
    state = request.args.get("state")
    if state != session.get("oauth_state"):
        return "Invalid state parameter", 400

    code = request.args.get("code")
    if not code:
        return "Authorization failed: no code", 400

    # 2. 用 code 换取 access_token
    code_verifier = session.get("code_verifier")
    if not code_verifier:
        return "Missing code_verifier", 400

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID_zerocat,
        "client_secret": CLIENT_SECRET_zerocat,
        "redirect_uri": REDIRECT_URI_zerocat,
        "code_verifier": code_verifier,
    }

    resp = requests.post(TOKEN_URL_zerocat, data=token_data)
    if resp.status_code != 200:
        return f"Token exchange failed: {resp.text}", 400

    tokens = resp.json()
    access_token = tokens["access_token"]

    # 3. 获取用户信息
    headers = {"Authorization": f"Bearer {access_token}"}
    user_resp = requests.get(USERINFO_URL_zerocat, headers=headers)
    if user_resp.status_code != 200:
        return "Failed to fetch user info", 400

    user_info = user_resp.json()

    # 4. 检查用户是否已登录
    if "username" in session:
        # 用户已登录，将zerocat账号与当前账号关联
        current_username = session["username"]
        # 存储zerocat的用户信息到用户数据库中
        import sqlite3

        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()
            # 添加zerocat_openid字段用于存储zerocat账号关联信息
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN zerocat_openid TEXT")
            except sqlite3.OperationalError:
                # 列已存在，忽略错误
                pass
            cursor.execute(
                "UPDATE users SET zerocat_openid = ? WHERE username = ?",
                (user_info["openid"], current_username),
            )
            conn.commit()

        # 提示用户关联成功
        return render_template(
            "information.html",
            Information=f"zerocat账号 {user_info['nickname']} 已成功关联到您的账户 {current_username}！请前往用户更改页面完成验证。",
        )
    else:
        # 用户未登录，尝试通过openid查找用户
        import sqlite3

        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username FROM users WHERE zerocat_openid = ?",
                (user_info["openid"],),
            )
            result = cursor.fetchone()

            if result:
                # 找到已关联的用户，直接登录
                username = result[0]
                session.clear()
                session["username"] = username

                # 发送登录通知邮件
                username = session.get("username")
                con = f"""
Hey {username}!<br>
<br>
You have logged in to the little box through ZeroCat OAuth!<br>
<br>
If you encounter any problems, you can visit <a href="{config.SITE_URL}">{config.SITE_URL}</a> or send mail to {config.EMAIL_SENDER or "the administrator"} for support<br>
<br>
Thank you<br>
Sbox Team
                """
                email_send.email(
                    genggai.caxu(username, 4),
                    con,
                    "[Sbox] You have been authorized to log in through ZeroCat.",
                )

                return redirect(url_for("main.index"))
            else:
                # 未找到关联用户，提示用户需要先登录或注册
                # 临时存储zerocat信息到session，以便在登录后处理
                session["pending_zerocat_login"] = {
                    "openid": user_info["openid"],
                    "username": user_info["username"],
                    "nickname": user_info["nickname"],
                }
                return render_template(
                    "information.html",
                    Information=f"未找到与zerocat账号 {user_info['nickname']} 关联的账户。请先登录您的小盒子账户，然后在用户更改页面完成zerocat快捷登录的设置。",
                )


# 导入必要的模块
import urllib


# NOTE:用户登录，支持密码+TOTP两步验证
@main_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    page = request.args.get("page")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        token = request.form["token"]

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password, totp_secret FROM users WHERE username=?",
                (username,),
            )
            user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            # 密码正确
            if user[3]:  # totp_secret 存在，需要 2FA
                session["2fa_user_id"] = user[0]
                session["2fa_username"] = user[1]
                flash("Please enter your TOTP code.", "info")

                user_id = user[0]

                with sqlite3.connect(DATABASE) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT totp_secret FROM users WHERE id = ?", (user_id,))
                    row = cursor.fetchone()

                if row and row[0]:
                    import pyotp

                    totp = pyotp.TOTP(row[0])
                    if totp.verify(token, valid_window=1):
                        # TOTP 验证成功，完成登录
                        session["username"] = session["2fa_username"]
                        session.pop("2fa_user_id", None)
                        session.pop("2fa_username", None)

                        username = session.get("username")

                        # 检查是否有待处理的zerocat登录关联
                        pending_zerocat = session.get("pending_zerocat_login")
                        if pending_zerocat:
                            # 将zerocat账号与当前登录用户关联
                            with sqlite3.connect(DATABASE) as conn:
                                cursor = conn.cursor()
                                try:
                                    cursor.execute(
                                        "ALTER TABLE users ADD COLUMN zerocat_openid TEXT"
                                    )
                                except sqlite3.OperationalError:
                                    # 列已存在，忽略错误
                                    pass
                                cursor.execute(
                                    "UPDATE users SET zerocat_openid = ? WHERE username = ?",
                                    (pending_zerocat["openid"], username),
                                )
                                conn.commit()
                            # 清除session中的待处理数据
                            session.pop("pending_zerocat_login", None)

                        con = f"""
Hey {username}!<br>
<br>
You have logged in to the little box!<br>
<br>
If you encounter any problems, you can visit <a href="{config.SITE_URL}">{config.SITE_URL}</a> or send mail to {config.EMAIL_SENDER or "the administrator"} for support<br>
<br>
Thank you<br>
Sbox Team
                        """
                        email_send.email(
                            genggai.caxu(username, 4),
                            con,
                            "[Sbox] You have been authorized to log in.",
                        )
                        if page == "studyhelp":
                            return redirect(url_for("studyhelp.studyhelp"))
                        else:
                            return redirect(url_for("main.index"))
            else:
                # 未启用 TOTP，直接登录
                session.clear()
                session["username"] = user[1]
                username = session.get("username")

                # 检查是否有待处理的zerocat登录关联
                pending_zerocat = session.get("pending_zerocat_login")
                if pending_zerocat:
                    # 将zerocat账号与当前登录用户关联
                    with sqlite3.connect(DATABASE) as conn:
                        cursor = conn.cursor()
                        try:
                            cursor.execute("ALTER TABLE users ADD COLUMN zerocat_openid TEXT")
                        except sqlite3.OperationalError:
                            # 列已存在，忽略错误
                            pass
                        cursor.execute(
                            "UPDATE users SET zerocat_openid = ? WHERE username = ?",
                            (pending_zerocat["openid"], username),
                        )
                        conn.commit()
                    # 清除session中的待处理数据
                    session.pop("pending_zerocat_login", None)

                con = f"""
Hey {username}!<br>
<br>
You have logged in to the little box!<br>
<br>
If you encounter any problems, you can visit <a href="{config.SITE_URL}">{config.SITE_URL}</a> or send mail to {config.EMAIL_SENDER or "the administrator"} for support<br>
<br>
Thank you<br>
Sbox Team
                """
                email_send.email(
                    genggai.caxu(username, 4),
                    con,
                    "[Sbox] You have been authorized to log in.",
                )

                if page == "studyhelp":
                    return redirect(url_for("studyhelp.studyhelp"))
                else:
                    return redirect(url_for("main.index"))
        else:
            flash("Invalid username or password!", "error")

    return render_template("login.html")


# NOTE:显示用户使用协议页面
@main_bp.route("/required")
def required2():
    return render_template("required.html")


# NOTE:用户注册，发送邮箱验证码
@main_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def register():
    client_ip = request.remote_addr
    if request.method == "POST":
        email = request.form["email"]
        if check_email_registered(email):
            if not (config.EMAIL_SENDER and email == config.EMAIL_SENDER):
                return render_template("information.html", Information="邮箱已被注册")
        elif not (
            "@qq.com" in email
            or "@163.com" in email
            or "@126.com" in email
            or "@139.com" in email
            or "@163.vip.com" in email
        ):
            return render_template("information.html", Information="请用qq邮箱")

        import verification_codes

        verification_code = verification_codes.generate_verification_code()
        sent = email_send.email(email, f"以下为验证码<br>{verification_code}", "验证码")
        if not sent:
            flash("验证码发送失败，请检查邮箱配置或稍后重试", "error")
            return render_template("register2.html")
        verification_codes.store_verification_code(email, verification_code)

        logger.info("验证码已发送到 %s", email)
        sdb.down("yzm2.sdb", client_ip, "yes")
        return redirect(url_for("main.register_yzm"))
    return render_template("register2.html")


# NOTE:注册验证码验证，校验后创建用户
@main_bp.route("/register/yzm", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def register_yzm():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        yzm = request.form["yzm"]
        email = request.form["email"]

        import verification_codes

        if not verification_codes.validate_verification_code(email, yzm):
            return render_template("information.html", Information="验证码无效或已过期")

        if not check_password_strength(password):
            return render_template(
                "information.html",
                Information="密码强度不足，请使用至少8位包含数字、大小写字母和特殊字符的密码",
            )

        hashed_password = generate_password_hash(password)
        shenfen = "用户"

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users (username, password, shenfen, email) 
                VALUES (?, ?, ?, ?)
            """,
                (username, hashed_password, shenfen, email),
            )

            conn.commit()
            conn.close()

            verification_codes.delete_verification_code(email)
            aid = genggai.update_user(username, 0, email, "email")
            admin_email = config.EMAIL_SENDER or "sbox520@163.com"
            email_send.email(
                admin_email,
                f"喵~✨主人您好喵~🎉<br> {username}注册成功，ID是{aid}哟~<br>如果是捣乱的请及时处理喵~",
                "信息提醒",
            )
            return redirect(url_for("main.login"))
        except sqlite3.IntegrityError:
            flash("用户名或邮箱已存在！请选择其他用户名或邮箱。")
            conn.close()
    return render_template("register.html")


# NOTE:忘记密码，三步流程：验证邮箱→验证码→重置密码
@main_bp.route("/forget", methods=["GET", "POST"])
@limiter.limit("30 per minute")
def forget():
    if request.method == "POST":
        step = request.form.get("step", "1")

        if step == "1":
            email = request.form.get("email", "").strip()

            if not email:
                flash("请输入邮箱地址。", "error")
                return render_template("forgot_password.html", step=1)

            username = genggai.get_username_by_email(email)
            if not username:
                flash("该邮箱未注册，请检查邮箱地址。", "error")
                return render_template("forgot_password.html", step=1)

            import verification_codes

            verification_code = verification_codes.generate_verification_code()
            verification_codes.store_verification_code(email, verification_code)

            try:
                email_send.email(
                    email,
                    f"您的验证码是：{verification_code}，10分钟内有效。",
                    "[Sbox]密码重置验证码",
                )
                flash("验证码已发送到您的邮箱，请查收。", "success")
                return render_template("forgot_password.html", step=2, email=email)
            except Exception as e:
                logger.error("发送邮件失败: %s", e)
                flash("验证码发送失败，请稍后重试。", "error")
                return render_template("forgot_password.html", step=1)

        elif step == "2":
            email = request.form.get("email", "").strip()
            verification_code = request.form.get("verification_code", "").strip()

            if not email or not verification_code:
                flash("请填写完整信息。", "error")
                return render_template("forgot_password.html", step=2, email=email)

            import verification_codes

            if verification_codes.validate_verification_code(email, verification_code):
                return render_template("forgot_password.html", step=3, email=email)
            else:
                flash("验证码错误或已过期，请重新输入。", "error")
                return render_template("forgot_password.html", step=2, email=email)

        elif step == "3":
            email = request.form.get("email", "").strip()
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not email or not new_password or not confirm_password:
                flash("请填写完整信息。", "error")
                return render_template("forgot_password.html", step=3, email=email)

            if new_password != confirm_password:
                flash("两次输入的密码不一致，请重新输入。", "error")
                return render_template("forgot_password.html", step=3, email=email)

            if not check_password_strength(new_password):
                flash(
                    "密码强度不足，请使用至少8位包含数字、大小写字母和特殊字符的密码。",
                    "error",
                )
                return render_template("forgot_password.html", step=3, email=email)

            username = genggai.get_username_by_email(email)
            if not username:
                flash("用户不存在。", "error")
                return render_template("forgot_password.html", step=1)

            hashed_password = generate_password_hash(new_password)
            genggai.update_user(username, 2, hashed_password, "password")

            import verification_codes

            verification_codes.delete_verification_code(email)

            flash("密码已成功重置，请使用新密码登录。", "success")
            return redirect(url_for("main.login"))

    return render_template("forgot_password.html", step=1)


# NOTE:40code OAuth登录跳转
@main_bp.route("/OAuth_40code")
def OAuth_40code():
    state = "40code_OAuth_" + secrets.token_urlsafe(16)
    session["oauth_state"] = state
    redirect_uri_encoded = urllib.parse.quote(REDIRECT_URI_40code, safe="")
    return redirect(
        f"https://www.40code.com/#page=oauth_authorize&client_id={CLIENT_ID_40code}&redirect_uri={redirect_uri_encoded}&scope={SCOPE_40code},message&state={state}"
    )


# NOTE:40code OAuth回调处理，获取用户信息并登录
@main_bp.route("/callback/40code")
def callback_40code():
    code = request.args.get("code")
    state = request.args.get("state")

    # 验证参数
    if not code:
        return "授权失败：缺少code参数", 400

    if state != session.get("oauth_state"):
        return "授权失败：State参数不匹配", 403

    # 获取access_token
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.SITE_URL + "/callback/40code",
        "client_id": CLIENT_ID_40code,
        "client_secret": CLIENT_SECRET_40code,
    }

    try:
        token_response = requests.post(TOKEN_URL_40code, data=token_data)
        token_json = token_response.json()

        if token_response.status_code != 200:
            return "授权失败: 第三方登录异常", 400

        access_token = token_json["access_token"]

        # 获取用户信息
        headers = {"Authorization": f"Bearer {access_token}"}
        user_response = requests.get(USER_INFO_URL_40code, headers=headers)
        user_info = user_response.json()

        if user_response.status_code != 200:
            return "用户信息获取失败", 400

        username = user_info["nickname"]
        user_email = user_info["email"]

        # Clear the oauth_state after use for security
        session.pop("oauth_state", None)

        if check_email_registered(user_email):
            username = genggai.get_username_by_email(user_email)
            con = f"""
hey {username}!<br>
<br>
You log in through the authorization of 40code.<br>
Please confirm that you are the one operating to ensure security.<br>
<br>
If you encounter any problems, you can visit <a href="{config.SITE_URL}">{config.SITE_URL}</a> or send mail to {config.EMAIL_SENDER or "the administrator"} for support<br>
<br>
Thank you,<br>
The Sbox Team
            """
            # Get the user's email from the database
            user_email_db = genggai.caxu(username, 4)
            if user_email_db:
                email_send.email(
                    user_email_db,
                    con,
                    "[Sbox] You log in through the authorization of 40code.",
                )
            session.clear()
            session["username"] = username
            return redirect(url_for("main.index"))
        else:
            # Handle unregistered users
            flash("Your email is not registered. Please register first.", "error")
            return redirect(url_for("main.register"))

    except Exception as e:
        # Clear the oauth_state even in case of error
        session.pop("oauth_state", None)
        return f"服务器错误: {str(e)}", 500


# NOTE:搜索页面
@main_bp.route("/search", methods=["GET", "POST"])
def search():
    return render_template("search.html", nav=nav)


# NOTE:搜索API，支持按类型搜索Scratch
@main_bp.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json()  # 接收 JSON 数据
    search_term = data.get("search_term")
    filter_term = data.get("filter_term")
    Type = data.get("selection")

    import time

    start_time = time.time()
    if Type == "scratch":
        results = sdb.search_by_content_and_filter("zhuopin.sdb", search_term, filter_term)
    else:
        results = []
    end_time = time.time()
    elapsed_time = (end_time - start_time) * 1000  # 转换为毫秒
    return jsonify(
        {
            "results": [{"variable": row[0], "content": row[1], "id": row[2]} for row in results],
            "elapsed_time": f"{elapsed_time:.2f}",
        }
    )


# NOTE:AJAX登录API，支持TOTP两步验证
@main_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    token = data.get("token", "")

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password, totp_secret FROM users WHERE username=?",
            (username,),
        )
        user = cursor.fetchone()

    if user and check_password_hash(user[2], password):
        # 密码正确
        if user[3]:  # totp_secret 存在，需要 2FA
            import pyotp

            totp = pyotp.TOTP(user[3])
            if not token or not totp.verify(token, valid_window=1):
                return jsonify({"success": False, "error": "需要两步验证码", "require_2fa": True})

        # 登录成功
        session["username"] = user[1]
        session.pop("2fa_user_id", None)
        session.pop("2fa_username", None)

        return jsonify({"success": True, "redirect": "/", "username": username})
    else:
        return jsonify({"success": False, "error": "用户名或密码错误"})


# NOTE:AJAX注册API，发送邮箱验证码
@main_bp.route("/api/register/send-code", methods=["POST"])
def api_register_send_code():
    data = request.get_json()
    email = data.get("email", "")

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱地址"})

    # 检查邮箱格式
    if not (
        "@qq.com" in email
        or "@163.com" in email
        or "@126.com" in email
        or "@139.com" in email
        or "@163.vip.com" in email
        or "@gmail.com" in email
    ):
        return jsonify({"success": False, "error": "请使用支持的邮箱地址"})

    # 检查邮箱是否已注册
    if check_email_registered(email):
        return jsonify({"success": False, "error": "邮箱已被注册"})

    # 生成并发送验证码
    import verification_codes

    verification_code = verification_codes.generate_verification_code()
    verification_codes.store_verification_code(email, verification_code)

    try:
        email_send.email(
            email,
            f"您的验证码是：{verification_code}，10分钟内有效。",
            "[Sbox] 注册验证码",
        )
        return jsonify({"success": True, "message": "验证码已发送"})
    except Exception as e:
        return jsonify({"success": False, "error": f"验证码发送失败：{str(e)}"})


# NOTE:AJAX注册API，校验验证码后创建用户
@main_bp.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    email = data.get("email", "")
    yzm = data.get("yzm", "")

    # 验证数据
    if not username or not password or not email or not yzm:
        return jsonify({"success": False, "error": "请填写完整信息"})

    # 验证验证码
    import verification_codes

    if not verification_codes.validate_verification_code(email, yzm):
        return jsonify({"success": False, "error": "验证码无效或已过期"})

    # 检查用户名是否已存在
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            return jsonify({"success": False, "error": "用户名已存在"})

    # 检查邮箱是否已注册
    if check_email_registered(email):
        return jsonify({"success": False, "error": "邮箱已被注册"})

    # 创建用户
    hashed_password = generate_password_hash(password)
    shenfen = "用户"

    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, password, shenfen, email) 
                VALUES (?, ?, ?, ?)
            """,
                (username, hashed_password, shenfen, email),
            )
            conn.commit()

        # 删除验证码
        verification_codes.delete_verification_code(email)

        # 更新用户信息
        genggai.update_user(username, 0, email, "email")

        # 发送通知邮件
        admin_email = config.EMAIL_SENDER or "sbox520@163.com"
        email_send.email(
            admin_email,
            f"新用户注册：{username}，邮箱：{email}",
            "[Sbox] 新用户注册通知",
        )

        return jsonify({"success": True, "message": "注册成功"})
    except Exception as e:
        return jsonify({"success": False, "error": f"注册失败：{str(e)}"})


# NOTE:AJAX检查用户名是否已被注册
@main_bp.route("/api/check-username", methods=["GET"])
def api_check_username():
    username = request.args.get("username", "")

    if not username or len(username) < 3:
        return jsonify({"exists": False})

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=?", (username,))
        user = cursor.fetchone()

    return jsonify({"exists": user is not None})


# NOTE:AJAX检查邮箱是否已被注册
@main_bp.route("/api/check-email", methods=["GET"])
def api_check_email():
    email = request.args.get("email", "")

    if not email:
        return jsonify({"exists": False})

    return jsonify({"exists": check_email_registered(email)})


# NOTE:退出登录，清除Session
@main_bp.route("/logout")
def logout():
    page = request.args.get("page")
    session.pop("username", None)
    return redirect(url_for("main.login", page=page))


# NOTE:启用TOTP两步验证，生成二维码
@main_bp.route("/enable-totp", methods=["GET", "POST"])
def enable_totp():
    if "username" not in session:
        return redirect(url_for("main.login"))

    username = session["username"]

    if request.method == "POST":
        # 验证用户输入的 TOTP 是否正确
        token = request.form.get("token")
        secret = session.get("provisioning_secret")
        if not secret or not token:
            flash("Invalid request", "error")
            return redirect(url_for("main.enable_totp"))

        totp = pyotp.TOTP(secret)
        if totp.verify(token, valid_window=1):  # 允许前后30秒偏移
            # 保存 secret 到数据库
            with sqlite3.connect(DATABASE) as conn:
                conn.execute(
                    "UPDATE users SET totp_secret = ? WHERE username = ?",
                    (secret, username),
                )
            flash("TOTP enabled successfully!", "success")
            session.pop("provisioning_secret", None)
            return redirect(url_for("main.index"))
        else:
            flash("Invalid TOTP code. Please try again.", "error")
            return redirect(url_for("main.enable_totp"))

    # GET: 生成新的 secret 和二维码
    secret = pyotp.random_base32()
    session["provisioning_secret"] = secret

    # 生成 URI（用于 Authenticator App）
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name="小盒子社区")

    # 生成二维码
    qr = qrcode.make(uri)
    img_io = io.BytesIO()
    qr.save(img_io, "PNG")
    img_io.seek(0)
    qr_b64 = base64.b64encode(img_io.getvalue()).decode()

    return render_template("totp.html", qr_b64=qr_b64)
