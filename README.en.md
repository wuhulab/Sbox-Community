# Sbox - Small Box Community

**English** | [中文](README.md)

A Scratch community platform built with Flask. Users can upload, share, and manage Scratch projects (.sb3/.sb2), write blogs (Markdown), authenticate via OAuth (40code, GitHub, ZeroCat), and submit PRs for Scratch projects.

## Features

- **Scratch Project Management** — Upload, browse, like, star, and download Scratch projects
- **Blog System** — Markdown-powered blog posts with novel/series support
- **OAuth Login** — 40code, GitHub, ZeroCat authentication
- **JWT Authentication** — Token-based auth with refresh tokens
- **TOTP 2FA** — Time-based one-time password two-factor authentication
- **AI Integration** — AI-powered study helper and project description generation
- **Scratch PR System** — Submit pull requests for Scratch projects
- **RESTful API** — Full V1 API for Scratch, blog, and user operations

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | Flask 3.0.x |
| Auth | Flask-JWT-Extended, pyotp |
| Database | SQLite (dev), PostgreSQL (production) |
| Frontend | Jinja2 Templates, Vanilla JS |
| Image Server | FastAPI + Uvicorn |
| AI | OpenAI API |
| Tools | Ruff (linting), pytest (testing) |

## Quick Start

```bash
git clone https://github.com/your-username/sbox.git
cd sbox
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
# source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
# Visit http://localhost:5219
```

## Project Structure

```
sbox/
├── app.py                  # Main Flask application (port 5219)
├── sboxapi.py              # FastAPI image server (port 5218)
├── config.py               # Environment configuration
├── blueprints/             # Flask blueprints
├── utils/                  # Utility modules
├── tests/                  # Test suite (pytest)
├── templates/              # Jinja2 HTML templates
├── static/                 # Static assets
├── dist/                   # Frontend build
└── uploads/                # User uploaded files
```

For detailed documentation (in Chinese), see [README.md](README.md).
