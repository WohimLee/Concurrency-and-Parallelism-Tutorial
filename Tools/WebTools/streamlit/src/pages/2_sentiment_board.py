from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib.mock_data import next_sentiment

st.title("舆论看板")

t_input = st.text_input("主题列表（逗号分隔）", value="AI,半导体,美联储,新能源,加密")
topics = [s.strip() for s in t_input.split(",") if s.strip()]

sentiment = next_sentiment(st.session_state, topics)
df = pd.DataFrame(sentiment)

bar = go.Figure(
    go.Bar(
        x=df["score"],
        y=df["topic"],
        orientation="h",
        marker=dict(color=df["score"], colorscale="RdYlGn", cmin=-1, cmax=1),
    )
)
bar.update_layout(title="情绪值", xaxis_title="score", yaxis_title="topic")
st.plotly_chart(bar, width="stretch")

bubble = px.scatter(df, x="score", y="mentions", color="topic", size="mentions", title="热度 vs 情绪")
st.plotly_chart(bubble, width="stretch")

st.dataframe(df.sort_values("score", ascending=False), width="stretch", hide_index=True)
