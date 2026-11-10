"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import { apiFetch, ApiError } from "@/lib/api";
import type { McqResponse, McqSubmitResponse, RagAnswerResponse, TimetableResponse, TodayTopicResponse } from "@/lib/types";

type Subject = { id: string; label: string };

const SUBJECTS: Subject[] = [
  { id: "mathematics", label: "Mathematics" },
  { id: "chemistry", label: "Chemistry" },
  { id: "urdu", label: "Urdu" },
];

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending",
  done: "Done ✓",
  today: "Today",
  missed: "Missed",
};

export default function ExamPrepPage() {
  const [selectedSubjects, setSelectedSubjects] = useState<string[]>(["mathematics"]);
  const [testDate, setTestDate] = useState("");
  const [studyMode, setStudyMode] = useState("");

  const [timetable, setTimetable] = useState<TimetableResponse | null>(null);
  const [todayTopic, setTodayTopic] = useState<TodayTopicResponse | null>(null);
  const [mcq, setMcq] = useState<McqResponse | null>(null);
  const [mcqResult, setMcqResult] = useState<McqSubmitResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [addedVideos, setAddedVideos] = useState<string[]>([]);

  const [topicQuestion, setTopicQuestion] = useState("");
  const [topicAnswer, setTopicAnswer] = useState<string | null>(null);
  const [topicAsking, setTopicAsking] = useState(false);
  const [topicAskError, setTopicAskError] = useState<string | null>(null);

  useEffect(() => {
    loadAll();
  }, []);

  // Deliberately NOT a single Promise.all gating all three state updates
  // behind whichever request finishes last — /exam/mcq can legitimately
  // take 60-90s (M2, the local FLAN-T5 generator, under load; see Phase 8's
  // Locust findings), which was holding the already-successful timetable
  // and today-topic data hostage behind it. Each fetch now updates its own
  // state independently, as soon as IT resolves.
  function loadAll() {
    const timetable = apiFetch<TimetableResponse>("/exam/timetable")
      .then(setTimetable)
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : "Couldn't load the timetable"));
    const topic = apiFetch<TodayTopicResponse>("/exam/today-topic")
      .then(setTodayTopic)
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : "Couldn't load today's topic"));
    const mcq = apiFetch<McqResponse>("/exam/mcq")
      .then(setMcq)
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : "Couldn't load the MCQ"));
    return Promise.allSettled([timetable, topic, mcq]);
  }

  async function handleRegenerate(e: React.MouseEvent) {
    e.preventDefault();
    setRegenerating(true);
    setLoadError(null);
    setTimetable(null);
    setTodayTopic(null);
    setMcq(null);
    await loadAll();
    setRegenerating(false);
  }

  async function handleAddToPlaylist(video: { title: string; source: string; duration_min: number }) {
    const primarySubject = SUBJECTS.find((s) => s.id === selectedSubjects[0])?.label ?? "Mathematics";
    try {
      await apiFetch("/learning/playlist", {
        method: "POST",
        body: JSON.stringify({
          title: video.title,
          subject: primarySubject,
          source: video.source,
          duration_min: video.duration_min,
        }),
      });
      setAddedVideos((prev) => [...prev, video.title]);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Couldn't add that video");
    }
  }

  async function savePreferences(next: { subjects?: string[]; test_date?: string; study_mode?: string }) {
    try {
      await apiFetch("/exam/subjects", {
        method: "PATCH",
        body: JSON.stringify({
          subjects: next.subjects ?? selectedSubjects,
          test_date: next.test_date ?? (testDate || null),
          study_mode: next.study_mode ?? (studyMode || null),
        }),
      });
    } catch {
      // Preferences are non-critical — fail silently rather than block the UI.
    }
  }

  async function handleAskTopicQuestion(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!topicQuestion.trim()) return;
    setTopicAsking(true);
    setTopicAskError(null);
    setTopicAnswer(null);
    try {
      const result = await apiFetch<RagAnswerResponse>(`/exam/topic-explainer?query=${encodeURIComponent(topicQuestion)}`);
      setTopicAnswer(result.answer);
    } catch (err) {
      setTopicAskError(err instanceof ApiError ? err.message : "Couldn't get an answer right now");
    } finally {
      setTopicAsking(false);
    }
  }

  function toggleSubject(id: string) {
    const next = selectedSubjects.includes(id)
      ? selectedSubjects.filter((s) => s !== id)
      : [...selectedSubjects, id];
    setSelectedSubjects(next);
    savePreferences({ subjects: next });
  }

  async function handleMcqSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!mcq) return;
    const formData = new FormData(e.currentTarget);
    const answer = formData.get(`answer_${mcq.question.question_id}`);
    if (!answer) return;

    setSubmitting(true);
    setMcqResult(null);
    try {
      const result = await apiFetch<McqSubmitResponse>("/exam/mcq/submit", {
        method: "POST",
        body: JSON.stringify({ question_id: mcq.question.question_id, answer }),
      });
      setMcqResult(result);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Couldn't submit that answer");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <SiteHeader variant="app" />

      <section className="page-heading">
        <div className="container">
          <div>
            <h1>Sindh University Entry Test Prep</h1>
            <p>AI-generated timetable · Auto-updated daily</p>
          </div>
          <Link href="/learning-portal#materials" className="btn btn-primary">
            Upload Content
          </Link>
        </div>
      </section>

      <section className="section">
        <div className="container">
          {loadError && <div className="form-error">{loadError}</div>}

          <div className="grid-2" style={{ gridTemplateColumns: "200px 1fr", marginBottom: 28 }}>
            <div className="stat-block">
              <div className="stat-num">{timetable?.days_to_exam ?? "—"}</div>
              <div className="stat-label">Days to Exam · Auto-updated daily</div>
            </div>

            <div className="panel-tint">
              <div className="small-muted" style={{ marginBottom: 10 }}>
                Select subjects & test date
              </div>
              <div id="subject-selector" role="group" aria-label="Select subjects">
                {SUBJECTS.map((subject) => {
                  const isSelected = selectedSubjects.includes(subject.id);
                  return (
                    <button
                      key={subject.id}
                      type="button"
                      className={`chip${isSelected ? " selected" : ""}`}
                      data-subject={subject.id}
                      aria-pressed={isSelected}
                      onClick={() => toggleSubject(subject.id)}
                    >
                      {isSelected ? "✓ " : "+ "}
                      {subject.label}
                    </button>
                  );
                })}
              </div>

              <form id="exam-preferences-form" name="exam-preferences-form">
                <div className="field-row mt-24" style={{ marginTop: 16 }}>
                  <div className="field mb-0">
                    <label htmlFor="test_date">Test date</label>
                    <input
                      type="date"
                      id="test_date"
                      name="test_date"
                      value={testDate}
                      onChange={(e) => {
                        setTestDate(e.target.value);
                        savePreferences({ test_date: e.target.value });
                      }}
                    />
                  </div>
                  <div className="field mb-0">
                    <label htmlFor="study_mode">Study mode</label>
                    <select
                      id="study_mode"
                      name="study_mode"
                      value={studyMode}
                      onChange={(e) => {
                        setStudyMode(e.target.value);
                        savePreferences({ study_mode: e.target.value });
                      }}
                    >
                      <option value="" disabled>
                        Select study mode
                      </option>
                      <option value="self_study">Self-study</option>
                      <option value="tutor">With Tutor</option>
                    </select>
                  </div>
                </div>
              </form>
            </div>
          </div>

          <div className="flex-between" style={{ marginBottom: 14 }}>
            <h3 style={{ fontFamily: "var(--font-display)", margin: 0 }}>AI-Generated Study Timetable</h3>
            <a href="#" className="link-inline" onClick={handleRegenerate}>
              {regenerating ? "Regenerating…" : "Regenerate"}
            </a>
          </div>

          <table className="data-table">
            <thead>
              <tr>
                <th>Day</th>
                <th>Topic</th>
                <th>Subject</th>
                <th>Duration</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {timetable ? (
                timetable.rows.map((row) => (
                  <tr key={row.day}>
                    <td>{row.day}</td>
                    <td>{row.topic}</td>
                    <td>{row.subject}</td>
                    <td>{row.duration}</td>
                    <td>
                      <span className={`status-pill status-${row.status}`}>{STATUS_LABEL[row.status]}</span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="small-muted">
                    Loading timetable…
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <h3 style={{ fontFamily: "var(--font-display)", margin: "28px 0 14px" }}>
            {todayTopic ? `Today's Topic: ${todayTopic.topic}` : "Today's Topic"}
          </h3>
          <div className="grid-3">
            <div id="topic-explainer" className="panel" style={{ scrollMarginTop: 90 }}>
              <div className="small-muted" style={{ marginBottom: 8 }}>
                AI Topic Explainer
              </div>
              {todayTopic ? (
                <>
                  <p style={{ fontSize: "0.88rem", color: "var(--ink-700)" }}>{todayTopic.explainer.summary}</p>
                  <ul
                    style={{
                      margin: "0 0 16px",
                      paddingLeft: 18,
                      listStyle: "disc",
                      fontSize: "0.85rem",
                      color: "var(--ink-700)",
                    }}
                  >
                    {todayTopic.explainer.points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="small-muted">Loading…</p>
              )}
              <a href="#mcq-form" className="btn btn-primary btn-block" style={{ marginBottom: 14 }}>
                Take MCQ Test →
              </a>

              <div className="small-muted" style={{ margin: "14px 0 8px" }}>
                Ask AI about this topic
              </div>
              <form onSubmit={handleAskTopicQuestion} className="flex-between" style={{ gap: 8 }}>
                <input
                  type="text"
                  value={topicQuestion}
                  onChange={(e) => setTopicQuestion(e.target.value)}
                  placeholder="e.g. How do I factor a quadratic?"
                  style={{
                    flex: 1,
                    padding: "10px 12px",
                    border: "1px solid var(--border-soft)",
                    borderRadius: 8,
                    background: "var(--white)",
                    fontSize: "0.85rem",
                  }}
                />
                <button type="submit" className="btn btn-primary btn-sm" disabled={topicAsking}>
                  {topicAsking ? "Asking…" : "Ask"}
                </button>
              </form>
              {topicAskError && (
                <div className="form-error" style={{ marginTop: 12, marginBottom: 0 }}>
                  {topicAskError}
                </div>
              )}
              {topicAnswer && (
                <p className="small-muted" style={{ marginTop: 12, marginBottom: 0, whiteSpace: "pre-wrap" }}>
                  {topicAnswer}
                </p>
              )}
            </div>
            {(todayTopic?.videos ?? []).map((video) => (
              <div className="panel" key={video.title}>
                <div className="small-muted" style={{ marginBottom: 8 }}>
                  YouTube Video
                </div>
                <h4 style={{ margin: "0 0 4px" }}>{video.title}</h4>
                <p className="small-muted" style={{ margin: "0 0 14px" }}>
                  {video.source} · {video.duration_min} min · AI-matched
                </p>
                <button
                  className="btn btn-outline btn-block"
                  disabled={addedVideos.includes(video.title)}
                  onClick={() => handleAddToPlaylist(video)}
                >
                  {addedVideos.includes(video.title) ? "Added ✓" : "+ Add to Playlist"}
                </button>
              </div>
            ))}
          </div>

          <form id="mcq-form" name="mcq-form" className="panel mt-24" onSubmit={handleMcqSubmit}>
            {mcq ? (
              <>
                <h4 style={{ margin: "0 0 14px" }}>MCQ Practice — {todayTopic?.topic} (AI-Generated)</h4>
                <p style={{ fontSize: "0.92rem", margin: "0 0 14px" }} data-question-id={mcq.question.question_id}>
                  {mcq.question.text}
                </p>
                {mcq.question.options.map((option) => (
                  <label className="mcq-option" key={option.value}>
                    <input
                      type="radio"
                      name={`answer_${mcq.question.question_id}`}
                      value={option.value}
                      required
                    />{" "}
                    {option.text}
                  </label>
                ))}
                {mcqResult && (
                  <div className={mcqResult.correct === null ? "form-neutral" : mcqResult.correct ? "form-success" : "form-error"}>
                    {mcqResult.correct === null
                      ? (mcqResult.detail ?? "This question isn't gradable.")
                      : mcqResult.correct
                        ? "Correct!"
                        : `Not quite — the correct answer is ${mcqResult.correct_answer}.`}
                    {mcqResult.weak_topics_flagged && mcqResult.weak_topics_flagged.length > 0 && (
                      <>
                        {" "}
                        AI flagged: {mcqResult.weak_topics_flagged.join(", ")}.
                      </>
                    )}
                  </div>
                )}
                <div className="flex-between mt-24">
                  <button type="submit" className="btn btn-primary" disabled={submitting}>
                    {submitting ? "Submitting…" : "Submit →"}
                  </button>
                  <span className="small-muted">
                    {mcq.total} MCQs total · {mcq.remaining} remaining · Generated by {mcq.generated_by}
                  </span>
                </div>
              </>
            ) : (
              <p className="small-muted">Loading MCQ…</p>
            )}
          </form>
        </div>
      </section>

      <SiteFooter />
    </>
  );
}
