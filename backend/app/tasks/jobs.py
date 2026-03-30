from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.db import SessionLocal
from app.models import (
    AsyncJob,
    CompanyBlueprint,
    Course,
    Module,
    Lesson,
    Assessment,
    AssessmentQuestion,
    SimulationScenario,
    SimulationAttempt,
    KnowledgeItem,
)
from app.services.ai_service import call_llm, build_lesson_content


def _set_job_status(job_id: UUID, status: str, *, result_json: dict | None = None, error_message: str = "") -> None:
    with SessionLocal() as db:
        job = db.scalar(select(AsyncJob).where(AsyncJob.id == job_id))
        if not job:
            return
        job.status = status
        if status == "running" and not job.started_at:
            job.started_at = datetime.utcnow()
        if status in ("succeeded", "failed"):
            job.completed_at = datetime.utcnow()
        if result_json is not None:
            job.result_json = result_json
        job.error_message = error_message
        db.commit()


@celery_app.task(name="jobs.generate_lms")
def generate_lms_job(job_id: str, tenant_id: str, blueprint_id: str) -> dict:
    job_uuid = UUID(job_id)
    _set_job_status(job_uuid, "running")
    try:
        with SessionLocal() as db:
            blueprint = db.scalar(
                select(CompanyBlueprint).where(
                    CompanyBlueprint.id == UUID(blueprint_id),
                    CompanyBlueprint.tenant_id == UUID(tenant_id),
                )
            )
            if not blueprint:
                raise RuntimeError("Blueprint not found")

            data = blueprint.blueprint_json or {}
            teams = data.get("teams") or ["General"]
            focus = data.get("training_focus") or ["sop_compliance"]
            kpis = data.get("kpis") or ["conversion_rate", "resolution_time"]
            knowledge_items = db.scalars(select(KnowledgeItem).where(KnowledgeItem.tenant_id == UUID(tenant_id))).all()
            grouped_by_tab: dict[str, list[KnowledgeItem]] = {}
            for item in knowledge_items:
                grouped_by_tab.setdefault(item.source_tab, []).append(item)

            course = Course(
                tenant_id=UUID(tenant_id),
                title=f"Adaptive Training: {', '.join(teams[:2])} ({len(knowledge_items)} KB items)",
                description="Generated asynchronously from blueprint and tenant knowledge base.",
            )
            db.add(course)
            db.flush()

            created_lessons = 0
            # Generate one playbook module per available source tab.
            tabs = list(grouped_by_tab.keys()) if grouped_by_tab else teams[:3]
            for idx, tab in enumerate(tabs):
                module = Module(tenant_id=UUID(tenant_id), course_id=course.id, title=f"{tab} Playbook", order_index=idx)
                db.add(module)
                db.flush()
                topic = focus[idx % len(focus)]
                context_examples = grouped_by_tab.get(tab, [])[:3]
                source_lines = []
                for ex in context_examples:
                    source_lines.append(f"- {ex.title}: {ex.description[:200]}")
                source_block = "\n".join(source_lines) if source_lines else "- No examples available."
                try:
                    lesson_text = call_llm(
                        "You are a corporate L&D assistant.",
                        (
                            f"Create a concise lesson for module={tab}, topic={topic}, kpis={','.join(kpis[:3])}.\n"
                            f"Use these source examples:\n{source_block}"
                        ),
                    )
                except Exception:
                    lesson_text = build_lesson_content(tab, topic, kpis)
                db.add(
                    Lesson(
                        tenant_id=UUID(tenant_id),
                        module_id=module.id,
                        title=f"{module.title}: Foundations",
                        content_text=lesson_text,
                        source_refs_json={
                            "blueprint_id": str(blueprint.id),
                            "module": tab,
                            "focus_topic": topic,
                            "knowledge_item_ids": [str(ex.id) for ex in context_examples],
                        },
                    )
                )
                created_lessons += 1

            assessment = Assessment(tenant_id=UUID(tenant_id), title="Knowledge Check (Generated)", assessment_type="quiz")
            db.add(assessment)
            db.flush()
            db.add(
                AssessmentQuestion(
                    tenant_id=UUID(tenant_id),
                    assessment_id=assessment.id,
                    question_text="What is the purpose of adaptive AI tutoring?",
                    options_json={"a": "Static reading only", "b": "Role-aware guidance", "c": "No feedback", "d": "Manual-only training"},
                    correct_answer_index=1,
                )
            )
            db.commit()

            result = {"ok": True, "course_id": str(course.id), "assessment_id": str(assessment.id), "lessons_created": created_lessons}
            _set_job_status(job_uuid, "succeeded", result_json=result)
            return result
    except Exception as exc:
        _set_job_status(job_uuid, "failed", error_message=str(exc))
        raise


@celery_app.task(name="jobs.tutor_feedback")
def tutor_feedback_job(job_id: str, lesson_title: str, lesson_content: str, learner_answer: str, source_refs_json: str = "{}") -> dict:
    job_uuid = UUID(job_id)
    _set_job_status(job_uuid, "running")
    try:
        prompt = (
            "Review the learner answer against lesson context and return strict JSON with keys: "
            "feedback (string), follow_up_question (string), confidence_score (0-100 int).\n"
            f"Lesson title: {lesson_title}\nLesson content:\n{lesson_content[:3000]}\nSource refs:{source_refs_json}\n\nLearner answer:\n{learner_answer[:2000]}"
        )
        try:
            raw = call_llm("You are an adaptive AI tutor.", prompt)
            parsed = __import__("json").loads(raw)
            result = {
                "feedback": str(parsed.get("feedback") or "Good attempt. Keep practicing with more specific examples."),
                "follow_up_question": str(parsed.get("follow_up_question") or "How would you apply this in a real customer scenario?"),
                "confidence_score": max(0, min(100, int(parsed.get("confidence_score", 70)))),
                "source_refs": source_refs_json,
            }
        except Exception:
            result = {
                "feedback": "Good attempt. You captured important points, but include clearer role-specific actions next time.",
                "follow_up_question": "What would be your first two actions in a real scenario using this lesson?",
                "confidence_score": 70,
                "source_refs": source_refs_json,
            }
        _set_job_status(job_uuid, "succeeded", result_json=result)
        return result
    except Exception as exc:
        _set_job_status(job_uuid, "failed", error_message=str(exc))
        raise


@celery_app.task(name="jobs.simulation_evaluate")
def simulation_evaluate_job(job_id: str, attempt_id: str, scenario_prompt: str, user_response_text: str) -> dict:
    job_uuid = UUID(job_id)
    _set_job_status(job_uuid, "running")
    try:
        try:
            raw = call_llm(
                "You evaluate roleplay simulation responses. Return strict JSON with keys: score(0-100 int), feedback(string).",
                f"Scenario:\n{scenario_prompt[:2500]}\n\nUser response:\n{user_response_text[:2000]}",
            )
            parsed = __import__("json").loads(raw)
            score = max(0, min(100, int(parsed.get("score", 70))))
            feedback = str(parsed.get("feedback") or "Solid attempt with room for clearer structure.")
        except Exception:
            # Deterministic fallback scoring.
            length_score = min(40, max(10, len(user_response_text.strip()) // 10))
            keyword_bonus = 20 if any(k in user_response_text.lower() for k in ["kpi", "customer", "sop", "escalation"]) else 5
            score = min(100, length_score + keyword_bonus + 30)
            feedback = "Decent response. Add more role-specific actions and measurable outcomes."

        with SessionLocal() as db:
            attempt = db.scalar(select(SimulationAttempt).where(SimulationAttempt.id == UUID(attempt_id)))
            if attempt:
                attempt.score = score
                attempt.feedback_text = feedback
                attempt.status = "completed"
                attempt.completed_at = datetime.utcnow()
                db.commit()
        result = {"attempt_id": attempt_id, "score": score, "feedback_text": feedback}
        _set_job_status(job_uuid, "succeeded", result_json=result)
        return result
    except Exception as exc:
        _set_job_status(job_uuid, "failed", error_message=str(exc))
        raise

