import json
import random
import re
from datetime import date, timedelta
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.models import ExamSession, Question, StudentIntelligenceProfile, TopicScore, TopicVideo, User, utcnow
from database.session import get_db
from ml_core.model_manager import ModelManager
from rag_core.exam_rag import ExamRAG
from rag_core.pipeline import RAGUnavailableError
from schemas.exam import McqSubmit, SubjectsUpdate
from services.auth_service import get_current_user
from services.notification_service import notify_once

router = APIRouter(prefix="/exam", tags=["exam"])

_exam_rag = ExamRAG()
# Separate instance, not the one above — found 2026-11-15 testing the new
# Groq-generated MCQ path live: the default 300-token limit (fine for
# topic-explainer prose) truncated mid-JSON on a question with LaTeX-style
# math formatting (option text like "$x=3$ or $x=-\frac{1}{2}$" alone can
# run past 300 tokens), making every one of these silently fail JSON
# parsing and fall back to the question bank — defeating the whole point
# of switching to Groq. Same model/API key, just enough headroom for a
# full MCQ's question + 4 options + correct_answer to never truncate.
_exam_mcq_rag = ExamRAG(max_tokens=700)

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Every subject actually present in the real question bank — see
# mentora_data/SOURCES.md. Biology/Chemistry/Physics/English/Logical
# Reasoning are sourced from 23 real Sindh MDCAT past papers (2000-2023);
# Mathematics is a generic college-readiness dataset used only because
# MDCAT itself has no math component — not verified against any specific
# Pakistani university's own syllabus.
_ALL_SUBJECTS = ["Mathematics", "Chemistry", "Physics", "Biology", "English", "Logical Reasoning"]

# 2026-11-14 — found via a user testing their own account: exam_goal was
# captured at registration and then never read anywhere, so every goal
# looked identical in Exam Prep regardless of what was picked at sign-up.
# First fix only split MDCAT vs. a generic "university" catch-all. The
# user then correctly pushed back: different universities and competitive
# exams have genuinely different real syllabi, and "keep the full 6 for
# every university" wasn't actually true for any of them. Researched each
# one directly (web search, 2026-11-14) rather than guessing — sources
# below. Every entry here only uses the 6 subjects this question bank
# actually has (Mathematics/Chemistry/Physics/Biology/English/Logical
# Reasoning — see mentora_data/SOURCES.md); where a real syllabus includes
# something this bank doesn't cover at all (Pakistan Studies, Islamiyat,
# General Knowledge, Computer Science, Sindhi/Urdu, essay-writing,
# candidate-chosen electives), that part is simply not representable here
# — noted per entry, not silently dropped.
_GOAL_SUBJECTS: dict[str, list[str]] = {
    # Sindh University's own SUTC sample paper (sutc.usindh.edu.pk,
    # Sample_TEST_Paper_OMR_SHEET_PET2025_SUTC.pdf): English 30%, General
    # Science 20% (physics/chemistry/computer — NOT biology), General
    # Knowledge 20% (Pakistan Studies/Islamiyat — not in this bank),
    # Simple Arithmetic 20% (-> Mathematics, the closest available
    # category), Intelligence 10% (word/shape problems -> Logical
    # Reasoning). No Biology.
    "sindh_university": ["Mathematics", "Chemistry", "Physics", "English", "Logical Reasoning"],
    # MUET's Pre-Engineering pattern (the dominant, consistently-cited one
    # across eduvision.edu.pk and gotest.com.pk's 2026 guides): 100 MCQs,
    # 25 each in English/Mathematics/Physics/Chemistry. MUET's own
    # Pre-Medical pattern (English/Biology/Physics) exists for medical-
    # track applicants but isn't the default for an engineering
    # university's own entry test.
    "mehran_university": ["Mathematics", "Chemistry", "Physics", "English"],
    # LUMHS (Liaquat University of Medical & Health Sciences, Hyderabad)
    # admits MBBS/BDS via the real provincial Sindh MDCAT itself (per
    # brecorder.com's coverage of LUMHS hosting MDCAT 2024-25) — same
    # subject set as "mdcat" below, not a separate syllabus.
    "lumhs": ["Biology", "Chemistry", "Physics", "English", "Logical Reasoning"],
    # University of Karachi's General Science group: English + General
    # Knowledge (not in this bank) + 3 of 5 optional science subjects
    # chosen by the student's own intermediate track (per 2026 sources on
    # pakera.pk/educationinkarachi.net). The 5 real optionals are Physics/
    # Chemistry/Biology/Mathematics/Computer — Computer isn't in this
    # bank; the other 4 are each genuinely part of some student's real
    # paper, so all 4 are offered here rather than arbitrarily picking 3.
    "karachi_university": ["Mathematics", "Chemistry", "Physics", "Biology", "English"],
    # Iqra University's own 2024-25 undergraduate prospectus (not a
    # third-party guide): English 40%, Mathematics 30%, Analytical 30%.
    # No compulsory science subject for general undergraduate admission —
    # Physics only appears conditionally for computing-program applicants
    # per one source, not as a default.
    "iqra_university": ["Mathematics", "English", "Logical Reasoning"],
    # Sindh Agriculture University, Tando Jam: the official 2024-25
    # admission policy (sau.edu.pk) confirms "four subjects" tested but
    # not their names in the available excerpt; third-party past-paper
    # sources agree the content is Mathematics-heavy for engineering
    # applicants and Biology-heavy for medical/agri-science applicants,
    # with a confirmed real Physics sample paper (mechanics, heat, light,
    # electricity, modern physics) and no Chemistry for Computer Science
    # applicants specifically. Kept inclusive of all 4 sciences + English
    # for the same "different track, different real paper" reason as
    # Karachi above, rather than guessing a single track.
    "tando_jam_university": ["Mathematics", "Chemistry", "Physics", "Biology", "English"],
    # PMDC's Uniform Curriculum MDCAT (pmdc.pk; identical across provinces
    # per premeth.com/beambeprep.com's 2026 guides, Sindh included):
    # Biology 45%, Chemistry 25%, Physics 20%, English 5%, Logical
    # Reasoning 5%. No Mathematics — confirmed, not assumed.
    "mdcat": ["Biology", "Chemistry", "Physics", "English", "Logical Reasoning"],
    # PMS/SPSC/PPSC's real compulsory papers (noacss.pk, grand-review.com
    # 2026 guides) are English Essay/Précis, Current Affairs & Pakistan
    # Affairs, General Science & Ability, and Islamic Studies — essay-
    # based, not MCQ — plus candidate-CHOSEN optional subjects (Economics,
    # Accounting, Computer Science, Political Science, Physics,
    # Statistics, etc.), not a fixed syllabus. None of this bank's MCQ
    # science subjects are actually compulsory for this exam; English and
    # Logical Reasoning are kept as the closest honest approximation of
    # the compulsory General Science & Ability / English components, not
    # a claim that this matches the real exam's essay format.
    "pms_spsc_ppsc": ["English", "Logical Reasoning"],
    # ISSB's own Initial Test (the academic screening stage before the
    # main board — conceptuallearningacademy.com, prepareissb.com)
    # confirmed subjects: English, Mathematics, Pakistan Studies,
    # Islamiyat (the latter two not in this bank), plus a separate
    # verbal/non-verbal Intelligence Test (-> Logical Reasoning).
    "issb": ["English", "Mathematics", "Logical Reasoning"],
    # Army/Navy/PAF's own Initial Tests (prepareissb.com, mcquniverse.pk)
    # share the same Academic + Intelligence (verbal/non-verbal) structure
    # as ISSB above, consistently citing English and Mathematics across
    # all three branches (Navy's academic test is explicitly English/
    # Physics/Mathematics; PAF's varies further by trade/branch beyond
    # what a single subject list can represent). Kept to the subjects
    # confirmed common across all three rather than guessing a specific
    # branch's full list.
    "army_navy_paf": ["English", "Mathematics", "Logical Reasoning"],
}


def _allowed_subjects(user: User) -> list[str]:
    return _GOAL_SUBJECTS.get(user.exam_goal, _ALL_SUBJECTS)


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
    allowed = _allowed_subjects(user)
    # Re-filter against the CURRENT exam_goal, not just whatever was saved
    # last — changing exam_goal in Settings (e.g. to MDCAT, which doesn't
    # test Math) shouldn't leave a stale, now-disallowed subject showing in
    # the timetable/MCQ until the student happens to touch the selector.
    valid_saved = [s for s in prefs.get("subjects", []) if s in allowed]
    if not valid_saved:
        valid_saved = allowed[:1]
    prefs["subjects"] = valid_saved
    return prefs


def _topic_for(db: Session, subject: str, seed: str) -> str:
    topics = [t for (t,) in db.query(Question.topic).filter(Question.subject == subject).distinct().all()]
    if not topics:
        return subject
    return random.Random(seed).choice(sorted(topics))


def _days_to_exam(prefs: dict) -> int:
    if prefs.get("test_date"):
        try:
            return max(0, (date.fromisoformat(prefs["test_date"]) - date.today()).days)
        except ValueError:
            pass  # malformed date from an old/manual request — fall back to the default below
    return 47  # no real deadline known — same arbitrary placeholder this already used


def _study_duration_for(days_to_exam: int) -> str:
    # 2026-11-15 — found via a user testing their own account: every day
    # showed "2 hrs" regardless of whether the real deadline (test_date)
    # was 1 day away or 15 — no actual urgency signal at all. Scales with
    # how close the real deadline is; the default 47-day placeholder
    # (no test_date set) lands in the most relaxed tier, which is correct
    # — there's no real known urgency to react to yet.
    if days_to_exam <= 2:
        return "4 hrs"
    if days_to_exam <= 7:
        return "3 hrs"
    if days_to_exam <= 14:
        return "2 hrs"
    return "1.5 hrs"


def _build_week(db: Session, user: User, subjects: list[str], days_to_exam: int) -> list[dict]:
    today = date.today()
    today_idx = today.weekday()  # 0=Mon .. 6=Sun
    # 2026-11-15 — found live, testing on an actual Sunday: anchoring to
    # "this calendar week's Monday" unconditionally meant that on a
    # weekend, every single row was a day that had ALREADY PASSED (this
    # week's Mon-Fri, all before today), so every row showed "Missed" and
    # a 3-days-out exam (genuinely next Wednesday) never truncated anything
    # because the real exam date fell outside this already-past window
    # entirely. On a weekend, jump forward to the UPCOMING Monday instead —
    # a rolling "your next study days" view, not a fixed dead calendar week.
    on_weekend = today_idx >= 5  # 5=Sat, 6=Sun
    monday = today + timedelta(days=7 - today_idx) if on_weekend else today - timedelta(days=today_idx)
    exam_date = today + timedelta(days=days_to_exam)
    duration = _study_duration_for(days_to_exam)

    rows = []
    for i, day in enumerate(_WEEKDAYS):
        # Don't plan study time on a day past the real exam date — found
        # alongside the duration issue above: a 1-day-away deadline still
        # showed a full Mon-Fri week, including days after the exam itself.
        # No real test_date set -> exam_date is 47 days out, always past
        # this week, so this never truncates in that case.
        if monday + timedelta(days=i) > exam_date:
            break
        subject = subjects[i % len(subjects)]
        topic = _topic_for(db, subject, seed=f"{user.user_id}-{today.isocalendar()[1]}-{day}")
        if on_weekend:
            # Every row in this window is the upcoming week — genuinely in
            # the future relative to today, never "today" or already past.
            status = "pending"
        elif i == today_idx:
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
        rows.append({"day": day, "topic": topic, "subject": subject, "duration": duration, "status": status})
    return rows


@router.get("/subjects")
def get_subjects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    prefs = _get_prefs(db, user)
    return {
        "subjects": prefs["subjects"],
        "allowed_subjects": _allowed_subjects(user),
        "test_date": prefs.get("test_date"),
        "study_mode": prefs.get("study_mode"),
    }


@router.patch("/subjects")
def update_subjects(payload: SubjectsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    allowed = _allowed_subjects(user)
    subjects = payload.subjects or allowed[:1]
    invalid = [s for s in subjects if s not in allowed]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"{', '.join(invalid)} not offered for this exam goal — choose from {', '.join(allowed)}",
        )
    sip = _get_or_create_sip(db, user)
    sip.priority_queue = {
        "subjects": subjects,
        "test_date": payload.test_date,
        "study_mode": payload.study_mode.value if payload.study_mode else None,
    }
    db.commit()
    return {"detail": "Preferences saved", **sip.priority_queue}


@router.get("/timetable")
def get_timetable(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    prefs = _get_prefs(db, user)
    days_to_exam = _days_to_exam(prefs)
    week = _build_week(db, user, prefs["subjects"], days_to_exam)

    # One of the 4 hardcoded "session_reminders" notifications every account
    # used to see regardless of their real schedule — there's no background
    # scheduler in this app, so this fires opportunistically whenever the
    # timetable is actually viewed, naming tomorrow's real topic rather than
    # a fixed "Grammar session — 7 PM". notify_once's dedup means it only
    # actually inserts once per distinct (topic, day) pending reminder.
    today_idx = date.today().weekday()
    if today_idx < len(_WEEKDAYS) - 1:
        tomorrow = week[today_idx + 1]
        if tomorrow["status"] == "pending":
            notify_once(db, user.user_id, "time", f"Tomorrow: {tomorrow['topic']} session ({tomorrow['subject']})")
            db.commit()

    return {"days_to_exam": days_to_exam, "rows": week}


def _youtube_search_url(title: str) -> str:
    return f"https://www.youtube.com/results?search_query={quote_plus(title)}"


def _resolve_video(db: Session, topic: str) -> dict:
    # 2026-11-15 — "suggested video" was always a generic YouTube search,
    # never a real specific video, and the Watch button had nothing to
    # open directly from Exam Prep itself (only after Add to Playlist).
    # Prefers a real curated TopicVideo row (added via Settings -> Manage
    # Topic Videos) when one exists for this topic; falls back to the
    # same genuine search link otherwise — never a fabricated/guessed
    # specific video this app can't verify still exists or is accurate.
    curated = db.get(TopicVideo, topic)
    if curated is not None:
        return {"title": curated.title, "source": "Curated", "duration_min": 0, "video_url": curated.video_url}
    title = f"{topic} — Overview"
    return {"title": title, "source": "YouTube search", "duration_min": 0, "video_url": _youtube_search_url(title)}


class TopicVideoIn(BaseModel):
    video_url: str
    title: str


@router.get("/topic-videos")
def list_topic_videos(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Every real topic in the question bank (not just the 20 a given
    # account's allowed subjects touch) so Settings can offer the full
    # list to curate from, merged with whatever's already been set.
    topics = sorted({t for (t,) in db.query(Question.topic).distinct().all()})
    curated = {row.topic: row for row in db.query(TopicVideo).all()}
    return {
        "topics": [
            {
                "topic": t,
                "video_url": curated[t].video_url if t in curated else None,
                "title": curated[t].title if t in curated else None,
            }
            for t in topics
        ]
    }


@router.put("/topic-videos/{topic}")
def set_topic_video(topic: str, payload: TopicVideoIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Shared across every student, not per-user — see TopicVideo's own
    # comment in database/models.py for why (no admin-role concept yet,
    # and a topic's best video doesn't vary by who's watching it).
    if not payload.video_url.strip().lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="video_url must be a real http(s) link")
    row = db.get(TopicVideo, topic)
    if row is None:
        row = TopicVideo(topic=topic, video_url=payload.video_url, title=payload.title)
        db.add(row)
    else:
        row.video_url = payload.video_url
        row.title = payload.title
    db.commit()
    return {"detail": "Saved", "topic": topic, "video_url": row.video_url, "title": row.title}


@router.delete("/topic-videos/{topic}")
def delete_topic_video(topic: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(TopicVideo, topic)
    if row is not None:
        db.delete(row)
        db.commit()
    return {"detail": "Removed"}


@router.get("/today-topic")
async def get_today_topic(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    prefs = _get_prefs(db, user)
    week = _build_week(db, user, prefs["subjects"], _days_to_exam(prefs))
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
        "videos": [_resolve_video(db, topic)],
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


async def _generate_mcq_via_llm(topic: str, difficulty: str = "medium") -> dict | None:
    # 2026-11-15 — M2 (FLAN-T5+LoRA) almost never produces valid JSON (0/32
    # real topics tested live, see the 2026-11-13 retry-removal commit) and
    # took 18-45s to fail even once, every single time, on the page's
    # default load. Default live generation now goes straight to Groq
    # instead — the same reasoning this app already applied to its RAG
    # pipeline (Groq over local Ollama, a disclosed, deliberate tradeoff):
    # M2 is real, trained, and evaluated (its real metrics are documented
    # in the thesis results), but demonstrably not fit for live use, so the
    # live default uses a reliable model instead. M2 itself stays fully
    # reachable on request — see get_mcq's source="m2" path below — so it
    # remains genuinely demonstrable, just not blocking the common path.
    prompt = (
        f"Generate one {difficulty}-difficulty multiple-choice exam question about {topic}, "
        "suitable for a university entry test. Respond with ONLY valid JSON, no markdown "
        "code fences, no extra commentary, in exactly this shape: "
        '{"question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, '
        '"correct_answer": "A"}'
    )
    try:
        response = await _exam_mcq_rag.agenerate(prompt)
    except RAGUnavailableError:
        return None
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or not ({"question", "options", "correct_answer"} <= parsed.keys()):
        return None
    options = parsed["options"]
    if not isinstance(options, dict) or not options or parsed["correct_answer"] not in options:
        return None
    return parsed


@router.get("/mcq")
async def get_mcq(
    request: Request, topic: str | None = None, count: int = 5, source: str = "llm",
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    # 2026-11-11: topic now defaults to today's real scheduled topic (same
    # one /exam/today-topic shows) instead of an unconditional fixed string
    # — found via a user testing their own account that selecting subjects
    # on /exam-prep had no visible effect anywhere, including here.
    manager: ModelManager = request.app.state.model_manager
    if topic is None:
        prefs = _get_prefs(db, user)
        week = _build_week(db, user, prefs["subjects"], _days_to_exam(prefs))
        today_row = next((r for r in week if r["status"] == "today"), week[0])
        topic = today_row["topic"]
        subject = today_row["subject"]
    else:
        subject_row = db.query(Question.subject).filter(Question.topic == topic).first()
        subject = subject_row[0] if subject_row else topic

    generated: dict | None = None
    generated_by: str | None = None

    if source == "m2":
        # Explicit, on-request path — lets the real trained model still be
        # demonstrated live without it blocking the default experience.
        # Phase 5/13's own docs already call this model "most likely to
        # misfire" — that's expected and disclosed, not hidden.
        try:
            generated = await manager.infer("question_generator", topic)
            generated_by = "question_generator_m2"
        except ValueError:
            generated = None
    else:
        generated = await _generate_mcq_via_llm(topic)
        generated_by = "groq_generated" if generated is not None else None

    if generated is not None:
        # Persisted as a real Question row — not a disposable/stateless
        # response — so submit_mcq's existing grading, weak-topic
        # flagging, and notification logic all just work for it via the
        # exact same path as every other question, instead of needing a
        # separate "generated questions aren't graded" special case.
        # correct_answer_source="ai_inferred" keeps it honestly
        # distinguishable from the original labeled dataset (see
        # Question.correct_answer_source's own comment).
        row = Question(
            subject=subject, topic=topic, subtopic=None, difficulty="medium",
            question_text=generated["question"], options=generated["options"],
            correct_answer=generated["correct_answer"], correct_answer_source="ai_inferred",
            source=generated_by,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        question = {
            "question_id": str(row.question_id),
            "text": row.question_text,
            "options": [{"value": k, "text": v} for k, v in (row.options or {}).items()],
        }
    else:
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


async def _determine_correct_answer(question: Question) -> str | None:
    # 2026-11-15 — 1777 of the 2155 seeded questions (every MDCAT-sourced
    # one — see mentora_data/SOURCES.md) have no correct_answer at all: the
    # original scanned answer-key pages didn't OCR reliably. Rather than
    # leave those permanently ungraded, ask Groq to determine the answer
    # from the question's own text — a plain reasoning call via agenerate(),
    # not retrieval (there's no knowledge-base lookup involved, just "solve
    # this question"). Result is persisted by the caller so this runs once
    # per question, not once per student.
    options = question.options or {}
    options_text = "\n".join(f"{k}. {v}" for k, v in options.items())
    prompt = (
        "You are grading a multiple-choice exam question. Determine the single "
        f"correct answer.\n\nQuestion: {question.question_text}\n\nOptions:\n{options_text}\n\n"
        "Respond with ONLY the letter of the correct option (for example: A). "
        "No explanation, no punctuation, nothing else."
    )
    try:
        response = await _exam_rag.agenerate(prompt)
    except RAGUnavailableError:
        return None
    cleaned = response.strip().upper()
    valid_keys = set(options.keys())
    # Looks for a whole-word match first (handles "The answer is B" even
    # though the prompt asks for just the letter) — stricter exact-match
    # fallback covers a bare "B" response with no word-boundary to match.
    for key in valid_keys:
        if re.search(rf"\b{re.escape(key)}\b", cleaned):
            return key
    return cleaned if cleaned in valid_keys else None


@router.post("/mcq/submit")
async def submit_mcq(
    request: Request, payload: McqSubmit, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    # Legacy safety net only — get_mcq now persists every generated question
    # (Groq or M2) as a real Question row with a real integer id before
    # ever returning it (2026-11-15), specifically so it grades through the
    # exact same path as every other question below, correct answer and
    # all. "generated" should never actually arrive here anymore; kept so
    # an old cached frontend response can't crash this on int(...).
    if payload.question_id == "generated":
        return {"question_id": payload.question_id, "correct": None, "graded_by": None,
                "detail": "This question wasn't saved properly — try Regenerate for a new one."}

    question = db.get(Question, int(payload.question_id))
    if question is None:
        return {"question_id": payload.question_id, "correct": None, "graded_by": None, "detail": "Unknown question_id."}

    # A large fraction of the seeded question bank (Phase 3/4's historic past
    # papers) has no labeled correct_answer at all — grading those would
    # always report "incorrect" regardless of the real answer, which is worse
    # than saying plainly that this one can't be graded. 2026-11-15: now
    # asks Groq to determine it instead of leaving it permanently ungraded
    # — see _determine_correct_answer(). Persisted so it's asked once per
    # question, not once per student; "ai_inferred" is reported back so the
    # frontend can disclose this wasn't from the original dataset.
    if not question.correct_answer:
        determined = await _determine_correct_answer(question)
        if determined is None:
            return {
                "question_id": payload.question_id, "correct": None, "correct_answer": None, "graded_by": None,
                "detail": "This question has no labeled correct answer, and AI grading couldn't "
                          "determine one right now — try submitting again shortly.",
            }
        question.correct_answer = determined
        question.correct_answer_source = "ai_inferred"
        db.commit()

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
        "graded_by": question.correct_answer_source,
        "weak_topics_flagged": weak_topics,
    }
