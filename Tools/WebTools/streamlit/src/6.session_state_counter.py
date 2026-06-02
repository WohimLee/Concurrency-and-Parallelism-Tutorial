import streamlit as st

st.set_page_config(page_title="状态管理", page_icon="🧠", layout="centered")
st.title("Session State 示例")

if "count" not in st.session_state:
    st.session_state.count = 0

if "todos" not in st.session_state:
    st.session_state.todos = []

col1, col2, col3 = st.columns(3)
if col1.button("+1"):
    st.session_state.count += 1
if col2.button("-1"):
    st.session_state.count -= 1
if col3.button("重置"):
    st.session_state.count = 0

st.metric("当前计数", st.session_state.count)

st.subheader("Todo 列表")
item = st.text_input("新增任务")
if st.button("添加任务") and item.strip():
    st.session_state.todos.append(item.strip())

for idx, todo in enumerate(st.session_state.todos, start=1):
    st.write(f"{idx}. {todo}")
