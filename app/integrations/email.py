"""Email sender. Sends via SMTP when configured; otherwise no-ops (the in-app
notification is always stored by the caller)."""
import smtplib
from email.mime.text import MIMEText

from ..config import (SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER)


def configured() -> bool:
    return bool(SMTP_HOST)


def send_email(to: str, subject: str, body: str) -> dict:
    if not SMTP_HOST or not to:
        return {"sent": False, "reason": "smtp-not-configured"}
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.starttls()
            if SMTP_USER:
                s.login(SMTP_USER, SMTP_PASSWORD)
            s.sendmail(SMTP_FROM, [to], msg.as_string())
        return {"sent": True}
    except Exception as e:
        return {"sent": False, "reason": str(e)}
