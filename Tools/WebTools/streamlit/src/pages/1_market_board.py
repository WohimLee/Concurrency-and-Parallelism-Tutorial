from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from lib.mock_data import next_market

st.title("行情看板")

watch = st.text_input("标的列表（逗号分隔）", value="AAPL,MSFT,NVDA,TSLA,BTC-USD")
symbols = [s.strip().upper() for s in watch.split(",") if s.strip()]

market = next_market(st.session_state, symbols)
df = pd.DataFrame(market)

cols = st.columns(min(4, len(df)))
for i, row in df.head(4).iterrows():
    cols[i].metric(row["symbol"], f"{row['price']:.2f}", f"{row['change_pct']:+.2f}%")

hist_rows = []
for symbol, row in st.session_state.market_store.items():
    for p in row["history"][-40:]:
        hist_rows.append({"symbol": symbol, "time": p["time"], "price": p["price"]})

hist = pd.DataFrame(hist_rows)
if not hist.empty:
    fig = px.line(hist, x="time", y="price", color="symbol", title="价格轨迹")
    st.plotly_chart(fig, width="stretch")

st.dataframe(df.sort_values("change_pct", ascending=False), width="stretch", hide_index=True)
