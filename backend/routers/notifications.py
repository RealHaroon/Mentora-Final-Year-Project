from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.models import Notification, User
from database.session import get_db
from services.auth_service import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Maps each notification "type" to the NotificationPrefs field that gates it,
# so toggling a preference off actually hides that category rather than just
# recording a setting nobody reads.
_TYPE_TO_PREF = {
    "alert": "weak_topic_alerts",
    "ok": "content_updates",
    "time": "session_reminders",
    "match": "career_match_updates",
}


@router.get("")
def get_notifications(unread: bool | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Was 4 hardcoded items identical for every account regardless of what
    # had actually happened to them — found 2026-11-13 while checking why
    # /dashboard/at-risk-check's own real Notification writes (M3, the
    # trajectory predictor) never showed up anywhere: this endpoint never
    # read the table at all. Real write sites now exist for all 4 types —
    # see dashboard.py (alert), career.py (match), learning.py (ok), and
    # exam.py's timetable (time).
    query = db.query(Notification).filter(Notification.user_id == user.user_id)
    if unread:
        query = query.filter(Notification.is_read.is_(False))
    rows = query.order_by(Notification.created_at.desc()).all()

    prefs = user.notification_prefs or {}
    items = [
        {"type": r.type, "message": r.message, "is_read": r.is_read}
        for r in rows
        if prefs.get(_TYPE_TO_PREF.get(r.type, ""), True)
    ]
    return {"items": items}
