from flask import Flask, request  # 需要 import request 处理 POST 方法

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Flask!"

@app.route('/user/<name>')
def user(name):
    return f"Hello, {name}!"

@app.route('/post/<int:post_id>')
def show_post(post_id):
    return f"Post ID: {post_id}"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return "Processing login..."
    return "Show login form"

if __name__ == '__main__':

    app.run(debug=False)  # True 启用 debug 模式，方便开发调试
