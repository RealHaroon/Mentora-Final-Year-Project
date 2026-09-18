from fastapi import APIRouter, Depends

from database.models import User
from schemas.exam import McqSubmit, SubjectsUpdate
from services.auth_service import get_current_user

router = APIRouter(prefix="/exam", tags=["exam"])

# MOCK — every endpoint below returns fixed data shaped like the real future
# response. Replace with real SIP/TOPIC_SCORES queries and Model Manager calls
# in Phase 6, one endpoint at a time. Field names match the frontend's
# hardcoded JSX exactly (see MENTORA_Frontend_Documentation.md §4.5).


@router.get("/timetable")
def get_timetable(user: User = Depends(get_current_user)):
    return {
        "days_to_exam": 47,
        "rows": [
            {"day": "Monday", "topic": "Algebra — Quadratic Equations", "subject": "Mathematics", "duration": "2 hrs", "status": "pending"},
            {"day": "Tuesday", "topic": "Reading Comprehension", "subject": "English", "duration": "1.5 hrs", "status": "done"},
            {"day": "Wednesday", "topic": "Grammar — Tenses & Voice", "subject": "English", "duration": "2 hrs", "status": "today"},
            {"day": "Thursday", "topic": "Geometry — Lines & Angles", "subject": "Mathematics", "duration": "2 hrs", "status": "missed"},
            {"day": "Friday", "topic": "Revision + MCQ Test", "subject": "Mixed", "duration": "1 hr", "status": "pending"},
        ],
    }


@router.get("/today-topic")
def get_today_topic(user: User = Depends(get_current_user)):
    return {
        "topic": "Quadratic Equations",
        "explainer": {
            "summary": "A quadratic equation has the form ax² + bx + c = 0. Key methods:",
            "points": ["Factorization method", "Quadratic formula", "Completing the square"],
        },
        "videos": [
            {"title": "Quadratic Equations — Full Chapter", "source": "MathCity.org", "duration_min": 18},
            {"title": "Quadratic Formula — Step by Step", "source": "Khan Academy", "duration_min": 12},
        ],
    }


@router.get("/mcq")
def get_mcq(topic: str | None = None, count: int = 5, user: User = Depends(get_current_user)):
    return {
        "total": count,
        "remaining": count - 1,
        "generated_by": "FLAN-T5",
        "question": {
            "question_id": "Q1001",
            "text": "Solve x² − 5x + 6 = 0. What are the roots?",
            "options": [
                {"value": "A", "text": "x = 2, 3"},
                {"value": "B", "text": "x = −2, 3"},
                {"value": "C", "text": "x = 1, 6"},
                {"value": "D", "text": "x = −1, −6"},
            ],
        },
    }


@router.post("/mcq/submit")
def submit_mcq(payload: McqSubmit, user: User = Depends(get_current_user)):
    # MOCK — Phase 6 runs M1 (Gap Classifier) here and updates TOPIC_SCORES.
    is_correct = payload.answer == "A"
    return {"question_id": payload.question_id, "correct": is_correct, "correct_answer": "A"}


@router.patch("/subjects")
def update_subjects(payload: SubjectsUpdate, user: User = Depends(get_current_user)):
    # MOCK — Phase 6 persists this to SIP.priority_queue / user prefs.
    return {"detail": "Preferences saved", **payload.model_dump()}
