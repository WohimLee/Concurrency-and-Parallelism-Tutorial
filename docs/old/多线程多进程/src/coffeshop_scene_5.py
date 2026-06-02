import asyncio, time

def blocking_grind(order):
    print(f"磨豆中 {order}")
    time.sleep(2)
    return f"{order} 的豆磨好了"

async def make_coffee(order):
    print(f"准备做 {order}")
    result = await asyncio.to_thread(blocking_grind, order)  # 放后台线程执行
    print(result)
    await asyncio.sleep(1)  # 模拟异步I/O（冲咖啡）
    print(f"{order} 完成")

async def main():
    orders = ["拿铁", "美式", "卡布奇诺"]
    await asyncio.gather(*(make_coffee(o) for o in orders))

asyncio.run(main())
