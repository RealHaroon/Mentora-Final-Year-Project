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
  top_career_match: { title: string; fit_percent: number };
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

// ---- exam ----

export interface TimetableRow {
  day: string;
  topic: string;
  subject: string;
  duration: string;
  status: "pending" | "done" | "today" | "missed";
}

export interface TimetableResponse {
  days_to_exam: number;
  rows: TimetableRow[];
}

export interface TodayTopicResponse {
  topic: string;
  explainer: { summary: string; points: string[] };
  videos: { title: string; source: string; duration_min: number }[];
}

export interface McqQuestion {
  question_id: string;
  text: string;
  options: { value: string; text: string }[];
}

export interface McqResponse {
  total: number;
  remaining: number;
  generated_by: string;
  question: McqQuestion;
}

export interface McqSubmitResponse {
  question_id: string;
  correct: boolean;
  correct_answer: string;
}

// ---- career ----

export interface CvUploadResponse {
  filename: string;
  gpa: number;
  skills: string[];
  certifications: string[];
  projects: string[];
}

export interface AiSuggestResponse {
  career_goal: string;
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
  month_number: number | string;
  milestone_title: string;
  description: string;
  status: "completed" | "in_progress" | "pending";
}

export interface RoadmapResponse {
  career_id: number;
  title: string;
  steps: RoadmapStep[];
}

export interface InterviewStartResponse {
  interview_id: number;
  question: string;
}

export interface InterviewAskResponse {
  interview_id: number;
  ai_feedback: string;
  next_question: string;
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
