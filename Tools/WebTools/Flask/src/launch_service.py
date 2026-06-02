
from flask import Flask, request  # 需要 import request 处理 POST 方法

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Flask!"

@app.route("/milvus", methods=["POST"])
def search_recipe():
    # 从请求中获取 JSON 数据, 收到的 request 内容
    data = request.json

    # 从 JSON 数据中提取 "query" 字段的值，如果不存在则默认为空字符串
    query_text = data.get("prompt", "") 
    other = data.get("other", "")
    # 检查 query_text 是否为空
    if not query_text:
        return {"message": "Query text is required"}

    result = f"process results for {query_text}"
    return {"result": result}


if __name__ == '__main__':
    app.run(host="127.0.0.1", port=18888, debug=False) # True 启用 debug 模式，方便开发调试

