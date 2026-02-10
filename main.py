from flask import Flask, jsonify, send_from_directory
import time
import os
from datetime import datetime

app = Flask(__name__)

# -----------------------------------
# Container start time (cold start)
# -----------------------------------
START_TIME = time.time()

# -----------------------------------
# Globals for CPU delta calculation
# -----------------------------------
LAST_CPU_TOTAL = None
LAST_CPU_TIME = None


# -----------------------------------
# Helper: uptime
# -----------------------------------
def get_uptime_seconds():
    return round(time.time() - START_TIME, 2)


# -----------------------------------
# Helper: SYSTEM CPU (/proc/stat)
# -----------------------------------
def read_proc_stat():
    """
    System-wide CPU stats from /proc/stat
    Values are cumulative since boot (or container start)
    """
    try:
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("cpu "):
                    parts = line.split()

                    user = int(parts[1])
                    nice = int(parts[2])
                    system = int(parts[3])
                    idle = int(parts[4])
                    iowait = int(parts[5])

                    total = user + nice + system + idle + iowait
                    clk = os.sysconf(os.sysconf_names["SC_CLK_TCK"])

                    # Prevent divide-by-zero
                    usage = 0.0
                    if total > 0:
                        usage = (user + system) / total * 100

                    # Visual floor so charts don’t look broken
                    usage = round(max(usage, 0.1), 2)

                    return {
                        "cores_logical": os.cpu_count(),
                        "usage_percent": usage,
                        "time_breakdown_seconds": {
                            "user": round(user / clk, 2),
                            "system": round(system / clk, 2),
                            "idle": round(idle / clk, 2),
                            "iowait": round(iowait / clk, 2)
                        },
                        "unit": "seconds",
                        "source": "/proc/stat"
                    }

    except Exception as e:
        return {
            "cores_logical": os.cpu_count(),
            "usage_percent": 0.1,
            "time_breakdown_seconds": {},
            "unit": "seconds",
            "source": "/proc/stat",
            "error": str(e)
        }


# -----------------------------------
# Helper: PROCESS CPU (delta-based)
# -----------------------------------
def read_process_cpu():
    """
    Process-level CPU usage using delta calculation.
    This is the MOST reliable metric on Cloud Run.
    """
    global LAST_CPU_TOTAL, LAST_CPU_TIME

    with open("/proc/self/stat") as f:
        parts = f.read().split()

    utime = int(parts[13])
    stime = int(parts[14])
    total_ticks = utime + stime

    now = time.time()

    # First request → seed values
    if LAST_CPU_TOTAL is None:
        LAST_CPU_TOTAL = total_ticks
        LAST_CPU_TIME = now
        return {
            "process_usage_percent": 0.1,
            "cpu_time_ticks": total_ticks,
            "source": "/proc/self/stat"
        }

    tick_delta = total_ticks - LAST_CPU_TOTAL
    time_delta = now - LAST_CPU_TIME

    LAST_CPU_TOTAL = total_ticks
    LAST_CPU_TIME = now

    clk = os.sysconf(os.sysconf_names["SC_CLK_TCK"])

    cpu_percent = 0.0
    if time_delta > 0:
        cpu_percent = (tick_delta / clk) / time_delta * 100

    return {
        "process_usage_percent": round(max(cpu_percent, 0.1), 2),
        "cpu_time_ticks": total_ticks,
        "source": "/proc/self/stat"
    }


# -----------------------------------
# Helper: MEMORY (/proc/meminfo)
# -----------------------------------
def read_meminfo():
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


# -----------------------------------
# Helper: PROCESS INFO
# -----------------------------------
def read_process_info():
    with open("/proc/self/stat") as f:
        parts = f.read().split()

    with open("/proc/self/status") as f:
        status_lines = f.read().splitlines()

    threads = 0
    state = "unknown"
    for line in status_lines:
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


# -----------------------------------
# Helper: HEALTH SCORE
# -----------------------------------
def calculate_health(cpu_percent, mem_percent):
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


# -----------------------------------
# Routes
# -----------------------------------
@app.route("/")
def home():
    return "Hello from Cloud Run! System check complete."


@app.route("/dashboard")
def dashboard():
    return send_from_directory("static", "dashboard.html")


@app.route("/analyze")
def analyze():
    system_cpu = read_proc_stat()
    process_cpu = read_process_cpu()
    memory = read_meminfo()
    process = read_process_info()

    health = calculate_health(
        process_cpu["process_usage_percent"],
        memory["used_percent"]
    )

    return jsonify({
        "meta": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": get_uptime_seconds(),
            "container_scope": "cloud-run",
            "note": "CPU values are delta-based to work on serverless"
        },
        "cpu": {
            **system_cpu,
            **process_cpu
        },
        "memory": memory,
        "process": process,
        "health": health
    })


# -----------------------------------
# Local entry point
# -----------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

