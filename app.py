from flask import Flask
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return f"""
    <h1>HW3 - Azure PaaS</h1>
    <p>學號：1123304</p>
    <p>姓名：Juan</p>
    <p>Server Time (UTC)：{datetime.utcnow()}</p>
    """

if __name__ == "__main__":
    app.run()
