# rag_minimal.py
import os, re, math, asyncio, uvicorn
from fastapi import FastAPI, Query
from typing import List, Tuple

from openai import OpenAI

# --------- 极简向量化：哈希BOW -> 稀疏向量 ----------
DIM = 2048
def embed(text: str) -> List[float]:
    v = [0.0]*DIM
    for tok in re.findall(r"\w+", text.lower()):
        h = hash(tok) % DIM
        v[h] += 1.0
    # L2 normalize
    norm = math.sqrt(sum(x*x for x in v)) or 1.0
    return [x/norm for x in v]

def cos(a: List[float], b: List[float]) -> float:
    return sum(x*y for x, y in zip(a, b))

KB = [
    "RAG 是 Retrieval-Augmented Generation，将检索到的外部知识拼接到提示里。",
    "Agent 会基于工具使用（tool use）感知-计划-执行，常见工具含搜索、计算、数据库。",
    "使用 FastAPI 可用 async 端点并发 I/O，CPU 密集任务交给进程池。",
    "FAISS/Elastic/PGVector 都可做向量检索，重排可用 cross-encoder 或简单打分。"
]
KB_EMB = [embed(x) for x in KB]

def llm(prompt: str) -> str:
    client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key="sk-9f53ec0ec3234971af8af2c605c83c09",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    completion = client.chat.completions.create(
        model="qwen3-max",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "你是谁？"},
        ],
        stream=True
    )
    for chunk in completion:
        print(chunk.choices[0].delta.content, end="", flush=True)
    return 

app = FastAPI(title="Mini RAG")

async def topk(query: str, k=3) -> List[Tuple[float, str]]:
    q = embed(query)
    # I/O 不阻塞，这里只是计算；若非常耗时，可 to_thread
    scores = [(cos(q, e), KB[i]) for i, e in enumerate(KB_EMB)]
    return sorted(scores, key=lambda x: x[0], reverse=True)[:k]

@app.get("/ask")
async def ask(q: str = Query(..., description="你的问题")):
    # 1) 并发检索（此处只有一个检索器，形式上保留并发）
    docs = await topk(q, 3)
    context = "\n\n".join(f"[doc{i}] {d}" for i, (_, d) in enumerate(docs, 1))
    # 2) 组装提示并“生成”
    prompt = f"问题：{q}\n\n已检索到的资料：\n{context}\n\n请基于资料回答，并给出处编号。"
    answer = await asyncio.to_thread(llm, prompt)
    return {"answer": answer, "citations": [{"score": float(s), "text": d} for s, d in docs]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
