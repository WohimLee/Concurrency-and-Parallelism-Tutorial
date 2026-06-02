from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import mammoth

app = FastAPI()

def docx_to_html(docx_path: str) -> str:
    with open(docx_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        return result.value  # 返回 HTML 内容

@app.get("/", response_class=HTMLResponse)
def read_docx_tables():
    html_content = docx_to_html("/Users/azen/Desktop/llm/RAG-Tutorial/data/附件1：2024年度东莞市“倍增计划”骨干人员子女入读民办中小学校资助项目申报指南.docx")
    full_page = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Word 表格展示</title>
        <style>
            table {{ border-collapse: collapse; margin-bottom: 20px; }}
            td, th {{ border: 1px solid #333; padding: 8px; text-align: center; }}
        </style>
    </head>
    <body>
        <h2>提取的 Word 表格如下：</h2>
        {html_content}
    </body>
    </html>
    """
    print(html_content)
    return full_page
