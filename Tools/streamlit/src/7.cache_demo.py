import time

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="缓存", page_icon="⚡", layout="wide")
st.title("缓存机制示例")


@st.cache_data(ttl=60)
def heavy_dataframe(rows: int) -> pd.DataFrame:
    time.sleep(1.5)
    return pd.DataFrame(
        {
            "x": np.arange(rows),
            "y": np.random.normal(loc=0.0, scale=1.0, size=rows),
        }
    )


@st.cache_resource
def load_resource() -> dict:
    time.sleep(1.0)
    return {"model_name": "demo-model", "version": "1.0"}


rows = st.slider("数据量", min_value=1000, max_value=20000, value=5000, step=1000)

with st.spinner("加载数据中..."):
    df = heavy_dataframe(rows)

resource = load_resource()

st.success(f"resource loaded: {resource['model_name']}@{resource['version']}")
st.line_chart(df.set_index("x"), y="y", width="stretch")
st.dataframe(df.head(20), width="stretch")
