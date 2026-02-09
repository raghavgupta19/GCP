from flask import Flask, jsonify
import psutil
import time
from datetime import datetime

app = Flask(__name__)
start_time = time.time()  # Track container start time

@app.route('/')
def home():
    return "Hello from Cloud Run! System check complete."

@app.route('/analyze')
def analyze():
    timestamp = datetime.utcnow().isoformat() + 'Z'
    uptime_seconds = time.time() - start_time
    cpu_metric = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    memory_metric = memory.percent

    # Health score logic
    health_score = int(100 - (cpu_metric*0.5 + memory_metric*0.5))
    health_score = max(0, min(health_score, 100))

    # Message based on score
    if health_score > 80:
        message = "Healthy"
    elif health_score > 50:
        message = "Warning"
    else:
        message = "Critical"

    return jsonify({
        "timestamp": timestamp,
        "uptime_seconds": round(uptime_seconds, 2),
        "cpu_metric": cpu_metric,
        "memory_metric": memory_metric,
        "health_score": health_score,
        "message": message
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
