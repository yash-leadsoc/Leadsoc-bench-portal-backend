"""Reset any user's password to a known value.
    python reset_password.py user@leadsoc.com newpass123
"""
import sys
from app.database import get_db
from app.security import hash_password

if len(sys.argv) < 3:
    print("usage: python reset_password.py <email> <new_password>")
    raise SystemExit(1)

email, new_pw = sys.argv[1].lower(), sys.argv[2]
db = get_db()
res = db["users"].update_one({"email": email}, {"$set": {
    "passwordHash": hash_password(new_pw), "mustChangePassword": True}})
print("updated" if res.modified_count else "no user with that email", "->", email)