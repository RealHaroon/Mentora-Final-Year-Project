"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { PlaylistVideo } from "@/lib/types";

export default function PlaylistSection({
  initialVideos,
  allowedSubjects,
}: {
  initialVideos: PlaylistVideo[];
  allowedSubjects: string[];
}) {
  const [videos, setVideos] = useState(initialVideos);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [adding, setAdding] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

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

  async function logWatch(title: string, subject: string) {
    try {
      await apiFetch("/learning/watch-history", {
        method: "POST",
        body: JSON.stringify({ title, subject }),
      });
      window.dispatchEvent(new Event("mentora:watch-logged"));
    } catch {
      // Watch history is non-critical — the video still opened either way.
    }
  }

  // Found 2026-11-15 testing live, extensively: a React onClick prop on the
  // SAME <a target="_blank"> that performs the navigation reliably broke the
  // native new-tab navigation (confirmed directly — the anchor's own default
  // action silently failed to fire every single time, even though the
  // handler itself ran correctly and logged watch history), while an
  // otherwise-identical anchor with no onClick at all, or with a listener
  // attached via plain addEventListener instead of React's synthetic
  // onClick, worked. Logging watch history via a native, delegated listener
  // here instead — attached to the list container, not the anchor itself —
  // keeps the Watch link a pure, unmodified navigation element, matching
  // Exam Prep's own already-working "▶ Watch" link exactly.
  useEffect(() => {
    const container = listRef.current;
    if (!container) return;
    function handleClick(e: MouseEvent) {
      const link = (e.target as HTMLElement).closest<HTMLAnchorElement>("a.watch-link");
      if (!link) return;
      const title = link.dataset.title;
      const subject = link.dataset.subject;
      if (title && subject) logWatch(title, subject);
    }
    container.addEventListener("click", handleClick);
    return () => container.removeEventListener("click", handleClick);
  }, []);

  async function handleAddVideo(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    // Captured before the first await: the native DOM event's currentTarget
    // is only valid during synchronous dispatch — by the time an async
    // handler resumes after awaiting, e.currentTarget is already null, so
    // calling e.currentTarget.reset() down there throws (even though the
    // add itself already succeeded), which the catch block below reports as
    // "Couldn't add that video" — a false failure on a request that worked.
    const form = e.currentTarget;
    const formData = new FormData(form);
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
          // Found 2026-11-15 testing live: this form never sent a video_url
          // at all, so Watch always fell back to a generic YouTube search
          // for the title — even when a real link (or a real playlist
          // link, like "Inorganic Chemistry" below) had been pasted into
          // the Source field above, which is a display label, not a URL.
          video_url: formData.get("video_url"),
        }),
      });
      // The backend silently no-ops a duplicate title (dedup by title) but
      // still returns a 200 with the submitted video — appending it
      // unconditionally would show a second, inconsistent copy locally.
      setVideos((prev) => (prev.some((v) => v.title === result.video.title) ? prev : [...prev, result.video]));
      setShowAddForm(false);
      form.reset();
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
                {allowedSubjects.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="video-url">Video or playlist link</label>
              <input
                id="video-url"
                name="video_url"
                type="url"
                required
                placeholder="https://www.youtube.com/watch?v=... or a playlist link"
              />
            </div>
            <div className="field">
              <label htmlFor="video-source">Source</label>
              <input id="video-source" name="source" required placeholder="e.g. Khan Academy, YouTube" />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="video-duration">Duration (min)</label>
              <input
                id="video-duration"
                name="duration_min"
                type="number"
                min="1"
                required
                placeholder="For a playlist, estimate the total length"
              />
            </div>
          </div>
          <button type="submit" className="btn btn-primary btn-sm" disabled={adding}>
            {adding ? "Adding…" : "Add to playlist"}
          </button>
        </form>
      )}

      {videos.length === 0 && <p className="small-muted">No videos in your playlist yet.</p>}

      <div ref={listRef}>
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
              {/* A plain, unmodified <a target="_blank"> — no onClick on
                  this element itself (see the useEffect above for why).
                  data-title/data-subject let the delegated listener on the
                  container log watch history without touching this anchor's
                  own default navigation behavior at all. */}
              <a
                href={video.video_url}
                target="_blank"
                rel="noopener noreferrer"
                className="watch-link btn btn-primary btn-sm"
                data-title={video.title}
                data-subject={video.subject}
              >
                Watch
              </a>
              <button className="btn btn-outline btn-sm" onClick={() => handleRemove(video.title)}>
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
