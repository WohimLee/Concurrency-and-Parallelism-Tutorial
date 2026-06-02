明白了：一旦引入 **LLM API**，你最核心的风险就变成了 **“慢 + 贵 + 易被限流/失败”**。所以通信栈要围绕 **异步化、限流隔离、可追踪、可回放** 来设计。

## 推荐的整体通信技术栈（Python 生产级、LLM 友好）

### 1) 同步层（对话端/网页端入口）

* **FastAPI + HTTP/JSON**（对外最好用）
* 内部服务调用如果多：可加 **gRPC**（可选）

用途：

* 搜索/推荐：同步返回（低延迟）
* 背调/解析：同步只返回 `job_id`（不要让入口卡住）

---

### 2) 异步任务层（LLM 调用必备）

**强烈建议：Celery + RabbitMQ + Redis（缓存/幂等/速率限制）**

* RabbitMQ：任务分发更适合“任务队列”（重试、优先级、routing）
* Celery：Python 生态成熟，快速落地
* Redis：存幂等 key、短期结果、限流令牌、热点缓存

> 你之前问“Celery+Redis算不算生产级 MQ”：
> 在你这个场景，它可以跑，但我更推荐把 **Broker 换成 RabbitMQ**，Redis 做缓存/锁/限流。

---

### 3) 事件/通知层（把结果推回对话端）

两种都行，按你对话端能力选：

* **Webhook 回调**（最简单）：任务完成后回调对话端的 URL
* **WebSocket/SSE**（如果你们自己前端要实时显示进度）
* 若你们已经有企业 IM/聊天平台：也可用它的回调机制

实践里常见是：

* “任务完成 → 你的服务发 webhook 给对话端”
* 对话端也可以轮询 `GET /jobs/{id}` 兜底

---

## 针对你两个新增点：LLM API 的关键设计

### A) 给 LLM 调用做“隔离队列 + 限流”

不要所有任务共用一个队列/worker。

建议至少分 3 类队列（RabbitMQ routing）：

1. `parse.high`：PDF/官网解析的关键路径（用户等待中）
2. `parse.low`：离线补全、二次结构化、索引更新
3. `llm.reco`：推荐生成（可控并发）

每类队列配不同 worker 数、并发数、超时、重试策略。

限流建议（非常实用）：

* **全局限流**：按你们 LLM 的 RPM/TPM 限制
* **租户限流**：防止单一租户刷爆额度
* **任务级超时**：每次 LLM 调用设置 hard timeout

Redis 做令牌桶（token bucket）很常见：

* key: `llm:global`, `llm:tenant:{tenant_id}`
* worker 取令牌才允许发请求

---

### B) LLM 结果“缓存 + 去重”（省钱神器）

对解析和推荐都很重要：

* **解析**：相同文件（hash）+ 相同 prompt 版本 → 直接复用结果
* **推荐**：相同 query + filters + prompt_version（或 embedding_version）→ 缓存短 TTL

缓存存 Redis，长期结果入 DB（Postgres）。

---

### C) 解析要做成 pipeline（LLM 只是其中一步）

不要一个 Celery 任务从头干到尾，建议拆成阶段，失败更容易补偿：

**PDF 解析建议链路**

1. `extract_text(file_id)`（本地解析/ocr）
2. `chunk_and_clean(file_id)`
3. `llm_structuring(file_id, chunk_id...)`（LLM 调用，限流隔离）
4. `merge_and_validate(file_id)`（结构校验、置信度）
5. `index_to_search(file_id)`（写 ES/OpenSearch）
6. `notify_done(job_id)`

这样你可以：

* 某一步失败只重跑那一步
* 可以并行（chunk 多个并发，但受限流控制）

---

### D) 推荐“同步返回”还是“异步返回”？

看体验目标：

* **需要秒回**：先返回 “规则/检索召回” 的候选 + 简短答案
  LLM 只做轻量 rerank/summary（严格超时 1-2s）
* **允许稍慢（3-8s）**：同步调用 LLM，但必须：

  * 强超时
  * 降级策略（LLM 超时→返回非 LLM 结果）
* **需要高质量且可稍后补全**：先回基础结果，再异步补充“更好的推荐解释/文案”，通过 webhook 推送二段消息

我对“对话端推荐”更推荐：

> **同步：检索/规则出结果 +（可选）轻量 LLM**
> **异步：更精细的 LLM 解释/搭配/邮件文案等**

---

## 你这三类业务的最终落地映射（含 LLM）

1. 背调核验（外部 API + 不确定耗时）

* HTTP 接入 → `verify.requested` 任务 → worker 执行（带重试、熔断）→ 结果入库 → webhook 回调

2. PDF/官网解析（LLM + pipeline）

* 上传/提交 URL → `parse.requested` → 多阶段任务（含 `llm_structuring` 隔离队列+限流）→ 建索引 → webhook / 前端查询状态

3. 搜索/推荐（LLM）

* 同步：ES/OpenSearch 查询 + Redis 缓存
* LLM：轻量同步（严格超时）或异步补强（二段返回）

---

## 最小但“生产级”的组件清单

* **FastAPI**
* **RabbitMQ（broker）**
* **Celery（workers）**
* **Redis（缓存/幂等/限流/状态）**
* **PostgreSQL（任务状态、结果、审计）**
* **S3/OSS/MinIO（文件）**
* **OpenSearch/Elasticsearch（搜索）**
* 可观测：Prometheus + Grafana + Sentry（至少要错误追踪）

---

如果你要我直接给你“可落地配置”，我可以按你的业务把：

* 队列划分（exchange/queue/routing key）
* Celery worker 并发/超时/重试策略
* LLM 限流（全局+租户）设计
* 推荐的降级策略（超时/额度/错误时怎么回）

都写成一份清单。
你们用的 LLM 是哪家（OpenAI/Anthropic/阿里/火山等）以及大致的 RPM/TPM 额度范围？我就能把限流参数和队列并发给你定到可用的级别。
