## asyncio.run_coroutine_threadsafe

`asyncio.run_coroutine_threadsafe()` 是 asyncio 里一个比较高级、但非常实用的 API。

它解决的问题是：

> **在一个普通线程里，向另一个线程中的 asyncio Event Loop 提交协程执行。**

简单说：

```text
线程A（普通线程）
    │
    │ 提交 coroutine
    ▼
线程B（运行 EventLoop）
    │
    ▼
执行协程
```

---

### 1 为什么需要它？

先记住 asyncio 的一个重要原则：

> Event Loop 不是线程安全的。

例如：

```python
loop.create_task(coro())
```

只能在 Event Loop 所在线程调用。

如果你在另一个线程直接这么干：

```python
threading.Thread(
    target=lambda: loop.create_task(coro())
)
```

可能出现：

```text
RuntimeError
Task attached to a different loop
线程竞争问题
```

因为：

```text
Task
Future
Ready Queue
Scheduled Queue
```

这些内部结构都不是为跨线程直接操作设计的。

---

### 2 run_coroutine_threadsafe 的作用

官方提供的安全方案：

```python
asyncio.run_coroutine_threadsafe(
    coro,
    loop
)
```

意思是：

```text
把 coro 安全提交给 loop 所在线程执行
```

---

### 3 函数签名

```python
asyncio.run_coroutine_threadsafe(
    coro,
    loop
)
```

参数：

* `coro`

  * 协程对象

* `loop`

  * 目标事件循环

返回：

```python
concurrent.futures.Future
```

注意：

不是：

```python
asyncio.Future
```

而是：

```python
concurrent.futures.Future
```

---

### 4 最简单示例

#### 4.1 Event Loop 线程

```python
import asyncio
import threading

loop = asyncio.new_event_loop()

def loop_thread():
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(
    target=loop_thread,
    daemon=True
).start()
```

---

定义协程：

```python
async def hello():
    await asyncio.sleep(1)
    return "hello"
```

---

主线程提交：

```python
future = asyncio.run_coroutine_threadsafe(
    hello(),
    loop
)

print(future.result())
```

输出：

```text
hello
```

---

### 5 它内部做了什么？

大致流程：

```text
run_coroutine_threadsafe()
        │
        ▼
call_soon_threadsafe()
        │
        ▼
create_task(coro)
        │
        ▼
Task执行
        │
        ▼
结果写入 concurrent.futures.Future
```

源码思路类似：

```python
future = concurrent.futures.Future()

def callback():
    task = loop.create_task(coro)

    task.add_done_callback(
        lambda t: future.set_result(
            t.result()
        )
    )

loop.call_soon_threadsafe(callback)

return future
```

当然真实实现复杂得多。

---

### 6 为什么返回 concurrent.futures.Future？

因为调用者通常不在 Event Loop 里。

例如：

```python
threading.Thread(...)
```

里的代码根本不能：

```python
await something
```

因此返回一个线程友好的 Future：

```python
future.result()
```

就能阻塞等待结果。

---

例如：

```python
future = asyncio.run_coroutine_threadsafe(
    hello(),
    loop
)

result = future.result(timeout=5)
```

---

### 7 获取异常

如果协程抛异常：

```python
async def boom():
    raise ValueError("bad")
```

提交：

```python
future = asyncio.run_coroutine_threadsafe(
    boom(),
    loop
)
```

取结果：

```python
future.result()
```

抛出：

```text
ValueError: bad
```

异常会自动从协程传播出来。

---

### 8 取消协程

返回的 Future 可以取消：

```python
future.cancel()
```

例如：

```python
future = asyncio.run_coroutine_threadsafe(
    long_task(),
    loop
)

future.cancel()
```

对应的 asyncio Task 也会收到：

```python
CancelledError
```

---

### 9 与 call_soon_threadsafe 的关系

很多人会同时看到：

```python
loop.call_soon_threadsafe(...)
```

和：

```python
asyncio.run_coroutine_threadsafe(...)
```

区别：

| API                        | 提交对象   |
| -------------------------- | ------ |
| `call_soon_threadsafe`     | 普通回调函数 |
| `run_coroutine_threadsafe` | 协程     |

---

例如：

提交普通函数：

```python
loop.call_soon_threadsafe(
    print,
    "hello"
)
```

---

提交协程：

```python
asyncio.run_coroutine_threadsafe(
    hello(),
    loop
)
```

---

实际上：

```text
run_coroutine_threadsafe
        ↓
call_soon_threadsafe
        ↓
create_task
```

是建立在后者之上的。

---

### 10 典型场景 1：同步代码调用异步代码

例如你的项目：

```text
Flask
线程池
Django
Celery
GUI程序
```

里面已经有一个 asyncio Loop 在后台运行。

同步函数想调用：

```python
async def send_message():
    ...
```

就可以：

```python
future = asyncio.run_coroutine_threadsafe(
    send_message(),
    loop
)

result = future.result()
```

---

### 11 典型场景 2：WebSocket 服务

后台：

```python
async def websocket_server():
    ...
```

运行在 asyncio Loop。

---

另一个线程收到消息：

```python
def on_message(data):
```

需要广播：

```python
await ws.send(data)
```

这时不能直接 await。

可以：

```python
asyncio.run_coroutine_threadsafe(
    broadcast(data),
    loop
)
```

---

### 12 典型场景 3：GUI + asyncio

例如：

* Tkinter
* PyQt
* wxPython

GUI 主线程：

```text
GUI Event Loop
```

Async 网络层：

```text
Asyncio Event Loop
```

放在另一线程。

按钮点击：

```python
def on_click():
    asyncio.run_coroutine_threadsafe(
        fetch_data(),
        loop
    )
```

---

### 13 与 asyncio.to_thread 的区别

很多人会混。

#### 13.1 asyncio.to_thread

方向：

```text
Async
 ↓
Thread
```

把同步函数丢到线程执行。

```python
await asyncio.to_thread(func)
```

---

#### 13.2 run_coroutine_threadsafe

方向：

```text
Thread
 ↓
Async
```

把协程丢到 Event Loop 执行。

```python
asyncio.run_coroutine_threadsafe(
    coro,
    loop
)
```

可以把它们看成互逆关系：

```text
Async → Thread
    asyncio.to_thread()

Thread → Async
    run_coroutine_threadsafe()
```

---

### 实战示例

```python
import asyncio
import threading

loop = asyncio.new_event_loop()

def start_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(
    target=start_loop,
    daemon=True
).start()


async def add(a, b):
    await asyncio.sleep(1)
    return a + b


future = asyncio.run_coroutine_threadsafe(
    add(1, 2),
    loop
)

print(future.result())
```

输出：

```text
3
```

流程：

```text
Main Thread
    │
    ▼
run_coroutine_threadsafe()
    │
    ▼
Loop Thread
    │
    ▼
Task(add)
    │
    ▼
Result=3
    │
    ▼
concurrent.futures.Future
    │
    ▼
future.result()
```

---

### 一句话总结

`asyncio.run_coroutine_threadsafe()` 是：

> **从非 Event Loop 线程安全地向指定 Event Loop 提交协程执行，并返回一个 `concurrent.futures.Future` 用于等待结果、获取异常或取消任务。**

记忆口诀：

```text
to_thread:
    Async → Thread

run_coroutine_threadsafe:
    Thread → Async
```

这两个 API 经常成对出现，是 asyncio 与传统多线程代码互操作的核心桥梁。
