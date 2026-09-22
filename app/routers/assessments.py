from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from .. import models
from ..database import get_db, log_audit, now_iso, out, out_list
from ..deps import bu_filter, current_user, require
from ..ids import next_code
from ..notify import notify_employee
from ..schemas import AssessmentIn, AssignIn, SubmitIn

router = APIRouter(tags=["assessments"])
C = models


@router.get("/assessments")
def list_assessments(db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.ASSESSMENTS].find(bu_filter(user)))


@router.get("/assessments/{aid}")
def get_assessment(aid: str, db=Depends(get_db), user=Depends(current_user)):
    doc = db[C.ASSESSMENTS].find_one({"_id": aid})
    if not doc:
        raise HTTPException(404, "Not found")
    return out(doc)


@router.post("/assessments")
def create_assessment(body: AssessmentIn, db=Depends(get_db), user=Depends(require("add"))):
    bu = body.bu if user.role == "admin" else user.bu
    aid = next_code(db, "assessment", "A")
    doc = {"_id": aid, "name": body.name, "bu": bu, "practice": body.practice,
           "skill": body.skill, "topic": body.topic, "difficulty": body.difficulty,
           "durationMinutes": body.durationMinutes, "passingScorePct": body.passingScorePct,
           "maxAttempts": body.maxAttempts, "status": body.status, "createdBy": user.name,
           "createdAt": now_iso(), "questions": [q.model_dump() for q in body.questions]}
    db[C.ASSESSMENTS].insert_one(doc)
    log_audit(db, user.name, "Create assessment", body.name, new=aid)
    return out(doc)


@router.put("/assessments/{aid}")
def update_assessment(aid: str, body: AssessmentIn, db=Depends(get_db), user=Depends(require("edit"))):
    if not db[C.ASSESSMENTS].find_one({"_id": aid}):
        raise HTTPException(404, "Not found")
    db[C.ASSESSMENTS].update_one({"_id": aid}, {"$set": {
        "name": body.name, "practice": body.practice, "skill": body.skill,
        "topic": body.topic, "difficulty": body.difficulty,
        "durationMinutes": body.durationMinutes, "passingScorePct": body.passingScorePct,
        "maxAttempts": body.maxAttempts, "status": body.status,
        "questions": [q.model_dump() for q in body.questions]}})
    return out(db[C.ASSESSMENTS].find_one({"_id": aid}))


@router.delete("/assessments/{aid}")
def delete_assessment(aid: str, db=Depends(get_db), user=Depends(require("edit"))):
    db[C.ASSESSMENTS].delete_one({"_id": aid})
    return {"ok": True, "id": aid}


@router.get("/assessments/{aid}/assignments")
def assignments_for(aid: str, db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.ASSIGNMENTS].find({"assessmentId": aid}))


@router.get("/assessments/{aid}/results")
def results_for(aid: str, db=Depends(get_db), user=Depends(current_user)):
    return out_list(db[C.RESULTS].find({"assessmentId": aid}))


@router.post("/assessments/{aid}/assign")
def assign(aid: str, body: AssignIn, db=Depends(get_db), user=Depends(require("assign"))):
    a = db[C.ASSESSMENTS].find_one({"_id": aid})
    if not a:
        raise HTTPException(404, "Not found")
    base = db[C.ASSIGNMENTS].count_documents({})
    made = []
    for i, eid in enumerate(body.employeeIds):
        doc = {"_id": f"ASG{base + i + 1}", "assessmentId": aid, "employeeId": eid,
               "assignedBy": user.name, "assignedAt": now_iso(), "dueDate": body.dueDate,
               "attemptsUsed": 0, "attemptLimit": a.get("maxAttempts", 2), "status": "assigned"}
        db[C.ASSIGNMENTS].insert_one(doc)
        made.append(out(doc))
        db[C.EMPLOYEES].update_one({"_id": eid}, {"$set": {"status": "assessmentDue"}})
        notify_employee(db, eid, "New assessment assigned",
                        f"'{a['name']}' is due {body.dueDate or 'soon'}.")
    log_audit(db, user.name, "Assign assessment", a["name"], new=f"{len(made)} employees")
    return made


@router.get("/assignments")
def all_assignments(db=Depends(get_db), user=Depends(current_user)):
    emp_ids = {e["_id"] for e in db[C.EMPLOYEES].find(bu_filter(user), {"_id": 1})}
    return [out(x) for x in db[C.ASSIGNMENTS].find() if x["employeeId"] in emp_ids]


@router.get("/assignments/mine")
def my_assignments(db=Depends(get_db), user=Depends(current_user)):
    if not user.employee_id:
        return []
    return out_list(db[C.ASSIGNMENTS].find({"employeeId": user.employee_id}))


@router.post("/assignments/{asg_id}/submit")
def submit(asg_id: str, body: SubmitIn, db=Depends(get_db), user=Depends(current_user)):
    asg = db[C.ASSIGNMENTS].find_one({"_id": asg_id})
    if not asg:
        raise HTTPException(404, "Assignment not found")
    limit = asg.get("attemptLimit", 2)
    used = asg.get("attemptsUsed", 0)
    if used >= limit:
        raise HTTPException(400, "No attempts left")
    a = db[C.ASSESSMENTS].find_one({"_id": asg["assessmentId"]})
    pass_pct = a.get("passingScorePct", 60) if a else 60
    passed = body.totalMarks > 0 and (body.scoreMarks / body.totalMarks) * 100 >= pass_pct
    attempts = used + 1
    # If passed, or no attempts remain, mark completed; otherwise allow a retry.
    new_status = "completed" if (passed or attempts >= limit) else "assessmentDue"
    db[C.ASSIGNMENTS].update_one({"_id": asg_id},
        {"$set": {"attemptsUsed": attempts, "status": new_status}})
    rid = f"R{100 + db[C.RESULTS].count_documents({}) + 1}"
    res = {"_id": rid, "assessmentId": asg["assessmentId"], "assignmentId": asg_id,
           "employeeId": asg["employeeId"], "scoreMarks": body.scoreMarks,
           "totalMarks": body.totalMarks, "correct": body.correct, "incorrect": body.incorrect,
           "timeTakenSeconds": body.timeTakenSeconds, "passed": passed,
           "answers": body.answers,
           "submittedAt": now_iso(), "attemptNumber": attempts}
    db[C.RESULTS].insert_one(res)
    emp = db[C.EMPLOYEES].find_one({"_id": asg["employeeId"]})
    if emp:
        from .readiness_calc import compute_readiness
        compute_readiness(db, emp)
    return out(res)


@router.get("/assignments/{asg_id}/result")
def my_assignment_result(asg_id: str, db=Depends(get_db), user=Depends(current_user)):
    asg = db[C.ASSIGNMENTS].find_one({"_id": asg_id})
    if not asg:
        raise HTTPException(404, "Assignment not found")
    res = list(db[C.RESULTS].find({"assignmentId": asg_id}).sort("attemptNumber", -1))
    return {"attemptsUsed": asg.get("attemptsUsed", 0),
            "attemptLimit": asg.get("attemptLimit", 2),
            "status": asg.get("status"),
            "results": [out(r) for r in res]}

@router.get("/results")
def all_results(db=Depends(get_db), user=Depends(current_user)):
    vis = {a["_id"] for a in db[C.ASSESSMENTS].find(bu_filter(user), {"_id": 1})}
    return [out(r) for r in db[C.RESULTS].find() if r["assessmentId"] in vis]
