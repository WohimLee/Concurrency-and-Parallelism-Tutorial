from concurrent.futures import ProcessPoolExecutor
import math

def grind_beans(amount):
    # 计算质数模拟CPU重活
    count = 0
    for i in range(2, amount):
        if all(i % j for j in range(2, int(i**0.5)+1)):
            count += 1
    return count

with ProcessPoolExecutor() as pp:
    results = pp.map(grind_beans, [20000, 21000, 22000, 23000])
print(list(results))
