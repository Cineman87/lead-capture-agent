#!/usr/bin/env python3
"""
Agent Chimp Deployment Script v0.3
One-click installer for Agent Chimp environments.

Usage:
    python deploy_agent_chimp.py

Edit CLIENT_CONFIG below to customise each deployment.
"""

import os
import sys
import time
import json
import logging
import subprocess
import webbrowser
import platform
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# ==============================================================================
#  CLIENT CONFIGURATION  ← Edit this section for each deployment
# ==============================================================================

CLIENT_CONFIG = {
    "client_name":       "Client A",
    "assigned_agents":   ["Desktop Cleaner", "Lead Finder", "Guardian"],
    "backend_port":      5000,
    "dashboard_type":    "client",    # "client" or "admin"
    "auto_start_agents": True,        # start agents automatically after setup
    "self_destruct":     False,       # delete this script after confirmed running
}

# ── Predefined client configs  (uncomment the one you need) ──────────────────

# CLIENT_CONFIG = {    # Client B – Guardian only
#     "client_name": "Client B",
#     "assigned_agents": ["Guardian"],
#     "backend_port": 5001,
#     "dashboard_type": "client",
#     "auto_start_agents": True,
#     "self_destruct": False,
# }

# CLIENT_CONFIG = {    # Client C – AC Agents
#     "client_name": "Client C",
#     "assigned_agents": ["AC Agent 1", "AC Agent 2"],
#     "backend_port": 5002,
#     "dashboard_type": "client",
#     "auto_start_agents": True,
#     "self_destruct": False,
# }

# CLIENT_CONFIG = {    # Admin – all 10 AC Agents + 3 test agents
#     "client_name": "Admin",
#     "assigned_agents": [
#         "AC Agent 1",  "AC Agent 2",  "AC Agent 3",  "AC Agent 4",  "AC Agent 5",
#         "AC Agent 6",  "AC Agent 7",  "AC Agent 8",  "AC Agent 9",  "AC Agent 10",
#         "Test Agent 1", "Test Agent 2", "Test Agent 3",
#     ],
#     "backend_port": 5000,
#     "dashboard_type": "admin",
#     "auto_start_agents": True,
#     "self_destruct": False,
# }

# ==============================================================================
#  INSTALL PATHS  (no need to change these)
# ==============================================================================

BASE_DIR       = Path.home() / "agent_chimp"
BACKEND_DIR    = BASE_DIR / "backend"
DASHBOARDS_DIR = BASE_DIR / "dashboards"
AGENTS_DIR     = BASE_DIR / "agents"
LOGS_DIR       = BASE_DIR / "logs"

BACKEND_SCRIPT = "agent_chimp_backend_v0.3.py"
DASHBOARD_FILE = "agent_chimp_dashboard_client_v0.3.2.html"
CHECKIN_MODULE = "agent_checkin_v0.3.py"

REQUIRED_PACKAGES = ["flask", "flask-cors", "requests"]
CHECKIN_TIMEOUT   = 30   # seconds to wait for all agents before giving up

# ==============================================================================
#  AGENT TASK DESCRIPTIONS
# ==============================================================================

AGENT_TASKS = {
    "Desktop Cleaner":  "Scans the desktop for old/temp files and organises them into folders",
    "Lead Finder":      "Searches configured sources for new business leads and logs them",
    "Guardian":         "Monitors system health and security events; alerts on anomalies",
    "AC Agent 1":       "General-purpose automation agent #1",
    "AC Agent 2":       "General-purpose automation agent #2",
    "AC Agent 3":       "General-purpose automation agent #3",
    "AC Agent 4":       "General-purpose automation agent #4",
    "AC Agent 5":       "General-purpose automation agent #5",
    "AC Agent 6":       "General-purpose automation agent #6",
    "AC Agent 7":       "General-purpose automation agent #7",
    "AC Agent 8":       "General-purpose automation agent #8",
    "AC Agent 9":       "General-purpose automation agent #9",
    "AC Agent 10":      "General-purpose automation agent #10",
    "Test Agent 1":     "Test / development agent #1",
    "Test Agent 2":     "Test / development agent #2",
    "Test Agent 3":     "Test / development agent #3",
}


def agent_filename(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_") + ".py"


# ==============================================================================
#  EMBEDDED FILE TEMPLATES
#  Substitution tokens: __PORT__  __CLIENT__  __AGENT_NAME__  __AGENT_TASK__
# ==============================================================================

BACKEND_TEMPLATE = '''#!/usr/bin/env python3
"""Agent Chimp Backend v0.3"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
CORS(app)

_HERE    = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(_HERE, "agent_chimp.db")
DASH_DIR = os.path.join(_HERE, "..", "dashboards")


def _db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    db = _db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name   TEXT    UNIQUE NOT NULL,
            client_name  TEXT    NOT NULL,
            status       TEXT    DEFAULT 'offline',
            last_checkin TEXT,
            machine_info TEXT,
            version      TEXT    DEFAULT '0.3'
        );
        CREATE TABLE IF NOT EXISTS checkins (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name  TEXT NOT NULL,
            client_name TEXT NOT NULL,
            timestamp   TEXT DEFAULT (datetime('now')),
            status      TEXT,
            message     TEXT
        );
    """)
    db.commit()
    db.close()


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/checkin", methods=["POST"])
def checkin():
    d = request.get_json(force=True) or {}
    db = _db()
    db.execute("""
        INSERT INTO agents (agent_name, client_name, status, last_checkin, machine_info, version)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(agent_name) DO UPDATE SET
            client_name  = excluded.client_name,
            status       = excluded.status,
            last_checkin = excluded.last_checkin,
            machine_info = excluded.machine_info,
            version      = excluded.version
    """, (d.get("agent_name", "?"), d.get("client_name", "?"),
          d.get("status", "online"), datetime.now().isoformat(),
          d.get("machine_info", ""), d.get("version", "0.3")))
    db.execute(
        "INSERT INTO checkins (agent_name, client_name, status, message) VALUES (?,?,?,?)",
        (d.get("agent_name", "?"), d.get("client_name", "?"),
         d.get("status", "online"), d.get("message", "")))
    db.commit()
    db.close()
    return jsonify({"status": "ok"})


@app.route("/agents")
def agents():
    db = _db()
    rows = db.execute("SELECT * FROM agents ORDER BY agent_name").fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route("/status")
def backend_status():
    db = _db()
    total  = db.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    online = db.execute("SELECT COUNT(*) FROM agents WHERE status='online'").fetchone()[0]
    db.close()
    return jsonify({"total": total, "online": online})


@app.route("/")
@app.route("/dashboard")
def dashboard():
    return send_from_directory(os.path.abspath(DASH_DIR),
                               "agent_chimp_dashboard_client_v0.3.2.html")


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", __PORT__))
    print(f"[Agent Chimp Backend] Running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
'''

# ─────────────────────────────────────────────────────────────
DASHBOARD_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent Chimp Dashboard</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0d1117; color:#c9d1d9; font-family:"Segoe UI",system-ui,monospace; padding:20px; }
  .header {
    display:flex; justify-content:space-between; align-items:center;
    padding:20px 24px; background:#161b22; border:1px solid #30363d;
    border-radius:10px; margin-bottom:20px;
  }
  .logo  { font-size:1.6em; font-weight:700; color:#58a6ff; letter-spacing:-0.5px; }
  .client{ font-size:0.9em; color:#8b949e; margin-top:4px; }
  .stats { display:flex; gap:16px; }
  .stat  {
    text-align:center; padding:10px 22px;
    background:#21262d; border-radius:8px; border:1px solid #30363d;
  }
  .stat .n { font-size:2em; font-weight:700; }
  .stat.on  .n { color:#3fb950; }
  .stat.off .n { color:#f85149; }
  .stat .lbl { font-size:0.75em; color:#8b949e; margin-top:2px; }
  .meta { display:flex; justify-content:space-between; color:#8b949e; font-size:0.82em; margin-bottom:16px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:14px; }
  .card {
    background:#161b22; border:1px solid #30363d; border-radius:8px;
    padding:16px; border-left:3px solid #30363d; transition:border-color .2s;
  }
  .card.online  { border-left-color:#3fb950; }
  .card.offline { border-left-color:#f85149; }
  .card.error   { border-left-color:#d29922; }
  .card-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
  .name  { font-weight:600; font-size:1.05em; color:#e6edf3; }
  .dot   { width:9px; height:9px; border-radius:50%; flex-shrink:0; }
  .dot.online  { background:#3fb950; box-shadow:0 0 6px #3fb950aa; }
  .dot.offline { background:#484f58; }
  .dot.error   { background:#d29922; }
  .info  { font-size:0.82em; color:#8b949e; line-height:1.7; }
  .badge {
    display:inline-block; padding:1px 7px; border-radius:4px;
    font-size:0.78em; font-weight:600;
  }
  .badge.online  { background:#1f4a2a; color:#3fb950; }
  .badge.offline { background:#2d1e1e; color:#f85149; }
  .badge.error   { background:#2d2207; color:#d29922; }
  .empty { text-align:center; padding:60px; color:#484f58; grid-column:1/-1; }
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="logo">&#x1F412; Agent Chimp</div>
    <div class="client" id="client-label">Loading&hellip;</div>
  </div>
  <div class="stats">
    <div class="stat on">  <div class="n" id="cnt-on">0</div>  <div class="lbl">Online</div></div>
    <div class="stat off"> <div class="n" id="cnt-off">0</div> <div class="lbl">Offline</div></div>
  </div>
</div>

<div class="meta">
  <span>Backend: <strong>http://localhost:__PORT__</strong></span>
  <span>Refresh in <span id="cd">10</span>s &nbsp;|&nbsp; Updated: <span id="ts">--</span></span>
</div>

<div class="grid" id="grid">
  <div class="empty">Connecting to backend&hellip;</div>
</div>

<script>
const API = "http://localhost:__PORT__";
let cd = 10;

function ago(iso) {
  if (!iso) return "never";
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60)   return s + "s ago";
  if (s < 3600) return Math.floor(s/60) + "m ago";
  return Math.floor(s/3600) + "h ago";
}

async function refresh() {
  try {
    const res  = await fetch(API + "/agents");
    const data = await res.json();
    const now  = Date.now();

    // Mark stale check-ins as offline
    data.forEach(a => {
      if (a.last_checkin) {
        const stale = (now - new Date(a.last_checkin).getTime()) / 1000 > 90;
        if (stale && a.status === "online") a.status = "offline";
      }
    });

    const on  = data.filter(a => a.status === "online").length;
    const off = data.length - on;
    document.getElementById("cnt-on").textContent  = on;
    document.getElementById("cnt-off").textContent = off;

    if (data.length > 0)
      document.getElementById("client-label").textContent =
        data[0].client_name + " &mdash; " + data.length + " agent" + (data.length!==1?"s":"") + " assigned";

    const grid = document.getElementById("grid");
    if (data.length === 0) {
      grid.innerHTML = "<div class=\\"empty\\">No agents registered yet.</div>";
    } else {
      grid.innerHTML = data.map(a => `
        <div class="card ${a.status}">
          <div class="card-head">
            <span class="name">${a.agent_name}</span>
            <span class="dot ${a.status}"></span>
          </div>
          <div class="info">
            <span class="badge ${a.status}">${a.status.toUpperCase()}</span><br>
            Last seen: ${ago(a.last_checkin)}<br>
            Client: ${a.client_name}<br>
            Version: v${a.version || "0.3"}
          </div>
        </div>`).join("");
    }
    document.getElementById("ts").textContent = new Date().toLocaleTimeString();
  } catch(e) {
    document.getElementById("grid").innerHTML =
      "<div class=\\"empty\\">&#9888; Cannot reach backend at " + API + "</div>";
  }
}

function tick() {
  cd--;
  document.getElementById("cd").textContent = cd;
  if (cd <= 0) { cd = 10; refresh(); }
}

refresh();
setInterval(tick, 1000);
</script>
</body>
</html>
'''

# ─────────────────────────────────────────────────────────────
CHECKIN_TEMPLATE = '''#!/usr/bin/env python3
"""Agent Chimp – shared check-in helper v0.3"""
import json, socket, platform, requests

BACKEND_URL = "http://localhost:__PORT__"


def checkin(agent_name, client_name, status="online", message="",
            backend_url=None, version="0.3"):
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
'''

# ─────────────────────────────────────────────────────────────
AGENT_TEMPLATE = '''#!/usr/bin/env python3
"""
Agent Chimp – __AGENT_NAME__
Task: __AGENT_TASK__
"""
import sys, os, time, json, socket, platform, requests
from pathlib import Path

# Config (written by deploy script; edit directly if needed)
AGENT_NAME  = "__AGENT_NAME__"
CLIENT_NAME = "__CLIENT__"
BACKEND_URL = "http://localhost:__PORT__"
INTERVAL    = 30   # seconds between check-ins

# Override from config.json if present
_cfg_path = Path(__file__).parent.parent / "config.json"
if _cfg_path.exists():
    _cfg = json.loads(_cfg_path.read_text())
    BACKEND_URL = _cfg.get("backend_url", BACKEND_URL)
    CLIENT_NAME = _cfg.get("client_name", CLIENT_NAME)


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


def work():
    """Agent-specific logic goes here."""
    # __AGENT_TASK__
    pass


def run():
    print(f"[{AGENT_NAME}] Starting for {CLIENT_NAME} ...")
    checkin("online", "Agent started")
    while True:
        try:
            work()
            checkin("online", "Running")
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
'''


# ==============================================================================
#  HELPERS
# ==============================================================================

log: logging.Logger  # set up in setup_logging()


def setup_logging() -> None:
    global log
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "setup.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout),
        ],
    )
    log = logging.getLogger("deploy")


def banner(msg: str) -> None:
    width = 60
    log.info("=" * width)
    log.info(f"  {msg}")
    log.info("=" * width)


def http_get(url: str, timeout: int = 5) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


# ==============================================================================
#  SETUP STEPS
# ==============================================================================

def create_directories() -> None:
    banner("Creating directory structure")
    for d in (BACKEND_DIR, DASHBOARDS_DIR, AGENTS_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
        log.info(f"  {d}")


def install_dependencies() -> None:
    banner("Installing Python dependencies")
    for pkg in REQUIRED_PACKAGES:
        log.info(f"  Installing {pkg} ...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", pkg],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            # Fall back to --user install
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", "--user", pkg],
                capture_output=True, text=True,
            )
        if result.returncode == 0:
            log.info(f"  ✓ {pkg}")
        else:
            log.warning(f"  ✗ {pkg}: {result.stderr.strip()[:120]}")


def apply_template(template: str, config: dict, agent_name: str = "") -> str:
    task = AGENT_TASKS.get(agent_name, f"General-purpose agent: {agent_name}")
    return (
        template
        .replace("__PORT__",       str(config["backend_port"]))
        .replace("__CLIENT__",     config["client_name"])
        .replace("__AGENT_NAME__", agent_name)
        .replace("__AGENT_TASK__", task)
    )


def write_files(config: dict) -> None:
    banner("Writing files")

    # Backend
    backend_path = BACKEND_DIR / BACKEND_SCRIPT
    backend_path.write_text(apply_template(BACKEND_TEMPLATE, config))
    log.info(f"  {backend_path}")

    # Dashboard
    dash_path = DASHBOARDS_DIR / DASHBOARD_FILE
    dash_path.write_text(apply_template(DASHBOARD_TEMPLATE, config))
    log.info(f"  {dash_path}")

    # Check-in module
    checkin_path = AGENTS_DIR / CHECKIN_MODULE
    checkin_path.write_text(apply_template(CHECKIN_TEMPLATE, config))
    log.info(f"  {checkin_path}")

    # One agent script per assigned agent
    for agent_name in config["assigned_agents"]:
        agent_path = AGENTS_DIR / agent_filename(agent_name)
        agent_path.write_text(apply_template(AGENT_TEMPLATE, config, agent_name))
        log.info(f"  {agent_path}")

    # Shared config.json so agents can read dynamic settings
    cfg_path = BASE_DIR / "config.json"
    cfg_path.write_text(json.dumps({
        "client_name":    config["client_name"],
        "backend_url":    f"http://localhost:{config['backend_port']}",
        "dashboard_type": config["dashboard_type"],
        "assigned_agents": config["assigned_agents"],
    }, indent=2))
    log.info(f"  {cfg_path}")


def init_database() -> None:
    banner("Initialising SQLite database")
    import sqlite3
    db_path = BACKEND_DIR / "agent_chimp.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name   TEXT    UNIQUE NOT NULL,
            client_name  TEXT    NOT NULL,
            status       TEXT    DEFAULT 'offline',
            last_checkin TEXT,
            machine_info TEXT,
            version      TEXT    DEFAULT '0.3'
        );
        CREATE TABLE IF NOT EXISTS checkins (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name  TEXT NOT NULL,
            client_name TEXT NOT NULL,
            timestamp   TEXT DEFAULT (datetime('now')),
            status      TEXT,
            message     TEXT
        );
    """)
    conn.commit()
    conn.close()
    log.info(f"  {db_path}")


def start_backend(config: dict) -> subprocess.Popen:
    banner("Starting backend server")
    backend_script = BACKEND_DIR / BACKEND_SCRIPT
    log_file = open(LOGS_DIR / "backend.log", "w")

    kwargs = dict(
        stdout=log_file,
        stderr=log_file,
        env={**os.environ, "PORT": str(config["backend_port"])},
    )
    if platform.system() == "Windows":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen([sys.executable, str(backend_script)], **kwargs)
    log.info(f"  PID {proc.pid} – port {config['backend_port']}")

    # Wait up to 10 s for the backend to become healthy
    port = config["backend_port"]
    for i in range(20):
        time.sleep(0.5)
        if http_get(f"http://localhost:{port}/health"):
            log.info(f"  Backend healthy after {(i+1)*0.5:.1f}s")
            return proc
    log.warning("  Backend did not respond in time – continuing anyway")
    return proc


def start_agents(config: dict) -> list[subprocess.Popen]:
    banner("Starting agents")
    procs = []
    port  = config["backend_port"]
    for agent_name in config["assigned_agents"]:
        script = AGENTS_DIR / agent_filename(agent_name)
        if not script.exists():
            log.warning(f"  Script not found: {script}")
            continue
        agent_log = open(LOGS_DIR / f"{agent_filename(agent_name)[:-3]}.log", "w")
        kwargs = dict(
            stdout=agent_log,
            stderr=agent_log,
            env={**os.environ, "PORT": str(port)},
        )
        if platform.system() == "Windows":
            kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        else:
            kwargs["start_new_session"] = True

        proc = subprocess.Popen([sys.executable, str(script)], **kwargs)
        log.info(f"  [{agent_name}] PID {proc.pid}")
        procs.append(proc)
    return procs


def wait_for_agents(config: dict, timeout: int = CHECKIN_TIMEOUT) -> bool:
    banner(f"Waiting for agents to check in (timeout: {timeout}s)")
    port    = config["backend_port"]
    needed  = set(config["assigned_agents"])
    url     = f"http://localhost:{port}/agents"
    deadline = time.time() + timeout

    while time.time() < deadline:
        data = http_get(url)
        if data is not None:
            checked_in = {a["agent_name"] for a in data if a.get("status") == "online"}
            missing    = needed - checked_in
            if not missing:
                log.info(f"  All {len(needed)} agent(s) checked in successfully!")
                return True
            remaining = int(deadline - time.time())
            log.info(f"  Waiting… {len(checked_in)}/{len(needed)} online, "
                     f"{remaining}s left. Missing: {', '.join(sorted(missing))}")
        time.sleep(2)

    # Report what's still missing
    data     = http_get(url) or []
    checked  = {a["agent_name"] for a in data if a.get("status") == "online"}
    missing  = needed - checked
    log.warning(f"  Timed out. Still missing: {', '.join(sorted(missing))}")
    return False


def open_dashboard(config: dict) -> None:
    banner("Opening dashboard")
    port = config["backend_port"]
    url  = f"http://localhost:{port}/"
    log.info(f"  {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        log.warning(f"  Could not open browser automatically: {e}")
        log.info(f"  Open manually: {url}")


def self_destruct() -> None:
    banner("Self-destructing deploy script")
    script = Path(__file__).resolve()
    log.info(f"  Deleting {script}")
    try:
        script.unlink()
        log.info("  Done.")
    except Exception as e:
        log.warning(f"  Could not delete: {e}")


# ==============================================================================
#  MAIN
# ==============================================================================

def setup() -> None:
    config = CLIENT_CONFIG
    start_time = time.time()

    setup_logging()
    banner("Agent Chimp Deployment Script v0.3")
    log.info(f"  Client:  {config['client_name']}")
    log.info(f"  Agents:  {', '.join(config['assigned_agents'])}")
    log.info(f"  Port:    {config['backend_port']}")
    log.info(f"  Install: {BASE_DIR}")

    create_directories()
    install_dependencies()
    write_files(config)
    init_database()

    backend_proc = start_backend(config)

    if config.get("auto_start_agents", True):
        start_agents(config)
        agents_ok = wait_for_agents(config)
    else:
        log.info("auto_start_agents=False – skipping agent launch")
        agents_ok = True

    open_dashboard(config)

    elapsed = time.time() - start_time
    banner("Setup complete")
    log.info(f"  Finished in {elapsed:.1f}s")
    log.info(f"  Dashboard:    http://localhost:{config['backend_port']}/")
    log.info(f"  Install dir:  {BASE_DIR}")
    log.info(f"  Logs:         {LOGS_DIR}")
    if not agents_ok:
        log.warning("  Some agents did not check in – check logs for details.")

    if config.get("self_destruct", False):
        self_destruct()


if __name__ == "__main__":
    setup()
