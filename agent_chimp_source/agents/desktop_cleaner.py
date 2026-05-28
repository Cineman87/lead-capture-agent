#!/usr/bin/env python3
"""
Agent Chimp – Desktop Cleaner
Scans the desktop for old/temp files and organises them into folders.
"""
import sys
import os
import time
import json
import shutil
import socket
import platform
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Config (overridden from config.json at runtime if present)
AGENT_NAME  = "Desktop Cleaner"
CLIENT_NAME = "Client A"
BACKEND_URL = "http://localhost:5000"
INTERVAL    = 30   # seconds between check-ins

_cfg_path = Path(__file__).parent.parent / "config.json"
if _cfg_path.exists():
    _cfg = json.loads(_cfg_path.read_text())
    BACKEND_URL = _cfg.get("backend_url", BACKEND_URL)
    CLIENT_NAME = _cfg.get("client_name", CLIENT_NAME)

# Desktop Cleaner settings
DESKTOP_PATH   = Path.home() / "Desktop"
ARCHIVE_FOLDER = DESKTOP_PATH / "_Archived"
OLD_FILE_DAYS  = 30   # files not touched in this many days get archived
TEMP_EXTENSIONS = {".tmp", ".temp", ".bak", ".log~", ".swp"}


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


def clean_desktop() -> dict:
    if not DESKTOP_PATH.exists():
        return {"skipped": True, "reason": "Desktop path not found"}

    moved   = 0
    deleted = 0
    cutoff  = datetime.now() - timedelta(days=OLD_FILE_DAYS)

    for item in DESKTOP_PATH.iterdir():
        if item.name.startswith("_") or item.is_dir():
            continue
        try:
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            # Delete known temp files
            if item.suffix.lower() in TEMP_EXTENSIONS:
                item.unlink()
                deleted += 1
                continue
            # Archive old files
            if mtime < cutoff:
                ARCHIVE_FOLDER.mkdir(exist_ok=True)
                dest = ARCHIVE_FOLDER / item.name
                if dest.exists():
                    dest = ARCHIVE_FOLDER / f"{item.stem}_{int(mtime.timestamp())}{item.suffix}"
                shutil.move(str(item), str(dest))
                moved += 1
        except Exception as e:
            print(f"[{AGENT_NAME}] Could not process {item.name}: {e}")

    return {"moved": moved, "deleted": deleted}


def run():
    print(f"[{AGENT_NAME}] Starting for {CLIENT_NAME} ...")
    checkin("online", "Agent started")

    while True:
        try:
            result = clean_desktop()
            msg = f"Scan done: moved={result.get('moved',0)} deleted={result.get('deleted',0)}"
            print(f"[{AGENT_NAME}] {msg}")
            checkin("online", msg)
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
