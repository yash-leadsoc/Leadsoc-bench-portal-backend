from fastapi import APIRouter, Depends, HTTPException

from .. import models
from ..database import get_db, log_audit, out, out_list
from ..deps import current_user, require_role
from ..enums import PERMISSIONS, ROLES
from ..ids import next_code
from ..rbac import can, is_enterprise
from .readiness_calc import DEFAULT_WEIGHTS

router = APIRouter(tags=["admin"], prefix="/admin")
C = models


@router.get("/roles")
def roles(user=Depends(require_role("admin"))):
    return [{"role": r, "permissions": {p: can(r, p) for p in PERMISSIONS},
             "enterprise": is_enterprise(r)} for r in ROLES]


@router.get("/practices")
def practices(db=Depends(get_db), user=Depends(require_role("admin"))):
    return out_list(db[C.PRACTICES].find())


@router.post("/practices")
def add_practice(name: str, bu: str, db=Depends(get_db), user=Depends(require_role("admin"))):
    pid = next_code(db, "practice", "PRc")
    db[C.PRACTICES].insert_one({"_id": pid, "bu": bu, "name": name})
    return out(db[C.PRACTICES].find_one({"_id": pid}))


@router.delete("/practices/{pid}")
def del_practice(pid: str, db=Depends(get_db), user=Depends(require_role("admin"))):
    db[C.PRACTICES].delete_one({"_id": pid})
    return {"ok": True, "id": pid}


@router.get("/sla")
def sla(db=Depends(get_db), user=Depends(require_role("admin"))):
    return out_list(db[C.SLA].find())


@router.put("/sla/{sid}")
def edit_sla(sid: str, thresholdDays: int, escalateTo: str, db=Depends(get_db),
             user=Depends(require_role("admin"))):
    db[C.SLA].update_one({"_id": sid},
        {"$set": {"thresholdDays": thresholdDays, "escalateTo": escalateTo}}, upsert=True)
    return out(db[C.SLA].find_one({"_id": sid}))


@router.get("/templates")
def templates(db=Depends(get_db), user=Depends(require_role("admin"))):
    return out_list(db[C.TEMPLATES].find())


@router.put("/templates/{tid}")
def edit_template(tid: str, name: str, channel: str, subject: str, db=Depends(get_db),
                  user=Depends(require_role("admin"))):
    db[C.TEMPLATES].update_one({"_id": tid},
        {"$set": {"name": name, "channel": channel, "subject": subject}}, upsert=True)
    return out(db[C.TEMPLATES].find_one({"_id": tid}))


@router.get("/integrations")
def integrations(db=Depends(get_db), user=Depends(require_role("admin"))):
    return out_list(db[C.INTEGRATIONS].find())


@router.post("/integrations/{iid}/toggle")
def toggle_integration(iid: str, db=Depends(get_db), user=Depends(require_role("admin"))):
    doc = db[C.INTEGRATIONS].find_one({"_id": iid})
    if not doc:
        raise HTTPException(404, "Not found")
    new = not doc.get("enabled", False)
    db[C.INTEGRATIONS].update_one({"_id": iid}, {"$set": {"enabled": new}})
    log_audit(db, user.name, "Integration toggle", doc.get("name", iid), new=str(new))
    return out(db[C.INTEGRATIONS].find_one({"_id": iid}))


@router.get("/readiness-weights")
def get_weights(db=Depends(get_db), user=Depends(require_role("admin"))):
    cfg = db[C.READINESS_CFG].find_one({"_id": "weights"})
    return cfg.get("weights", DEFAULT_WEIGHTS) if cfg else DEFAULT_WEIGHTS


@router.put("/readiness-weights")
def set_weights(skills: float, training: float, assessment: float, db=Depends(get_db),
                user=Depends(require_role("admin"))):
    total = skills + training + assessment
    if total <= 0:
        raise HTTPException(400, "Weights must sum to a positive number")
    weights = {"skills": skills / total, "training": training / total,
               "assessment": assessment / total}
    db[C.READINESS_CFG].update_one({"_id": "weights"},
        {"$set": {"weights": weights}}, upsert=True)
    return weights


@router.get("/audit")
def audit(db=Depends(get_db), user=Depends(require_role("admin"))):
    return out_list(db[C.AUDIT].find().sort("at", -1))
