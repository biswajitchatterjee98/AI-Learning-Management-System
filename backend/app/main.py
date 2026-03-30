from datetime import datetime
import csv
import json
from collections import Counter
from typing import Any, Dict, List
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.deps import get_current_user, require_roles
from app.db_init import safe_init
from app.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentSubmission,
    CompanyBlueprint,
    Course,
    Lesson,
    LessonProgress,
    Module,
    SkillScorecard,
    User,
    UserBadge,
    UserGamification,
    IntegrationWebhook,
    AsyncJob,
    SimulationScenario,
    SimulationAttempt,
    KnowledgeItem,
    TenantProfile,
)
from app.schemas import (
    AssessmentOut,
    AssessmentQuestionOut,
    AssessmentSubmissionOut,
    AssessmentSubmissionRequest,
    BlueprintCreateRequest,
    BlueprintOut,
    CourseCreateRequest,
    CourseOut,
    GenerateLmsRequest,
    LessonCompleteRequest,
    LessonCreateRequest,
    LessonOut,
    LoginRequest,
    LoginResponse,
    ModuleCreateRequest,
    ModuleOut,
    ProgressOut,
    RecommendationOut,
    LessonRecommendationOut,
    TutorFeedbackRequest,
    TutorFeedbackOut,
    KpiIngestRequest,
    KpiIngestOut,
    GamificationProfileOut,
    LeaderboardOut,
    LeaderboardRowOut,
    BadgeOut,
    WebhookCreateRequest,
    WebhookOut,
    JobEnqueueOut,
    JobStatusOut,
    SimulationStartRequest,
    SimulationScenarioOut,
    SimulationSubmitRequest,
    SimulationAttemptOut,
    TenantDataSyncRequest,
    TenantDataSyncOut,
    KnowledgeItemOut,
    KnowledgeStatsOut,
    TenantProfileUpsertRequest,
    TenantProfileOut,
)
from app.tasks.jobs import generate_lms_job, tutor_feedback_job, simulation_evaluate_job


app = FastAPI(title="AI-LMS (Phase 4 Enablement)")

if settings.CORS_ORIGINS.strip() == "*":
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    safe_init()


DEFAULT_NAMADARSHAN_TABS: List[Dict[str, str]] = [
    {"name": "Temples", "gid": "99463276", "url": "https://docs.google.com/spreadsheets/d/1lnfU0PJhK749X3HKLgECls6-7z7AzLCFf7xsOrwVaC8/edit?gid=99463276#gid=99463276"},
    {"name": "Darshan", "gid": "426249344", "url": "https://docs.google.com/spreadsheets/d/1lnfU0PJhK749X3HKLgECls6-7z7AzLCFf7xsOrwVaC8/edit?gid=426249344#gid=426249344"},
    {"name": "Puja", "gid": "599025530", "url": "https://docs.google.com/spreadsheets/d/1lnfU0PJhK749X3HKLgECls6-7z7AzLCFf7xsOrwVaC8/edit?gid=599025530#gid=599025530"},
    {"name": "Yatra", "gid": "1038947046", "url": "https://docs.google.com/spreadsheets/d/1lnfU0PJhK749X3HKLgECls6-7z7AzLCFf7xsOrwVaC8/edit?gid=1038947046#gid=1038947046"},
    {"name": "Prasadam", "gid": "986093364", "url": "https://docs.google.com/spreadsheets/d/1lnfU0PJhK749X3HKLgECls6-7z7AzLCFf7xsOrwVaC8/edit?gid=986093364#gid=986093364"},
    {"name": "Chadhava", "gid": "218786251", "url": "https://docs.google.com/spreadsheets/d/1lnfU0PJhK749X3HKLgECls6-7z7AzLCFf7xsOrwVaC8/edit?gid=218786251#gid=218786251"},
    {"name": "Astro Naman (Kundli)", "gid": "644363953", "url": "https://docs.google.com/spreadsheets/d/1lnfU0PJhK749X3HKLgECls6-7z7AzLCFf7xsOrwVaC8/edit?gid=644363953#gid=644363953"},
    {"name": "AI Kundli", "gid": "174839660", "url": "https://docs.google.com/spreadsheets/d/1lnfU0PJhK749X3HKLgECls6-7z7AzLCFf7xsOrwVaC8/edit?gid=174839660#gid=174839660"},
    {"name": "Vedic Consultants", "gid": "1539574068", "url": "https://docs.google.com/spreadsheets/d/1lnfU0PJhK749X3HKLgECls6-7z7AzLCFf7xsOrwVaC8/edit?gid=1539574068#gid=1539574068"},
    {"name": "Live Darshan", "gid": "838748373", "url": "https://docs.google.com/spreadsheets/d/1lnfU0PJhK749X3HKLgECls6-7z7AzLCFf7xsOrwVaC8/edit?gid=838748373#gid=838748373"},
]


def _fetch_google_sheet_csv(spreadsheet_url: str, gid: str) -> List[Dict[str, str]]:
    # Supports normal sheet edit URL by converting to export CSV.
    base = spreadsheet_url.split("/edit")[0]
    csv_url = f"{base}/export?format=csv&gid={gid}"
    req = urlrequest.Request(csv_url, method="GET")
    with urlrequest.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
    rows: List[Dict[str, str]] = []
    reader = csv.DictReader(raw.splitlines())
    for row in reader:
        normalized: Dict[str, str] = {}
        for k, v in row.items():
            key = (k or "").strip()
            if not key:
                continue
            normalized[key] = (v or "").strip()
        if any(normalized.values()):
            rows.append(normalized)
    return rows


def _team_hint_from_tab(tab_name: str) -> str:
    t = tab_name.lower()
    if t in ("temples", "darshan", "puja", "yatra", "prasadam", "chadhava", "live darshan"):
        return "operations"
    if "astro" in t or "kundli" in t or "vedic consultants" in t:
        return "customer_support"
    return "sales"


def _normalize_sheet_row(tab_name: str, row: Dict[str, str], source_row: int, source_url: str, gid: str) -> Dict[str, Any]:
    title = row.get("Title") or row.get("Name") or row.get("Temple Name") or row.get("Package Name") or row.get("Service Type") or row.get("Feature") or row.get("ID") or f"{tab_name} Row {source_row}"
    category = row.get("Category") or row.get("Type") or tab_name
    service_type = row.get("Service Type") or row.get("Topic") or row.get("Type") or tab_name
    description = row.get("Description") or row.get("About") or row.get("Services Offered") or row.get("Key Aartis") or ""
    tags = [tab_name, category, service_type, row.get("Location", ""), row.get("Temple", ""), row.get("Deity", "")]
    tags = [t.strip() for t in tags if t and t.strip()]
    canonical_seed = row.get("Slug") or row.get("Page URL") or row.get("ID") or title
    canonical_key = f"{tab_name.lower().replace(' ', '_')}::{str(canonical_seed).lower().strip()}"
    return {
        "source_tab": tab_name,
        "source_gid": gid,
        "source_row": source_row,
        "source_url": source_url,
        "canonical_key": canonical_key[:255],
        "title": str(title)[:500],
        "category": str(category)[:255],
        "service_type": str(service_type)[:255],
        "team_hint": _team_hint_from_tab(tab_name),
        "description": str(description),
        "tags_json": {"tags": tags},
        "attrs_json": row,
    }


def _generate_blueprint_stub(req: BlueprintCreateRequest) -> Dict[str, Any]:
    docs = req.documents_text.lower()
    teams: List[str] = []
    if "sales" in docs:
        teams.append("Sales")
    if "support" in docs:
        teams.append("Support")
    if "ops" in docs or "operation" in docs or "operations" in docs:
        teams.append("Operations")
    if not teams:
        teams = ["General"]

    focus: List[str] = []
    for key in ["objection", "compliance", "sop", "escalation", "ticket", "resolution", "lead", "conversion"]:
        if key in docs:
            focus.append(key)
    if not focus:
        focus = ["sop_compliance", "workflow_execution"]

    # Small normalization
    normalized = []
    for f in focus:
        if f == "objection":
            normalized.append("objection_handling")
        elif f in ("compliance", "sop", "sop_compliance"):
            normalized.append("SOP_compliance")
        elif f == "escalation":
            normalized.append("escalation_decision_trees")
        elif f == "ticket":
            normalized.append("ticket_simulation")
        elif f in ("resolution", "resolution_time"):
            normalized.append("resolution_time_improvement")
        elif f in ("lead", "conversion", "conversion_rate"):
            normalized.append("conversion_rate_training")
        else:
            normalized.append(f)

    return {
        "teams": teams,
        "kpis": ["conversion_rate", "resolution_time"],
        "training_focus": normalized[:5],
        "simulation_required": True,
        "source": {
            "website_url": req.website_url,
            "questionnaire_keys": list((req.questionnaire or {}).keys())[:10],
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    if not settings.AI_API_KEY:
        raise RuntimeError("AI_API_KEY is not configured")

    body = json.dumps(
        {
            "model": settings.AI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
    ).encode("utf-8")
    base_url = settings.AI_BASE_URL.rstrip("/")
    provider = (settings.AI_PROVIDER or "").lower().strip()
    if provider == "groq" and "groq.com" not in base_url:
        base_url = "https://api.groq.com/openai/v1"
    elif provider == "openai" and "openai.com" not in base_url:
        base_url = "https://api.openai.com/v1"

    req = urlrequest.Request(
        f"{base_url}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.AI_API_KEY}",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return str(payload["choices"][0]["message"]["content"]).strip()
    except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM call failed: {exc}") from exc


def _generate_blueprint_ai(req: BlueprintCreateRequest) -> Dict[str, Any]:
    system_prompt = (
        "You generate compact LMS blueprints in strict JSON. "
        "Return keys: teams (array of strings), kpis (array), training_focus (array), simulation_required (boolean). "
        "Do not include markdown."
    )
    user_prompt = (
        f"Website: {req.website_url or 'N/A'}\n"
        f"Questionnaire: {json.dumps(req.questionnaire or {}, ensure_ascii=True)}\n"
        f"Documents:\n{req.documents_text[:6000]}"
    )
    text = _call_llm(system_prompt, user_prompt)
    parsed = json.loads(text)
    return {
        "teams": parsed.get("teams") or ["General"],
        "kpis": parsed.get("kpis") or ["conversion_rate", "resolution_time"],
        "training_focus": parsed.get("training_focus") or ["SOP_compliance", "workflow_execution"],
        "simulation_required": bool(parsed.get("simulation_required", True)),
        "source": {
            "website_url": req.website_url,
            "questionnaire_keys": list((req.questionnaire or {}).keys())[:10],
            "generator": "llm",
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def _build_lesson_content(team: str, focus_topic: str, kpis: List[str]) -> str:
    return (
        f"Team context: {team}\n\n"
        f"Focus topic: {focus_topic}\n\n"
        "Learning goals:\n"
        f"- Apply {focus_topic.replace('_', ' ')} using tenant SOP patterns.\n"
        f"- Improve KPI signals: {', '.join(kpis[:2]) if kpis else 'core business outcomes'}.\n"
        "- Practice with scenario-based responses and self-review prompts.\n\n"
        "Practice task:\n"
        f"Write a short response for a realistic {team.lower()} scenario that demonstrates {focus_topic.replace('_', ' ')}."
    )


def _build_lesson_content_ai(team: str, focus_topic: str, kpis: List[str]) -> str:
    prompt = (
        "Generate a practical LMS lesson in plain text with sections:\n"
        "1) context\n2) learning goals (3 bullets)\n3) role-play scenario\n4) self-check question.\n"
        f"Team: {team}\nFocus: {focus_topic}\nKPIs: {', '.join(kpis[:3])}"
    )
    return _call_llm("You are a corporate L&D assistant.", prompt)


def _generate_lms_stub(tenant_id: UUID, blueprint_json: Dict[str, Any], db: Session) -> None:
    teams = blueprint_json.get("teams") or ["General"]
    focus = blueprint_json.get("training_focus") or ["sop_compliance"]
    kpis = blueprint_json.get("kpis") or ["completion_rate", "quality_score"]

    course = Course(
        tenant_id=tenant_id,
        title=f"Adaptive Training: {', '.join(teams[:2])}",
        description="Generated from company blueprint (Phase 2 adaptive template).",
    )
    db.add(course)
    db.flush()

    # One module per team (max 3 for scaffolding)
    modules: List[Module] = []
    for i, tname in enumerate(teams[:3]):
        mod = Module(tenant_id=tenant_id, course_id=course.id, title=f"{tname} Track", order_index=i)
        db.add(mod)
        db.flush()
        modules.append(mod)

    for i, mod in enumerate(modules):
        primary_focus = focus[i % len(focus)]
        secondary_focus = focus[(i + 1) % len(focus)]
        try:
            foundation_text = _build_lesson_content_ai(teams[i % len(teams)], primary_focus, kpis)
            scenario_text = _build_lesson_content_ai(teams[i % len(teams)], secondary_focus, kpis)
        except RuntimeError:
            foundation_text = _build_lesson_content(teams[i % len(teams)], primary_focus, kpis)
            scenario_text = _build_lesson_content(teams[i % len(teams)], secondary_focus, kpis)

        db.add(
            Lesson(
                tenant_id=tenant_id,
                module_id=mod.id,
                title=f"{mod.title}: Foundations",
                content_text=foundation_text,
            )
        )
        db.add(
            Lesson(
                tenant_id=tenant_id,
                module_id=mod.id,
                title=f"{mod.title}: Applied Scenario",
                content_text=scenario_text,
            )
        )

    assessment = Assessment(
        tenant_id=tenant_id,
        title="Knowledge Check (Generated)",
        assessment_type="quiz",
    )
    db.add(assessment)
    db.flush()

    # Minimal question set for scaffolding.
    questions = [
        {
            "q": "What is the primary goal of adaptive AI tutoring in this LMS?",
            "opts": {"a": "Only static content delivery", "b": "Role-aware coaching with feedback", "c": "Random guidance", "d": "No feedback"},
            "correct": 1,
        },
        {
            "q": "How does the LMS decide what training to recommend next?",
            "opts": {"a": "Always the same sequence", "b": "Skill outcomes and scorecards", "c": "Based on user’s browser type", "d": "Not adaptive at all"},
            "correct": 1,
        },
        {
            "q": "What will Phase 3 connect training to?",
            "opts": {"a": "Only lesson duration", "b": "Real KPIs and performance metrics", "c": "User timezone", "d": "No performance linkage"},
            "correct": 1,
        },
    ]
    for item in questions:
        db.add(
            AssessmentQuestion(
                tenant_id=tenant_id,
                assessment_id=assessment.id,
                question_text=item["q"],
                options_json=item["opts"],
                correct_answer_index=item["correct"],
            )
        )


def _xp_to_level(xp_points: int) -> int:
    # Linear level formula for a predictable scaffold.
    return max(1, (xp_points // 100) + 1)


def _ensure_gamification_profile(tenant_id: UUID, user_id: UUID, db: Session) -> UserGamification:
    profile = db.scalar(
        select(UserGamification).where(
            UserGamification.tenant_id == tenant_id,
            UserGamification.user_id == user_id,
        )
    )
    if profile:
        return profile
    profile = UserGamification(tenant_id=tenant_id, user_id=user_id, xp_points=0, level=1, badges_count=0, streak_days=0)
    db.add(profile)
    db.flush()
    return profile


def _award_badge_if_missing(tenant_id: UUID, user_id: UUID, badge_code: str, badge_name: str, db: Session) -> bool:
    existing = db.scalar(
        select(UserBadge).where(
            UserBadge.tenant_id == tenant_id,
            UserBadge.user_id == user_id,
            UserBadge.badge_code == badge_code,
        )
    )
    if existing:
        return False
    db.add(UserBadge(tenant_id=tenant_id, user_id=user_id, badge_code=badge_code, badge_name=badge_name))
    return True


def _recompute_badges_count(tenant_id: UUID, user_id: UUID, db: Session) -> int:
    badges = db.scalars(select(UserBadge).where(UserBadge.tenant_id == tenant_id, UserBadge.user_id == user_id)).all()
    return len(badges)


def _create_async_job(
    *,
    tenant_id: UUID,
    created_by_user_id: UUID,
    job_type: str,
    payload_json: Dict[str, Any],
    db: Session,
) -> AsyncJob:
    job = AsyncJob(
        tenant_id=tenant_id,
        created_by_user_id=created_by_user_id,
        job_type=job_type,
        status="queued",
        payload_json=payload_json,
    )
    db.add(job)
    db.flush()
    return job


def _ensure_tenant_profile(tenant_id: UUID, db: Session) -> TenantProfile:
    profile = db.scalar(select(TenantProfile).where(TenantProfile.tenant_id == tenant_id))
    if profile:
        return profile
    profile = TenantProfile(
        tenant_id=tenant_id,
        business_domain="pilgrimage_services",
        role_template_json={
            "admin": ["tenant_admin", "analytics", "configuration"],
            "manager": ["training_manager", "operations_coach"],
            "employee": ["learner", "support_exec"],
        },
        taxonomy_mapping_json={"tabs_to_domains": {"Temples": "catalog", "Darshan": "service", "Puja": "rituals"}},
        generation_prefs_json={"tone": "clear_practical", "audience": "employee"},
        connectors_json={"primary": "google_sheets"},
        labels_json={"tenant_display_name": "Namadarshan"},
    )
    db.add(profile)
    db.flush()
    return profile


def _build_blueprint_from_knowledge(tenant_id: UUID, db: Session) -> Dict[str, Any]:
    rows = db.scalars(select(KnowledgeItem).where(KnowledgeItem.tenant_id == tenant_id)).all()
    if not rows:
        return {
            "teams": ["Sales", "Support", "Operations"],
            "kpis": ["conversion_rate", "resolution_time", "first_response_time"],
            "training_focus": ["service_knowledge", "SOP_compliance", "customer_clarity"],
            "simulation_required": True,
            "source": {"generator": "knowledge_empty_fallback"},
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
    team_counts = Counter([r.team_hint for r in rows if r.team_hint])
    domain_counts = Counter([r.source_tab for r in rows])
    top_domains = [d for d, _ in domain_counts.most_common(6)]
    top_teams = [t for t, _ in team_counts.most_common(3)] or ["operations", "customer_support", "sales"]
    team_map = {"operations": "Operations", "customer_support": "Support", "sales": "Sales"}
    teams = [team_map.get(t, t.title()) for t in top_teams]
    return {
        "teams": teams,
        "kpis": ["conversion_rate", "resolution_time", "customer_satisfaction"],
        "training_focus": [f"{d.lower().replace(' ', '_')}_handling" for d in top_domains[:5]],
        "simulation_required": True,
        "source": {"generator": "knowledge_items", "items_count": len(rows), "tabs": top_domains},
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/api/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # Note: we keep auth logic in a single file for Phase 1 scaffolding speed.
    # We use the db dependency from deps.py.
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(str(user.id), {"tenant_id": str(user.tenant_id), "role": user.role})
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "is_active": user.is_active,
        },
    )


@app.get("/api/me")
def me(current: User = Depends(get_current_user)):
    return {
        "id": current.id,
        "email": current.email,
        "full_name": current.full_name,
        "role": current.role,
        "tenant_id": current.tenant_id,
        "is_active": current.is_active,
    }


@app.post("/api/auth/google")
def google_auth_stub():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google OAuth not implemented in Phase 1 scaffolding")


@app.get("/api/tenant/profile", response_model=TenantProfileOut)
def get_tenant_profile(
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    profile = _ensure_tenant_profile(current.tenant_id, db)
    db.commit()
    return profile


@app.put("/api/tenant/profile", response_model=TenantProfileOut)
def upsert_tenant_profile(
    payload: TenantProfileUpsertRequest,
    current: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    profile = _ensure_tenant_profile(current.tenant_id, db)
    profile.business_domain = payload.business_domain
    profile.role_template_json = payload.role_template_json
    profile.taxonomy_mapping_json = payload.taxonomy_mapping_json
    profile.generation_prefs_json = payload.generation_prefs_json
    profile.connectors_json = payload.connectors_json
    profile.labels_json = payload.labels_json
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


@app.post("/api/tenant-data/sync", response_model=TenantDataSyncOut)
def sync_tenant_data(
    payload: TenantDataSyncRequest,
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    tabs = payload.tabs or [
        {"name": item["name"], "url": item["url"], "gid": item["gid"]} for item in DEFAULT_NAMADARSHAN_TABS
    ]
    synced_tabs = 0
    upserted = 0
    for tab in tabs:
        tab_name = str(tab["name"]).strip()
        tab_url = str(tab["url"]).strip()
        tab_gid = str(tab["gid"]).strip()
        rows = _fetch_google_sheet_csv(tab_url, tab_gid)
        synced_tabs += 1
        for idx, row in enumerate(rows, start=2):
            normalized = _normalize_sheet_row(tab_name, row, idx, tab_url, tab_gid)
            existing = db.scalar(
                select(KnowledgeItem).where(
                    KnowledgeItem.tenant_id == current.tenant_id,
                    KnowledgeItem.source_tab == normalized["source_tab"],
                    KnowledgeItem.canonical_key == normalized["canonical_key"],
                )
            )
            if not existing:
                existing = KnowledgeItem(
                    tenant_id=current.tenant_id,
                    source_kind="google_sheet",
                    source_tab=normalized["source_tab"],
                    source_gid=normalized["source_gid"],
                    source_row=normalized["source_row"],
                    source_url=normalized["source_url"],
                    canonical_key=normalized["canonical_key"],
                )
                db.add(existing)
            existing.title = normalized["title"]
            existing.category = normalized["category"]
            existing.service_type = normalized["service_type"]
            existing.team_hint = normalized["team_hint"]
            existing.description = normalized["description"]
            existing.tags_json = normalized["tags_json"]
            existing.attrs_json = normalized["attrs_json"]
            existing.updated_at = datetime.utcnow()
            upserted += 1
    db.commit()
    return TenantDataSyncOut(ok=True, synced_tabs=synced_tabs, upserted_items=upserted)


@app.get("/api/knowledge-items", response_model=List[KnowledgeItemOut])
def list_knowledge_items(
    tab: str = "",
    limit: int = 100,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(KnowledgeItem).where(KnowledgeItem.tenant_id == current.tenant_id)
    if tab.strip():
        stmt = stmt.where(KnowledgeItem.source_tab == tab.strip())
    stmt = stmt.order_by(KnowledgeItem.updated_at.desc()).limit(max(1, min(limit, 500)))
    return db.scalars(stmt).all()


@app.get("/api/knowledge/stats", response_model=KnowledgeStatsOut)
def knowledge_stats(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(KnowledgeItem).where(KnowledgeItem.tenant_id == current.tenant_id)).all()
    by_tab = Counter([r.source_tab for r in rows])
    by_team = Counter([r.team_hint for r in rows])
    return KnowledgeStatsOut(
        total_items=len(rows),
        by_tab=dict(by_tab),
        by_team_hint=dict(by_team),
    )


@app.post("/api/onboarding/blueprint/from-knowledge", response_model=BlueprintOut)
def create_blueprint_from_knowledge(
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    blueprint = CompanyBlueprint(
        tenant_id=current.tenant_id,
        version=1,
        blueprint_json=_build_blueprint_from_knowledge(current.tenant_id, db),
        source_refs_json={"type": "knowledge_items"},
    )
    db.add(blueprint)
    db.commit()
    db.refresh(blueprint)
    return blueprint


@app.post("/api/onboarding/blueprint", response_model=BlueprintOut)
def create_blueprint(
    payload: BlueprintCreateRequest,
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    try:
        blueprint_json = _generate_blueprint_ai(payload)
    except Exception:
        blueprint_json = _generate_blueprint_stub(payload)
    blueprint = CompanyBlueprint(tenant_id=current.tenant_id, version=1, blueprint_json=blueprint_json)
    db.add(blueprint)
    db.commit()
    db.refresh(blueprint)
    return blueprint


@app.get("/api/onboarding/blueprints", response_model=List[BlueprintOut])
def list_blueprints(
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(CompanyBlueprint)
        .where(CompanyBlueprint.tenant_id == current.tenant_id)
        .order_by(CompanyBlueprint.created_at.desc())
    ).all()
    return rows


@app.post("/api/onboarding/generate-lms", response_model=JobEnqueueOut)
def generate_lms(
    payload: GenerateLmsRequest,
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    blueprint = db.scalar(
        select(CompanyBlueprint).where(CompanyBlueprint.id == payload.blueprint_id, CompanyBlueprint.tenant_id == current.tenant_id)
    )
    if not blueprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found")

    job = _create_async_job(
        tenant_id=current.tenant_id,
        created_by_user_id=current.id,
        job_type="generate_lms",
        payload_json={"blueprint_id": str(blueprint.id)},
        db=db,
    )
    db.commit()
    try:
        generate_lms_job.delay(str(job.id), str(current.tenant_id), str(blueprint.id))
    except Exception:
        # Fallback when queue infra is unavailable in local/dev.
        generate_lms_job(str(job.id), str(current.tenant_id), str(blueprint.id))
    return JobEnqueueOut(job_id=job.id, status="queued", message="LMS generation job queued")


@app.get("/api/jobs/{job_id}", response_model=JobStatusOut)
def get_job_status(
    job_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.scalar(select(AsyncJob).where(AsyncJob.id == job_id, AsyncJob.tenant_id == current.tenant_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobStatusOut(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        result_json=job.result_json or {},
        error_message=job.error_message or "",
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@app.get("/api/courses", response_model=List[CourseOut])
def list_courses(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    courses = db.scalars(select(Course).where(Course.tenant_id == current.tenant_id)).all()
    return courses


@app.post("/api/courses", response_model=CourseOut)
def create_course(
    payload: CourseCreateRequest,
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    course = Course(tenant_id=current.tenant_id, title=payload.title, description=payload.description)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@app.get("/api/courses/{course_id}/modules", response_model=List[ModuleOut])
def list_modules(
    course_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    modules = db.scalars(select(Module).where(Module.tenant_id == current.tenant_id, Module.course_id == course_id)).all()
    return modules


@app.post("/api/courses/{course_id}/modules", response_model=ModuleOut)
def create_module(
    course_id: UUID,
    payload: ModuleCreateRequest,
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    course = db.scalar(select(Course).where(Course.tenant_id == current.tenant_id, Course.id == course_id))
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    mod = Module(
        tenant_id=current.tenant_id,
        course_id=course_id,
        title=payload.title,
        order_index=payload.order_index,
    )
    db.add(mod)
    db.commit()
    db.refresh(mod)
    return mod


@app.get("/api/modules/{module_id}/lessons", response_model=List[LessonOut])
def list_lessons(
    module_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lessons = db.scalars(select(Lesson).where(Lesson.tenant_id == current.tenant_id, Lesson.module_id == module_id)).all()
    return lessons


@app.post("/api/modules/{module_id}/lessons", response_model=LessonOut)
def create_lesson(
    module_id: UUID,
    payload: LessonCreateRequest,
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    module = db.scalar(select(Module).where(Module.tenant_id == current.tenant_id, Module.id == module_id))
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    lesson = Lesson(
        tenant_id=current.tenant_id,
        module_id=module_id,
        title=payload.title,
        content_text=payload.content_text,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@app.get("/api/assessments", response_model=List[AssessmentOut])
def list_assessments(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assessments = db.scalars(select(Assessment).where(Assessment.tenant_id == current.tenant_id)).all()
    return assessments


@app.get("/api/assessments/{assessment_id}/questions", response_model=List[AssessmentQuestionOut])
def list_assessment_questions(
    assessment_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(AssessmentQuestion).where(AssessmentQuestion.tenant_id == current.tenant_id, AssessmentQuestion.assessment_id == assessment_id)
    ).all()
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No questions found")
    return rows


@app.post("/api/submissions", response_model=AssessmentSubmissionOut)
def submit_assessment(
    payload: AssessmentSubmissionRequest,
    current: User = Depends(require_roles("employee", "manager", "admin")),
    db: Session = Depends(get_db),
):
    assessment = db.scalar(select(Assessment).where(Assessment.tenant_id == current.tenant_id, Assessment.id == payload.assessment_id))
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    questions = db.scalars(
        select(AssessmentQuestion).where(AssessmentQuestion.tenant_id == current.tenant_id, AssessmentQuestion.assessment_id == payload.assessment_id)
    ).all()
    if not questions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assessment has no questions")

    correct = 0
    # answers_json stores: {question_id: selected_index}
    for q in questions:
        selected = payload.answers.get(str(q.id)) if payload.answers else None
        # Fallback: allow question_id as raw UUID string
        if selected is None:
            continue
        if int(selected) == q.correct_answer_index:
            correct += 1

    score = int(round(100 * correct / len(questions)))
    submission = AssessmentSubmission(
        tenant_id=current.tenant_id,
        user_id=current.id,
        assessment_id=payload.assessment_id,
        answers_json=payload.answers,
        score=score,
    )
    db.add(submission)

    # Update a simple skill scorecard (Phase 1 stub)
    skill_name = "general_knowledge"
    card = db.scalar(
        select(SkillScorecard).where(SkillScorecard.tenant_id == current.tenant_id, SkillScorecard.user_id == current.id, SkillScorecard.skill_name == skill_name)
    )
    if not card:
        card = SkillScorecard(tenant_id=current.tenant_id, user_id=current.id, skill_name=skill_name, score=score, last_updated_at=datetime.utcnow())
        db.add(card)
    else:
        card.score = score
        card.last_updated_at = datetime.utcnow()

    # Phase 4 gamification: assessment gives XP and milestone badges.
    profile = _ensure_gamification_profile(current.tenant_id, current.id, db)
    gained_xp = 40 if score >= 80 else 25 if score >= 60 else 15
    profile.xp_points += gained_xp
    profile.level = _xp_to_level(profile.xp_points)
    profile.last_activity_at = datetime.utcnow()
    if score >= 90:
        _award_badge_if_missing(current.tenant_id, current.id, "quiz_master", "Quiz Master", db)
    if profile.level >= 3:
        _award_badge_if_missing(current.tenant_id, current.id, "level_3", "Level 3 Achiever", db)
    profile.badges_count = _recompute_badges_count(current.tenant_id, current.id, db)
    db.commit()
    db.refresh(submission)
    return submission


@app.post("/api/progress/lesson-complete")
def complete_lesson(
    payload: LessonCompleteRequest,
    current: User = Depends(require_roles("employee", "manager", "admin")),
    db: Session = Depends(get_db),
):
    lesson = db.scalar(select(Lesson).where(Lesson.tenant_id == current.tenant_id, Lesson.id == payload.lesson_id))
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    existing = db.scalar(
        select(LessonProgress).where(
            LessonProgress.tenant_id == current.tenant_id,
            LessonProgress.user_id == current.id,
            LessonProgress.lesson_id == payload.lesson_id,
        )
    )
    if not existing:
        db.add(LessonProgress(tenant_id=current.tenant_id, user_id=current.id, lesson_id=payload.lesson_id))
        profile = _ensure_gamification_profile(current.tenant_id, current.id, db)
        profile.xp_points += 15
        profile.level = _xp_to_level(profile.xp_points)
        profile.last_activity_at = datetime.utcnow()
        # Lightweight streak scaffold: increment when learner interacts.
        profile.streak_days += 1
        if profile.streak_days >= 3:
            _award_badge_if_missing(current.tenant_id, current.id, "streak_3", "3-Day Momentum", db)
        if profile.xp_points >= 100:
            _award_badge_if_missing(current.tenant_id, current.id, "xp_100", "100 XP Milestone", db)
        profile.badges_count = _recompute_badges_count(current.tenant_id, current.id, db)
    db.commit()
    return {"ok": True}


@app.get("/api/progress", response_model=ProgressOut)
def get_progress(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    progress_rows = db.scalars(
        select(LessonProgress).where(LessonProgress.tenant_id == current.tenant_id, LessonProgress.user_id == current.id)
    ).all()
    completed = [row.lesson_id for row in progress_rows]

    skill_rows = db.scalars(
        select(SkillScorecard).where(SkillScorecard.tenant_id == current.tenant_id, SkillScorecard.user_id == current.id)
    ).all()
    last_scores = [{"skill_name": r.skill_name, "score": r.score, "updated_at": r.last_updated_at} for r in skill_rows]

    return ProgressOut(completed_lesson_ids=completed, last_scores=last_scores)


@app.get("/api/recommendations/next-lessons", response_model=RecommendationOut)
def get_next_lessons(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    completed_rows = db.scalars(
        select(LessonProgress.lesson_id).where(
            LessonProgress.tenant_id == current.tenant_id,
            LessonProgress.user_id == current.id,
        )
    ).all()
    completed_ids = set(completed_rows)

    lessons = db.scalars(select(Lesson).where(Lesson.tenant_id == current.tenant_id).order_by(Lesson.created_at.asc())).all()
    average_score = None
    scores = db.scalars(
        select(SkillScorecard.score).where(
            SkillScorecard.tenant_id == current.tenant_id,
            SkillScorecard.user_id == current.id,
        )
    ).all()
    if scores:
        average_score = sum(scores) / len(scores)

    if average_score is not None and average_score < 60:
        lessons = sorted(
            lessons,
            key=lambda l: 0 if "Foundations" in l.title else 1,
        )

    recommendations: List[LessonRecommendationOut] = []
    for lesson in lessons:
        if lesson.id in completed_ids:
            continue
        if average_score is None:
            reason = "Start here to build your adaptive learning path."
        elif average_score < 60:
            reason = "Recommended first due to current skill score trend."
        elif average_score < 80:
            reason = "Recommended to improve consistency before advanced topics."
        else:
            reason = "Next best lesson to maintain momentum."
        recommendations.append(
            LessonRecommendationOut(
                lesson_id=lesson.id,
                module_id=lesson.module_id,
                title=lesson.title,
                reason=reason,
            )
        )
        if len(recommendations) >= 3:
            break

    return RecommendationOut(next_lessons=recommendations)


@app.post("/api/tutor/feedback", response_model=JobEnqueueOut)
def tutor_feedback(
    payload: TutorFeedbackRequest,
    current: User = Depends(require_roles("employee", "manager", "admin")),
    db: Session = Depends(get_db),
):
    lesson = db.scalar(select(Lesson).where(Lesson.tenant_id == current.tenant_id, Lesson.id == payload.lesson_id))
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    job = _create_async_job(
        tenant_id=current.tenant_id,
        created_by_user_id=current.id,
        job_type="tutor_feedback",
        payload_json={"lesson_id": str(lesson.id)},
        db=db,
    )
    db.commit()
    try:
        tutor_feedback_job.delay(
            str(job.id),
            lesson.title,
            lesson.content_text,
            payload.learner_answer,
            json.dumps(lesson.source_refs_json or {}, ensure_ascii=True),
        )
    except Exception:
        tutor_feedback_job(
            str(job.id),
            lesson.title,
            lesson.content_text,
            payload.learner_answer,
            json.dumps(lesson.source_refs_json or {}, ensure_ascii=True),
        )
    return JobEnqueueOut(job_id=job.id, status="queued", message="Tutor feedback job queued")


@app.post("/api/simulations/start", response_model=SimulationScenarioOut)
def start_simulation(
    payload: SimulationStartRequest,
    current: User = Depends(require_roles("employee", "manager", "admin")),
    db: Session = Depends(get_db),
):
    source_refs: Dict[str, Any] = {}
    if payload.blueprint_id:
        blueprint = db.scalar(
            select(CompanyBlueprint).where(
                CompanyBlueprint.id == payload.blueprint_id,
                CompanyBlueprint.tenant_id == current.tenant_id,
            )
        )
        if not blueprint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found")
        source_refs = {"blueprint_id": str(blueprint.id)}

    team = payload.team.strip()
    focus = payload.focus_topic.strip()
    prompt = (
        f"You are in a realistic {team} scenario.\n"
        f"Focus area: {focus}\n"
        "Customer says: \"I am not convinced this process helps me.\"\n"
        "Respond with a professional, measurable, SOP-aligned answer."
    )
    scenario = SimulationScenario(
        tenant_id=current.tenant_id,
        blueprint_id=payload.blueprint_id,
        title=f"{team} Simulation - {focus}",
        team=team,
        focus_topic=focus,
        prompt_text=prompt,
        expected_outcomes_json={"criteria": ["clarity", "SOP alignment", "KPI orientation"]},
        source_refs_json=source_refs,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@app.post("/api/simulations/submit", response_model=JobEnqueueOut)
def submit_simulation(
    payload: SimulationSubmitRequest,
    current: User = Depends(require_roles("employee", "manager", "admin")),
    db: Session = Depends(get_db),
):
    scenario = db.scalar(
        select(SimulationScenario).where(
            SimulationScenario.id == payload.scenario_id,
            SimulationScenario.tenant_id == current.tenant_id,
        )
    )
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation scenario not found")

    attempt = SimulationAttempt(
        tenant_id=current.tenant_id,
        user_id=current.id,
        scenario_id=scenario.id,
        user_response_text=payload.user_response_text,
        status="pending",
    )
    db.add(attempt)
    db.flush()
    job = _create_async_job(
        tenant_id=current.tenant_id,
        created_by_user_id=current.id,
        job_type="simulation_evaluate",
        payload_json={"attempt_id": str(attempt.id), "scenario_id": str(scenario.id)},
        db=db,
    )
    db.commit()
    try:
        simulation_evaluate_job.delay(str(job.id), str(attempt.id), scenario.prompt_text, payload.user_response_text)
    except Exception:
        simulation_evaluate_job(str(job.id), str(attempt.id), scenario.prompt_text, payload.user_response_text)
    return JobEnqueueOut(job_id=job.id, status="queued", message="Simulation evaluation job queued")


@app.get("/api/simulations/attempts/{attempt_id}", response_model=SimulationAttemptOut)
def get_simulation_attempt(
    attempt_id: UUID,
    current: User = Depends(require_roles("employee", "manager", "admin")),
    db: Session = Depends(get_db),
):
    attempt = db.scalar(
        select(SimulationAttempt).where(
            SimulationAttempt.id == attempt_id,
            SimulationAttempt.tenant_id == current.tenant_id,
        )
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation attempt not found")
    return attempt


@app.post("/api/kpi/ingest", response_model=KpiIngestOut)
def ingest_kpi(
    payload: KpiIngestRequest,
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.tenant_id == current.tenant_id, User.id == payload.user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    updated: List[Dict[str, Any]] = []
    for metric_name, raw_value in payload.metrics.items():
        score = max(0, min(100, int(round(float(raw_value)))))
        card = db.scalar(
            select(SkillScorecard).where(
                SkillScorecard.tenant_id == current.tenant_id,
                SkillScorecard.user_id == user.id,
                SkillScorecard.skill_name == metric_name,
            )
        )
        if not card:
            card = SkillScorecard(
                tenant_id=current.tenant_id,
                user_id=user.id,
                skill_name=metric_name,
                score=score,
                last_updated_at=datetime.utcnow(),
            )
            db.add(card)
        else:
            card.score = score
            card.last_updated_at = datetime.utcnow()
        updated.append({"skill_name": metric_name, "score": score})

    db.commit()
    return KpiIngestOut(ok=True, updated_skills=updated)


@app.get("/api/analytics/tenant")
def tenant_analytics(
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    users = db.scalars(select(User).where(User.tenant_id == current.tenant_id)).all()
    attempts = db.scalars(select(SimulationAttempt).where(SimulationAttempt.tenant_id == current.tenant_id)).all()
    submissions = db.scalars(select(AssessmentSubmission).where(AssessmentSubmission.tenant_id == current.tenant_id)).all()
    lessons_done = db.scalars(select(LessonProgress).where(LessonProgress.tenant_id == current.tenant_id)).all()
    cards = db.scalars(select(SkillScorecard).where(SkillScorecard.tenant_id == current.tenant_id)).all()
    knowledge = db.scalars(select(KnowledgeItem).where(KnowledgeItem.tenant_id == current.tenant_id)).all()

    avg_quiz = round(sum(s.score for s in submissions) / len(submissions), 2) if submissions else 0
    avg_sim = round(sum(a.score for a in attempts if a.status == "completed") / max(1, len([a for a in attempts if a.status == "completed"])), 2) if attempts else 0

    weak_skills = sorted(cards, key=lambda c: c.score)[:5]
    weak_skill_payload = [{"skill_name": c.skill_name, "score": c.score, "user_id": str(c.user_id)} for c in weak_skills]
    by_tab = dict(Counter([k.source_tab for k in knowledge]))

    return {
        "users_count": len(users),
        "knowledge_items": len(knowledge),
        "knowledge_by_tab": by_tab,
        "lesson_completions": len(lessons_done),
        "assessments_submitted": len(submissions),
        "avg_assessment_score": avg_quiz,
        "simulations_completed": len([a for a in attempts if a.status == "completed"]),
        "avg_simulation_score": avg_sim,
        "weak_skills": weak_skill_payload,
    }


@app.get("/api/gamification/me", response_model=GamificationProfileOut)
def gamification_me(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _ensure_gamification_profile(current.tenant_id, current.id, db)
    badges = db.scalars(
        select(UserBadge)
        .where(UserBadge.tenant_id == current.tenant_id, UserBadge.user_id == current.id)
        .order_by(UserBadge.awarded_at.desc())
    ).all()
    db.commit()
    return GamificationProfileOut(
        user_id=current.id,
        xp_points=profile.xp_points,
        level=profile.level,
        badges_count=profile.badges_count,
        streak_days=profile.streak_days,
        badges=[BadgeOut(badge_code=b.badge_code, badge_name=b.badge_name, awarded_at=b.awarded_at) for b in badges],
    )


@app.get("/api/gamification/leaderboard", response_model=LeaderboardOut)
def gamification_leaderboard(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(UserGamification).where(UserGamification.tenant_id == current.tenant_id).order_by(UserGamification.xp_points.desc())
    ).all()
    user_ids = [r.user_id for r in rows[:10]]
    users = db.scalars(select(User).where(User.tenant_id == current.tenant_id, User.id.in_(user_ids))).all() if user_ids else []
    user_map = {u.id: u for u in users}
    leaderboard = []
    for row in rows[:10]:
        user = user_map.get(row.user_id)
        if not user:
            continue
        leaderboard.append(
            LeaderboardRowOut(
                user_id=row.user_id,
                full_name=user.full_name,
                role=user.role,
                xp_points=row.xp_points,
                level=row.level,
                badges_count=row.badges_count,
            )
        )
    return LeaderboardOut(leaderboard=leaderboard)


@app.post("/api/integrations/webhooks", response_model=WebhookOut)
def create_integration_webhook(
    payload: WebhookCreateRequest,
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    webhook = IntegrationWebhook(
        tenant_id=current.tenant_id,
        provider=payload.provider.strip().lower(),
        target_url=payload.target_url.strip(),
        event_name=payload.event_name.strip().lower(),
        is_active=True,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@app.get("/api/integrations/webhooks", response_model=List[WebhookOut])
def list_integration_webhooks(
    current: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(IntegrationWebhook)
        .where(IntegrationWebhook.tenant_id == current.tenant_id)
        .order_by(IntegrationWebhook.created_at.desc())
    ).all()
    return rows


@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "ai-lms-backend", "timestamp": datetime.utcnow().isoformat() + "Z"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    db.scalar(select(User.id).limit(1))
    redis_client = Redis.from_url(settings.REDIS_URL)
    redis_client.ping()
    return {"ok": True, "db": "reachable", "redis": "reachable"}

