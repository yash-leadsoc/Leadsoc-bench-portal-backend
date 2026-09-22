from fastapi import APIRouter, Depends, HTTPException

from .. import models
from ..database import get_db, log_audit, now_iso, out, out_list
from ..deps import bu_filter, current_user, require
from ..ids import next_code
from ..notify import notify_employee
from ..schemas import MaterialIn, PlanIn, ProgressIn, ProgressLogIn, ModuleDoneIn, NoteIn

router = APIRouter(tags=["learning"])
C = models


# --- Materials (replaces courses; type = pdf/video/link/doc/other) -----------
@router.get("/materials")
def list_materials(db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.MATERIALS].find(bu_filter(user)))


@router.post("/materials")
def add_material(body: MaterialIn, db=Depends(get_db), user=Depends(require("add"))):
    bu = body.bu if user.role == "admin" else user.bu
    mid = next_code(db, "material", "M")
    doc = {"_id": mid, "title": body.title, "type": body.type, "url": body.url,
           "downloadUrl": body.downloadUrl, "fileName": body.fileName, "fileType": body.fileType,
           "skill": body.skill, "bu": bu, "owner": user.name,
           "description": body.description, "createdAt": now_iso()}
    db[C.MATERIALS].insert_one(doc)
    log_audit(db, user.name, "Add material", body.title, new=mid)
    return out(doc)


@router.put("/materials/{mid}")
def edit_material(mid: str, body: MaterialIn, db=Depends(get_db), user=Depends(require("edit"))):
    if not db[C.MATERIALS].find_one({"_id": mid}):
        raise HTTPException(404, "Not found")
    db[C.MATERIALS].update_one({"_id": mid}, {"$set": {
        "title": body.title, "type": body.type, "url": body.url,
        "downloadUrl": body.downloadUrl, "fileName": body.fileName, "fileType": body.fileType,
        "skill": body.skill, "description": body.description}})
    return out(db[C.MATERIALS].find_one({"_id": mid}))


@router.delete("/materials/{mid}")
def delete_material(mid: str, db=Depends(get_db), user=Depends(require("edit"))):
    doc = db[C.MATERIALS].find_one({"_id": mid})
    if not doc:
        raise HTTPException(404, "Not found")
    db[C.MATERIALS].delete_one({"_id": mid})
    log_audit(db, user.name, "Delete material", doc.get("title", mid))
    return {"ok": True, "id": mid}


# --- Training plans (full CRUD, detailed) ------------------------------------
@router.get("/plans")
def list_plans(db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.PLANS].find(bu_filter(user)))


@router.get("/plans/{pid}")
def get_plan(pid: str, db=Depends(get_db), user=Depends(current_user)):
    doc = db[C.PLANS].find_one({"_id": pid})
    if not doc:
        raise HTTPException(404, "Not found")
    return out(doc)


# @router.post("/plans")
# def create_plan(body: PlanIn, db=Depends(get_db), user=Depends(require("add"))):
#     bu = body.bu if user.role == "admin" else user.bu
#     pid = next_code(db, "plan", "PL")
#     doc = {"_id": pid, "name": body.name, "bu": bu, "targetRole": body.targetRole,
#            "description": body.description, "durationHours": body.durationHours,
#            "skills": body.skills, "items": [i.model_dump() for i in body.items],
#            "createdBy": user.name, "createdAt": now_iso()}
#     db[C.PLANS].insert_one(doc)
#     log_audit(db, user.name, "Create plan", body.name, new=pid)
#     return out(doc)
#
#
# @router.put("/plans/{pid}")
# def edit_plan(pid: str, body: PlanIn, db=Depends(get_db), user=Depends(require("edit"))):
#     if not db[C.PLANS].find_one({"_id": pid}):
#         raise HTTPException(404, "Not found")
#     db[C.PLANS].update_one({"_id": pid}, {"$set": {
#         "name": body.name, "targetRole": body.targetRole, "description": body.description,
#         "durationHours": body.durationHours, "skills": body.skills,
#         "items": [i.model_dump() for i in body.items]}})
#     return out(db[C.PLANS].find_one({"_id": pid}))


@router.post("/plans")
def create_plan(body: PlanIn, db=Depends(get_db), user=Depends(require("add"))):
    bu = body.bu if user.role == "admin" else user.bu
    pid = next_code(db, "plan", "PL")
    skills = body.skills or [s.skill for s in body.skillsCovered if s.skill]
    doc = {"_id": pid, "name": body.name, "bu": bu, "targetRole": body.targetRole,
           "primarySkill": body.primarySkill, "category": body.category,
           "difficulty": body.difficulty, "durationValue": body.durationValue,
           "durationUnit": body.durationUnit, "durationHours": body.durationHours or body.durationValue,
           "skills": skills, "skillsCovered": [s.model_dump() for s in body.skillsCovered],
           "items": [i.model_dump() for i in body.items],
           "description": body.description, "expectedOutcome": body.expectedOutcome,
           "trainer": body.trainer, "status": body.status,
           "createdBy": user.name, "createdAt": now_iso(), "assessmentIds": body.assessmentIds
           }
    db[C.PLANS].insert_one(doc)
    log_audit(db, user.name, "Create plan", body.name, new=pid)
    return out(doc)


@router.put("/plans/{pid}")
def edit_plan(pid: str, body: PlanIn, db=Depends(get_db), user=Depends(require("edit"))):
    if not db[C.PLANS].find_one({"_id": pid}):
        raise HTTPException(404, "Not found")
    skills = body.skills or [s.skill for s in body.skillsCovered if s.skill]
    db[C.PLANS].update_one({"_id": pid}, {"$set": {
        "name": body.name, "targetRole": body.targetRole, "primarySkill": body.primarySkill,
        "category": body.category, "difficulty": body.difficulty,
        "durationValue": body.durationValue, "durationUnit": body.durationUnit,
        "durationHours": body.durationHours or body.durationValue,
        "skills": skills, "skillsCovered": [s.model_dump() for s in body.skillsCovered],
        "items": [i.model_dump() for i in body.items], "description": body.description, "assessmentIds": body.assessmentIds,
        "expectedOutcome": body.expectedOutcome, "trainer": body.trainer, "status": body.status}})
    return out(db[C.PLANS].find_one({"_id": pid}))


@router.delete("/plans/{pid}")
def delete_plan(pid: str, db=Depends(get_db), user=Depends(require("edit"))):
    doc = db[C.PLANS].find_one({"_id": pid})
    if not doc:
        raise HTTPException(404, "Not found")
    db[C.PLANS].delete_one({"_id": pid})
    log_audit(db, user.name, "Delete plan", doc.get("name", pid))
    return {"ok": True, "id": pid}


@router.post("/plans/{pid}/assign")
def assign_plan(pid: str, employeeId: str, db=Depends(get_db), user=Depends(require("assign"))):
    plan = db[C.PLANS].find_one({"_id": pid})
    if not plan:
        raise HTTPException(404, "Plan not found")
    # for item in plan.get("items", []):
    #     if not item.get("materialId"):
    #         continue
    #     db[C.PROGRESS].update_one(
    #         {"employeeId": employeeId, "planId": pid, "materialId": item["materialId"]},
    #         {"$setOnInsert": {"status": "notStarted", "pct": 0, "updatedAt": now_iso(),
    #                           "title": item.get("title", "")}}, upsert=True)
    for idx, item in enumerate(plan.get("items", [])):
        key = item.get("materialId") or f"mod:{item.get('order', idx)}"
        db[C.PROGRESS].update_one(
            {"employeeId": employeeId, "planId": pid, "materialId": key},
            {"$setOnInsert": {"status": "notStarted", "pct": 0, "updatedAt": now_iso(),
                              "assignedAt": now_iso(), "title": item.get("title", "")}}, upsert=True)
    db[C.EMPLOYEES].update_one({"_id": employeeId}, {"$set": {"status": "trainingInProgress"}})
    notify_employee(db, employeeId, "Training plan assigned",
                    f"You have been assigned the plan: {plan['name']}")
    log_audit(db, user.name, "Assign plan", plan["name"], new=employeeId)
    return {"ok": True, "planId": pid, "employeeId": employeeId}


# --- Training progress (per-employee detail) ---------------------------------
@router.get("/training/progress")
def all_progress(db=Depends(get_db), user=Depends(current_user)):
    emp_ids = {e["_id"] for e in db[C.EMPLOYEES].find(bu_filter(user), {"_id": 1})}
    rows = [out(p) for p in db[C.PROGRESS].find() if p.get("employeeId") in emp_ids]
    # roll up per employee
    summary = {}
    for p in rows:
        s = summary.setdefault(p["employeeId"], {"employeeId": p["employeeId"],
                                                 "items": 0, "avgPct": 0, "completed": 0})
        s["items"] += 1
        s["avgPct"] += p.get("pct", 0)
        if p.get("status") == "completed":
            s["completed"] += 1
    for s in summary.values():
        s["avgPct"] = round(s["avgPct"] / s["items"]) if s["items"] else 0
    return {"rows": rows, "byEmployee": list(summary.values())}


@router.get("/training/progress/{eid}")
def employee_progress(eid: str, db=Depends(get_db), user=Depends(current_user)):
    emp = db[C.EMPLOYEES].find_one({"_id": eid})
    if not emp:
        raise HTTPException(404, "Employee not found")
    items = out_list(db[C.PROGRESS].find({"employeeId": eid}))
    # enrich each with material info
    for it in items:
        m = db[C.MATERIALS].find_one({"_id": it.get("materialId")})
        if m:
            it["material"] = out(m)
    avg = round(sum(i.get("pct", 0) for i in items) / len(items)) if items else 0
    return {"employee": out(emp), "items": items, "avgPct": avg,
            "completed": sum(1 for i in items if i.get("status") == "completed")}


@router.post("/training/progress")
def upsert_progress(body: ProgressIn, db=Depends(get_db), user=Depends(current_user)):
    key = {"employeeId": body.employeeId, "planId": body.planId, "materialId": body.materialId}
    db[C.PROGRESS].update_one(key, {"$set": {
        "status": body.status, "pct": body.pct, "updatedAt": now_iso()}}, upsert=True)
    emp = db[C.EMPLOYEES].find_one({"_id": body.employeeId})
    if emp:
        from .readiness_calc import compute_readiness
        compute_readiness(db, emp)
    return {"ok": True}


@router.get("/training/plans/mine")
def my_training_plans(db=Depends(get_db), user=Depends(current_user)):
    eid = user.employee_id
    if not eid:
        return {"plans": []}
    prog = list(db[C.PROGRESS].find({"employeeId": eid}))
    done = {(p.get("planId"), p.get("materialId")): p for p in prog}
    plan_ids = sorted({p.get("planId") for p in prog if p.get("planId")})
    plans = []
    for pid in plan_ids:
        plan = db[C.PLANS].find_one({"_id": pid})
        if not plan:
            continue
        mods = sorted(plan.get("items", []), key=lambda x: (x.get("week", 0), x.get("order", 0)))
        modules, completed = [], 0
        for idx, it in enumerate(mods):
            key = it.get("materialId") or f"mod:{it.get('order', idx)}"
            pr = done.get((pid, key))
            pct = pr.get("pct", 0) if pr else 0
            mat = db[C.MATERIALS].find_one({"_id": it.get("materialId")}) if it.get("materialId") else None
            if pct >= 100:
                completed += 1
            modules.append({
                "key": key, "title": it.get("title") or (mat.get("title") if mat else "Module"),
                "week": it.get("week", 0), "duration": it.get("duration", ""),
                "assessmentType": it.get("assessmentType", "None"),
                "materialId": it.get("materialId", ""),
                "materialTitle": mat.get("title") if mat else None,
                "materialType": mat.get("type") if mat else None,
                "url": mat.get("url") if mat else None,
                "downloadUrl": mat.get("downloadUrl") if mat else None,
                "pct": pct, "completed": pct >= 100,
            })
        total = len(modules)
        plans.append({
            "id": pid, "name": plan.get("name"), "targetRole": plan.get("targetRole"),
            "primarySkill": plan.get("primarySkill"), "category": plan.get("category"),
            "difficulty": plan.get("difficulty"),
            "durationValue": plan.get("durationValue"), "durationUnit": plan.get("durationUnit"),
            "description": plan.get("description"), "expectedOutcome": plan.get("expectedOutcome"),
            "modules": modules, "total": total, "completed": completed,
            "pct": round(100 * completed / total) if total else 0,
        })
    return {"plans": plans}


@router.post("/training/module/complete")
def complete_module(body: ModuleDoneIn, db=Depends(get_db), user=Depends(current_user)):
    eid = user.employee_id
    if not eid:
        raise HTTPException(400, "Not an employee account")
    if not (body.planId and body.key):
        raise HTTPException(400, "planId and key are required")
    pct = 100 if body.completed else 0
    status = "completed" if body.completed else "inProgress"
    db[C.PROGRESS].update_one(
        {"employeeId": eid, "planId": body.planId, "materialId": body.key},
        {"$set": {"pct": pct, "status": status, "title": body.title, "updatedAt": now_iso()}},
        upsert=True)
    db[C.PROGRESS_LOGS].insert_one({
        "employeeId": eid, "materialId": body.key, "planId": body.planId,
        "note": ("Completed: " if body.completed else "Reopened: ") + (body.title or "module"),
        "pct": pct, "date": now_iso()[:10], "at": now_iso()})
    emp = db[C.EMPLOYEES].find_one({"_id": eid})
    if emp:
        from .readiness_calc import compute_readiness
        compute_readiness(db, emp)
    return {"ok": True, "completed": body.completed}


@router.get("/training/mine")
def my_training(db=Depends(get_db), user=Depends(current_user)):
    """The signed-in employee's own training progress, enriched with material."""
    eid = user.employee_id
    if not eid:
        return {"items": [], "avgPct": 0, "completed": 0}
    items = out_list(db[C.PROGRESS].find({"employeeId": eid}))
    for it in items:
        m = db[C.MATERIALS].find_one({"_id": it.get("materialId")})
        if m:
            it["material"] = out(m)
    avg = round(sum(i.get("pct", 0) for i in items) / len(items)) if items else 0
    return {"items": items, "avgPct": avg,
            "completed": sum(1 for i in items if i.get("status") == "completed")}


@router.get("/plans/{pid}/assignments")
def plan_assignments(pid: str, db=Depends(get_db), user=Depends(current_user)):
    """Employees assigned to a plan, with their per-plan average progress."""
    plan = db[C.PLANS].find_one({"_id": pid})
    if not plan:
        raise HTTPException(404, "Plan not found")
    by_emp = {}
    for p in db[C.PROGRESS].find({"planId": pid}):
        s = by_emp.setdefault(p["employeeId"], {"items": 0, "sum": 0, "completed": 0})
        s["items"] += 1
        s["sum"] += p.get("pct", 0)
        if p.get("status") == "completed":
            s["completed"] += 1
    rows = []
    for eid, s in by_emp.items():
        emp = db[C.EMPLOYEES].find_one({"_id": eid})
        rows.append({"employeeId": eid, "name": emp.get("name") if emp else eid,
                     "bu": emp.get("bu") if emp else None,
                     "items": s["items"], "completed": s["completed"],
                     "avgPct": round(s["sum"] / s["items"]) if s["items"] else 0})
    return {"plan": out(plan), "rows": rows}


@router.post("/training/progress/log")
def log_progress(body: ProgressLogIn, db=Depends(get_db), user=Depends(current_user)):
    """Employee logs what they did today; updates the material's % and is
    visible date-wise to BU/TA."""
    eid = user.employee_id
    if not eid:
        raise HTTPException(400, "Not an employee account")
    day = body.date or now_iso()[:10]
    db[C.PROGRESS_LOGS].insert_one({
        "employeeId": eid, "materialId": body.materialId, "planId": body.planId,
        "note": body.note, "pct": body.pct, "date": day, "at": now_iso()})
    # update the material's progress row (create if missing)
    if body.materialId:
        key = {"employeeId": eid, "materialId": body.materialId}
        if body.planId:
            key["planId"] = body.planId
        status = "completed" if body.pct >= 100 else "inProgress"
        db[C.PROGRESS].update_one(key, {"$set": {
            "pct": body.pct, "status": status, "updatedAt": now_iso()}}, upsert=True)
    emp = db[C.EMPLOYEES].find_one({"_id": eid})
    if emp:
        from .readiness_calc import compute_readiness
        compute_readiness(db, emp)
    return {"ok": True, "date": day}


@router.get("/training/progress/{eid}/logs")
def progress_logs(eid: str, db=Depends(get_db), user=Depends(current_user)):
    """Date-wise daily progress logs for an employee (BU/TA/own)."""
    if user.role == "benchEngineer" and user.employee_id != eid:
        raise HTTPException(403, "Not permitted")
    logs = out_list(db[C.PROGRESS_LOGS].find({"employeeId": eid}).sort("at", -1))
    for lg in logs:
        m = db[C.MATERIALS].find_one({"_id": lg.get("materialId")})
        if m:
            lg["materialTitle"] = m.get("title")
    return {"rows": logs}


@router.get("/training/mine/logs")
def my_logs(db=Depends(get_db), user=Depends(current_user)):
    if not user.employee_id:
        return {"rows": []}
    return progress_logs(user.employee_id, db, user)


@router.get("/training/plans/mine/{pid}")
def my_training_plan_detail(pid: str, db=Depends(get_db), user=Depends(current_user)):
    from datetime import date as _date, timedelta
    eid = user.employee_id
    if not eid:
        raise HTTPException(400, "Not an employee account")
    plan = db[C.PLANS].find_one({"_id": pid})
    if not plan:
        raise HTTPException(404, "Plan not found")
    prog = list(db[C.PROGRESS].find({"employeeId": eid, "planId": pid}))
    if not prog:
        raise HTTPException(403, "Plan not assigned to you")
    done = {p.get("materialId"): p for p in prog}

    mods = sorted(plan.get("items", []), key=lambda x: (x.get("week", 0), x.get("order", 0)))
    modules, completed = [], 0
    for idx, it in enumerate(mods):
        key = it.get("materialId") or f"mod:{it.get('order', idx)}"
        pr = done.get(key)
        pct = pr.get("pct", 0) if pr else 0
        mat = db[C.MATERIALS].find_one({"_id": it.get("materialId")}) if it.get("materialId") else None
        if pct >= 100:
            completed += 1
        modules.append({
            "key": key, "title": it.get("title") or (mat.get("title") if mat else "Module"),
            "week": it.get("week", 0), "duration": it.get("duration", ""),
            "assessmentType": it.get("assessmentType", "None"),
            "materialId": it.get("materialId", ""),
            "materialTitle": mat.get("title") if mat else None,
            "materialType": mat.get("type") if mat else None,
            "url": mat.get("url") if mat else None,
            "downloadUrl": mat.get("downloadUrl") if mat else None,
            "pct": pct, "completed": pct >= 100,
        })

    assessments = []
    for aid in plan.get("assessmentIds", []):
        a = db[C.ASSESSMENTS].find_one({"_id": aid})
        if not a:
            continue
        res = sorted(db[C.RESULTS].find({"assessmentId": aid, "employeeId": eid}),
                     key=lambda r: r.get("attemptNumber", 0), reverse=True)
        asg = db[C.ASSIGNMENTS].find_one({"assessmentId": aid, "employeeId": eid})
        if res:
            r = res[0]
            assessments.append({"id": aid, "name": a.get("name"), "status": "completed",
                                "scoreMarks": r.get("scoreMarks"), "totalMarks": r.get("totalMarks"),
                                "passed": r.get("passed")})
        else:
            assessments.append({"id": aid, "name": a.get("name"),
                                "status": "pending" if asg else "notStarted"})

    notes = sorted(out_list(db[C.NOTES].find({"employeeId": eid, "planId": pid})),
                   key=lambda n: n.get("at", ""), reverse=True)

    def _pd(s):
        try: return _date.fromisoformat(str(s)[:10])
        except Exception: return None
    starts = [d for d in (_pd(p.get("assignedAt") or p.get("updatedAt")) for p in prog) if d]
    start = min(starts) if starts else None
    unit, val = plan.get("durationUnit", "days"), int(plan.get("durationValue") or 0)
    days = val * 7 if unit == "weeks" else (max(1, round(val / 8)) if unit == "hours" else val)
    end = start + timedelta(days=days) if (start and days) else None

    total = len(modules)
    return {"id": pid, "name": plan.get("name"), "targetRole": plan.get("targetRole"),
            "primarySkill": plan.get("primarySkill"), "category": plan.get("category"),
            "difficulty": plan.get("difficulty"), "skillsCovered": plan.get("skillsCovered", []),
            "durationValue": plan.get("durationValue"), "durationUnit": plan.get("durationUnit"),
            "description": plan.get("description"), "expectedOutcome": plan.get("expectedOutcome"),
            "modules": modules, "total": total, "completed": completed,
            "pct": round(100 * completed / total) if total else 0,
            "assessments": assessments, "notes": notes,
            "startDate": start.isoformat() if start else None,
            "expectedEndDate": end.isoformat() if end else None}


@router.post("/training/plans/{pid}/notes")
def add_training_note(pid: str, body: NoteIn, db=Depends(get_db), user=Depends(current_user)):
    eid = user.employee_id
    if not eid:
        raise HTTPException(400, "Not an employee account")
    if not db[C.PLANS].find_one({"_id": pid}):
        raise HTTPException(404, "Plan not found")
    nid = next_code(db, "note", "NT")
    doc = {"_id": nid, "employeeId": eid, "planId": pid, "title": body.title,
           "body": body.body, "date": now_iso()[:10], "at": now_iso()}
    db[C.NOTES].insert_one(doc)
    return out(doc)


@router.delete("/training/notes/{nid}")
def delete_training_note(nid: str, db=Depends(get_db), user=Depends(current_user)):
    note = db[C.NOTES].find_one({"_id": nid})
    if not note or note.get("employeeId") != user.employee_id:
        raise HTTPException(404, "Not found")
    db[C.NOTES].delete_one({"_id": nid})
    return {"ok": True, "id": nid}
