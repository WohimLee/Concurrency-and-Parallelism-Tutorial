from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="数据处理", page_icon="🧹", layout="wide")
st.title("数据加载与清洗")

base = Path(__file__).resolve().parent / "sample_data" / "sales.csv"
df = pd.read_csv(base)

default_regions = sorted(df["region"].unique().tolist())

with st.sidebar:
    regions = st.multiselect("地区", default_regions, default=default_regions)
    min_revenue = st.slider("最小收入", 50, 500, 100)

cleaned = (
    df.dropna(subset=["date", "region", "revenue", "orders"])
    .query("region in @regions and revenue >= @min_revenue")
    .sort_values("date")
)

st.subheader("原始数据")
st.dataframe(df, width="stretch", hide_index=True)

st.subheader("清洗后数据")
st.dataframe(cleaned, width="stretch", hide_index=True)

st.caption(f"清洗后记录数：{len(cleaned)}")
