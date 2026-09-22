"""Create or reset the LeadSoc admin login directly in the database.

Run this if you can't log in as admin. It uses the SAME settings the app uses
(reading .env if python-dotenv is installed), connects to your MongoDB, and
force-sets admin@leadsoc.com to the password from LEADSOC_ADMIN_PASSWORD
(default admin123).

    python reset_admin.py
    python reset_admin.py --password mynewpass    # optional override
"""
import argparse

from app import config
from app.database import get_db
from app.security import hash_password


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default=config.ADMIN_EMAIL)
    ap.add_argument("--password", default=config.ADMIN_PASSWORD)
    args = ap.parse_args()

    db = get_db()
    # Force a connection so failures are obvious (not swallowed).
    db.command("ping")

    email = args.email.lower()
    res = db["users"].update_one(
        {"email": email},
        {"$set": {
            "name": "LeadSoc Admin", "email": email, "role": "admin",
            "bu": None, "employeeId": None, "crossBu": True, "active": True,
            "mustChangePassword": False,
            "passwordHash": hash_password(args.password),
        }, "$setOnInsert": {"_id": "u_admin"}},
        upsert=True,
    )
    action = "created" if res.upserted_id else "reset"
    print(f"OK: admin {action}.")
    print(f"  DB:       {config.MONGO_URL}  /  {config.DB_NAME}")
    print(f"  Email:    {email}")
    print(f"  Password: {args.password}")
    total = db["users"].count_documents({})
    print(f"  users collection now has {total} account(s).")


if __name__ == "__main__":
    main()
