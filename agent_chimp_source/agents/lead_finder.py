#!/usr/bin/env python3
"""
Agent Chimp – Lead Finder
Searches configured sources for new business leads and logs them.
"""
import sys
import os
import csv
import time
import json
import socket
import platform
import requests
from pathlib import Path
from datetime import datetime

# Config (overridden from config.json at runtime if present)
AGENT_NAME  = "Lead Finder"
CLIENT_NAME = "Client A"
BACKEND_URL = "http://localhost:5000"
INTERVAL    = 60   # seconds between search cycles

_cfg_path = Path(__file__).parent.parent / "config.json"
if _cfg_path.exists():
    _cfg = json.loads(_cfg_path.read_text())
    BACKEND_URL = _cfg.get("backend_url", BACKEND_URL)
    CLIENT_NAME = _cfg.get("client_name", CLIENT_NAME)

# Lead Finder settings
LEADS_DIR  = Path(__file__).parent.parent / "leads"
LEADS_FILE = LEADS_DIR / "leads_found.csv"

# Add your actual lead sources here (RSS feeds, API endpoints, etc.)
LEAD_SOURCES: list[dict] = [
    # Example: {"name": "Example RSS", "url": "https://example.com/rss", "type": "rss"},
]


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


def ensure_leads_file():
    LEADS_DIR.mkdir(parents=True, exist_ok=True)
    if not LEADS_FILE.exists():
        with open(LEADS_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["timestamp", "source", "title", "url", "description"])


def save_lead(source: str, title: str, url: str, description: str = ""):
    with open(LEADS_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.now().isoformat(), source, title, url, description
        ])


def search_sources() -> int:
    """Query each configured lead source; return count of new leads found."""
    found = 0
    for source in LEAD_SOURCES:
        try:
            resp = requests.get(source["url"], timeout=10)
            if not resp.ok:
                continue
            # Basic RSS parsing (extend for other types as needed)
            if source.get("type") == "rss":
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                for item in root.iter("item"):
                    title = (item.findtext("title") or "").strip()
                    link  = (item.findtext("link") or "").strip()
                    desc  = (item.findtext("description") or "").strip()[:200]
                    if title and link:
                        save_lead(source["name"], title, link, desc)
                        found += 1
        except Exception as e:
            print(f"[{AGENT_NAME}] Error searching {source.get('name','?')}: {e}")
    return found


def run():
    print(f"[{AGENT_NAME}] Starting for {CLIENT_NAME} ...")
    ensure_leads_file()
    checkin("online", "Agent started")

    while True:
        try:
            new_leads = search_sources()
            msg = f"Scan complete: {new_leads} new lead(s) found"
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
