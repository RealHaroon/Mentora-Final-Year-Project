from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from database.models import User, utcnow
from services.auth_service import get_current_user

router = APIRouter(prefix="/learning", tags=["learning"])

# MOCK — matches the hardcoded /learning-portal page exactly
# (MENTORA_Frontend_Documentation.md §4.7). The playlist, materials, and
# watch history are in-memory, per-process mutable lists (not persisted to
# the DB — there's no PLAYLIST/WATCH_HISTORY table in the ERD) so
# add/remove/watch feel real within a session.


def _youtube_search_url(title: str, source: str) -> str:
    # No real video hosting exists yet — link somewhere genuinely useful
    # (a real YouTube search for the topic) instead of a dead/fake link.
    return f"https://www.youtube.com/results?search_query={quote_plus(f'{title} {source}')}"


_MATERIALS = [
    {"id": 1, "title": "MDCAT Biology Full Syllabus 2025", "size": "4.2 MB", "source": "Sindh Board"},
    {"id": 2, "title": "Mathematics Chapter Notes — Entry Test", "size": "1.8 MB", "source": "Self-uploaded"},
    {"id": 3, "title": "CSS Past Papers 2020-2024", "size": "6.1 MB", "source": "FPSC Official PDFs"},
]
_next_material_id = 4

_playlist = [
    {"title": "Quadratic Equations — Full Chapter", "subject": "Mathematics", "source": "MathCity.org", "duration_min": 18, "note": "AI-added from today's session"},
    {"title": "Grammar Tenses — Active & Passive Voice", "subject": "English", "source": "Khan Academy", "duration_min": 12, "note": "AI-added"},
    {"title": "Geometry — Circles & Angles Full Revision", "subject": "Mathematics", "source": "MathCity.org", "duration_min": 24, "note": "AI-added"},
]
for _video in _playlist:
    _video["video_url"] = _youtube_search_url(_video["title"], _video["source"])

_watch_history: list[dict] = []


class PlaylistItemIn(BaseModel):
    title: str
    subject: str
    source: str
    duration_min: int


class WatchEventIn(BaseModel):
    title: str
    subject: str


@router.get("/stats")
def get_stats(user: User = Depends(get_current_user)):
    return {
        "videos_in_playlist": len(_playlist),
        "videos_watched_this_week": 14,
        "mcq_assignments": 12,
        "mcq_pending_today": 3,
        "course_pdfs": len(_MATERIALS),
        "pdfs_downloaded": 2,
        "avg_mcq_score": 72,
        "avg_mcq_score_delta": 5,
    }


@router.get("/playlist")
def get_playlist(subject: str | None = None, user: User = Depends(get_current_user)):
    videos = _playlist
    if subject:
        videos = [v for v in videos if v["subject"].lower() == subject.lower()]
    return {"videos": videos}


@router.post("/playlist")
def add_to_playlist(payload: PlaylistItemIn, user: User = Depends(get_current_user)):
    item = {
        **payload.model_dump(),
        "note": "Added manually",
        "video_url": _youtube_search_url(payload.title, payload.source),
    }
    if not any(v["title"] == item["title"] for v in _playlist):
        _playlist.append(item)
    return {"detail": "Added to playlist", "video": item}


@router.delete("/playlist/{title}")
def remove_from_playlist(title: str, user: User = Depends(get_current_user)):
    global _playlist
    before = len(_playlist)
    _playlist = [v for v in _playlist if v["title"] != title]
    if len(_playlist) == before:
        raise HTTPException(status_code=404, detail="Video not found in playlist")
    return {"detail": "Removed from playlist"}


@router.get("/watch-history")
def get_watch_history(user: User = Depends(get_current_user)):
    return {"items": list(reversed(_watch_history))}


@router.post("/watch-history")
def log_watch_event(payload: WatchEventIn, user: User = Depends(get_current_user)):
    entry = {**payload.model_dump(), "watched_at": utcnow().isoformat()}
    _watch_history.append(entry)
    return {"detail": "Logged", "entry": entry}


@router.get("/assignments")
def get_assignments(user: User = Depends(get_current_user)):
    return {
        "assignments": [
            {"title": "Quadratic Equations Test", "subject": "Mathematics", "question_count": 5, "difficulty": "Medium", "status": "new", "score": None},
            {"title": "English Grammar — Tenses", "subject": "English", "question_count": 5, "difficulty": "Medium", "status": "completed", "score": 60},
        ]
    }


@router.get("/materials")
def get_materials(user: User = Depends(get_current_user)):
    return {"materials": _MATERIALS}


@router.post("/materials")
async def upload_material(file: UploadFile, user: User = Depends(get_current_user)):
    global _next_material_id
    content = await file.read()
    size_kb = max(len(content) / 1024, 0.1)
    size_label = f"{size_kb / 1024:.1f} MB" if size_kb >= 1024 else f"{size_kb:.1f} KB"
    material = {
        "id": _next_material_id,
        "title": file.filename or "Untitled upload",
        "size": size_label,
        "source": "Self-uploaded",
    }
    _next_material_id += 1
    _MATERIALS.append(material)
    return {"detail": "Uploaded", "material": material}


@router.get("/materials/{material_id}/download")
def download_material(material_id: int, user: User = Depends(get_current_user)):
    material = next((m for m in _MATERIALS if m["id"] == material_id), None)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    # MOCK — Phase 6+ streams the real file / a signed URL.
    return {"detail": "Download would start here", "material": material}
