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

import os
from typing import Optional


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]

        load_dotenv()
    except ImportError:
        pass
    return os.environ.get(key, default)


# Flask
SECRET_KEY: str = get_env("SECRET_KEY", "dev-secret-key-change-in-production")  # type: ignore[assignment]

# JWT
JWT_SECRET_KEY: str = get_env("JWT_SECRET_KEY", SECRET_KEY)  # type: ignore[assignment]

# 40code OAuth
CLIENT_ID_40CODE: Optional[str] = get_env("CLIENT_ID_40CODE")
CLIENT_SECRET_40CODE: Optional[str] = get_env("CLIENT_SECRET_40CODE")

# GitHub OAuth
GITHUB_CLIENT_ID: Optional[str] = get_env("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET: Optional[str] = get_env("GITHUB_CLIENT_SECRET")

# ZeroCat OAuth
ZEROCAT_CLIENT_ID: Optional[str] = get_env("ZEROCAT_CLIENT_ID")
ZEROCAT_CLIENT_SECRET: Optional[str] = get_env("ZEROCAT_CLIENT_SECRET")

# AI API Keys
AI_API_KEY_A: Optional[str] = get_env("AI_API_KEY_A")
AI_API_KEY_B: Optional[str] = get_env("AI_API_KEY_B")
AI_API_KEY_SILICONFLOW: Optional[str] = get_env("AI_API_KEY_SILICONFLOW")

# Email
EMAIL_HOST: Optional[str] = get_env("EMAIL_HOST")
EMAIL_USER: Optional[str] = get_env("EMAIL_USER")
EMAIL_PASS: Optional[str] = get_env("EMAIL_PASS")
EMAIL_SENDER: Optional[str] = get_env("EMAIL_SENDER")
SMTP_PORT: int = int(get_env("SMTP_PORT", "465"))  # 465=SSL, 587=STARTTLS, 25=明文
SMTP_USE_SSL: bool = get_env("SMTP_USE_SSL", "True").lower() == "true"

# Database
DATABASE_URL: str = get_env("SQLITE_DB", "sbox.db")  # type: ignore[assignment]

# Debug
DEBUG: bool = get_env("DEBUG", "False").lower() == "true"

# Site URL
SITE_URL: str = get_env("SITE_URL", "http://localhost:5219")  # type: ignore[assignment]

# External service URLs (override per deployment)
TURBOWARP_ORIGIN: str = get_env("TURBOWARP_ORIGIN", "https://turbowarp.org")  # type: ignore[assignment]
SBOXAPI_URL: str = get_env("SBOXAPI_URL", "https://sboxapi.yearnstudio.cn")  # type: ignore[assignment]
SCRATCH_EXTENSION_URL: str = get_env(
    "SCRATCH_EXTENSION_URL", "https://api.yearnstudio.cn/static/one.js"
)  # type: ignore[assignment]
CDN_MARKDOWN_URL: str = get_env(
    "CDN_MARKDOWN_URL", "https://shunian.scerpark.cn/markdown/markdown.js"
)  # type: ignore[assignment]
