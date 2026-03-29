import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def uuid_pk() -> uuid.UUID:
    return uuid.uuid4()


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    # Roles for Phase 1:
    # admin -> Admin dashboard
    # manager -> Manager dashboard
    # employee -> Employee dashboard
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="users")


class CompanyBlueprint(Base):
    __tablename__ = "company_blueprints"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    blueprint_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_refs_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("modules.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_refs_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(50), default="quiz", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessments.id"), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Options: ["a", "b", "c", "d"]
    options_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # correct_answer_index: 0..N-1
    correct_answer_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AssessmentSubmission(Base):
    __tablename__ = "assessment_submissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessments.id"), nullable=False, index=True)
    answers_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    lesson_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lessons.id"), nullable=False, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class SkillScorecard(Base):
    __tablename__ = "skill_scorecards"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class UserGamification(Base):
    __tablename__ = "user_gamification"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    xp_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    badges_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class UserBadge(Base):
    __tablename__ = "user_badges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    badge_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    badge_name: Mapped[str] = mapped_column(String(255), nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class IntegrationWebhook(Base):
    __tablename__ = "integration_webhooks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    event_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AsyncJob(Base):
    __tablename__ = "async_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class SimulationScenario(Base):
    __tablename__ = "simulation_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    blueprint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_blueprints.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    team: Mapped[str] = mapped_column(String(100), nullable=False)
    focus_topic: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_outcomes_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_refs_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class SimulationAttempt(Base):
    __tablename__ = "simulation_attempts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid_pk)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulation_scenarios.id"), nullable=False, index=True)
    user_response_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

