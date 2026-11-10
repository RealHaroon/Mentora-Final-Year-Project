from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.models import CareerProfile, InterviewQa, InterviewSession, User
from database.session import get_db
from rag_core.interview_rag import InterviewRAG
from rag_core.pipeline import RAGUnavailableError
from schemas.career import CareerGoal, InterviewAnswer
from services.auth_service import get_current_user

router = APIRouter(prefix="/interview", tags=["interview"])

# Matches the career_id values backend/scripts/seed_careers.py assigns to
# each title — kept here rather than a title-string lookup since the
# CareerGoal enum and the seeded rows are both fixed and small.
_CAREER_GOAL_IDS = {
    CareerGoal.data_scientist: 1,
    CareerGoal.ml_engineer: 2,
    CareerGoal.business_analyst: 3,
    CareerGoal.software_engineer: 4,
    CareerGoal.product_manager: 5,
}

_interview_rag = InterviewRAG()


def _history_from_qa_rows(rows: list[InterviewQa]) -> list[dict]:
    history = []
    for row in rows:
        history.append({"role": "assistant", "text": row.question_text})
        if row.student_answer:
            history.append({"role": "user", "text": row.student_answer})
    return history


@router.post("/start")
async def start_interview(career_goal: CareerGoal, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    career_id = _CAREER_GOAL_IDS[career_goal]
    career = db.get(CareerProfile, career_id)
    career_title = career.title if career else career_goal.value

    try:
        first_question = await _interview_rag.start(career_title)
    except RAGUnavailableError:
        # Raised before any DB write below — no partial session created.
        raise HTTPException(status_code=503, detail="Mock interview is temporarily unavailable — please try again shortly.")

    session = InterviewSession(user_id=user.user_id, career_id=career_id)
    db.add(session)
    db.flush()  # assigns session.interview_id before we reference it below
    db.add(InterviewQa(interview_id=session.interview_id, question_text=first_question))
    db.commit()

    return {"interview_id": session.interview_id, "career_title": career_title, "question": first_question}


@router.post("/{interview_id}/ask")
async def ask_interview(
    interview_id: int, payload: InterviewAnswer, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    session = db.get(InterviewSession, interview_id)
    if session is None or session.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Interview session not found")

    rows = db.query(InterviewQa).filter(InterviewQa.interview_id == interview_id).order_by(InterviewQa.qa_id).all()
    current = rows[-1]
    if current.student_answer is not None:
        raise HTTPException(status_code=400, detail="This turn was already answered")

    career = db.get(CareerProfile, session.career_id) if session.career_id else None
    career_title = career.title if career else "this role"

    history = _history_from_qa_rows(rows[:-1])
    # The model's reply intentionally combines feedback on the last answer
    # AND the next question into one piece of text (Phase 7 doc §8.4's own
    # design — it doesn't ask for structured output), so it's stored as
    # both this turn's feedback and next turn's question.
    try:
        reply = await _interview_rag.answer(career_title, history, payload.answer)
    except RAGUnavailableError:
        # Raised before any DB write below — the student's answer to this
        # turn isn't lost, they can just retry the same /ask call.
        raise HTTPException(status_code=503, detail="Mock interview is temporarily unavailable — please try again shortly.")

    current.student_answer = payload.answer
    current.ai_feedback = reply
    db.add(InterviewQa(interview_id=interview_id, question_text=reply))
    db.commit()

    return {"interview_id": interview_id, "answer": reply}
