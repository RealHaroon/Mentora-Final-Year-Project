from enum import Enum
from typing import Literal

from pydantic import BaseModel


class RoadmapStatusUpdate(BaseModel):
    status: Literal["completed", "in_progress", "pending"]


class CareerGoal(str, Enum):
    data_scientist = "data_scientist"
    ml_engineer = "ml_engineer"
    business_analyst = "business_analyst"
    software_engineer = "software_engineer"
    product_manager = "product_manager"


class CareerGoalUpdate(BaseModel):
    career_goal: CareerGoal


class InterviewAnswer(BaseModel):
    answer: str
