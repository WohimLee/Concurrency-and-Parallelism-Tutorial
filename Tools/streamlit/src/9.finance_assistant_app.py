from __future__ import annotations

import streamlit as st


st.set_page_config(page_title="Finance Assistant Course App", page_icon="📊", layout="wide")

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": "欢迎来到课程综合项目。请在左侧页面切换：行情、舆论、聊天。",
        }
    ]

st.title("Streamlit 综合项目：金融助手")
st.markdown(
    """
本应用用于教学，展示：
- 多页面结构
- 行情与舆论看板
- 多轮对话状态管理

请从左侧导航进入各页面。
"""
)

st.info("运行入口：streamlit run src/09_finance_assistant_app.py")
