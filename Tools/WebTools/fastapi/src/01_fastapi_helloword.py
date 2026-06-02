from fastapi import FastAPI

app = FastAPI()

# http://127.0.0.1:8000
@app.get("/")
def home():
    return {"message": "Hello, FastAPI！！!"}

# http://127.0.0.1:8000/my_info
@app.get("/my_info")
def my_info():
    return "哈欠老师"