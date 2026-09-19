"use client";

import { useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { Material } from "@/lib/types";

export default function MaterialsSection({ initialMaterials }: { initialMaterials: Material[] }) {
  const [materials, setMaterials] = useState(initialMaterials);
  const [statusById, setStatusById] = useState<Record<number, string>>({});
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadingAll, setDownloadingAll] = useState(false);

  async function handleDownload(material: Material) {
    setStatusById((prev) => ({ ...prev, [material.id]: "Requesting…" }));
    try {
      await apiFetch(`/learning/materials/${material.id}/download`);
      setStatusById((prev) => ({ ...prev, [material.id]: "No real file yet — backend confirmed the request" }));
    } catch (err) {
      setStatusById((prev) => ({
        ...prev,
        [material.id]: err instanceof ApiError ? err.message : "Download failed",
      }));
    }
  }

  async function handleDownloadAll() {
    setDownloadingAll(true);
    await Promise.all(materials.map((m) => handleDownload(m)));
    setDownloadingAll(false);
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setUploading(true);
    setError(null);
    try {
      const result = await apiFetch<{ material: Material }>("/learning/materials", {
        method: "POST",
        body: formData,
        headers: {}, // let the browser set the multipart boundary
      });
      setMaterials((prev) => [...prev, result.material]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <>
      <div className="flex-between" style={{ margin: "28px 0 14px" }}>
        <h3 id="materials" style={{ fontFamily: "var(--font-display)", margin: 0, scrollMarginTop: 90 }}>
          Course PDFs
        </h3>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-outline btn-sm" onClick={handleDownloadAll} disabled={downloadingAll || materials.length === 0}>
            {downloadingAll ? "Downloading…" : "Download All"}
          </button>
          <label className="btn btn-primary btn-sm" style={{ cursor: "pointer" }}>
            {uploading ? "Uploading…" : "Upload Content"}
            <input type="file" onChange={handleUpload} disabled={uploading} style={{ display: "none" }} />
          </label>
        </div>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="grid-3">
        {materials.map((material) => (
          <div className="panel" key={material.id}>
            <h4 style={{ margin: "0 0 6px" }}>{material.title}</h4>
            <p className="small-muted" style={{ margin: "0 0 14px" }}>
              {material.size} · {material.source}
            </p>
            <button className="btn btn-outline btn-block btn-sm" onClick={() => handleDownload(material)}>
              Download
            </button>
            {statusById[material.id] && (
              <p className="small-muted" style={{ marginTop: 8, marginBottom: 0 }}>
                {statusById[material.id]}
              </p>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
