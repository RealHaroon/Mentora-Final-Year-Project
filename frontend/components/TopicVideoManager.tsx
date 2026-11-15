"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { TopicVideoEntry } from "@/lib/types";

// Extracted from DashboardSettings.tsx's "videos" panel (2026-11-15) so it
// can live on its own /admin page instead of being buried inside Settings
// alongside password/profile/notifications. Same endpoints, same behavior —
// this is the one real place that controls what Exam Prep's "Suggested
// Video" shows for a topic (see backend/routers/exam.py's _resolve_video).
export default function TopicVideoManager({ initialTopics }: { initialTopics: TopicVideoEntry[] | null }) {
  const [topicVideos, setTopicVideos] = useState<TopicVideoEntry[] | null>(initialTopics);
  const [videoDrafts, setVideoDrafts] = useState<Record<string, { video_url: string; title: string }>>(
    Object.fromEntries((initialTopics ?? []).map((t) => [t.topic, { video_url: t.video_url ?? "", title: t.title ?? "" }]))
  );
  const [videoSaving, setVideoSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (topicVideos !== null) return;
    apiFetch<{ topics: TopicVideoEntry[] }>("/exam/topic-videos")
      .then((data) => {
        setTopicVideos(data.topics);
        setVideoDrafts(
          Object.fromEntries(data.topics.map((t) => [t.topic, { video_url: t.video_url ?? "", title: t.title ?? "" }]))
        );
      })
      .catch(() => setError("Couldn't load topic videos"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSaveTopicVideo(topic: string) {
    const draft = videoDrafts[topic];
    if (!draft?.video_url.trim()) return;
    setVideoSaving(topic);
    setError(null);
    setSuccess(null);
    try {
      await apiFetch(`/exam/topic-videos/${encodeURIComponent(topic)}`, {
        method: "PUT",
        body: JSON.stringify({ video_url: draft.video_url.trim(), title: draft.title.trim() || `${topic} — Overview` }),
      });
      setTopicVideos((prev) =>
        (prev ?? []).map((t) => (t.topic === topic ? { ...t, video_url: draft.video_url.trim(), title: draft.title.trim() } : t))
      );
      setSuccess(`Video saved for ${topic}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save that video");
    } finally {
      setVideoSaving(null);
    }
  }

  async function handleRemoveTopicVideo(topic: string) {
    setVideoSaving(topic);
    setError(null);
    setSuccess(null);
    try {
      await apiFetch(`/exam/topic-videos/${encodeURIComponent(topic)}`, { method: "DELETE" });
      setTopicVideos((prev) => (prev ?? []).map((t) => (t.topic === topic ? { ...t, video_url: null, title: null } : t)));
      setVideoDrafts((prev) => ({ ...prev, [topic]: { video_url: "", title: "" } }));
      setSuccess(`Reverted ${topic} to the default search link`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't remove that video");
    } finally {
      setVideoSaving(null);
    }
  }

  return (
    <div className="panel mt-24">
      <p className="small-muted" style={{ margin: "0 0 14px" }}>
        Exam Prep suggests a generic YouTube search for a topic until you add a real video here — then
        every student sees your curated one instead, for that topic.
      </p>

      {error && <div className="form-error">{error}</div>}
      {success && <div className="form-success">{success}</div>}

      {topicVideos === null ? (
        <p className="small-muted">Loading…</p>
      ) : (
        topicVideos.map((t) => {
          const draft = videoDrafts[t.topic] ?? { video_url: "", title: "" };
          return (
            <div key={t.topic} className="field-row" style={{ alignItems: "flex-end", marginBottom: 14 }}>
              <div className="field" style={{ flex: "0 0 160px" }}>
                <label>{t.topic}</label>
                <input
                  placeholder="Video title"
                  value={draft.title}
                  onChange={(e) => setVideoDrafts((prev) => ({ ...prev, [t.topic]: { ...draft, title: e.target.value } }))}
                />
              </div>
              <div className="field">
                <label>Video URL</label>
                <input
                  placeholder="https://www.youtube.com/watch?v=..."
                  value={draft.video_url}
                  onChange={(e) => setVideoDrafts((prev) => ({ ...prev, [t.topic]: { ...draft, video_url: e.target.value } }))}
                />
              </div>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                disabled={videoSaving === t.topic || !draft.video_url.trim()}
                onClick={() => handleSaveTopicVideo(t.topic)}
              >
                Save
              </button>
              {t.video_url && (
                <button
                  type="button"
                  className="btn btn-sm"
                  style={{ background: "var(--red-100)", color: "var(--red-600)" }}
                  disabled={videoSaving === t.topic}
                  onClick={() => handleRemoveTopicVideo(t.topic)}
                >
                  Remove
                </button>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
