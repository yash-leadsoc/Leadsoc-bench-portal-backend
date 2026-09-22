import os, uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from .. import models as C
from ..database import get_db, now_iso, out, out_list, log_audit
from ..deps import current_user, require
from ..ids import next_code
from ..schemas import LibraryDocIn, LibraryQuizIn, LibraryQuizSubmitIn, QuestionIn

router = APIRouter(tags=["library"])
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _scope(user):
    return {} if user.role == "admin" else {"bu": user.bu}


# ---- list docs (approved to everyone; own pending to the uploader; all to admin) ----
@router.get("/library/docs")
def list_docs(db=Depends(get_db), user=Depends(current_user)):
    q = _scope(user)
    if user.role == "admin":
        docs = out_list(db[C.LIBRARY].find(q))
    else:
        docs = out_list(db[C.LIBRARY].find({**q, "$or": [
            {"approved": True}, {"uploadedBy": user.id}]}))
    return docs


@router.get("/library/pending")
def pending_docs(db=Depends(get_db), user=Depends(require("approve"))):
    return out_list(db[C.LIBRARY].find({"approved": False}))


@router.post("/library/docs")
def add_doc(body: LibraryDocIn, db=Depends(get_db), user=Depends(current_user)):
    # employees may add but need approval; BU/TA/admin auto-approved
    auto = user.role in ("admin", "buHead", "ta")
    did = next_code(db, "libdoc", "LD")
    doc = {"_id": did, "domain": body.domain.strip(), "title": body.title,
           "type": body.type, "url": body.url, "description": body.description,
           "bu": user.bu, "uploadedBy": user.id, "uploadedByName": user.name,
           "approved": auto, "createdAt": now_iso()}
    db[C.LIBRARY].insert_one(doc)
    return out(doc)


@router.post("/library/upload")
async def upload_doc(domain: str = Form(...), title: str = Form(...),
                     type: str = Form("pdf"), description: str = Form(""),
                     file: UploadFile = File(...), db=Depends(get_db),
                     user=Depends(current_user)):
    ext = os.path.splitext(file.filename)[1]
    fname = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR, fname), "wb") as f:
        f.write(await file.read())
    auto = user.role in ("admin", "buHead", "ta")
    did = next_code(db, "libdoc", "LD")
    doc = {"_id": did, "domain": domain.strip(), "title": title, "type": type,
           "url": f"/library/file/{fname}", "fileName": file.filename,
           "description": description, "bu": user.bu, "uploadedBy": user.id,
           "uploadedByName": user.name, "approved": auto, "createdAt": now_iso()}
    db[C.LIBRARY].insert_one(doc)
    return out(doc)


@router.get("/library/file/{fname}")
def get_file(fname: str):
    path = os.path.join(UPLOAD_DIR, fname)
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")
    return FileResponse(path)


@router.post("/library/docs/{did}/approve")
def approve_doc(did: str, db=Depends(get_db), user=Depends(require("approve"))):
    db[C.LIBRARY].update_one({"_id": did}, {"$set": {"approved": True}})
    log_audit(db, user.name, "Approve library doc", did)
    return {"ok": True}


@router.delete("/library/docs/{did}")
def delete_doc(did: str, db=Depends(get_db), user=Depends(current_user)):
    doc = db[C.LIBRARY].find_one({"_id": did})
    if not doc:
        raise HTTPException(404, "Not found")
    # uploader can delete own; approvers can delete any
    from ..rbac import can
    if doc.get("uploadedBy") != user.id and not can(user.role, "approve"):
        raise HTTPException(403, "Not permitted")
    db[C.LIBRARY].delete_one({"_id": did})
    return {"ok": True, "id": did}


# ---- domain quiz (BU uploads questions per domain) ----
@router.get("/library/domains")
def domains(db=Depends(get_db), user=Depends(current_user)):
    """Domains with doc counts + whether a quiz exists + the user's progress."""
    q = _scope(user)
    docs = [d for d in db[C.LIBRARY].find({**q, "approved": True})]
    by = {}
    for d in docs:
        by.setdefault(d["domain"], 0)
        by[d["domain"]] += 1
    quizzes = {qz["domain"]: qz for qz in db[C.LIBRARY_QUIZ].find(_scope(user))}
    prog = {p["domain"]: p for p in db[C.LIBRARY_PROGRESS].find({"userId": user.id})}
    rows = []
    for domain, count in sorted(by.items()):
        p = prog.get(domain)
        rows.append({"domain": domain, "docCount": count,
                     "hasQuiz": domain in quizzes,
                     "quizQuestions": len(quizzes[domain].get("questions", [])) if domain in quizzes else 0,
                     "myScorePct": p.get("scorePct") if p else None,
                     "completed": bool(p and p.get("completed"))})
    return {"rows": rows}


@router.get("/library/quiz/{domain}")
def get_quiz(domain: str, db=Depends(get_db), user=Depends(current_user)):
    qz = db[C.LIBRARY_QUIZ].find_one({"domain": domain, **_scope(user)})
    return out(qz) if qz else {"domain": domain, "questions": []}


@router.post("/library/quiz")
def set_quiz(body: LibraryQuizIn, db=Depends(get_db), user=Depends(require("add"))):
    db[C.LIBRARY_QUIZ].update_one(
        {"domain": body.domain, "bu": user.bu},
        {"$set": {"domain": body.domain, "bu": user.bu,
                  "questions": [q.model_dump() for q in body.questions],
                  "updatedBy": user.name, "updatedAt": now_iso()}}, upsert=True)
    return {"ok": True}


@router.post("/library/quiz/submit")
def submit_quiz(body: LibraryQuizSubmitIn, db=Depends(get_db), user=Depends(current_user)):
    pct = round(100 * body.scoreMarks / body.totalMarks) if body.totalMarks else 0
    db[C.LIBRARY_PROGRESS].update_one(
        {"userId": user.id, "domain": body.domain},
        {"$set": {"userId": user.id, "employeeId": user.employee_id,
                  "domain": body.domain, "scorePct": pct,
                  "completed": pct >= 60, "at": now_iso()}}, upsert=True)
    return {"ok": True, "scorePct": pct, "passed": pct >= 60}


@router.get("/library/progress/{domain}")
def domain_progress(domain: str, db=Depends(get_db), user=Depends(require("view"))):
    """BU/TA: everyone's progress for a domain."""
    rows = out_list(db[C.LIBRARY_PROGRESS].find({"domain": domain}))
    for r in rows:
        emp = db[C.EMPLOYEES].find_one({"_id": r.get("employeeId")})
        r["name"] = emp.get("name") if emp else r.get("employeeId")
    return {"rows": rows}

@router.get("/library/my-progress")
def my_library_progress(db=Depends(get_db), user=Depends(current_user)):
    """The signed-in employee's own domain quiz progress."""
    rows = out_list(db[C.LIBRARY_PROGRESS].find({"userId": user.id}))
    return {"rows": rows}


@router.get("/library/progress/{domain}")
def domain_progress(domain: str, db=Depends(get_db), user=Depends(current_user)):
    """Progress for a domain. Employees see only their own row; staff see all."""
    if user.role == "benchEngineer":
        rows = out_list(db[C.LIBRARY_PROGRESS].find({"domain": domain, "userId": user.id}))
    else:
        rows = out_list(db[C.LIBRARY_PROGRESS].find({"domain": domain}))
        for r in rows:
            emp = db[C.EMPLOYEES].find_one({"_id": r.get("employeeId")})
            r["name"] = emp.get("name") if emp else r.get("employeeId")
    return {"rows": rows}