from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import date, datetime
from app.models import GenderEnum, PostStatus


# ─── Auth ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    date_of_birth: Optional[date] = None
    gender: Optional[GenderEnum] = None
    timezone: str = "UTC"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── User ─────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: str
    email: str
    name: str
    date_of_birth: Optional[date] = None
    gender: Optional[GenderEnum] = None
    timezone: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[GenderEnum] = None
    timezone: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# ─── Instagram ────────────────────────────────────────────────────────────────

class InstagramConnectionOut(BaseModel):
    id: str
    ig_account_id: str
    ig_username: Optional[str]
    connected_at: datetime
    token_expiry: Optional[datetime]
    is_active: bool
    scopes: Optional[List[str]] = []

    class Config:
        from_attributes = True


# ─── Schedule ─────────────────────────────────────────────────────────────────

class ScheduleOut(BaseModel):
    id: str
    hhmm_time: str
    timezone: str
    active: bool
    skip_next: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]

    class Config:
        from_attributes = True


class ScheduleCreate(BaseModel):
    hhmm_time: str  # "HH:MM"
    timezone: str = "UTC"

    @field_validator("hhmm_time")
    @classmethod
    def valid_time(cls, v: str) -> str:
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format")
        h, m = parts
        if not (h.isdigit() and m.isdigit()):
            raise ValueError("Time must be in HH:MM format")
        if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
            raise ValueError("Invalid time values")
        return v


# ─── Posts ────────────────────────────────────────────────────────────────────

class PostOut(BaseModel):
    id: str
    scheduled_for: datetime
    quote_text: Optional[str]
    quote_author: Optional[str]
    caption_text: Optional[str]
    status: PostStatus
    instagram_post_id: Optional[str]
    error_message: Optional[str]
    retry_count: Optional[str]
    created_at: datetime
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    message: str
