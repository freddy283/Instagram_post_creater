import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Enum as SAEnum,
    ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


def gen_uuid():
    return str(uuid.uuid4())


class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    non_binary = "non_binary"
    prefer_not_to_say = "prefer_not_to_say"


class PostStatus(str, enum.Enum):
    pending = "pending"
    queued = "queued"
    video_ready = "video_ready"   # Video generated, waiting to be posted/downloaded
    success = "success"           # Posted to Instagram or manually acknowledged
    failed = "failed"
    skipped = "skipped"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(SAEnum(GenderEnum), nullable=True)
    timezone = Column(String, default="UTC")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    # User preferences
    ig_handle = Column(String, nullable=True)          # @handle for video watermark
    video_theme = Column(String, nullable=True)        # Custom theme override
    notify_email = Column(Boolean, default=True)       # Email reminder when video is ready
    auto_post_ig = Column(Boolean, default=False)      # Auto-post to IG if connected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    instagram_connections = relationship("InstagramConnection", back_populates="user", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="refresh_tokens")


class InstagramConnection(Base):
    __tablename__ = "instagram_connections"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    ig_account_id = Column(String, nullable=False)
    ig_username = Column(String, nullable=True)
    access_token_encrypted = Column(Text, nullable=False)
    token_expiry = Column(DateTime, nullable=True)
    scopes = Column(JSON, default=list)
    connected_at = Column(DateTime, default=datetime.utcnow)
    last_refresh_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="instagram_connections")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    hhmm_time = Column(String, nullable=False, default="09:00")
    timezone = Column(String, nullable=False, default="UTC")
    active = Column(Boolean, default=True)
    skip_next = Column(Boolean, default=False)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="schedules")


class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    scheduled_for = Column(DateTime, nullable=False)
    image_path = Column(String, nullable=True)          # path to .mp4 file
    caption_text = Column(Text, nullable=True)
    quote_text = Column(Text, nullable=True)
    quote_author = Column(String, nullable=True)
    video_theme = Column(String, nullable=True)         # theme used for this video
    status = Column(SAEnum(PostStatus), default=PostStatus.pending)
    instagram_post_id = Column(String, nullable=True)
    ig_auto_posted = Column(Boolean, default=False)     # whether it was auto-posted to IG
    error_message = Column(Text, nullable=True)
    retry_count = Column(String, default="0")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="posts")


class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    status = Column(String, default="pending")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
