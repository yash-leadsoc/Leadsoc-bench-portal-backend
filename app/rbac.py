def is_enterprise(role: str, cross_bu: bool = False) -> bool:
    return role in ("admin", "cto") or cross_bu


def can(role: str, perm: str) -> bool:
    if role == "admin":
        return True
    if role == "cto":
        return perm in ("view", "export")
    if role == "buHead":
        # Full control within the BU, including creating TAs. No global admin.
        return perm in ("view", "add", "edit", "deactivate", "assign", "approve",
                        "export", "manageTa", "schedule")
    if role == "ta":
        return perm in ("view", "add", "edit", "assign", "export", "schedule")
    if role == "benchEngineer":
        return perm == "view"
    return False
