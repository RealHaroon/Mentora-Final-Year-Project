from fastapi import APIRouter, Depends, UploadFile

from database.models import User
from schemas.career import CareerGoalUpdate
from services.auth_service import get_current_user

router = APIRouter(prefix="/career", tags=["career"])

# MOCK — see routers/exam.py header. These match the hardcoded values in the
# original /career page exactly (MENTORA_Frontend_Documentation.md §4.6).

_RANKINGS = [
    {"career_id": 1, "title": "Data Scientist", "match_score": 88, "key_skill_gap": "Deep Learning, TensorFlow"},
    {"career_id": 2, "title": "ML Engineer", "match_score": 78, "key_skill_gap": "TensorFlow, MLOps"},
    {"career_id": 3, "title": "Business Analyst", "match_score": 66, "key_skill_gap": "SQL, Tableau, Excel"},
    {"career_id": 4, "title": "Software Engineer", "match_score": 58, "key_skill_gap": "System Design, APIs"},
    {"career_id": 5, "title": "Product Manager", "match_score": 42, "key_skill_gap": "Leadership, Strategy, UX"},
]

_ROADMAP = [
    {"month_number": "1-2", "milestone_title": "Python & Stats", "description": "Fundamentals", "status": "completed"},
    {"month_number": 3, "milestone_title": "ML Algorithms", "description": "Scikit-learn", "status": "completed"},
    {"month_number": 4, "milestone_title": "Deep Learning", "description": "TensorFlow", "status": "in_progress"},
    {"month_number": 5, "milestone_title": "Projects & RAG", "description": "Portfolio", "status": "pending"},
    {"month_number": 6, "milestone_title": "Mock Interviews", "description": "Job Applications", "status": "pending"},
]


@router.post("/cv-upload")
async def upload_cv(cv_file: UploadFile, user: User = Depends(get_current_user)):
    # MOCK — Phase 6 runs M5 (CV/Transcript NER Extractor) on the real file
    # contents. For now just confirm the upload arrived and return fixed data.
    await cv_file.read()
    return {
        "filename": cv_file.filename,
        "gpa": 3.6,
        "skills": ["Python", "Data Analysis", "SQL"],
        "certifications": ["AWS Cloud Foundations"],
        "projects": ["Sentiment Analyzer"],
    }


@router.post("/goal")
def set_career_goal(payload: CareerGoalUpdate, user: User = Depends(get_current_user)):
    return {"detail": "Career goal saved", "career_goal": payload.career_goal.value}


@router.get("/ai-suggest")
def ai_suggest_career(user: User = Depends(get_current_user)):
    # MOCK — Phase 6 runs M4 (Sentence-Transformers career matcher).
    return {"career_goal": "data_scientist", "title": "Data Scientist", "match_score": 88}


@router.get("/rankings")
def get_rankings(user: User = Depends(get_current_user)):
    return {"model": "all-mpnet-base-v2", "rankings": _RANKINGS}


@router.get("/roadmap")
def get_roadmap(career_id: int = 1, user: User = Depends(get_current_user)):
    title = next((r["title"] for r in _RANKINGS if r["career_id"] == career_id), "Data Scientist")
    return {"career_id": career_id, "title": title, "steps": _ROADMAP}
