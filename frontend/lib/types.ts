// Mirrors the backend's Pydantic/JSON response shapes exactly. Keep this the
// single source of truth for API shapes — see backend/routers/*.py and
// backend/schemas/*.py for what actually produces each of these.

export interface UserOut {
  user_id: number;
  first_name: string;
  last_name: string;
  email: string;
  university: string;
  exam_goal: string;
  created_at: string;
}

// ---- dashboard ----

export interface DashboardStats {
  exam_sessions: number;
  avg_score: number;
  avg_score_delta: number;
  videos_watched: number;
  videos_watched_this_week: number;
  // null until the user has uploaded a CV and viewed /career at least once
  // (that's when CareerRanking rows first get computed and stored).
  top_career_match: { title: string; fit_percent: number } | null;
}

export interface ScoreTrendPoint {
  session: string;
  score: number;
}

export interface WeeklySnapshotDay {
  day: string;
  topic: string;
  status: "done" | "today" | "missed" | "pending";
}

export interface WeakTopic {
  subject: string;
  topic: string;
  score: number;
  note: string | null;
}

export interface NotificationItem {
  type: "alert" | "ok" | "time" | "match";
  message: string;
  is_read: boolean;
}

// M3 (trajectory predictor) — not wired into any page yet (added in Phase 6,
// after this frontend's initial wiring pass). `available: false` when the
// student has fewer than 5 scored sessions.
export type AtRiskCheckResponse =
  | { available: false; detail: string }
  | { available: true; predicted_next_score: number; trend: "declining" | "improving" | "stable" };

// ---- exam ----

export interface TimetableSession {
  subject: string;
  topic: string;
  duration: string;
  status: "pending" | "done" | "today" | "missed";
}

export interface TimetableRow {
  day: string;
  // Every selected subject gets a real session every day (see backend/
  // routers/exam.py's _build_week) — a day is no longer just one subject.
  sessions: TimetableSession[];
  total_duration: string;
}

export interface TimetableResponse {
  days_to_exam: number;
  rows: TimetableRow[];
}

export interface ExamPreferences {
  subjects: string[];
  // The real subjects available for this account's exam_goal — e.g. MDCAT
  // excludes Mathematics (MDCAT doesn't test it). See backend/routers/
  // exam.py's _GOAL_SUBJECTS.
  allowed_subjects: string[];
  test_date: string | null;
  study_mode: string | null;
}

export interface TodayTopicResponse {
  topic: string;
  explainer: { summary: string; points: string[] };
  videos: { title: string; source: string; duration_min: number; video_url: string }[];
}

// Settings -> Manage Topic Videos. video_url/title are null when no one
// has curated a video for that topic yet (Exam Prep then falls back to a
// generic YouTube search — see backend/routers/exam.py's _resolve_video).
export interface TopicVideoEntry {
  topic: string;
  video_url: string | null;
  title: string | null;
}

// Shared shape for /exam/topic-explainer and /career/ask (RAG + Groq, Phase
// 7) — not wired into any page yet, added after this frontend's initial
// wiring pass. A 503 means Groq is temporarily unavailable, not a crash —
// see RAGUnavailableError in backend/rag_core/pipeline.py.
export interface RagAnswerResponse {
  answer: string;
}

export interface McqQuestion {
  question_id: string;
  text: string;
  options: { value: string; text: string }[];
}

export interface McqResponse {
  total: number;
  remaining: number;
  // "groq_generated" (default live path, 2026-11-15 — M2 almost never
  // produces valid JSON and was blocking the page for 18-45s every time),
  // "question_generator_m2" (the real trained model, reachable via
  // GET /exam/mcq?source=m2, not used by default), or
  // "question_bank_fallback" (either generator failed/unavailable).
  // Every one of these is now a real, persisted, gradable question — see
  // McqSubmitResponse below.
  generated_by: string;
  question: McqQuestion;
}

export interface McqSubmitResponse {
  question_id: string;
  // null only when grading is truly unavailable right now: a real-dataset
  // question Groq couldn't determine an answer for on this attempt (rare —
  // see graded_by below for the normal case of a dataset-unlabeled one).
  correct: boolean | null;
  correct_answer: string | null;
  // "dataset" = the original labeled source (e.g. the Kaggle math set).
  // "ai_inferred" = the ~82% of the seeded historic past-paper questions
  // with no real answer key (see mentora_data/SOURCES.md) — Groq
  // determined this one instead of leaving it permanently ungraded.
  graded_by?: "dataset" | "ai_inferred" | null;
  weak_topics_flagged?: string[];
  detail?: string;
}

// ---- career ----

export interface CvUploadResponse {
  filename: string;
  gpa: number | null; // M5 often can't extract a GPA from real CVs — null, not a crash
  skills: string[];
  certifications: string[];
  // M5's real tag set has no PROJECT label (CERT/DEGREE/GPA/SKILL only) —
  // this is actually extracted degrees (e.g. "BSc"), not projects.
  degrees: string[];
}

export interface AiSuggestResponse {
  career_id: number;
  title: string;
  match_score: number;
}

export interface CareerRanking {
  career_id: number;
  title: string;
  match_score: number;
  key_skill_gap: string;
}

export interface RankingsResponse {
  model: string;
  rankings: CareerRanking[];
}

export interface RoadmapStep {
  roadmap_id: number;
  month_number: number | string;
  milestone_title: string;
  description: string;
  status: "completed" | "in_progress" | "pending";
  explanation: string | null;
  video: { title: string; source: string; duration_min: number } | null;
}

export interface RoadmapResponse {
  career_id: number;
  title: string;
  steps: RoadmapStep[];
}

export interface InterviewStartResponse {
  interview_id: number;
  career_title: string;
  question: string;
}

export interface InterviewAskResponse {
  interview_id: number;
  // One combined block of text (feedback on the last answer + the next
  // question), not split fields — a deliberate Phase 7 design choice: the
  // RAG prompt asks for both together, not structured output.
  answer: string;
}

// ---- learning portal ----

export interface LearningStats {
  videos_in_playlist: number;
  videos_watched_this_week: number;
  mcq_assignments: number;
  mcq_pending_today: number;
  course_pdfs: number;
  pdfs_downloaded: number;
  avg_mcq_score: number;
  avg_mcq_score_delta: number;
}

export interface PlaylistVideo {
  title: string;
  subject: string;
  source: string;
  duration_min: number;
  note: string;
  video_url: string;
}

export interface WatchHistoryItem {
  title: string;
  subject: string;
  watched_at: string;
}

export interface NotificationPrefs {
  weak_topic_alerts: boolean;
  content_updates: boolean;
  session_reminders: boolean;
  career_match_updates: boolean;
}

export interface Assignment {
  title: string;
  subject: string;
  question_count: number;
  difficulty: string;
  status: "new" | "completed";
  score: number | null;
}

export interface Material {
  id: number;
  title: string;
  size: string;
  source: string;
}
