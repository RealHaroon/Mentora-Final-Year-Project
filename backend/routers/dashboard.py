from fastapi import APIRouter, Depends

from database.models import User
from services.auth_service import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# MOCK — matches MENTORA_Phase2_Frontend_Backend_Wiring.md §1.1 exactly.


@router.get("/stats")
def get_stats(user: User = Depends(get_current_user)):
    return {
        "exam_sessions": 24,
        "avg_score": 72,
        "avg_score_delta": 5,
        "videos_watched": 38,
        "videos_watched_this_week": 14,
        "top_career_match": {"title": "Data Scientist", "fit_percent": 88},
    }


@router.get("/score-trend")
def get_score_trend(sessions: int = 10, user: User = Depends(get_current_user)):
    return {
        "points": [
            {"session": f"S{i + 1}", "score": v}
            for i, v in enumerate([55, 60, 68, 65, 75, 72, 82, 80, 90, 88][:sessions])
        ]
    }


@router.get("/weekly-snapshot")
def get_weekly_snapshot(user: User = Depends(get_current_user)):
    return {
        "days": [
            {"day": "Mon", "topic": "Algebra", "status": "done"},
            {"day": "Tue", "topic": "English", "status": "done"},
            {"day": "Wed", "topic": "Grammar", "status": "today"},
            {"day": "Thu", "topic": "Geometry", "status": "missed"},
            {"day": "Fri", "topic": "Revision", "status": "pending"},
        ]
    }


@router.get("/weak-topics")
def get_weak_topics(user: User = Depends(get_current_user)):
    return {
        "topics": [
            {"subject": "Algebra", "topic": "Quadratic Equations", "score": 38, "note": "Needs urgent review"},
            {"subject": "Grammar", "topic": "Tenses", "score": 44, "note": None},
            {"subject": "Geometry", "topic": "Circles", "score": 60, "note": "Medium"},
            {"subject": "English", "topic": "Reading Comprehension", "score": 62, "note": "Improving"},
        ]
    }
