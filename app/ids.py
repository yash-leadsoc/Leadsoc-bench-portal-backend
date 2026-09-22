from .config import EMP_ID_PREFIX

# Employee ids look like LS1703. A counters collection guarantees uniqueness.
def next_employee_id(db, start=1700):
    doc = db["counters"].find_one_and_update(
        {"_id": "employee"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=True)
    seq = doc.get("seq", 1)
    return f"{EMP_ID_PREFIX}{start + seq}"


def next_code(db, name, prefix, start=100):
    doc = db["counters"].find_one_and_update(
        {"_id": name}, {"$inc": {"seq": 1}},
        upsert=True, return_document=True)
    return f"{prefix}{start + doc.get('seq', 1)}"


def email_from_name(name: str, domain="leadsoc.com") -> str:
    base = "".join(ch for ch in name.lower() if ch.isalnum() or ch == " ").strip()
    base = base.replace(" ", ".")
    return f"{base}@{domain}" if base else f"user@{domain}"
