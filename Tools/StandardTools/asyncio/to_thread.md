## to_thread

`asyncio.to_thread()` 是 Python 3.9 引入的一个工具，用来**在 asyncio 程序中把阻塞函数放到线程池里执行**，避免阻塞事件循环（event loop）。

### 1 为什么需要它？

假设你在异步代码里调用一个普通同步函数：

```python
import asyncio
import time

def blocking_task():
    time.sleep(5)  # 阻塞5秒
    return "done"

async def main():
    print("start")
    result = blocking_task()  # 阻塞整个事件循环
    print(result)

asyncio.run(main())
```

这里 `time.sleep(5)` 会让整个事件循环停下来 5 秒，期间所有协程都无法运行。

而使用 `to_thread()`：

```python
import asyncio
import time

def blocking_task():
    time.sleep(5)
    return "done"

async def main():
    print("start")

    result = await asyncio.to_thread(blocking_task)

    print(result)

asyncio.run(main())
```

此时：

* `blocking_task()` 在单独线程执行
* asyncio 事件循环继续运行
* 其他协程不会被卡住

---

### 2 基本语法

```python
result = await asyncio.to_thread(func, *args, **kwargs)
```

等价于：

```python
loop = asyncio.get_running_loop()

result = await loop.run_in_executor(
    None,      # 默认线程池
    func,
    *args
)
```

例如：

```python
import asyncio

def add(a, b):
    return a + b

async def main():
    result = await asyncio.to_thread(add, 1, 2)
    print(result)

asyncio.run(main())
```

输出：

```text
3
```

---

### 3 一个更直观的例子

假设有两个协程：

```python
import asyncio
import time

def blocking():
    time.sleep(5)
    return "finished"

async def heartbeat():
    while True:
        print("tick")
        await asyncio.sleep(1)

async def main():
    task = asyncio.create_task(heartbeat())

    result = await asyncio.to_thread(blocking)

    print(result)
    task.cancel()

asyncio.run(main())
```

运行效果：

```text
tick
tick
tick
tick
tick
finished
```

如果直接调用 `blocking()`，则 5 秒内一个 `tick` 都不会出现。

---

### 4 适合什么场景？

#### 4.1. 文件 I/O

```python
def read_big_file():
    with open("data.txt") as f:
        return f.read()

content = await asyncio.to_thread(read_big_file)
```

---

#### 4.2. 调用同步库

很多第三方库没有 async API：

```python
import requests

def fetch():
    return requests.get("https://example.com").text

html = await asyncio.to_thread(fetch)
```

不过如果有异步版本（如 `aiohttp`），通常优先使用异步版本。

---

#### 4.3. 数据库驱动不支持 asyncio

```python
def query_db():
    return cursor.execute(sql).fetchall()

rows = await asyncio.to_thread(query_db)
```

---

### 5 与 create_task 的区别

很多人容易混淆：

```python
asyncio.create_task(...)
```

和

```python
asyncio.to_thread(...)
```

区别：

| 方法              | 执行对象      | 运行位置        |
| --------------- | --------- | ----------- |
| `create_task()` | coroutine | Event Loop  |
| `to_thread()`   | 普通同步函数    | Thread      |
| `await`         | 等待协程      | Event Loop  |
| `to_thread`     | 包装同步函数    | Thread Pool |

例如：

```python
async def foo():
    ...

asyncio.create_task(foo())
```

这里 `foo` 本身就是异步函数。

而：

```python
def foo():
    ...

await asyncio.to_thread(foo)
```

这里 `foo` 是同步函数。

---

### 6 CPU 密集型任务能用吗？

技术上能：

```python
await asyncio.to_thread(cpu_heavy_work)
```

但通常**效果不好**。

原因是 Python 的 **GIL（全局解释器锁）**：

```python
def cpu_heavy():
    sum(i*i for i in range(10**8))
```

放在线程里：

```python
await asyncio.to_thread(cpu_heavy)
```

不会真正并行执行 CPU 计算。

对于 CPU 密集型任务，更推荐：

```python
ProcessPoolExecutor
```

或者：

```python
multiprocessing
```

实现多进程并行。

#### 6.1 经验法则

* I/O 密集型 → `asyncio.to_thread()`
* CPU 密集型 → `ProcessPoolExecutor`

---

### 7 ContextVar 会自动传递

`to_thread()` 相比老式 `run_in_executor()` 的一个优点是会自动复制当前上下文（`contextvars`）。

例如：

```python
import asyncio
import contextvars

request_id = contextvars.ContextVar("request_id")

def worker():
    print(request_id.get())

async def main():
    request_id.set("abc123")
    await asyncio.to_thread(worker)

asyncio.run(main())
```

输出：

```text
abc123
```

而很多旧的 `run_in_executor()` 用法做不到这一点。

---

### 8 总结

`asyncio.to_thread()` 的核心作用可以概括为：

> **把阻塞的同步函数丢到线程池执行，并以 await 的方式获取结果，从而不阻塞 asyncio 事件循环。**

典型写法：

```python
result = await asyncio.to_thread(
    blocking_func,
    arg1,
    arg2,
)
```

最常见用途：

* 文件读写
* 调用同步 HTTP 库（如 requests）
* 调用同步数据库驱动
* 任何无法改造成 async 的阻塞 I/O 操作

不推荐用于：

* 大量 CPU 计算
* 需要真正并行计算的场景（应使用多进程）
