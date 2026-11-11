import random
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database.models import ExamSession, Question, StudentIntelligenceProfile, TopicScore, User, utcnow
from database.session import get_db
from ml_core.model_manager import ModelManager
from rag_core.exam_rag import ExamRAG
from rag_core.pipeline import RAGUnavailableError
from schemas.exam import McqSubmit, SubjectsUpdate
from services.auth_service import get_current_user

router = APIRouter(prefix="/exam", tags=["exam"])

_exam_rag = ExamRAG()

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
_DEFAULT_SUBJECTS = ["Mathematics"]


def _get_or_create_sip(db: Session, user: User) -> StudentIntelligenceProfile:
    sip = db.query(StudentIntelligenceProfile).filter(StudentIntelligenceProfile.user_id == user.user_id).first()
    if sip is None:
        sip = StudentIntelligenceProfile(user_id=user.user_id)
        db.add(sip)
        db.commit()
        db.refresh(sip)
    return sip


def _get_prefs(db: Session, user: User) -> dict:
    # priority_queue is a generic JSON field (ERD) — repurposed here to hold
    # the whole small prefs blob (subjects/test_date/study_mode) rather than
    # adding three new columns for what's still a small, evolving feature.
    sip = _get_or_create_sip(db, user)
    prefs = sip.priority_queue or {}
    if not prefs.get("subjects"):
        prefs["subjects"] = _DEFAULT_SUBJECTS
    return prefs


def _topic_for(db: Session, subject: str, seed: str) -> str:
    topics = [t for (t,) in db.query(Question.topic).filter(Question.subject == subject).distinct().all()]
    if not topics:
        return subject
    return random.Random(seed).choice(sorted(topics))


def _build_week(db: Session, user: User, subjects: list[str]) -> list[dict]:
    today_idx = date.today().weekday()  # 0=Mon .. 6=Sun
    rows = []
    for i, day in enumerate(_WEEKDAYS):
        subject = subjects[i % len(subjects)]
        topic = _topic_for(db, subject, seed=f"{user.user_id}-{date.today().isocalendar()[1]}-{day}")
        if i == today_idx:
            status = "today"
        elif i < today_idx:
            has_session = (
                db.query(ExamSession)
                .filter(ExamSession.user_id == user.user_id, ExamSession.subject == subject)
                .first()
                is not None
            )
            status = "done" if has_session else "missed"
        else:
            status = "pending"
        rows.append({"day": day, "topic": topic, "subject": subject, "duration": "2 hrs", "status": status})
    return rows


@router.get("/subjects")
def get_subjects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    prefs = _get_prefs(db, user)
    return {
        "subjects": prefs["subjects"],
        "test_date": prefs.get("test_date"),
        "study_mode": prefs.get("study_mode"),
    }


@router.patch("/subjects")
def update_subjects(payload: SubjectsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sip = _get_or_create_sip(db, user)
    sip.priority_queue = {
        "subjects": payload.subjects or _DEFAULT_SUBJECTS,
        "test_date": payload.test_date,
        "study_mode": payload.study_mode.value if payload.study_mode else None,
    }
    db.commit()
    return {"detail": "Preferences saved", **sip.priority_queue}


@router.get("/timetable")
def get_timetable(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    prefs = _get_prefs(db, user)
    days_to_exam = 47
    if prefs.get("test_date"):
        try:
            days_to_exam = max(0, (date.fromisoformat(prefs["test_date"]) - date.today()).days)
        except ValueError:
            pass  # malformed date from an old/manual request — fall back to the default above
    return {"days_to_exam": days_to_exam, "rows": _build_week(db, user, prefs["subjects"])}


@router.get("/today-topic")
async def get_today_topic(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    prefs = _get_prefs(db, user)
    week = _build_week(db, user, prefs["subjects"])
    today_row = next((r for r in week if r["status"] == "today"), week[0])  # weekend fallback: Monday's plan
    topic = today_row["topic"]

    try:
        explainer_text = await _exam_rag.answer(f"Explain {topic} for {today_row['subject']} exam preparation")
    except RAGUnavailableError:
        explainer_text = (
            f"AI explainer is temporarily unavailable — try the 'Ask AI about this topic' box below once it's back."
        )

    return {
        "topic": topic,
        "explainer": {"summary": explainer_text, "points": []},
        # No real video catalog exists yet — a genuine YouTube search for the
        # real topic, not a fabricated specific video/channel/duration.
        "videos": [
            {"title": f"{topic} — Overview", "source": "YouTube search", "duration_min": 0},
        ],
    }


@router.get("/topic-explainer")
async def topic_explainer(query: str, user: User = Depends(get_current_user)):
    # Phase 7 — ExamRAG (grounded in rag_pipelines/exam_rag/content/, Groq
    # for generation). Separate from /today-topic above, which is a fixed
    # structured panel (summary + points + videos), not a free-text Q&A.
    try:
        answer = await _exam_rag.answer(query)
    except RAGUnavailableError:
        # Phase 9 §5 — degrade this one feature, don't 500 the whole app.
        # Real risk now that generation is Groq (cloud), not local Ollama:
        # this endpoint needs internet, unlike everything else in the app.
        raise HTTPException(status_code=503, detail="Topic explainer is temporarily unavailable — please try again shortly.")
    return {"answer": answer}


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
    #
    # 2026-11-11: topic now defaults to today's real scheduled topic (same
    # one /exam/today-topic shows) instead of an unconditional fixed string
    # — found via a user testing their own account that selecting subjects
    # on /exam-prep had no visible effect anywhere, including here.
    manager: ModelManager = request.app.state.model_manager
    if topic is None:
        prefs = _get_prefs(db, user)
        week = _build_week(db, user, prefs["subjects"])
        today_row = next((r for r in week if r["status"] == "today"), week[0])
        topic = today_row["topic"]

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
        # 2026-11-11 — found live: M1 can return the same topic string twice
        # in one call, and `.one_or_none()` below then crashes with
        # MultipleResultsFound the SECOND time that topic is ever flagged
        # (the first flag's two inserts both landed, since this loop had no
        # dedup and nothing enforces uniqueness on (user_id, topic) in the
        # schema). Deduping here stops new duplicates; `.first()` below
        # instead of `.one_or_none()` makes this resilient to the ones
        # that already exist rather than crashing on them forever.
        for topic in dict.fromkeys(weak_topics):
            # question.subject is used for every flagged topic, not a
            # per-topic lookup — M1's topic labels are already subject-specific
            # (e.g. "Algebra", "General Biology"), so this is a reasonable
            # approximation, not an exact join.
            row = (
                db.query(TopicScore)
                .filter(TopicScore.user_id == user.user_id, TopicScore.topic == topic)
                .order_by(TopicScore.topic_score_id)
                .first()
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
