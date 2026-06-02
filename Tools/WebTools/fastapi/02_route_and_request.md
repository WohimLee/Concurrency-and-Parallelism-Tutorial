## 🧩 模块 2：路由与请求处理
>🎯 学习目标
- 掌握 FastAPI 中的路由定义方式
- 理解路径参数、查询参数的使用方法
- 学会使用 Pydantic 进行请求体校验
- 掌握响应模型定义与数据验证

✅ 常见 HTTP 请求方法汇总

| 方法          | 含义          | 典型用途           | 是否安全 | 是否幂等    |
| ----------- | ----------- | -------------- | ---- | ------- |
| **GET**     | 获取资源        | 获取网页、数据查询      | ✅ 是  | ✅ 是     |
| **POST**    | 提交数据，创建资源   | 表单提交、用户注册、上传文件 | ❌ 否  | ❌ 否     |
| **PUT**     | 更新（整体替换）资源  | 更新用户信息、商品信息等   | ❌ 否  | ✅ 是     |
| **PATCH**   | 局部更新资源      | 修改部分字段         | ❌ 否  | ✅ 是（通常） |
| **DELETE**  | 删除资源        | 删除账户、删除文件      | ❌ 否  | ✅ 是     |
| **HEAD**    | 获取响应头，不返回正文 | 检测资源是否存在、检查缓存等 | ✅ 是  | ✅ 是     |
| **OPTIONS** | 查询服务器支持的方法  | 跨域请求预检（CORS）   | ✅ 是  | ✅ 是     |

🔍 安全性与幂等性解释
- 安全方法：不会修改服务器数据（如 GET、HEAD、OPTIONS）
- 幂等方法：执行多次结果相同（如 GET、PUT、DELETE）

| FastAPI 装饰器     | HTTP 方法 |
| --------------- | ------- |
| `@app.get()`    | GET     |
| `@app.post()`   | POST    |
| `@app.put()`    | PUT     |
| `@app.patch()`  | PATCH   |
| `@app.delete()` | DELETE  |



>🧾 请求体：Pydantic 模型入门
- 用于接收 POST / PUT 请求中的 JSON 数据
- 特点:
    - 自动校验字段类型和格式
    - 支持默认值、可选字段、嵌套结构
    - FastAPI 自动解析请求体为 Pydantic 模型
```py
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    tags: list[str] = []

@app.post("/items/")
def create_item(item: Item):
    return {"received": item}
```
>如果你想让公网也能访问，应该这样启动
```py
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

#### 1 GET 请求 —— 获取资源
- `GET` 用于获取数据，不会对服务器资源造成任何修改

>server.py
```py
from fastapi import FastAPI

app = FastAPI()


# 假设有一个固定的商品列表
items = {
    1: {"name": "Apple", "price": 1.2},
    2: {"name": "Banana", "price": 0.8},
}

@app.get("/")
def home():
    return "我的FastAPI"

# GET 请求：获取所有商品
@app.get("/items")
def read_items():
    return items

# GET 方法：获取指定 item
@app.get("/items/{item_id}")
def get_item(item_id: int):

    return items[item_id]
```

>测试方法
```py
### 方法一
uvicorn 02_1_get:app --reload
# 然后在网址栏输入: 
# http://127.0.0.1:8000
# http://127.0.0.1:8000/items
# http://127.0.0.1:8000/items/1

### 方法二
curl http://localhost:8000/items

### 方法三: 在 client.py 使用 requests
import requests

url = "http://localhost:8000/items"

response = requests.get(url=url,)
print(response.json())
```

#### 2 POST 请求 —— 创建资源
- POST 用于向服务器提交数据，通常用于创建新的资源项

>server.py
```py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
def home():
    return "我的FastAPI"

class Item(BaseModel):
    name: str
    price: float

@app.post("/items")
def create_item(item: Item):
    return {"msg": "Item received", "item": item}
```

>测试方法
```py
# 方法一
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Apple", "price": 888}'

# 方法二
import requests
data = {
    "name": "Orange",
    "price": 2.99
}
response = requests.post("http://localhost:8000/items", json=data)
print(response.json())
```









