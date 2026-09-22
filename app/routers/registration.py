from fastapi import APIRouter, Depends, HTTPException

from .. import models
from ..database import get_db, log_audit, now_iso, out, out_list
from ..deps import bu_filter, current_user, enterprise, require_role
from ..ids import email_from_name, next_code
from ..notify import notify
from ..schemas import BuIn, TaIn, CtoIn, ResetPasswordIn
from ..security import hash_password

router = APIRouter(tags=["registration"])
C = models


# --- Admin creates Business Units (each with a BU-Head login) ----------------
@router.get("/admin/business-units")
def list_bus(db=Depends(get_db), user=Depends(require_role("admin"))):
    return out_list(db[C.BUS].find())


@router.post("/admin/business-units")
def create_bu(body: BuIn, db=Depends(get_db), user=Depends(require_role("admin"))):
    code = body.code.strip()
    if db[C.BUS].find_one({"_id": code}):
        raise HTTPException(400, "BU code already exists")
    db[C.BUS].insert_one({"_id": code, "name": body.name, "code": code,
                          "practices": body.practices, "active": True,
                          "createdAt": now_iso()})
    # BU-Head user
    head_email = (body.headEmail or email_from_name(body.headName)).lower()
    if db[C.USERS].find_one({"email": head_email}):
        raise HTTPException(400, f"User {head_email} already exists")
    pw = body.password or "changeme123"
    uid = next_code(db, "user", "u_")
    db[C.USERS].insert_one({
        "_id": uid, "name": body.headName, "email": head_email, "role": "buHead",
        "bu": code, "employeeId": None, "crossBu": False, "active": True,
        "mustChangePassword": True, "passwordHash": hash_password(pw)})
    log_audit(db, user.name, "Create BU", body.name, new=code)
    notify(db, uid, "Welcome to LeadSoc TEDP",
           f"Your BU-Head account for {body.name} is ready. Please change your password.",
           email=head_email)
    return {"bu": out(db[C.BUS].find_one({"_id": code})),
            "head": {"email": head_email, "tempPassword": pw, "userId": uid}}


@router.put("/admin/business-units/{code}")
def edit_bu(code: str, body: BuIn, db=Depends(get_db), user=Depends(require_role("admin"))):
    if not db[C.BUS].find_one({"_id": code}):
        raise HTTPException(404, "Not found")
    db[C.BUS].update_one({"_id": code}, {"$set": {
        "name": body.name, "practices": body.practices}})
    log_audit(db, user.name, "Edit BU", body.name, new=code)
    return out(db[C.BUS].find_one({"_id": code}))


@router.post("/admin/business-units/{code}/active")
def toggle_bu(code: str, db=Depends(get_db), user=Depends(require_role("admin"))):
    doc = db[C.BUS].find_one({"_id": code})
    if not doc:
        raise HTTPException(404, "Not found")
    new = not doc.get("active", True)
    db[C.BUS].update_one({"_id": code}, {"$set": {"active": new}})
    return out(db[C.BUS].find_one({"_id": code}))


# --- BU-Head (or admin) creates TA users -------------------------------------
@router.post("/ta")
def create_ta(body: TaIn, db=Depends(get_db), user=Depends(require_role("buHead", "admin"))):
    bu = body.bu if user.role == "admin" else user.bu
    if not bu:
        raise HTTPException(400, "BU is required")
    email = (body.email or email_from_name(body.name)).lower()
    if db[C.USERS].find_one({"email": email}):
        raise HTTPException(400, f"User {email} already exists")
    pw = body.password or "changeme123"
    uid = next_code(db, "user", "u_")
    db[C.USERS].insert_one({
        "_id": uid, "name": body.name, "email": email, "role": "ta", "bu": bu,
        "employeeId": None, "crossBu": False, "active": True,
        "mustChangePassword": True, "passwordHash": hash_password(pw)})
    log_audit(db, user.name, "Create TA", body.name, new=email)
    notify(db, uid, "Welcome to LeadSoc TEDP",
           "Your TA account is ready. Please change your password.", email=email)
    return {"userId": uid, "email": email, "tempPassword": pw, "bu": bu}


# --- User administration -----------------------------------------------------
@router.get("/users")
def list_users(db=Depends(get_db), user=Depends(current_user)):
    if user.role == "admin":
        return out_list(db[C.USERS].find())
    if user.role in ("buHead",):
        return out_list(db[C.USERS].find({"bu": user.bu}))
    raise HTTPException(403, "Not permitted")


@router.post("/users/{uid}/active")
def toggle_user(uid: str, db=Depends(get_db), user=Depends(require_role("admin", "buHead"))):
    doc = db[C.USERS].find_one({"_id": uid})
    if not doc:
        raise HTTPException(404, "Not found")
    if user.role == "buHead" and doc.get("bu") != user.bu:
        raise HTTPException(403, "Out of scope")
    new = not doc.get("active", True)
    db[C.USERS].update_one({"_id": uid}, {"$set": {"active": new}})
    return {"id": uid, "active": new}


@router.post("/admin/cto")
def create_cto(body: CtoIn, db=Depends(get_db), user=Depends(require_role("admin"))):
    email = (body.email or email_from_name(body.name)).lower()
    if db[C.USERS].find_one({"email": email}):
        raise HTTPException(400, f"User {email} already exists")
    first = (body.name or "user").strip().split()[0].capitalize()
    pw = body.password or f"{first}@123"
    uid = next_code(db, "user", "u_")
    db[C.USERS].insert_one({
        "_id": uid, "name": body.name, "email": email, "role": "cto",
        "bu": None, "employeeId": body.employeeId, "phone": body.phone,
        "crossBu": True, "active": True, "mustChangePassword": True,
        "passwordHash": hash_password(pw)})
    log_audit(db, user.name, "Create CTO", body.name, new=email)
    notify(db, uid, "Welcome to LeadSoc TEDP",
           "Your CTO account is ready. Please change your password.", email=email)
    return {"userId": uid, "email": email, "tempPassword": pw}


@router.post("/users/{uid}/reset-password")
def reset_password(uid: str, body: ResetPasswordIn, db=Depends(get_db), user=Depends(require_role("admin"))):
    doc = db[C.USERS].find_one({"_id": uid})
    if not doc:
        raise HTTPException(404, "Not found")
    first = (doc.get("name") or "user").split()[0].capitalize()
    pw = body.password or f"{first}@123"
    db[C.USERS].update_one({"_id": uid}, {"$set": {"passwordHash": hash_password(pw), "mustChangePassword": True}})
    log_audit(db, user.name, "Reset password", doc.get("email"))
    return {"id": uid, "tempPassword": pw}
