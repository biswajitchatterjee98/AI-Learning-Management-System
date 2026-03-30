Adaptive AI LMS Generator (4-Phase Roadmap, Phase 4 in progress)

This folder contains the initial skeleton for an adaptive, multi-tenant AI LMS generator.

Roadmap (4 phases total)
- Phase 1: Core LMS foundation
- Phase 2: AI tutor + content generation + simulation basics
- Phase 3: KPI tracking + scorecards + adaptive learning
- Phase 4: Gamification + integrations + scaling/production hardening

Current implementation snapshot
- Backend (FastAPI): JWT auth + RBAC, multi-tenant data model, onboarding blueprint creation/listing, AI-backed generation, course/module/lesson APIs, assessment APIs, lesson progress tracking, next-lesson recommendations, KPI ingestion, gamification and webhook registry.
- Tenant data foundation: Google Sheets ingestion + normalization into tenant knowledge items (`knowledge_items`) for Namadarshan tabs, with source references preserved for downstream AI and lessons.
- Phase 2 async implementation: Redis + Celery job queue for LMS generation, tutor feedback, and simulation evaluation.
- Frontend (Next.js): login + role-based dashboard, onboarding UI (sync tenant data, create blueprint from knowledge, async LMS generation), learning flow UI, assessment UI, tutor UI (async feedback), simulation UI (async evaluation), recommendations, tenant analytics.
- Ops endpoints: `GET /healthz`, `GET /readyz` (DB + Redis reachability).

Dev prerequisites
- Docker/Docker Compose
- Node.js (for frontend) and Python (for backend)

Local setup (quick start)
1) Start infra (Postgres + Redis + worker):
   - `docker compose up -d`
2) Backend:
   - `cd backend`
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
   - `uvicorn app.main:app --reload --port 8000`
   - Optional worker (if not using compose worker):
   - `celery -A app.core.celery_app.celery_app worker --loglevel=info`
3) Frontend:
   - `cd frontend`
   - `npm install`
   - `npm run dev`

Demo accounts (seeded on first backend startup)
- Admin: `admin@gmail.com` / `admin@123` (role: `admin`)
- Manager: `manager@gmail.com` / `manager@123` (role: `manager`)
- Employee: `employee@gmail.com` / `employee@123` (role: `employee`)

Note: if `AI_API_KEY` is configured, blueprint generation, lesson generation, and tutor feedback use the configured LLM. If not configured or if provider calls fail, the app automatically falls back to deterministic templates.

Useful API endpoints
- Auth: `POST /api/login`, `GET /api/me`
- Onboarding: `POST /api/onboarding/blueprint`, `POST /api/onboarding/blueprint/from-knowledge`, `GET /api/onboarding/blueprints`, `POST /api/onboarding/generate-lms`
- Tenant data + generalization: `POST /api/tenant-data/sync`, `GET /api/knowledge-items`, `GET /api/knowledge/stats`, `GET /api/tenant/profile`, `PUT /api/tenant/profile`
- Learning: `GET /api/courses`, `GET /api/courses/{course_id}/modules`, `GET /api/modules/{module_id}/lessons`, `POST /api/progress/lesson-complete`
- Assessment: `GET /api/assessments`, `GET /api/assessments/{assessment_id}/questions`, `POST /api/submissions`
- Recommendations: `GET /api/recommendations/next-lessons`
- Tutor: `POST /api/tutor/feedback`
- Async jobs: `GET /api/jobs/{job_id}`
- Simulation: `POST /api/simulations/start`, `POST /api/simulations/submit`, `GET /api/simulations/attempts/{attempt_id}`
- KPI ingestion: `POST /api/kpi/ingest`
- Analytics: `GET /api/analytics/tenant`
- Gamification: `GET /api/gamification/me`, `GET /api/gamification/leaderboard`
- Integrations: `POST /api/integrations/webhooks`, `GET /api/integrations/webhooks`
- Ops: `GET /healthz`, `GET /readyz`

Namadarshan flow
1. Login as admin/manager.
2. Run `Sync Namadarshan Sheet Data` from dashboard (or call `POST /api/tenant-data/sync`).
3. Create blueprint from synced data (`POST /api/onboarding/blueprint/from-knowledge`).
4. Generate LMS asynchronously (`POST /api/onboarding/generate-lms`), then track job in `GET /api/jobs/{job_id}`.
5. Employees use lessons, tutor feedback, simulation, and adaptive recommendations.

Before pushing to GitHub
- Ensure `.env` is not committed (keep secrets local only).
- If any API key was ever shared, rotate it before publishing.
- Commit only source files and configs; do not commit:
  - `frontend/.next/`
  - `frontend/node_modules/`
  - `backend/.venv/`
- Verify app boots from clean setup:
  - `docker compose up -d`
  - backend: `pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000`
  - frontend: `npm install && npm run dev`

