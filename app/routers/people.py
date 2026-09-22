from fastapi import APIRouter, Depends, HTTPException

from .. import models
from ..database import get_db, log_audit, now_iso, out, out_list
from ..deps import bu_filter, current_user, require
from ..ids import next_code
from ..notify import notify_employee
from ..schemas import SkillIn, TrainerIn

router = APIRouter(tags=["people"])
C = models


# --- Trainers (CRUD + assign to employee) ------------------------------------
@router.get("/people/trainers")
def trainers(db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.TRAINERS].find())


@router.post("/people/trainers")
def add_trainer(body: TrainerIn, db=Depends(get_db), user=Depends(require("add"))):
    tid = next_code(db, "trainer", "T")
    doc = {"_id": tid, "name": body.name, "email": body.email, "internal": body.internal,
           "expertise": body.expertise, "capacityHoursPerWeek": body.capacityHoursPerWeek,
           "rating": body.rating, "assignments": [], "createdAt": now_iso()}
    db[C.TRAINERS].insert_one(doc)
    log_audit(db, user.name, "Add trainer", body.name, new=tid)
    return out(doc)


@router.put("/people/trainers/{tid}")
def edit_trainer(tid: str, body: TrainerIn, db=Depends(get_db), user=Depends(require("edit"))):
    if not db[C.TRAINERS].find_one({"_id": tid}):
        raise HTTPException(404, "Not found")
    db[C.TRAINERS].update_one({"_id": tid}, {"$set": {
        "name": body.name, "email": body.email, "internal": body.internal,
        "expertise": body.expertise, "capacityHoursPerWeek": body.capacityHoursPerWeek,
        "rating": body.rating}})
    return out(db[C.TRAINERS].find_one({"_id": tid}))


@router.delete("/people/trainers/{tid}")
def delete_trainer(tid: str, db=Depends(get_db), user=Depends(require("edit"))):
    db[C.TRAINERS].delete_one({"_id": tid})
    return {"ok": True, "id": tid}


@router.post("/people/trainers/{tid}/assign")
def assign_trainer(tid: str, employeeId: str, db=Depends(get_db), user=Depends(require("assign"))):
    t = db[C.TRAINERS].find_one({"_id": tid})
    if not t:
        raise HTTPException(404, "Not found")
    db[C.TRAINERS].update_one({"_id": tid}, {"$addToSet": {"assignments": employeeId}})
    notify_employee(db, employeeId, "Trainer assigned",
                    f"{t['name']} has been assigned as your trainer.")
    return out(db[C.TRAINERS].find_one({"_id": tid}))


# --- Skills directory (CRUD) --------------------------------------------------
@router.get("/people/skills")
def skills(db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.SKILLS].find())


@router.post("/people/skills")
def add_skill(body: SkillIn, db=Depends(get_db), user=Depends(require("add"))):
    sid = next_code(db, "skill", "S")
    doc = {"_id": sid, "name": body.name, "category": body.category, "levels": body.levels}
    db[C.SKILLS].insert_one(doc)
    log_audit(db, user.name, "Add skill", body.name, new=sid)
    return out(doc)


@router.put("/people/skills/{sid}")
def edit_skill(sid: str, body: SkillIn, db=Depends(get_db), user=Depends(require("edit"))):
    if not db[C.SKILLS].find_one({"_id": sid}):
        raise HTTPException(404, "Not found")
    db[C.SKILLS].update_one({"_id": sid}, {"$set": {
        "name": body.name, "category": body.category, "levels": body.levels}})
    return out(db[C.SKILLS].find_one({"_id": sid}))


@router.delete("/people/skills/{sid}")
def delete_skill(sid: str, db=Depends(get_db), user=Depends(require("edit"))):
    db[C.SKILLS].delete_one({"_id": sid})
    return {"ok": True, "id": sid}
