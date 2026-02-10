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
def calculate_health(cpu, memory, process, uptime_seconds):
    """
    Multi-level health calculation with alert breakpoints
    """

    # -----------------------------
    # Extract signals safely
    # -----------------------------
    process_cpu = cpu.get("usage_percent", 0.0)

    total_mem_kb = memory.get("total_kb", 1)
    process_rss_kb = process.get("memory", {}).get("rss_kb", 0)
    process_mem_percent = round((process_rss_kb / total_mem_kb) * 100, 2)

    system_mem_percent = memory.get("used_percent", 0.0)
    threads = process.get("threads", 1)

    cold_start = uptime_seconds < 30

    # -----------------------------
    # Base score
    # -----------------------------
    score = 100

    score -= process_cpu * 0.4
    score -= process_mem_percent * 0.3
    score -= system_mem_percent * 0.2

    if threads > 5:
        score -= min((threads - 5) * 2, 12)

    # Cold start soft protection
    if cold_start:
        score = max(score, 70)

    score = int(max(0, min(score, 100)))

    # -----------------------------
    # Breakpoints
    # -----------------------------
    if score > 80:
        state = "Healthy"
        color = "green"
        severity = "normal"
    elif score > 70:
        state = "Warning"
        color = "yellow"
        severity = "low"
    elif score > 55:
        state = "Degraded"
        color = "orange"
        severity = "medium"
    elif score > 40:
        state = "Alert"
        color = "red"
        severity = "high"
    else:
        state = "Failure"
        color = "red"
        severity = "critical"

    # -----------------------------
    # Reason generator (UI gold ✨)
    # -----------------------------
    reasons = []
    if process_cpu > 70:
        reasons.append("High CPU usage")
    if process_mem_percent > 60:
        reasons.append("High process memory usage")
    if system_mem_percent > 80:
        reasons.append("System memory pressure")
    if threads > 10:
        reasons.append("High thread count")
    if cold_start:
        reasons.append("Cold start warming phase")

    if not reasons:
        reasons.append("Operating normally")

    # -----------------------------
    # Final object
    # -----------------------------
    return {
        "score": score,
        "state": state,
        "color": color,
        "severity": severity,
        "reasons": reasons,
        "signals": {
            "process_cpu_percent": process_cpu,
            "process_memory_percent": process_mem_percent,
            "system_memory_percent": system_mem_percent,
            "threads": threads,
            "uptime_seconds": uptime_seconds,
            "cold_start": cold_start
        },
        "thresholds": {
            "healthy": "> 80",
            "warning": "71–80",
            "degraded": "56–70",
            "alert": "41–55",
            "failure": "<= 40"
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

