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
