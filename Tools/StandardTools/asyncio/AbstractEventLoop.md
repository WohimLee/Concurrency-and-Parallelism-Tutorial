## AbstractEventLoop

理解 asyncio 的事件循环层次，最好按下面的顺序：

```text
AbstractEventLoop
        ↑
  BaseEventLoop
        ↑
 ┌──────┴──────┐
 ↓             ↓
SelectorEventLoop
ProactorEventLoop
```

很多人一上来就看 `BaseEventLoop`，但其实它只是 **`AbstractEventLoop` 的一个实现**。

---

# 1. AbstractEventLoop 是什么

它定义了：

> **一个事件循环应该具备哪些能力（接口规范）**

类似于：

```python
from abc import ABC

class AbstractEventLoop(ABC):

    def create_task(...):
        ...

    def call_soon(...):
        ...

    def run_forever(...):
        ...

    def stop(...):
        ...
```

注意：

```text
AbstractEventLoop
    ≠ 实现

AbstractEventLoop
    = 接口规范
```

类似：

```text
Java Interface
C++ Pure Virtual Class
Go Interface
```

的概念。

---

## 为什么需要它？

假设 asyncio 没有抽象层：

```text
业务代码
    ↓
SelectorEventLoop
```

那未来换实现就麻烦了。

有了抽象层：

```text
业务代码
    ↓
AbstractEventLoop
    ↓
具体实现
```

业务代码只依赖接口。

---

## AbstractEventLoop 规定了什么？

例如：

### 生命周期

```python
run_forever()
run_until_complete()
stop()
close()
is_running()
is_closed()
```

---

### 调度

```python
call_soon()
call_later()
call_at()
```

---

### Task/Future

```python
create_task()
create_future()
```

---

### Executor

```python
run_in_executor()
set_default_executor()
```

---

### 网络

```python
create_connection()
create_server()
```

---

### 子进程

```python
subprocess_exec()
subprocess_shell()
```

---

### 文件描述符

```python
add_reader()
remove_reader()

add_writer()
remove_writer()
```

---

因此可以理解为：

```text
AbstractEventLoop
=
asyncio事件循环能力说明书
```

---

# 2. BaseEventLoop 是什么

如果说：

```text
AbstractEventLoop
=
接口
```

那么：

```text
BaseEventLoop
=
通用实现
```

它实现了大量与平台无关的逻辑。

---

例如：

### Task 调度

```python
create_task()
```

实现已经在 BaseEventLoop 里。

---

### Timer

```python
call_later()
call_at()
```

实现也在 BaseEventLoop。

---

### Ready Queue

```python
_ready
```

管理立即执行任务。

---

### Scheduled Queue

```python
_scheduled
```

管理定时任务。

---

### Future

```python
create_future()
```

实现也在这里。

---

### Executor

```python
run_in_executor()
```

也是 BaseEventLoop 提供。

---

因此：

```text
BaseEventLoop
=
80%通用逻辑
```

---

# BaseEventLoop 不负责什么？

最重要的一点：

## 不负责具体 I/O 多路复用

因为不同平台不同。

Linux:

```text
epoll
```

BSD/macOS:

```text
kqueue
```

Windows:

```text
IOCP
```

---

所以：

```python
BaseEventLoop
```

把这部分留给子类实现。

---

# SelectorEventLoop

Unix 默认实现：

```python
asyncio.SelectorEventLoop
```

结构：

```text
SelectorEventLoop
       ↑
 BaseEventLoop
```

内部：

```python
self._selector
```

可能是：

```text
epoll
kqueue
poll
select
```

---

例如：

```python
loop.add_reader(fd, callback)
```

最终：

```python
selector.register(...)
```

---

# ProactorEventLoop

Windows 专用：

```python
asyncio.ProactorEventLoop
```

结构：

```text
ProactorEventLoop
        ↑
   BaseEventLoop
```

底层：

```text
IOCP
```

即：

```text
I/O Completion Port
```

---

# 真实运行时关系

例如：

```python
import asyncio

async def main():
    loop = asyncio.get_running_loop()
    print(type(loop))

asyncio.run(main())
```

Linux 输出可能：

```python
<class 'asyncio.unix_events._UnixSelectorEventLoop'>
```

继承链：

```text
_UnixSelectorEventLoop
          ↑
   SelectorEventLoop
          ↑
     BaseEventLoop
          ↑
  AbstractEventLoop
```

---

# 一个 create_task 的调用链

例如：

```python
loop.create_task(coro)
```

在哪实现？

不是：

```text
SelectorEventLoop
```

而是：

```text
BaseEventLoop.create_task()
```

因为所有平台都一样。

---

源码思想类似：

```python
class BaseEventLoop:

    def create_task(self, coro):
        return Task(coro, loop=self)
```

---

# 一个 add_reader 的调用链

例如：

```python
loop.add_reader(fd, callback)
```

这就和平台有关。

BaseEventLoop 不知道：

```text
epoll?
kqueue?
IOCP?
```

因此：

```python
class AbstractEventLoop:

    @abstractmethod
    def add_reader(...):
        ...
```

具体由：

```python
SelectorEventLoop
```

实现。

---

# _run_once 的位置

asyncio 最核心循环：

```python
while True:
    _run_once()
```

就在：

```python
BaseEventLoop
```

里。

大致：

```python
def _run_once():

    timeout = ...

    events = self._selector.select(timeout)

    self._process_events(events)

    self._run_ready()
```

这里可以看到：

* 调度逻辑在 BaseEventLoop
* I/O 获取依赖 selector

---

# 一个形象比喻

把事件循环看成汽车：

## AbstractEventLoop

```text
汽车设计图
```

规定：

* 必须有方向盘
* 必须有刹车
* 必须有发动机

但不提供实现。

---

## BaseEventLoop

```text
汽车底盘
```

实现：

* 转向系统
* 仪表盘
* 传动系统

大部分逻辑都在这里。

---

## SelectorEventLoop

```text
汽油发动机版本
```

---

## ProactorEventLoop

```text
电动发动机版本
```

---

# 为什么平时几乎看不到 AbstractEventLoop？

因为业务代码通常：

```python
loop = asyncio.get_running_loop()
```

拿到的是：

```python
SelectorEventLoop
```

或者：

```python
ProactorEventLoop
```

实例。

但类型注解经常写：

```python
from asyncio import AbstractEventLoop

def foo(loop: AbstractEventLoop):
    ...
```

因为：

```text
依赖抽象
而不是依赖实现
```

---

# 总结

## AbstractEventLoop

定义：

```text
事件循环应该具备哪些能力
```

属于接口/抽象基类。

主要作用：

* 定义 API
* 统一规范
* 解耦实现

---

## BaseEventLoop

实现：

```text
事件循环的大部分通用逻辑
```

包括：

* create_task
* create_future
* call_soon
* call_later
* run_forever
* run_until_complete
* run_in_executor
* _run_once

---

## SelectorEventLoop / ProactorEventLoop

负责：

```text
平台相关的 I/O 实现
```

例如：

* epoll
* kqueue
* IOCP

---

一句话概括：

```text
AbstractEventLoop 负责定义“事件循环是什么”。

BaseEventLoop 负责实现“事件循环怎么调度”。

SelectorEventLoop / ProactorEventLoop 负责实现“事件循环如何与操作系统的 I/O 交互”。
```
