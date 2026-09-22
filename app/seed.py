"""Seeds ONLY the pre-registered admin plus system config. Business Units,
TAs and employees are created at runtime (admin creates BUs, BU creates TAs)."""
from . import config, models as C
from .database import now_iso
from .integrations.calendar import google_connected
from .integrations.email import configured as email_configured
from .security import hash_password


def seed(db):
    # Ensure the pre-registered admin ALWAYS exists, even if the users
    # collection already has other rows (previous seed gated on empty collection,
    # which silently skipped admin creation and caused "Invalid credentials").
    if db[C.USERS].find_one({"email": config.ADMIN_EMAIL.lower()}) is None:
        db[C.USERS].insert_one({
            "_id": "u_admin", "name": "LeadSoc Admin", "email": config.ADMIN_EMAIL.lower(),
            "role": "admin", "bu": None, "employeeId": None, "crossBu": True,
            "active": True, "mustChangePassword": False,
            "passwordHash": hash_password(config.ADMIN_PASSWORD)})

    if db[C.INTEGRATIONS].count_documents({}) == 0:
        db[C.INTEGRATIONS].insert_many([
            {"_id": "IN_SSO", "name": "SSO (SAML)", "category": "SSO", "enabled": False, "detail": "Okta / Azure AD"},
            {"_id": "IN_EMAIL", "name": "Email (SMTP)", "category": "Email",
             "enabled": email_configured(), "detail": config.SMTP_HOST or "not configured"},
            {"_id": "IN_MEET", "name": "Google Meet", "category": "Meetings",
             "enabled": google_connected(), "detail": "Meet link creation"},
            {"_id": "IN_CAL", "name": "Google Calendar", "category": "Calendar",
             "enabled": google_connected(), "detail": "Availability sync"},
            {"_id": "IN_GROK", "name": "Grok (x.ai) Insights", "category": "AI",
             "enabled": bool(config.GROQ_API_KEY), "detail": config.GROQ_MODEL},
            {"_id": "IN_STORE", "name": "Object Storage", "category": "Storage", "enabled": False, "detail": "S3 / GCS"},
        ])

    if db[C.SLA].count_documents({}) == 0:
        db[C.SLA].insert_many([
            {"_id": "SLA1", "area": "Interview feedback", "thresholdDays": 2, "escalateTo": "TA Lead"},
            {"_id": "SLA2", "area": "Bench ageing alert", "thresholdDays": 45, "escalateTo": "BU Head"},
            {"_id": "SLA3", "area": "Prep readiness", "thresholdDays": 7, "escalateTo": "BU Head"},
            {"_id": "SLA4", "area": "Assignment submission", "thresholdDays": 3, "escalateTo": "Trainer"},
        ])

    if db[C.TEMPLATES].count_documents({}) == 0:
        db[C.TEMPLATES].insert_many([
            {"_id": "NT1", "name": "Assessment Assigned", "channel": "Email", "subject": "A new assessment has been assigned"},
            {"_id": "NT2", "name": "Interview Scheduled", "channel": "Email", "subject": "Your interview is scheduled"},
            {"_id": "NT3", "name": "Readiness Warning", "channel": "In-app", "subject": "Readiness below threshold"},
        ])

    if db[C.READINESS_CFG].count_documents({"_id": "weights"}) == 0:
        db[C.READINESS_CFG].insert_one(
            {"_id": "weights", "weights": {"skills": 0.4, "training": 0.35, "assessment": 0.25}})

    # Populate demo data (idempotent; skips if BUs already exist).
    try:
        seed_demo(db)
    except Exception as e:
        print(f"[seed] demo skipped: {e}")


def seed_demo(db):
    """Populate realistic demo data once (only if no Business Units exist).
    Registration endpoints still work — this just gives you data to explore."""
    import os
    if os.getenv("LEADSOC_SEED_DEMO", "1") not in ("1", "true", "True"):
        return
    if db[C.BUS].count_documents({}) > 0:
        return

    from .database import now_iso
    from .ids import email_from_name, next_code, next_employee_id
    from .routers.readiness_calc import compute_readiness
    from .security import hash_password

    def user(name, role, bu=None, employee_id=None, pw="changeme123", cross=False):
        email = email_from_name(name)
        db[C.USERS].update_one({"email": email}, {"$setOnInsert": {
            "_id": next_code(db, "user", "u_"), "name": name, "email": email,
            "role": role, "bu": bu, "employeeId": employee_id, "crossBu": cross,
            "active": True, "mustChangePassword": False,
            "passwordHash": hash_password(pw)}}, upsert=True)
        return email

    # --- Business Units + BU Heads ------------------------------------------
    bus = [
        {"code": "SW", "name": "Software", "practices": ["ASW", "Embedded", "Cloud"], "head": "Sanjay Rao"},
        {"code": "VL", "name": "VLSI", "practices": ["RTL", "DV", "Physical Design"], "head": "Vidya Menon"},
    ]
    for b in bus:
        db[C.BUS].insert_one({"_id": b["code"], "name": b["name"], "code": b["code"],
                              "practices": b["practices"], "active": True, "createdAt": now_iso()})
        user(b["head"], "buHead", bu=b["code"], pw="buhead123")

    # --- TAs (registered under each BU) -------------------------------------
    user("Tara Nair", "ta", bu="SW", pw="ta12345")
    user("Kiran Shah", "ta", bu="VL", pw="ta12345")

    # --- Skills directory ----------------------------------------------------
    skills = [("Python", "Software"), ("Node.js", "Software"), ("React", "Software"),
              ("SystemVerilog", "VLSI"), ("UVM", "VLSI"), ("Physical Design", "VLSI"),
              ("Docker", "Cloud"), ("Communication", "Soft Skills")]
    for n, cat in skills:
        db[C.SKILLS].insert_one({"_id": next_code(db, "skill", "S"), "name": n,
                                 "category": cat, "levels": ["Beginner", "Intermediate", "Advanced", "Expert"]})

    # --- Trainers ------------------------------------------------------------
    for n, exp, cap in [("Anil Kapoor", ["Python", "Node.js"], 12),
                        ("Deepa Iyer", ["SystemVerilog", "UVM"], 10)]:
        db[C.TRAINERS].insert_one({"_id": next_code(db, "trainer", "T"), "name": n,
            "email": email_from_name(n), "internal": True, "expertise": exp,
            "capacityHoursPerWeek": cap, "rating": 4.5, "assignments": [], "createdAt": now_iso()})

    # --- Materials -----------------------------------------------------------
    mats = [
        ("Python Deep Dive", "video", "https://learn.leadsoc.com/py", "Python", "SW"),
        ("Node.js Patterns", "pdf", "https://learn.leadsoc.com/node.pdf", "Node.js", "SW"),
        ("React Fundamentals", "link", "https://learn.leadsoc.com/react", "React", "SW"),
        ("SystemVerilog Assertions", "pdf", "https://learn.leadsoc.com/sva.pdf", "SystemVerilog", "VL"),
        ("UVM Bootcamp", "video", "https://learn.leadsoc.com/uvm", "UVM", "VL"),
    ]
    mat_ids = {}
    for title, typ, url, skill, bu in mats:
        mid = next_code(db, "material", "M")
        mat_ids[title] = mid
        db[C.MATERIALS].insert_one({"_id": mid, "title": title, "type": typ, "url": url,
            "skill": skill, "bu": bu, "owner": "LeadSoc Admin", "description": f"{skill} material",
            "createdAt": now_iso()})

    # --- Training plans ------------------------------------------------------
    plan_sw = next_code(db, "plan", "PL")
    db[C.PLANS].insert_one({"_id": plan_sw, "name": "Full-Stack Ramp", "bu": "SW",
        "targetRole": "Full-Stack Engineer", "description": "Python + Node + React",
        "durationHours": 40, "skills": ["Python", "Node.js", "React"], "items": [
            {"materialId": mat_ids["Python Deep Dive"], "title": "Python Deep Dive", "mandatory": True, "order": 1},
            {"materialId": mat_ids["Node.js Patterns"], "title": "Node.js Patterns", "mandatory": True, "order": 2},
            {"materialId": mat_ids["React Fundamentals"], "title": "React Fundamentals", "mandatory": False, "order": 3}],
        "createdBy": "Sanjay Rao", "createdAt": now_iso()})
    plan_vl = next_code(db, "plan", "PL")
    db[C.PLANS].insert_one({"_id": plan_vl, "name": "DV Accelerator", "bu": "VL",
        "targetRole": "Design Verification Engineer", "description": "SVA + UVM",
        "durationHours": 32, "skills": ["SystemVerilog", "UVM"], "items": [
            {"materialId": mat_ids["SystemVerilog Assertions"], "title": "SVA", "mandatory": True, "order": 1},
            {"materialId": mat_ids["UVM Bootcamp"], "title": "UVM Bootcamp", "mandatory": True, "order": 2}],
        "createdBy": "Vidya Menon", "createdAt": now_iso()})

    # --- Employees (with logins) + progress ---------------------------------
    people = [
        ("Aditya Kumar", "SW", "ASW", "Full-Stack Engineer", [("Python", 7), ("Node.js", 6), ("React", 5)], plan_sw),
        ("Meera Iyer", "SW", "Cloud", "Backend Engineer", [("Python", 8), ("Docker", 6)], plan_sw),
        ("Rahul Verma", "SW", "Embedded", "Full-Stack Engineer", [("Python", 4), ("React", 3)], plan_sw),
        ("Sneha Rao", "VL", "DV", "DV Engineer", [("SystemVerilog", 7), ("UVM", 6)], plan_vl),
        ("Vikram Singh", "VL", "RTL", "RTL Engineer", [("SystemVerilog", 5)], plan_vl),
        ("Priya Nair", "VL", "DV", "DV Engineer", [("SystemVerilog", 8), ("UVM", 8)], plan_vl),
    ]
    emp_ids = []
    for name, bu, practice, role, sk, plan in people:
        eid = next_employee_id(db)
        emp_ids.append((eid, bu, plan))
        db[C.EMPLOYEES].insert_one({"_id": eid, "name": name, "email": email_from_name(name),
            "phone": "", "location": "Bengaluru", "bu": bu, "practice": practice,
            "manager": "Team Lead", "benchStart": "2026-01-05", "status": "trainingInProgress",
            "owner": "TA", "targetDeploymentDate": None, "targetRole": role, "benchReason": "New allocation",
            "readinessScore": 0, "deployable": False,
            "skills": [{"skill": s, "proficiency": p, "years": 2} for s, p in sk],
            "availability": [{"date": "2026-03-12", "start": "10:00", "end": "11:00", "status": "free"}],
            "timeline": [{"at": now_iso(), "text": "Added to bench", "actor": "TA"}]})
        user(name, "benchEngineer", bu=bu, employee_id=eid, pw="emp12345")
        # progress on plan items
        plan_doc = db[C.PLANS].find_one({"_id": plan})
        for j, item in enumerate(plan_doc.get("items", [])):
            pct = [100, 60, 20][j % 3]
            db[C.PROGRESS].insert_one({"employeeId": eid, "planId": plan, "materialId": item["materialId"],
                "title": item.get("title", ""), "status": "completed" if pct == 100 else "inProgress",
                "pct": pct, "updatedAt": now_iso()})

    # --- Assessments + assignments + results --------------------------------
    a_sw = next_code(db, "assessment", "A")
    db[C.ASSESSMENTS].insert_one({"_id": a_sw, "name": "Python Fundamentals", "bu": "SW",
        "practice": "ASW", "skill": "Python", "topic": "Core", "difficulty": "medium",
        "durationMinutes": 30, "passingScorePct": 60, "maxAttempts": 2, "status": "published",
        "createdBy": "Sanjay Rao", "createdAt": now_iso(), "questions": [
            {"id": "q1", "text": "What is a Python decorator?", "options": ["A function wrapper", "A loop", "A class", "A module"], "correctIndex": 0, "marks": 1},
            {"id": "q2", "text": "Which keyword defines a generator?", "options": ["return", "yield", "async", "def"], "correctIndex": 1, "marks": 1}]})
    a_vl = next_code(db, "assessment", "A")
    db[C.ASSESSMENTS].insert_one({"_id": a_vl, "name": "SystemVerilog Basics", "bu": "VL",
        "practice": "DV", "skill": "SystemVerilog", "topic": "Core", "difficulty": "hard",
        "durationMinutes": 45, "passingScorePct": 65, "maxAttempts": 2, "status": "published",
        "createdBy": "Vidya Menon", "createdAt": now_iso(), "questions": [
            {"id": "q1", "text": "What does 'logic' type allow?", "options": ["4-state", "2-state", "real", "string"], "correctIndex": 0, "marks": 1}]})

    for idx, (eid, bu, _) in enumerate(emp_ids):
        aid = a_sw if bu == "SW" else a_vl
        asg_id = f"ASG{idx + 1}"
        db[C.ASSIGNMENTS].insert_one({"_id": asg_id, "assessmentId": aid, "employeeId": eid,
            "assignedBy": "TA", "assignedAt": now_iso(), "dueDate": "2026-03-20",
            "attemptsUsed": 1, "attemptLimit": 2, "status": "completed"})
        score = [9, 5, 7, 8, 4, 10][idx % 6]
        db[C.RESULTS].insert_one({"_id": f"R{idx + 1}", "assessmentId": aid, "assignmentId": asg_id,
            "employeeId": eid, "scoreMarks": score, "totalMarks": 10, "correct": score,
            "incorrect": 10 - score, "timeTakenSeconds": 600, "passed": score >= 6,
            "submittedAt": now_iso(), "attemptNumber": 1})

    # --- Question banks + one prep assignment --------------------------------
    qb = next_code(db, "bank", "QB")
    db[C.QUESTION_BANKS].insert_one({"_id": qb, "name": "Client ABC — Python", "client": "ABC Corp",
        "role": "Python Developer", "bu": "SW", "confidentiality": "Internal", "version": "v1",
        "questions": [{"id": "q1", "text": "Explain the GIL.", "answerText": ""},
                      {"id": "q2", "text": "Describe async/await.", "answerText": ""}],
        "questionCount": 2, "createdBy": "Tara Nair", "createdAt": now_iso()})
    if emp_ids:
        first = emp_ids[0][0]
        db[C.PREP].insert_one({"_id": next_code(db, "prep", "PR"), "employeeId": first,
            "bankId": qb, "bankName": "Client ABC — Python", "assignedBy": "Tara Nair",
            "status": "assigned", "createdAt": now_iso(), "answers": [
                {"questionId": "q1", "questionText": "Explain the GIL.", "answerText": "", "status": "notStarted", "reviewerComment": "", "score": 0},
                {"questionId": "q2", "questionText": "Describe async/await.", "answerText": "", "status": "notStarted", "reviewerComment": "", "score": 0}]})

    # --- Interview panel ------------------------------------------------------
    db[C.PANELS].insert_one({"_id": next_code(db, "panel", "PN"), "name": "Software Hiring Panel",
        "bu": "SW", "members": [{"name": "Anil Kapoor", "skills": ["Python"]},
                                 {"name": "Sanjay Rao", "skills": ["System Design"]}],
        "rounds": ["Screening", "Technical", "Managerial"], "assignments": [], "createdBy": "Sanjay Rao",
        "createdAt": now_iso()})

    # --- Recompute readiness for everyone -----------------------------------
    for eid, _, _ in emp_ids:
        emp = db[C.EMPLOYEES].find_one({"_id": eid})
        if emp:
            compute_readiness(db, emp)

    # --- A couple of notifications for the admin ----------------------------
    admin = db[C.USERS].find_one({"role": "admin"})
    if admin:
        db[C.NOTIFICATIONS].insert_many([
            {"userId": admin["_id"], "title": "Demo data loaded",
             "body": "2 BUs, 2 TAs, 6 employees and sample content are ready.",
             "kind": "info", "read": False, "createdAt": now_iso()},
            {"userId": admin["_id"], "title": "Welcome to LeadSoc TEDP",
             "body": "Use Administration → Business Units to register more BUs.",
             "kind": "info", "read": False, "createdAt": now_iso()}])
