import streamlit as st

st.set_page_config(page_title="Streamlit Hello", page_icon="🚀", layout="wide")

st.title("Hello Streamlit")
st.subheader("第一课：5 分钟跑起来")
st.write("Streamlit 是脚本式 Web 框架，交互时会触发脚本重跑。")

st.markdown(
    """
### 你会在本课程掌握
- 页面组件与布局
- 数据处理与图表联动
- session_state 与缓存
- 多页面项目组织与部署
"""
)

name = st.text_input("输入你的名字", value="Azen")
if st.button("打招呼"):
    st.success(f"你好，{name}，开始学习 Streamlit。")
