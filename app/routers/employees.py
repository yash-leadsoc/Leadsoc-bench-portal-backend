from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException

from .. import models
from ..database import get_db, log_audit, now_iso, out, out_list
from ..deps import bu_filter, current_user, require
from ..ids import email_from_name, next_employee_id
from ..integrations.calendar import availability_events, google_connected
from ..schemas import EmployeeIn, StatusIn
from .readiness_calc import compute_readiness

router = APIRouter(tags=["employees"])
C = models


@router.get("/employees")
def list_employees(db=Depends(get_db), user=Depends(current_user)):
    from ..profile_calc import compute_profile_completion
    rows = out_list(db[C.EMPLOYEES].find(bu_filter(user)))
    for e in rows:
        e["profileCompletionPct"] = compute_profile_completion(e)["pct"]
    return rows


@router.get("/employees/{eid}")
def get_employee(eid: str, db=Depends(get_db), user=Depends(current_user)):
    doc = db[C.EMPLOYEES].find_one({"_id": eid})
    if not doc:
        raise HTTPException(404, "Not found")
    return out(doc)


@router.post("/employees")
def add_employee(body: EmployeeIn, db=Depends(get_db), user=Depends(require("add"))):
    bu = body.bu if user.role == "admin" else user.bu
    # Fixed id entered by BU; fall back to auto-generated only if left blank.
    eid = (body.employeeId or "").strip() or next_employee_id(db)
    if db[C.EMPLOYEES].find_one({"_id": eid}):
        raise HTTPException(400, f"Employee id {eid} already exists")
    email = (body.email or "").strip().lower() or email_from_name(body.name)
    doc = {"_id": eid, "name": body.name, "email": email,
           "phone": (body.phone or "").strip(), "location": "Bengaluru", "bu": bu, "practice": body.practice,
            "manager": (body.manager or "").strip() if user.role == "admin" else user.name,
           "benchStart": date.today().isoformat(),
           "status": "newEntry", "owner": user.name, "targetDeploymentDate": None,
           "targetRole": body.targetRole, "benchReason": body.benchReason,
           "readinessScore": 0, "deployable": False, "skills": body.skills,
           "availability": [],
           "timeline": [{"at": now_iso(), "text": "Added to bench", "actor": user.name}]}
    db[C.EMPLOYEES].insert_one(doc)
    # Create the employee's self-service login (benchEngineer), linked by id.
    # Default password is firstname@123 (lowercased first name) unless BU set one.
    first = (body.name or "user").strip().split()[0].capitalize()
    temp_password = (body.password or "").strip() or f"{first}@123"
    if db[C.USERS].find_one({"email": email}):
        raise HTTPException(400, f"Email {email} is already in use")
    if not db[C.USERS].find_one({"email": email}):
        from ..ids import next_code
        from ..security import hash_password
        uid = next_code(db, "user", "u_")
        db[C.USERS].insert_one({
            "_id": uid, "name": body.name, "email": email, "role": "benchEngineer",
            "bu": bu, "employeeId": eid, "crossBu": False, "active": True,
            "mustChangePassword": True, "passwordHash": hash_password(temp_password)})
    log_audit(db, user.name, "Add employee", body.name, new=eid)
    result = out(doc)
    result["loginEmail"] = email
    result["tempPassword"] = temp_password
    return result


@router.put("/employees/{eid}")
def edit_employee(eid: str, body: EmployeeIn, db=Depends(get_db),
                  user=Depends(require("edit"))):
    if not db[C.EMPLOYEES].find_one({"_id": eid}):
        raise HTTPException(404, "Not found")
    patch = {"name": body.name, "practice": body.practice, "manager": body.manager,
             "targetRole": body.targetRole, "benchReason": body.benchReason,
             "phone": (body.phone or "").strip()}
    if body.skills:
        patch["skills"] = body.skills
    if body.bu and user.role == "admin":
        patch["bu"] = body.bu

    # If email changed, update it on the employee AND their login account.
    new_email = (body.email or "").strip().lower()
    if new_email:
        clash = db[C.USERS].find_one({"email": new_email, "employeeId": {"$ne": eid}})
        if clash:
            raise HTTPException(400, f"Email {new_email} is already in use")
        patch["email"] = new_email
        db[C.USERS].update_one({"employeeId": eid},
                               {"$set": {"email": new_email, "name": body.name}})

    db[C.EMPLOYEES].update_one({"_id": eid}, {"$set": patch})
    log_audit(db, user.name, "Edit employee", body.name, new=eid)
    return out(db[C.EMPLOYEES].find_one({"_id": eid}))


@router.post("/employees/{eid}/status")
def change_status(eid: str, body: StatusIn, db=Depends(get_db), user=Depends(require("edit"))):
    doc = db[C.EMPLOYEES].find_one({"_id": eid})
    if not doc:
        raise HTTPException(404, "Not found")
    old = doc.get("status")
    db[C.EMPLOYEES].update_one({"_id": eid}, {"$set": {"status": body.status},
        "$push": {"timeline": {"at": now_iso(),
                               "text": f"Status {old} -> {body.status}", "actor": user.name}}})
    log_audit(db, user.name, "Status change", doc.get("name", eid), old, body.status)
    return out(db[C.EMPLOYEES].find_one({"_id": eid}))


# --- bench analytics --------------------------------------------------------
def _bucket(d):
    return "0-15" if d <= 15 else "16-30" if d <= 30 else "31-45" if d <= 45 \
        else "46-60" if d <= 60 else ">60"


def _age(bs):
    return (date.today() - date.fromisoformat(str(bs)[:10])).days


@router.get("/bench/ageing")
def ageing(db=Depends(get_db), user=Depends(current_user)):
    emps = list(db[C.EMPLOYEES].find(bu_filter(user)))
    buckets = {b: 0 for b in ["0-15", "16-30", "31-45", "46-60", ">60"]}
    by_bu, rows = {}, []
    for e in emps:
        a = _age(e["benchStart"])
        buckets[_bucket(a)] += 1
        by_bu[e.get("bu")] = by_bu.get(e.get("bu"), 0) + 1
        rows.append({"id": e["_id"], "name": e["name"], "bu": e.get("bu"),
                     "ageDays": a, "status": e["status"], "owner": e.get("owner", "")})
    rows.sort(key=lambda r: r["ageDays"], reverse=True)
    return {"buckets": buckets, "byBu": by_bu, "rows": rows}


@router.get("/bench/readiness")
def readiness(db=Depends(get_db), user=Depends(current_user)):
    rows = []
    for e in db[C.EMPLOYEES].find(bu_filter(user)):
        score = compute_readiness(db, e)
        rows.append({"id": e["_id"], "name": e["name"], "bu": e.get("bu"),
                     "readiness": score, "status": e["status"],
                     "deployable": score >= 80})
    rows.sort(key=lambda r: r["readiness"], reverse=True)
    return {"rows": rows}


@router.get("/calendar/availability")
def calendar(db=Depends(get_db), user=Depends(current_user)):
    bu = None if user.role == "admin" else user.bu
    return {"googleConnected": google_connected(),
            "events": availability_events(db, bu)}


@router.get("/deployments")
def deployments(db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.DEPLOYMENTS].find(bu_filter(user)))
