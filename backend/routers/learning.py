from fastapi import APIRouter, Depends, HTTPException

from database.models import User
from services.auth_service import get_current_user

router = APIRouter(prefix="/learning", tags=["learning"])

# MOCK — matches the hardcoded /learning-portal page exactly
# (MENTORA_Frontend_Documentation.md §4.7).

_MATERIALS = [
    {"id": 1, "title": "MDCAT Biology Full Syllabus 2025", "size": "4.2 MB", "source": "Sindh Board"},
    {"id": 2, "title": "Mathematics Chapter Notes — Entry Test", "size": "1.8 MB", "source": "Self-uploaded"},
    {"id": 3, "title": "CSS Past Papers 2020-2024", "size": "6.1 MB", "source": "FPSC Official PDFs"},
]


@router.get("/stats")
def get_stats(user: User = Depends(get_current_user)):
    return {
        "videos_in_playlist": 38,
        "videos_watched_this_week": 14,
        "mcq_assignments": 12,
        "mcq_pending_today": 3,
        "course_pdfs": 7,
        "pdfs_downloaded": 2,
        "avg_mcq_score": 72,
        "avg_mcq_score_delta": 5,
    }


@router.get("/playlist")
def get_playlist(subject: str | None = None, user: User = Depends(get_current_user)):
    videos = [
        {"title": "Quadratic Equations — Full Chapter", "subject": "Mathematics", "source": "MathCity.org", "duration_min": 18, "note": "AI-added from today's session"},
        {"title": "Grammar Tenses — Active & Passive Voice", "subject": "English", "source": "Khan Academy", "duration_min": 12, "note": "AI-added"},
        {"title": "Geometry — Circles & Angles Full Revision", "subject": "Mathematics", "source": "MathCity.org", "duration_min": 24, "note": "AI-added"},
    ]
    if subject:
        videos = [v for v in videos if v["subject"].lower() == subject.lower()]
    return {"videos": videos}


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


@router.get("/materials/{material_id}/download")
def download_material(material_id: int, user: User = Depends(get_current_user)):
    material = next((m for m in _MATERIALS if m["id"] == material_id), None)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    # MOCK — Phase 6+ streams the real file / a signed URL.
    return {"detail": "Download would start here", "material": material}
