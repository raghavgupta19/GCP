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
# Globals for process CPU delta
# -----------------------------------
LAST_CPU_TICKS = None
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
    try:
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("cpu "):
                    parts = line.split()
                    user, nice, system, idle, iowait = map(int, parts[1:6])
                    clk = os.sysconf(os.sysconf_names["SC_CLK_TCK"])

                    total = user + nice + system + idle + iowait
                    usage = 0.1 if total == 0 else (user + system) / total * 100

                    return {
                        "cores_logical": os.cpu_count(),
                        "usage_percent": round(max(usage, 0.1), 2),
                        "time_breakdown_seconds": {
                            "user": round(user / clk, 2),
                            "system": round(system / clk, 2),
                            "idle": round(idle / clk, 2),
                            "iowait": round(iowait / clk, 2),
                        },
                        "unit": "seconds",
                        "source": "/proc/stat",
                    }
    except Exception as e:
        return {
            "cores_logical": os.cpu_count(),
            "usage_percent": 0.1,
            "time_breakdown_seconds": {},
            "unit": "seconds",
            "source": "/proc/stat",
            "error": str(e),
        }


# -----------------------------------
# Helper: PROCESS CPU (delta-based)
# -----------------------------------
def read_process_cpu():
    global LAST_CPU_TICKS, LAST_CPU_TIME

    with open("/proc/self/stat") as f:
        parts = f.read().split()

    utime = int(parts[13])
    stime = int(parts[14])
    total_ticks = utime + stime
    now = time.time()

    if LAST_CPU_TICKS is None:
        LAST_CPU_TICKS = total_ticks
        LAST_CPU_TIME = now
        return {
            "process_usage_percent": 0.1,
            "cpu_time_ticks": total_ticks,
            "source": "/proc/self/stat",
        }

    tick_delta = total_ticks - LAST_CPU_TICKS
    time_delta = now - LAST_CPU_TIME

    LAST_CPU_TICKS = total_ticks
    LAST_CPU_TIME = now

    clk = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    cpu = 0.1 if time_delta <= 0 else (tick_delta / clk) / time_delta * 100

    return {
        "process_usage_percent": round(max(cpu, 0.1), 2),
        "cpu_time_ticks": total_ticks,
        "source": "/proc/self/stat",
    }


# -----------------------------------
# Helper: MEMORY
# -----------------------------------
def read_meminfo():
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":")
            mem[k] = int(v.strip().split()[0])

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
            "swap_used": mem.get("SwapTotal", 0) - mem.get("SwapFree", 0),
        },
        "human_readable": {
            "total_gb": round(total / 1024 / 1024, 2),
            "used_gb": round(used / 1024 / 1024, 2),
            "available_gb": round(available / 1024 / 1024, 2),
        },
        "unit": "kilobytes",
        "source": "/proc/meminfo",
    }


# -----------------------------------
# Helper: PROCESS INFO
# -----------------------------------
def read_process_info():
    with open("/proc/self/stat") as f:
        parts = f.read().split()

    with open("/proc/self/status") as f:
        status = f.read().splitlines()

    threads = 1
    state = "unknown"

    for line in status:
        if line.startswith("Threads"):
            threads = int(line.split(":")[1])
        if line.startswith("State"):
            state = line.split(":")[1].strip()

    return {
        "pid": os.getpid(),
        "state": state,
        "threads": threads,
        "memory": {
            "virtual_kb": int(parts[22]) // 1024,
            "rss_kb": int(parts[23]) * 4,
        },
        "source": ["/proc/self/stat", "/proc/self/status"],
    }


# -----------------------------------
# Helper: HEALTH SCORE
# -----------------------------------
def calculate_health(cpu, memory, process, uptime_seconds):
    process_cpu = cpu.get("process_usage_percent", 0.1)
    system_mem = memory.get("used_percent", 0.0)

    total_mem = memory.get("total_kb", 1)
    rss = process.get("memory", {}).get("rss_kb", 0)
    proc_mem = (rss / total_mem) * 100 if total_mem else 0

    threads = process.get("threads", 1)
    cold_start = uptime_seconds < 30

    score = 100
    score -= process_cpu * 0.4
    score -= proc_mem * 0.3
    score -= system_mem * 0.2

    if threads > 5:
        score -= min((threads - 5) * 2, 12)

    if cold_start:
        score = max(score, 70)

    score = int(max(0, min(score, 100)))

    if score > 80:
        state, color = "Healthy", "green"
    elif score > 70:
        state, color = "Warning", "yellow"
    elif score > 55:
        state, color = "Degraded", "orange"
    elif score > 40:
        state, color = "Alert", "red"
    else:
        state, color = "Failure", "red"

    reasons = []
    if cold_start:
        reasons.append("Cold start warming phase")
    if process_cpu > 70:
        reasons.append("High CPU usage")
    if proc_mem > 60:
        reasons.append("High process memory")
    if system_mem > 80:
        reasons.append("System memory pressure")
    if threads > 10:
        reasons.append("High thread count")
    if not reasons:
        reasons.append("Operating normally")

    return {
        "score": score,
        "state": state,
        "color": color,
        "reasons": reasons,
        "signals": {
            "process_cpu_percent": round(process_cpu, 2),
            "process_memory_percent": round(proc_mem, 2),
            "system_memory_percent": system_mem,
            "threads": threads,
            "uptime_seconds": uptime_seconds,
            "cold_start": cold_start,
        },
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
    uptime = get_uptime_seconds()

    health = calculate_health(
        process_cpu,
        memory,
        process,
        uptime,
    )

    return jsonify({
        "meta": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": uptime,
            "container_scope": "cloud-run",
            "note": "Process CPU is delta-based for serverless accuracy",
        },
        "cpu": {
            **system_cpu,
            **process_cpu,
        },
        "memory": memory,
        "process": process,
        "health": health,
    })


# -----------------------------------
# Entry point
# -----------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

