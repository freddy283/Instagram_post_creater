from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import pytz

from app.database import get_db
from app.models import User, Schedule
from app.schemas import ScheduleOut, ScheduleCreate, MessageOut
from app.auth import get_current_user

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


def compute_next_run(hhmm: str, timezone: str) -> datetime:
    """Compute next UTC datetime for the given local HH:MM."""
    try:
        tz = pytz.timezone(timezone)
    except Exception:
        tz = pytz.UTC

    now_local = datetime.now(tz)
    h, m = int(hhmm[:2]), int(hhmm[3:])
    next_run = now_local.replace(hour=h, minute=m, second=0, microsecond=0)
    if next_run <= now_local:
        from datetime import timedelta
        next_run += timedelta(days=1)
    return next_run.astimezone(pytz.UTC).replace(tzinfo=None)


@router.get("", response_model=ScheduleOut)
def get_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = db.query(Schedule).filter(Schedule.user_id == current_user.id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="No schedule found")
    return schedule


@router.post("", response_model=ScheduleOut)
def set_schedule(
    payload: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = db.query(Schedule).filter(Schedule.user_id == current_user.id).first()
    next_run = compute_next_run(payload.hhmm_time, payload.timezone)

    if schedule:
        schedule.hhmm_time = payload.hhmm_time
        schedule.timezone = payload.timezone
        schedule.active = True
        schedule.next_run = next_run
    else:
        schedule = Schedule(
            user_id=current_user.id,
            hhmm_time=payload.hhmm_time,
            timezone=payload.timezone,
            active=True,
            next_run=next_run,
        )
        db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.post("/pause", response_model=ScheduleOut)
def pause_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = db.query(Schedule).filter(Schedule.user_id == current_user.id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="No schedule found")
    schedule.active = False
    db.commit()
    db.refresh(schedule)
    return schedule


@router.post("/resume", response_model=ScheduleOut)
def resume_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = db.query(Schedule).filter(Schedule.user_id == current_user.id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="No schedule found")
    schedule.active = True
    schedule.next_run = compute_next_run(schedule.hhmm_time, schedule.timezone)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.post("/skip", response_model=MessageOut)
def skip_next(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = db.query(Schedule).filter(Schedule.user_id == current_user.id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="No schedule found")
    schedule.skip_next = True
    db.commit()
    return {"message": "Next post will be skipped"}
