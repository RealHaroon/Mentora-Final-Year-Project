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
  RankingsResponse,
  RoadmapResponse,
} from "@/lib/types";

const PROGRESS_CLASS = (score: number) => (score >= 75 ? "" : score >= 50 ? " warn" : " low");

export default function CareerPage() {
  const [extracted, setExtracted] = useState<CvUploadResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [careerGoal, setCareerGoal] = useState("data_scientist");

  const [rankings, setRankings] = useState<RankingsResponse | null>(null);
  const [roadmap, setRoadmap] = useState<RoadmapResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [interview, setInterview] = useState<InterviewStartResponse | null>(null);
  const [interviewFeedback, setInterviewFeedback] = useState<InterviewAskResponse | null>(null);
  const [interviewAnswer, setInterviewAnswer] = useState("");
  const [interviewLoading, setInterviewLoading] = useState(false);

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
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "CV upload failed");
    } finally {
      setUploading(false);
    }
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
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save career goal");
    }
  }

  async function handleAiSuggest() {
    try {
      const suggestion = await apiFetch<AiSuggestResponse>("/career/ai-suggest");
      setCareerGoal(suggestion.career_goal);
      await refreshRankings();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't get an AI suggestion");
    }
  }

  async function handleViewRoadmap(careerId: number) {
    try {
      const data = await apiFetch<RoadmapResponse>(`/career/roadmap?career_id=${careerId}`);
      setRoadmap(data);
      document.getElementById("roadmap-section")?.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load that roadmap");
    }
  }

  async function handleStartInterview() {
    setInterviewLoading(true);
    setError(null);
    try {
      const session = await apiFetch<InterviewStartResponse>("/interview/start", { method: "POST" });
      setInterview(session);
      setInterviewFeedback(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't start the mock interview");
    } finally {
      setInterviewLoading(false);
    }
  }

  async function handleInterviewAsk(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!interview || !interviewAnswer.trim()) return;
    setInterviewLoading(true);
    try {
      const result = await apiFetch<InterviewAskResponse>(`/interview/${interview.interview_id}/ask`, {
        method: "POST",
        body: JSON.stringify({ answer: interviewAnswer }),
      });
      setInterviewFeedback(result);
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
              {extracted ? (
                <>
                  <div className="flex-between" style={{ marginBottom: 12 }}>
                    <span className="small-muted">GPA</span>
                    <strong>{extracted.gpa} / 4.0</strong>
                  </div>
                  <div className="small-muted" style={{ marginBottom: 6 }}>
                    Technical Skills
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    {extracted.skills.map((skill) => (
                      <span className="chip" key={skill}>
                        {skill}
                      </span>
                    ))}
                  </div>
                  <div className="small-muted" style={{ marginBottom: 6 }}>
                    Certifications
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    {extracted.certifications.map((cert) => (
                      <span className="chip" key={cert}>
                        {cert}
                      </span>
                    ))}
                  </div>
                  <div className="small-muted" style={{ marginBottom: 6 }}>
                    Projects
                  </div>
                  <div style={{ marginBottom: 14 }}>
                    {extracted.projects.map((project) => (
                      <span className="chip" key={project}>
                        {project}
                      </span>
                    ))}
                  </div>
                </>
              ) : (
                <p className="small-muted" style={{ marginBottom: 14 }}>
                  Upload a CV in Step 1 to see extracted skills here.
                </p>
              )}
              <button className="btn btn-outline btn-block btn-sm">Edit extracted info</button>
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
                    Loading rankings…
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
                key={step.milestone_title}
                className={`step${step.status === "completed" ? " is-complete" : step.status === "in_progress" ? " is-current" : ""}`}
                data-status={step.status}
              >
                <div className="step-circle">{step.month_number}</div>
                <p>
                  {step.milestone_title}
                  <br />
                  <span className="small-muted">{step.description}</span>
                </p>
              </div>
            ))}
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
                <p style={{ fontWeight: 600, marginBottom: 6 }}>Q: {interviewFeedback?.next_question ?? interview.question}</p>
                {interviewFeedback && (
                  <p className="small-muted" style={{ marginBottom: 14 }}>
                    {interviewFeedback.ai_feedback}
                  </p>
                )}
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
