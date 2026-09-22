from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .database import get_db
from .routers import (admin_config, assessments, auth, bootstrap, employees,
                      insights, interviews, learning, notifications, people,
                      prep, registration, reports, google_auth, library, files)

from .seed import seed

app = FastAPI(title="LeadSoc TEDP API", version="2.0.0",
              description="LeadSoc Talent Enablement & Deployment Portal (MongoDB)")

app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _startup():
    try:
        seed(get_db())
    except Exception as e:
        print(f"[startup] seed skipped: {e}")


@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "service": "LeadSoc TEDP API", "db": "mongodb"}


for r in (auth, registration, employees, learning, assessments, prep, interviews,
          people, admin_config, reports, notifications, insights, bootstrap, library, google_auth, files):
    app.include_router(r.router)
