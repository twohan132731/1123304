from flask import Flask
from datetime import datetime, timezone

app = Flask(__name__)

@app.route("/")
def home():
    now = datetime.now(timezone.utc).isoformat()
    return f"<h1>HW3 - Azure PaaS</h1><p>UTC: {now}</p>"

if __name__ == "__main__":
    app.run()
