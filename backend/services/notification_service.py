from sqlalchemy.orm import Session

from database.models import Notification


def notify_once(db: Session, user_id: int, type: str, message: str) -> None:
    """Insert a notification unless an identical unread one already exists.

    Without this, a write site that re-evaluates on every request (e.g. the
    at-risk check, which already ran on every /dashboard/at-risk-check call
    before this existed) would insert a duplicate row every single time its
    condition stays true, rather than once per real change. Caller commits —
    this only adds to the session.
    """
    existing = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.type == type,
            Notification.message == message,
            Notification.is_read.is_(False),
        )
        .first()
    )
    if existing is None:
        db.add(Notification(user_id=user_id, type=type, message=message))
