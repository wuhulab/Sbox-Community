# 小盒子社区 API 文档

**版本**: V1
**基础 URL**: `http://localhost:5000/api/v1`
**最后更新**: 2026-03-22

---

## 1. API 概述

### 1.1 基础 URL

```
http://localhost:5000/api/v1
```

### 1.2 认证方式

本 API 采用 **JWT Bearer Token** 进行身份认证。

**请求头格式**:
```http
Authorization: Bearer <access_token>
```

**Token 类型**:
- `access_token`: 访问令牌，有效期 **15 分钟**
- `refresh_token`: 刷新令牌，有效期 **7 天**

**获取 Token**: 通过 `/api/v1/auth/login` 或 `/api/v1/auth/register` 接口获取

### 1.3 请求格式

**请求头**:
```http
Content-Type: application/json
Authorization: Bearer <access_token>  # 需要认证的接口
```

**URL 参数**: 用于 GET 请求的查询参数
```
GET /api/v1/scratch/list?page=1&per_page=20
```

**请求体**: 用于 POST/PUT/DELETE 请求的 JSON 数据
```json
{
    "username": "example",
    "password": "password123"
}
```

**表单数据**: 部分接口使用 `multipart/form-data` 格式（如文件上传）
```
POST /api/v1/scratch/upload
Content-Type: multipart/form-data
```

### 1.4 响应格式

所有接口返回统一 JSON 格式：

**成功响应**:
```json
{
    "code": 200,
    "message": "操作成功",
    "data": { ... }
}
```

**错误响应**:
```json
{
    "code": 400,
    "message": "错误描述",
    "data": null
}
```

**分页响应**:
```json
{
    "code": 200,
    "message": "获取列表成功",
    "data": {
        "items": [...],
        "total": 100,
        "page": 1,
        "per_page": 20
    }
}
```

---

## 2. 认证接口 `/api/v1/auth`

### 2.1 POST /login - 用户登录

用户登录系统，获取访问令牌。

**请求**:
```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "username": "example_user",
    "password": "Password123"
}
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "登录成功",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "user": {
            "id": 1,
            "username": "example_user",
            "email": "example@example.com"
        }
    }
}
```

**错误响应 (401 Unauthorized)**:
```json
{
    "code": 401,
    "message": "用户名或密码错误",
    "data": null
}
```

---

### 2.2 POST /register - 用户注册

注册新用户账号。

**请求**:
```http
POST /api/v1/auth/register
Content-Type: application/json

{
    "username": "new_user",
    "password": "Password123",
    "email": "newuser@example.com"
}
```

**响应 (201 Created)**:
```json
{
    "code": 201,
    "message": "注册成功",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "user": {
            "id": 2,
            "username": "new_user",
            "email": "newuser@example.com"
        }
    }
}
```

**错误响应 (409 Conflict)**:
```json
{
    "code": 409,
    "message": "用户名已存在",
    "data": null
}
```

**验证规则**:
- 用户名: 3-20 个字符
- 密码: 至少 8 位，必须包含数字和字母
- 邮箱: 有效的邮箱格式

---

### 2.3 POST /logout - 用户登出

将当前 Token 加入黑名单，实现登出。

**请求**:
```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "登出成功",
    "data": null
}
```

---

### 2.4 POST /refresh - 刷新 Token

使用 Refresh Token 获取新的 Access Token。

**请求**:
```http
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "Token 刷新成功",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
}
```

---

### 2.5 GET /me - 获取当前用户信息

获取已登录用户的详细信息。

**请求**:
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取用户信息成功",
    "data": {
        "id": 1,
        "username": "example_user",
        "email": "example@example.com"
    }
}
```

---

### 2.6 GET /verify - 验证 Token

验证当前 Token 的有效性。

**请求**:
```http
GET /api/v1/auth/verify
Authorization: Bearer <access_token>
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "Token 有效",
    "data": {
        "valid": true,
        "username": "example_user"
    }
}
```

---

## 3. Scratch 作品接口 `/api/v1/scratch`

### 3.1 GET /list - 作品列表

获取 Scratch 作品列表。

**请求**:
```http
GET /api/v1/scratch/list?page=1&per_page=20
```

**Query 参数**:
| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| per_page | int | 20 | 每页数量 |

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取作品列表成功",
    "data": {
        "works": [
            {
                "id": 1,
                "title": "我的第一个作品",
                "author": "example_user",
                "cover": "/scratchphoto/1",
                "views": 100,
                "likes": 25
            }
        ],
        "total": 50,
        "page": 1,
        "per_page": 20
    }
}
```

---

### 3.2 GET /<id> - 作品详情

获取指定作品的详细信息。

**请求**:
```http
GET /api/v1/scratch/1
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取作品详情成功",
    "data": {
        "id": 1,
        "title": "我的第一个作品",
        "author": "example_user",
        "description": "<p>这是一个 Scratch 作品</p>",
        "raw_description": "这是一个 Scratch 作品",
        "stats": {
            "views": 101,
            "likes": 25,
            "stars": 10,
            "downloads": 50
        },
        "license": "mit",
        "editor": "sbox-scratch",
        "is_author": false,
        "file_url": "/works/1",
        "cover_url": "/scratchphoto/1"
    }
}
```

**错误响应 (404 Not Found)**:
```json
{
    "code": 404,
    "message": "作品不存在",
    "data": null
}
```

---

### 3.3 POST /upload - 上传作品

上传新的 Scratch 作品。需要登录且已验证邮箱。

**请求**:
```http
POST /api/v1/scratch/upload
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: [文件]
name: 作品名称
jianjie: 作品简介
license: mit
sbox: sbox-scratch
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "作品上传成功",
    "data": {
        "id": 51
    }
}
```

**错误响应 (403 Forbidden)**:
```json
{
    "code": 403,
    "message": "请先验证邮箱后再上传作品",
    "data": null
}
```

**支持的文件的扩展名**: `png`, `jpg`, `jpeg`, `html`, `sb3`, `sb2`

---

### 3.4 PUT /<id> - 更新作品

更新已有作品信息。仅作者或管理员可操作。

**请求**:
```http
PUT /api/v1/scratch/1
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

name: 更新后的作品名称
jianjie: 更新后的简介
cover: [封面图片文件]
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "作品更新成功",
    "data": {
        "id": 1
    }
}
```

**错误响应 (403 Forbidden)**:
```json
{
    "code": 403,
    "message": "权限不足，仅作者或管理员可操作",
    "data": null
}
```

---

### 3.5 POST /like/<id> - 点赞作品

对指定作品进行点赞。

**请求**:
```http
POST /api/v1/scratch/like/1
Authorization: Bearer <access_token>
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "点赞成功",
    "data": {
        "liked": true,
        "count": 26
    }
}
```

**重复点赞响应**:
```json
{
    "code": 200,
    "message": "已点赞",
    "data": {
        "liked": true,
        "count": 26
    }
}
```

---

### 3.6 POST /star/<id> - 收藏作品

收藏或取消收藏指定作品。

**请求**:
```http
POST /api/v1/scratch/star/1
Authorization: Bearer <access_token>
```

**收藏响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "收藏成功",
    "data": {
        "starred": true,
        "count": 11
    }
}
```

**取消收藏响应**:
```json
{
    "code": 200,
    "message": "取消收藏成功",
    "data": {
        "starred": false,
        "count": 10
    }
}
```

---

### 3.7 GET /<id>/issues - 获取作品 Issues

获取指定作品的 Issues 列表。

**请求**:
```http
GET /api/v1/scratch/1/issues?page=1&per_page=10
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取 Issues 成功",
    "data": {
        "issues": [
            "user1 [BUG]: 发现一个错误",
            "user2 [GENERAL]: 建议优化"
        ],
        "total": 2,
        "page": 1,
        "per_page": 10
    }
}
```

---

### 3.8 POST /<id>/issues - 添加 Issue

为指定作品添加 Issue。需要登录。

**请求**:
```http
POST /api/v1/scratch/1/issues
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "content": "发现一个 Bug",
    "type": "bug"
}
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "Issue 添加成功",
    "data": {
        "entry": "example_user [BUG]: 发现一个 Bug"
    }
}
```

---

## 4. 博客接口 `/api/v1/blog`

### 4.1 GET /list - 博客列表

获取博客文章列表。

**请求**:
```http
GET /api/v1/blog/list?page=1&per_page=20&novel_id=1
```

**Query 参数**:
| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| per_page | int | 20 | 每页数量 |
| novel_id | int | - | 文集ID，可选 |

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取博客列表成功",
    "data": {
        "blogs": [
            {
                "id": 1,
                "title": "我的第一篇文章",
                "author": "example_user",
                "time": "2026-03-22 10:00:00",
                "views": 100,
                "likes": 20,
                "novel_id": "1"
            }
        ],
        "total": 30,
        "page": 1,
        "per_page": 20
    }
}
```

---

### 4.2 GET /<id> - 博客详情

获取指定博客文章的详细信息。

**请求**:
```http
GET /api/v1/blog/1
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取博客详情成功",
    "data": {
        "id": 1,
        "title": "我的第一篇文章",
        "author": "example_user",
        "content": "<p>这是文章内容...</p>",
        "raw_content": "这是文章内容...",
        "time": "2026-03-22 10:00:00",
        "novel_id": "1",
        "stats": {
            "views": 101,
            "likes": 20
        },
        "is_author": false,
        "navigation": {
            "prev": null,
            "next": 2,
            "novel_id": "1"
        }
    }
}
```

---

### 4.3 POST / - 创建博客

创建新的博客文章。需要登录且已验证邮箱。

**请求**:
```http
POST /api/v1/blog/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "title": "我的新文章",
    "content": "这是文章内容，支持 Markdown 格式",
    "novel_id": "1"
}
```

**响应 (201 Created)**:
```json
{
    "code": 201,
    "message": "博客创建成功",
    "data": {
        "id": 31
    }
}
```

---

### 4.4 PUT /<id> - 更新博客

更新已有博客文章。仅作者或管理员可操作。

**请求**:
```http
PUT /api/v1/blog/1
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "title": "更新后的标题",
    "content": "更新后的内容"
}
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "博客更新成功",
    "data": {
        "id": 1
    }
}
```

---

### 4.5 DELETE /<id> - 删除博客

删除指定博客文章。仅作者或管理员可操作。

**请求**:
```http
DELETE /api/v1/blog/1
Authorization: Bearer <access_token>
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "博客删除成功",
    "data": {
        "id": 1
    }
}
```

---

### 4.6 POST /<id>/like - 点赞博客

对指定博客文章进行点赞。

**请求**:
```http
POST /api/v1/blog/1/like
Authorization: Bearer <access_token>
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "点赞成功",
    "data": {
        "liked": true,
        "count": 21
    }
}
```

---

### 4.7 GET /novels - 文集列表

获取文集列表。

**请求**:
```http
GET /api/v1/blog/novels?page=1&per_page=20
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取文集列表成功",
    "data": {
        "novels": [
            {
                "id": 1,
                "title": "我的小说集",
                "author": "example_user",
                "description": "这是小说集简介",
                "time": "2026-03-22 10:00:00",
                "chapter_count": 5
            }
        ],
        "total": 10,
        "page": 1,
        "per_page": 20
    }
}
```

---

### 4.8 GET /novels/<id> - 文集详情

获取指定文集的详细信息。

**请求**:
```http
GET /api/v1/blog/novels/1
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取文集详情成功",
    "data": {
        "id": 1,
        "title": "我的小说集",
        "author": "example_user",
        "description": "这是小说集简介",
        "time": "2026-03-22 10:00:00",
        "chapters": [
            {
                "id": 1,
                "title": "第一章",
                "time": "2026-03-22 10:00:00",
                "views": 50
            }
        ],
        "chapter_count": 5
    }
}
```

---

## 5. 用户接口 `/api/v1/user`

### 5.1 GET /<username> - 用户信息

获取指定用户的公开信息。

**请求**:
```http
GET /api/v1/user/example_user
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取用户信息成功",
    "data": {
        "id": 1,
        "username": "example_user",
        "email": "example@example.com",
        "shengfen": "高级管理员",
        "grade": 10,
        "jianjie": "<p>这是个人简介</p>",
        "raw_jianjie": "这是个人简介",
        "gexing": "每天进步一点点",
        "avatar_url": "/avaphoto=1",
        "works_count": 5,
        "stars_count": 10,
        "show_stars": true,
        "money": 100.0,
        "version": "社区版"
    }
}
```

---

### 5.2 PUT /<username> - 更新用户信息

更新用户个人信息。仅用户本人可操作。

**请求**:
```http
PUT /api/v1/user/example_user
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "gexing": "新的个性签名",
    "jianjie": "新的个人简介"
}
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "用户信息更新成功",
    "data": {
        "username": "example_user",
        "gexing": "新的个性签名",
        "jianjie": "新的个人简介"
    }
}
```

---

### 5.3 PUT /<username>/password - 修改密码

修改用户密码。仅用户本人可操作。

**请求**:
```http
PUT /api/v1/user/example_user/password
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "current_password": "OldPassword123",
    "new_password": "NewPassword456"
}
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "密码修改成功",
    "data": {
        "username": "example_user"
    }
}
```

**密码强度要求**: 至少 8 位，包含数字、大小写字母和特殊字符

---

### 5.4 GET /<username>/works - 用户作品

获取指定用户的所有作品。

**请求**:
```http
GET /api/v1/user/example_user/works?page=1&per_page=20&type=all
```

**Query 参数**:
| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| per_page | int | 20 | 每页数量 |
| type | string | all | 作品类型: `all`, `scratch`, `blog`, `novel` |

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取用户作品列表成功",
    "data": {
        "works": [
            {
                "id": 1,
                "type": "scratch",
                "title": "Scratch 作品",
                "author": "example_user",
                "views": 100,
                "likes": 25,
                "stars": 10,
                "cover_url": "/scratchphoto/1",
                "license": "mit",
                "editor": "sbox-scratch"
            },
            {
                "id": 2,
                "type": "blog",
                "title": "博客文章",
                "author": "example_user",
                "views": 50,
                "likes": 10,
                "time": "2026-03-22 10:00:00",
                "novel_id": "1"
            }
        ],
        "total": 5,
        "page": 1,
        "per_page": 20,
        "type": "all"
    }
}
```

---

### 5.5 GET /<username>/stars - 用户收藏

获取指定用户收藏的作品列表。

**请求**:
```http
GET /api/v1/user/example_user/stars?page=1&per_page=20
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取用户收藏列表成功",
    "data": {
        "stars": [
            {
                "id": 5,
                "type": "scratch",
                "title": "收藏的作品",
                "author": "other_user",
                "views": 200,
                "likes": 50,
                "stars": 20,
                "cover_url": "/scratchphoto/5",
                "license": "mit",
                "editor": "sbox-scratch"
            }
        ],
        "total": 10,
        "page": 1,
        "per_page": 20
    }
}
```

**错误响应 (403 Forbidden)**:
```json
{
    "code": 403,
    "message": "该用户设置了收藏私密",
    "data": null
}
```

---

### 5.6 GET /search - 搜索用户

根据关键词搜索用户。

**请求**:
```http
GET /api/v1/user/search?q=example&page=1&per_page=20
```

**Query 参数**:
| 参数 | 类型 | 描述 |
|------|------|------|
| q | string | 搜索关键词（至少 2 个字符） |
| page | int | 页码 |
| per_page | int | 每页数量 |

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "搜索用户成功",
    "data": {
        "users": [
            {
                "id": 1,
                "username": "example_user",
                "shengfen": "高级管理员",
                "grade": 10,
                "avatar_url": "/avaphoto=1"
            }
        ],
        "total": 1,
        "page": 1,
        "per_page": 20,
        "keyword": "example"
    }
}
```

---

### 5.7 GET /me - 获取当前用户完整信息

获取当前登录用户的完整信息。

**请求**:
```http
GET /api/v1/user/me
Authorization: Bearer <access_token>
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取当前用户信息成功",
    "data": {
        "id": 1,
        "username": "example_user",
        "email": "example@example.com",
        "shengfen": "高级管理员",
        "grade": 10,
        "jianjie": "<p>这是个人简介</p>",
        "raw_jianjie": "这是个人简介",
        "gexing": "每天进步一点点",
        "avatar_url": "/avaphoto=1",
        "works_count": 5,
        "stars_count": 10,
        "money": 100.0,
        "version": "社区版",
        "ai_api_key": "sk-xxxxxxxx...",
        "is_admin": true
    }
}
```

---

## 6. AI 接口 `/api/v1/ai`

### 6.1 POST /chat - AI 聊天

与 AI 进行对话。需要登录且已验证邮箱。

**请求**:
```http
POST /api/v1/ai/chat
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "model": "Qwen2.5-14B-Instruct",
    "messages": [
        {"role": "system", "content": "你是一个有用的助手"},
        {"role": "user", "content": "你好，请介绍一下自己"}
    ],
    "stream": false
}
```

**Query 参数说明**:
| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| model | string | Qwen2.5-14B-Instruct | AI 模型名称 |
| messages | array | - | 消息数组，每条消息包含 role 和 content |
| stream | bool | false | 是否使用流式响应 |

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "AI 响应成功",
    "data": {
        "response": "你好！我是...",
        "model": "Qwen2.5-14B-Instruct",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "total_tokens": 300
        },
        "cost": 0.0016,
        "balance": 98.4
    }
}
```

**支持的模型列表**:
- `DeepSeek-V3`, `DeepSeek-R1`, `DeepSeek-R1-Distill-Qwen-32B`, `DeepSeek-R1-Distill-Qwen-14B`, `DeepSeek-R1-Distill-Qwen-7B`, `DeepSeek-R1-Distill-Qwen-1.5B`
- `Qwen3-8B`, `Qwen3-32B`, `Qwen3-30B-A3B`, `QwQ-32B`
- `Qwen2.5-32B-Instruct`, `Qwen2.5-14B-Instruct`, `Qwen2-72B-Instruct`, `Qwen2-7B-Instruct`
- `Qwen2.5-Coder-32B-Instruct`, `Qwen2.5-Coder-14B-Instruct`
- `GLM-4_5`, `GLM-4_5-Air`, `GLM-4-32B`, `GLM-4-9B-0414`, `glm-4-9b-chat`
- `ERNIE-4.5-Turbo`, `ERNIE-X1-Turbo`
- `internlm3-8b-instruct`, `InternVL3-78B`, `InternVL3-38B`, `InternVL2.5-78B`, `InternVL2-8B`

**错误响应 (403 Forbidden)**:
```json
{
    "code": 403,
    "message": "请先验证邮箱后再使用 AI 功能",
    "data": null
}
```

---

### 6.2 POST /summary - 生成摘要

使用 AI 生成文章摘要。需要登录且已验证邮箱。

**请求**:
```http
POST /api/v1/ai/summary
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "content": "这是要生成摘要的原始文章内容...",
    "model": "Qwen2.5-14B-Instruct"
}
```

**参数说明**:
| 参数 | 类型 | 描述 |
|------|------|------|
| content | string | 原始内容（50-50000 字） |
| model | string | 使用的模型 |

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "摘要生成成功",
    "data": {
        "summary": "这是生成的文章摘要...",
        "original_length": 5000,
        "summary_length": 150,
        "model": "Qwen2.5-14B-Instruct",
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 100,
            "total_tokens": 1100
        },
        "cost": 0.0008,
        "balance": 97.6
    }
}
```

---

### 6.3 POST /chat/stream - AI 流式聊天

与 AI 进行流式对话。

**请求**:
```http
POST /api/v1/ai/chat/stream
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "model": "Qwen2.5-14B-Instruct",
    "messages": [
        {"role": "user", "content": "讲一个故事"}
    ]
}
```

**响应**: Server-Sent Events (SSE) 流式响应
```
data: {"choices":[{"delta":{"content":"从前"}}]}\n\n
data: {"choices":[{"delta":{"content":"有一"}}]}\n\n
...
data: [DONE]
```

---

### 6.4 GET /balance - 获取 AI 余额

获取当前用户的 AI 账户余额。

**请求**:
```http
GET /api/v1/ai/balance
Authorization: Bearer <access_token>
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取余额成功",
    "data": {
        "api_key": "sk-xxxxxxx...",
        "balance": 98.4,
        "total_used": 1.6
    }
}
```

---

### 6.5 GET /models - 获取支持的模型列表

**请求**:
```http
GET /api/v1/ai/models
```

**响应 (200 OK)**:
```json
{
    "code": 200,
    "message": "获取模型列表成功",
    "data": {
        "models": [
            {
                "name": "DeepSeek-V3",
                "provider": "gitee",
                "pricing": "$2.0000/1M - $16.0000/1M"
            },
            {
                "name": "DeepSeek-R1",
                "provider": "gitee",
                "pricing": "$5.0000/1M - $17.0000/1M"
            }
        ],
        "total": 29
    }
}
```

---

## 7. 错误码说明

| 状态码 | 名称 | 描述 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误或格式不正确 |
| 401 | Unauthorized | 未授权，Token 无效或已过期 |
| 403 | Forbidden | 禁止访问，权限不足 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突，如用户名已存在 |
| 500 | Internal Server Error | 服务器内部错误 |

---

## 8. 通用错误响应示例

**Token 过期 (401)**:
```json
{
    "code": 401,
    "message": "Token 无效或已过期",
    "data": null
}
```

**权限不足 (403)**:
```json
{
    "code": 403,
    "message": "权限不足，仅作者或管理员可操作",
    "data": null
}
```

**资源不存在 (404)**:
```json
{
    "code": 404,
    "message": "作品不存在",
    "data": null
}
```

**参数错误 (400)**:
```json
{
    "code": 400,
    "message": "请求数据不能为空",
    "data": null
}
```

**服务器错误 (500)**:
```json
{
    "code": 500,
    "message": "服务器内部错误",
    "data": null
}
```

---

## 9. 注意事项

1. **Token 刷新**: Access Token 有效期为 15 分钟，建议在即将过期时使用 Refresh Token 刷新
2. **邮箱验证**: 部分功能（如上传作品、创建博客、AI 功能）需要先验证邮箱
3. **权限控制**: 修改、删除操作仅作者或管理员可执行
4. **文件上传**: HTML 文件上传仅限管理员，普通用户只能上传 `.sb3`, `.sb2` 等文件
5. **内容安全**: 博客内容支持 Markdown，系统会自动进行 XSS 过滤
6. **AI 费用**: AI 接口会根据实际使用量扣除账户余额
