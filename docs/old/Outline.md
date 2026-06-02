下面给你一份**重新设计的 step-by-step 大纲**：把 **FastAPI + asyncio + concurrent.futures + MQ** 串在一起，从一个极简例子出发，按“**碰到问题 → 必须加什么**”的逻辑逐步演进。你贴的 `lifespan + create_task(periodic_consume)` 会在后半段自然落地成“最终形态”。

我会用“阶段”来组织，每个阶段都包含：**目标、最小代码/结构、会遇到的问题、为什么必须加下一步**、验收标准。

---

## Stage 1｜只有 FastAPI：做一个最小服务

**目标**：跑起来，理解 FastAPI 的 async handler 是跑在事件循环里。
**最小结构**

* 一个 `GET /health`
* 一个 `POST /work` 模拟做点事（先 `await asyncio.sleep(0.1)`）

**很快会遇到的问题**

* “我要在服务启动时初始化资源（模型、DB client）怎么办？”

**必须加的东西**

* `lifespan`（你现在已经用的）来做启动/关闭钩子

**验收**

* 启动时打印“models loaded”；关机时打印“cleanup”

---

## Stage 2｜把“全局资源”放进 lifespan（你当前这段）

**目标**：掌握“生命周期内持有资源”的方式。
**最小结构**

* `set_models(load_models())`
* `set_db_client(...)`

**很快会遇到的问题**

* “我还要启动一个后台任务（比如 MQ consumer），不能阻塞启动，也不能影响 API 响应。”

**必须加的东西**

* `asyncio.create_task(...)` 在 lifespan 里启动后台协程（你已经做了）

**验收**

* API 可正常响应；后台任务每隔几秒打日志

---

## Stage 3｜后台任务 naive 版本：`create_task(periodic_consume)`

**目标**：理解 `create_task` 只是“调度”，不保证不会卡住事件循环。
**最小结构**

* `periodic_consume()`：`while True` → 拉消息 → 处理 → `await sleep`

**会遇到的问题（你已经遇到的）**

* “消息来了，但像是要等一会儿才开始处理”
* 或者 “API 卡顿/延迟变高”

**为什么发生**

* 你在后台协程里如果调用了任何**同步阻塞**操作（MQ SDK `.result()` / requests / time.sleep），就会**冻结整个 event loop**
  → 于是 Web 请求也会慢，后台处理也像“延迟”。

**必须加的东西**

* 把阻塞调用挪到线程池：`asyncio.to_thread` 或 `run_in_executor`

**验收**

* 后台 long poll 时，API 仍然丝滑；处理能立即开始

---

## Stage 4｜引入 `to_thread`：让 MQ 拉取不冻结事件循环

**目标**：掌握“同步 SDK + asyncio”的第一种正确集成方式。
**做法**

* `recv_msgs = await asyncio.to_thread(future.result)`（或 `await loop.run_in_executor(...)`）
* 禁止在 async 函数里直接 `.result()` / `time.sleep()` / requests

**会遇到的问题**

* “消息量一大，`create_task(consume_once)` 开很多任务，内存涨、延迟飙升、下游被打爆”
* 典型症状：任务堆积、CPU 低但延迟高（排队）

**必须加的东西**

* **背压（Backpressure）**：队列 + 并发上限

**验收**

* 突发 1w 消息时，服务不炸，延迟可控（哪怕变慢也可控）

---

## Stage 5｜引入 `asyncio.Queue`：把“拉取”和“处理”解耦

**目标**：形成标准结构：**puller → queue → workers**，并提供背压。
**结构**

* `queue = asyncio.Queue(maxsize=1000)`
* Puller：不断拉消息，`await queue.put(msg)`（满了就阻塞，形成背压）
* N 个 Worker：`msg = await queue.get()` → 处理 → `queue.task_done()`

**会遇到的问题**

* “处理函数里还有大量同步阻塞（模型推理可能 CPU、DB/HTTP 同步调用、PDF解析等）”
* 如果 worker 里直接跑同步逻辑，又会卡 event loop

**必须加的东西**

* 处理路径的“阻塞隔离”：线程池/进程池（concurrent.futures）

**验收**

* queue 深度能稳定；worker 并发可控；API 不受影响

---

## Stage 6｜引入 `concurrent.futures`：线程池/进程池隔离重活

**目标**：学会把“真正阻塞/重 CPU”的部分移出去。
**规则**

* **阻塞 I/O**（同步 MQ/HTTP/DB SDK）：线程池 `ThreadPoolExecutor`
* **CPU 密集**（向量计算/压缩/大批量预处理）：进程池 `ProcessPoolExecutor`
* async worker 里用：

  * `await asyncio.to_thread(blocking_io)`
  * 或 `await loop.run_in_executor(executor, fn, ...)`

**会遇到的问题**

* “线程池开太大/太小怎么调？线程池排队导致‘看起来延迟’”
* “任务超时、取消怎么做？超时后线程还在跑怎么办？”

**必须加的东西**

* 并发控制（Semaphore）+ 超时（wait_for）+ 可观测性（metrics/log）

**验收**

* 线程池队列长度可观测；超时可控；不会无限堆积

---

## Stage 7｜引入“并发上限 + 超时 + 取消”：让系统可控

**目标**：生产化必备三件套。
**做法**

* `sem = asyncio.Semaphore(MAX_INFLIGHT)`
* worker 里：`async with sem: await wait_for(process(msg), timeout=...)`
* 对 thread future：超时后只能“逻辑超时”（线程可能仍在跑），因此要设计：

  * 任务幂等
  * 超时后标记失败并回推/进入重试

**会遇到的问题**

* “消息确认（ACK）应该什么时候做？先 ack 还是后 ack？”
* “重复消费怎么办？”

**必须加的东西**

* ACK 策略 + 幂等设计 + 重试体系（DLQ / 业务回推）

**验收**

* 宕机/超时/重启不丢关键任务（或至少语义明确）

---

## Stage 8｜消息语义：ACK、重试、DLQ、幂等（结合你现有策略）

**目标**：把 MQ 变成“可靠系统”，而不是“最好能跑”。
**你现在策略**

* “先 ACK 再处理，失败走业务回推” → **at-most-once**（宕机会丢）

**会遇到的问题**

* “偶发丢消息/回推没发出去”
* “重复消息导致重复下发”

**必须加的东西（按你们业务选择）**

* 方案 A（推荐默认）：**处理成功再 ACK** + MQ 重投递 + DLQ
* 方案 B（保留你们策略）：**先 ACK** 但必须补：

  * 本地落库/outbox（先写任务表再 ack）
  * 启动时扫描未完成任务补偿
* 幂等：msg_id / business_key 去重表

**验收**

* 你能清晰说明你系统是 at-least-once 还是 at-most-once，并能证明不乱

---

## Stage 9｜把它和 FastAPI lifespan 融合成“最终模板”（对标你现在代码）

**目标**：在 lifespan 启动：

* 初始化资源（models/db）
* 启动 puller + worker pool
* 优雅停止：cancel + drain + shutdown threadpool

**结构落地（建议最终形态）**

* `app.state` 保存：

  * `queue`
  * `puller_task`
  * `worker_tasks`
  * `threadpool_executor`
  * `stop_event`（可选）
* shutdown 时：

  * cancel puller
  * 等 queue drain（可选，或设置超时）
  * cancel workers
  * `executor.shutdown(wait=False, cancel_futures=True)`（py>=3.9）

**会遇到的问题**

* “服务停止时还在处理消息，怎么不丢/怎么快停？”
* “两个 consumer（email + product）怎么隔离，互不影响？”

**必须加的东西**

* 每个 consumer 独立：自己的 queue、自己的 sem、自己的线程池前缀/metrics
* 统一的 ConsumerManager（可选）

**验收**

* stop 时日志干净；不会挂死；不会大量 CancelledError 冒泡

---

## Stage 10｜工程化加成：可观测性 + 压测 + 故障演练

**目标**：能定位“延迟来自哪里”。
**必须加的东西**

* 指标：pull 耗时、queue depth、processing p95、线程池排队、重试次数
* 日志字段：msg_id、trace_id、stage、elapsed_ms
* 压测脚本：模拟突发 10k 消息、下游限流、超时

**验收**

* 你能用数据回答：慢在拉取、排队、处理、还是回推

---

# 结合你现有代码：你现在处在什么阶段？

你现在已经完成了：

* Stage 1–3（FastAPI + lifespan + create_task 启动后台任务）

你正在卡在：

* Stage 3 → Stage 4 的“必须引入 to_thread/线程池隔离阻塞点”
  （你之前那个“消息延迟开始消费”就是典型症状）

---

# 给你一个从“最简单例子”开始的练习路径（建议按天）

1. Day1：Stage1-2（lifespan 管资源）
2. Day2：Stage3（后台 task + 心跳日志）
3. Day3：Stage4（把一个阻塞调用改成 to_thread，观察 API 不再卡）
4. Day4：Stage5（queue + workers，做背压）
5. Day5：Stage6-7（线程池 + 超时 + semaphore）
6. Day6：Stage8（ACK/幂等/重试策略落地）
7. Day7：Stage9-10（优雅停机 + metrics + 压测）

---

如果你想，我可以按这个大纲**直接给你 Stage5 的模板代码**（FastAPI lifespan 里启动：`puller + queue + N workers`），并把你们现有的 `periodic_consume` 改造成：

* 拉取：`to_thread`（不阻塞 loop）
* 处理：worker 并发上限 + 超时
* 失败：按你们“业务回推”策略走

你贴一下 `consumer.receive_async` 具体返回对象（是 `concurrent.futures.Future` 还是别的），我就能把桥接写得完全对。
