import io
from pathlib import Path

import pdfplumber
from docx import Document
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import CareerProfile, CareerRanking, CvUpload, User
from database.session import get_db
from ml_core.model_manager import ModelManager
from schemas.career import CareerGoalUpdate
from services.auth_service import get_current_user

router = APIRouter(prefix="/career", tags=["career"])

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads" / "cv"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_ROADMAP = [
    {"month_number": "1-2", "milestone_title": "Python & Stats", "description": "Fundamentals", "status": "completed"},
    {"month_number": 3, "milestone_title": "ML Algorithms", "description": "Scikit-learn", "status": "completed"},
    {"month_number": 4, "milestone_title": "Deep Learning", "description": "TensorFlow", "status": "in_progress"},
    {"month_number": 5, "milestone_title": "Projects & RAG", "description": "Portfolio", "status": "pending"},
    {"month_number": 6, "milestone_title": "Mock Interviews", "description": "Job Applications", "status": "pending"},
]


def _extract_text(filename: str, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        text_parts = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n\n".join(text_parts)
    if suffix == ".docx":
        doc = Document(io.BytesIO(raw))
        return "\n\n".join(p.text for p in doc.paragraphs)
    # .txt and anything else — best-effort decode
    return raw.decode("utf-8", errors="ignore")


def _skill_text_for_user(db: Session, user_id: int) -> str | None:
    # Built from the most recent CV upload's extracted fields — the real
    # analogue of the doc's "sip_service.get_skill_text", which doesn't exist
    # in this codebase; CvUpload is the actual source of truth we have.
    cv = db.execute(
        select(CvUpload).where(CvUpload.user_id == user_id).order_by(CvUpload.uploaded_at.desc()).limit(1)
    ).scalar_one_or_none()
    if cv is None or not cv.extracted_skills:
        return None
    parts = [", ".join(cv.extracted_skills)]
    if cv.certifications:
        parts.append(", ".join(cv.certifications))
    return ". ".join(parts)


@router.post("/cv-upload")
async def upload_cv(
    request: Request, cv_file: UploadFile, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    # Phase 6 — M5 (CV NER Extractor).
    raw = await cv_file.read()
    text = _extract_text(cv_file.filename, raw)
    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract any text from this file")

    file_path = UPLOAD_DIR / f"{user.user_id}_{cv_file.filename}"
    file_path.write_bytes(raw)

    manager: ModelManager = request.app.state.model_manager
    extracted = await manager.infer("cv_ner", text)

    gpa_raw = extracted.get("gpa")
    try:
        gpa = float(gpa_raw) if gpa_raw else None
    except ValueError:
        gpa = None  # model extracted something that isn't a plain number — don't fabricate one

    db.add(CvUpload(
        user_id=user.user_id,
        file_path=str(file_path),
        extracted_skills=extracted["skills"],
        gpa=gpa,
        certifications=extracted["certifications"],
        projects=extracted.get("degrees", []),  # M5's actual tag set has no PROJECT label — see cv_ner.py
    ))
    db.commit()

    return {
        "filename": cv_file.filename,
        "gpa": gpa,
        "skills": extracted["skills"],
        "certifications": extracted["certifications"],
        "degrees": extracted.get("degrees", []),
    }


@router.post("/goal")
def set_career_goal(payload: CareerGoalUpdate, user: User = Depends(get_current_user)):
    return {"detail": "Career goal saved", "career_goal": payload.career_goal.value}


async def _compute_rankings(request: Request, db: Session, user: User, top_k: int) -> list[dict]:
    skill_text = _skill_text_for_user(db, user.user_id)
    if skill_text is None:
        raise HTTPException(status_code=422, detail="Upload a CV first — no extracted skills to match against")

    manager: ModelManager = request.app.state.model_manager
    rankings = await manager.infer("career_matcher", skill_text, top_k=top_k)

    db.query(CareerRanking).filter(CareerRanking.user_id == user.user_id).delete()
    for r in rankings:
        db.add(CareerRanking(user_id=user.user_id, career_id=r["career_id"], match_score=r["match_score"]))
    db.commit()
    return rankings


@router.get("/ai-suggest")
async def ai_suggest_career(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rankings = await _compute_rankings(request, db, user, top_k=1)
    top = rankings[0]
    return {"career_id": top["career_id"], "title": top["career_title"], "match_score": top["match_score"]}


@router.get("/rankings")
async def get_rankings(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rankings = await _compute_rankings(request, db, user, top_k=5)
    catalogue = {c.career_id: c for c in db.query(CareerProfile).all()}
    return {
        "model": "all-mpnet-base-v2",
        "rankings": [
            {
                "career_id": r["career_id"],
                "title": r["career_title"],
                "match_score": r["match_score"],
                "key_skill_gap": ", ".join((catalogue[r["career_id"]].required_skills or [])[:2]),
            }
            for r in rankings
        ],
    }


@router.get("/roadmap")
def get_roadmap(career_id: int = 1, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    career = db.get(CareerProfile, career_id)
    title = career.title if career else "Data Scientist"
    return {"career_id": career_id, "title": title, "steps": _ROADMAP}
