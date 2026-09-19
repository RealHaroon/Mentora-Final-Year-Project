"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { WatchHistoryItem } from "@/lib/types";

export default function WatchHistorySection() {
  const [items, setItems] = useState<WatchHistoryItem[] | null>(null);

  function load() {
    apiFetch<{ items: WatchHistoryItem[] }>("/learning/watch-history")
      .then((data) => setItems(data.items))
      .catch(() => setItems([]));
  }

  useEffect(() => {
    load();
    // PlaylistSection dispatches this after logging a watch — keep this
    // section in sync without needing shared state between the two islands.
    window.addEventListener("mentora:watch-logged", load);
    return () => window.removeEventListener("mentora:watch-logged", load);
  }, []);

  return (
    <>
      <h3 id="watch-history" style={{ fontFamily: "var(--font-display)", margin: "28px 0 14px", scrollMarginTop: 90 }}>
        Watch History
      </h3>
      {items === null && <p className="small-muted">Loading…</p>}
      {items?.length === 0 && <p className="small-muted">Nothing watched yet — hit "Watch" on a playlist video.</p>}
      {items?.map((item, i) => (
        <div className="media-row" key={`${item.title}-${i}`}>
          <div className="media-thumb" />
          <div className="media-info">
            <h4>{item.title}</h4>
            <span className="tag-subject">{item.subject}</span>
            <div className="meta">{new Date(item.watched_at).toLocaleString()}</div>
          </div>
        </div>
      ))}
    </>
  );
}
