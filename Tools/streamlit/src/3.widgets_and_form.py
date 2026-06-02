import pandas as pd
import streamlit as st

st.set_page_config(page_title="交互控件", page_icon="🎛️", layout="wide")

st.title("交互控件与表单")

with st.sidebar:
    st.header("筛选条件")
    category = st.multiselect("类别", ["股票", "基金", "债券", "加密"], default=["股票", "加密"])
    risk = st.slider("风险偏好", min_value=1, max_value=10, value=6)

st.write("当前类别：", category)
st.write("风险偏好：", risk)

st.subheader("表单提交模式")
with st.form("strategy_form"):
    symbol = st.text_input("标的", value="NVDA")
    budget = st.number_input("预算", min_value=1000, max_value=1000000, step=1000, value=20000)
    style = st.radio("策略风格", ["保守", "均衡", "激进"], horizontal=True)
    submitted = st.form_submit_button("生成建议")

if submitted:
    ratio = {"保守": 0.3, "均衡": 0.5, "激进": 0.75}[style]
    position = int(budget * ratio)
    st.success(f"建议：{symbol} 目标仓位约 {position:,}（{style}）")

uploaded = st.file_uploader("上传 CSV（可选）", type=["csv"])
if uploaded is not None:
    up_df = pd.read_csv(uploaded)
    st.dataframe(up_df.head(20), width="stretch")
