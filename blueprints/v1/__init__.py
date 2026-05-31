# -*- coding: utf-8 -*-
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

"""
V1 版本 API Blueprint 包
包含所有 V1 版本的 API 接口
"""

from blueprints.v1.scratch import scratch_bp
from blueprints.v1.user import user_bp
# from blueprints.v1.ai import ai_bp  # TODO: 创建 ai.py 后取消注释

__all__ = ["scratch_bp", "user_bp"]
