from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="可视化", page_icon="📈", layout="wide")
st.title("Plotly 交互看板")

base = Path(__file__).resolve().parent / "sample_data" / "sales.csv"
df = pd.read_csv(base)
df["date"] = pd.to_datetime(df["date"])

with st.sidebar:
    region = st.selectbox("地区", ["全部"] + sorted(df["region"].unique().tolist()))

if region != "全部":
    show = df[df["region"] == region]
else:
    show = df.copy()

show_daily = show.groupby("date", as_index=False).agg(revenue=("revenue", "sum"), orders=("orders", "sum"))

c1, c2 = st.columns(2)
with c1:
    line = px.line(show_daily, x="date", y="revenue", title="收入趋势")
    st.plotly_chart(line, width="stretch")

with c2:
    bar = px.bar(show.groupby("region", as_index=False)["revenue"].sum(), x="region", y="revenue", title="地区收入")
    st.plotly_chart(bar, width="stretch")

scatter = px.scatter(show, x="orders", y="revenue", color="region", title="订单与收入关系")
st.plotly_chart(scatter, width="stretch")
