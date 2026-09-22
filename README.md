# LeadSoc TEDP — Backend (FastAPI + MongoDB)

Talent Enablement & Deployment Portal API. Roles: **admin, buHead, ta, benchEngineer**
(the interview-panel login portal has been removed).

## Registration model
- **Admin is pre-registered** (seeded on first run) — `admin@leadsoc.com` / `admin123`.
- **Admin registers Business Units** — each BU gets a **BU-Head** login (temp password, must change on first login).
- **BU-Head registers TAs** — TA accounts scoped to the BU.
- **BU/TA add employees** — each employee gets a **benchEngineer** self-service login
  (`firstname.lastname@leadsoc.com` / `changeme123`, must change on first login).
  Employee IDs look like **LS1703** (LS + number).
- Everyone can **change their own password**; admin can too.

## Run
```bash
# 1) MongoDB
docker run -d -p 27017:27017 --name leadsoc-mongo mongo:7
# 2) API
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env .env      # edit as needed
uvicorn app.main:app --reload --port 8000   # or ./run.sh
```
Docs at http://127.0.0.1:8000/docs. Only the admin + system config are seeded — all
business data is created at runtime through the registration flow above.

## Feature modules (all implemented + tested)
- **Materials** (replaces "courses") — pdf / video / link / doc / other, full CRUD. No topics, no cohorts.
- **Training plans** — detailed builder (ordered material items, skills, duration), CRUD + assign.
- **Training progress** — per-employee, item-by-item detail.
- **Assessments** — create (with questions), assign to employees, submit, results.
- **Interview prep** — question banks (create + upload more questions), prep assignments,
  answer submission + reviewer review.
- **Interviews** — panels (CRUD + assign), mock interviews and interview scheduling
  (auto Google Meet link), scorecards.
- **Readiness** — computed from skills + training + assessments; weights editable by admin.
- **People & capacity** — trainers (add + assign to employee), skills directory (CRUD).
- **Reports** — overview, bench ageing/readiness, training, assessments, interviews, trainers,
  employee 360; **CSV exports** at `/export/{employees|readiness|results|training-progress}.csv`.
- **Profile & settings, notifications** — per user; notifications also email (when SMTP set).
- **Admin administration** — BUs, users, role matrix, integrations toggle, SLA, templates,
  readiness weights, audit log.

## Integrations (real, credential-guarded — add your keys in `.env`)
- **Google Meet / Calendar** — set `GOOGLE_OAUTH_TOKEN` (+ `GOOGLE_CALENDAR_ID`). Without it,
  a deterministic Meet-style link is generated so scheduling works offline.
- **Email (SMTP)** — set `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD`. Without it, in-app
  notifications are still stored.
- **Grok (x.ai)** — set `XAI_API_KEY` (+ `XAI_MODEL`). Without it, insights fall back to a
  local heuristic with the same output shape.

Every integration degrades gracefully, so the whole app runs with **no keys at all**.
