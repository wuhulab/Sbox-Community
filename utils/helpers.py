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

import re
import os
import hashlib
import base64
import secrets
import sqlite3
import logging
from typing import Set, Tuple
import subprocess

logger = logging.getLogger(__name__)


def check_password_strength(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True


def count_subdirectories(directory: str) -> int:
    entries = os.listdir(directory)
    subdirs = [entry for entry in entries if os.path.isdir(os.path.join(directory, entry))]
    return len(subdirs)


def count_files_recursively(directory: str) -> int:
    file_count = 0
    for root, dirs, files in os.walk(directory):
        file_count += len(files)
    return file_count


def svg_to_png(svg_path: str, png_path: str, width: int = 800, height: int = 600) -> bool:
    try:
        import cairosvg

        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=width, output_height=height)
        return True
    except ImportError:
        try:
            from wand.image import Image as WandImage

            with WandImage(filename=svg_path) as img:
                img.format = "png"
                img.resize(width, height)
                img.save(filename=png_path)
            return True
        except ImportError:
            try:
                import gi

                gi.require_version("Rsvg", "2.0")
                from gi.repository import Rsvg
                import cairo

                handle = Rsvg.Handle.new_from_file(svg_path)
                svg_dim = handle.get_dimensions()

                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
                ctx = cairo.Context(surface)

                scale_x = width / svg_dim.width
                scale_y = height / svg_dim.height
                scale = min(scale_x, scale_y)
                ctx.scale(scale, scale)
                handle.render_cairo(ctx)
                surface.write_to_png(png_path)
                return True
            except ImportError:
                try:
                    subprocess.run(
                        [
                            "inkscape",
                            "--export-type=png",
                            f"--export-filename={png_path}",
                            f"--export-width={width}",
                            f"--export-height={height}",
                            svg_path,
                        ],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    return False


def generate_pkce_pair() -> Tuple[str, str]:
    verifier = secrets.token_urlsafe(96)[:128]
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    return verifier, challenge


def check_email_registered(email: str) -> bool:
    DATABASE = os.environ.get("SQLITE_DB", "sbox.db")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", (email,))
        result = cursor.fetchone()
        return result[0] > 0 if result else False
    except Exception as e:
        logger.error("查询邮箱错误: %s", e)
        return False
    finally:
        conn.close()


def allowed_file(filename: str, allowed_extensions: Set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


from flask import session as flask_session


def validate_csrf_token(token: str) -> bool:
    stored = flask_session.get("csrf_token")
    if not stored or stored != token:
        return False
    return True
