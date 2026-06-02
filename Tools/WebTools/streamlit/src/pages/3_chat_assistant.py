from __future__ import annotations

import pandas as pd
import streamlit as st

from lib.mock_data import next_market, next_sentiment

st.title("多轮聊天助手")

symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "BTC-USD"]
topics = ["AI", "半导体", "美联储", "新能源", "加密"]

market_df = pd.DataFrame(next_market(st.session_state, symbols))
senti_df = pd.DataFrame(next_sentiment(st.session_state, topics))

for m in st.session_state.chat_messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("例如：现在半导体板块和 NVDA 风险如何？")
if prompt:
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    mover = market_df.iloc[market_df["change_pct"].abs().idxmax()]
    topic = senti_df.iloc[senti_df["score"].abs().idxmax()]
    reply = (
        "基于当前看板：\n"
        f"- 波动最大标的：{mover['symbol']} ({mover['change_pct']:+.2f}%)\n"
        f"- 情绪最强主题：{topic['topic']} ({topic['score']:+.2f}, {topic['label']})\n"
        "- 建议先看价量是否同向，再决定是否分批交易。"
    )

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
