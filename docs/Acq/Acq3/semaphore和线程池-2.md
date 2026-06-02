有新的PDF上传，就会调我的fastapi接口（可能同时有多个租户调），可能是多个pdf，然后单个pdf又需要并发处理页


你这个场景可以用一句话概括：**多租户 + 多文件突发 + 单文件内按页并发**，核心难点是 **隔离、限流、背压、避免把 FastAPI 进程打爆**。

下面给你一个“可落地的并发模型”，把你提到的三层并发都管住：

* **租户级并发**：防止一个租户把资源吃完
* **全局并发**：防止所有租户一起冲垮服务
* **单 PDF 的页级并发**：提高吞吐，但别开太猛

---

## 推荐的并发结构（3 层闸门 + 1 个队列）

### 1) 请求入口：快速返回，不在接口里“硬处理”

**上传/通知接口只做：落库/入队 → 返回 202**
真正的 PDF 处理放到后台 worker（同进程也行，最好独立进程）。

原因：同时多租户+多 PDF，一旦你在接口里 `await` 大量任务，**连接占用、超时、进程内存上涨**都会让你痛苦。

---

## 2) 三层 Semaphore 怎么放

### A. 全局闸门：限制“同时处理多少个 PDF”

```py
GLOBAL_PDF_SEM = asyncio.Semaphore(8)  # 例：全服务最多同时处理 8 个PDF
```

### B. 租户闸门：每个租户同时处理多少个 PDF

```py
tenant_sem[tenant_id] = asyncio.Semaphore(2)  # 例：每租户最多同时 2 个PDF
```

### C. 页级闸门：单个 PDF 内最多并发多少页

```py
PAGE_SEM_PER_PDF = 6  # 例：单PDF并发处理 6 页
```

> 这三层是“正交”的：
> **全局**保系统稳，**租户**保公平，**页级**提吞吐。

---

## 3) 队列（背压）一定要有

如果上游突然推 1000 个 PDF，Semaphore 只能“让任务等待”，但任务对象会堆在内存里。更好的方式是：

* 入队（持久化队列更好：Redis/RabbitMQ/Kafka）
* worker 消费（可水平扩展）

即使你暂时不引入外部队列，也至少用一个 `asyncio.Queue(maxsize=...)` 在内存里做背压。

---

# 一个可用的 FastAPI 结构示例（同进程 worker 版）

> 这个示例展示：入队 + 后台 worker + 三层限流 + 单 PDF 页并发。

```python
import asyncio
from collections import defaultdict
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

app = FastAPI()

# ---- 配置 ----
GLOBAL_PDF_CONCURRENCY = 8
PER_TENANT_PDF_CONCURRENCY = 2
PER_PDF_PAGE_CONCURRENCY = 6
QUEUE_MAXSIZE = 2000

GLOBAL_PDF_SEM = asyncio.Semaphore(GLOBAL_PDF_CONCURRENCY)
tenant_sems = defaultdict(lambda: asyncio.Semaphore(PER_TENANT_PDF_CONCURRENCY))

queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)

class Job(BaseModel):
    tenant_id: str
    pdf_ids: list[str]   # 你可以换成存储路径/URL
    # 也可以带其他参数：priority、callback等

# ---- 入口：只入队，快速返回 ----
@app.post("/pdf/ingest", status_code=202)
async def ingest(job: Job):
    try:
        queue.put_nowait(job)
    except asyncio.QueueFull:
        raise HTTPException(status_code=429, detail="Server busy, queue is full")
    return {"accepted": True, "queued_pdfs": len(job.pdf_ids)}

# ---- 启动 worker ----
@app.on_event("startup")
async def startup():
    # 起多个消费者：提高从队列取 job 的能力（注意：下面真正的并发主要由信号量控制）
    for _ in range(4):
        asyncio.create_task(worker_loop())

async def worker_loop():
    while True:
        job: Job = await queue.get()
        try:
            # 一个 job 可能含多个 pdf：这里也可以并发，但建议再加一层job内并发限制
            for pdf_id in job.pdf_ids:
                asyncio.create_task(process_pdf(job.tenant_id, pdf_id))
        finally:
            queue.task_done()

# ---- 核心：处理一个 PDF（全局+租户闸门）----
async def process_pdf(tenant_id: str, pdf_id: str):
    tsem = tenant_sems[tenant_id]
    async with GLOBAL_PDF_SEM:
        async with tsem:
            # 1) 解析 PDF 得到页数/页对象（可能阻塞：放线程池）
            pages = await extract_pages_async(pdf_id)  # 例如返回页索引列表

            # 2) 单 PDF 内并发处理页
            page_sem = asyncio.Semaphore(PER_PDF_PAGE_CONCURRENCY)
            async with asyncio.TaskGroup() as tg:
                for page in pages:
                    tg.create_task(process_page_with_sem(page_sem, tenant_id, pdf_id, page))

            # 3) 汇总结果 / 回调 / 落库
            await finalize_pdf(pdf_id)

async def process_page_with_sem(page_sem, tenant_id, pdf_id, page):
    async with page_sem:
        # 页处理：如果CPU密集或阻塞IO，分别走进程池/线程池
        await process_page_async(tenant_id, pdf_id, page)

# ---- 示例：阻塞操作包装 ----
# 假设这些函数里用到了同步库（比如 pypdf、poppler、tesseract 等）
async def extract_pages_async(pdf_id: str):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, extract_pages_blocking, pdf_id)

def extract_pages_blocking(pdf_id: str):
    # 打开pdf，返回页列表（示例）
    return list(range(1, 101))

async def process_page_async(tenant_id: str, pdf_id: str, page: int):
    # 这里模拟I/O
    await asyncio.sleep(0.05)

async def finalize_pdf(pdf_id: str):
    await asyncio.sleep(0.01)
```

---

## 关键点（你一定会踩的坑，我提前给你挡）

### 1) 不要在接口里直接 `create_task` 一堆就算完

如果进程重启/崩溃，这些任务全丢。**至少要落库记录状态**，最好上外部队列。

### 2) 页级并发不要无限开

单 PDF 1000 页你开 1000 并发，内存/文件句柄/CPU 直接爆。
用 `PER_PDF_PAGE_CONCURRENCY` 控制住。

### 3) 多租户隔离：租户信号量 +（可选）权重

* 小租户：每租户并发 1~2 PDF
* 大租户：并发更高
  可以把 `tenant_sems` 做成按配置动态生成。

### 4) CPU 密集别用线程池硬扛（GIL）

如果页处理是 OCR/渲染/图像特征提取这类 CPU/外部命令为主：

* 外部命令（subprocess）通常 OK（不吃 GIL）
* 纯 Python CPU 密集：用 `ProcessPoolExecutor` 或拆成独立 worker 服务

### 5) 需要“取消/超时/重试”

生产环境通常要：

* 每页超时
* 每 PDF 超时
* 重试（指数退避）
* 幂等（同 pdf_id 重复通知不重复处理）

---

## 给你一个“建议的配置起点”（经验值）

* `GLOBAL_PDF_CONCURRENCY`: 4~16（看机器核数、内存、外部依赖）
* `PER_TENANT_PDF_CONCURRENCY`: 1~4（公平优先）
* `PER_PDF_PAGE_CONCURRENCY`: 4~12（看单页处理耗时 & 内存峰值）
* 队列 `maxsize`: 500~5000（要有 429 背压）

---

## 我可以帮你把它精确化

你只要告诉我下面三点（不用很准，拍个大概也行），我就能给你算一套更稳的默认值 + 该用线程池/进程池/外部队列的建议：

1. 单页处理是 **I/O 多** 还是 **CPU 多**？（比如：只抽文本 vs OCR/渲染）
2. 平均每个 PDF 页数大概多少？（10/100/1000？）
3. 峰值并发：同时可能来多少租户、多少 PDF？（比如：10 租户同时各 20 个）

不想回答也行——你按上面示例先搭起来就能跑，而且结构是可扩展到 Celery/RQ/Kafka 的。
