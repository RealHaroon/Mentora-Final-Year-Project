from datetime import datetime, UTC

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.session import Base


def utcnow() -> datetime:
    # Naive UTC on purpose: SQLite drops tzinfo on round-trip, so mixing
    # naive/aware datetimes later (e.g. comparing reset_code_expires_at)
    # would raise. Keep every stored timestamp naive-UTC consistently.
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    university: Mapped[str] = mapped_column(String(255))
    exam_goal: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    # Not in the original ERD — needed to actually implement the documented
    # forgot-password / reset-password flow (Phase 1 milestone).
    reset_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    reset_code_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Also not in the original ERD — per-user notification toggle settings.
    notification_prefs: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    sip: Mapped["StudentIntelligenceProfile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class StudentIntelligenceProfile(Base):
    __tablename__ = "student_intelligence_profile"

    sip_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), unique=True)
    skill_vector: Mapped[list | None] = mapped_column(JSON, nullable=True)  # 768-d
    career_rankings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    priority_queue: Mapped[list | None] = mapped_column(JSON, nullable=True)
    roadmap: Mapped[list | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="sip")


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    session_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    exam_type: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(String(100))
    start_time: Mapped[datetime] = mapped_column(default=utcnow)
    end_time: Mapped[datetime | None] = mapped_column(nullable=True)
    total_score: Mapped[float | None] = mapped_column(nullable=True)


class Question(Base):
    __tablename__ = "questions"

    question_id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(100))
    topic: Mapped[str] = mapped_column(String(150))
    subtopic: Mapped[str | None] = mapped_column(String(150), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20))
    question_text: Mapped[str] = mapped_column(Text)
    options: Mapped[dict] = mapped_column(JSON)
    correct_answer: Mapped[str] = mapped_column(String(10))
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)


class SessionAnswer(Base):
    __tablename__ = "session_answers"

    answer_id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("exam_sessions.session_id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.question_id"))
    student_answer: Mapped[str] = mapped_column(String(10))
    is_correct: Mapped[bool] = mapped_column(default=False)
    time_taken_sec: Mapped[int | None] = mapped_column(nullable=True)


class TopicScore(Base):
    __tablename__ = "topic_scores"

    topic_score_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    subject: Mapped[str] = mapped_column(String(100))
    topic: Mapped[str] = mapped_column(String(150))
    score: Mapped[float] = mapped_column()
    last_updated: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class CareerProfile(Base):
    __tablename__ = "career_profiles"

    career_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    onet_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)


class CareerRanking(Base):
    __tablename__ = "career_rankings"

    ranking_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    career_id: Mapped[int] = mapped_column(ForeignKey("career_profiles.career_id"))
    match_score: Mapped[float] = mapped_column()
    key_skill_gap: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ranked_at: Mapped[datetime] = mapped_column(default=utcnow)


class Roadmap(Base):
    __tablename__ = "roadmaps"

    roadmap_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    career_id: Mapped[int] = mapped_column(ForeignKey("career_profiles.career_id"))
    # String, not int — the first milestone spans two months ("1-2"), same as
    # the roadmap display always has. Table had zero rows when this was
    # written (2026-11-13), so no migration/data-loss concern changing it.
    month_number: Mapped[str] = mapped_column(String(10))
    milestone_title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # RAG-grounded, generated once at creation time (not on every view) and
    # persisted alongside the rest of the milestone — see routers/career.py.
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)


class CvUpload(Base):
    __tablename__ = "cv_uploads"

    cv_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    file_path: Mapped[str] = mapped_column(String(500))
    uploaded_at: Mapped[datetime] = mapped_column(default=utcnow)
    extracted_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    gpa: Mapped[float | None] = mapped_column(nullable=True)
    certifications: Mapped[list | None] = mapped_column(JSON, nullable=True)
    projects: Mapped[list | None] = mapped_column(JSON, nullable=True)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    interview_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    career_id: Mapped[int | None] = mapped_column(ForeignKey("career_profiles.career_id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)


class InterviewQa(Base):
    __tablename__ = "interview_qa"

    qa_id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.interview_id"))
    question_text: Mapped[str] = mapped_column(Text)
    student_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    message: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20))
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


# Not in the original ERD — added 2026-11-12 to fix the Learning Portal's
# playlist/materials/watch-history, which were plain module-level Python
# lists shared across every user of the process (found 2026-11-10 while
# writing e2e tests against it). See routers/learning.py.
class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    item_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(150))
    duration_min: Mapped[int] = mapped_column()
    note: Mapped[str] = mapped_column(String(255))
    video_url: Mapped[str] = mapped_column(String(500))
    added_at: Mapped[datetime] = mapped_column(default=utcnow)


class WatchHistoryEntry(Base):
    __tablename__ = "watch_history"

    watch_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(100))
    watched_at: Mapped[datetime] = mapped_column(default=utcnow)


class Material(Base):
    __tablename__ = "materials"

    material_id: Mapped[int] = mapped_column(primary_key=True)
    # NULL = a shared catalog resource visible to every student (e.g. board
    # past papers); set = a private self-upload visible only to its owner.
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    size_label: Mapped[str] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(150))
    uploaded_at: Mapped[datetime] = mapped_column(default=utcnow)
