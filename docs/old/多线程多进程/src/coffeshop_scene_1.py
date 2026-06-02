import time

def make_coffee(order):
    print(f"开始做 {order}")
    time.sleep(2)  # 模拟烧水/冲咖啡（阻塞IO）
    print(f"{order} 完成")

def main():
    orders = ["拿铁", "美式", "卡布奇诺"]
    for o in orders:
        make_coffee(o)

main()
