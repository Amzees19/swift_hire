"""
Small SMTP helpers shared by routes and workers.
"""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText


def _effective_from(email_from: str | None, email_user: str | None, smtp_server: str) -> str:
    if "gmail" in (smtp_server or "").lower() and email_user:
        return email_user
    return email_from or email_user or "noreply@zone-alerts.com"


def send_text_email(to_email: str, subject: str, body: str) -> None:
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_from = os.getenv("EMAIL_FROM")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not (email_user and email_password):
        raise RuntimeError("Email credentials not configured. Set EMAIL_USER and EMAIL_PASSWORD.")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = _effective_from(email_from, email_user, smtp_server)
    msg["To"] = to_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(email_user, email_password)
        server.sendmail(msg["From"], [to_email], msg.as_string())

