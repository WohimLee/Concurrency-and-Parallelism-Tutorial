单页处理是 I/O 多 （比如：LLM API 抽取文本）

平均每个 PDF 页数大概5-50页

峰值并发：目前还比较少，但是要考虑后续可能的情况（不过后续应该会用k8s去做多个容器实例）


好，那你的场景属于 **I/O 型（LLM API）+ 页数不大（5–50）+ 未来会水平扩展（k8s 多副本）**。最重要的是：**别把“并发”变成“把上游 API/你自己打挂”**，所以建议用“全局+租户+页级”三层闸门，并且把限流点放在 **“LLM 调用处”**，而不是只限 PDF 数。

下面给你一套**默认配置起点 + k8s 扩展思路 + 代码结构要点**。

---

## 推荐的并发策略：以“LLM 调用并发”为中心

### 为什么？

你单页处理主要花在 LLM API（外部 I/O），瓶颈通常是：

* 上游的 QPS / 并发限制（429）
* 你的网络连接数
* 你的费用/速率预算

所以最关键的 semaphore 其实是：

> **全服务同时进行的 LLM 请求数（in-flight requests）**

---

## 一套可用的默认参数（起步就稳）

假设你每个 LLM 请求平均 2–10 秒，页数 5–50：

### 单实例（一个 FastAPI worker 进程）推荐：

* **全局 LLM 并发**：`GLOBAL_LLM_CONCURRENCY = 16`（先从 8 或 16 起）
* **每租户 LLM 并发**：`PER_TENANT_LLM_CONCURRENCY = 4`
* **单 PDF 页并发**：`PER_PDF_PAGE_CONCURRENCY = 4`（页数不大，4 足够，避免突刺）
* **同时处理的 PDF 数（可选）**：`GLOBAL_PDF_CONCURRENCY = 8`（更多是控制内存/下载/解析压力）

> 经验：**LLM 并发（16）通常比“PDF 并发”更重要**。

---

## 未来 k8s 多副本时怎么想

你会变成：`总并发 = 单副本并发 × 副本数`

所以要提前规划两种限制：

### 1) 进程内限制（Semaphore）只能管“本副本”

每个 Pod 都放 `GLOBAL_LLM_CONCURRENCY=16`，开 10 个 Pod 就是 160 并发，可能直接把上游打 429。

### 2) 分布式全局限流（建议后续补）

如果你希望“全集群总并发/总QPS”可控，通常用：

* Redis-based rate limiter（全局 token bucket / leaky bucket）
* 或者用队列系统把吞吐稳定下来（Celery/RQ/Kafka consumer 数量就是并发旋钮）
* 或者服务网关层（APISIX/Envoy）限流

**你现在可以先用本地 Semaphore 起步**，但上线到多副本前，建议加 Redis 限流（最实用）。

---

## 代码结构：把闸门放在 LLM 调用处（核心）

你可以这样分层：

* PDF 任务：下载/解析 -> 得到 pages
* 每页任务：提取页文本 -> 调 LLM -> 写结果
* 关键：`call_llm()` 内部统一限流 + 重试 + 429 退避

### 关键示意（只看结构）

```py
GLOBAL_LLM_SEM = asyncio.Semaphore(16)
tenant_llm_sems = defaultdict(lambda: asyncio.Semaphore(4))

async def call_llm(tenant_id: str, payload: dict):
    async with GLOBAL_LLM_SEM:
        async with tenant_llm_sems[tenant_id]:
            return await llm_request_with_retry(payload)
```

然后每页处理里就直接：

```py
async def process_page(tenant_id, pdf_id, page):
    # ...准备prompt...
    resp = await call_llm(tenant_id, payload)
    # ...落库...
```

这样不管你怎么并发 pages，真正会打到 LLM 的并发都会被管住。

---

## 重试与退避（LLM 场景必备）

建议策略：

* 遇到 `429 / 503 / 超时`：指数退避 + jitter
* 尊重上游 `Retry-After`（如果有）
* 每页最多重试 5 次
* 超过就把该页标记失败，PDF 继续（或整单失败看业务）

这会让系统在突发时“自动变慢但不崩”。

---

## 入队/后台处理建议（你后续上 k8s 会更顺）

即使你现在峰值不大，也建议你**接口只接收事件并入队**，因为：

* 你未来会多副本
* 需要幂等、防重、可恢复
* 处理可能很久（LLM）

最小可行：

* 落库一条 job 记录（tenant_id, pdf_id, status）
* 后台 worker 扫描 PENDING 任务处理（或 asyncio.Queue）

生产推荐（后续）：

* Redis + RQ/Celery
* 或 Kafka（更重）

---

## 给你一个“起步不踩坑”的配置建议

### 如果你现在是单机、上游 LLM 限制不严格：

* `GLOBAL_LLM_CONCURRENCY=16`
* `PER_TENANT_LLM_CONCURRENCY=4`
* `PER_PDF_PAGE_CONCURRENCY=4`
* `GLOBAL_PDF_CONCURRENCY=8`

### 如果你经常遇到 429：

* `GLOBAL_LLM_CONCURRENCY` 降到 8
* 加强退避（并把重试时间拉长）
* 或按租户权重调整（大租户更高，小租户更低）

---

## 一个很实用的小技巧：分“快路径/慢路径”

页数 5–10 的 PDF，可以更激进一点；50 页的保守一点：

* 小 PDF：`PER_PDF_PAGE_CONCURRENCY=6`
* 大 PDF：`PER_PDF_PAGE_CONCURRENCY=3`

但注意：**最终仍然受 `call_llm()` 的全局/租户信号量约束**，所以不会失控。

---

如果你愿意，我可以按你实际 LLM 供应商（OpenAI/Claude/自建）和你现在的部署方式（uvicorn worker 数、是否多进程）把参数再收敛一下，并给你一段“带重试+退避+metrics（prometheus）”的 `call_llm()` 模板。你现在 FastAPI 是单 worker 单进程，还是 gunicorn/uvicorn 多 worker？
