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

# NOTE: 这个模块实现了一个简单的图片服务器，使用FastAPI框架来处理HTTP请求。它提供了一个路由来根据图片ID返回对应的图片文件，如果图片不存在则返回一个默认的图片。图片文件存储在本地的'scratchphoto'目录中，并且设置了适当的缓存控制头来优化性能。

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime, timedelta

app = FastAPI()

# 配置图片目录
PHOTO_DIR = os.path.join(os.getcwd(), "scratchphoto")
app.mount("/static", StaticFiles(directory=PHOTO_DIR), name="static")


# NOTE:FastAPI图片服务器首页
@app.get("/")
async def index():
    return {"Hello": "How are you"}


# NOTE:根据ID返回Scratch作品封面图片
@app.get("/scratchphoto/{id}")
async def serve_photo(id: str):
    try:
        # 拼接文件名
        filename = f"{id}.png"
        # 拼接文件路径
        file_path = os.path.join(PHOTO_DIR, filename)

        # 如果文件不存在，则重定向到默认图片
        if not os.path.exists(file_path):
            return RedirectResponse(url="/scratchphoto/scratch")

        # 返回文件响应
        response = FileResponse(
            file_path,
            headers={
                "Cache-Control": "public, max-age=1209600",
                "Expires": (datetime.now() + timedelta(seconds=1209600)).strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"
                ),
            },
        )
        return response
    except Exception as e:
        # 抛出HTTP异常
        raise HTTPException(status_code=500, detail="Server Error")


# NOTE:返回默认封面图片
@app.get("/scratchphoto/scratch")
async def default_photo():
    try:
        default_file_path = os.path.join(PHOTO_DIR, "scratch.png")
        if os.path.exists(default_file_path):
            return FileResponse(
                default_file_path,
                headers={
                    "Cache-Control": "public, max-age=1209600",
                    "Expires": (datetime.now() + timedelta(seconds=1209600)).strftime(
                        "%a, %d %b %Y %H:%M:%S GMT"
                    ),
                },
            )
        else:
            raise HTTPException(status_code=404, detail="Default photo not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Server Error")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5218)
