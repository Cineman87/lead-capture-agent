#!/usr/bin/env python3
"""
Agent Chimp Backend v0.3
Flask API server – agents check in here, dashboard reads from here.

Run:
    python agent_chimp_backend_v0.3.py
    PORT=5001 python agent_chimp_backend_v0.3.py
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
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
    port = int(os.environ.get("PORT", 5000))
    print(f"[Agent Chimp Backend] Running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
