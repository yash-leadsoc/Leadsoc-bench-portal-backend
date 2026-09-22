from fastapi import APIRouter, Depends

from .. import models
from ..database import get_db, out, out_list
from ..deps import bu_filter, current_user
from ..integrations.calendar import google_connected

router = APIRouter(tags=["bootstrap"])
C = models


@router.get("/bootstrap")
def bootstrap(db=Depends(get_db), user=Depends(current_user)):
    is_admin = user.role == "admin"
    emps = out_list(db[C.EMPLOYEES].find(bu_filter(user)))
    emp_ids = {e["id"] for e in emps}
    assessments = out_list(db[C.ASSESSMENTS].find(bu_filter(user)))
    a_ids = {a["id"] for a in assessments}
    assignments = [out(x) for x in db[C.ASSIGNMENTS].find()
                   if x["employeeId"] in emp_ids or x["assessmentId"] in a_ids]
    results = [out(r) for r in db[C.RESULTS].find() if r["assessmentId"] in a_ids]
    mocks = [out(m) for m in db[C.MOCKS].find() if m.get("employeeId") in emp_ids]
    prep = []  # Prep Assignment removed
    notifs = out_list(db[C.NOTIFICATIONS].find({"userId": user.id}).sort("createdAt", -1))

    def scoped(coll):
        return out_list(db[coll].find(bu_filter(user)))

    return {
        "user": user.as_dict(),
        "businessUnits": out_list(db[C.BUS].find()),
        "employees": emps,
        "materials": scoped(C.MATERIALS),
        "plans": scoped(C.PLANS),
        "assessments": assessments,
        "assignments": assignments,
        "results": results,
        "questionBanks": scoped(C.QUESTION_BANKS),
        "prepAssignments": [],  # removed
        "mockInterviews": mocks,
        "panels": scoped(C.PANELS),
        "trainers": out_list(db[C.TRAINERS].find()),
        "skills": out_list(db[C.SKILLS].find()),
        "requirements": scoped(C.REQUIREMENTS),
        "candidates": out_list(db[C.CANDIDATES].find()),
        "interviews": scoped(C.INTERVIEWS),
        "deployments": scoped(C.DEPLOYMENTS),
        "notifications": notifs,
        "unreadNotifications": sum(1 for n in notifs if not n.get("read")),
        "practices": out_list(db[C.PRACTICES].find()) if is_admin else [],
        "slaRules": out_list(db[C.SLA].find()) if is_admin else [],
        "notifTemplates": out_list(db[C.TEMPLATES].find()) if is_admin else [],
        "integrations": out_list(db[C.INTEGRATIONS].find()) if is_admin else [],
        "users": (out_list(db[C.USERS].find()) if is_admin
                  else out_list(db[C.USERS].find({"bu": user.bu})) if user.role == "buHead"
                  else []),
        "auditLogs": out_list(db[C.AUDIT].find().sort("at", -1)) if is_admin else [],
        "flags": {"googleConnected": google_connected()},
    }
