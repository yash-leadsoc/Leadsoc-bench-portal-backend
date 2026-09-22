from .database import now_iso
from .integrations.email import send_email
from . import models


def notify(db, user_id: str, title: str, body: str, kind="info", email=None):
    """Store an in-app notification and best-effort send an email."""
    db[models.NOTIFICATIONS].insert_one({
        "userId": user_id, "title": title, "body": body, "kind": kind,
        "read": False, "createdAt": now_iso()})
    if email:
        send_email(email, title, body)


def notify_employee(db, employee_id: str, title: str, body: str, kind="info"):
    u = db[models.USERS].find_one({"employeeId": employee_id})
    if u:
        notify(db, u["_id"], title, body, kind, u.get("email"))
