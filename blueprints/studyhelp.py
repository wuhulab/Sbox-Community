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

# NOTE: 这个模块实现了一个学习助手功能，提供智能解题和智能解决方案两个页面。用户可以上传题目图片，选择模型（如Qwen3-VL-4B-Instruct等），然后系统会调用OpenAI的API进行解题，并通过Server-Sent Events（SSE）实时返回解题过程和最终答案。该模块还实现了一个简单的限流器来防止滥用，并且对输入进行了基本的验证和错误处理。

from flask import (
    Blueprint,
    render_template,
    request,
    Response,
    stream_with_context,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import base64
from openai import OpenAI
import os
import json

# 创建蓝图
studyhelp_bp = Blueprint("studyhelp", __name__)

# 配置限流器
limiter = Limiter(get_remote_address, app=None, storage_uri="memory://")

# 导航栏
nav3 = """
            <div class="toolbox">
                <div class="dropdown" onclick="toggleDropdown()">
                    ☰
                    <div class="dropdown-content">
                        <a href="/studyhelp">首页</a>
                        <a href="/logout?page=studyhelp">登陆</a>
                    </div>
                </div>
                <button class="theme-toggle" onclick="toggleTheme()">&#9788;</button>
            </div>
        </div>
"""


# NOTE:学习助手首页
@studyhelp_bp.route("/studyhelp")
def studyhelp():
    content = ""
    return render_template(r"studyhelp/index.html", content=content, nav=nav3)


# NOTE:智能解题页面
@studyhelp_bp.route("/studyhelp/Intelligent-problem-solving")
def studyhelp_Intelligent_problem_solving():
    return render_template("studyhelp/Intelligent-problem-solving.html", nav=nav3)


# NOTE:智能解题API，调用AI模型流式返回解答
@studyhelp_bp.route("/api/solve", methods=["POST"])
@limiter.limit("10 per minute")
def solve_problem():
    def generate():
        try:
            # --- 1. 获取模型参数（默认 Qwen3-VL-4B） ---
            model = (
                request.form.get("model") or request.json.get("model") if request.is_json else None
            )
            model = model or "Qwen3-VL-4B-Instruct"
            # ✅ 支持的模型白名单（防注入）
            ALLOWED_MODELS = {
                "Qwen3-VL-4B-Instruct",
                "Qwen3-VL-8B-Instruct",
                "Qwen3-VL-30B-A3B-Instruct",
                "GLM-4_5V",
                "step3",
                "ERNIE-4.5-Turbo-VL",
            }
            if model not in ALLOWED_MODELS:
                yield " " + json.dumps({"error": f"不支持的模型：{model}"}) + "\n\n"
                return

            # --- 2. 解析图片（同前） ---
            image_data_uri = None
            if "image" in request.files:
                image_file = request.files["image"]
                if not image_file.filename:
                    yield " " + json.dumps({"error": "No image uploaded"}) + "\n\n"
                    return
                image_bytes = image_file.read()
                image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                mime_type = image_file.mimetype or "image/jpeg"
                image_data_uri = f"data:{mime_type};base64,{image_b64}"
            elif request.is_json:
                data = request.get_json()
                img_url = data.get("image", "")
                if not img_url.startswith("data:image"):
                    yield " " + json.dumps({"error": "Invalid image format"}) + "\n\n"
                    return
                header, image_b64 = img_url.split(",", 1)
                mime_type = header.split(";"[0].split(":"[1]))
                image_data_uri = f"data:{mime_type};base64,{image_b64}"
            else:
                yield " " + json.dumps({"error": "No image provided"}) + "\n\n"
                return

            # --- 3. 初始化 client ---
            client = OpenAI(
                base_url="https://ai.gitee.com/v1",  # ✅ 无空格！
                api_key=os.getenv("GITEE_AI_API_KEY", ""),
            )

            messages = [
                {
                    "role": "system",
                    "content": "你是一位严谨、耐心的辅导老师。请用 Markdown 格式分步解答，公式用 $...$ 或 $$...$$ 包裹。语言清晰，适合学生理解。",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data_uri}},
                        {
                            "type": "text",
                            "text": "请用 Markdown 分步解答这道题，并给出最终答案。",
                        },
                    ],
                },
            ]

            yield " " + json.dumps({"status": "thinking"}) + "\n\n"

            stream = client.chat.completions.create(
                model=model,  # ✅ 动态模型
                messages=messages,
                max_tokens=2048,
                temperature=0.3,
                stream=True,
            )

            full_text = ""
            for chunk in stream:
                if len(chunk.choices) == 0:
                    continue
                delta = chunk.choices[0].delta
                content = delta.content or ""
                if content:
                    full_text += content
                    yield (" " + json.dumps({"type": "content", "text": content}) + "\n\n")

            yield (" " + json.dumps({"type": "done", "final": full_text.strip()}) + "\n\n")

        except Exception as e:
            logging.exception("Stream error")
            yield " " + json.dumps({"error": str(e)}) + "\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# NOTE:智能解决方案页面
@studyhelp_bp.route("/studyhelp/Intelligent-solution")
def studyhelp3():
    content = ""
    return render_template(r"studyhelp/index.html", content=content, nav=nav3)
