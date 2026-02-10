from flask import Flask, jsonify
import time
import os
from datetime import datetime
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

# Container start time (resets on Cloud Run cold start)
START_TIME = time.time()


# -----------------------------
# Helper functions
# -----------------------------

def get_uptime_seconds():
    """Uptime of this container instance (seconds)"""
    return round(time.time() - START_TIME, 2)


def read_proc_stat():
    """
    Read CPU stats from /proc/stat
    CPU times are in USER JIFFIES -> converted to SECONDS
    """
    with open("/proc/stat") as f:
        for line in f:
            if line.startswith("cpu "):
                parts = line.split()
                user, nice, system, idle, iowait = map(int, parts[1:6])

                # Linux uses 100 jiffies/sec on most systems
                JIFFIES_PER_SEC = os.sysconf(os.sysconf_names["SC_CLK_TCK"])

                return {
                    "usage_percent": round(
                        100 * (user + system) / (user + system + idle + iowait), 2
                    ),
                    "cores_logical": os.cpu_count(),
                    "time_breakdown_seconds": {
                        "user": round(user / JIFFIES_PER_SEC, 2),
                        "system": round(system / JIFFIES_PER_SEC, 2),
                        "idle": round(idle / JIFFIES_PER_SEC, 2),
                        "iowait": round(iowait / JIFFIES_PER_SEC, 2)
                    },
                    "unit": "seconds",
                    "source": "/proc/stat"
                }


def read_meminfo():
    """
    Memory info from /proc/meminfo
    All values are in KB
    """
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, value = line.split(":")
            mem[key] = int(value.strip().split()[0])

    total = mem["MemTotal"]
    available = mem["MemAvailable"]
    used = total - available

    return {
        "total_kb": total,
        "used_kb": used,
        "available_kb": available,
        "used_percent": round((used / total) * 100, 2),
        "breakdown_kb": {
            "buffers": mem.get("Buffers", 0),
            "cached": mem.get("Cached", 0),
            "swap_total": mem.get("SwapTotal", 0),
            "swap_used": mem.get("SwapTotal", 0) - mem.get("SwapFree", 0)
        },
        "human_readable": {
            "total_gb": round(total / 1024 / 1024, 2),
            "used_gb": round(used / 1024 / 1024, 2),
            "available_gb": round(available / 1024 / 1024, 2)
        },
        "unit": "kilobytes",
        "source": "/proc/meminfo"
    }


def read_process_info():
    """
    Process info for THIS app container
    """
    with open("/proc/self/stat") as f:
        parts = f.read().split()

    with open("/proc/self/status") as f:
        status = f.read()

    threads = 0
    state = "unknown"
    for line in status.splitlines():
        if line.startswith("Threads"):
            threads = int(line.split(":")[1].strip())
        if line.startswith("State"):
            state = line.split(":")[1].strip()

    return {
        "pid": os.getpid(),
        "state": state,
        "cpu_time_ticks": int(parts[13]) + int(parts[14]),
        "memory": {
            "virtual_kb": int(parts[22]) // 1024,
            "rss_kb": int(parts[23]) * 4
        },
        "threads": threads,
        "source": [
            "/proc/self/stat",
            "/proc/self/status"
        ]
    }


def calculate_health(cpu_percent, mem_percent):
    """
    Simple weighted health score
    """
    score = int(100 - (cpu_percent * 0.6 + mem_percent * 0.4))
    score = max(0, min(score, 100))

    if score > 80:
        status = "Healthy"
    elif score > 50:
        status = "Warning"
    else:
        status = "Critical"

    return {
        "score": score,
        "status": status,
        "calculation": {
            "cpu_weight": 0.6,
            "memory_weight": 0.4
        }
    }


# -----------------------------
# Routes
# -----------------------------

@app.route("/")
def home():
    return "Hello from Cloud Run! System check complete."
@app.route("/dashboard")
def dashboard():
    return send_from_directory("static", "dashboard.html")


@app.route("/analyze")
def analyze():
    cpu = read_proc_stat()
    memory = read_meminfo()
    process = read_process_info()

    health = calculate_health(
        cpu["usage_percent"],
        memory["used_percent"]
    )

    return jsonify({
        "meta": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": get_uptime_seconds(),
            "container_scope": "cloud-run",
            "note": "metrics reset on container cold start"
        },
        "cpu": cpu,
        "memory": memory,
        "process": process,
        "health": health
    })


# -----------------------------
# Local entry point
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

