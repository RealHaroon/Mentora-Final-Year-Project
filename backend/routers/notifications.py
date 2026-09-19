from fastapi import APIRouter, Depends

from database.models import User
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
def get_notifications(unread: bool | None = None, user: User = Depends(get_current_user)):
    # MOCK — matches the 4 hardcoded notif-items on /dashboard.
    items = [
        {"type": "alert", "message": 'Score trend flagged "at risk" in Algebra — Trajectory Predictor', "is_read": False},
        {"type": "ok", "message": "New topic playlist ready for Algebra", "is_read": False},
        {"type": "time", "message": "Tomorrow: Grammar session — 7 PM", "is_read": False},
        {"type": "match", "message": "Career match updated: +2 points", "is_read": True},
    ]
    prefs = user.notification_prefs or {}
    items = [n for n in items if prefs.get(_TYPE_TO_PREF[n["type"]], True)]
    if unread:
        items = [n for n in items if not n["is_read"]]
    return {"items": items}
