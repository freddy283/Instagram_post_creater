from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.auth import get_current_user, get_password_hash
from app.models import User

router = APIRouter(prefix="/api/user", tags=["user"])


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    timezone: str
    ig_handle: Optional[str] = None
    video_theme: Optional[str] = None
    notify_email: bool = True
    auto_post_ig: bool = False

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    ig_handle: Optional[str] = None
    video_theme: Optional[str] = None
    notify_email: Optional[bool] = None
    auto_post_ig: Optional[bool] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, val)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me")
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.delete(current_user)
    db.commit()
    return {"ok": True}
