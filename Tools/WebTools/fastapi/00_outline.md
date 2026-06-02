# 🧾 FastAPI 教学大纲
>📌 教学目标
- 理解 FastAPI 的设计理念与核心特性
- 能够构建 RESTful API 服务
- 掌握与前端交互、数据库集成、认证授权等实用能力
- 学会部署与性能优化技巧

#### 🧩 模块 1：FastAPI 简介与开发环境搭建
- FastAPI 概览：特点、对比 Flask/Django
- 安装与虚拟环境配置
- 第一个 FastAPI 项目（Hello World）
- 使用 uvicorn 启动服务

#### 🧩 模块 2：路由与请求处理
- 路由注册与路径参数：@app.get(), @app.post() 等
- 查询参数与默认值
- 请求体：Pydantic 模型入门
- 响应模型与数据校验

#### 🧩 模块 3：进阶数据处理与验证
- 嵌套模型与类型提示
- 表单与文件上传：Form, File, UploadFile
- 自定义响应（如 HTML、Redirect）
- 异常处理：HTTPException, 全局异常钩子

#### 🧩 模块 4：数据库集成（以 SQLite / PostgreSQL 为例）
- ORM 简介：使用 SQLAlchemy 或 Tortoise-ORM
- 数据库建模与迁移
- 增删改查操作（CRUD）
- 异步数据库操作（async/await）

#### 🧩 模块 5：认证与授权
- 基础认证（HTTPBasicAuth）
- OAuth2 + JWT 登录机制实现
- 用户注册、登录、权限验证
- FastAPI 的安全模块使用

#### 🧩 模块 6：中间件与依赖注入
- 创建中间件（Logging, CORS, 请求计时等）
- FastAPI 的依赖注入系统（Depends）
- 常见依赖封装：数据库连接、当前用户、权限校验等

#### 🧩 模块 7：与前端/第三方集成
- 跨域资源共享（CORS）设置
- Swagger 和 Redoc 自动文档
- 与前端表单交互、Axios 测试
- 与其他系统的对接示例（如微信小程序/爬虫）

#### 🧩 模块 8：异步任务与后台处理
- FastAPI 中的异步视图
- 使用 BackgroundTasks 执行后台任务
- 集成 Celery + Redis 实现分布式任务队列（可选）

#### 🧩 模块 9：测试与项目管理
- 单元测试与 API 测试（pytest + httpx）
- 自动化测试与覆盖率评估
- 配置文件与环境变量（pydantic + dotenv）
- 结构化项目目录（app/main/schemas/routes）

#### 🧩 模块 10：部署与性能优化
- 使用 Gunicorn + Uvicorn 部署生产服务
- Docker 化部署（Dockerfile + docker-compose）
- 性能分析与优化建议
- 异常日志与监控（Sentry / Prometheus）