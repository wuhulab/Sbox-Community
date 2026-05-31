# Sbox 数据库架构说明

## 表结构

### users - 用户表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER/SERIAL | 主键 |
| username | TEXT | 用户名（唯一） |
| password | TEXT | 密码哈希 |
| shenfen | TEXT | 身份 |
| email | TEXT | 邮箱（唯一） |
| totp_secret | TEXT | TOTP密钥 |
| zerocat_openid | TEXT | ZeroCat关联ID |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### classtap_data - 班级作业板数据
### oauth_clients - OAuth客户端
### auth_codes - 授权码
### access_tokens - 访问令牌
### refresh_tokens - 刷新令牌
### kv_store - 键值存储
### verification_codes - 验证码

## 使用方法

### 开发环境（SQLite）

```python
from utils.db import get_db, init_db

# 初始化数据库
init_db()

# 查询
with get_db() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
```

### 生产环境（PostgreSQL）

设置环境变量：
```bash
export DATABASE_TYPE=postgresql
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=sbox
export DB_USER=postgres
export DB_PASSWORD=your_password
```


## 环境配置

参考 `.env.example` 文件配置环境变量。