export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }

  return (await res.json()) as T;
}

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: {
    id: string;
    email: string;
    full_name: string;
    role: string;
    tenant_id: string;
    is_active: boolean;
  };
};

export async function loginApi(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/api/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export type MeResponse = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  tenant_id: string;
  is_active: boolean;
};

export async function meApi(accessToken: string): Promise<MeResponse> {
  return request<MeResponse>("/api/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export type CourseOut = { id: string; title: string; description: string; created_at: string };
export type ModuleOut = { id: string; course_id: string; title: string; order_index: number; created_at: string };
export type LessonOut = { id: string; module_id: string; title: string; content_text: string; created_at: string };
export type BlueprintOut = {
  id: string;
  version: number;
  blueprint_json: Record<string, unknown>;
  created_at: string;
};
export type AssessmentOut = { id: string; title: string; assessment_type: string; created_at: string };
export type AssessmentQuestionOut = {
  id: string;
  question_text: string;
  options_json: Record<string, string>;
  correct_answer_index: number;
};
export type AssessmentSubmissionOut = {
  id: string;
  assessment_id: string;
  score: number;
  submitted_at: string;
};
export type TutorFeedbackOut = {
  feedback: string;
  follow_up_question: string;
  confidence_score: number;
};
export type JobEnqueueOut = {
  job_id: string;
  status: string;
  message: string;
};
export type JobStatusOut = {
  id: string;
  job_type: string;
  status: string;
  result_json: Record<string, unknown>;
  error_message: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
};
export type KpiIngestOut = {
  ok: boolean;
  updated_skills: Array<{ skill_name: string; score: number }>;
};
export type NextLessonRecommendationOut = {
  lesson_id: string;
  module_id: string;
  title: string;
  reason: string;
};
export type RecommendationOut = { next_lessons: NextLessonRecommendationOut[] };
export type BadgeOut = { badge_code: string; badge_name: string; awarded_at: string };
export type GamificationProfileOut = {
  user_id: string;
  xp_points: number;
  level: number;
  badges_count: number;
  streak_days: number;
  badges: BadgeOut[];
};
export type LeaderboardRowOut = {
  user_id: string;
  full_name: string;
  role: string;
  xp_points: number;
  level: number;
  badges_count: number;
};
export type LeaderboardOut = { leaderboard: LeaderboardRowOut[] };
export type WebhookOut = {
  id: string;
  provider: string;
  target_url: string;
  event_name: string;
  is_active: boolean;
  created_at: string;
};
export type SimulationScenarioOut = {
  id: string;
  title: string;
  team: string;
  focus_topic: string;
  prompt_text: string;
  created_at: string;
};
export type SimulationAttemptOut = {
  id: string;
  scenario_id: string;
  status: string;
  score: number;
  feedback_text: string;
  created_at: string;
  completed_at?: string | null;
};
export type TenantProfileOut = {
  business_domain: string;
  role_template_json: Record<string, unknown>;
  taxonomy_mapping_json: Record<string, unknown>;
  generation_prefs_json: Record<string, unknown>;
  connectors_json: Record<string, unknown>;
  labels_json: Record<string, unknown>;
  updated_at: string;
};
export type SheetTabSource = { name: string; url: string; gid: string };
export type TenantDataSyncOut = { ok: boolean; synced_tabs: number; upserted_items: number };
export type KnowledgeItemOut = {
  id: string;
  source_tab: string;
  source_row: number;
  title: string;
  category: string;
  service_type: string;
  team_hint: string;
  description: string;
  tags_json: Record<string, unknown>;
  attrs_json: Record<string, unknown>;
  source_url: string;
  updated_at: string;
};
export type KnowledgeStatsOut = {
  total_items: number;
  by_tab: Record<string, number>;
  by_team_hint: Record<string, number>;
};
export type TenantAnalyticsOut = {
  users_count: number;
  knowledge_items: number;
  knowledge_by_tab: Record<string, number>;
  lesson_completions: number;
  assessments_submitted: number;
  avg_assessment_score: number;
  simulations_completed: number;
  avg_simulation_score: number;
  weak_skills: Array<{ skill_name: string; score: number; user_id: string }>;
};

export async function coursesApi(accessToken: string): Promise<CourseOut[]> {
  return request<CourseOut[]>("/api/courses", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function listBlueprintsApi(accessToken: string): Promise<BlueprintOut[]> {
  return request<BlueprintOut[]>("/api/onboarding/blueprints", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function createBlueprintApi(
  accessToken: string,
  payload: { website_url?: string; documents_text: string; questionnaire?: Record<string, unknown> }
): Promise<BlueprintOut> {
  return request<BlueprintOut>("/api/onboarding/blueprint", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload)
  });
}

export async function generateLmsApi(accessToken: string, blueprint_id: string): Promise<JobEnqueueOut> {
  return request<JobEnqueueOut>("/api/onboarding/generate-lms", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ blueprint_id })
  });
}

export async function jobStatusApi(accessToken: string, jobId: string): Promise<JobStatusOut> {
  return request<JobStatusOut>(`/api/jobs/${jobId}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function modulesApi(accessToken: string, courseId: string): Promise<ModuleOut[]> {
  return request<ModuleOut[]>(`/api/courses/${courseId}/modules`, {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function lessonsApi(accessToken: string, moduleId: string): Promise<LessonOut[]> {
  return request<LessonOut[]>(`/api/modules/${moduleId}/lessons`, {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function completeLessonApi(accessToken: string, lessonId: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/api/progress/lesson-complete", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ lesson_id: lessonId })
  });
}

export async function assessmentsApi(accessToken: string): Promise<AssessmentOut[]> {
  return request<AssessmentOut[]>("/api/assessments", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function assessmentQuestionsApi(accessToken: string, assessmentId: string): Promise<AssessmentQuestionOut[]> {
  return request<AssessmentQuestionOut[]>(`/api/assessments/${assessmentId}/questions`, {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function submitAssessmentApi(
  accessToken: string,
  payload: { assessment_id: string; answers: Record<string, number> }
): Promise<AssessmentSubmissionOut> {
  return request<AssessmentSubmissionOut>("/api/submissions", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload)
  });
}

export async function tutorFeedbackApi(
  accessToken: string,
  payload: { lesson_id: string; learner_answer: string }
): Promise<JobEnqueueOut> {
  return request<JobEnqueueOut>("/api/tutor/feedback", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload)
  });
}

export async function ingestKpiApi(
  accessToken: string,
  payload: { user_id: string; metrics: Record<string, number> }
): Promise<KpiIngestOut> {
  return request<KpiIngestOut>("/api/kpi/ingest", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload)
  });
}

export async function nextLessonRecommendationsApi(accessToken: string): Promise<RecommendationOut> {
  return request<RecommendationOut>("/api/recommendations/next-lessons", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function gamificationMeApi(accessToken: string): Promise<GamificationProfileOut> {
  return request<GamificationProfileOut>("/api/gamification/me", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function gamificationLeaderboardApi(accessToken: string): Promise<LeaderboardOut> {
  return request<LeaderboardOut>("/api/gamification/leaderboard", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function integrationsWebhooksApi(accessToken: string): Promise<WebhookOut[]> {
  return request<WebhookOut[]>("/api/integrations/webhooks", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function createWebhookApi(
  accessToken: string,
  payload: { provider: string; target_url: string; event_name: string }
): Promise<WebhookOut> {
  return request<WebhookOut>("/api/integrations/webhooks", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload)
  });
}

export async function startSimulationApi(
  accessToken: string,
  payload: { blueprint_id?: string; team: string; focus_topic: string }
): Promise<SimulationScenarioOut> {
  return request<SimulationScenarioOut>("/api/simulations/start", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload)
  });
}

export async function submitSimulationApi(
  accessToken: string,
  payload: { scenario_id: string; user_response_text: string }
): Promise<JobEnqueueOut> {
  return request<JobEnqueueOut>("/api/simulations/submit", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload)
  });
}

export async function simulationAttemptApi(accessToken: string, attemptId: string): Promise<SimulationAttemptOut> {
  return request<SimulationAttemptOut>(`/api/simulations/attempts/${attemptId}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function tenantProfileApi(accessToken: string): Promise<TenantProfileOut> {
  return request<TenantProfileOut>("/api/tenant/profile", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function upsertTenantProfileApi(
  accessToken: string,
  payload: Omit<TenantProfileOut, "updated_at">
): Promise<TenantProfileOut> {
  return request<TenantProfileOut>("/api/tenant/profile", {
    method: "PUT",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload)
  });
}

export async function syncTenantDataApi(
  accessToken: string,
  payload: { tabs?: SheetTabSource[] }
): Promise<TenantDataSyncOut> {
  return request<TenantDataSyncOut>("/api/tenant-data/sync", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload)
  });
}

export async function knowledgeStatsApi(accessToken: string): Promise<KnowledgeStatsOut> {
  return request<KnowledgeStatsOut>("/api/knowledge/stats", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function knowledgeItemsApi(accessToken: string, tab = "", limit = 20): Promise<KnowledgeItemOut[]> {
  const q = new URLSearchParams();
  if (tab) q.set("tab", tab);
  q.set("limit", String(limit));
  return request<KnowledgeItemOut[]>(`/api/knowledge-items?${q.toString()}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function createBlueprintFromKnowledgeApi(accessToken: string): Promise<BlueprintOut> {
  return request<BlueprintOut>("/api/onboarding/blueprint/from-knowledge", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function tenantAnalyticsApi(accessToken: string): Promise<TenantAnalyticsOut> {
  return request<TenantAnalyticsOut>("/api/analytics/tenant", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

