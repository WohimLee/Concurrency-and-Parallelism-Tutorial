## asyncio

### 一、asyncio 是做什么的？

asyncio 是 Python 的异步并发库，主要用于：

- 高并发 I/O 密集型任务（网络请求、数据库、文件、定时器等）
- 单线程 + 协程（不是多线程、不是多进程）
- 通过 事件循环（event loop） 调度任务

>核心思想
- 👉 遇到 I/O 就让出控制权，去做别的事情

### 二、最简单的 asyncio demo
#### 1️⃣ 定义一个协程（async function）
```py
import asyncio

async def hello():
    print("Hello")
    await asyncio.sleep(1)  # 模拟 I/O 等待
    print("World")
```

说明：
- async def：定义协程函数
- await：等待一个 可等待对象（协程 / Future / Task）

#### 2️⃣ 运行协程
```py
asyncio.run(hello())
```

输出：
```
Hello
（1 秒后）
World
```
### 三、并发执行多个协程（重点）
>❌ 错误示例（看起来是并发，实际是串行）
```py
async def task(name):
    print(f"{name} start")
    await asyncio.sleep(2)
    print(f"{name} end")

async def main():
    await task("A")
    await task("B")

asyncio.run(main())
```

执行时间：约 4 秒

>✅ 正确示例：并发执行
```py
async def task(name):
    print(f"{name} start")
    await asyncio.sleep(2)
    print(f"{name} end")

async def main():
    await asyncio.gather(
        task("A"),
        task("B"),
        task("C"),
    )

asyncio.run(main())
```

输出（顺序可能不同）：
```
A start
B start
C start
（2 秒后）
A end
B end
C end
```

⏱ 执行时间：约 2 秒

### 四、Task 的概念（显式创建任务）
使用 asyncio.create_task
```py
async def task(name):
    await asyncio.sleep(1)
    print(f"{name} done")

async def main():
    t1 = asyncio.create_task(task("task1"))
    t2 = asyncio.create_task(task("task2"))

    print("tasks created")

    await t1
    await t2

asyncio.run(main())
```

说明：
- create_task：把协程交给事件循环 立即调度
- Task 是对协程的封装

### 五、模拟真实场景：并发请求 demo
```py
import asyncio
import random

async def fetch_data(url):
    delay = random.uniform(0.5, 2)
    print(f"fetching {url}, delay={delay:.2f}s")
    await asyncio.sleep(delay)
    return f"data from {url}"

async def main():
    urls = [
        "https://api.service1.com",
        "https://api.service2.com",
        "https://api.service3.com",
    ]

    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)

    for r in results:
        print(r)

asyncio.run(main())
```

适用场景：
- HTTP 请求（配合 aiohttp）
- RPC 调用
- 数据库异步查询

### 六、asyncio 的核心概念总结
| 概念               | 说明          |
| ---------------- | ----------- |
| `async def`      | 定义协程        |
| `await`          | 挂起当前协程，等待结果 |
| Event Loop       | 事件循环，调度所有任务 |
| Coroutine        | 协程对象        |
| Task             | 被调度的协程      |
| `asyncio.run`    | 启动事件循环      |
| `asyncio.gather` | 并发执行多个协程    |


### 七、什么时候用 asyncio？什么时候不用？
>✅ 适合

- 网络请求
- Web 服务（FastAPI）
- 爬虫
- 高并发 I/O

>❌ 不适合

- CPU 密集型计算（用 multiprocessing）
- 需要阻塞调用的老库（除非用 run_in_executor）