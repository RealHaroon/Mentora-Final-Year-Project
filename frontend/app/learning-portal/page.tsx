import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import { apiFetchServer } from "@/lib/api";
import type { Assignment, LearningStats, Material, PlaylistVideo } from "@/lib/types";

export const metadata: Metadata = {
  title: "Learning Portal",
};

async function loadPortalData() {
  const token = cookies().get("mentora_session")?.value;
  try {
    const [stats, playlist, assignments, materials] = await Promise.all([
      apiFetchServer<LearningStats>("/learning/stats", token),
      apiFetchServer<{ videos: PlaylistVideo[] }>("/learning/playlist", token),
      apiFetchServer<{ assignments: Assignment[] }>("/learning/assignments", token),
      apiFetchServer<{ materials: Material[] }>("/learning/materials", token),
    ]);
    return { stats, videos: playlist.videos, assignments: assignments.assignments, materials: materials.materials, error: null as string | null };
  } catch {
    return { stats: null, videos: [], assignments: [], materials: [], error: "Couldn't load this right now" };
  }
}

export default async function LearningPortalPage() {
  const { stats, videos, assignments, materials, error } = await loadPortalData();

  return (
    <>
      <SiteHeader variant="app" />

      <section className="page-heading">
        <div className="container">
          <div>
            <h1>Learning Portal</h1>
            <p>Your personal playlists, MCQ assignments, and course materials — all in one place</p>
          </div>
          <button className="btn btn-primary">Upload Content</button>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 32 }}>
        <div className="container">
          {error && <div className="form-error">{error}</div>}

          <div className="stat-strip mt-24" style={{ marginBottom: 28 }}>
            <div className="stat-cell">
              <div className="stat-label">Videos in Playlist</div>
              <div className="stat-num">{stats?.videos_in_playlist ?? "—"}</div>
              <div className="stat-sub">{stats ? `${stats.videos_watched_this_week} watched this week` : ""}</div>
            </div>
            <div className="stat-cell">
              <div className="stat-label">MCQ Assignments</div>
              <div className="stat-num">{stats?.mcq_assignments ?? "—"}</div>
              <div className="stat-sub">{stats ? `${stats.mcq_pending_today} pending today` : ""}</div>
            </div>
            <div className="stat-cell">
              <div className="stat-label">Course PDFs</div>
              <div className="stat-num">{stats?.course_pdfs ?? "—"}</div>
              <div className="stat-sub">{stats ? `${stats.pdfs_downloaded} downloaded` : ""}</div>
            </div>
            <div className="stat-cell">
              <div className="stat-label">Avg. MCQ Score</div>
              <div className="stat-num">{stats ? `${stats.avg_mcq_score}%` : "—"}</div>
              <div className="stat-sub">{stats ? `+${stats.avg_mcq_score_delta}% this week` : ""}</div>
            </div>
          </div>

          <div className="layout-sidebar">
            <aside className="side-nav-block">
              <div className="group-label">My Content</div>
              <a href="#" className="side-link active">
                My Playlists <span className="count-badge">{videos.length}</span>
              </a>
              <a href="#" className="side-link">
                MCQ Assignments <span className="count-badge">{assignments.filter((a) => a.status === "new").length}</span>
              </a>
              <a href="#" className="side-link">
                Course PDFs
              </a>
              <a href="#" className="side-link">
                Watch History
              </a>
              <div className="group-label">Filter by Subject</div>
              <a href="#" className="side-link">
                Mathematics
              </a>
              <a href="#" className="side-link">
                English
              </a>
              <a href="#" className="side-link">
                Physics
              </a>
              <a href="#" className="side-link">
                Chemistry
              </a>
              <div className="group-label">Tools</div>
              <a href="#" className="side-link">
                AI Topic Explainer
              </a>
              <a href="#" className="side-link">
                Download All
              </a>
            </aside>

            <div>
              <div className="flex-between" style={{ marginBottom: 14 }}>
                <h3 style={{ fontFamily: "var(--font-display)", margin: 0 }}>My Video Playlists</h3>
                <button className="btn btn-primary btn-sm">Add Video</button>
              </div>

              {videos.map((video) => (
                <div className="media-row" key={video.title}>
                  <div className="media-thumb" />
                  <div className="media-info">
                    <h4>{video.title}</h4>
                    <span className="tag-subject">{video.subject}</span>
                    <div className="meta">
                      {video.source} · {video.duration_min} min · {video.note}
                    </div>
                  </div>
                  <div className="media-actions">
                    <button className="btn btn-primary btn-sm">Watch</button>
                    <button className="btn btn-outline btn-sm">Remove</button>
                  </div>
                </div>
              ))}

              <h3 style={{ fontFamily: "var(--font-display)", margin: "28px 0 14px" }}>MCQ Assignments</h3>
              <div className="grid-2" style={{ marginBottom: 28 }}>
                {assignments.map((assignment) => (
                  <div className="panel" key={assignment.title}>
                    <div className="flex-between" style={{ marginBottom: 10 }}>
                      <h4 style={{ margin: 0 }}>{assignment.title}</h4>
                      <span className={`status-pill ${assignment.status === "new" ? "status-today" : "status-done"}`}>
                        {assignment.status === "new" ? "New" : "Completed"}
                      </span>
                    </div>
                    <p className="small-muted" style={{ margin: "0 0 14px" }}>
                      {assignment.subject} · {assignment.question_count} MCQs · Generated by FLAN-T5 · Difficulty:{" "}
                      {assignment.difficulty}
                      {assignment.score !== null && (
                        <>
                          <br />
                          Score: {assignment.score}%
                        </>
                      )}
                    </p>
                    <Link
                      href="/exam-prep"
                      className={assignment.status === "new" ? "btn btn-primary btn-block" : "btn btn-outline btn-block"}
                    >
                      {assignment.status === "new" ? "Start Test →" : "Retry Test →"}
                    </Link>
                  </div>
                ))}
              </div>

              <h3 style={{ fontFamily: "var(--font-display)", margin: "28px 0 14px" }}>Course PDFs</h3>
              <div className="grid-3">
                {materials.map((material) => (
                  <div className="panel" key={material.id}>
                    <h4 style={{ margin: "0 0 6px" }}>{material.title}</h4>
                    <p className="small-muted" style={{ margin: "0 0 14px" }}>
                      {material.size} · {material.source}
                    </p>
                    <button className="btn btn-outline btn-block btn-sm">Download</button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <SiteFooter />
    </>
  );
}
