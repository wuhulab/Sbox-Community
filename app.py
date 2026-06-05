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

from flask import (
    Flask,
    render_template,
    session,
    jsonify,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress
import secrets
import logging
import os
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import scratch_pr_bp
import random
import email_send
from jinja2 import FileSystemLoader
import config

from blueprints.main import main_bp
from blueprints.scratch import scratch_bp
from blueprints.studyhelp import studyhelp_bp
from blueprints.oauth import oauth_bp
from blueprints.user import user_bp
from blueprints.scratch_api import scratch_api_bp
from blueprints.auth import auth_bp

from utils.database import init_db

app = Flask(__name__, static_folder="dist", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": config.SITE_URL}})
jwt = JWTManager(app)
app.register_blueprint(scratch_pr_bp.scratch_pr_bp)

app.register_blueprint(main_bp)
app.register_blueprint(scratch_bp)
app.register_blueprint(scratch_api_bp)
app.register_blueprint(studyhelp_bp)
app.register_blueprint(oauth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(auth_bp)
app.secret_key = email_send.key()

app.config["JWT_SECRET_KEY"] = email_send.jwt_key()
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 86400

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = config.SITE_URL.startswith("https")
app.config["TEMPLATES_AUTO_RELOAD"] = True

template_dirs = ["dist", "templates"]
app.jinja_loader = FileSystemLoader(template_dirs)

app.static_folder = "dist"
app.static_url_path = ""
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DIST_FOLDER = os.path.join(BASE_DIR, "dist")
limiter = Limiter(get_remote_address, app=app)
Compress(app)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app.config["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {
    "txt",
    "gif",
    "sb3",
    "sb2",
    "mp4",
    "md",
    "mp3",
    "zip",
    "7z",
    "rar",
}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["SCRATCH_OLD_FOLDER"] = "scratch_old"
app.config["SCRATCH2_FOLDER"] = os.path.join(os.getcwd(), "scratch2")
app.config["SCRATCH2_PHOTO"] = os.path.join(os.getcwd(), "scratchphoto")
app.config["SCRATCH_FOLDER"] = os.path.join(os.getcwd(), "scratch2")

if not os.path.exists(app.config["SCRATCH2_FOLDER"]):
    os.makedirs(app.config["SCRATCH2_FOLDER"])
if not os.path.exists(app.config["SCRATCH2_PHOTO"]):
    os.makedirs(app.config["SCRATCH2_PHOTO"])


# NOTE: 页脚统一配置（优先从环境变量 FOOTER 读取，否则使用默认值）
_DEFAULT_FOOTER = """
        <p>2025 小盒子社区</p>
        开源文件 <a href="https://gitee.com/wujiajiouwei/small-box-community">gitee</a> | <a href="https://gitee.com/wujiajiouwei/scratch-git">ScratchGit</a> | <a href="https://gitee.com/wujiajiouwei/sbox-api">Sboxapi</a><br>
        网站相关 <a href = "/required">使用小盒子必读</a> | <a href="/download">下载相关软件</a> | <a href="/thanks">特别鸣谢</a> | <a href="https://github.com/wuhulab/Sbox-Community">GitHub</a><br>
"""
footer = os.environ.get("FOOTER", _DEFAULT_FOOTER)

# NOTE: 这里是下拉栏统一配置
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

# footer3 与 footer 内容一致，保留作为别名XXX:可以不保留
footer3 = footer

# NOTE:首页推荐
Excellent_scratch = [10, 12, 36]

try:
    CLIENT_ID = config.CLIENT_ID_40CODE
    CLIENT_SECRET = config.CLIENT_SECRET_40CODE
    REDIRECT_URI = config.SITE_URL
    SCOPE = "basic"

    AUTH_URL = "https://www.40code.com/#page=oauth_authorize"
    TOKEN_URL = "https://api.abc.520gxx.com/oauth/token"
    USER_INFO_URL = "https://api.abc.520gxx.com/oauth/user"
except Exception:
    pass

try:
    GITHUB_CLIENT_ID = config.GITHUB_CLIENT_ID
    GITHUB_CLIENT_SECRET = config.GITHUB_CLIENT_SECRET
    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_API_URL = "https://api.github.com/user"
    GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
    REDIRECT_URI = config.SITE_URL + "/github/callback"
except Exception:
    pass

CLIENT_ID_zerocat = config.ZEROCAT_CLIENT_ID
try:
    CLIENT_SECRET_zerocat = config.ZEROCAT_CLIENT_SECRET
except Exception:
    pass
REDIRECT_URI_zerocat = config.SITE_URL + "/zerocat"
AUTHORIZE_URL_zerocat = "https://zerocat-api.houlangs.com/oauth/authorize"
TOKEN_URL_zerocat = "https://zerocat-api.houlangs.com/oauth/token"
USERINFO_URL_zerocat = "https://zerocat-api.houlangs.com/oauth/userinfo"


# NOTE:确保每个会话都有CSRF Token
@app.before_request
def ensure_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)


# NOTE:注入全局模板变量（footer、CSRF Token 和外部服务 URL）
@app.context_processor
def inject_global_vars():
    return dict(
        footer=footer,
        csrf_token=session.get("csrf_token", ""),
        turbowarp_origin=config.TURBOWARP_ORIGIN,
        sboxapi_url=config.SBOXAPI_URL,
        scratch_extension_url=config.SCRATCH_EXTENSION_URL,
        cdn_markdown_url=config.CDN_MARKDOWN_URL,
    )


# NOTE:添加安全响应头（XSS、CSP等防护）
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if "Content-Security-Policy" not in response.headers:
        tw_origin = config.TURBOWARP_ORIGIN.rstrip("/")
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; script-src 'self' 'unsafe-inline' {tw_origin}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' {tw_origin}; frame-ancestors 'self';"
        )
    return response


# NOTE:429限流错误处理
@app.errorhandler(429)
def rate_limit_error(error):
    wenz = [
        "喵~主人，是不是又做了什么让人心动的事情？我都快忍不住想要扑过来了~",
        "喵~ 主人今天看起来真是魅力四射呀，简直让人无法抗拒呢~",
    ]
    return render_template("520.html", wenz=wenz[random.randint(0, 1)]), 520


# NOTE:404页面未找到错误处理
@app.errorhandler(404)
def page_not_found(e):
    wenz = [
        "喵~主人，是不是又做了什么让人心动的事情？我都快忍不住想要扑过来了~",
        "喵~ 主人今天看起来真是魅力四射呀，简直让人无法抗拒呢~",
    ]
    return render_template("520.html", wenz=wenz[random.randint(0, 1)]), 520


# NOTE:520页面（彩蛋）
@app.route("/520")
def loveyou():
    wenz = [
        "喵~主人，是不是又做了什么让人心动的事情？我都快忍不住想要扑过来了~",
        "喵~ 主人今天看起来真是魅力四射呀，简直让人无法抗拒呢~",
    ]
    return render_template("520.html", wenz=wenz[random.randint(0, 1)]), 520


# NOTE:健康检查接口
@app.route("/health")
def health_check():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    from utils.database import init_db

    init_db()
    app.run(host="0.0.0.0", port=5219, debug=config.DEBUG)
