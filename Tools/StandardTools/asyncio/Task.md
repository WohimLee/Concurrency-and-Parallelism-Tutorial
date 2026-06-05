## asyncio.Task
`asyncio.Task` 是 asyncio 最核心的对象之一。

很多人知道：

```python
await foo()
```

或者：

```python
asyncio.create_task(foo())
```

但如果你问：

> **Task 到底是什么？为什么有了 coroutine 还需要 Task？**

很多人就说不清了。

实际上：

```text
Coroutine（协程）
      ↓
Task（调度单位）
      ↓
Event Loop（执行）
```

Task 是连接协程和事件循环的桥梁。

---

### 1 先理解 Coroutine

定义：

```python
async def foo():
    return 123
```

调用：

```python
coro = foo()
```

此时：

```python
print(type(coro))
```

输出：

```text
<class 'coroutine'>
```

注意：

```python
coro = foo()
```

并没有执行。

只是创建了一个协程对象。

---

可以理解为：

```text
函数
 ↓

协程对象(coroutine)

 ↓（等待调度）

运行
```

协程对象本身不会主动运行。

---

### 2 Task 为什么出现

假设：

```python
coro = foo()
```

Event Loop 怎么知道：

* 什么时候执行它？
* 执行到哪里了？
* await 时怎么暂停？
* 什么时候恢复？

于是 asyncio 引入：

```text
Task
```

包装 coroutine。

---

关系：

```text
Coroutine
    ↓ 包装
Task
    ↓ 调度
EventLoop
```

---

### 3 创建 Task

最常见：

```python
task = asyncio.create_task(foo())
```

或者：

```python
loop.create_task(foo())
```

返回：

```python
print(type(task))
```

输出：

```text
<class '_asyncio.Task'>
```

---

此时：

```text
foo()
 ↓
Coroutine

 ↓

Task

 ↓

Ready Queue
```

已经加入事件循环等待执行。

---

### 4 为什么 create_task 后自动运行

例如：

```python
async def worker():
    print("start")
    await asyncio.sleep(1)
    print("end")
```

```python
task = asyncio.create_task(worker())
```

创建后：

```text
Task立即加入EventLoop调度队列
```

不需要：

```python
task.start()
```

这种操作。

---

### 5 Task 是 Future 的子类

这是理解源码最关键的一点。

继承关系：

```text
Future
   ↑
 Task
```

即：

```python
isinstance(task, asyncio.Future)
```

返回：

```python
True
```

---

源码关系大致：

```python
class Task(Future):
    ...
```

---

所以：

Task 拥有 Future 的能力：

```python
task.done()

task.cancel()

task.result()

task.exception()
```

全部可以用。

---

### 6 Task 的状态

一个 Task 生命周期：

```text
PENDING
   ↓

RUNNING
   ↓

FINISHED
```

或者：

```text
PENDING
   ↓

RUNNING
   ↓

CANCELLED
```

---

例如：

```python
task.done()
```

判断是否结束。

---

### 7 await Task

例如：

```python
task = asyncio.create_task(foo())

result = await task
```

等价于：

```python
result = await foo()
```

但区别在于：

```python
foo()
```

执行权交给当前协程。

---

而：

```python
create_task(foo())
```

会立即开始调度。

---

### 8 create_task 与 await 的区别

看一个例子。

---

#### 8.1 直接 await

```python
async def main():
    await worker1()
    await worker2()
```

执行：

```text
worker1
    ↓
完成
    ↓
worker2
```

串行。

---

#### 8.2 create_task

```python
async def main():
    t1 = asyncio.create_task(worker1())
    t2 = asyncio.create_task(worker2())

    await t1
    await t2
```

执行：

```text
worker1
      ↘
        并发运行
      ↗
worker2
```

---

### 9 Task 内部保存什么

可以粗略理解为：

```python
class Task:

    _coro
        # coroutine对象

    _state
        # 当前状态

    _result
        # 返回值

    _exception
        # 异常

    _loop
        # 所属EventLoop

    _callbacks
        # 完成回调
```

---

### 10 Event Loop 如何执行 Task

例如：

```python
task = asyncio.create_task(worker())
```

内部：

```text
Task
 ↓
加入 ready queue
```

---

Event Loop：

```python
_run_once()
```

执行：

```python
task._step()
```

---

Task：

```python
coro.send(None)
```

推进协程。

---

假设：

```python
await asyncio.sleep(1)
```

出现。

则：

```text
Task暂停
 ↓
等待Future
 ↓
注册回调
```

---

Future 完成后：

```text
Task恢复
 ↓
继续send()
```

---

直到：

```python
return value
```

结束。

---

### 11 Task 的本质

可以把 Task 理解成：

```text
Coroutine Runtime
```

它负责：

* 保存执行状态
* 保存返回值
* 保存异常
* 负责暂停恢复

---

而 coroutine 本身只是：

```text
生成器升级版
```

---

### 12 获取返回值

例如：

```python
async def foo():
    return 123
```

```python
task = asyncio.create_task(foo())

result = await task
```

结果：

```text
123
```

---

或者：

```python
await task

print(task.result())
```

输出：

```text
123
```

---

### 13 获取异常

```python
async def foo():
    raise ValueError("bad")
```

```python
task = asyncio.create_task(foo())
```

```python
try:
    await task
except Exception as e:
    print(e)
```

输出：

```text
bad
```

---

也可以：

```python
task.exception()
```

---

### 14 取消 Task

```python
task.cancel()
```

例如：

```python
task = asyncio.create_task(worker())

task.cancel()
```

---

Task 内部会向协程注入：

```python
CancelledError
```

相当于：

```python
raise CancelledError
```

---

协程：

```python
async def worker():
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("cancelled")
        raise
```

---

### 15 add_done_callback

Task 完成后触发：

```python
task.add_done_callback(callback)
```

例如：

```python
def done(t):
    print(t.result())

task.add_done_callback(done)
```

---

Task 完成：

```text
123
```

自动输出。

---

### 16 当前所有 Task

查看：

```python
asyncio.all_tasks()
```

例如：

```python
tasks = asyncio.all_tasks()
```

返回：

```text
{Task1, Task2, Task3}
```

---

当前 Task：

```python
asyncio.current_task()
```

例如：

```python
task = asyncio.current_task()
```

获得：

```text
正在运行自己的Task对象
```

---

### 17 TaskGroup（3.11+）

现代 asyncio 更推荐：

```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(worker1())
    tg.create_task(worker2())
```

底层仍然创建 Task。

只是：

```text
TaskGroup
    ↓
统一管理多个Task
```

避免任务泄漏。

---

### 18 Task 在 asyncio 架构中的位置

整体结构：

```text
async def
     ↓
Coroutine
     ↓
Task
     ↓
Future
     ↓
EventLoop
```

更准确一点：

```text
Coroutine
     ↓
Task(Future)
     ↓
BaseEventLoop
     ↓
OS IO
```

---

### 19 源码层面一句话

Task 的核心工作其实就一件事：

```python
while not done:
    coro.send(...)
```

或者：

```python
coro.throw(...)
```

不断推进协程执行。

---

### 20 一句话总结

`asyncio.Task` 可以理解为：

> **一个被 Event Loop 调度执行的协程实例。**

它本质上：

* 包装 coroutine
* 继承 Future
* 保存执行状态
* 管理暂停/恢复
* 保存结果和异常
* 被 Event Loop 调度运行

最重要的关系记住：

```text
Coroutine 是代码

Task 是运行中的协程

Event Loop 是调度器
```

所以：

```python
asyncio.create_task(coro())
```

本质上就是：

> **把一个协程对象包装成 Task，并交给 Event Loop 开始调度执行。**
