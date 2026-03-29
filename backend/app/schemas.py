from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    tenant_id: UUID
    is_active: bool = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class BlueprintCreateRequest(BaseModel):
    website_url: Optional[str] = None
    documents_text: str = Field(..., description="Extracted text from uploaded SOPs/docs")
    questionnaire: Dict[str, Any] = Field(default_factory=dict)


class BlueprintOut(BaseModel):
    id: UUID
    version: int
    blueprint_json: Dict[str, Any]
    created_at: datetime


class GenerateLmsRequest(BaseModel):
    blueprint_id: UUID


class CourseCreateRequest(BaseModel):
    title: str
    description: str = ""


class CourseOut(BaseModel):
    id: UUID
    title: str
    description: str
    created_at: datetime


class ModuleCreateRequest(BaseModel):
    title: str
    order_index: int = 0


class ModuleOut(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    order_index: int
    created_at: datetime


class LessonCreateRequest(BaseModel):
    title: str
    content_text: str = ""


class LessonOut(BaseModel):
    id: UUID
    module_id: UUID
    title: str
    content_text: str
    created_at: datetime


class AssessmentCreateRequest(BaseModel):
    title: str
    assessment_type: str = "quiz"


class AssessmentOut(BaseModel):
    id: UUID
    title: str
    assessment_type: str
    created_at: datetime


class AssessmentQuestionOut(BaseModel):
    id: UUID
    question_text: str
    options_json: Dict[str, Any]
    correct_answer_index: int


class AssessmentSubmissionRequest(BaseModel):
    assessment_id: UUID
    # answers: {question_id: selected_option_index}
    answers: Dict[str, int]


class AssessmentSubmissionOut(BaseModel):
    id: UUID
    assessment_id: UUID
    score: int
    submitted_at: datetime


class LessonCompleteRequest(BaseModel):
    lesson_id: UUID


class ProgressOut(BaseModel):
    completed_lesson_ids: List[UUID]
    last_scores: List[Dict[str, Any]]


class LessonRecommendationOut(BaseModel):
    lesson_id: UUID
    module_id: UUID
    title: str
    reason: str


class RecommendationOut(BaseModel):
    next_lessons: List[LessonRecommendationOut]


class TutorFeedbackRequest(BaseModel):
    lesson_id: UUID
    learner_answer: str


class TutorFeedbackOut(BaseModel):
    feedback: str
    follow_up_question: str
    confidence_score: int


class KpiIngestRequest(BaseModel):
    user_id: UUID
    metrics: Dict[str, float] = Field(default_factory=dict)


class KpiIngestOut(BaseModel):
    ok: bool
    updated_skills: List[Dict[str, Any]]


class BadgeOut(BaseModel):
    badge_code: str
    badge_name: str
    awarded_at: datetime


class GamificationProfileOut(BaseModel):
    user_id: UUID
    xp_points: int
    level: int
    badges_count: int
    streak_days: int
    badges: List[BadgeOut] = Field(default_factory=list)


class LeaderboardRowOut(BaseModel):
    user_id: UUID
    full_name: str
    role: str
    xp_points: int
    level: int
    badges_count: int


class LeaderboardOut(BaseModel):
    leaderboard: List[LeaderboardRowOut]


class WebhookCreateRequest(BaseModel):
    provider: str
    target_url: str
    event_name: str = "progress.updated"


class WebhookOut(BaseModel):
    id: UUID
    provider: str
    target_url: str
    event_name: str
    is_active: bool
    created_at: datetime


class JobEnqueueOut(BaseModel):
    job_id: UUID
    status: str
    message: str


class JobStatusOut(BaseModel):
    id: UUID
    job_type: str
    status: str
    result_json: Dict[str, Any] = Field(default_factory=dict)
    error_message: str = ""
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class SimulationStartRequest(BaseModel):
    blueprint_id: Optional[UUID] = None
    team: str
    focus_topic: str


class SimulationScenarioOut(BaseModel):
    id: UUID
    title: str
    team: str
    focus_topic: str
    prompt_text: str
    created_at: datetime


class SimulationSubmitRequest(BaseModel):
    scenario_id: UUID
    user_response_text: str


class SimulationAttemptOut(BaseModel):
    id: UUID
    scenario_id: UUID
    status: str
    score: int
    feedback_text: str
    created_at: datetime
    completed_at: Optional[datetime] = None

