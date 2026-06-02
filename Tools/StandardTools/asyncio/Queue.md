## asyncio.Queue

`asyncio.Queue` 是 asyncio 里的**异步队列**，用于在多个协程之间安全地传递数据。

可以把它理解成异步版的 `queue.Queue`：

* `queue.Queue` → 线程之间通信
* `asyncio.Queue` → 协程之间通信

它是 asyncio 中实现 **生产者-消费者模式（Producer-Consumer）** 的核心工具之一。

---

### 1 为什么不用普通 list？

假设：

```python
items = []
```

生产者：

```python
items.append(data)
```

消费者：

```python
while not items:
    pass

data = items.pop(0)
```

问题：

1. 忙等（Busy Waiting）
2. 浪费 CPU
3. 协程无法优雅挂起

asyncio 希望：

```python
data = await queue.get()
```

如果没数据：

* 自动挂起当前协程
* 不占 CPU
* 有数据时自动唤醒

这就是 `asyncio.Queue` 的价值。

---

### 2 创建队列

```python
import asyncio

queue = asyncio.Queue()
```

无限大小。

也可以限制容量：

```python
queue = asyncio.Queue(maxsize=100)
```

最多放 100 个元素。

---

### 3 最基本示例

#### 3.1 Producer

```python
async def producer(queue):
    for i in range(5):
        print(f"produce {i}")
        await queue.put(i)
```

---

#### 3.2 Consumer

```python
async def consumer(queue):
    while True:
        item = await queue.get()

        print(f"consume {item}")

        queue.task_done()
```

---

#### 3.3 运行

```python
async def main():
    queue = asyncio.Queue()

    asyncio.create_task(producer(queue))
    asyncio.create_task(consumer(queue))

    await asyncio.sleep(3)

asyncio.run(main())
```

输出类似：

```text
produce 0
produce 1
produce 2
consume 0
consume 1
consume 2
...
```

---
### 4 常用 Method
#### 4.1 put()

向队列放数据：

```python
await queue.put(item)
```

---

无限队列：

```python
queue = asyncio.Queue()
```

永远不会阻塞。

---

有限队列：

```python
queue = asyncio.Queue(maxsize=2)
```

```python
await queue.put(1)
await queue.put(2)
await queue.put(3)
```

执行第三次时：

```python
await queue.put(3)
```

会挂起等待。

直到消费者取走一个元素。

---

#### 4.2  get()

获取数据：

```python
item = await queue.get()
```

如果队列为空：

```python
item = await queue.get()
```

当前协程自动挂起。

直到有生产者：

```python
await queue.put(...)
```

放入数据。

---

#### 4.3 qsize()

查看当前元素个数：

```python
queue.qsize()
```

例如：

```python
print(queue.qsize())
```

输出：

```text
5
```

---

#### 4.4 empty()

判断是否为空：

```python
queue.empty()
```

返回：

```python
True
False
```

---

#### 4.5 full()

判断是否已满：

```python
queue.full()
```

例如：

```python
queue = asyncio.Queue(maxsize=10)
```

```python
queue.full()
```

返回：

```python
True
False
```

---

#### 4.6 task_done()

这是很多人第一次看到最迷惑的地方。

消费者处理完成后：

```python
queue.task_done()
```

告诉 Queue：

> 这个任务我处理完了。

例如：

```python
item = await queue.get()

await process(item)

queue.task_done()
```

---

#### 4.7 join()

等待所有任务处理完成。

例如：

```python
await queue.join()
```

它会等待：

```python
put次数 == task_done次数
```

---

示例：

```python
async def producer(queue):
    for i in range(10):
        await queue.put(i)

async def consumer(queue):
    while True:
        item = await queue.get()

        await asyncio.sleep(1)

        queue.task_done()
```

主程序：

```python
await producer(queue)

await queue.join()
```

意思：

> 等待 10 个任务全部消费完。

---

#### 4.8 join() 工作原理

Queue 内部维护：

```python
unfinished_tasks
```

每次：

```python
await queue.put(...)
```

增加：

```python
unfinished_tasks += 1
```

---

每次：

```python
queue.task_done()
```

减少：

```python
unfinished_tasks -= 1
```

---

当：

```python
unfinished_tasks == 0
```

时：

```python
await queue.join()
```

解除阻塞。

---

### 5 多生产者多消费者

这是最常见的场景。

```python
queue = asyncio.Queue()
```

启动：

```python
for _ in range(5):
    asyncio.create_task(producer(queue))

for _ in range(10):
    asyncio.create_task(consumer(queue))
```

结构：

```text
Producer1 \
Producer2  \
Producer3   > Queue -> Consumer1
Producer4  /           Consumer2
Producer5 /            Consumer3
```

Queue 自动保证：

* 不会重复消费
* 不会丢数据
* 获取顺序正确

---

### 6 优雅关闭消费者

消费者通常：

```python
while True:
    item = await queue.get()
```

永远不会退出。

常见做法是放一个特殊值：

```python
None
```

---

生产者结束：

```python
await queue.put(None)
```

---

消费者：

```python
while True:
    item = await queue.get()

    if item is None:
        queue.task_done()
        break

    print(item)

    queue.task_done()
```

称为：

**Poison Pill（毒丸模式）**


### 7 Queue vs Semaphore

很多人会混淆。

#### 7.1 Semaphore

控制：

> 同时运行多少个任务

```python
sem = asyncio.Semaphore(10)
```

限制并发数。

---

#### 7.2 Queue

控制：

> 任务从哪里来

```python
queue = asyncio.Queue()
```

保存待处理任务。

---

实际项目经常一起用：

```python
Queue
   ↓
Worker
   ↓
Semaphore
   ↓
HTTP请求
```

例如：

```text
100000 URL
      ↓
 Queue
      ↓
 20 Worker
      ↓
 Semaphore(5)
      ↓
 网络请求
```

这样既能缓存任务，又能限制并发。

---

### 8 总结

`asyncio.Queue` 的核心能力：

| 方法             | 作用       |
| -------------- | -------- |
| `await put(x)` | 放入任务     |
| `await get()`  | 获取任务     |
| `task_done()`  | 标记任务完成   |
| `await join()` | 等待全部任务完成 |
| `qsize()`      | 当前长度     |
| `empty()`      | 是否为空     |
| `full()`       | 是否已满     |

最经典模式：

```python
queue = asyncio.Queue()

# Producer
await queue.put(task)

# Consumer
task = await queue.get()
...
queue.task_done()

# Wait all done
await queue.join()
```

几乎所有 asyncio 的任务池、爬虫、消息处理器、异步流水线，底层都会围绕 `asyncio.Queue` 构建。
