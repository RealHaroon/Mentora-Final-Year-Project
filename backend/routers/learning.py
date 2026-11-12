from datetime import timedelta
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from database.models import Material, PlaylistItem, User, WatchHistoryEntry, utcnow
from database.session import get_db
from services.auth_service import get_current_user

router = APIRouter(prefix="/learning", tags=["learning"])

# Real, per-user DB-backed data (PlaylistItem, WatchHistoryEntry, Material —
# database/models.py). Previously these were plain module-level Python lists:
# not just "not persisted to a DB" but shared across EVERY user of the
# process — one account's add/remove/watch was visible to every other
# account. Found 2026-11-10 while writing e2e tests against this; fixed
# 2026-11-12. Materials are the one exception that's intentionally shared:
# owner_user_id is NULL for catalogue resources (board past papers etc.,
# seeded once via scripts/seed_materials.py) and set only for a student's
# own uploads, which stay private to them.
#
# Still mocked, out of scope for this fix: MCQ Assignments (no backing
# table yet — there's no real concept of an "assignment" distinct from the
# question bank/exam-prep flow) and pdfs_downloaded (no download-event log).


def _youtube_search_url(title: str, source: str) -> str:
    # No real video hosting exists yet — link somewhere genuinely useful
    # (a real YouTube search for the topic) instead of a dead/fake link.
    return f"https://www.youtube.com/results?search_query={quote_plus(f'{title} {source}')}"


class PlaylistItemIn(BaseModel):
    title: str
    subject: str
    source: str
    duration_min: int


class WatchEventIn(BaseModel):
    title: str
    subject: str


def _playlist_out(item: PlaylistItem) -> dict:
    return {
        "title": item.title,
        "subject": item.subject,
        "source": item.source,
        "duration_min": item.duration_min,
        "note": item.note,
        "video_url": item.video_url,
    }


def _material_out(m: Material) -> dict:
    return {"id": m.material_id, "title": m.title, "size": m.size_label, "source": m.source}


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    videos_in_playlist = len(db.scalars(select(PlaylistItem).where(PlaylistItem.user_id == user.user_id)).all())
    week_ago = utcnow() - timedelta(days=7)
    videos_watched_this_week = len(
        db.scalars(
            select(WatchHistoryEntry).where(
                WatchHistoryEntry.user_id == user.user_id, WatchHistoryEntry.watched_at >= week_ago
            )
        ).all()
    )
    course_pdfs = len(
        db.scalars(
            select(Material).where(or_(Material.owner_user_id.is_(None), Material.owner_user_id == user.user_id))
        ).all()
    )
    return {
        "videos_in_playlist": videos_in_playlist,
        "videos_watched_this_week": videos_watched_this_week,
        "mcq_assignments": 12,
        "mcq_pending_today": 3,
        "course_pdfs": course_pdfs,
        "pdfs_downloaded": 0,
        "avg_mcq_score": 72,
        "avg_mcq_score_delta": 5,
    }


@router.get("/playlist")
def get_playlist(subject: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(PlaylistItem).where(PlaylistItem.user_id == user.user_id).order_by(PlaylistItem.added_at)
    if subject:
        query = query.where(PlaylistItem.subject.ilike(subject))
    items = db.scalars(query).all()
    return {"videos": [_playlist_out(i) for i in items]}


@router.post("/playlist")
def add_to_playlist(payload: PlaylistItemIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    existing = db.scalar(
        select(PlaylistItem).where(PlaylistItem.user_id == user.user_id, PlaylistItem.title == payload.title)
    )
    if existing is None:
        existing = PlaylistItem(
            user_id=user.user_id,
            title=payload.title,
            subject=payload.subject,
            source=payload.source,
            duration_min=payload.duration_min,
            note="Added manually",
            video_url=_youtube_search_url(payload.title, payload.source),
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return {"detail": "Added to playlist", "video": _playlist_out(existing)}


@router.delete("/playlist/{title}")
def remove_from_playlist(title: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.scalar(select(PlaylistItem).where(PlaylistItem.user_id == user.user_id, PlaylistItem.title == title))
    if item is None:
        raise HTTPException(status_code=404, detail="Video not found in playlist")
    db.delete(item)
    db.commit()
    return {"detail": "Removed from playlist"}


@router.get("/watch-history")
def get_watch_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.scalars(
        select(WatchHistoryEntry)
        .where(WatchHistoryEntry.user_id == user.user_id)
        .order_by(WatchHistoryEntry.watched_at.desc())
    ).all()
    return {"items": [{"title": i.title, "subject": i.subject, "watched_at": i.watched_at.isoformat()} for i in items]}


@router.post("/watch-history")
def log_watch_event(payload: WatchEventIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    entry = WatchHistoryEntry(user_id=user.user_id, title=payload.title, subject=payload.subject)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"detail": "Logged", "entry": {"title": entry.title, "subject": entry.subject, "watched_at": entry.watched_at.isoformat()}}


@router.get("/assignments")
def get_assignments(user: User = Depends(get_current_user)):
    # Still mocked — no real "assignment" concept/table exists yet, distinct
    # from the exam-prep MCQ flow. Out of scope for this fix.
    return {
        "assignments": [
            {"title": "Quadratic Equations Test", "subject": "Mathematics", "question_count": 5, "difficulty": "Medium", "status": "new", "score": None},
            {"title": "English Grammar — Tenses", "subject": "English", "question_count": 5, "difficulty": "Medium", "status": "completed", "score": 60},
        ]
    }


@router.get("/materials")
def get_materials(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    materials = db.scalars(
        select(Material)
        .where(or_(Material.owner_user_id.is_(None), Material.owner_user_id == user.user_id))
        .order_by(Material.material_id)
    ).all()
    return {"materials": [_material_out(m) for m in materials]}


@router.post("/materials")
async def upload_material(file: UploadFile, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    content = await file.read()
    size_kb = max(len(content) / 1024, 0.1)
    size_label = f"{size_kb / 1024:.1f} MB" if size_kb >= 1024 else f"{size_kb:.1f} KB"
    material = Material(
        owner_user_id=user.user_id,
        title=file.filename or "Untitled upload",
        size_label=size_label,
        source="Self-uploaded",
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return {"detail": "Uploaded", "material": _material_out(material)}


@router.get("/materials/{material_id}/download")
def download_material(material_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = db.scalar(
        select(Material).where(
            Material.material_id == material_id,
            or_(Material.owner_user_id.is_(None), Material.owner_user_id == user.user_id),
        )
    )
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    # MOCK — Phase 6+ streams the real file / a signed URL.
    return {"detail": "Download would start here", "material": _material_out(material)}
