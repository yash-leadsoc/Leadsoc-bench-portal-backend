from fastapi import APIRouter, Depends

from .. import models
from ..database import get_db, out_list
from ..deps import current_user

router = APIRouter(tags=["notifications"])
C = models


@router.get("/notifications")
def my_notifications(db=Depends(get_db), user=Depends(current_user)):
    rows = out_list(db[C.NOTIFICATIONS].find({"userId": user.id}).sort("createdAt", -1))
    return {"rows": rows, "unread": sum(1 for r in rows if not r.get("read"))}


@router.post("/notifications/{nid}/read")
def mark_read(nid: str, db=Depends(get_db), user=Depends(current_user)):
    from bson import ObjectId
    try:
        oid = ObjectId(nid)
    except Exception:
        oid = nid
    db[C.NOTIFICATIONS].update_one({"_id": oid, "userId": user.id},
                                   {"$set": {"read": True}})
    return {"ok": True}


@router.post("/notifications/read-all")
def mark_all(db=Depends(get_db), user=Depends(current_user)):
    db[C.NOTIFICATIONS].update_many({"userId": user.id}, {"$set": {"read": True}})
    return {"ok": True}
