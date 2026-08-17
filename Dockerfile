# syntax=docker/dockerfile:1
# 小盒子社区 (Sbox) — Flask 主应用镜像
# 运行端口: 5219

FROM python:3.12-slim AS base

# 系统依赖:
# - cairosvg/Pillow 需 libffi / libcairo2 / libjpeg
# - psycopg2-binary 需 libpq
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libcairo2 \
        libpango-1.0-0 \
        libpq-dev \
        libjpeg62-turbo \
        zlib1g \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用层缓存）
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# 复制源码
COPY . .

# 运行时目录（持久化挂载点）
RUN mkdir -p /app/uploads /app/scratch2 /app/scratchphoto /app/scratch_old /app/data
VOLUME ["/app/uploads", "/app/scratch2", "/app/scratchphoto", "/app/scratch_old", "/app/data"]

ENV PYTHONPATH=/app \
    PORT=5219

EXPOSE 5219

# 健康检查：命中 app.py 里的 /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:5219/health || exit 1

# 生产用 gunicorn；本地构建也可直接 python app.py（通过覆盖 CMD）
CMD ["gunicorn", "--bind", "0.0.0.0:5219", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
