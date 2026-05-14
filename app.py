from flask import Flask, request, jsonify, send_from_directory
import csv
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)

LEADS_FILE = os.path.join(os.path.dirname(__file__), "leads.csv")

NOTIFY_EMAIL = "cineman1987@gmail.com"
SMTP_USER = "cineman1987@gmail.com"
SMTP_PASS = "mwzc wxhm vbgh qmvi"

def init_csv():
    if not os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Name", "Email", "Phone", "Message"])

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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name = data.get("name", "")
    email = data.get("email", "")
    phone = data.get("phone", "")
    message = data.get("message", "")
    with open(LEADS_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, name, email, phone, message])
    send_notification(name, email, phone, message)
    print(f"New lead: {name} - {email}")
    return jsonify({"status": "success", "message": "Thanks! We will be in touch."})

if __name__ == "__main__":
    init_csv()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)