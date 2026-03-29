import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.db import Base, SessionLocal, engine
from app.models import (
    Course,
    CompanyBlueprint,
    Lesson,
    LessonProgress,
    Module,
    Assessment,
    AssessmentQuestion,
    SkillScorecard,
    Tenant,
    User,
)


def init_db() -> None:
    # For Phase 1 scaffolding we create tables directly.
    Base.metadata.create_all(bind=engine)


def seed_demo_data() -> None:
    # Only seed if empty to avoid duplication on reload.
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).limit(1))
        if not tenant:
            tenant = Tenant(id=uuid.uuid4(), name="Demo College")
            db.add(tenant)
            db.flush()

        # Reconcile demo user roles on every startup (important during early refactors).
        demo_users = [
            ("admin@gmail.com", "Demo Admin", "admin", "admin@123"),
            ("manager@gmail.com", "Demo Manager", "manager", "manager@123"),
            ("employee@gmail.com", "Demo Employee", "employee", "employee@123"),
        ]
        for email, full_name, role, raw_password in demo_users:
            user = db.scalar(select(User).where(User.email == email, User.tenant_id == tenant.id))
            if not user:
                user = User(
                    tenant_id=tenant.id,
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password(raw_password),
                    role=role,
                    is_active=True,
                )
                db.add(user)
            else:
                user.full_name = full_name
                user.password_hash = hash_password(raw_password)
                user.role = role
                user.is_active = True
        db.flush()

        blueprint_exists = db.scalar(
            select(CompanyBlueprint.id).where(CompanyBlueprint.tenant_id == tenant.id).limit(1)
        )
        if not blueprint_exists:
            # Create a small starter blueprint + LMS skeleton.
            blueprint = CompanyBlueprint(
                tenant_id=tenant.id,
                version=1,
                blueprint_json={
                    "teams": ["Sales", "Support"],
                    "kpis": ["conversion_rate", "resolution_time"],
                    "training_focus": ["objection_handling", "SOP_compliance"],
                    "simulation_required": True,
                },
            )
            db.add(blueprint)
            db.flush()

            course = Course(tenant_id=tenant.id, title="Adaptive Onboarding (Demo)", description="Starter course")
            db.add(course)
            db.flush()

            module = Module(tenant_id=tenant.id, course_id=course.id, title="Core Concepts", order_index=0)
            db.add(module)
            db.flush()

            lesson = Lesson(
                tenant_id=tenant.id,
                module_id=module.id,
                title="Welcome to the LMS",
                content_text="This is a scaffolded lesson. Phase 1 will populate lessons via blueprint generation.",
            )
            db.add(lesson)

            assessment = Assessment(tenant_id=tenant.id, title="Quick Knowledge Check", assessment_type="quiz")
            db.add(assessment)
            db.flush()

            # One question for scaffolding.
            q = AssessmentQuestion(
                tenant_id=tenant.id,
                assessment_id=assessment.id,
                question_text="What does the AI Tutor primarily provide?",
                options_json={"a": "Static content only", "b": "Role-aware tutoring", "c": "Random feedback", "d": "No feedback"},
                correct_answer_index=1,
            )
            db.add(q)
            db.flush()

        db.commit()


def safe_init() -> None:
    init_db()
    seed_demo_data()

