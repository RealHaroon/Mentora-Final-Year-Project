"use client";

import { useEffect, useState } from "react";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import { apiFetch, ApiError } from "@/lib/api";
import type {
  AiSuggestResponse,
  CvUploadResponse,
  InterviewAskResponse,
  InterviewStartResponse,
  RagAnswerResponse,
  RankingsResponse,
  RoadmapResponse,
} from "@/lib/types";

const PROGRESS_CLASS = (score: number) => (score >= 75 ? "" : score >= 50 ? " warn" : " low");

// Matches backend/routers/interview.py's _CAREER_GOAL_IDS exactly — both
// sides are fixed, small, and tied to the same CareerGoal enum, so a
// lookup here is simpler than round-tripping through another endpoint.
const CAREER_ID_TO_GOAL: Record<number, string> = {
  1: "data_scientist",
  2: "ml_engineer",
  3: "business_analyst",
  4: "software_engineer",
  5: "product_manager",
  6: "ux_ui_designer",
  7: "devops_engineer",
  8: "cybersecurity_analyst",
  9: "digital_marketing_specialist",
  10: "financial_analyst",
};
const GOAL_TO_CAREER_ID: Record<string, number> = Object.fromEntries(
  Object.entries(CAREER_ID_TO_GOAL).map(([id, goal]) => [goal, Number(id)]),
);

export default function CareerPage() {
  const [extracted, setExtracted] = useState<CvUploadResponse | null>(null);
  const [editingInfo, setEditingInfo] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [careerGoal, setCareerGoal] = useState("data_scientist");

  const [rankings, setRankings] = useState<RankingsResponse | null>(null);
  const [roadmap, setRoadmap] = useState<RoadmapResponse | null>(null);
  const [addedRoadmapVideos, setAddedRoadmapVideos] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [interview, setInterview] = useState<InterviewStartResponse | null>(null);
  const [interviewHistory, setInterviewHistory] = useState<{ role: "student" | "ai"; text: string }[]>([]);
  const [interviewAnswer, setInterviewAnswer] = useState("");
  const [interviewLoading, setInterviewLoading] = useState(false);

  const [careerQuestion, setCareerQuestion] = useState("");
  const [careerAnswer, setCareerAnswer] = useState<string | null>(null);
  const [careerAsking, setCareerAsking] = useState(false);
  const [careerAskError, setCareerAskError] = useState<string | null>(null);

  async function refreshRankings() {
    try {
      const data = await apiFetch<RankingsResponse>("/career/rankings");
      setRankings(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load career rankings");
    }
  }

  useEffect(() => {
    refreshRankings();
    apiFetch<RoadmapResponse>("/career/roadmap?career_id=1")
      .then(setRoadmap)
      .catch(() => {});
  }, []);

  async function handleCvUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    if (!(formData.get("cv_file") as File)?.name) return;

    setUploading(true);
    setError(null);
    try {
      const result = await apiFetch<CvUploadResponse>("/career/cv-upload", {
        method: "POST",
        body: formData,
        headers: {}, // don't set Content-Type — the browser sets the multipart boundary itself
      });
      setExtracted(result);
      setEditingInfo(false);
      // Rankings need extracted skills, which only exist after this upload
      // succeeds — the initial page-load fetch 422s for every new user.
      await refreshRankings();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "CV upload failed");
    } finally {
      setUploading(false);
    }
  }

  function handleEditInfoSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!extracted) return;
    const formData = new FormData(e.currentTarget);
    const splitList = (value: FormDataEntryValue | null) =>
      String(value ?? "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

    setExtracted({
      ...extracted,
      gpa: Number(formData.get("gpa")) || extracted.gpa,
      skills: splitList(formData.get("skills")),
      certifications: splitList(formData.get("certifications")),
      degrees: splitList(formData.get("degrees")),
    });
    setEditingInfo(false);
  }

  async function handleGoalChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const value = e.target.value;
    setCareerGoal(value);
    try {
      await apiFetch("/career/goal", {
        method: "POST",
        body: JSON.stringify({ career_goal: value }),
      });
      await refreshRankings();
      // Same sync as handleViewRoadmap, in the other direction — otherwise
      // the Mock Interview panel's label (driven by roadmap.title) goes
      // stale against this dropdown's new value.
      const careerId = GOAL_TO_CAREER_ID[value];
      if (careerId) {
        const data = await apiFetch<RoadmapResponse>(`/career/roadmap?career_id=${careerId}`);
        setRoadmap(data);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save career goal");
    }
  }

  async function handleAiSuggest() {
    try {
      const suggestion = await apiFetch<AiSuggestResponse>("/career/ai-suggest");
      const goal = CAREER_ID_TO_GOAL[suggestion.career_id];
      if (goal) setCareerGoal(goal);
      await refreshRankings();
      const data = await apiFetch<RoadmapResponse>(`/career/roadmap?career_id=${suggestion.career_id}`);
      setRoadmap(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't get an AI suggestion");
    }
  }

  async function handleViewRoadmap(careerId: number) {
    try {
      const data = await apiFetch<RoadmapResponse>(`/career/roadmap?career_id=${careerId}`);
      setRoadmap(data);
      // Keep the Mock Interview panel's target in sync with whichever
      // roadmap is on screen — it was previously left on whatever the Step 3
      // dropdown last held, so the panel could say "Business Analyst roles"
      // while Start Mock Interview silently started a Data Scientist session.
      const goal = CAREER_ID_TO_GOAL[careerId];
      if (goal) setCareerGoal(goal);
      document.getElementById("roadmap-section")?.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load that roadmap");
    }
  }

  const NEXT_ROADMAP_STATUS = { pending: "in_progress", in_progress: "completed", completed: "pending" } as const;

  // Milestones now persist real progress (database/models.py's Roadmap
  // table) instead of being recomputed from the CV and thrown away on every
  // page load — clicking a step cycles pending -> in progress -> completed
  // and that choice sticks across visits.
  async function handleToggleRoadmapStep(roadmapId: number) {
    if (!roadmap) return;
    const current = roadmap.steps.find((s) => s.roadmap_id === roadmapId);
    if (!current) return;
    const nextStatus = NEXT_ROADMAP_STATUS[current.status];
    const previous = roadmap;
    setRoadmap({
      ...roadmap,
      steps: roadmap.steps.map((s) => (s.roadmap_id === roadmapId ? { ...s, status: nextStatus } : s)),
    });
    try {
      await apiFetch(`/career/roadmap/${roadmapId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });
    } catch (err) {
      setRoadmap(previous); // roll back on failure
      setError(err instanceof ApiError ? err.message : "Couldn't update that milestone");
    }
  }

  // Career Counseling had no connection to the Learning Portal at all —
  // Exam Prep's "Today's Topic" video already had an identical Add to
  // Playlist button, so a student could start closing a skill gap the
  // roadmap just told them about, same as they already could for an
  // exam-prep topic.
  async function handleAddRoadmapVideoToPlaylist(video: { title: string; source: string; duration_min: number }) {
    try {
      await apiFetch("/learning/playlist", {
        method: "POST",
        body: JSON.stringify({
          title: video.title,
          subject: roadmap?.title ?? "Career Development",
          source: video.source,
          duration_min: video.duration_min,
        }),
      });
      setAddedRoadmapVideos((prev) => [...prev, video.title]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't add that video");
    }
  }

  async function handleAskCareerQuestion(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!careerQuestion.trim()) return;
    setCareerAsking(true);
    setCareerAskError(null);
    setCareerAnswer(null);
    try {
      const result = await apiFetch<RagAnswerResponse>(`/career/ask?query=${encodeURIComponent(careerQuestion)}`);
      setCareerAnswer(result.answer);
    } catch (err) {
      setCareerAskError(err instanceof ApiError ? err.message : "Couldn't get an answer right now");
    } finally {
      setCareerAsking(false);
    }
  }

  async function handleStartInterview() {
    setInterviewLoading(true);
    setError(null);
    try {
      // career_goal is a REQUIRED query param on the real endpoint — the
      // original wiring never sent it, which would 422 every time.
      const session = await apiFetch<InterviewStartResponse>(
        `/interview/start?career_goal=${encodeURIComponent(careerGoal)}`,
        { method: "POST" }
      );
      setInterview(session);
      setInterviewHistory([]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't start the mock interview");
    } finally {
      setInterviewLoading(false);
    }
  }

  async function handleInterviewAsk(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!interview || !interviewAnswer.trim()) return;
    const studentAnswer = interviewAnswer;
    setInterviewLoading(true);
    try {
      const result = await apiFetch<InterviewAskResponse>(`/interview/${interview.interview_id}/ask`, {
        method: "POST",
        body: JSON.stringify({ answer: studentAnswer }),
      });
      // The model's reply deliberately combines feedback on the last answer
      // AND the next question into one block of text (Phase 7's design —
      // the RAG prompt doesn't ask for structured output), so it's rendered
      // as one continuing conversation, not split into separate fields.
      setInterviewHistory((prev) => [...prev, { role: "student", text: studentAnswer }, { role: "ai", text: result.answer }]);
      setInterviewAnswer("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't submit that answer");
    } finally {
      setInterviewLoading(false);
    }
  }

  return (
    <>
      <SiteHeader variant="app" />

      <section className="page-heading">
        <div className="container">
          <div>
            <h1>Career Counseling</h1>
            <p>AI-powered career-fit analysis using your CV · 50+ career paths ranked · 6-month roadmap builder</p>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          {error && <div className="form-error">{error}</div>}

          <div className="grid-3" style={{ marginBottom: 28 }}>
            <div className="panel">
              <div className="small-muted" style={{ marginBottom: 14 }}>
                Step 1 — Upload CV / Transcript
              </div>
              <form id="cv-upload-form" name="cv-upload-form" onSubmit={handleCvUpload}>
                <label
                  htmlFor="cv_file"
                  style={{
                    display: "block",
                    border: "1px dashed var(--border-soft)",
                    borderRadius: 8,
                    padding: 24,
                    textAlign: "center",
                    cursor: "pointer",
                  }}
                >
                  <p style={{ fontSize: "0.85rem", color: "var(--ink-500)", margin: "0 0 14px" }}>
                    Drag & drop your CV or Transcript
                    <br />
                    Supports PDF, DOCX formats · NER model extracts your data
                  </p>
                  <span className="btn btn-primary btn-sm">{uploading ? "Uploading…" : "Browse File"}</span>
                  <input
                    type="file"
                    id="cv_file"
                    name="cv_file"
                    accept=".pdf,.docx"
                    onChange={(e) => e.target.form?.requestSubmit()}
                    style={{ position: "absolute", width: 1, height: 1, opacity: 0, overflow: "hidden" }}
                  />
                </label>
              </form>
            </div>

            <div className="panel">
              <div className="small-muted" style={{ marginBottom: 14 }}>
                Step 2 — Skills Extracted (AI)
              </div>
              {extracted && editingInfo ? (
                <form onSubmit={handleEditInfoSubmit}>
                  <div className="field">
                    <label htmlFor="gpa">GPA</label>
                    <input id="gpa" name="gpa" type="number" step="0.1" min="0" max="4" defaultValue={extracted.gpa ?? ""} placeholder="Not detected" />
                  </div>
                  <div className="field">
                    <label htmlFor="skills">Technical Skills (comma-separated)</label>
                    <input id="skills" name="skills" defaultValue={extracted.skills.join(", ")} />
                  </div>
                  <div className="field">
                    <label htmlFor="certifications">Certifications (comma-separated)</label>
                    <input id="certifications" name="certifications" defaultValue={extracted.certifications.join(", ")} />
                  </div>
                  <div className="field">
                    <label htmlFor="degrees">Degrees (comma-separated)</label>
                    <input id="degrees" name="degrees" defaultValue={extracted.degrees.join(", ")} />
                  </div>
                  <div className="flex-between" style={{ gap: 8 }}>
                    <button type="submit" className="btn btn-primary btn-sm" style={{ flex: 1 }}>
                      Save
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline btn-sm"
                      style={{ flex: 1 }}
                      onClick={() => setEditingInfo(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : extracted ? (
                <>
                  <div className="flex-between" style={{ marginBottom: 12 }}>
                    <span className="small-muted">GPA</span>
                    <strong>{extracted.gpa !== null ? `${extracted.gpa} / 4.0` : "Not detected"}</strong>
                  </div>
                  <div className="small-muted" style={{ marginBottom: 6 }}>
                    Technical Skills
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    {extracted.skills.length > 0 ? (
                      extracted.skills.map((skill) => (
                        <span className="chip" key={skill}>
                          {skill}
                        </span>
                      ))
                    ) : (
                      <span className="small-muted">None detected</span>
                    )}
                  </div>
                  <div className="small-muted" style={{ marginBottom: 6 }}>
                    Certifications
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    {extracted.certifications.length > 0 ? (
                      extracted.certifications.map((cert) => (
                        <span className="chip" key={cert}>
                          {cert}
                        </span>
                      ))
                    ) : (
                      <span className="small-muted">None detected</span>
                    )}
                  </div>
                  <div className="small-muted" style={{ marginBottom: 6 }}>
                    Degrees
                  </div>
                  <div style={{ marginBottom: 14 }}>
                    {extracted.degrees.length > 0 ? (
                      extracted.degrees.map((degree) => (
                        <span className="chip" key={degree}>
                          {degree}
                        </span>
                      ))
                    ) : (
                      <span className="small-muted">None detected</span>
                    )}
                  </div>
                  <button className="btn btn-outline btn-block btn-sm" onClick={() => setEditingInfo(true)}>
                    Edit extracted info
                  </button>
                </>
              ) : (
                <p className="small-muted" style={{ marginBottom: 14 }}>
                  Upload a CV in Step 1 to see extracted skills here.
                </p>
              )}
            </div>

            <div className="panel">
              <div className="small-muted" style={{ marginBottom: 14 }}>
                Step 3 — Set Career Goal
              </div>
              <form id="career-goal-form" name="career-goal-form">
                <div className="field">
                  <label htmlFor="career_goal">Your selected goal</label>
                  <select id="career_goal" name="career_goal" required value={careerGoal} onChange={handleGoalChange}>
                    <option value="data_scientist">◆ Data Scientist</option>
                    <option value="ml_engineer">ML Engineer</option>
                    <option value="business_analyst">Business Analyst</option>
                    <option value="software_engineer">Software Engineer</option>
                    <option value="product_manager">Product Manager</option>
                    <option value="ux_ui_designer">UX/UI Designer</option>
                    <option value="devops_engineer">DevOps Engineer</option>
                    <option value="cybersecurity_analyst">Cybersecurity Analyst</option>
                    <option value="digital_marketing_specialist">Digital Marketing Specialist</option>
                    <option value="financial_analyst">Financial Analyst</option>
                  </select>
                </div>
              </form>
              <p className="small-muted text-center" style={{ margin: "0 0 12px" }}>
                Or let AI suggest best fit →
              </p>
              <button type="button" id="ai-suggest-career" className="btn btn-primary btn-block" onClick={handleAiSuggest}>
                AI Suggest Best Career
              </button>
            </div>
          </div>

          <div className="small-muted" style={{ marginBottom: 14 }}>
            Your Career Fit Rankings (AI — Top 5 of 50+ Paths · Model: {rankings?.model ?? "…"})
          </div>
          <table className="data-table" style={{ marginBottom: 32 }}>
            <thead>
              <tr>
                <th>Career Path</th>
                <th>Match Score</th>
                <th>Key Skill Gap</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rankings ? (
                rankings.rankings.map((rank) => (
                  <tr key={rank.career_id}>
                    <td>{rank.title}</td>
                    <td>
                      <span className="progress-track">
                        <span
                          className={`progress-fill${PROGRESS_CLASS(rank.match_score)}`}
                          style={{ width: `${rank.match_score}%` }}
                        />
                      </span>
                      {rank.match_score}%
                    </td>
                    <td>{rank.key_skill_gap}</td>
                    <td>
                      <button className="btn btn-outline btn-sm" onClick={() => handleViewRoadmap(rank.career_id)}>
                        View Roadmap
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="small-muted">
                    {error ? "Upload a CV above to see your rankings." : "Loading rankings…"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div id="roadmap-section" className="small-muted" style={{ marginBottom: 16 }}>
            6-Month Skill Roadmap — {roadmap?.title ?? "…"}
          </div>
          <div className="timeline" style={{ marginBottom: 32 }}>
            {(roadmap?.steps ?? []).map((step) => (
              <div
                key={step.roadmap_id}
                className={`step${step.status === "completed" ? " is-complete" : step.status === "in_progress" ? " is-current" : ""}`}
                data-status={step.status}
              >
                <button
                  type="button"
                  className="step-circle"
                  style={{ cursor: "pointer", padding: 0, font: "inherit", fontWeight: 700 }}
                  onClick={() => handleToggleRoadmapStep(step.roadmap_id)}
                  title={`Status: ${step.status.replace("_", " ")} — click to update`}
                >
                  {step.month_number}
                </button>
                <p>
                  {step.milestone_title}
                  <br />
                  <span className="small-muted">{step.description}</span>
                </p>
              </div>
            ))}
          </div>

          {roadmap && roadmap.steps.some((s) => s.video) && (
            <div style={{ marginBottom: 32 }}>
              {roadmap.steps
                .filter((step) => step.video)
                .map((step) => (
                  <div key={step.roadmap_id} className="panel" style={{ marginBottom: 14 }}>
                    <div className="flex-between" style={{ marginBottom: 8, alignItems: "flex-start" }}>
                      <h4 style={{ margin: 0 }}>
                        Month {step.month_number} — {step.milestone_title}
                      </h4>
                      <span className={`status-pill ${step.status === "completed" ? "status-done" : step.status === "in_progress" ? "status-today" : ""}`}>
                        {step.status.replace("_", " ")}
                      </span>
                    </div>
                    <p className="small-muted" style={{ margin: "0 0 14px" }}>
                      {step.explanation ?? "AI explanation is temporarily unavailable for this milestone."}
                    </p>
                    {step.video && (
                      <button
                        className="btn btn-outline btn-sm"
                        disabled={addedRoadmapVideos.includes(step.video.title)}
                        onClick={() => handleAddRoadmapVideoToPlaylist(step.video!)}
                      >
                        {addedRoadmapVideos.includes(step.video.title) ? "Added ✓" : `+ Add "${step.video.title}" to Playlist`}
                      </button>
                    )}
                  </div>
                ))}
            </div>
          )}

          <div id="career-qa" className="panel-tint" style={{ marginBottom: 24, scrollMarginTop: 90 }}>
            <h4 style={{ margin: "0 0 4px" }}>Ask a Career Question</h4>
            <p className="small-muted" style={{ margin: "0 0 14px" }}>
              e.g. "What skills matter most for an ML Engineer role?" · Powered by RAG + Career Knowledge Base
            </p>
            <form onSubmit={handleAskCareerQuestion} className="flex-between" style={{ gap: 10 }}>
              <input
                type="text"
                value={careerQuestion}
                onChange={(e) => setCareerQuestion(e.target.value)}
                placeholder="Type your question…"
                style={{
                  flex: 1,
                  padding: "12px 14px",
                  border: "1px solid var(--border-soft)",
                  borderRadius: 8,
                  background: "var(--white)",
                  fontSize: "0.92rem",
                }}
              />
              <button type="submit" className="btn btn-primary" disabled={careerAsking}>
                {careerAsking ? "Asking…" : "Ask"}
              </button>
            </form>
            {careerAskError && (
              <div className="form-error" style={{ marginTop: 14, marginBottom: 0 }}>
                {careerAskError}
              </div>
            )}
            {careerAnswer && (
              <p className="small-muted" style={{ marginTop: 14, marginBottom: 0, whiteSpace: "pre-wrap" }}>
                {careerAnswer}
              </p>
            )}
          </div>

          <div id="mock-interview" className="panel-tint">
            <div className="flex-between">
              <div>
                <h4 style={{ margin: "0 0 4px" }}>Mock Interview Simulation</h4>
                <p className="small-muted" style={{ margin: 0 }}>
                  Practice real interview questions for {roadmap?.title ?? "your target"} roles · Powered by RAG +
                  Interview Knowledge Base
                </p>
              </div>
              {!interview && (
                <button
                  type="button"
                  id="start-mock-interview"
                  className="btn btn-primary"
                  onClick={handleStartInterview}
                  disabled={interviewLoading}
                >
                  {interviewLoading ? "Starting…" : "Start Mock Interview →"}
                </button>
              )}
            </div>

            {interview && (
              <div style={{ marginTop: 18 }}>
                <p style={{ fontWeight: 600, marginBottom: 6 }}>Q: {interview.question}</p>
                {interviewHistory.map((turn, i) => (
                  <p
                    key={i}
                    className={turn.role === "student" ? "small-muted" : undefined}
                    style={{ marginBottom: 10, whiteSpace: "pre-wrap" }}
                  >
                    {turn.role === "student" ? "You: " : ""}
                    {turn.text}
                  </p>
                ))}
                <form onSubmit={handleInterviewAsk} className="flex-between" style={{ gap: 10 }}>
                  <input
                    type="text"
                    value={interviewAnswer}
                    onChange={(e) => setInterviewAnswer(e.target.value)}
                    placeholder="Type your answer…"
                    style={{
                      flex: 1,
                      padding: "12px 14px",
                      border: "1px solid var(--border-soft)",
                      borderRadius: 8,
                      background: "var(--white)",
                      fontSize: "0.92rem",
                    }}
                  />
                  <button type="submit" className="btn btn-primary" disabled={interviewLoading}>
                    Send
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>
      </section>

      <SiteFooter />
    </>
  );
}
