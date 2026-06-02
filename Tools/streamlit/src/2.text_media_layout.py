from datetime import date

import pandas as pd
import streamlit as st

st.set_page_config(page_title="组件与布局", page_icon="🧩", layout="wide")

st.title("组件与布局示例")
st.caption(f"Today: {date.today()}")

with st.sidebar:
    st.header("侧边栏")
    selected = st.selectbox("选择主题", ["产品", "运营", "研发"])
    st.write("当前选择：", selected)

c1, c2, c3 = st.columns(3)
c1.metric("日活", "28,420", "+4.1%")
c2.metric("转化率", "6.8%", "+0.7%")
c3.metric("客单价", "¥146", "-1.3%")

st.divider()

left, right = st.columns([1.2, 1.0], gap="large")
with left:
    st.subheader("数据展示")
    df = pd.DataFrame(
        {
            "region": ["华北", "华东", "华南", "西南"],
            "revenue": [120, 156, 131, 98],
            "orders": [870, 960, 910, 680],
        }
    )
    st.dataframe(df, width="stretch", hide_index=True)

with right:
    st.subheader("代码展示")
    st.code("st.columns([1.2, 1.0])\nst.dataframe(df, width='stretch')", language="python")

with st.expander("展开查看说明"):
    st.write("布局建议：侧边栏放筛选，主区第一屏放指标卡，细节放表格和图。")

tab1, tab2 = st.tabs(["表格", "原始数据"])
with tab1:
    st.table(df)
with tab2:
    st.json(df.to_dict(orient="records"))
