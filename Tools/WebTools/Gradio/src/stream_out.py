import gradio as gr
import time

def answer(input_text):
    accumulated_result = ""  # 存储累积的输出
    for char in input_text:  # 逐字符输出
        accumulated_result += char  # 追加字符
        yield accumulated_result  # 发送累积的结果
        time.sleep(0.2)  # 模拟流式生成的延迟

if __name__ == "__main__":
    iface = gr.Interface(
        fn=answer,
        inputs=gr.Textbox(),
        outputs=gr.Markdown()
    )
    iface.launch(
        server_name="127.0.0.1", 
        server_port=33333, 
        share=True # 生成公共链接
    )
