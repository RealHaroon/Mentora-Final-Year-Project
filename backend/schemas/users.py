from datetime import datetime

from pydantic import BaseModel

from schemas.auth import ExamGoal


class UserOut(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: str
    university: str
    exam_goal: ExamGoal
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    university: str | None = None
    exam_goal: ExamGoal | None = None


class NotificationPrefs(BaseModel):
    # Matches the 4 notification "type" values already shown on /dashboard
    # (alert / ok / time / match) — see routers/notifications.py.
    weak_topic_alerts: bool = True
    content_updates: bool = True
    session_reminders: bool = True
    career_match_updates: bool = True
