import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Post, PostStatus
from app.schemas import PostOut, MessageOut
from app.auth import get_current_user
from app.services.quotes import generate_quote_with_openai

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("", response_model=List[PostOut])
def list_posts(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    posts = (
        db.query(Post)
        .filter(Post.user_id == current_user.id)
        .order_by(Post.scheduled_for.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    result = []
    for p in posts:
        po = PostOut.model_validate(p)
        if p.image_path and os.path.exists(p.image_path):
            po.image_url = f"/api/video/post/{p.id}/stream"
        result.append(po)
    return result


@router.get("/preview")
def preview_quote(current_user: User = Depends(get_current_user)):
    """Generate a fresh AI quote for dashboard preview."""
    quote, author = generate_quote_with_openai()
    return {"quote": quote, "author": author}


@router.get("/{post_id}", response_model=PostOut)
def get_post(
    post_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == current_user.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    po = PostOut.model_validate(post)
    if post.image_path and os.path.exists(post.image_path):
        po.image_url = f"/api/video/post/{post_id}/stream"
    return po
