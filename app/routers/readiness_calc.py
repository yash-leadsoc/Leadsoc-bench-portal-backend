"""Readiness scoring. Weights are configurable (readiness_config collection),
editable by admin. Score blends skills, training completion and assessment
pass-rate."""
from .. import models


DEFAULT_WEIGHTS = {"skills": 0.4, "training": 0.35, "assessment": 0.25}


def get_weights(db):
    cfg = db[models.READINESS_CFG].find_one({"_id": "weights"})
    return cfg.get("weights", DEFAULT_WEIGHTS) if cfg else DEFAULT_WEIGHTS


def compute_readiness(db, emp: dict) -> int:
    w = get_weights(db)
    skills = emp.get("skills", [])
    skill_score = 0
    if skills:
        skill_score = sum(min(s.get("proficiency", 0), 10) for s in skills) / (len(skills) * 10) * 100

    prog = list(db[models.PROGRESS].find({"employeeId": emp["_id"]}))
    if prog:
        train_score = sum(p.get("pct", 0) for p in prog) / len(prog)
    else:
        train_score = 0

    results = list(db[models.RESULTS].find({"employeeId": emp["_id"]}))
    if results:
        assess_score = 100 * sum(1 for r in results if r.get("passed")) / len(results)
    else:
        assess_score = 0

    score = (w["skills"] * skill_score + w["training"] * train_score +
             w["assessment"] * assess_score)
    score = round(score)
    if score != emp.get("readinessScore"):
        db[models.EMPLOYEES].update_one({"_id": emp["_id"]},
            {"$set": {"readinessScore": score, "deployable": score >= 80}})
    return score
