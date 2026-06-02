## 模块 1：FastAPI 简介与开发环境搭建

>🎯 学习目标
- 理解 FastAPI 的核心特点与定位
- 与 Flask / Django 对比，明确使用场景
- 搭建开发环境并成功运行第一个 FastAPI 项目
- 掌握 uvicorn 的使用方法

### 🔍 什么是 FastAPI？
FastAPI 是一个现代、快速（高性能）的 Web 框架，用于构建 API，基于：
- Python 3.7+ 的类型注解
- Starlette（Web 框架） + Pydantic（数据校验）

>🎯 设计目标
- 开发速度快（比 Flask 快 200%）
- 自动生成交互式文档（Swagger UI / Redoc）
- 原生支持异步编程（async/await）
- 强类型校验 + 自动提示

### ⚖️ FastAPI vs Flask vs Django
| 特性   | FastAPI         | Flask     | Django                |
| ---- | --------------- | --------- | --------------------- |
| 异步支持 | ✅ 原生            | ❌（需插件）    | ❌（Django 3.1+ 才有部分支持） |
| 自动文档 | ✅ Swagger/Redoc | ❌（需手动配置）  | ❌（需 DRF 支持）           |
| 数据验证 | ✅ Pydantic      | ❌（手动处理）   | ✅（基于模型）               |
| 学习曲线 | 🟢 简单           | 🟢 简单     | 🔴 偏复杂                |
| 使用场景 | API、微服务、现代系统    | 轻量 Web 项目 | 重型 Web 项目、Admin 管理    |

📝 总结：FastAPI 更适合构建现代、高性能的 API 服务。

### 🛠️ 安装开发环境
推荐使用虚拟环境来隔离依赖：

#### 1 创建虚拟环境（任选其一）
```py
# 使用 venv（Python 内置）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 或使用 conda
conda create -n fastapi-env python=3.10
conda activate fastapi-env
```

#### 2 安装 FastAPI 与 Uvicorn
```
pip install fastapi uvicorn
```
✅ FastAPI：用于编写应用
✅ Uvicorn：ASGI 服务器，运行 FastAPI 应用

### 👋 第一个 FastAPI 项目：Hello World
>文件：main.py

```py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}
```
🧠 理解：

- app = FastAPI()：创建应用实例
- @app.get("/")：定义 GET 路由
- read_root()：处理函数，返回 JSON 响应

### 🚀 启动服务：Uvicorn
运行 FastAPI 项目（命令行）：
```sh
python -m uvicorn doc_extract_table:app --reload
```
- main：文件名（不含 .py）
- app：FastAPI 实例变量名
- --reload：开启热更新，开发推荐（随时更改代码，刷新可见）

#### 📌 成功运行后：

- Swagger 文档地址：http://127.0.0.1:8000/docs
- Redoc 文档地址：http://127.0.0.1:8000/redoc
- API 主入口：http://127.0.0.1:8000/

### 🧪 小练习
- 修改 / 路由返回的消息为你的名字
- 新增一个 /hello 路由，返回 {"msg": "Welcome to FastAPI"}
- 访问 http://127.0.0.1:8000/docs，查看 API 文档

### ✅ 本节小结
- FastAPI 是专为 API 构建优化的现代 Web 框架
- 拥有强大的类型支持与自动文档功能
- 搭建开发环境只需几步
- 使用 uvicorn 启动开发服务非常方便