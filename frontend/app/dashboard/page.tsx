import type { Metadata } from "next";
import { cookies } from "next/headers";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import DashboardSettings from "@/components/DashboardSettings";
import { apiFetchServer } from "@/lib/api";
import type {
  DashboardStats,
  NotificationItem,
  ScoreTrendPoint,
  UserOut,
  WeakTopic,
  WeeklySnapshotDay,
} from "@/lib/types";

export const metadata: Metadata = {
  title: "Dashboard",
};

const SNAPSHOT_STYLE: Record<string, { background: string; color: string; border?: string }> = {
  done: { background: "var(--mint-card)", color: "var(--green-700)" },
  today: { background: "var(--green-100)", color: "var(--green-700)", border: "2px solid var(--green-700)" },
  missed: { background: "var(--red-100)", color: "var(--red-600)" },
  pending: { background: "var(--green-50)", color: "var(--ink-500)" },
};

const SNAPSHOT_LABEL: Record<string, string> = {
  done: "Done ✓",
  today: "Today",
  missed: "Missed",
  pending: "Pending",
};

const PROGRESS_CLASS = (score: number) => (score >= 70 ? "" : score >= 50 ? " warn" : " low");

async function loadDashboardData() {
  const token = cookies().get("mentora_session")?.value;
  try {
    const [user, stats, trend, snapshot, weakTopics, notifications] = await Promise.all([
      apiFetchServer<UserOut>("/users/me", token),
      apiFetchServer<DashboardStats>("/dashboard/stats", token),
      apiFetchServer<{ points: ScoreTrendPoint[] }>("/dashboard/score-trend", token),
      apiFetchServer<{ days: WeeklySnapshotDay[] }>("/dashboard/weekly-snapshot", token),
      apiFetchServer<{ topics: WeakTopic[] }>("/dashboard/weak-topics", token),
      apiFetchServer<{ items: NotificationItem[] }>("/notifications", token),
    ]);
    return {
      user,
      stats,
      trend: trend.points,
      snapshot: snapshot.days,
      weakTopics: weakTopics.topics,
      notifications: notifications.items,
      error: null as string | null,
    };
  } catch {
    return {
      user: null,
      stats: null,
      trend: [],
      snapshot: [],
      weakTopics: [],
      notifications: [],
      error: "Couldn't load your dashboard right now",
    };
  }
}

function scoreTrendPoints(points: ScoreTrendPoint[]) {
  if (points.length === 0) return { line: "", fill: "" };
  const maxScore = 100;
  const chartWidth = 560;
  const chartHeight = 160;
  const leftPad = 10;
  const rightPad = 55;
  const step = points.length > 1 ? (chartWidth - leftPad - rightPad) / (points.length - 1) : 0;
  const coords = points.map((p, i) => {
    const x = leftPad + i * step;
    const y = chartHeight - (p.score / maxScore) * (chartHeight - 20);
    return `${x.toFixed(0)},${y.toFixed(0)}`;
  });
  const line = coords.join(" ");
  const lastX = leftPad + (points.length - 1) * step;
  const fill = `${line} ${lastX.toFixed(0)},${chartHeight} ${leftPad},${chartHeight}`;
  return { line, fill };
}

export default async function DashboardPage() {
  const { user, stats, trend, snapshot, weakTopics, notifications, error } = await loadDashboardData();
  const { line, fill } = scoreTrendPoints(trend);
  const initials = user ? `${user.first_name[0] ?? ""}${user.last_name[0] ?? ""}`.toUpperCase() : "";

  return (
    <>
      <SiteHeader variant="app" />

      <section id="profile" className="page-heading" style={{ scrollMarginTop: 90 }}>
        <div className="container">
          <div className="profile-row">
            <div className="avatar-circle">{initials}</div>
            <div>
              <h1 style={{ marginBottom: 2 }}>{user ? `${user.first_name} ${user.last_name}` : "—"}</h1>
              <p className="mb-0">{user?.university ?? ""}</p>
              <p className="small-muted" style={{ margin: "2px 0 0" }}>
                Preparing for: {user?.exam_goal ?? "—"}
              </p>
            </div>
          </div>
          <a href="#settings" className="btn btn-primary">
            Edit Profile
          </a>
        </div>
      </section>

      <section className="section">
        <div className="container">
          {error && <div className="form-error">{error}</div>}

          <div className="stat-strip" style={{ marginBottom: 28 }}>
            <div className="stat-cell">
              <div className="stat-label">Exam Sessions</div>
              <div className="stat-num">{stats?.exam_sessions ?? "—"}</div>
              <div className="stat-sub" style={{ color: "var(--ink-500)" }}>
                Total practice sessions
              </div>
            </div>
            <div className="stat-cell">
              <div className="stat-label">Avg. Score</div>
              <div className="stat-num">{stats ? `${stats.avg_score}%` : "—"}</div>
              <div className="stat-sub">{stats ? `+${stats.avg_score_delta}% from last week` : ""}</div>
            </div>
            <div className="stat-cell">
              <div className="stat-label">Videos Watched</div>
              <div className="stat-num">{stats?.videos_watched ?? "—"}</div>
              <div className="stat-sub" style={{ color: "var(--ink-500)" }}>
                {stats ? `${stats.videos_watched_this_week} this week` : ""}
              </div>
            </div>
            <div className="stat-cell">
              <div className="stat-label">Career Match (top)</div>
              <div className="stat-num" style={{ fontSize: "1.2rem" }}>
                {stats?.top_career_match.title ?? "—"}
              </div>
              <div className="stat-sub">{stats ? `${stats.top_career_match.fit_percent}% fit` : ""}</div>
            </div>
          </div>

          <div className="grid-2" style={{ gridTemplateColumns: "2fr 1fr", alignItems: "start" }}>
            <div>
              <div id="score-trend" className="panel" style={{ marginBottom: 20, scrollMarginTop: 90 }}>
                <h4 style={{ margin: "0 0 16px" }}>Score trend (last {trend.length || 10} sessions)</h4>
                <div className="chart-wrap">
                  <svg viewBox="0 0 560 160" width="100%" height="160" preserveAspectRatio="none">
                    <polyline points={line} fill="none" stroke="#1a5c42" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
                    <polyline points={fill} fill="#eef8f2" stroke="none" opacity={0.7} />
                  </svg>
                </div>
                <div className="chart-axis-labels">
                  {trend.map((p) => (
                    <span key={p.session}>{p.session}</span>
                  ))}
                </div>
              </div>

              <div id="weekly-snapshot" className="panel" style={{ scrollMarginTop: 90 }}>
                <h4 style={{ margin: "0 0 14px" }}>This week&apos;s timetable snapshot</h4>
                <div className="snapshot-grid">
                  {snapshot.map((day) => {
                    const style = SNAPSHOT_STYLE[day.status];
                    return (
                      <div className="snapshot-day" style={style} key={day.day}>
                        <div className="day-name">{day.day}</div>
                        <div style={{ color: style.color }}>
                          {SNAPSHOT_LABEL[day.status]}
                          <br />
                          {day.topic}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <p className="small-muted" style={{ margin: "14px 0 0" }}>
                  ● Completion rate this week: {snapshot.filter((d) => d.status === "done").length}/{snapshot.length}{" "}
                  sessions
                </p>
              </div>
            </div>

            <div>
              <h4 style={{ margin: "0 0 12px", display: "flex", alignItems: "center", gap: 6 }}>
                ⚠ Weak Topics (AI flagged)
              </h4>
              {weakTopics.length > 0 ? (
                weakTopics.map((topic) => (
                  <div className="weak-item" key={topic.topic}>
                    <h4>
                      {topic.subject} — {topic.topic}
                    </h4>
                    <div className="score-line">
                      Score: {topic.score}%{topic.note ? ` · ${topic.note}` : ""}
                    </div>
                    <span className="progress-track">
                      <span className={`progress-fill${PROGRESS_CLASS(topic.score)}`} style={{ width: `${topic.score}%` }} />
                    </span>
                  </div>
                ))
              ) : (
                <p className="small-muted">No weak topics flagged yet — take a few MCQ tests to get started.</p>
              )}

              <h4 id="notifications" style={{ margin: "24px 0 12px", display: "flex", alignItems: "center", gap: 6, scrollMarginTop: 90 }}>
                🔔 Notifications
              </h4>
              {notifications.map((n, i) => (
                <div className={`notif-item ${n.type}`} key={i}>
                  {n.message}
                </div>
              ))}
            </div>
          </div>

          <DashboardSettings
            initialFirstName={user?.first_name ?? ""}
            initialLastName={user?.last_name ?? ""}
            initialUniversity={user?.university ?? ""}
          />
        </div>
      </section>

      <SiteFooter />
    </>
  );
}
