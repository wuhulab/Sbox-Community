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
import time
from functools import wraps
from typing import Callable, Any
from flask import request, jsonify

try:
    from utils.db import get_db, init_db as _init_db, DATABASE
except ImportError:
    DATABASE = os.environ.get("SQLITE_DB", "sbox.db")
    import sqlite3


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    try:
        from utils.db import init_db as _init_db

        _init_db()
    except Exception:
        pass


def require_auth(f: Callable) -> Callable:
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
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
