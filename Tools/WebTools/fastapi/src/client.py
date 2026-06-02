import requests

data = {
    "name": "Orange",
    "price": 2.99
}

print("正在发送请求到服务器，请稍候...")

try:
    response = requests.post("http://localhost:8000/items", json=data, timeout=5)
    print("服务器响应：", response.json())
except requests.exceptions.Timeout:
    print("请求超时！服务器可能没有响应。")
except requests.exceptions.ConnectionError:
    print("连接失败！可能是服务器地址或端口错误，或者未开启服务。")
except Exception as e:
    print(f"发生其他错误：{e}")


pass