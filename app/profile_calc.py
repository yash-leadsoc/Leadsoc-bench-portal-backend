"""Dynamic employee profile completion. Weighted by section; returns the overall
percentage plus which fields are still missing (for the 'Complete Profile' UI)."""

WEIGHTS = {"basic": 15, "professional": 15, "skills": 20, "experience": 10,
           "preferences": 10, "availability": 10, "resume": 10,
           "certifications": 5, "links": 5}


def _has(v):
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


def compute_profile_completion(emp: dict) -> dict:
    emp = emp or {}
    sections = {
        "basic": ["name", "email", "phone", "bu", "designation", "manager"],
        "professional": ["totalExperience", "primaryDomain", "targetRole"],
        "experience": ["relevantExperience"],
        "preferences": ["preferredRole", "preferredTechnology", "preferredLocation", "workMode"],
        "availability": ["availabilityType", "availableFrom"],
        "links": ["github", "linkedin"],
    }
    missing = []
    total = 0.0
    detail = {}
    for sec, fields in sections.items():
        filled = sum(1 for f in fields if _has(emp.get(f)))
        frac = filled / len(fields) if fields else 1
        detail[sec] = round(frac * 100)
        total += WEIGHTS[sec] * frac
        for f in fields:
            if not _has(emp.get(f)):
                missing.append(f)
    # collection-based sections
    skills_ok = 1 if len(emp.get("skills", [])) >= 1 else 0
    detail["skills"] = skills_ok * 100
    total += WEIGHTS["skills"] * skills_ok
    if not skills_ok:
        missing.append("skills")

    resume_ok = 1 if _has(emp.get("resumeUrl")) else 0
    detail["resume"] = resume_ok * 100
    total += WEIGHTS["resume"] * resume_ok
    if not resume_ok:
        missing.append("resumeUrl")

    cert_ok = 1 if len(emp.get("certifications", [])) >= 1 else 0
    detail["certifications"] = cert_ok * 100
    total += WEIGHTS["certifications"] * cert_ok
    if not cert_ok:
        missing.append("certifications")

    return {"pct": round(total), "sections": detail, "missing": missing}
