import random
import time
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="实时面板", page_icon="📡", layout="wide")
st.title("实时刷新面板")

if "prices" not in st.session_state:
    st.session_state.prices = {"AAPL": 195.0, "NVDA": 720.0, "TSLA": 200.0}

with st.sidebar:
    auto = st.toggle("自动刷新", value=True)
    interval = st.slider("刷新间隔（秒）", 2, 10, 3)

rows = []
for symbol, price in st.session_state.prices.items():
    next_price = max(1.0, price * (1 + random.gauss(0, 0.004)))
    st.session_state.prices[symbol] = next_price
    rows.append({"symbol": symbol, "price": round(next_price, 2)})

df = pd.DataFrame(rows)

cols = st.columns(len(df))
for i, row in df.iterrows():
    cols[i].metric(row["symbol"], f"{row['price']:.2f}")

st.dataframe(df, width="stretch", hide_index=True)
st.caption(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if auto:
    time.sleep(interval)
    st.rerun()
