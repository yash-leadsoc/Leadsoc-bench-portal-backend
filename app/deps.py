from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import models, rbac
from .database import get_db
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer),
                 db=Depends(get_db)) -> models.User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    doc = db[models.USERS].find_one({"_id": payload.get("sub")})
    if not doc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return models.User(doc)


def require(permission: str):
    def _dep(user: models.User = Depends(current_user)) -> models.User:
        if not rbac.can(user.role, permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"Role {user.role} lacks '{permission}'")
        return user
    return _dep


def require_role(*roles):
    def _dep(user: models.User = Depends(current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"Requires role: {', '.join(roles)}")
        return user
    return _dep


def enterprise(user: models.User) -> bool:
    return rbac.is_enterprise(user.role, user.cross_bu)


def bu_filter(user, extra: dict | None = None) -> dict:
    f = dict(extra or {})
    if not enterprise(user):
        f["bu"] = user.bu
    return f
