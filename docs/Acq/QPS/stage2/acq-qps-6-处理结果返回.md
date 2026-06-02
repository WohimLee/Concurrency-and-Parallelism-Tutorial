处理完的结果要怎么给到原来的请求？

当你在 **“场景 1：接收请求，立马返回一个消息，后台继续处理”** 中使用异步任务处理请求时，通常后台任务的处理结果需要反馈给原来的请求者。因为你在异步处理时已经立刻返回了响应，原本的请求和后台任务是分离的，问题在于如何将处理完的结果推送回请求者。

有几种常见的方式来将结果返回给原来的请求者：

### 1. **通过异步轮询（Polling）返回结果**

这种方法是最简单的方式。后台任务完成后，用户可以通过定时轮询的方式来获取任务的最终结果。这通常用于简单的系统中，用户可以定期查询任务的状态或结果。

#### 实现步骤：

1. **接收请求时**：返回一个任务ID给用户。
2. **后台处理**：后台任务完成后，任务ID对应的结果会被存储。
3. **查询任务结果**：用户通过提供任务ID查询任务是否完成，如果完成则返回结果。

#### FastAPI 实现示例：

```python
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uuid
import time

app = FastAPI()

# 存储任务结果的字典（模拟数据库）
task_results = {}

# 模拟的后台任务
def simulate_task(task_id: str):
    time.sleep(5)  # 假设任务处理时间
    task_results[task_id] = {"status": "completed", "result": f"Task {task_id} is processed."}

@app.post("/process/")
async def process_request(background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())  # 生成一个唯一的任务ID
    background_tasks.add_task(simulate_task, task_id)  # 后台任务处理
    return {"message": "Request is being processed", "task_id": task_id}

@app.get("/result/{task_id}")
async def get_result(task_id: str):
    # 检查任务是否已完成
    if task_id in task_results:
        return task_results[task_id]
    else:
        return {"message": "Task is still being processed"}
```

#### 关键点：

* 当用户发起请求时，返回一个 `task_id`，并立即响应。
* 后台任务完成后，将结果存储在 `task_results` 中，用户可以使用 `task_id` 来查询任务结果。
* 用户通过访问 `/result/{task_id}` 来查询任务是否完成以及结果。

#### 优缺点：

* **优点**：简单易实现，不需要复杂的推送机制。
* **缺点**：轮询方式可能会增加不必要的负担，尤其在高并发场景下，客户端需要定期检查状态。

---

### 2. **通过WebSocket推送结果**

WebSocket允许服务端与客户端保持长连接，从而在任务完成时主动推送结果给客户端。这种方法非常适合实时更新任务结果，且不需要客户端频繁轮询。

#### 实现步骤：

1. 客户端和服务器建立一个WebSocket连接。
2. 客户端发起请求时，返回任务ID并建立WebSocket连接。
3. 后台任务完成时，服务器通过WebSocket连接推送结果给客户端。

#### FastAPI + WebSocket 示例：

```python
from fastapi import FastAPI, WebSocket, BackgroundTasks
import uuid
import time

app = FastAPI()

# 存储任务结果的字典（模拟数据库）
task_results = {}

# 模拟的后台任务
def simulate_task(task_id: str):
    time.sleep(5)  # 假设任务处理时间
    task_results[task_id] = {"status": "completed", "result": f"Task {task_id} is processed."}

@app.post("/process/")
async def process_request(background_tasks: BackgroundTasks, websocket: WebSocket):
    task_id = str(uuid.uuid4())  # 生成一个唯一的任务ID
    background_tasks.add_task(simulate_task, task_id)  # 后台任务处理
    # 建立WebSocket连接
    await websocket.accept()
    await websocket.send_json({"message": "Request is being processed", "task_id": task_id})

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    # 建立WebSocket连接
    await websocket.accept()
    while task_id not in task_results:
        await asyncio.sleep(1)  # 等待任务完成
    # 任务完成，推送结果
    await websocket.send_json(task_results[task_id])
    await websocket.close()
```

#### 关键点：

* 用户通过 `/process/` 发起请求，FastAPI会返回一个 `task_id`，并且建立一个 WebSocket 连接。
* 用户通过 `/ws/{task_id}` 连接到服务器，并保持长连接。
* 后台任务完成后，FastAPI通过WebSocket推送任务的结果给客户端。

#### 优缺点：

* **优点**：WebSocket提供了实时性，服务器可以主动推送结果，避免了轮询带来的延迟和资源消耗。
* **缺点**：需要客户端支持WebSocket，并且处理并发连接的复杂性较高。

---

### 3. **通过邮件、短信等方式通知结果**

如果你不希望客户端实时查询或依赖WebSocket，也可以选择在后台任务完成时，通过邮件、短信等方式通知用户。这种方法适用于不需要立即获取结果的场景。

#### 处理步骤：

1. 客户端发起请求时返回一个任务ID。
2. 后台任务完成后，通过邮件或短信等方式将任务结果发送给用户。

#### FastAPI 邮件示例：

```python
from fastapi import FastAPI, BackgroundTasks
import smtplib
from email.mime.text import MIMEText
import uuid
import time

app = FastAPI()

def send_email(task_id: str, email: str):
    # 模拟发送邮件
    msg = MIMEText(f"Task {task_id} has been completed!")
    msg['Subject'] = 'Task Completion Notification'
    msg['From'] = 'no-reply@example.com'
    msg['To'] = email
    try:
        with smtplib.SMTP('smtp.example.com') as server:
            server.login('user', 'password')
            server.sendmail(msg['From'], [email], msg.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")

def simulate_task(task_id: str, email: str):
    time.sleep(5)  # 模拟处理任务
    send_email(task_id, email)  # 任务完成后发送邮件

@app.post("/process/")
async def process_request(background_tasks: BackgroundTasks, email: str):
    task_id = str(uuid.uuid4())  # 生成唯一任务ID
    background_tasks.add_task(simulate_task, task_id, email)  # 后台任务处理
    return {"message": "Your request is being processed.", "task_id": task_id}
```

#### 关键点：

* 当后台任务完成时，系统会通过邮件通知用户任务的完成情况。
* 用户收到邮件后可以查看任务结果。

#### 优缺点：

* **优点**：适用于不需要实时返回结果的场景。
* **缺点**：存在延迟（邮件或短信的送达可能需要一段时间）。

---

### 总结

根据不同的需求，你可以选择不同的方式将处理完的结果返回给原来的请求者：

1. **轮询（Polling）**：适合简单场景，客户端定期查询任务结果。
2. **WebSocket**：适合需要实时反馈任务结果的场景，减少轮询带来的延迟。
3. **邮件/短信通知**：适合不需要实时反馈的场景，任务完成后通过邮件或短信通知用户。

选择哪种方式取决于你的具体需求，特别是对结果实时性的要求和客户端的技术支持。
