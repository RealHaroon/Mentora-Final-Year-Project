from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import CareerProfile, CareerRanking, ExamSession, TopicScore, User, utcnow
from database.session import get_db
from ml_core.model_manager import ModelManager
from services.auth_service import get_current_user
from services.notification_service import notify_once

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# weekly-snapshot and the frontend's whole exam/timetable system are still
# MOCK (matches MENTORA_Phase2_Frontend_Backend_Wiring.md §1.1) — there's no
# real "study schedule" concept in the schema yet, and selecting subjects on
# /exam-prep doesn't change it. Found 2026-11-11 via a user testing their own
# fresh account and seeing fixed numbers regardless of real activity.


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sessions = db.query(ExamSession).filter(ExamSession.user_id == user.user_id).all()
    scored = [s.total_score for s in sessions if s.total_score is not None]
    avg_score = round(sum(scored) / len(scored)) if scored else 0

    now = utcnow()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    this_week = [s.total_score for s in sessions if s.total_score is not None and s.start_time >= week_ago]
    last_week = [
        s.total_score for s in sessions
        if s.total_score is not None and two_weeks_ago <= s.start_time < week_ago
    ]
    avg_score_delta = (
        round(sum(this_week) / len(this_week) - sum(last_week) / len(last_week))
        if this_week and last_week
        else 0
    )

    top_ranking = (
        db.query(CareerRanking)
        .filter(CareerRanking.user_id == user.user_id)
        .order_by(CareerRanking.match_score.desc())
        .first()
    )
    top_career_match = None
    if top_ranking is not None:
        career = db.get(CareerProfile, top_ranking.career_id)
        top_career_match = {
            "title": career.title if career else "Unknown",
            "fit_percent": round(top_ranking.match_score),
        }

    return {
        "exam_sessions": len(sessions),
        "avg_score": avg_score,
        "avg_score_delta": avg_score_delta,
        # Still mock — videos_in_playlist/watch-history (backend/routers/
        # learning.py) are in-memory and not scoped per user at all, so
        # there's no real per-user count to report yet. See that file's
        # header comment and docs/phase10/viva_question_bank.md.
        "videos_watched": 0,
        "videos_watched_this_week": 0,
        "top_career_match": top_career_match,
    }


@router.get("/score-trend")
def get_score_trend(sessions: int = 10, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(ExamSession)
        .filter(ExamSession.user_id == user.user_id, ExamSession.total_score.is_not(None))
        .order_by(ExamSession.start_time.desc())
        .limit(sessions)
        .all()
    )[::-1]
    return {"points": [{"session": f"S{i + 1}", "score": r.total_score} for i, r in enumerate(rows)]}


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
        # notify_once, not a plain add() — this check re-runs on every
        # dashboard visit, and without dedup a still-declining trend would
        # insert a fresh duplicate row every single time rather than once.
        notify_once(db, user.user_id, "alert", 'Score trend flagged "at risk" — Trajectory Predictor')
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
