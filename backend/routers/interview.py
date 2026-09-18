from fastapi import APIRouter, Depends, HTTPException

from database.models import User
from schemas.career import InterviewAnswer
from services.auth_service import get_current_user

router = APIRouter(prefix="/interview", tags=["interview"])

# MOCK — Phase 7 replaces this with the real RAG pipeline (ChromaDB + Ollama).
_SESSIONS: dict[int, dict] = {}
_NEXT_ID = 1
_FIRST_QUESTION = "Tell me about a project where you used data to make a decision."


@router.post("/start")
def start_interview(user: User = Depends(get_current_user)):
    global _NEXT_ID
    interview_id = _NEXT_ID
    _NEXT_ID += 1
    _SESSIONS[interview_id] = {"user_id": user.user_id, "turns": 0}
    return {"interview_id": interview_id, "question": _FIRST_QUESTION}


@router.post("/{interview_id}/ask")
def ask_interview(interview_id: int, payload: InterviewAnswer, user: User = Depends(get_current_user)):
    session = _SESSIONS.get(interview_id)
    if session is None or session["user_id"] != user.user_id:
        raise HTTPException(status_code=404, detail="Interview session not found")

    session["turns"] += 1
    # MOCK — Phase 7 grounds this reply in the interview_kb ChromaDB collection via Ollama.
    return {
        "interview_id": interview_id,
        "ai_feedback": "That's a great point — tell me more about the impact it had.",
        "next_question": "What would you do differently next time?",
    }
