from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, RefreshToken
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, MessageOut
from app.auth import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, hash_token
)
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        timezone=payload.timezone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _issue_tokens(user, db)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    return _issue_tokens(user, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = hash_token(payload.refresh_token)
    db_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Rotate: revoke old, issue new
    db_token.revoked = True
    db.commit()

    user = db.query(User).filter(User.id == db_token.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return _issue_tokens(user, db)


@router.post("/logout", response_model=MessageOut)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = hash_token(payload.refresh_token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if db_token:
        db_token.revoked = True
        db.commit()
    return {"message": "Logged out"}


# ─── Helper ──────────────────────────────────────────────────────────────────

def _issue_tokens(user: User, db: Session) -> dict:
    access = create_access_token(user.id)
    raw_refresh, hashed_refresh = create_refresh_token()

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.commit()

    return TokenResponse(access_token=access, refresh_token=raw_refresh)
