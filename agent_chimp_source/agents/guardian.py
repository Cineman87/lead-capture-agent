#!/usr/bin/env python3
"""
Agent Chimp – Guardian
Monitors system health and security events; alerts on anomalies.
"""
import sys
import os
import time
import json
import socket
import platform
import requests
from pathlib import Path
from datetime import datetime

# Config (overridden from config.json at runtime if present)
AGENT_NAME  = "Guardian"
CLIENT_NAME = "Client A"
BACKEND_URL = "http://localhost:5000"
INTERVAL    = 30   # seconds between health checks

_cfg_path = Path(__file__).parent.parent / "config.json"
if _cfg_path.exists():
    _cfg = json.loads(_cfg_path.read_text())
    BACKEND_URL = _cfg.get("backend_url", BACKEND_URL)
    CLIENT_NAME = _cfg.get("client_name", CLIENT_NAME)

# Guardian thresholds
CPU_WARN_PCT    = 90.0   # alert if CPU usage exceeds this
MEM_WARN_PCT    = 90.0   # alert if memory usage exceeds this
DISK_WARN_PCT   = 95.0   # alert if any disk is fuller than this


def checkin(status="online", message=""):
    payload = {
        "agent_name":   AGENT_NAME,
        "client_name":  CLIENT_NAME,
        "status":       status,
        "message":      message,
        "version":      "0.3",
        "machine_info": json.dumps({
            "hostname":   socket.gethostname(),
            "platform":   platform.system(),
            "os_version": platform.version()[:60],
        }),
    }
    try:
        requests.post(f"{BACKEND_URL}/checkin", json=payload, timeout=5)
    except Exception as e:
        print(f"[{AGENT_NAME}] check-in failed: {e}")


def get_system_health() -> dict:
    health = {"ok": True, "alerts": []}

    try:
        import psutil  # optional dependency; gracefully skipped if absent

        cpu = psutil.cpu_percent(interval=1)
        if cpu > CPU_WARN_PCT:
            health["alerts"].append(f"High CPU: {cpu:.0f}%")
            health["ok"] = False

        mem = psutil.virtual_memory()
        if mem.percent > MEM_WARN_PCT:
            health["alerts"].append(f"High memory: {mem.percent:.0f}%")
            health["ok"] = False

        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                if usage.percent > DISK_WARN_PCT:
                    health["alerts"].append(
                        f"Disk {part.mountpoint} at {usage.percent:.0f}%")
                    health["ok"] = False
            except PermissionError:
                pass

        health["cpu_pct"]  = cpu
        health["mem_pct"]  = mem.percent
        health["uptime"]   = int(time.time() - psutil.boot_time())

    except ImportError:
        # psutil not installed – report basic uptime only
        health["note"] = "psutil not installed; install it for full monitoring"

    return health


def run():
    print(f"[{AGENT_NAME}] Starting for {CLIENT_NAME} ...")
    checkin("online", "Guardian started")

    while True:
        try:
            health = get_system_health()
            if health["ok"]:
                msg = "System healthy"
                if "cpu_pct" in health:
                    msg += f" | CPU {health['cpu_pct']:.0f}% MEM {health['mem_pct']:.0f}%"
                status = "online"
            else:
                msg    = "ALERT: " + "; ".join(health["alerts"])
                status = "error"

            print(f"[{AGENT_NAME}] {msg}")
            checkin(status, msg[:240])
            time.sleep(INTERVAL)

        except KeyboardInterrupt:
            checkin("offline", "Stopped by user")
            print(f"[{AGENT_NAME}] Stopped.")
            sys.exit(0)
        except Exception as e:
            print(f"[{AGENT_NAME}] Error: {e}")
            checkin("error", str(e)[:120])
            time.sleep(INTERVAL)


if __name__ == "__main__":
    run()
