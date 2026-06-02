from flask import Flask, request, jsonify, send_from_directory
import os
import psycopg2
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
NOTIFY_EMAIL = "cineman1987@gmail.com"
SMTP_USER = "cineman1987@gmail.com"
SMTP_PASS = os.environ.get("SMTP_PASS")


def get_db():
    # Heroku Postgres supplies postgres:// but psycopg2 requires postgresql://
    url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
    return psycopg2.connect(url)


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id        SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    name      TEXT,
                    email     TEXT,
                    phone     TEXT,
                    message   TEXT
                )
            """)
        conn.commit()


def send_notification(name, email, phone, message):
    try:
        body = f"New lead received:\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage: {message}"
        msg = MIMEText(body)
        msg["Subject"] = f"New Lead: {name}"
        msg["From"] = SMTP_USER
        msg["To"] = NOTIFY_EMAIL
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, NOTIFY_EMAIL, msg.as_string())
        print(f"Notification sent for {name}")
    except Exception as e:
        print(f"Email notification failed: {e}")


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(__file__), "form.html")


@app.route("/submit", methods=["POST"])
def submit():
    data = request.form
    timestamp = datetime.now()
    name = data.get("name", "")
    email = data.get("email", "")
    phone = data.get("phone", "")
    message = data.get("message", "")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO leads (timestamp, name, email, phone, message) VALUES (%s, %s, %s, %s, %s)",
                (timestamp, name, email, phone, message),
            )
        conn.commit()
    send_notification(name, email, phone, message)
    print(f"New lead: {name} - {email}")
    return jsonify({"status": "success", "message": "Thanks! We will be in touch."})


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
