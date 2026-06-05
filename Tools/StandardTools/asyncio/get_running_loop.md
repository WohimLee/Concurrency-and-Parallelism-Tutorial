`asyncio.get_running_loop()` 是现代 asyncio 里获取当前事件循环（Event Loop）的标准方式。

它看起来很简单：

```python
loop = asyncio.get_running_loop()
```

但实际上它体现了 asyncio 从早期设计到现代设计的一次重要演进。

---

# 它到底返回什么？

返回：

```python
BaseEventLoop
```

的某个具体实现实例，例如：

```python
<_UnixSelectorEventLoop ...>
```

或者 Windows 上：

```python
<ProactorEventLoop ...>
```

所以：

```python
loop = asyncio.get_running_loop()
```

得到的其实就是：

```text
当前正在执行这个协程的 Event Loop
```

---

# 最简单例子

```python
import asyncio

async def main():
    loop = asyncio.get_running_loop()
    print(loop)

asyncio.run(main())
```

输出类似：

```text
<_UnixSelectorEventLoop running=True closed=False>
```

---

# 为什么叫 running loop？

注意名字：

```python
get_running_loop()
```

不是：

```python
get_loop()
```

也不是：

```python
get_current_loop()
```

而是：

```text
获取当前正在运行的 Event Loop
```

这里有两个条件：

### 1. 必须在线程里

### 2. 必须有正在运行的 Event Loop

否则会报错。

---

# 在协程里使用

这是最常见场景：

```python
async def worker():
    loop = asyncio.get_running_loop()
```

完全没问题。

因为：

```text
worker()
    ↓
Task
    ↓
Event Loop 正在调度
```

所以 asyncio 知道该返回哪个 loop。

---

# 在普通函数里会怎样？

```python
import asyncio

loop = asyncio.get_running_loop()
```

直接报错：

```text
RuntimeError:
no running event loop
```

因为：

```text
当前没有 Event Loop 在运行
```

---

例如：

```python
def foo():
    asyncio.get_running_loop()
```

调用：

```python
foo()
```

也会报同样错误。

---

# 为什么这样设计？

因为 asyncio 需要避免歧义。

假设一个线程里：

```python
loop1
loop2
```

都存在。

那：

```python
get_loop()
```

到底返回谁？

不明确。

所以现代 asyncio 的原则是：

> 只有真正正在执行协程时，才能无歧义地知道所属的 Event Loop。

---

# 与 get_event_loop() 的区别

这是最容易混淆的地方。

---

## 老 API

```python
asyncio.get_event_loop()
```

---

## 新 API

```python
asyncio.get_running_loop()
```

---

### get_event_loop()

历史行为非常复杂。

例如：

```python
loop = asyncio.get_event_loop()
```

可能：

* 返回已有 loop
* 创建新 loop
* 返回线程局部 loop

行为在不同 Python 版本里还变过。

---

### get_running_loop()

规则非常简单：

```text
有运行中的 loop
    返回它

没有
    RuntimeError
```

没有任何隐式创建。

---

例如：

```python
import asyncio

try:
    asyncio.get_running_loop()
except RuntimeError as e:
    print(e)
```

输出：

```text
no running event loop
```

---

# asyncio.run 里面发生了什么？

例如：

```python
asyncio.run(main())
```

内部大致：

```python
loop = asyncio.new_event_loop()

set_running_loop(loop)

loop.run_until_complete(main())
```

因此：

```python
async def main():
    asyncio.get_running_loop()
```

能成功。

---

# 什么时候会用到它？

很多高级 API 都需要 loop。

例如：

```python
loop = asyncio.get_running_loop()

future = loop.create_future()
```

---

创建 Task：

```python
loop.create_task(...)
```

虽然现代写法通常：

```python
asyncio.create_task(...)
```

---

Executor：

```python
await loop.run_in_executor(...)
```

---

线程安全调度：

```python
loop.call_soon_threadsafe(...)
```

---

# 一个真实例子：create_future

Future 必须绑定到某个 Event Loop。

```python
async def main():
    loop = asyncio.get_running_loop()

    fut = loop.create_future()

    fut.set_result(123)

    print(await fut)

asyncio.run(main())
```

输出：

```text
123
```

---

# 一个真实例子：当前 Loop 的时间

```python
async def main():
    loop = asyncio.get_running_loop()

    print(loop.time())

asyncio.run(main())
```

输出类似：

```text
123456.789
```

这里：

```python
loop.time()
```

使用的是 loop 的单调时钟（monotonic clock）。

很多定时器都依赖它：

```python
loop.call_at(...)
```

---

# get_running_loop 的实现思路

简化后类似：

```python
_running_loop = threading.local()
```

每个线程维护：

```text
当前正在运行的 loop
```

---

当：

```python
loop.run_forever()
```

开始执行时：

```python
_running_loop.loop = loop
```

---

调用：

```python
asyncio.get_running_loop()
```

本质上就是：

```python
return _running_loop.loop
```

如果没有：

```python
raise RuntimeError
```

---

# 多线程场景

例如：

```python
import asyncio
import threading
```

主线程：

```python
asyncio.run(main())
```

有 loop。

---

新线程：

```python
def worker():
    asyncio.get_running_loop()
```

会报：

```text
RuntimeError
```

因为：

```text
那个线程没有运行 Event Loop
```

注意：

```text
Event Loop 是线程绑定的
```

不是进程级别的全局对象。

---

# 为什么库作者喜欢它？

假设你在写库：

```python
async def connect():
```

你不能假设用户的 loop 是什么。

所以：

```python
loop = asyncio.get_running_loop()
```

总能拿到：

```text
当前调度这个协程的 loop
```

这样：

* 支持默认 asyncio loop
* 支持 uvloop
* 支持自定义 loop

不会写死实现。

---

# 与 create_task 的关系

现代 asyncio：

```python
asyncio.create_task(coro())
```

内部实际上类似：

```python
loop = asyncio.get_running_loop()

return loop.create_task(coro())
```

所以：

```python
asyncio.create_task(...)
```

必须在运行中的 Event Loop 里调用。

否则：

```text
RuntimeError:
no running event loop
```

---

# 一句话总结

`asyncio.get_running_loop()` 的作用是：

> **获取当前协程正在运行的 Event Loop；如果当前线程没有正在运行的 Event Loop，则抛出 `RuntimeError`。**

记忆方式：

```text
get_running_loop()

= 我现在正在某个 Event Loop 里面运行吗？

是 → 返回这个 Loop

否 → RuntimeError
```

现代 asyncio 代码里，如果你在协程内部需要访问底层事件循环（创建 Future、访问时间、调用 Executor、线程安全调度等），优先使用：

```python
loop = asyncio.get_running_loop()
```

而不是旧的：

```python
asyncio.get_event_loop()
```
