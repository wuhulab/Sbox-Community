# Sbox - 小盒子社区

[English](README.en.md) | **中文**

一个基于 Flask 的 Scratch 创作者社区平台。用户可上传、分享和管理 Scratch 作品（.sb3/.sb2）、通过 OAuth 登录（40code、GitHub、ZeroCat），以及提交作品 PR。

## 功能特性

- **Scratch 作品管理** — 上传、浏览、点赞、收藏、下载 Scratch 作品
- **第三方登录** — 支持 40code、GitHub、ZeroCat OAuth 登录
- **JWT 认证** — Token 认证 + Refresh Token 自动刷新
- **TOTP 两步验证** — 基于时间的一次性密码双因素认证
- **AI 集成** — AI 学习助手、作品简介智能生成
- **Scratch PR 系统** — 为 Scratch 作品提交 Pull Request
- **RESTful API** — 完整的 V1 API（作品、用户接口）

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | Flask 3.0.x |
| 认证 | Flask-JWT-Extended, pyotp |
| 数据库 | SQLite（开发）、PostgreSQL（生产） |
| 前端 | Jinja2 模板、原生 JavaScript |
| 图片服务 | FastAPI + Uvicorn |
| AI | OpenAI API |
| 工具 | Ruff（代码检查）、pytest（测试） |

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/wuhulab/Sbox-Community

cd sbox

# 创建虚拟环境
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
# source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填写你的配置

# 启动主应用
python app.py
# 访问 http://localhost:5219
```

## 配置说明

复制 `.env.example` 为 `.env` 并配置以下变量：

| 变量 | 说明 |
|------|------|
| `SECRET_KEY` | Flask 密钥 |
| `SITE_URL` | 站点地址（如 `http://localhost:5219`）|
| `SQLITE_DB` | SQLite 数据库路径 |
| `CLIENT_ID_40CODE` | 40code OAuth 客户端 ID |
| `GITHUB_CLIENT_ID` | GitHub OAuth 客户端 ID |
| `ZEROCAT_CLIENT_ID` | ZeroCat OAuth 客户端 ID |
| `EMAIL_HOST` | SMTP 服务器地址 |
| `EMAIL_USER` | SMTP 用户名 |
| `EMAIL_PASS` | SMTP 密码 |

## 项目结构

```
sbox/
├── app.py                  # Flask 主应用（端口 5219）
├── config.py               # 环境配置
├── blueprints/             # Flask 蓝图
│   ├── auth.py             # JWT 认证 API
│   ├── main.py             # 主路由、登录、OAuth
│   ├── scratch.py          # Scratch 作品 CRUD
│   ├── user.py             # 用户个人中心
│   └── v1/                 # API v1 蓝图
├── utils/                  # 工具模块
│   ├── db.py               # 数据库连接
│   ├── helpers.py          # 辅助函数
│   └── api_response.py     # 统一 API 响应格式
├── tests/                  # 测试（pytest）
├── templates/              # Jinja2 HTML 模板
├── static/                 # 静态资源（CSS、JS）
├── dist/                   # 前端构建（Scratch 编辑器）
└── uploads/                # 用户上传文件
```

## API 文档

完整的 V1 API 文档请查看 `api_docs/README.md`。

## 测试

```bash
pytest -v
```

安装覆盖率工具后：
```bash
pip install pytest-cov
pytest --cov=. --cov-report=term-missing
```

## 贡献

欢迎贡献代码！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

本项目基于 **GNU Affero General Public License v3 (AGPL-3.0)** 开源，详见 [LICENSE](LICENSE) 文件。
