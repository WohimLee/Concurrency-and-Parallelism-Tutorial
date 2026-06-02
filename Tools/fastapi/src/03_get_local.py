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
