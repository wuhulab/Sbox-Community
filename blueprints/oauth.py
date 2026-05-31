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

# NOTE: 这个模块实现了一个简单的OAuth 2.0授权服务器，支持授权码模式和刷新令牌模式。它提供了客户端注册、授权端点、Token端点和用户信息端点等功能。用户可以通过授权页面同意授权，系统会生成授权码并发送邮件通知用户。客户端可以使用授权码交换访问令牌，并使用访问令牌获取用户信息。该模块还包含一些安全措施，如验证参数、检查令牌有效性等。

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
)
import sqlite3
import time
import secrets
from urllib.parse import urlencode
from functools import wraps

try:
    from utils.db import get_db, DATABASE
except ImportError:
    DATABASE = "sbox.db"

    def get_db():
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn


oauth_bp = Blueprint("oauth", __name__)


# NOTE:上栏
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
                <button class="theme-toggle" onclick="toggleTheme()">☀</button>
            </div>
        </div>
"""


# NOTE:Token认证装饰器，验证Bearer Token有效性
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return jsonify(error="Missing or invalid access token"), 401
        token = auth.split(" ", 1)[1]
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM access_tokens WHERE token = ? AND expires_at > ?",
                (token, int(time.time())),
            ).fetchone()
            if not row:
                return jsonify(error="Invalid or expired token"), 401
            request.current_user_id = row["user_id"]
        return f(*args, **kwargs)

    return decorated


# ========================
# 1. NOTE:注册 OAuth 客户端（用于测试）
# ========================
@oauth_bp.route("/register_client", methods=["GET", "POST"])
def register_client():
    if session.get("username") == None:
        return redirect(url_for("login"))

    if (
        genggai.caxu(session.get("username"), 4) == None
        or genggai.caxu(session.get("username"), 4) == ""
    ):
        return render_template("information.html", Information="需要验证邮箱")

    if request.method == "POST":
        redirect_uri = request.form["redirect_uri"]
        client_id = secrets.token_urlsafe(16)
        client_secret = secrets.token_urlsafe(32)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO oauth_clients (client_id, client_secret, redirect_uri) VALUES (?, ?, ?)",
                (client_id, client_secret, redirect_uri),
            )
            conn.commit()
        return f"""
        <h3>客户端注册成功！</h3>
        <p>client_id: <strong>{client_id}</strong></p>
        <p>client_secret: <strong>{client_secret}</strong></p>
        <p>redirect_uri: {redirect_uri}</p>
        <p>请立即保管好，不显示第二次，建议复制到本地记事本！！！</p>
        <p>请立即保管好，不显示第二次，建议复制到本地记事本！！！</p>
        <p>请立即保管好，不显示第二次，建议复制到本地记事本！！！</p>
        """
    return """
    <form method="post">
        Redirect URI: <input name="redirect_uri" value="http://localhost:5000/callback" size=50><br>
        <button type="submit">注册 OAuth 客户端</button>
    </form>
    """


# NOTE: 下面是授权端点，用户登录后访问，显示授权页面，用户同意后生成授权码并发送邮件通知用户，然后重定向回客户端并带上授权码和 state 参数。客户端可以使用授权码交换访问令牌。
@oauth_bp.route("/oauth/authorize", methods=["GET", "POST"])
def authorize():
    if session.get("username") == None:
        return redirect(url_for("login"))

    if (
        genggai.caxu(session.get("username"), 4) == None
        or genggai.caxu(session.get("username"), 4) == ""
    ):
        return render_template("information.html", Information="需要验证邮箱")

    # 1. 验证必要参数
    client_id = request.args.get("client_id")
    redirect_uri = request.args.get("redirect_uri")
    response_type = request.args.get("response_type")
    state = request.args.get("state", "")
    scope = request.args.get("scope", "basic")

    if not client_id or not redirect_uri or response_type != "code":
        return "Missing parameters", 400

    with get_db() as conn:
        client = conn.execute(
            "SELECT * FROM oauth_clients WHERE client_id = ?", (client_id,)
        ).fetchone()
        if not client or client["redirect_uri"] != redirect_uri:
            return "Invalid client or redirect_uri", 400

    if request.method == "GET":
        # 显示授权确认页面
        return render_template(
            "oauth_shouquan.html",
            nav=nav,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            scope=scope,
        )

    # 4. 处理 POST（用户点击同意/拒绝）
    decision = request.form.get("decision")
    if decision == "deny":
        # 拒绝授权：重定向回客户端并带上 error
        params = {"error": "access_denied", "state": state}
        return redirect(f"{redirect_uri}?{urlencode(params)}")
    elif decision == "allow":
        user_id = genggai.caxu(session.get("username"), 0)
        code = secrets.token_urlsafe(32)
        expires_at = int(time.time()) + 600  # 10分钟
        with get_db() as conn:
            conn.execute(
                "INSERT INTO auth_codes (code, client_id, user_id, redirect_uri, scope, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                (code, client_id, user_id, redirect_uri, scope, expires_at),
            )
            conn.commit()

        username = session.get("username")
        # XXX: 改成中文
        con = f"""
    hey {username}!<br>
    <br>
    Search for and retrieve your verification email address and your ID in order to authorize the application {redirect_uri}<br>
    <br>
    If you encounter any problems, you can visit {config.SITE_URL} or send mail to {config.EMAIL_SENDER or "the administrator"} for support<br>
    <br>
    Thank you,<br>
    The Sbox Team
        """
        # 关键：email_send 缩进与 con = ... 对齐（通常 8 空格，在 elif 下是 2 级缩进）
        email_send.email(
            genggai.caxu(username, 4),  # ← 用 username，更安全
            con,
            "[Sbox] You have been authorized to log in.",
        )

        # 构造重定向参数（与 email_send 同级）
        params = {"code": code}
        if state:
            params["state"] = state
        return redirect(f"{redirect_uri}?{urlencode(params)}")

    else:
        return "无效操作", 400


# ========================
# 3. 获取 Access Token
# ========================
@oauth_bp.route("/oauth/token", methods=["POST"])
def token():
    grant_type = request.json.get("grant_type")
    client_id = request.json.get("client_id")
    client_secret = request.json.get("client_secret")

    with get_db() as conn:
        client = conn.execute(
            "SELECT * FROM oauth_clients WHERE client_id = ? AND client_secret = ?",
            (client_id, client_secret),
        ).fetchone()
        if not client:
            return jsonify(error="Invalid client credentials"), 401

    user_id = None
    scope = "basic"  # 默认 scope

    if grant_type == "authorization_code":
        code = request.json.get("code")
        redirect_uri = request.json.get("redirect_uri")

        with get_db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            auth_code = conn.execute(
                "SELECT * FROM auth_codes WHERE code = ? AND client_id = ? AND redirect_uri = ? AND expires_at > ?",
                (code, client_id, redirect_uri, int(time.time())),
            ).fetchone()
            if not auth_code:
                return jsonify(error="Invalid or expired authorization code"), 400

            conn.execute("DELETE FROM auth_codes WHERE code = ?", (code,))
            conn.commit()

            user_id = auth_code["user_id"]
            scope = auth_code["scope"] if "scope" in auth_code else "basic"  # 安全获取

    elif grant_type == "refresh_token":
        refresh_token = request.json.get("refresh_token")
        with get_db() as conn:
            # 同样：如果 refresh_tokens 表没有 scope，这里会出错
            rt = conn.execute(
                "SELECT * FROM refresh_tokens WHERE token = ? AND client_id = ? AND expires_at > ?",
                (refresh_token, client_id, int(time.time())),
            ).fetchone()
            if not rt:
                return jsonify(error="Invalid refresh token"), 400
            user_id = rt["user_id"]
            scope = rt["scope"] if "scope" in rt else "basic"
    else:
        return jsonify(error="Unsupported grant_type"), 400

    # 生成 tokens
    access_token = secrets.token_urlsafe(48)
    new_refresh_token = secrets.token_urlsafe(48)
    expires_in = 604800
    expires_at = int(time.time()) + expires_in

    with get_db() as conn:
        # 插入 access_token —— 不包含 scope 字段
        conn.execute(
            "INSERT INTO access_tokens (token, user_id, client_id, expires_at) VALUES (?, ?, ?, ?)",
            (access_token, user_id, client_id, expires_at),
        )
        # 插入 refresh_token —— 不包含 scope 字段
        conn.execute(
            "INSERT INTO refresh_tokens (token, user_id, client_id, expires_at) VALUES (?, ?, ?, ?)",
            (new_refresh_token, user_id, client_id, expires_at),
        )
        conn.commit()

    return jsonify(
        access_token=access_token,
        token_type="Bearer",
        expires_in=expires_in,
        refresh_token=new_refresh_token,
        scope=scope,  # 仍然返回 scope 给客户端
    )


# 4. 刷新 Token（可选，上面已支持）
# 实际上 /oauth/token 已支持 refresh_token，此端点可省略
# 但为符合文档，单独实现
@oauth_bp.route("/oauth/refresh", methods=["POST"])
def refresh():
    return token()  # 复用逻辑


# NOTE:获取用户信息
@oauth_bp.route("/oauth/user", methods=["GET"])
@require_auth
def get_user_info():
    with get_db() as conn:
        user = conn.execute(
            "SELECT id, username, email FROM users WHERE id = ?",
            (request.current_user_id,),
        ).fetchone()
        if not user:
            return jsonify(error="User not found"), 404
        return jsonify(
            id=user["id"],
            nickname=user["username"],  # 用 username 作为 nickname
            email=user["email"],
        )


# NOTE:OAuth授权服务器首页
@oauth_bp.route("/OAuth")
def OAuth_index():
    return """
    <h1>OAuth 2.0 授权服务器</h1>
    <ul>
        <li><a href="/register_client">注册 OAuth 客户端</a></li>
    </ul>
    <p>授权端点: <code>GET /oauth/authorize</code></p>
    <p>Token 端点: <code>POST /oauth/token</code></p>
    <p>用户信息: <code>GET /oauth/user</code></p>
    """


# NOTE:40code OAuth登录跳转
@oauth_bp.route("/OAuth_40code")
def OAuth_40code():
    state = "40code_OAuth_" + secrets.token_urlsafe(16)
    session["oauth_state"] = state
    return redirect(
        "https://www.40code.com/#page=oauth_authorize&client_id="
        + config.CLIENT_ID_40CODE
        + "&redirect_uri="
        + urllib.parse.quote(config.SITE_URL, safe="")
        + "&scope=basic,message&state="
        + state
    )


# 导入必要的模块
import urllib.parse
from flask import render_template
import genggai
import email_send
import config
