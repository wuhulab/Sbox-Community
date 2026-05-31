# 参与贡献

感谢您想为小盒子社区贡献力量！

# 贡献注意事项

1. 一次只做一件事，不要把多个功能放在一个 PR 里，不然将不会合并
2. 代码中添加中文注释，方便他人理解
3. 不要重复提交pr
4. 代码中不要出现中文变量名
5. 不要未经讨论提交新的功能，除非是紧急修复
6. 不要在代码中添加个人可识别信息（PII）
7. 不要在代码中添加个人网站链接，其他推广信息链接
8. 不要在代码中添加个人微信，QQ 等联系方式
9. 不要未经讨论添加引入新的编程语言，依赖（包括），重构代码，除非是紧急修复
10. 不要未经讨论修改代码风格
11. 为了考虑低端设备，Sbox的前端只能使用原生html + js + css

## 报告问题

- 使用 GitHub Issues 报告 bug 或功能请求
- 描述尽量清晰，附上复现步骤和截图
- 标明环境信息（Python 版本、操作系统等）

## 提交代码

1. Fork 本仓库
2. 创建特性分支: `git checkout -b feat/your-feature`
3. 提交改动: `git commit -m 'feat: 添加xxx功能'`
4. 推送到分支: `git push origin feat/your-feature`
5. 提交 Pull Request

## 代码规范

- 遵循 PEP 8 编码风格
- 新函数建议添加类型提示（Type Hints）
- 关键逻辑应有中文注释说明
- 运行 `ruff check .` 确保无 lint 错误

## 开发环境

```bash
git clone <仓库地址>
cd sbox
python -m venv venv
venv\Scripts\activate  # 或 source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## 测试

```bash
pytest -v
```

## 提交信息规范

建议遵循 Conventional Commits:

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具链相关
