from datetime import datetime
from pymongo import MongoClient
from .config import DB_NAME, MONGO_URL

client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000, tz_aware=False)
db = client[DB_NAME]


def get_db():
    return db


def out(doc):
    if doc is None:
        return None
    d = dict(doc)
    _id = d.pop("_id", None)
    if _id is not None and "id" not in d:
        d["id"] = _id if isinstance(_id, str) else str(_id)
    d.pop("passwordHash", None)
    return d


def out_list(cursor):
    return [out(d) for d in cursor]


def now_iso():
    return datetime.utcnow().isoformat()


def log_audit(db, actor, action, entity, old=None, new=None, reason=""):
    db["audit_logs"].insert_one({
        "at": now_iso(), "actor": actor, "action": action, "entity": entity,
        "oldValue": old, "newValue": new, "reason": reason})
