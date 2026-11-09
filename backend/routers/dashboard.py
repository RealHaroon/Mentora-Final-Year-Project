from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import ExamSession, Notification, TopicScore, User
from database.session import get_db
from ml_core.model_manager import ModelManager
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


@router.get("/at-risk-check")
async def check_at_risk(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Phase 6 — M3 (Trajectory Predictor). Needs the last SEQ_LEN=5 scored
    # exam sessions, oldest first, matching training's sequence order.
    stmt = (
        select(ExamSession.total_score)
        .where(ExamSession.user_id == user.user_id, ExamSession.total_score.is_not(None))
        .order_by(ExamSession.start_time.desc())
        .limit(5)
    )
    recent_scores = [s for (s,) in db.execute(stmt)][::-1]

    if len(recent_scores) < 5:
        return {
            "available": False,
            "detail": f"Need 5 scored exam sessions, have {len(recent_scores)}.",
        }

    manager: ModelManager = request.app.state.model_manager
    result = await manager.infer("trajectory_predictor", recent_scores)

    if result["trend"] == "declining":
        db.add(Notification(
            user_id=user.user_id,
            type="alert",
            message='Score trend flagged "at risk" — Trajectory Predictor',
        ))
        db.commit()

    return {"available": True, **result}


@router.get("/weak-topics")
def get_weak_topics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Phase 8 — found via integration testing: this was still Phase 2's mock,
    # never wired to the real TopicScore rows M1 (gap_classifier) writes in
    # /exam/mcq/submit. Low score = weak; the 38/44/60/62 mock thresholds are
    # kept as the "note" severity bands for continuity with the old UI copy.
    rows = (
        db.query(TopicScore)
        .filter(TopicScore.user_id == user.user_id)
        .order_by(TopicScore.score.asc())
        .all()
    )

    def note_for(score: float) -> str | None:
        if score < 40:
            return "Needs urgent review"
        if score < 60:
            return "Medium"
        if score < 70:
            return "Improving"
        return None

    return {
        "topics": [
            {"subject": r.subject, "topic": r.topic, "score": r.score, "note": note_for(r.score)}
            for r in rows
        ]
    }
