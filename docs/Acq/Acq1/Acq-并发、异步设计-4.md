可以做“起步版”，但按你现在这段写法，**在生产上会有 4 个硬伤**，会导致：吞吐上不去、偶发卡死、重试很难、以及多租户不公平。下面我先直接评价，再给你一版“最优可落地代码骨架”。

---

## 你这段代码能跑，但生产上主要问题

### 1) `Semaphore(1)` 只控了“PDF 级并发”，控不住你内部的“页级/向量化/入库”并发爆炸

你这里 `sem` 传给 `process_one()`，我猜你只在下载/解析 PDF 入口用了一下。

但真正会打爆的是：

* LLM：页标签 + 页抽取
* embedding：向量化
* ES：bulk 写入

这些需要**各自独立的全局限流器**，而不是只控 PDF 数量。

✅ 结论：`Semaphore` 要分资源：`llm_sem / embed_sem / es_sem`，并且最好再加 `tenant_sem[tenant_id]`。

---

### 2) 你在一个 request 里直接 `gather` 全部 PDF：容易造成“单 batch 消息占满 worker”

如果一条消息带 100 个 PDF，你会创建 100 个 task，即便 `sem=1`，task 也会把内存/调度/连接池压力拉满（很多 task 在排队等信号量也要占资源）。

✅ 更稳：用 `asyncio.TaskGroup`（py3.11）+ **分批（chunk）提交**，或用 `asyncio.Queue` worker 模式。

---

### 3) `return_exceptions=True` 只是“不炸”，但你没有“失败后的可恢复语义”

你现在只是 log error，然后继续。问题是：

* 这个 PDF 是否要重试？
* 重试次数？
* 是否进入 DLQ？
* 是否部分成功（ES 写入了一半）怎么办？

✅ 最稳：每个 PDF 处理要有 `pdf_job_id`，写 DB/内部队列状态机，失败可重入（幂等 doc_id + bulk upsert）。

---

### 4) ES 逻辑在 `gather` 前后检查一次 `get_data_size()` 意义不大，且可能造成额外负载

生产里 ES 查询要尽量少做，尤其是每次 batch 都查。你应该把“写入成功量、失败量、耗时”当成 metrics，而不是靠查数据量判断。

✅ 建议：ES 写入用 bulk，并记录 bulk 响应里的 success/fail + retry。

---

## 最优落地做法：**在“不改后端消息格式”的前提下，你内部拆成受控 pipeline**

### ✅ 你这段代码的正确改造方向（保持单消息多 PDF）

* **不要一次性 create 所有 task**
* 用 **队列 worker 模式** 控 PDF 并发
* 同时准备**资源级限流器**（LLM/Embed/ES）并传入 graph/nodes

下面给你一个“生产骨架版”，你可以直接套：

```python
import asyncio
from typing import Any

class Limits:
    def __init__(self):
        # 这些数值先给保守起步，后面压测调
        self.pdf_sem = asyncio.Semaphore(2)      # 同时跑几个PDF
        self.llm_sem = asyncio.Semaphore(10)     # 全局LLM并发
        self.embed_sem = asyncio.Semaphore(20)   # 全局embedding并发
        self.es_sem = asyncio.Semaphore(4)       # 全局ES bulk并发

        # 多租户公平：同一租户最多同时跑几个PDF
        self.tenant_sem: dict[int, asyncio.Semaphore] = {}

    def get_tenant_sem(self, tenant_id: int) -> asyncio.Semaphore:
        if tenant_id not in self.tenant_sem:
            self.tenant_sem[tenant_id] = asyncio.Semaphore(2)
        return self.tenant_sem[tenant_id]


async def process_one_pdf(
    omni_rag: Any,
    tenant_id: int,
    url: str,
    limits: Limits,
) -> Any:
    # PDF级 + 租户级限流（防止单租户吃满）
    tenant_sem = limits.get_tenant_sem(tenant_id)

    async with limits.pdf_sem, tenant_sem:
        # 注意：这里不是终点，真正关键是：
        # 你要在 graph 内部每次调用 LLM/embedding/ES 都用对应 semaphore 控
        return await omni_rag.ainvoke({
            "tenant_id": tenant_id,
            "pdf_url": url,
            "limits": limits,   # 👈 传进去给各节点用
        })


async def run_batch(request: dict):
    tenant_id = request["tenant_id"]
    pdf_urls = request.get("pdf_oss_urls", [])

    omni_rag = build_omnirag_graph()
    limits = Limits()

    # 用队列控制“提交压力”，而不是一次性 task 全开
    q: asyncio.Queue[str] = asyncio.Queue()
    for u in pdf_urls:
        q.put_nowait(u)

    results: dict[str, Any] = {}

    async def worker(worker_id: int):
        while True:
            try:
                url = q.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                r = await process_one_pdf(omni_rag, tenant_id, url, limits)
                results[url] = r
            except Exception as e:
                results[url] = e
                # 这里建议：记录 job 状态，决定是否重试/入DLQ
            finally:
                q.task_done()

    # PDF worker 数量 = 你希望“同一批消息”最多并发处理的 PDF 数
    # 一般 <= limits.pdf_sem 的值
    workers = [asyncio.create_task(worker(i)) for i in range(4)]
    await asyncio.gather(*workers)

    return results
```

---

## 关键中的关键：Graph 内部怎么用这些 semaphore（否则你还是会爆）

你现在最危险的是：**页级抽取/向量化/ES 写入**很可能在 graph 里又开了一堆并发。

正确姿势是：每个节点在做外部资源调用时都包一层：

```python
async with limits.llm_sem:
    resp = await llm.ainvoke(...)
```

```python
async with limits.embed_sem:
    vecs = await embedder.aembed_documents(batch_texts)
```

```python
async with limits.es_sem:
    await es.bulk(operations)
```

并且：

* ES 必须 bulk（别一条条写）
* embedding 必须 batch（别一条条 embed）

---

## 你现在这种“单消息多 PDF”还能更稳一点的策略（强烈建议）

### A) 给每个 PDF 生成 `pdf_job_id`（幂等）

用 `sha256(tenant_id + url)` 或者你们存储系统里已有的 file_id。
所有 ES doc_id / chunk_id 都基于这个生成，保证重试不会重复写。

### B) 这条 batch 消息的 ack 策略

* 如果你**有内部可靠落地（DB/内部队列）**：拆完就 ack 外部
* 如果你**没有内部落地**：那就只能“处理完再 ack”，但很容易超时/重复，风险高

---

## 你这段代码“能不能用”的结论

* ✅ **能跑**，适合 demo / 小流量
* ⚠️ **一上量就危险**：因为你只控了 PDF 级并发，控不住 LLM/embedding/ES 的真实瓶颈与限流
* ✅ 按我上面“两级限流 + 队列 worker + graph 内资源限流”的方式改，才能算生产级

---

如果你把 `process_one()` 里实际做的并发贴一下（尤其是：页级并发、embedding 并发、ES 写入方式），我可以直接帮你把“应该在哪些点加 semaphore、batch/bulk 怎么切、并发参数怎么配”标到具体位置上。
