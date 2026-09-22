from fastapi import APIRouter, Depends, HTTPException

from .. import models
from ..database import get_db, log_audit, now_iso, out, out_list
from ..deps import bu_filter, current_user, require
from ..ids import next_code
from ..notify import notify_employee
from ..schemas import (BankIn, PrepAnswerIn, PrepAssignIn, PrepReviewIn, QuestionIn, PrepMaterialIn)

router = APIRouter(tags=["prep"])
C = models


# --- Question banks (upload/add questions) -----------------------------------
@router.get("/prep/banks")
def banks(db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.QUESTION_BANKS].find(bu_filter(user)))


@router.post("/prep/banks")
def create_bank(body: BankIn, db=Depends(get_db), user=Depends(require("add"))):
    bu = body.bu if user.role == "admin" else user.bu
    bid = next_code(db, "bank", "QB")
    doc = {"_id": bid, "name": body.name, "client": body.client, "role": body.role,
           "technology": body.technology, "category": body.category,
           "bu": bu, "confidentiality": body.confidentiality, "version": body.version,
           "docUrl": body.docUrl, "fileName": body.fileName, "fileType": body.fileType,
           "questions": [q.model_dump() for q in body.questions],
           "questionCount": len(body.questions), "createdBy": user.name, "createdAt": now_iso()}
    db[C.QUESTION_BANKS].insert_one(doc)
    log_audit(db, user.name, "Create question bank", body.name, new=bid)
    return out(doc)


@router.put("/prep/banks/{bid}")
def edit_bank(bid: str, body: BankIn, db=Depends(get_db), user=Depends(require("edit"))):
    if not db[C.QUESTION_BANKS].find_one({"_id": bid}):
        raise HTTPException(404, "Not found")
    db[C.QUESTION_BANKS].update_one({"_id": bid}, {"$set": {
        "name": body.name, "client": body.client, "role": body.role,
        "confidentiality": body.confidentiality, "version": body.version,
        "questions": [q.model_dump() for q in body.questions],
        "questionCount": len(body.questions)}})
    return out(db[C.QUESTION_BANKS].find_one({"_id": bid}))


@router.post("/prep/banks/{bid}/questions")
def add_questions(bid: str, questions: list[QuestionIn], db=Depends(get_db),
                  user=Depends(require("edit"))):
    bank = db[C.QUESTION_BANKS].find_one({"_id": bid})
    if not bank:
        raise HTTPException(404, "Not found")
    qs = bank.get("questions", []) + [q.model_dump() for q in questions]
    db[C.QUESTION_BANKS].update_one({"_id": bid},
        {"$set": {"questions": qs, "questionCount": len(qs)}})
    return out(db[C.QUESTION_BANKS].find_one({"_id": bid}))


@router.delete("/prep/banks/{bid}")
def delete_bank(bid: str, db=Depends(get_db), user=Depends(require("edit"))):
    db[C.QUESTION_BANKS].delete_one({"_id": bid})
    return {"ok": True, "id": bid}


# --- Prep assignments + answer review ----------------------------------------
# --- Prep MATERIALS (company-wise; visible to all bench employees) -----------
@router.get("/prep/materials")
def prep_materials(db=Depends(get_db), user=Depends(current_user)):
    """All interview-prep materials in scope, for staff and bench employees.
    Employees see everything in their BU (company-wise)."""
    if user.role == "admin":
        q = {}
    else:
        q = {"bu": user.bu}
    return out_list(db[C.PREP_MATERIALS].find(q))


@router.post("/prep/materials")
def add_prep_material(body: PrepMaterialIn, db=Depends(get_db), user=Depends(require("add"))):
    bu = body.bu if user.role == "admin" else user.bu
    mid = next_code(db, "prepmat", "PM")
    doc = {"_id": mid, "title": body.title, "client": body.client or "General",
           "type": body.type, "url": body.url, "description": body.description,
           "bu": bu, "owner": user.name, "createdAt": now_iso()}
    db[C.PREP_MATERIALS].insert_one(doc)
    log_audit(db, user.name, "Add prep material", body.title, new=mid)
    return out(doc)


@router.delete("/prep/materials/{mid}")
def delete_prep_material(mid: str, db=Depends(get_db), user=Depends(require("edit"))):
    db[C.PREP_MATERIALS].delete_one({"_id": mid})
    return {"ok": True, "id": mid}
