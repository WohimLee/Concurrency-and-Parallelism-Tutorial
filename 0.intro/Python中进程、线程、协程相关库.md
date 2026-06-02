在 Python 里，**进程（Process）**、**线程（Thread）**、**协程（Coroutine）**相关的库可以按「抽象层级」来划分。很多人接触的是高级封装，但真正最底层的接口其实并不多。

# 一、进程相关

## 最底层

### `os`

```python
import os

pid = os.fork()

if pid == 0:
    print("child")
else:
    print("parent")
```

主要接口：

* `os.fork()`
* `os.exec*()`
* `os.wait()`
* `os.kill()`

本质上直接对应 Linux/Unix 系统调用。

这是 Python 进程控制最接近操作系统的一层。

---

## 标准库主流

### `multiprocessing`

```python
from multiprocessing import Process

def worker():
    print("hello")

p = Process(target=worker)
p.start()
p.join()
```

功能：

* 创建进程
* IPC（Queue/Pipe）
* Shared Memory
* Lock/Semaphore

内部：

```text
multiprocessing
    ↓
fork/spawn
    ↓
os
    ↓
kernel
```

---

## 更高级

### `concurrent.futures.ProcessPoolExecutor`

```python
from concurrent.futures import ProcessPoolExecutor
```

实际上是：

```text
ProcessPoolExecutor
    ↓
multiprocessing
    ↓
os
```

属于进程池封装。

---

# 二、线程相关

## 最底层

### `_thread`

这是 CPython 的原生线程模块。

```python
import _thread

def worker():
    print("hello")

_thread.start_new_thread(worker, ())
```

对应 C 层：

```c
PyThread_start_new_thread()
```

再往下：

Linux：

```text
pthread_create
```

Windows：

```text
CreateThread
```

---

## 标准线程库

### `threading`

大家最常用的。

```python
import threading

def worker():
    print("hello")

t = threading.Thread(target=worker)
t.start()
t.join()
```

内部结构：

```text
threading
    ↓
_thread
    ↓
pthread
    ↓
kernel
```

---

## 更高级

### `concurrent.futures.ThreadPoolExecutor`

```python
from concurrent.futures import ThreadPoolExecutor
```

内部：

```text
ThreadPoolExecutor
    ↓
threading
    ↓
_thread
```

---

# 三、协程相关

这里最容易混淆。

Python 协程实际上经历了三代。

---

## 第一代：Generator

### `yield`

```python
def task():
    yield 1
```

本质：

```text
generator
```

没有事件循环。

---

## 第二代：yield from

PEP 380

```python
yield from sub_task()
```

开始具备协程特征。

---

## 第三代：async/await

PEP 492

```python
async def task():
    await asyncio.sleep(1)
```

现代 Python 协程。

---

# 协程最底层

严格来说：

### `types.coroutine`

```python
from types import coroutine
```

或者直接：

```python
generator.send()
generator.throw()
generator.close()
```

因为 Python 协程最终仍然是：

```text
Coroutine
    ↓
Generator
    ↓
Frame Object
```

CPython 中对应：

```c
PyGenObject
PyCoroObject
```

所以协程的底层其实是：

```text
generator
```

而不是 asyncio。

---

# asyncio 的位置

### `asyncio`

```python
import asyncio
```

提供：

* Event Loop
* Task
* Future
* Socket IO
* 定时器

结构：

```text
asyncio
    ↓
selectors
    ↓
epoll/kqueue/select
    ↓
kernel
```

---

## asyncio 的更底层

### `selectors`

```python
import selectors
```

直接操作：

* epoll（Linux）
* kqueue（BSD/macOS）
* select

示例：

```python
import selectors

sel = selectors.DefaultSelector()
```

这是 Python 标准库中最接近事件驱动 IO 的层。

---

# 第三方协程库

### gevent

```python
import gevent
```

结构：

```text
gevent
    ↓
greenlet
    ↓
libev/libuv
```

---

### greenlet

```python
from greenlet import greenlet
```

可以手动切换执行栈：

```python
g.switch()
```

很多人认为：

```text
greenlet
```

是 Python 用户态协程最底层的第三方实现。

---

### trio

```python
import trio
```

现代 async 框架。

---

### anyio

```python
import anyio
```

统一：

* asyncio
* trio

接口。

---

# 四、整体层级图

```text
进程：

ProcessPoolExecutor
        ↓
multiprocessing
        ↓
os
        ↓
fork/spawn
        ↓
kernel


线程：

ThreadPoolExecutor
        ↓
threading
        ↓
_thread
        ↓
pthread
        ↓
kernel


协程：

anyio/trio/gevent
        ↓
asyncio
        ↓
selectors
        ↓
epoll/kqueue/select
        ↓
kernel


协程对象本身：

async/await
        ↓
Coroutine
        ↓
Generator
        ↓
Frame Object
        ↓
CPython VM
```

如果只看**Python 标准库里最底层的接口**，可以记成：

| 并发模型 | 常用库               | 最底层库                       |
| ---- | ----------------- | -------------------------- |
| 进程   | `multiprocessing` | `os`                       |
| 线程   | `threading`       | `_thread`                  |
| 协程调度 | `asyncio`         | `selectors`                |
| 协程对象 | `async/await`     | `generator` (`yield/send`) |

其中真正离操作系统最近的是：

* 进程：`os.fork()`
* 线程：`_thread`
* IO 多路复用：`selectors` → epoll/kqueue/select

而**协程本身并不是操作系统提供的概念**，它是 Python 解释器层（Generator/Coroutine）实现的，因此其“最底层”其实是 `generator.send()` 和 CPython 的 `PyGenObject`。
