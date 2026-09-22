import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from .. import models
from ..database import get_db, out, out_list
from ..deps import bu_filter, current_user, enterprise
from ..integrations.grok import employee_insights

router = APIRouter(tags=["reports"])
C = models


def _emp_ids(db, user):
    return {e["_id"] for e in db[C.EMPLOYEES].find(bu_filter(user), {"_id": 1})}


@router.get("/reports/overview")
def overview(db=Depends(get_db), user=Depends(current_user)):
    f = bu_filter(user)
    emp_ids = _emp_ids(db, user)
    results = [r for r in db[C.RESULTS].find() if r["employeeId"] in emp_ids]
    passed = sum(1 for r in results if r.get("passed"))
    return {
        "employees": db[C.EMPLOYEES].count_documents(f),
        "materials": db[C.MATERIALS].count_documents(f),
        "plans": db[C.PLANS].count_documents(f),
        "assessments": db[C.ASSESSMENTS].count_documents(f),
        "assignments": len([1 for a in db[C.ASSIGNMENTS].find() if a["employeeId"] in emp_ids]),
        "questionBanks": db[C.QUESTION_BANKS].count_documents(f),
        "mocks": len([1 for m in db[C.MOCKS].find() if m.get("employeeId") in emp_ids]),
        "trainers": db[C.TRAINERS].count_documents({}),
        "panels": db[C.PANELS].count_documents(f),
        "skills": db[C.SKILLS].count_documents({}),
        "assessmentPassRatePct": round(100 * passed / len(results)) if results else 0,
    }


@router.get("/reports/bench")
def bench_report(db=Depends(get_db), user=Depends(current_user)):
    today = date.today()
    dist = {b: 0 for b in ["0-15", "16-30", "31-45", "46-60", ">60"]}
    ready = {"deployable": 0, "developing": 0, "early": 0}
    rows = []
    for e in db[C.EMPLOYEES].find(bu_filter(user)):
        age = (today - date.fromisoformat(str(e["benchStart"])[:10])).days
        b = "0-15" if age <= 15 else "16-30" if age <= 30 else "31-45" if age <= 45 \
            else "46-60" if age <= 60 else ">60"
        dist[b] += 1
        r = e.get("readinessScore", 0)
        ready["deployable" if r >= 80 else "developing" if r >= 50 else "early"] += 1
        rows.append({"id": e["_id"], "name": e["name"], "bu": e.get("bu"),
                     "ageDays": age, "readiness": r, "status": e["status"]})
    return {"ageing": dist, "readiness": ready, "rows": rows}


@router.get("/reports/training")
def training_report(db=Depends(get_db), user=Depends(current_user)):
    emp_ids = _emp_ids(db, user)
    per_emp = {}
    for p in db[C.PROGRESS].find():
        if p["employeeId"] not in emp_ids:
            continue
        s = per_emp.setdefault(p["employeeId"], {"employeeId": p["employeeId"],
                                                 "items": 0, "sum": 0, "completed": 0})
        s["items"] += 1
        s["sum"] += p.get("pct", 0)
        if p.get("status") == "completed":
            s["completed"] += 1
    rows = []
    for s in per_emp.values():
        rows.append({"employeeId": s["employeeId"],
                     "avgPct": round(s["sum"] / s["items"]) if s["items"] else 0,
                     "items": s["items"], "completed": s["completed"]})
    return {"rows": rows}


@router.get("/reports/assessments")
def assessment_report(db=Depends(get_db), user=Depends(current_user)):
    rows = []
    for a in db[C.ASSESSMENTS].find(bu_filter(user)):
        res = list(db[C.RESULTS].find({"assessmentId": a["_id"]}))
        passed = sum(1 for r in res if r.get("passed"))
        rows.append({"id": a["_id"], "name": a["name"], "attempts": len(res),
                     "passed": passed,
                     "passRatePct": round(100 * passed / len(res)) if res else 0})
    return {"rows": rows}


@router.get("/reports/interviews")
def interview_report(db=Depends(get_db), user=Depends(current_user)):
    funnel = {}
    for c in db[C.CANDIDATES].find():
        funnel[c.get("stage")] = funnel.get(c.get("stage"), 0) + 1
    emp_ids = _emp_ids(db, user)
    mocks = [m for m in db[C.MOCKS].find() if m.get("employeeId") in emp_ids]
    completed = [m for m in mocks if m.get("status") == "completed"]
    return {"funnel": funnel, "mocks": len(mocks), "mocksCompleted": len(completed)}


@router.get("/reports/trainers")
def trainer_report(db=Depends(get_db), user=Depends(current_user)):
    rows = []
    for t in db[C.TRAINERS].find():
        rows.append({"id": t["_id"], "name": t["name"],
                     "assigned": len(t.get("assignments", [])),
                     "capacity": t.get("capacityHoursPerWeek", 0),
                     "rating": t.get("rating", 0)})
    return {"rows": rows}


@router.get("/reports/employee/{eid}")
def employee_360(eid: str, db=Depends(get_db), user=Depends(current_user)):
    if user.role == "benchEngineer" and user.employee_id != eid:
        raise HTTPException(403, "Not permitted")
    emp = db[C.EMPLOYEES].find_one({"_id": eid})
    if not emp:
        raise HTTPException(404, "Not found")
    progress = out_list(db[C.PROGRESS].find({"employeeId": eid}))
    results = out_list(db[C.RESULTS].find({"employeeId": eid}))
    mocks = out_list(db[C.MOCKS].find({"employeeId": eid}))
    prep = out_list(db[C.PREP].find({"employeeId": eid}))
    insight = employee_insights(out(emp), progress, results)
    return {"employee": out(emp), "progress": progress, "results": results,
            "mocks": mocks, "prep": prep, "insight": insight}


# --- CSV exports -------------------------------------------------------------
def _csv(rows, headers):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


@router.get("/export/{name}.csv")
def export_csv(name: str, db=Depends(get_db), user=Depends(current_user)):
    if user.role == "benchEngineer":
        raise HTTPException(403, "Not permitted")
    if name == "employees":
        rows = [out(e) for e in db[C.EMPLOYEES].find(bu_filter(user))]
        csv_text = _csv(rows, ["id", "name", "email", "bu", "practice", "status",
                               "readinessScore", "targetRole", "benchStart"])
    elif name == "readiness":
        rows = []
        for e in db[C.EMPLOYEES].find(bu_filter(user)):
            rows.append({"id": e["_id"], "name": e["name"], "bu": e.get("bu"),
                         "readiness": e.get("readinessScore", 0), "status": e["status"]})
        csv_text = _csv(rows, ["id", "name", "bu", "readiness", "status"])
    elif name == "results":
        emp_ids = _emp_ids(db, user)
        rows = [out(r) for r in db[C.RESULTS].find() if r["employeeId"] in emp_ids]
        csv_text = _csv(rows, ["id", "assessmentId", "employeeId", "scoreMarks",
                               "totalMarks", "passed", "submittedAt"])
    elif name == "training-progress":
        emp_ids = _emp_ids(db, user)
        rows = [out(p) for p in db[C.PROGRESS].find() if p["employeeId"] in emp_ids]
        csv_text = _csv(rows, ["employeeId", "planId", "materialId", "status", "pct", "updatedAt"])
    else:
        raise HTTPException(404, "Unknown export")
    return Response(content=csv_text, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}.csv"'})


@router.get("/dashboard/kpis")
def dashboard_kpis(db=Depends(get_db), user=Depends(current_user)):
    """Org-level (admin) or BU-level KPIs computed from live data."""
    from datetime import date as _date
    from ..profile_calc import compute_profile_completion
    # scope = {} if user.role == "admin" else {"bu": user.bu}
    scope = {} if enterprise(user) else {"bu": user.bu}
    emps = list(db[C.EMPLOYEES].find(scope))
    today = _date.today()

    def age(e):
        try:
            return (today - _date.fromisoformat(str(e.get("benchStart"))[:10])).days
        except Exception:
            return 0

    total = len(emps)
    active_bench = [e for e in emps if e.get("status") not in ("deployed", "released", "transferred")]
    critical = [e for e in active_bench if age(e) > 60]
    available = [e for e in emps if str(e.get("availabilityType", e.get("availability", ""))).lower().startswith("imm")]
    deployed = [e for e in emps if e.get("status") == "deployed"]
    ready = [e for e in emps if (e.get("readinessScore") or 0) >= 80]
    this_month = today.strftime("%Y-%m")
    new_bench = [e for e in emps if str(e.get("benchStart", ""))[:7] == this_month]
    deployed_month = [e for e in deployed if str(e.get("deployedAt", ""))[:7] == this_month]
    avg_bench_days = round(sum(age(e) for e in active_bench) / len(active_bench)) if active_bench else 0
    bench_rate = round(100 * len(active_bench) / total) if total else 0
    utilization = round(100 * len(deployed) / total) if total else 0
    avg_profile = round(sum(compute_profile_completion(e)["pct"] for e in emps) / total) if total else 0

    emp_ids = {e["_id"] for e in emps}
    prog = [p for p in db[C.PROGRESS].find() if p.get("employeeId") in emp_ids]
    training_completion = round(sum(p.get("pct", 0) for p in prog) / len(prog)) if prog else 0
    results = [r for r in db[C.RESULTS].find() if r.get("employeeId") in emp_ids]
    avg_assessment = round(sum(100 * r["scoreMarks"] / r["totalMarks"] for r in results if r.get("totalMarks")) / len(results)) if results else 0

    buckets = {"0-15": 0, "16-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    for e in active_bench:
        a = age(e)
        k = "0-15" if a <= 15 else "16-30" if a <= 30 else "31-60" if a <= 60 else "61-90" if a <= 90 else "90+"
        buckets[k] += 1

    status_dist, skill_dist, bu_dist, ready_dist = {}, {}, {}, {"Deployable (80+)": 0, "Developing (50-79)": 0, "Early (<50)": 0}
    for e in emps:
        status_dist[e.get("status", "unknown")] = status_dist.get(e.get("status", "unknown"), 0) + 1
        bu_dist[e.get("bu", "-")] = bu_dist.get(e.get("bu", "-"), 0) + 1
        r = e.get("readinessScore", 0) or 0
        ready_dist["Deployable (80+)" if r >= 80 else "Developing (50-79)" if r >= 50 else "Early (<50)"] += 1
        for s in e.get("skills", []):
            nm = s.get("skill", "?")
            skill_dist[nm] = skill_dist.get(nm, 0) + 1

    return {
        # "scope": "org" if user.role == "admin" else user.bu,
        "scope": "org" if enterprise(user) else user.bu,
        "totalEmployees": total, "activeBench": len(active_bench), "benchRatePct": bench_rate,
        "avgBenchDays": avg_bench_days, "criticalBench": len(critical),
        "availableEmployees": len(available), "newBench": len(new_bench),
        "deployed": len(deployed), "deployedThisMonth": len(deployed_month),
        "utilizationPct": utilization, "profileCompletionPct": avg_profile,
        # "readyEmployees": len(ready), "totalBUs": db[C.BUS].count_documents({}) if user.role == "admin" else 1,
        "readyEmployees": len(ready), "totalBUs": db[C.BUS].count_documents({}) if enterprise(user) else 1,
        "trainingCompletionPct": training_completion, "avgAssessmentScore": avg_assessment,
        "benchAging": buckets, "statusDistribution": status_dist, "skillAvailability": skill_dist,
        "buDistribution": bu_dist, "readinessDistribution": ready_dist,
    }
