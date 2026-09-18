from enum import Enum

from pydantic import BaseModel


class StudyMode(str, Enum):
    self_study = "self_study"
    tutor = "tutor"


class SubjectsUpdate(BaseModel):
    subjects: list[str]
    test_date: str | None = None
    study_mode: StudyMode | None = None


class McqSubmit(BaseModel):
    question_id: str
    answer: str
