from flask import Flask, jsonify,render_template
import time
from datetime import datetime

app = Flask(__name__)

# Container start time (resets on cold start)
APP_START_TIME = time.time()

# Store previous CPU values to calculate delta
PREV_CPU_TOTAL = None
PREV_CPU_IDLE = None


# ---------- Helper functions ----------

def read_cpu_stats():
    """
    Read CPU stats from /proc/stat
    Returns total_time, idle_time
    """
    with open("/proc/stat", "r") as f:
        cpu_line = f.readline().strip().split()

    values = list(map(int, cpu_line[1:]))

    idle_time = values[3] + values[4]   # idle + iowait
    total_time = sum(values)

    return total_time, idle_time


def get_cpu_usage():
    """
    Calculate CPU usage percentage using delta method
    """
    global PREV_CPU_TOTAL, PREV_CPU_IDLE

    total, idle = read_cpu_stats()

    if PREV_CPU_TOTAL is None:
        PREV_CPU_TOTAL = total
        PREV_CPU_IDLE = idle
        return 0.0

    total_delta = total - PREV_CPU_TOTAL
    idle_delta = idle - PREV_CPU_IDLE

    PREV_CPU_TOTAL = total
    PREV_CPU_IDLE = idle

    if total_delta == 0:
        return 0.0

    usage = 100 * (1 - idle_delta / total_delta)
    return round(usage, 2)


def get_memory_info():
    """
    Read memory details from /proc/meminfo
    """
    meminfo = {}

    with open("/proc/meminfo", "r") as f:
        for line in f:
            key, value = line.split(":")
            meminfo[key.strip()] = int(value.strip().split()[0])

    total = meminfo["MemTotal"]
    available = meminfo["MemAvailable"]
    used = total - available

    return {
        "total_kb": total,
        "used_kb": used,
        "available_kb": available,
        "used_percent": round((used / total) * 100, 2)
    }


def get_process_info():
    """
    Get current process stats from /proc/self/stat
    """
    with open("/proc/self/stat", "r") as f:
        data = f.read().split()

    return {
        "pid": int(data[0]),
        "cpu_time_ticks": int(data[13]) + int(data[14]),
        "memory_pages": int(data[23])
    }


# ---------- Routes ----------
@app.route("/ui")
def ui():
    return render_template("dashboard.html")
@app.route("/")
def home():
    return "Hello from Cloud Run! System check complete."


@app.route("/analyze")
def analyze():
    timestamp = datetime.utcnow().isoformat() + "Z"
    uptime_seconds = round(time.time() - APP_START_TIME, 2)

    cpu_usage = get_cpu_usage()
    memory = get_memory_info()
    process = get_process_info()

    # Health score (simple & explainable)
    health_score = int(100 - (cpu_usage * 0.6 + memory["used_percent"] * 0.4))
    health_score = max(0, min(health_score, 100))

    if health_score >= 80:
        message = "Healthy"
    elif health_score >= 50:
        message = "Degraded"
    else:
        message = "Critical"

    return jsonify({
        "meta": {
            "timestamp": timestamp,
            "uptime_seconds": uptime_seconds
        },
        "cpu": {
            "usage_percent": cpu_usage,
            "source": "/proc/stat"
        },
        "memory": {
            "source": "/proc/meminfo",
            **memory
        },
        "process": {
            "source": "/proc/self/stat",
            **process
        },
        "health": {
            "score": health_score,
            "status": message
        }
    })
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

