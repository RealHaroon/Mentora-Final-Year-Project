from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.models import StudentIntelligenceProfile, User, utcnow
from database.session import get_db
from schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from services.auth_service import (
    create_access_token,
    generate_reset_code,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        university=payload.university,
        exam_goal=payload.exam_goal.value,
    )
    db.add(user)
    db.flush()  # assigns user.user_id before we reference it below

    db.add(StudentIntelligenceProfile(user_id=user.user_id))
    db.commit()

    return TokenResponse(access_token=create_access_token(user.user_id))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return TokenResponse(access_token=create_access_token(user.user_id))


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    # Always return the same response whether or not the email exists,
    # so this endpoint can't be used to enumerate registered accounts.
    if user is not None:
        user.reset_code = generate_reset_code()
        user.reset_code_expires_at = utcnow() + timedelta(minutes=30)
        db.commit()
        # No email service wired up yet (out of scope for this phase) — log it
        # so the reset flow is testable end-to-end locally.
        print(f"[dev] password reset code for {user.email}: {user.reset_code}")

    return {"detail": "If that email is registered, a reset code has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    user = db.query(User).filter(User.reset_code == payload.reset_code).first()
    if (
        user is None
        or user.reset_code_expires_at is None
        or user.reset_code_expires_at < utcnow()
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    user.password_hash = hash_password(payload.new_password)
    user.reset_code = None
    user.reset_code_expires_at = None
    db.commit()

    return {"detail": "Password reset successfully"}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()

    return {"detail": "Password changed successfully"}
