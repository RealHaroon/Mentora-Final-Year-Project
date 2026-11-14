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
    ux_ui_designer = "ux_ui_designer"
    devops_engineer = "devops_engineer"
    cybersecurity_analyst = "cybersecurity_analyst"
    digital_marketing_specialist = "digital_marketing_specialist"
    financial_analyst = "financial_analyst"


class CareerGoalUpdate(BaseModel):
    career_goal: CareerGoal


class InterviewAnswer(BaseModel):
    answer: str
