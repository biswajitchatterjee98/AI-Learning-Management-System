"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  assessmentQuestionsApi,
  assessmentsApi,
  completeLessonApi,
  coursesApi,
  createBlueprintApi,
  generateLmsApi,
  jobStatusApi,
  ingestKpiApi,
  gamificationMeApi,
  gamificationLeaderboardApi,
  integrationsWebhooksApi,
  createWebhookApi,
  lessonsApi,
  listBlueprintsApi,
  meApi,
  modulesApi,
  nextLessonRecommendationsApi,
  submitAssessmentApi,
  tutorFeedbackApi,
  startSimulationApi,
  submitSimulationApi,
  simulationAttemptApi,
  type AssessmentOut,
  type AssessmentQuestionOut,
  type BlueprintOut,
  type CourseOut,
  type KpiIngestOut,
  type LessonOut,
  type ModuleOut,
  type NextLessonRecommendationOut,
  type TutorFeedbackOut,
  type JobStatusOut,
  type GamificationProfileOut,
  type LeaderboardRowOut,
  type WebhookOut,
  type SimulationScenarioOut,
  type SimulationAttemptOut,
} from "@/lib/api";

function roleLabel(role: string) {
  if (role === "admin") return "Admin";
  if (role === "manager") return "Manager";
  if (role === "employee") return "Employee";
  return role;
}

export default function DashboardPage() {
  const router = useRouter();
  const params = useParams<{ role: string }>();
  const role = params.role;

  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [me, setMe] = useState<null | { role: string; full_name: string }>(null);
  const [courses, setCourses] = useState<CourseOut[]>([]);
  const [modules, setModules] = useState<ModuleOut[]>([]);
  const [lessons, setLessons] = useState<LessonOut[]>([]);
  const [assessments, setAssessments] = useState<AssessmentOut[]>([]);
  const [assessmentQuestions, setAssessmentQuestions] = useState<AssessmentQuestionOut[]>([]);
  const [assessmentAnswers, setAssessmentAnswers] = useState<Record<string, number>>({});
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<string>("");
  const [selectedCourseId, setSelectedCourseId] = useState<string>("");
  const [selectedModuleId, setSelectedModuleId] = useState<string>("");
  const [recommendations, setRecommendations] = useState<NextLessonRecommendationOut[]>([]);
  const [blueprints, setBlueprints] = useState<BlueprintOut[]>([]);
  const [documentsText, setDocumentsText] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [onboardingMessage, setOnboardingMessage] = useState<string | null>(null);
  const [assessmentMessage, setAssessmentMessage] = useState<string | null>(null);
  const [learningMessage, setLearningMessage] = useState<string | null>(null);
  const [selectedLessonIdForTutor, setSelectedLessonIdForTutor] = useState<string>("");
  const [learnerAnswer, setLearnerAnswer] = useState("");
  const [tutorResult, setTutorResult] = useState<TutorFeedbackOut | null>(null);
  const [tutorMessage, setTutorMessage] = useState<string | null>(null);
  const [activeJobStatus, setActiveJobStatus] = useState<JobStatusOut | null>(null);
  const [isPollingJob, setIsPollingJob] = useState(false);
  const [simulationTeam, setSimulationTeam] = useState("Sales");
  const [simulationFocus, setSimulationFocus] = useState("objection_handling");
  const [simulationScenario, setSimulationScenario] = useState<SimulationScenarioOut | null>(null);
  const [simulationResponse, setSimulationResponse] = useState("");
  const [simulationAttempt, setSimulationAttempt] = useState<SimulationAttemptOut | null>(null);
  const [simulationMessage, setSimulationMessage] = useState<string | null>(null);
  const [kpiUserId, setKpiUserId] = useState("");
  const [kpiMetricsText, setKpiMetricsText] = useState('{"conversion_rate": 72, "resolution_time": 64}');
  const [kpiResult, setKpiResult] = useState<KpiIngestOut | null>(null);
  const [kpiMessage, setKpiMessage] = useState<string | null>(null);
  const [gamificationProfile, setGamificationProfile] = useState<GamificationProfileOut | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardRowOut[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookOut[]>([]);
  const [webhookProvider, setWebhookProvider] = useState("slack");
  const [webhookEventName, setWebhookEventName] = useState("progress.updated");
  const [webhookTargetUrl, setWebhookTargetUrl] = useState("");
  const [integrationMessage, setIntegrationMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const expectedRole = useMemo(() => role ?? "", [role]);
  const canManageOnboarding = me?.role === "admin" || me?.role === "manager";

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const savedRole = localStorage.getItem("user_role");
    if (!token || !savedRole) {
      router.push("/login");
      return;
    }
    setAccessToken(token);

    // If user tries to view a different role dashboard, redirect to their correct role.
    if (savedRole !== expectedRole) {
      router.push(`/dashboard/${savedRole}`);
      return;
    }
  }, [expectedRole, router]);

  async function loadDashboardData(token: string) {
    const meRes = await meApi(token);
    setMe({ role: meRes.role, full_name: meRes.full_name });

    const [courseRes, recRes, assessmentRes, gamificationRes, leaderboardRes] = await Promise.all([
      coursesApi(token),
      nextLessonRecommendationsApi(token),
      assessmentsApi(token),
      gamificationMeApi(token),
      gamificationLeaderboardApi(token),
    ]);

    setCourses(courseRes);
    setRecommendations(recRes.next_lessons);
    setAssessments(assessmentRes);
    setGamificationProfile(gamificationRes);
    setLeaderboard(leaderboardRes.leaderboard);

    if (courseRes.length > 0) {
      const cId = selectedCourseId || courseRes[0].id;
      setSelectedCourseId(cId);
      const modRes = await modulesApi(token, cId);
      setModules(modRes);

      if (modRes.length > 0) {
        const mId = selectedModuleId || modRes[0].id;
        setSelectedModuleId(mId);
        const lessonRes = await lessonsApi(token, mId);
        setLessons(lessonRes);
        if (lessonRes.length > 0 && !selectedLessonIdForTutor) {
          setSelectedLessonIdForTutor(lessonRes[0].id);
        }
      } else {
        setLessons([]);
      }
    } else {
      setModules([]);
      setLessons([]);
    }

    if (assessmentRes.length > 0) {
      const aId = selectedAssessmentId || assessmentRes[0].id;
      setSelectedAssessmentId(aId);
      const questionRes = await assessmentQuestionsApi(token, aId);
      setAssessmentQuestions(questionRes);
    } else {
      setAssessmentQuestions([]);
    }

    if (meRes.role === "admin" || meRes.role === "manager") {
      const [blueprintRes, webhookRes] = await Promise.all([listBlueprintsApi(token), integrationsWebhooksApi(token)]);
      setBlueprints(blueprintRes);
      setWebhooks(webhookRes);
    } else {
      setBlueprints([]);
      setWebhooks([]);
    }
  }

  useEffect(() => {
    async function run() {
      if (!accessToken) return;
      setLoading(true);
      setError(null);
      try {
        await loadDashboardData(accessToken);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    }
    run();
  }, [accessToken]);

  async function pollJobUntilDone(token: string, jobId: string): Promise<JobStatusOut> {
    setIsPollingJob(true);
    try {
      for (let i = 0; i < 120; i += 1) {
        const status = await jobStatusApi(token, jobId);
        setActiveJobStatus(status);
        if (status.status === "succeeded" || status.status === "failed") {
          return status;
        }
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
      throw new Error("Job timed out. Please check again shortly.");
    } finally {
      setIsPollingJob(false);
    }
  }

  async function handleCreateBlueprint(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken) return;
    setOnboardingMessage(null);
    try {
      const created = await createBlueprintApi(accessToken, {
        website_url: websiteUrl || undefined,
        documents_text: documentsText,
        questionnaire: {},
      });
      setOnboardingMessage(`Blueprint created (${created.id.slice(0, 8)}...).`);
      setDocumentsText("");
      await loadDashboardData(accessToken);
    } catch (err) {
      setOnboardingMessage(err instanceof Error ? err.message : "Failed to create blueprint");
    }
  }

  async function handleGenerateLms(blueprintId: string) {
    if (!accessToken) return;
    setOnboardingMessage(null);
    try {
      const enqueued = await generateLmsApi(accessToken, blueprintId);
      setOnboardingMessage(`${enqueued.message} (job: ${enqueued.job_id.slice(0, 8)}...)`);
      const finalStatus = await pollJobUntilDone(accessToken, enqueued.job_id);
      if (finalStatus.status === "succeeded") {
        setOnboardingMessage("LMS generation completed.");
      } else {
        setOnboardingMessage(finalStatus.error_message || "LMS generation failed.");
      }
      await loadDashboardData(accessToken);
    } catch (err) {
      setOnboardingMessage(err instanceof Error ? err.message : "Failed to generate LMS");
    }
  }

  async function handleCourseChange(courseId: string) {
    if (!accessToken) return;
    setSelectedCourseId(courseId);
    const modRes = await modulesApi(accessToken, courseId);
    setModules(modRes);
    if (modRes.length > 0) {
      setSelectedModuleId(modRes[0].id);
      const lessonRes = await lessonsApi(accessToken, modRes[0].id);
      setLessons(lessonRes);
    } else {
      setSelectedModuleId("");
      setLessons([]);
    }
  }

  async function handleModuleChange(moduleId: string) {
    if (!accessToken) return;
    setSelectedModuleId(moduleId);
    const lessonRes = await lessonsApi(accessToken, moduleId);
    setLessons(lessonRes);
    setSelectedLessonIdForTutor(lessonRes[0]?.id || "");
  }

  async function handleCompleteLesson(lessonId: string) {
    if (!accessToken) return;
    setLearningMessage(null);
    try {
      await completeLessonApi(accessToken, lessonId);
      setLearningMessage("Lesson marked as complete.");
      await loadDashboardData(accessToken);
    } catch (err) {
      setLearningMessage(err instanceof Error ? err.message : "Failed to update lesson progress");
    }
  }

  async function handleAssessmentChange(assessmentId: string) {
    if (!accessToken) return;
    setSelectedAssessmentId(assessmentId);
    const qs = await assessmentQuestionsApi(accessToken, assessmentId);
    setAssessmentQuestions(qs);
    setAssessmentAnswers({});
  }

  async function handleSubmitAssessment(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken || !selectedAssessmentId) return;
    setAssessmentMessage(null);
    try {
      const res = await submitAssessmentApi(accessToken, {
        assessment_id: selectedAssessmentId,
        answers: assessmentAnswers,
      });
      setAssessmentMessage(`Assessment submitted. Score: ${res.score}`);
      await loadDashboardData(accessToken);
    } catch (err) {
      setAssessmentMessage(err instanceof Error ? err.message : "Failed to submit assessment");
    }
  }

  async function handleTutorFeedback(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken || !selectedLessonIdForTutor || !learnerAnswer.trim()) return;
    setTutorMessage(null);
    setTutorResult(null);
    try {
      const enqueued = await tutorFeedbackApi(accessToken, {
        lesson_id: selectedLessonIdForTutor,
        learner_answer: learnerAnswer,
      });
      setTutorMessage(`Tutor job queued (${enqueued.job_id.slice(0, 8)}...).`);
      const finalStatus = await pollJobUntilDone(accessToken, enqueued.job_id);
      if (finalStatus.status === "succeeded") {
        const result = finalStatus.result_json;
        setTutorResult({
          feedback: String(result.feedback || ""),
          follow_up_question: String(result.follow_up_question || ""),
          confidence_score: Number(result.confidence_score || 0),
        });
        setTutorMessage("Tutor feedback ready.");
      } else {
        setTutorMessage(finalStatus.error_message || "Tutor feedback failed.");
      }
    } catch (err) {
      setTutorMessage(err instanceof Error ? err.message : "Failed to get tutor feedback");
    }
  }

  async function handleStartSimulation(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken) return;
    setSimulationMessage(null);
    setSimulationAttempt(null);
    try {
      const scenario = await startSimulationApi(accessToken, {
        team: simulationTeam,
        focus_topic: simulationFocus,
      });
      setSimulationScenario(scenario);
      setSimulationMessage("Simulation started. Submit your response for evaluation.");
    } catch (err) {
      setSimulationMessage(err instanceof Error ? err.message : "Failed to start simulation");
    }
  }

  async function handleSubmitSimulation(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken || !simulationScenario || !simulationResponse.trim()) return;
    setSimulationMessage(null);
    try {
      const enqueued = await submitSimulationApi(accessToken, {
        scenario_id: simulationScenario.id,
        user_response_text: simulationResponse,
      });
      const finalStatus = await pollJobUntilDone(accessToken, enqueued.job_id);
      if (finalStatus.status !== "succeeded") {
        setSimulationMessage(finalStatus.error_message || "Simulation evaluation failed.");
        return;
      }
      const attemptId = String(finalStatus.result_json.attempt_id || "");
      if (!attemptId) {
        setSimulationMessage("Simulation completed but attempt result was missing.");
        return;
      }
      const attempt = await simulationAttemptApi(accessToken, attemptId);
      setSimulationAttempt(attempt);
      setSimulationMessage("Simulation evaluation completed.");
    } catch (err) {
      setSimulationMessage(err instanceof Error ? err.message : "Failed to evaluate simulation");
    }
  }

  async function handleIngestKpi(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken || !kpiUserId.trim()) return;
    setKpiMessage(null);
    setKpiResult(null);
    try {
      const parsed = JSON.parse(kpiMetricsText) as Record<string, number>;
      const normalized: Record<string, number> = {};
      for (const [key, value] of Object.entries(parsed)) {
        normalized[key] = Number(value);
      }
      const res = await ingestKpiApi(accessToken, {
        user_id: kpiUserId.trim(),
        metrics: normalized,
      });
      setKpiResult(res);
      setKpiMessage("KPI metrics ingested successfully.");
      await loadDashboardData(accessToken);
    } catch (err) {
      setKpiMessage(err instanceof Error ? err.message : "Failed to ingest KPI metrics");
    }
  }

  async function handleCopyMyUserId() {
    if (!accessToken) return;
    try {
      const currentUser = await meApi(accessToken);
      await navigator.clipboard.writeText(currentUser.id);
      setKpiMessage("Your user ID was copied to clipboard.");
    } catch (err) {
      setKpiMessage(err instanceof Error ? err.message : "Failed to copy user ID");
    }
  }

  async function handleUseMyUserIdForKpi() {
    if (!accessToken) return;
    try {
      const currentUser = await meApi(accessToken);
      setKpiUserId(currentUser.id);
      setKpiMessage("KPI target user set to your user ID.");
    } catch (err) {
      setKpiMessage(err instanceof Error ? err.message : "Failed to fetch your user ID");
    }
  }

  async function handleCreateWebhook(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken) return;
    setIntegrationMessage(null);
    try {
      await createWebhookApi(accessToken, {
        provider: webhookProvider.trim().toLowerCase(),
        event_name: webhookEventName.trim().toLowerCase(),
        target_url: webhookTargetUrl.trim(),
      });
      setWebhookTargetUrl("");
      setIntegrationMessage("Webhook registered.");
      const updated = await integrationsWebhooksApi(accessToken);
      setWebhooks(updated);
    } catch (err) {
      setIntegrationMessage(err instanceof Error ? err.message : "Failed to register webhook");
    }
  }

  return (
    <main style={{ padding: 24, maxWidth: 920, margin: "0 auto" }}>
      <h1>
        {roleLabel(expectedRole)} Dashboard
      </h1>

      {loading ? <div>Loading...</div> : null}
      {error ? <div style={{ color: "crimson" }}>{error}</div> : null}

      {me ? (
        <div style={{ marginTop: 12, opacity: 0.9 }}>
          Logged in as: <strong>{me.full_name}</strong> ({me.role})
          {canManageOnboarding ? (
            <span style={{ marginLeft: 10 }}>
              <button onClick={() => void handleCopyMyUserId()} style={{ marginRight: 6 }}>
                Copy My User ID
              </button>
              <button onClick={() => void handleUseMyUserIdForKpi()}>Use My ID for KPI</button>
            </span>
          ) : null}
        </div>
      ) : null}

      {canManageOnboarding ? (
        <section style={{ marginTop: 20, borderTop: "1px solid #ddd", paddingTop: 16 }}>
          <h2>Onboarding</h2>
          <form onSubmit={handleCreateBlueprint} style={{ display: "grid", gap: 8, maxWidth: 700 }}>
            <input
              placeholder="Website URL (optional)"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              style={{ padding: 8 }}
            />
            <textarea
              placeholder="Paste SOP/document text for blueprint generation"
              value={documentsText}
              onChange={(e) => setDocumentsText(e.target.value)}
              rows={5}
              style={{ padding: 8 }}
              required
            />
            <button type="submit" style={{ padding: 10, width: 220 }}>
              Create Blueprint
            </button>
          </form>
          <div style={{ marginTop: 10 }}>
            <strong>Available Blueprints</strong>
            {blueprints.length === 0 ? (
              <div>No blueprints yet.</div>
            ) : (
              <ul>
                {blueprints.map((b) => (
                  <li key={b.id}>
                    <span>{new Date(b.created_at).toLocaleString()} - version {b.version}</span>{" "}
                    <button onClick={() => handleGenerateLms(b.id)} style={{ marginLeft: 8 }}>
                      Generate LMS
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {onboardingMessage ? <div style={{ marginTop: 8 }}>{onboardingMessage}</div> : null}
        </section>
      ) : null}

      <section style={{ marginTop: 20 }}>
        <h2>Courses</h2>
        {courses.length > 0 ? (
          <select value={selectedCourseId} onChange={(e) => void handleCourseChange(e.target.value)} style={{ padding: 8 }}>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
        ) : null}
        {courses.length === 0 ? (
          <div>No courses found for this tenant yet.</div>
        ) : (
          <ul>
            {courses.map((c) => (
              <li key={c.id}>
                <strong>{c.title}</strong>
                <div style={{ fontSize: 13, opacity: 0.8 }}>{c.description}</div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Learning Flow</h2>
        {modules.length > 0 ? (
          <select value={selectedModuleId} onChange={(e) => void handleModuleChange(e.target.value)} style={{ padding: 8 }}>
            {modules.map((m) => (
              <option key={m.id} value={m.id}>
                {m.title}
              </option>
            ))}
          </select>
        ) : (
          <div>No modules available for selected course.</div>
        )}
        {lessons.length > 0 ? (
          <ul style={{ marginTop: 10 }}>
            {lessons.map((lesson) => (
              <li key={lesson.id} style={{ marginBottom: 10 }}>
                <strong>{lesson.title}</strong>
                <div style={{ fontSize: 13, opacity: 0.85, whiteSpace: "pre-wrap" }}>{lesson.content_text}</div>
                <button onClick={() => void handleCompleteLesson(lesson.id)} style={{ marginTop: 6 }}>
                  Mark Complete
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        {learningMessage ? <div>{learningMessage}</div> : null}
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>AI Tutor Feedback</h2>
        {lessons.length > 0 ? (
          <form onSubmit={handleTutorFeedback} style={{ display: "grid", gap: 8, maxWidth: 760 }}>
            <select
              value={selectedLessonIdForTutor}
              onChange={(e) => setSelectedLessonIdForTutor(e.target.value)}
              style={{ padding: 8 }}
            >
              {lessons.map((lesson) => (
                <option key={lesson.id} value={lesson.id}>
                  {lesson.title}
                </option>
              ))}
            </select>
            <textarea
              placeholder="Write your answer for the selected lesson..."
              value={learnerAnswer}
              onChange={(e) => setLearnerAnswer(e.target.value)}
              rows={5}
              style={{ padding: 8 }}
              required
            />
            <button type="submit" style={{ padding: 10, width: 220 }}>
              Get Tutor Feedback
            </button>
          </form>
        ) : (
          <div>Choose a module with lessons to use tutor feedback.</div>
        )}
        {tutorMessage ? <div style={{ marginTop: 8 }}>{tutorMessage}</div> : null}
        {tutorResult ? (
          <div style={{ marginTop: 10, border: "1px solid #ddd", padding: 10 }}>
            <div><strong>Feedback:</strong> {tutorResult.feedback}</div>
            <div style={{ marginTop: 6 }}><strong>Follow-up:</strong> {tutorResult.follow_up_question}</div>
            <div style={{ marginTop: 6 }}><strong>Confidence:</strong> {tutorResult.confidence_score}</div>
          </div>
        ) : null}
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Simulation (Phase 2)</h2>
        <form onSubmit={handleStartSimulation} style={{ display: "grid", gap: 8, maxWidth: 760 }}>
          <input value={simulationTeam} onChange={(e) => setSimulationTeam(e.target.value)} placeholder="Team (e.g. Sales)" style={{ padding: 8 }} />
          <input
            value={simulationFocus}
            onChange={(e) => setSimulationFocus(e.target.value)}
            placeholder="Focus topic (e.g. objection_handling)"
            style={{ padding: 8 }}
          />
          <button type="submit" style={{ padding: 10, width: 220 }}>
            Start Simulation
          </button>
        </form>
        {simulationScenario ? (
          <div style={{ marginTop: 10, border: "1px solid #ddd", padding: 10 }}>
            <div><strong>{simulationScenario.title}</strong></div>
            <div style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{simulationScenario.prompt_text}</div>
            <form onSubmit={handleSubmitSimulation} style={{ display: "grid", gap: 8, marginTop: 10 }}>
              <textarea
                value={simulationResponse}
                onChange={(e) => setSimulationResponse(e.target.value)}
                placeholder="Write your simulation response"
                rows={5}
                style={{ padding: 8 }}
                required
              />
              <button type="submit" style={{ padding: 10, width: 260 }}>
                Submit For AI Evaluation
              </button>
            </form>
          </div>
        ) : null}
        {simulationMessage ? <div style={{ marginTop: 8 }}>{simulationMessage}</div> : null}
        {simulationAttempt ? (
          <div style={{ marginTop: 8 }}>
            <div><strong>Score:</strong> {simulationAttempt.score}</div>
            <div><strong>Feedback:</strong> {simulationAttempt.feedback_text}</div>
          </div>
        ) : null}
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Async Jobs</h2>
        {isPollingJob ? <div>Polling job status...</div> : null}
        {activeJobStatus ? (
          <div style={{ border: "1px solid #ddd", padding: 10 }}>
            <div>Job: {activeJobStatus.job_type}</div>
            <div>Status: <strong>{activeJobStatus.status}</strong></div>
            {activeJobStatus.error_message ? <div style={{ color: "crimson" }}>{activeJobStatus.error_message}</div> : null}
          </div>
        ) : (
          <div>No active background jobs yet.</div>
        )}
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Gamification</h2>
        {gamificationProfile ? (
          <div style={{ border: "1px solid #ddd", padding: 10 }}>
            <div>XP: <strong>{gamificationProfile.xp_points}</strong></div>
            <div>Level: <strong>{gamificationProfile.level}</strong></div>
            <div>Badges: <strong>{gamificationProfile.badges_count}</strong></div>
            <div>Streak: <strong>{gamificationProfile.streak_days}</strong></div>
            {gamificationProfile.badges.length > 0 ? (
              <ul style={{ marginTop: 8 }}>
                {gamificationProfile.badges.slice(0, 5).map((badge) => (
                  <li key={`${badge.badge_code}-${badge.awarded_at}`}>
                    {badge.badge_name} ({badge.badge_code})
                  </li>
                ))}
              </ul>
            ) : (
              <div style={{ marginTop: 8, opacity: 0.8 }}>No badges yet.</div>
            )}
          </div>
        ) : (
          <div>Loading gamification profile...</div>
        )}
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Leaderboard (Tenant)</h2>
        {leaderboard.length === 0 ? (
          <div>No leaderboard entries yet.</div>
        ) : (
          <ul>
            {leaderboard.map((row, idx) => (
              <li key={row.user_id}>
                #{idx + 1} {row.full_name} ({row.role}) - XP {row.xp_points}, L{row.level}, badges {row.badges_count}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Assessment</h2>
        {assessments.length > 0 ? (
          <select
            value={selectedAssessmentId}
            onChange={(e) => void handleAssessmentChange(e.target.value)}
            style={{ padding: 8 }}
          >
            {assessments.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title}
              </option>
            ))}
          </select>
        ) : (
          <div>No assessments found yet.</div>
        )}
        {assessmentQuestions.length > 0 ? (
          <form onSubmit={handleSubmitAssessment} style={{ marginTop: 12, display: "grid", gap: 12 }}>
            {assessmentQuestions.map((q) => (
              <div key={q.id} style={{ border: "1px solid #ddd", padding: 10 }}>
                <div style={{ marginBottom: 6 }}>
                  <strong>{q.question_text}</strong>
                </div>
                {Object.entries(q.options_json).map(([key, label], index) => (
                  <label key={key} style={{ display: "block", marginBottom: 4 }}>
                    <input
                      type="radio"
                      name={`question-${q.id}`}
                      checked={assessmentAnswers[q.id] === index}
                      onChange={() => setAssessmentAnswers((prev) => ({ ...prev, [q.id]: index }))}
                    />{" "}
                    {label}
                  </label>
                ))}
              </div>
            ))}
            <button type="submit" style={{ padding: 10, width: 220 }}>
              Submit Assessment
            </button>
          </form>
        ) : null}
        {assessmentMessage ? <div style={{ marginTop: 8 }}>{assessmentMessage}</div> : null}
      </section>

      <section style={{ marginTop: 20 }}>
        <h2>Recommended Next Lessons</h2>
        {recommendations.length === 0 ? (
          <div>You are all caught up. No pending lessons right now.</div>
        ) : (
          <ul>
            {recommendations.map((item) => (
              <li key={item.lesson_id}>
                <strong>{item.title}</strong>
                <div style={{ fontSize: 13, opacity: 0.8 }}>{item.reason}</div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {canManageOnboarding ? (
        <section style={{ marginTop: 20 }}>
          <h2>KPI Ingestion (Manager/Admin)</h2>
          <form onSubmit={handleIngestKpi} style={{ display: "grid", gap: 8, maxWidth: 760 }}>
            <input
              placeholder="Target user UUID"
              value={kpiUserId}
              onChange={(e) => setKpiUserId(e.target.value)}
              style={{ padding: 8 }}
              required
            />
            <textarea
              value={kpiMetricsText}
              onChange={(e) => setKpiMetricsText(e.target.value)}
              rows={4}
              style={{ padding: 8, fontFamily: "monospace" }}
              required
            />
            <button type="submit" style={{ padding: 10, width: 220 }}>
              Ingest KPI Metrics
            </button>
          </form>
          {kpiMessage ? <div style={{ marginTop: 8 }}>{kpiMessage}</div> : null}
          {kpiResult?.updated_skills?.length ? (
            <ul style={{ marginTop: 8 }}>
              {kpiResult.updated_skills.map((item) => (
                <li key={item.skill_name}>
                  {item.skill_name}: {item.score}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      {canManageOnboarding ? (
        <section style={{ marginTop: 20 }}>
          <h2>Integrations (Webhook Registry)</h2>
          <form onSubmit={handleCreateWebhook} style={{ display: "grid", gap: 8, maxWidth: 760 }}>
            <input
              placeholder="Provider (e.g. slack, teams, zapier)"
              value={webhookProvider}
              onChange={(e) => setWebhookProvider(e.target.value)}
              style={{ padding: 8 }}
              required
            />
            <input
              placeholder="Event name (e.g. progress.updated)"
              value={webhookEventName}
              onChange={(e) => setWebhookEventName(e.target.value)}
              style={{ padding: 8 }}
              required
            />
            <input
              placeholder="Target URL"
              type="url"
              value={webhookTargetUrl}
              onChange={(e) => setWebhookTargetUrl(e.target.value)}
              style={{ padding: 8 }}
              required
            />
            <button type="submit" style={{ padding: 10, width: 220 }}>
              Register Webhook
            </button>
          </form>
          {integrationMessage ? <div style={{ marginTop: 8 }}>{integrationMessage}</div> : null}
          {webhooks.length > 0 ? (
            <ul style={{ marginTop: 8 }}>
              {webhooks.map((hook) => (
                <li key={hook.id}>
                  {hook.provider} :: {hook.event_name} {"->"} {hook.target_url}
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ marginTop: 8 }}>No webhooks registered yet.</div>
          )}
        </section>
      ) : null}
    </main>
  );
}

