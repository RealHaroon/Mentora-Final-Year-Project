import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import PlaylistSection from "@/components/PlaylistSection";
import MaterialsSection from "@/components/MaterialsSection";
import WatchHistorySection from "@/components/WatchHistorySection";
import { apiFetchServer } from "@/lib/api";
import type { Assignment, LearningStats, Material, PlaylistVideo } from "@/lib/types";

export const metadata: Metadata = {
  title: "Learning Portal",
};

// Without this, Next's client Router Cache can serve a stale render when only
// the ?subject= query string changes via <Link> (same pathname), even though
// the server itself filters correctly on every direct request.
export const dynamic = "force-dynamic";

const SUBJECT_FILTERS = ["Mathematics", "English", "Physics", "Chemistry"];

async function loadPortalData(subject?: string) {
  const token = cookies().get("mentora_session")?.value;
  try {
    const [stats, playlist, assignments, materials] = await Promise.all([
      apiFetchServer<LearningStats>("/learning/stats", token),
      apiFetchServer<{ videos: PlaylistVideo[] }>(
        `/learning/playlist${subject ? `?subject=${encodeURIComponent(subject)}` : ""}`,
        token
      ),
      apiFetchServer<{ assignments: Assignment[] }>("/learning/assignments", token),
      apiFetchServer<{ materials: Material[] }>("/learning/materials", token),
    ]);
    return { stats, videos: playlist.videos, assignments: assignments.assignments, materials: materials.materials, error: null as string | null };
  } catch {
    return { stats: null, videos: [], assignments: [], materials: [], error: "Couldn't load this right now" };
  }
}

export default async function LearningPortalPage({
  searchParams,
}: {
  searchParams: { subject?: string };
}) {
  const activeSubject = searchParams.subject;
  const { stats, videos, assignments, materials, error } = await loadPortalData(activeSubject);

  return (
    <>
      <SiteHeader variant="app" />

      <section className="page-heading">
        <div className="container">
          <div>
            <h1>Learning Portal</h1>
            <p>Your personal playlists, MCQ assignments, and course materials — all in one place</p>
          </div>
          <a href="#materials" className="btn btn-primary">
            Upload Content
          </a>
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
              <a href="#playlists" className="side-link active">
                My Playlists <span className="count-badge">{videos.length}</span>
              </a>
              <a href="#assignments" className="side-link">
                MCQ Assignments <span className="count-badge">{assignments.filter((a) => a.status === "new").length}</span>
              </a>
              <a href="#materials" className="side-link">
                Course PDFs
              </a>
              <a href="#watch-history" className="side-link">
                Watch History
              </a>
              <div className="group-label">Filter by Subject</div>
              {SUBJECT_FILTERS.map((subject) => (
                // Plain <a>, not next/link: Next's client Router Cache can
                // serve a stale render when only ?subject= changes on the
                // same pathname, so force a real full-page navigation here.
                <a
                  key={subject}
                  href={activeSubject === subject ? "/learning-portal#playlists" : `/learning-portal?subject=${subject}#playlists`}
                  className={`side-link${activeSubject === subject ? " active" : ""}`}
                >
                  {subject}
                </a>
              ))}
              {activeSubject && (
                <a href="/learning-portal" className="side-link small-muted">
                  Clear filter ✕
                </a>
              )}
              <div className="group-label">Tools</div>
              <Link href="/exam-prep#topic-explainer" className="side-link">
                AI Topic Explainer
              </Link>
              <a href="#materials" className="side-link">
                Download All
              </a>
            </aside>

            <div>
              <PlaylistSection initialVideos={videos} />

              <h3 id="assignments" style={{ fontFamily: "var(--font-display)", margin: "28px 0 14px", scrollMarginTop: 90 }}>
                MCQ Assignments
              </h3>
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

              <MaterialsSection initialMaterials={materials} />

              <WatchHistorySection />
            </div>
          </div>
        </div>
      </section>

      <SiteFooter />
    </>
  );
}
