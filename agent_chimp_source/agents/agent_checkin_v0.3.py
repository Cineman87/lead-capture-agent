#!/usr/bin/env python3
"""
Agent Chimp – Shared Check-in Module v0.3
Import this in any agent to post a check-in to the backend.
"""
import json
import socket
import platform
import requests

BACKEND_URL = "http://localhost:5000"


def checkin(agent_name: str, client_name: str, status: str = "online",
            message: str = "", backend_url: str = None, version: str = "0.3") -> bool:
    """
    POST a check-in to the Agent Chimp backend.
    Returns True on success, False on any error.
    """
    url = backend_url or BACKEND_URL
    payload = {
        "agent_name":   agent_name,
        "client_name":  client_name,
        "status":       status,
        "message":      message,
        "version":      version,
        "machine_info": json.dumps({
            "hostname":   socket.gethostname(),
            "platform":   platform.system(),
            "os_version": platform.version()[:60],
        }),
    }
    try:
        r = requests.post(f"{url}/checkin", json=payload, timeout=5)
        return r.ok
    except Exception:
        return False
