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
统一 API 响应格式模块
提供标准的成功响应和错误响应函数
"""

from flask import jsonify
from typing import Any, Optional, Dict


# NOTE:返回统一格式的成功响应
def success_response(data: Any = None, message: str = "success", code: int = 200) -> Dict[str, Any]:
    """
    返回成功响应

    Args:
        data: 响应数据，可为任意类型
        message: 成功消息，默认为 "success"
        code: HTTP 状态码，默认为 200

    Returns:
        JSON 格式的响应字典，包含 code, message, data 字段
    """
    response = {"code": code, "message": message, "data": data}
    return jsonify(response)


# NOTE:返回统一格式的错误响应
def error_response(message: str, code: int = 400, error: Optional[str] = None) -> Dict[str, Any]:
    """
    返回错误响应

    Args:
        message: 错误消息
        code: HTTP 状态码，默认为 400
        error: 详细错误信息，可选

    Returns:
        JSON 格式的响应字典，包含 code, message, data 字段
        错误响应中 data 字段为 None 或包含错误详情
    """
    response = {"code": code, "message": message, "data": None}
    if error is not None:
        response["data"] = {"error": error}
    return jsonify(response)
