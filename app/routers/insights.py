from fastapi import APIRouter, Depends, HTTPException

from .. import models
from ..database import get_db, out, out_list
from ..deps import bu_filter, current_user
from ..integrations.grok import employee_insights

router = APIRouter(tags=["insights"])
C = models


def _insight_for(db, eid):
    emp = db[C.EMPLOYEES].find_one({"_id": eid})
    if not emp:
        raise HTTPException(404, "Employee not found")
    progress = out_list(db[C.PROGRESS].find({"employeeId": eid}))
    results = out_list(db[C.RESULTS].find({"employeeId": eid}))
    return employee_insights(out(emp), progress, results)


@router.get("/insights/employee/{eid}")
def employee_insight(eid: str, db=Depends(get_db), user=Depends(current_user)):
    # employees may only see their own
    if user.role == "benchEngineer" and user.employee_id != eid:
        raise HTTPException(403, "Not permitted")
    return _insight_for(db, eid)


@router.get("/insights/me")
def my_insight(db=Depends(get_db), user=Depends(current_user)):
    if not user.employee_id:
        raise HTTPException(400, "Not an employee account")
    return _insight_for(db, user.employee_id)


@router.get("/insights/team")
def team_insights(db=Depends(get_db), user=Depends(current_user)):
    if user.role == "benchEngineer":
        raise HTTPException(403, "Not permitted")
    out_rows = []
    for e in db[C.EMPLOYEES].find(bu_filter(user)):
        out_rows.append(_insight_for(db, e["_id"]))
    return {"rows": out_rows}
