## BaseEventLoop

`BaseEventLoop` 是 asyncio 的**事件循环基类**，几乎所有 asyncio 的能力最终都建立在它之上。

平时你写：

```python
asyncio.run(main())
```

或者：

```python
loop = asyncio.get_running_loop()
```

拿到的其实就是某个 `BaseEventLoop` 的具体实现对象。

例如：

* Linux/macOS：

  * `SelectorEventLoop`
* Windows：

  * `ProactorEventLoop`

它们都继承自 `BaseEventLoop`。

可以理解成：

```text
BaseEventLoop
├── SelectorEventLoop
└── ProactorEventLoop
```

---

### 1 Event Loop 到底是什么

先看：

```python
async def foo():
    await asyncio.sleep(1)

asyncio.run(foo())
```

很多人知道它能运行，却不知道是谁在调度。

实际上是：

```text
EventLoop
    ↓
创建 Task
    ↓
运行协程
    ↓
等待 IO
    ↓
恢复协程
    ↓
直到结束
```

而这一整套机制的核心实现就在 `BaseEventLoop`。

---

### 2 BaseEventLoop 的职责

它主要负责：

```text
1. 调度回调
2. 调度协程(Task)
3. 管理Future
4. 管理定时器
5. 监听IO事件
6. 管理线程交互
7. 管理Executor
```

可以把它想成：

```text
             BaseEventLoop

      ┌──────────┬──────────┐
      ↓          ↓          ↓

   Task      Timer      Socket

      ↓          ↓          ↓

        Event Loop Scheduler
```

---

### 3 获取当前 Loop

现代写法：

```python
loop = asyncio.get_running_loop()
```

例如：

```python
async def main():
    loop = asyncio.get_running_loop()
    print(loop)

asyncio.run(main())
```

输出类似：

```text
<_UnixSelectorEventLoop running=True>
```

这个对象就是 `BaseEventLoop` 子类实例。

---
### 4 EventLoop 常用 Method
#### 4.1 run_forever()

事件循环最原始的启动方式。

```python
loop.run_forever()
```

例如：

```python
import asyncio

loop = asyncio.new_event_loop()

loop.run_forever()
```

此时：

```text
while True:
    poll_io()
    run_callbacks()
```

无限运行。

---

#### 4.2 stop()

停止循环：

```python
loop.stop()
```

例如：

```python
loop.call_later(5, loop.stop)

loop.run_forever()
```

5秒后退出。

---

#### 4.3 run_until_complete()

运行到某个 Future 完成。

```python
loop.run_until_complete(coro)
```

例如：

```python
import asyncio

async def foo():
    await asyncio.sleep(1)
    return 123

loop = asyncio.new_event_loop()

result = loop.run_until_complete(foo())

print(result)
```

输出：

```text
123
```

实际上：

```python
asyncio.run(foo())
```

底层也是类似逻辑。

---

#### 4.4 call_soon()

注册一个回调：

```python
loop.call_soon(callback)
```

例如：

```python
def hello():
    print("hello")

loop.call_soon(hello)
```

下一轮 Event Loop 就会执行。

类似：

```javascript
setImmediate(...)
```

或者：

```text
microtask queue
```

的概念。

---

#### 4.5  call_later()

延迟执行：

```python
loop.call_later(
    5,
    callback
)
```

5秒后执行。

例如：

```python
loop.call_later(
    2,
    print,
    "hello"
)
```

输出：

```text
hello
```

（2秒后）

---

#### 4.6 call_at()

指定时间点执行：

```python
when = loop.time() + 5

loop.call_at(
    when,
    callback
)
```

---

#### 4.7 create_task()

最常用的方法之一。

```python
task = loop.create_task(coro())
```

例如：

```python
async def worker():
    await asyncio.sleep(1)

task = loop.create_task(worker())
```

作用：

```text
Coroutine
     ↓
Task包装
     ↓
加入调度队列
```

---

#### 4.8 create_future()

创建 Future：

```python
future = loop.create_future()
```

例如：

```python
future = loop.create_future()

future.set_result(123)

await future
```

返回：

```text
123
```

Task 本质上也是 Future 的子类。

---

#### 4.9 run_in_executor()

这是 `asyncio.to_thread()` 的前身。

```python
await loop.run_in_executor(
    None,
    blocking_func
)
```

例如：

```python
import time

def work():
    time.sleep(5)

await loop.run_in_executor(
    None,
    work
)
```

不会阻塞 Event Loop。

Python 3.9 以后通常直接：

```python
await asyncio.to_thread(work)
```

---

#### 4.10 add_reader()

Unix 下非常重要。

监听 fd 可读：

```python
loop.add_reader(
    fd,
    callback
)
```

例如：

```python
loop.add_reader(
    sock.fileno(),
    on_data
)
```

底层：

```text
epoll
kqueue
select
```

有数据时自动触发。

---

#### 4.11 add_writer()

监听 fd 可写：

```python
loop.add_writer(
    fd,
    callback
)
```

网络框架底层大量使用。

---

### 5 Event Loop 内部结构

可以简化成：

```text
BaseEventLoop

_ready
    立即执行队列

_scheduled
    定时任务堆

_selector
    epoll/select

_tasks
    Task集合

_default_executor
    线程池
```

每次循环：

```text
while not stopped:

    1. 检查定时器

    2. poll IO

    3. 将就绪事件加入 ready

    4. 执行 ready 队列

    5. 重复
```

---

### 6 _run_once()

这是整个 asyncio 最核心的方法。

源码结构大致：

```python
def _run_once():

    timeout = ...

    events = selector.select(timeout)

    process_events(events)

    run_ready_callbacks()
```

几乎所有调度最终都会走这里。

事件循环实际上一直在：

```text
_run_once()
_run_once()
_run_once()
_run_once()
...
```

无限执行。

---

### 7 一个 Task 是怎么运行的

例如：

```python
async def worker():
    await asyncio.sleep(1)
    print("done")
```

创建：

```python
task = loop.create_task(worker())
```

过程：

```text
Coroutine
     ↓
Task
     ↓
_ready队列
     ↓
执行一步

await sleep
     ↓

注册Timer

1秒后
     ↓

_ready队列
     ↓

继续执行

done
```

整个过程由 BaseEventLoop 调度。

---

### 8 为什么官方不建议直接操作 BaseEventLoop

现代 asyncio 推荐：

```python
asyncio.run()
asyncio.create_task()
asyncio.to_thread()
asyncio.timeout()
```

而不是：

```python
loop = asyncio.get_running_loop()

loop.create_task(...)
loop.run_until_complete(...)
```

原因：

1. API 更稳定
2. 不依赖具体 Loop 实现
3. 兼容 uvloop
4. 避免管理生命周期

因此业务代码里：

```python
asyncio.create_task(...)
```

比：

```python
loop.create_task(...)
```

更推荐。

---

### 9 BaseEventLoop 在 asyncio 中的位置

```text
async def
    ↓

Coroutine
    ↓

Task
    ↓

Future
    ↓

BaseEventLoop
    ↓

Selector/Proactor
    ↓

epoll/kqueue/IOCP
    ↓

OS
```

可以把它理解成：

> **BaseEventLoop 是 asyncio 的调度核心（scheduler），负责驱动 Task、Future、定时器和 I/O 事件运行。**

如果你以后阅读 asyncio 源码，最值得重点看的三个文件是：

* `asyncio/base_events.py`（BaseEventLoop）
* `asyncio/tasks.py`（Task）
* `asyncio/futures.py`（Future）

其中 `BaseEventLoop._run_once()` 是整个 asyncio 调度机制最核心的一段代码。
