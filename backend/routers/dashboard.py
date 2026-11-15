from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import CareerProfile, CareerRanking, ExamSession, TopicScore, User, WatchHistoryEntry, utcnow
from database.session import get_db
from ml_core.model_manager import ModelManager
from routers.exam import _build_week, _days_to_exam, _get_prefs
from services.auth_service import get_current_user
from services.notification_service import notify_once

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


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

    # 2026-11-15 — was hardcoded to 0 from a comment claiming watch-history
    # was still an in-memory, non-per-user list; that was fixed back on
    # 2026-11-12 (see routers/learning.py's own header comment) but this
    # call site was never updated to match.
    watch_count = db.query(WatchHistoryEntry).filter(WatchHistoryEntry.user_id == user.user_id).count()
    watch_count_this_week = (
        db.query(WatchHistoryEntry)
        .filter(WatchHistoryEntry.user_id == user.user_id, WatchHistoryEntry.watched_at >= week_ago)
        .count()
    )

    return {
        "exam_sessions": len(sessions),
        "avg_score": avg_score,
        "avg_score_delta": avg_score_delta,
        "videos_watched": watch_count,
        "videos_watched_this_week": watch_count_this_week,
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
def get_weekly_snapshot(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 2026-11-15 — this used to be 5 hardcoded days/topics regardless of the
    # account's real exam_goal, subjects, or deadline, while Exam Prep's own
    # timetable (same underlying _build_week) was fixed to be real and
    # adaptive in the same session — the two would have visibly disagreed on
    # the same real account. Reuses that exact, already-tested logic instead
    # of a second parallel (and inevitably drifting) implementation. Each
    # day's single topic/status is the first selected subject's session —
    # the same "spotlight" simplification /exam/today-topic and /exam/mcq
    # already use for a one-line summary; the full multi-subject breakdown
    # lives on /exam-prep itself.
    prefs = _get_prefs(db, user)
    week = _build_week(db, user, prefs["subjects"], _days_to_exam(prefs))
    return {
        "days": [
            {
                "day": row["day"][:3],
                "topic": row["sessions"][0]["topic"],
                "status": row["sessions"][0]["status"],
            }
            for row in week
            if row["sessions"]
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

    # 2026-11-16 — the model's raw float output (e.g. 84.6) was never
    # rounded, unlike every other percentage this app shows (get_stats'
    # avg_score already rounds). Never surfaced before because the seeded
    # historical scores happened to produce round predictions by
    # coincidence; exposed once submit_mcq started feeding real, variable
    # scores into this model's input window.
    result["predicted_next_score"] = round(result["predicted_next_score"])

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
