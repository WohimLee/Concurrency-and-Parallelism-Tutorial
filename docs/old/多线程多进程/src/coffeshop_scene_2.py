from concurrent.futures import ThreadPoolExecutor
import time

def make_coffee(order):
    print(f"开始做 {order}")
    time.sleep(2)
    print(f"{order} 完成")

orders = ["拿铁", "美式", "卡布奇诺", "摩卡", "抹茶拿铁"]
with ThreadPoolExecutor(max_workers=3) as tp:
    tp.map(make_coffee, orders)
