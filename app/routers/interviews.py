from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from .. import models
from ..database import get_db, log_audit, now_iso, out, out_list
from ..deps import bu_filter, current_user, require
from ..ids import next_code
from ..integrations.meet import create_meeting
from ..notify import notify_employee
from ..schemas import (InterviewIn, MockIn, PanelIn, ScorecardIn, StageIn)

router = APIRouter(tags=["interviews"])
C = models


# --- Interview panels ---------------------------------------------------------
@router.get("/panels")
def list_panels(db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.PANELS].find(bu_filter(user)))


@router.post("/panels")
def create_panel(body: PanelIn, db=Depends(get_db), user=Depends(require("add"))):
    bu = body.bu if user.role == "admin" else user.bu
    pid = next_code(db, "panel", "PN")
    doc = {"_id": pid, "name": body.name, "bu": bu, "members": body.members,
           "rounds": body.rounds, "assignments": [], "createdBy": user.name,
           "createdAt": now_iso()}
    db[C.PANELS].insert_one(doc)
    log_audit(db, user.name, "Create panel", body.name, new=pid)
    return out(doc)


@router.put("/panels/{pid}")
def edit_panel(pid: str, body: PanelIn, db=Depends(get_db), user=Depends(require("edit"))):
    if not db[C.PANELS].find_one({"_id": pid}):
        raise HTTPException(404, "Not found")
    db[C.PANELS].update_one({"_id": pid}, {"$set": {
        "name": body.name, "members": body.members, "rounds": body.rounds}})
    return out(db[C.PANELS].find_one({"_id": pid}))


@router.delete("/panels/{pid}")
def delete_panel(pid: str, db=Depends(get_db), user=Depends(require("edit"))):
    db[C.PANELS].delete_one({"_id": pid})
    return {"ok": True, "id": pid}


@router.post("/panels/{pid}/assign")
def assign_panel(pid: str, employeeId: str, db=Depends(get_db), user=Depends(require("assign"))):
    panel = db[C.PANELS].find_one({"_id": pid})
    if not panel:
        raise HTTPException(404, "Not found")
    db[C.PANELS].update_one({"_id": pid}, {"$addToSet": {"assignments": employeeId}})
    return out(db[C.PANELS].find_one({"_id": pid}))


# --- Requirements + candidates ------------------------------------------------
@router.get("/interviews/requirements")
def requirements(db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.REQUIREMENTS].find(bu_filter(user)))


@router.get("/interviews/candidates")
def candidates(db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.CANDIDATES].find())


@router.post("/interviews/candidates/{cid}/stage")
def move_candidate(cid: str, body: StageIn, db=Depends(get_db), user=Depends(require("edit"))):
    doc = db[C.CANDIDATES].find_one({"_id": cid})
    if not doc:
        raise HTTPException(404, "Not found")
    old = doc.get("stage")
    db[C.CANDIDATES].update_one({"_id": cid}, {"$set": {"stage": body.stage}})
    log_audit(db, user.name, "Candidate stage", doc.get("name", cid), old, body.stage)
    return out(db[C.CANDIDATES].find_one({"_id": cid}))


# --- Interview scheduling (with Google Meet link) ----------------------------
@router.get("/interviews/schedule")
def list_schedule(db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.INTERVIEWS].find(bu_filter(user)))


@router.post("/interviews/schedule")
def schedule_interview(body: InterviewIn, db=Depends(get_db), user=Depends(require("schedule"))):
    start = body.scheduledAt
    try:
        end = (datetime.fromisoformat(start) + timedelta(minutes=body.durationMinutes)).isoformat()
    except Exception:
        end = start
    if body.meetLink:
        meeting = {"meetLink": body.meetLink, "provider": "manual"}
    else:
        meeting = create_meeting(f"Interview — {body.role}", start, end)
    # meeting = create_meeting(f"Interview — {body.role}", start, end)
    iid = next_code(db, "interview", "IV")
    doc = {"_id": iid, "candidateId": body.candidateId, "employeeId": body.employeeId,
           "panelId": body.panelId, "role": body.role, "scheduledAt": start,
           "durationMinutes": body.durationMinutes, "meetLink": meeting["meetLink"],
           "meetProvider": meeting["provider"], "status": "scheduled",
           "bu": user.bu, "createdBy": user.name, "createdAt": now_iso()}
    db[C.INTERVIEWS].insert_one(doc)
    if body.employeeId:
        notify_employee(db, body.employeeId, "Interview scheduled",
                        f"Your interview for {body.role} is set. Meet: {meeting['meetLink']}")
    log_audit(db, user.name, "Schedule interview", body.role, new=iid)
    return out(doc)


# --- Mock interviews (create / assign / schedule / scorecard) -----------------
@router.get("/mocks")
def list_mocks(db=Depends(get_db), user=Depends(current_user)):
    if user.employee_id:
        return out_list(db[C.MOCKS].find({"employeeId": user.employee_id}))
    emp_ids = {e["_id"] for e in db[C.EMPLOYEES].find(bu_filter(user), {"_id": 1})}
    return [out(m) for m in db[C.MOCKS].find() if m.get("employeeId") in emp_ids]


@router.post("/mocks")
def create_mock(body: MockIn, db=Depends(get_db), user=Depends(require("schedule"))):
    start = body.scheduledAt
    try:
        end = (datetime.fromisoformat(start) + timedelta(minutes=body.durationMinutes)).isoformat()
    except Exception:
        end = start
    if body.meetLink:
        meeting = {"meetLink": body.meetLink, "provider": "manual"}
    else:
        meeting = create_meeting(f"Mock interview — {body.role}", start, end)
    # meeting = create_meeting(f"Mock interview — {body.role}", start, end)
    mid = next_code(db, "mock", "MK")
    doc = {"_id": mid, "employeeId": body.employeeId, "panelId": body.panelId,
           "role": body.role, "scheduledAt": start, "durationMinutes": body.durationMinutes,
           "meetLink": meeting["meetLink"], "meetProvider": meeting["provider"],
           "status": "scheduled", "scorecard": None, "createdBy": user.name,
           "bu": user.bu, "createdAt": now_iso()}
    db[C.MOCKS].insert_one(doc)
    notify_employee(db, body.employeeId, "Mock interview scheduled",
                    f"Mock for {body.role} on {start}. Meet: {meeting['meetLink']}")
    log_audit(db, user.name, "Create mock", body.role, new=mid)
    return out(doc)


@router.post("/mocks/{mid}/scorecard")
def submit_scorecard(mid: str, body: ScorecardIn, db=Depends(get_db), user=Depends(require("edit"))):
    if not db[C.MOCKS].find_one({"_id": mid}):
        raise HTTPException(404, "Not found")
    db[C.MOCKS].update_one({"_id": mid}, {"$set": {
        "scorecard": body.model_dump(), "status": "completed"}})
    return out(db[C.MOCKS].find_one({"_id": mid}))


@router.get("/interviews/mine")
def my_interviews(db=Depends(get_db), user=Depends(current_user)):
    """Interviews scheduled for the signed-in employee."""
    if not user.employee_id:
        return []
    return out_list(db[C.INTERVIEWS].find({"employeeId": user.employee_id}))
