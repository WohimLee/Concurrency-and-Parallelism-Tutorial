能搞，而且不一定要逼后端马上改。核心思路就一句话：

> **把“多 PDF 的大消息”在你的 worker 入口处拆成“单 PDF 子任务”，然后用你自己的队列/调度做背压与公平。**

下面给你一套“立刻能落地、不会把并发搞爆、还能兼容多租户”的最优改法。

---

## 最优方案：两级队列（外部 MQ 不动，你内部拆分再排队）

### 结构

1. **外部 MQ（后端发来的）**：`batch_jobs`

* 一条消息包含多个 PDF
* 你只负责“接住 + 拆分”，不要直接开多层并发处理

2. **内部队列（你自己维护）**：`pdf_jobs`（单 PDF 粒度）

* 拆成 `tenant_id + pdf_id + pdf_url + batch_id + idx` 这种“可幂等”的子任务
* 后续所有处理都只吃 `pdf_jobs`

### 好处

* ✅ 不改后端也能立刻稳定
* ✅ 并发控制变简单：只对 `pdf_jobs` 做并发
* ✅ 多租户公平：你可以对 `tenant_id` 做限流/配额
* ✅ 失败重试更干净：单 PDF 失败不会拖累整批
* ✅ 扩容容器实例更自然

---

## 关键细节 1：外部 batch 消息怎么 ack 才安全？

外部消息你不能“拆完就 ack”，也不能“全处理完再 ack”（会超时/锁死）。最稳的是：

### ✅ 推荐：**拆分落库/落队列成功后就 ack 外部 batch**

前提：你必须把“子任务”可靠地持久化（至少一种）：

* **A. 落到内部 MQ**（推荐：RabbitMQ/Kafka/Redis Streams/NATS 任选其一）
* **B. 或落到 DB 表**（outbox pattern，推荐 PostgreSQL/MySQL）

只要你能保证“外部 batch → 内部子任务”这一步是可靠的，就可以 ack 外部 batch。

> 换句话说：外部 MQ 只保证把“批”送到你这；你保证把“批”变成“可恢复的子任务”。

---

## 关键细节 2：避免重复拆分（幂等）

外部 MQ 可能重复投递（网络抖动/消费者重启），你必须做到**拆分幂等**。

### 做法

给每个 PDF 子任务一个确定性 `pdf_job_id`，比如：

* `hash(tenant_id + pdf_url + pdf_sha256)`
  或
* `batch_id + pdf_index + pdf_id`

拆分时写入内部队列/DB 用 “upsert / unique key” 保证不会重复入队。

---

## 关键细节 3：背压与并发怎么控（防止 batch 内 100 个 PDF 把你打爆）

拆分之后**不要立刻并发跑**。

### 你只需要控制两层并发：

1. **batch 拆分并发**：很小（1~2）
2. **pdf_jobs 消费并发**：按资源限流（LLM/Embedding/ES）+ 每租户限流

另外强烈建议：

* batch 消费者 `prefetch=1`（一次只拿一个 batch，避免“拆分风暴”）
* pdf 消费者 `prefetch=1~3`（控制“同时处理的 PDF 数”）

---

## 关键细节 4：多租户公平（非常实用）

拆分后，你可以做两种简单公平策略：

### 方案 A（最简单可用）：每租户一个队列（或 routing key）

* `pdf_jobs.tenantA`
* `pdf_jobs.tenantB`

消费者轮询，或按权重消费。

### 方案 B（更通用）：一个队列 + 你内部按 tenant 限流

用一个全局队列，但 worker 拿到任务后先过：

* `tenant_semaphore[tenant_id]`
  拿不到就把任务 requeue / 延迟重投（更优雅是“延迟队列/重试队列”）。

---

## 你问的“只能一条消息多个 PDF”下的最终推荐落地（不改后端）

### ✅ 最推荐组合

* 外部 MQ：保持不变（后端怎么发你怎么收）
* 你的拆分服务：**batch_consumer**
* 内部队列：**RabbitMQ 的 pdf_jobs 队列**
* 幂等：DB 表 `pdf_job`（unique(pdf_job_id)），状态机（PENDING/RUNNING/DONE/FAILED）

---

## 一个最小但生产级的状态机（建议你直接用）

**batch_received**

* batch_id, tenant_id?, pdf_list, received_at

**pdf_job**

* pdf_job_id（唯一）
* batch_id
* tenant_id
* pdf_url / storage_key
* status: PENDING/RUNNING/DONE/FAILED
* retries
* last_error
* updated_at

外部 batch 来了：

1. 解析 pdf_list
2. upsert pdf_job（幂等）
3. 对新建的 job 发到内部队列 `pdf_jobs`
4. ack 外部 batch

---

## 如果你不想引入“内部 MQ”，也能做：DB 队列（outbox）

就是拆分后只写 DB，然后 worker 轮询 `PENDING` 任务并 `SELECT … FOR UPDATE SKIP LOCKED` 抢占。

优点：组件少
缺点：吞吐通常不如 MQ，延迟/重试要自己做

---

## 你现在最该立刻做的 3 件事（不动后端也能稳定）

1. **加拆分层**：batch 消息只拆分，不做真正解析
2. **单 PDF 粒度进入内部队列/DB**：后面所有并发只针对单 PDF
3. **prefetch + semaphore**：prefetch 控“同时处理多少 PDF”，semaphore 控“LLM/embedding/ES 并发”

---

如果你告诉我：你们现在后端用的是哪种 MQ（Rabbit/Kafka/SQS/别的），以及平均每条消息包含多少 PDF、每个 PDF 平均页数，我可以把“prefetch、队列数量、租户限流参数、重试与 DLQ 规则”直接给你一套建议值。你不需要改架构，只要照着配就能跑稳。
