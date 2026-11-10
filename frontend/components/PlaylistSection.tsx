"use client";

import { useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { PlaylistVideo } from "@/lib/types";

const SUBJECTS = ["Mathematics", "English", "Physics", "Chemistry"];

export default function PlaylistSection({ initialVideos }: { initialVideos: PlaylistVideo[] }) {
  const [videos, setVideos] = useState(initialVideos);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [adding, setAdding] = useState(false);

  async function handleRemove(title: string) {
    const previous = videos;
    setVideos((prev) => prev.filter((v) => v.title !== title));
    try {
      await apiFetch(`/learning/playlist/${encodeURIComponent(title)}`, { method: "DELETE" });
    } catch (err) {
      setVideos(previous); // roll back on failure
      setError(err instanceof ApiError ? err.message : "Couldn't remove that video");
    }
  }

  async function handleWatch(video: PlaylistVideo) {
    window.open(video.video_url, "_blank", "noopener,noreferrer");
    try {
      await apiFetch("/learning/watch-history", {
        method: "POST",
        body: JSON.stringify({ title: video.title, subject: video.subject }),
      });
      window.dispatchEvent(new Event("mentora:watch-logged"));
    } catch {
      // Watch history is non-critical — the video still opened either way.
    }
  }

  async function handleAddVideo(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    setAdding(true);
    setError(null);
    try {
      const result = await apiFetch<{ video: PlaylistVideo }>("/learning/playlist", {
        method: "POST",
        body: JSON.stringify({
          title: formData.get("title"),
          subject: formData.get("subject"),
          source: formData.get("source"),
          duration_min: Number(formData.get("duration_min")),
        }),
      });
      // The backend silently no-ops a duplicate title (dedup by title) but
      // still returns a 200 with the submitted video — appending it
      // unconditionally would show a second, inconsistent copy locally.
      setVideos((prev) => (prev.some((v) => v.title === result.video.title) ? prev : [...prev, result.video]));
      setShowAddForm(false);
      e.currentTarget.reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't add that video");
    } finally {
      setAdding(false);
    }
  }

  return (
    <>
      <div className="flex-between" style={{ marginBottom: 14 }}>
        <h3 id="playlists" style={{ fontFamily: "var(--font-display)", margin: 0, scrollMarginTop: 90 }}>
          My Video Playlists
        </h3>
        <button className="btn btn-primary btn-sm" onClick={() => setShowAddForm((v) => !v)}>
          {showAddForm ? "Cancel" : "Add Video"}
        </button>
      </div>

      {error && <div className="form-error">{error}</div>}

      {showAddForm && (
        <form onSubmit={handleAddVideo} className="panel" style={{ marginBottom: 16 }}>
          <div className="field-row">
            <div className="field">
              <label htmlFor="video-title">Title</label>
              <input id="video-title" name="title" required placeholder="e.g. Trigonometry Basics" />
            </div>
            <div className="field">
              <label htmlFor="video-subject">Subject</label>
              <select id="video-subject" name="subject" required defaultValue="">
                <option value="" disabled>
                  Select subject
                </option>
                {SUBJECTS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="video-source">Source</label>
              <input id="video-source" name="source" required placeholder="e.g. Khan Academy" />
            </div>
            <div className="field">
              <label htmlFor="video-duration">Duration (min)</label>
              <input id="video-duration" name="duration_min" type="number" min="1" required />
            </div>
          </div>
          <button type="submit" className="btn btn-primary btn-sm" disabled={adding}>
            {adding ? "Adding…" : "Add to playlist"}
          </button>
        </form>
      )}

      {videos.length === 0 && <p className="small-muted">No videos in your playlist yet.</p>}

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
            <button className="btn btn-primary btn-sm" onClick={() => handleWatch(video)}>
              Watch
            </button>
            <button className="btn btn-outline btn-sm" onClick={() => handleRemove(video.title)}>
              Remove
            </button>
          </div>
        </div>
      ))}
    </>
  );
}
