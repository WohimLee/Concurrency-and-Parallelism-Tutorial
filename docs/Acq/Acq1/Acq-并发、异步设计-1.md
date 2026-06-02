行，我先按“你现在的做法为什么容易失控/不稳”→“最优并发模型长什么样”→“落地实现建议（含 LangGraph 怎么接）”给你一套可扩容、可控、对多租户友好的方案。

---

## 你现在的结构最大的问题：**嵌套并发 = 并发爆炸 + 难做背压**

你描述的是：

* 线程池消费任务（任务里多个 PDF）

  * 并发处理每个 PDF

    * PDF 内并发处理页

      * 并发向量化

        * 并发入 ES

这会导致几个典型问题：

1. **并发爆炸**：一个消息 20 个 PDF × 每个 200 页 × 页内再起向量化/入库任务，瞬间就是几千/几万“同时要跑的东西”。
2. **背压缺失**：ES 或 Embedding 或 LLM 限流时，上游还在疯狂产出任务，最终内存/队列堆积、超时重试风暴。
3. **多租户公平性差**：一个大租户一波大 PDF，可能把所有并发占满，小租户饿死。
4. **重试难、幂等难**：嵌套层级越深，局部失败/重试会越难保证“不会重复入库/重复写向量”。

所以“最优方案”的核心不是把并发堆满，而是：

> **把并发做成可控的、分阶段的、带背压的流水线，并且按资源类型（CPU / LLM / Embedding / ES）分别限流。**

---

## 最优并发架构：**分阶段队列 + 每阶段限流 + 文档内只保留必要并发**

### 目标原则（很关键）

* **文档级并发**：可以并发多个 PDF（跨容器扩展也靠这个）
* **文档内并发**：只在“页级抽取/向量化/入库”这些“互不依赖”的阶段并发
* **必须顺序的阶段**（你已识别对了）：页标签（需要顺序信息）就**严格串行**
* **所有并发都必须被 semaphore/令牌桶限制**，并能对下游慢自动降速（背压）

---

## 推荐的 Pipeline（强烈建议按阶段拆队列）

### 阶段 0：Ingest（接 MQ 消息）

**建议：一条 MQ 消息最好只对应 1 个 PDF（或最多 N 个），不要一条消息塞很多 PDF。**
否则天然放大并发爆炸与失败影响面。

产物：`pdf_job`（包含 tenant_id / pdf_id / 存储地址 / tracing_id）

---

### 阶段 1：PDF 解析与分页（CPU/IO）

* 做：下载、解密（如果有）、抽取文本/布局、分页对象（page blobs）
* 产物：`page_assets`（每页文本、图片、bbox、页序号）

> 这一步如果是纯 Python + 重 CPU（比如 OCR、版面分析），用 **ProcessPool** 或者独立“CPU Worker”队列更稳。
> 不要让它和 LLM/Embedding 混在同一个 event loop 里抢资源。

---

### 阶段 2：页标签（顺序 LLM 或规则+LLM）——**文档内串行**

你现在的判断“需要顺序信息所以不异步”是对的。

但我建议再加两点优化：

1. **不要按页逐个调 LLM**（很贵也慢）
   更好的：按窗口滑动（比如每次给 5~10 页，带上页码和上一窗口的摘要），让模型输出每页标签 + 关键结构信号。
2. **这一步也要限流**（LLM API 是共享资源）

产物：`page_labels`（page_idx -> label + confidence + section_id）

---

### 阶段 3：页级信息抽取（并发，受控）

对“产品页、公司页、资质页”等可并发抽取，但并发要**受控**：

* 只并发“需要抽取的页”（过滤目录页/封面等）
* 用 `Semaphore(max_extract_concurrency)` 限制该 PDF 内同时抽取页的数量
* 也要有**全局 LLM 限流**（跨所有 PDF）

产物：结构化 JSON（按页/按 section 聚合）

---

### 阶段 4：向量化（并发 + 批处理）

向量化最常见的最优解是：

* **批处理**：把多个 chunk 组成 batch 调 embedding（吞吐比逐条高很多）
* **并发受控**：`Semaphore(max_embed_concurrency)`
* **按租户限流**：避免某个租户把 embedding 打满导致别人排队

产物：`embeddings`（chunk_id -> vector）

---

### 阶段 5：写入 ES（bulk + 幂等）

* **永远 bulk 写**（比如 500~2000 docs/批，视 ES 配置调）
* 失败重试要“可重入”：

  * doc_id 设计成确定性的（tenant_id + pdf_id + page + chunk_hash）
  * 用 upsert / versioning，避免重试产生重复数据
* 并发写也要限流：`Semaphore(max_es_concurrency)`

---

## 关键点：并发控制的“正确姿势”

### 你需要的不是“多层线程池”，而是“资源类型限流 + 背压”

把并发控制分成 4 类资源，每类一个全局限流器：

1. **CPU 限流**：PDF 解析/OCR
2. **LLM 限流**：页标签 + 页抽取（可以拆两类限流，避免标签被抽取挤压）
3. **Embedding 限流**
4. **ES 写入限流**

并且每个 PDF 内再有一个“文档局部并发上限”，防止单 PDF 页数太多把全局并发占满。

---

## 多租户最容易踩坑的点：公平性（Fairness）

建议你至少做到这三件事：

1. **队列层做隔离或权重**

   * 简单版：按 tenant_id 分桶（hash 到多个队列），消费者多队列轮询
   * 进阶版：Priority Queue / Weighted Fair Queue（大客户权重大但不会饿死小客户）
2. **每租户限流器**（token bucket）

   * LLM：每租户每分钟最大请求数 / token 数
   * Embedding：每租户并发数
3. **每租户并发 PDF 上限**
   比如同一租户最多同时跑 3 个 PDF，其他排队。

---

## LangGraph 在你这怎么用才“对”

LangGraph 的确支持异步节点，但重点在于：

* **LangGraph 负责流程编排**（依赖关系、状态传递、失败恢复）
* **并发/限流要在节点内部用 async semaphore 控制**，不要让图“无限并发地扔任务”

推荐的图结构（概念）：

* `parse_pdf`（可能跑在 CPU worker）
* `label_pages_sequential`（串行）
* `extract_pages_parallel`（并发受控：gather + semaphore）
* `chunk_and_embed_batch`（batch + 限流）
* `bulk_index_es`（bulk + 限流）

如果你用 LangGraph 的并行边/Map 节点，一定要**明确设置并发上限**（如果框架层不好设，就在你自己的 map worker 里控）。

---

## 你现在“最该改”的 5 个具体改动（直接照做就会稳很多）

1. **MQ 消息粒度改成“1 PDF 1 job”**（或最多 3~5 个 PDF），杜绝一条消息几十个 PDF
2. **去掉多层线程池嵌套**：

   * IO/LLM/Embedding/ES 用 `asyncio` + `httpx.AsyncClient`
   * CPU 重活用 `ProcessPoolExecutor` 或拆独立 CPU worker 队列
3. **加全局限流器 + 每租户限流器**（LLM、Embedding、ES 三个必加）
4. **向量化 & ES 写入必须 batch/bulk**（吞吐和成本差一个数量级）
5. **幂等 ID + 可重试设计**：chunk_id / doc_id 确定性生成，避免重试重复入库

---

## 一个“可落地”的并发配置参考（起步值）

你可以先用这个做 baseline（再压测调参）：

* `MAX_PDF_IN_FLIGHT_PER_WORKER = 2~4`
* `MAX_PAGES_EXTRACT_PER_PDF = 5~10`
* `MAX_LLM_CONCURRENCY_GLOBAL = 10~30`（看你供应商限额）
* `MAX_EMBED_CONCURRENCY_GLOBAL = 10~50`（batch 后通常不需要很高）
* `MAX_ES_BULK_CONCURRENCY = 2~8`
* `BULK_SIZE_ES = 500~2000`
* `EMBED_BATCH_SIZE = 64~256`（看模型/长度/延迟）

---

## 你如果只想要一句话版“最优方案”

> **把“多层嵌套并发”改成“分阶段流水线 + 每阶段限流 + batch/bulk + 幂等重试 + 多租户公平调度”，文档内只在可并行的页抽取/向量化/入库阶段做受控并发，页标签阶段保持串行。**

---

如果你愿意，我还能基于你们的实际约束（LLM/embedding 供应商限额、平均 PDF 页数、容器 CPU/内存、ES 写入指标）给你一套“压测→算并发→算队列长度→算扩容阈值”的参数化方案；但就算不补这些信息，上面这套改完，你的系统稳定性和可扩展性一般都会立刻上一个台阶。
