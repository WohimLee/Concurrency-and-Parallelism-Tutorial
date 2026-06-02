import asyncio

async def make_coffee(order):
    print(f"开始做 {order}")
    await asyncio.sleep(2)   # 模拟异步I/O：烧水、出咖啡
    print(f"{order} 完成")

async def main():
    orders = ["拿铁", "美式", "卡布奇诺"]
    tasks = [make_coffee(o) for o in orders]
    await asyncio.gather(*tasks)

asyncio.run(main())
