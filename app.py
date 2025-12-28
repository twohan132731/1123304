from flask import Flask, request
from datetime import datetime
import io
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import base64

app = Flask(__name__)

# --- in-memory store (先不用 SQL，之後再換成 Azure SQL) ---
STORE = {
    "glucose": None,  # DataFrame with columns: time, value
}

def render_plot(df: pd.DataFrame) -> str:
    # df: time,value,roll,high_flag
    fig = plt.figure()
    plt.plot(df["time"], df["value"])
    if "roll" in df.columns:
        plt.plot(df["time"], df["roll"])
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def risk_from_glucose(df: pd.DataFrame) -> tuple[str, str]:
    """
    超簡單規則版（之後可換成你圖上的 Analysis & Detection + GenAI）
    """
    if df is None or len(df) < 5:
        return "未知", "請先上傳至少 5 筆血糖資料。"

    v = df["value"].astype(float)
    roll = v.rolling(5, min_periods=5).mean()
    std = v.rolling(10, min_periods=10).std()

    # shift detection: 最近 5 筆平均 vs 前 10 筆平均
    recent = v.tail(5).mean()
    prev = v.tail(15).head(10).mean() if len(v) >= 15 else v.head(max(len(v)-5, 1)).mean()

    score = 0
    if recent >= 140:  # 例：偏高（你可按課堂/專案標準調）
        score += 2
    if recent >= 180:
        score += 2
    if std.dropna().tail(1).values.size and std.dropna().tail(1).values[0] >= 25:
        score += 1
    if recent - prev >= 20:
        score += 1

    if score >= 4:
        return "高", "近期血糖偏高且波動大，建議先檢視飲食/作息並考慮諮詢醫護人員。"
    if score >= 2:
        return "中", "血糖有偏高或波動增加趨勢，建議留意餐後、活動量與睡眠。"
    return "低", "目前趨勢相對穩定，維持規律飲食、運動與作息。"

@app.route("/")
def home():
    return f"""
    <h1>HW3 - Azure PaaS</h1>
    <p>學號：1123304</p>
    <p>姓名：Juan</p>
    <p>Server Time (UTC)：{datetime.utcnow()}</p>
    <p><a href="/upload">Upload Glucose CSV</a> | <a href="/dashboard">Dashboard</a></p>
    """

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return """
        <h2>Upload Glucose CSV</h2>
        <p>CSV 欄位需包含：time,value</p>
        <form method="POST" enctype="multipart/form-data">
          <input type="file" name="file" accept=".csv" />
          <button type="submit">Upload</button>
        </form>
        <p><a href="/">Back</a></p>
        """

    f = request.files.get("file")
    if not f:
        return "No file", 400

    content = f.read().decode("utf-8", errors="ignore")
    df = pd.read_csv(io.StringIO(content))

    # normalize columns
    cols = {c.lower().strip(): c for c in df.columns}
    if "time" not in cols or "value" not in cols:
        return "CSV must include columns: time,value", 400

    df = df.rename(columns={cols["time"]: "time", cols["value"]: "value"})
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time", "value"]).sort_values("time")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])

    STORE["glucose"] = df.reset_index(drop=True)
    return """
    <p>Upload success ✅</p>
    <p><a href="/dashboard">Go to Dashboard</a></p>
    """

@app.route("/dashboard")
def dashboard():
    df = STORE["glucose"]
    if df is None or df.empty:
        return """
        <h2>Dashboard</h2>
        <p>No glucose data yet. Please <a href="/upload">upload</a>.</p>
        <p><a href="/">Back</a></p>
        """

    work = df.copy()
    work["roll"] = work["value"].rolling(5, min_periods=1).mean()
    img = render_plot(work)

    level, advice = risk_from_glucose(work)

    return f"""
    <h2>Dashboard</h2>
    <p><b>Glucose risk:</b> {level}</p>
    <p>{advice}</p>
    <img src="{img}" style="max-width: 900px; width: 100%; border:1px solid #ddd;" />
    <p><a href="/upload">Upload new CSV</a> | <a href="/">Back</a></p>
    """

if __name__ == "__main__":
    app.run()

