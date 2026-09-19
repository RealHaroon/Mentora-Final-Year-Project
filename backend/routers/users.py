from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.models import User
from database.session import get_db
from schemas.users import NotificationPrefs, UserOut, UserUpdate
from services.auth_service import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value.value if hasattr(value, "value") else value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=204)
def delete_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.delete(current_user)
    db.commit()


@router.get("/me/notification-prefs", response_model=NotificationPrefs)
def get_notification_prefs(current_user: User = Depends(get_current_user)):
    return NotificationPrefs(**(current_user.notification_prefs or {}))


@router.patch("/me/notification-prefs", response_model=NotificationPrefs)
def update_notification_prefs(
    payload: NotificationPrefs,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.notification_prefs = payload.model_dump()
    db.commit()
    return payload
