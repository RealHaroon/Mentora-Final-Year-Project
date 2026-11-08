import random

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database.models import Question, TopicScore, User, utcnow
from database.session import get_db
from ml_core.model_manager import ModelManager
from schemas.exam import McqSubmit, SubjectsUpdate
from services.auth_service import get_current_user

router = APIRouter(prefix="/exam", tags=["exam"])

# Endpoints below not yet wired to a real model (unchanged from Phase 2 mock):
# /timetable and /today-topic depend on the RAG/content pipeline (Phase 7+),
# not the Model Manager. /subjects still has nowhere real to persist to.


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
async def get_mcq(
    request: Request, topic: str | None = None, count: int = 5,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    # Phase 6 — M2 (Question Generator), with a fallback to the real question
    # bank on failure. M2 is the model most likely to misfire (generative,
    # not a classifier, and already documented as weak — see
    # scripts/phase5/README.md) — a demo where one bad generation crashes the
    # exam page is worse than quietly serving a question from the bank.
    manager: ModelManager = request.app.state.model_manager
    topic = topic or "General Logical Reasoning"

    generated_by = "FLAN-T5"
    try:
        generated = await manager.infer("question_generator", topic)
        question = {
            "question_id": "generated",
            "text": generated["question"],
            "options": [{"value": k, "text": v} for k, v in generated["options"].items()],
        }
    except ValueError:
        fallback_query = db.query(Question).filter(Question.topic == topic)
        candidates = fallback_query.all() or db.query(Question).all()
        picked = random.choice(candidates)
        generated_by = "question_bank_fallback"
        question = {
            "question_id": str(picked.question_id),
            "text": picked.question_text,
            "options": [{"value": k, "text": v} for k, v in (picked.options or {}).items()],
        }

    return {"total": count, "remaining": count - 1, "generated_by": generated_by, "question": question}


@router.post("/mcq/submit")
async def submit_mcq(
    request: Request, payload: McqSubmit, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    # Phase 6 — M1 (Gap Classifier), run only on wrong answers to real
    # question-bank questions. question_id "generated" (M2's live-generated
    # questions, see get_mcq above) has no DB row and no labeled
    # correct_answer to grade against — can't determine correctness for it.
    if payload.question_id == "generated":
        return {"question_id": payload.question_id, "correct": None,
                "detail": "Generated questions aren't graded — no stored correct answer."}

    question = db.get(Question, int(payload.question_id))
    if question is None:
        return {"question_id": payload.question_id, "correct": None, "detail": "Unknown question_id."}

    # A large fraction of the seeded question bank (Phase 3/4's historic past
    # papers) has no labeled correct_answer at all — grading those would
    # always report "incorrect" regardless of the real answer, which is worse
    # than saying plainly that this one can't be graded.
    if not question.correct_answer:
        return {"question_id": payload.question_id, "correct": None,
                "correct_answer": None, "detail": "This question has no labeled correct answer."}

    is_correct = payload.answer == question.correct_answer
    weak_topics: list[str] = []

    if not is_correct:
        manager: ModelManager = request.app.state.model_manager
        weak_topics = await manager.infer("gap_classifier", question.question_text)
        for topic in weak_topics:
            # question.subject is used for every flagged topic, not a
            # per-topic lookup — M1's topic labels are already subject-specific
            # (e.g. "Algebra", "General Biology"), so this is a reasonable
            # approximation, not an exact join.
            row = (
                db.query(TopicScore)
                .filter(TopicScore.user_id == user.user_id, TopicScore.topic == topic)
                .one_or_none()
            )
            if row is None:
                row = TopicScore(user_id=user.user_id, subject=question.subject, topic=topic, score=50.0)
                db.add(row)
            row.score = max(0.0, row.score - 5.0)
            row.last_updated = utcnow()
        db.commit()

    return {
        "question_id": payload.question_id,
        "correct": is_correct,
        "correct_answer": question.correct_answer,
        "weak_topics_flagged": weak_topics,
    }


@router.patch("/subjects")
def update_subjects(payload: SubjectsUpdate, user: User = Depends(get_current_user)):
    # MOCK — Phase 6 persists this to SIP.priority_queue / user prefs.
    return {"detail": "Preferences saved", **payload.model_dump()}
