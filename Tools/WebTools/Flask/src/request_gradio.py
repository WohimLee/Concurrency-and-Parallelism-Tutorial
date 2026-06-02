
import time
import requests
import gradio as gr

def answer(prompt):

    query_data = {
        "prompt": prompt,
        "other": "其它信息"
    }
    response = requests.post(
        "http://127.0.0.1:18888/milvus",
        json=query_data,
        headers={"Content-Type":"application/json"}
    )

    if response.status_code == 200:
        response = response.json()
        result = response["result"]

    accumulated_result = ""  # 存储累积的输出
    for char in result:  # 逐字符输出
        accumulated_result += char  # 追加字符
        yield accumulated_result  # 发送累积的结果
        time.sleep(0.2)  # 模拟流式生成的延迟

if __name__ == "__main__":
    iface = gr.Interface(
        fn=answer,
        inputs=gr.Textbox(),
        outputs=gr.Markdown()
    )
    iface.launch()