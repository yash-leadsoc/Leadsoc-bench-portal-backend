from fastapi import APIRouter, Depends, HTTPException, status

from .. import models
from ..database import get_db, log_audit, out
from ..deps import current_user
from ..schemas import ChangePasswordIn, LoginIn, ProfileIn, AvailabilityIn
from ..security import create_token, hash_password, verify_password

router = APIRouter(tags=["auth"])
C = models


@router.post("/auth/login")
def login(body: LoginIn, db=Depends(get_db)):
    doc = db[C.USERS].find_one({"email": body.email.lower().strip()})
    if not doc or not verify_password(body.password, doc.get("passwordHash", "")):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if doc.get("active") is False:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account deactivated")
    u = models.User(doc)
    token = create_token({"sub": u.id, "role": u.role})
    return {"access_token": token, "token_type": "bearer", "user": u.as_dict()}


@router.get("/auth/me")
def me(user: models.User = Depends(current_user)):
    return user.as_dict()


@router.post("/auth/change-password")
def change_password(body: ChangePasswordIn, db=Depends(get_db),
                    user: models.User = Depends(current_user)):
    doc = db[C.USERS].find_one({"_id": user.id})
    if not verify_password(body.currentPassword, doc.get("passwordHash", "")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    if len(body.newPassword) < 6:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password too short (min 6)")
    db[C.USERS].update_one({"_id": user.id}, {"$set": {
        "passwordHash": hash_password(body.newPassword), "mustChangePassword": False}})
    log_audit(db, user.name, "Change password", user.email)
    return {"ok": True}


@router.get("/me/profile")
def get_profile(db=Depends(get_db), user: models.User = Depends(current_user)):
    prof = user.as_dict()
    if user.employee_id:
        emp = db[C.EMPLOYEES].find_one({"_id": user.employee_id})
        if emp:
            from ..profile_calc import compute_profile_completion
            prof["employee"] = out(emp)
            prof["profileCompletion"] = compute_profile_completion(emp)
    return prof


@router.put("/me/profile")
def update_profile(body: ProfileIn, db=Depends(get_db),
                   user: models.User = Depends(current_user)):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if patch.get("name"):
        db[C.USERS].update_one({"_id": user.id}, {"$set": {"name": patch["name"]}})
    # The employee record is the single source of truth: write every master field.
    if user.employee_id:
        if patch:
            db[C.EMPLOYEES].update_one({"_id": user.employee_id}, {"$set": patch})
        emp = db[C.EMPLOYEES].find_one({"_id": user.employee_id})
        if emp:
            from .readiness_calc import compute_readiness
            compute_readiness(db, emp)
    return {"ok": True, **{k: v for k, v in patch.items() if k not in ("skills", "certifications")}}


@router.put("/me/availability")
def set_my_availability(body: AvailabilityIn, db=Depends(get_db),
                        user: models.User = Depends(current_user)):
    if not user.employee_id:
        raise HTTPException(400, "Not an employee account")
    db[C.EMPLOYEES].update_one({"_id": user.employee_id},
                               {"$set": {"availability": body.slots}})
    return {"ok": True, "slots": body.slots}
