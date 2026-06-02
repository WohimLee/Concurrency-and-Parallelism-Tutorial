from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict

app = FastAPI()

# 用于模拟数据库
fake_db: Dict[int, dict] = {}

# Pydantic 模型用于请求体验证
class Item(BaseModel):
    name: str
    price: float
    description: str = ""

# GET 方法：获取所有 item
@app.get("/items")
def get_items():
    return fake_db

# GET 方法：获取指定 item
@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return fake_db[item_id]

# POST 方法：创建新 item
@app.post("/items")
def create_item(item: Item):
    item_id = len(fake_db) + 1
    fake_db[item_id] = item.dict()
    return {"item_id": item_id, "message": "Item created"}

# PUT 方法：整体更新 item
@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="Item not found")
    fake_db[item_id] = item.dict()
    return {"message": "Item updated"}

# PATCH 方法：局部更新 item
@app.patch("/items/{item_id}")
def patch_item(item_id: int, item: Item):
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="Item not found")
    # 只更新非空字段
    for key, value in item.dict(exclude_unset=True).items():
        fake_db[item_id][key] = value
    return {"message": "Item patched"}

# DELETE 方法：删除 item
@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del fake_db[item_id]
    return {"message": "Item deleted"}
